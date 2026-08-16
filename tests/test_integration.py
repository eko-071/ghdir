"""End-to-end test against the live GitHub API. Run with `pytest -m integration`."""

import asyncio
from pathlib import Path

import httpx
import pytest

from ghdir.downloader import DownloadResult, download_all_async
from ghdir.github import GitHubClient
from ghdir.parser import parse_github_url
from ghdir.resolver import resolve


@pytest.mark.integration
def test_download_nvlab_eagle_embodied(tmp_path):
    ref = parse_github_url("https://github.com/NVlabs/Eagle/tree/main/Embodied")
    with GitHubClient() as client:
        resolved = resolve(client, ref)
        assert resolved.files, "no files resolved"

        async def _run() -> DownloadResult:
            async with httpx.AsyncClient(timeout=60) as download_client:
                return await download_all_async(resolved.files, str(tmp_path), download_client)

        result = asyncio.run(_run())
    assert len(result.written) == len(resolved.files)
    assert all(Path(p).is_file() for p in result.written)