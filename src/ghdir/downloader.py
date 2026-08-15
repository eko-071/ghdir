"""Sequential download engine. Async/streaming/retries land in Phase 3."""

from __future__ import annotations

import httpx

from ghdir import filesystem
from ghdir.models import FileEntry


def download_all(
    files: list[FileEntry] | tuple[FileEntry, ...], dest_root: str, http: httpx.Client
) -> list[str]:
    """Download every file, preserving relative paths under `dest_root`. Returns written paths."""
    written: list[str] = []
    for entry in files:
        resp = http.get(entry.download_url)
        resp.raise_for_status()
        written.append(filesystem.write_file(dest_root, entry.path, resp.content))
    return written