"""Typer CLI entry point."""

from __future__ import annotations

import asyncio
import os

import httpx
import typer
from rich.progress import BarColumn, DownloadColumn, Progress, TaskProgressColumn, TextColumn

from ghdir import __version__
from ghdir.downloader import DownloadResult, download_all_async
from ghdir.errors import GhdirError
from ghdir.filters import apply_filters, parse_size
from ghdir.github import GitHubClient
from ghdir.parser import parse_github_url
from ghdir.resolver import resolve

app = typer.Typer(add_completion=False, help="Download a subdirectory of a GitHub repository.")


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"ghdir {__version__}")
        raise typer.Exit()


@app.command()
def main(
    url: str,
    version: bool = typer.Option(
        False, "--version", is_eager=True, callback=_print_version, help="Show the version and exit."
    ),
    output: str = typer.Option(
        None, "-o", "--output", help="Output directory (default: the target dir's name)."
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
    """Download the directory at a GitHub tree URL, e.g. .../tree/main/Embodied."""
    try:
        ref = parse_github_url(url)

        with GitHubClient() as client:
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

            dest = output or resolved.default_output_dir
            os.makedirs(dest, exist_ok=True)
            with _progress() as progress:
                task = progress.add_task(
                    f"Downloading {len(files)} files", total=total_bytes
                )

                async def _run() -> DownloadResult:
                    async with httpx.AsyncClient(timeout=30) as download_client:
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