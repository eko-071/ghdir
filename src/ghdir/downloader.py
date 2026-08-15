"""Sequential download engine. Async/streaming/retries land in Phase 3."""

from __future__ import annotations

from collections.abc import Callable

import httpx

from ghdir import filesystem
from ghdir.models import FileEntry

Report = Callable[[int, int], None]


def download_all(
    files: list[FileEntry] | tuple[FileEntry, ...],
    dest_root: str,
    http: httpx.Client,
    report: Report | None = None,
) -> list[str]:
    """Download every file, preserving relative paths under `dest_root`. Returns written paths.

    `report(done_files, done_bytes)` is called after each file.
    """
    written: list[str] = []
    done_bytes = 0
    for done_files, entry in enumerate(files, 1):
        resp = http.get(entry.download_url)
        resp.raise_for_status()
        written.append(filesystem.write_file(dest_root, entry.path, resp.content))
        done_bytes += entry.size
        if report:
            report(done_files, done_bytes)
    return written