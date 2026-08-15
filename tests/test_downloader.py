import asyncio

import httpx
import pytest

from ghdir.downloader import download_all_async
from ghdir.models import FileEntry


def _files():
    return [
        FileEntry("a.txt", 3, "s1", "https://raw.githubusercontent.com/octo/hello/main/a.txt"),
        FileEntry(
            "sub/b.txt", 3, "s2", "https://raw.githubusercontent.com/octo/hello/main/sub/b.txt"
        ),
    ]


def _async_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_download_all_writes_files(tmp_path):
    client = _async_client(lambda r: httpx.Response(200, content=b"content " + r.url.path.encode()))
    try:
        written = asyncio.run(download_all_async(_files(), str(tmp_path), client))
    finally:
        asyncio.run(client.aclose())
    assert (tmp_path / "a.txt").read_bytes() == b"content /octo/hello/main/a.txt"
    assert (tmp_path / "sub" / "b.txt").read_bytes() == b"content /octo/hello/main/sub/b.txt"
    assert written == [str(tmp_path / "a.txt"), str(tmp_path / "sub" / "b.txt")]


def test_download_failure_propagates(tmp_path):
    client = _async_client(lambda r: httpx.Response(500))
    try:
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(download_all_async(_files(), str(tmp_path), client))
    finally:
        asyncio.run(client.aclose())


def test_retries_then_succeeds(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, content=b"recovered")

    files = [FileEntry("a.txt", 3, "s1", "https://raw.githubusercontent.com/o/r/main/a.txt")]
    client = _async_client(handler)
    try:
        written = asyncio.run(download_all_async(files, str(tmp_path), client))
    finally:
        asyncio.run(client.aclose())
    assert calls["n"] == 3
    assert (tmp_path / "a.txt").read_bytes() == b"recovered"
    assert written == [str(tmp_path / "a.txt")]


def test_concurrent_workers_download_all_files(tmp_path):
    files = [
        FileEntry(f"f{i}.txt", 3, f"s{i}", f"https://raw.githubusercontent.com/o/r/main/f{i}.txt")
        for i in range(5)
    ]
    client = _async_client(lambda r: httpx.Response(200, content=b"x"))
    try:
        written = asyncio.run(download_all_async(files, str(tmp_path), client, workers=2))
    finally:
        asyncio.run(client.aclose())
    assert len(written) == 5
    assert all((tmp_path / f"f{i}.txt").is_file() for i in range(5))