"""Concurrent, streaming download engine with retries."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx

from ghdir import filesystem
from ghdir.models import FileEntry

Report = Callable[[int], None]

MAX_RETRIES = 3
RETRY_STATUS = {429, 500, 502, 503, 504}


async def _fetch(client: httpx.AsyncClient, url: str) -> bytes:
    for attempt in range(MAX_RETRIES):
        try:
            async with client.stream("GET", url) as resp:
                if resp.status_code in RETRY_STATUS and attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                resp.raise_for_status()
                return b"".join([chunk async for chunk in resp.aiter_bytes()])
        except httpx.TransportError:
            if attempt == MAX_RETRIES - 1:
                raise
            await asyncio.sleep(2**attempt)
    raise RuntimeError("unreachable")  # loop always returns or raises


async def download_all_async(
    files: list[FileEntry] | tuple[FileEntry, ...],
    dest_root: str,
    client: httpx.AsyncClient,
    workers: int = 8,
    report: Report | None = None,
) -> list[str]:
    semaphore = asyncio.Semaphore(workers)
    written: list[str] = []
    done_bytes = 0

    async def run(entry: FileEntry) -> None:
        nonlocal done_bytes
        async with semaphore:
            data = await _fetch(client, entry.download_url)
        written.append(filesystem.write_file(dest_root, entry.path, data))
        done_bytes += len(data)
        if report:
            report(done_bytes)

    await asyncio.gather(*(run(entry) for entry in files))
    return written