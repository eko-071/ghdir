"""Typer CLI entry point."""

from __future__ import annotations

import httpx
import typer

from ghdir import filesystem
from ghdir.downloader import download_all
from ghdir.errors import GhdirError
from ghdir.github import GitHubClient
from ghdir.parser import parse_github_url
from ghdir.resolver import resolve

app = typer.Typer(add_completion=False, help="Download a subdirectory of a GitHub repository.")


@app.command()
def main(url: str) -> None:
    """Download the directory at a GitHub tree URL, e.g. .../tree/main/Embodied."""
    try:
        ref = parse_github_url(url)
        with GitHubClient() as client:
            resolved = resolve(client, ref)
            dest = resolved.default_output_dir
            filesystem.ensure_output_dir(dest)
            written = download_all(resolved.files, dest, client.http)
        typer.echo(f"Downloaded {len(written)} files ({resolved.total_bytes} bytes) to {dest}")
    except GhdirError as e:
        typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        typer.secho(f"error: network request failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()