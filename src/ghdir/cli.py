"""Typer CLI entry point."""

from __future__ import annotations

import asyncio
import os
from importlib.metadata import version
from pathlib import Path

import httpx
import typer
from rich.progress import BarColumn, DownloadColumn, Progress, TaskProgressColumn, TextColumn
from typer import _click
from typer.core import TyperGroup, _split_opt

from ghdir import auth
from ghdir.downloader import DownloadResult, download_all_async
from ghdir.errors import GhdirError
from ghdir.filters import apply_filters, parse_size
from ghdir.github import GitHubClient
from ghdir.parser import parse_github_url
from ghdir.resolver import resolve


class _DefaultCommandGroup(TyperGroup):
    """Treat an unrecognized first token (a URL) as the download command."""

    _DEFAULT = "download"

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except _click.exceptions.UsageError:
            if args and not _split_opt(args[0])[0]:
                cmd = self.commands.get(self._DEFAULT)
                if cmd is not None:
                    return self._DEFAULT, cmd, args
            raise


app = typer.Typer(
    cls=_DefaultCommandGroup,
    invoke_without_command=True,
    help="Download a subdirectory of a GitHub repository.",
)
auth_app = typer.Typer(help="Manage GitHub authentication.")
app.add_typer(auth_app, name="auth")


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"ghdir {version('ghdir')}")
        raise typer.Exit()


@auth_app.command("login")
def auth_login(
    token: str = typer.Option(
        None, "--token", help="Paste a token directly (otherwise prompted)."
    ),
) -> None:
    token = token or typer.prompt("GitHub personal access token", hide_input=True)
    auth.save_token(token)
    typer.echo(f"Saved to {auth.TOKEN_PATH}. Run 'ghdir auth status' to verify.")


@auth_app.command("logout")
def auth_logout() -> None:
    auth.clear_token()
    typer.echo("Removed stored token.")


@auth_app.command("status")
def auth_status() -> None:
    token = auth.load_token()
    if not token:
        typer.echo("Not logged in.")
        raise typer.Exit(code=1)
    resp = httpx.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        typer.echo("Stored token is invalid or expired.")
        raise typer.Exit(code=1)
    typer.echo(f"Logged in as {resp.json()['login']}")


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", is_eager=True, callback=_print_version, help="Show the version and exit."
    ),
) -> None:
    """Download the directory at a GitHub tree URL, e.g. .../tree/main/Embodied."""
    if ctx.invoked_subcommand is not None:
        return
    typer.echo("Error: Missing argument 'URL'.", err=True)
    raise typer.Exit(code=1)


@app.command("download", hidden=True)
def download(
    url: str,
    output: Path = typer.Option(
        None,
        "-o",
        "--output",
        file_okay=False,
        dir_okay=True,
        writable=True,
        help="Output directory (default: the target dir's name).",
    ),
    branch: str = typer.Option(None, "--branch", help="Override the branch parsed from the URL."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Resolve and report, download nothing."),
    workers: int = typer.Option(8, "--workers", help="Number of concurrent downloads."),
    include: list[str] = typer.Option(
        [], "--include", help="Only download files matching this glob (repeatable)."
    ),
    exclude: list[str] = typer.Option(
        [], "--exclude", help="Skip files matching this glob (repeatable)."
    ),
    max_size: str = typer.Option(
        None, "--max-size", help="Skip files larger than this, e.g. '50M', '1.5G'."
    ),
    force: bool = typer.Option(
        False, "--force", help="Re-download files even if already up to date."
    ),
) -> None:
    try:
        ref = parse_github_url(url)
        token = auth.load_token()

        with GitHubClient(token=token) as client:
            resolved = resolve(client, ref, branch_override=branch)

            max_size_bytes = parse_size(max_size) if max_size else None
            files = apply_filters(resolved.files, include, exclude, max_size_bytes)
            total_bytes = sum(f.size for f in files)

            where = resolved.branch + (f"/{resolved.path}" if resolved.path else "")
            typer.echo(f"Found {len(resolved.files)} files ({resolved.total_bytes} bytes) in {where}")

            skipped = len(resolved.files) - len(files)
            if skipped:
                typer.echo(f"Filtered out {skipped} files; {len(files)} remain ({total_bytes} bytes)")

            if not files:
                if resolved.files:
                    typer.echo("Nothing to download after filtering")
                else:
                    typer.echo("Nothing to download; directory is empty")
                return
            if dry_run:
                return

            dest = str(output) if output else resolved.default_output_dir
            os.makedirs(dest, exist_ok=True)
            with _progress() as progress:
                task = progress.add_task(
                    f"Downloading {len(files)} files", total=total_bytes
                )

                async def _run() -> DownloadResult:
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    async with httpx.AsyncClient(timeout=30, headers=headers) as download_client:
                        return await download_all_async(
                            files,
                            dest,
                            download_client,
                            workers=workers,
                            report=lambda done_bytes: progress.update(
                                task, completed=done_bytes
                            ),
                            skip_existing=not force,
                        )

                result = asyncio.run(_run())
        if result.skipped:
            typer.echo(
                f"Downloaded {len(result.written)} files, "
                f"skipped {result.skipped} already up to date, to {dest}"
            )
        else:
            typer.echo(f"Downloaded {len(result.written)} files to {dest}")
    except GhdirError as e:
        typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        typer.secho(f"error: network request failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


def _progress() -> Progress:
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
    )


if __name__ == "__main__":
    app()