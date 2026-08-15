"""Typer CLI entry point."""

from __future__ import annotations

import httpx
import typer
from rich.progress import BarColumn, DownloadColumn, Progress, TaskProgressColumn, TextColumn

from ghdir import __version__, filesystem
from ghdir.downloader import download_all
from ghdir.errors import GhdirError
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
) -> None:
    """Download the directory at a GitHub tree URL, e.g. .../tree/main/Embodied."""
    try:
        ref = parse_github_url(url)

        with GitHubClient() as client:
            resolved = resolve(client, ref, branch_override=branch)

            where = resolved.branch + (f"/{resolved.path}" if resolved.path else "")
            typer.echo(f"Found {len(resolved.files)} files ({resolved.total_bytes} bytes) in {where}")
            if not resolved.files:
                typer.echo("Nothing to download; directory is empty")
                return
            if dry_run:
                return

            dest = output or resolved.default_output_dir
            filesystem.ensure_output_dir(dest)
            with _progress() as progress:
                task = progress.add_task(
                    f"Downloading {len(resolved.files)} files", total=resolved.total_bytes
                )
                download_all(
                    resolved.files,
                    dest,
                    client.http,
                    report=lambda done_files, done_bytes: progress.update(task, completed=done_bytes),
                )
        typer.echo(f"Downloaded {len(resolved.files)} files ({resolved.total_bytes} bytes) to {dest}")
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