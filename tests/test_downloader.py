import asyncio

import httpx
import pytest

from ghdir import filesystem
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
        result = asyncio.run(download_all_async(_files(), str(tmp_path), client))
    finally:
        asyncio.run(client.aclose())
    assert (tmp_path / "a.txt").read_bytes() == b"content /octo/hello/main/a.txt"
    assert (tmp_path / "sub" / "b.txt").read_bytes() == b"content /octo/hello/main/sub/b.txt"
    assert result.written == [str(tmp_path / "a.txt"), str(tmp_path / "sub" / "b.txt")]


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
        result = asyncio.run(download_all_async(files, str(tmp_path), client))
    finally:
        asyncio.run(client.aclose())
    assert calls["n"] == 3
    assert (tmp_path / "a.txt").read_bytes() == b"recovered"
    assert result.written == [str(tmp_path / "a.txt")]


def test_concurrent_workers_download_all_files(tmp_path):
    files = [
        FileEntry(f"f{i}.txt", 3, f"s{i}", f"https://raw.githubusercontent.com/o/r/main/f{i}.txt")
        for i in range(5)
    ]
    client = _async_client(lambda r: httpx.Response(200, content=b"x"))
    try:
        result = asyncio.run(download_all_async(files, str(tmp_path), client, workers=2))
    finally:
        asyncio.run(client.aclose())
    assert len(result.written) == 5
    assert all((tmp_path / f"f{i}.txt").is_file() for i in range(5))


def test_skip_existing_makes_no_request(tmp_path):
    content = b"data"
    sha = filesystem.git_blob_sha(content)
    entry = FileEntry("a.txt", 3, sha, "https://raw.githubusercontent.com/o/r/main/a.txt")
    (tmp_path / "a.txt").write_bytes(content)
    assert filesystem.existing_sha(str(tmp_path), "a.txt") == sha

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=b"x")

    client = _async_client(handler)
    try:
        result = asyncio.run(download_all_async([entry], str(tmp_path), client))
    finally:
        asyncio.run(client.aclose())
    assert calls["n"] == 0
    assert result.skipped == 1
    assert result.written == []


def test_mismatched_content_redownloads(tmp_path):
    entry = FileEntry("a.txt", 3, "s1", "https://raw.githubusercontent.com/o/r/main/a.txt")
    (tmp_path / "a.txt").write_bytes(b"other")

    client = _async_client(lambda r: httpx.Response(200, content=b"fresh"))
    try:
        result = asyncio.run(download_all_async([entry], str(tmp_path), client))
    finally:
        asyncio.run(client.aclose())
    assert result.written == [str(tmp_path / "a.txt")]
    assert result.skipped == 0
    assert (tmp_path / "a.txt").read_bytes() == b"fresh"


def test_skip_existing_false_redownloads_matching_file(tmp_path):
    content = b"data"
    sha = filesystem.git_blob_sha(content)
    entry = FileEntry("a.txt", 3, sha, "https://raw.githubusercontent.com/o/r/main/a.txt")
    (tmp_path / "a.txt").write_bytes(content)
    assert filesystem.existing_sha(str(tmp_path), "a.txt") == sha

    client = _async_client(lambda r: httpx.Response(200, content=b"fresh"))
    try:
        result = asyncio.run(
            download_all_async([entry], str(tmp_path), client, skip_existing=False)
        )
    finally:
        asyncio.run(client.aclose())
    assert result.written == [str(tmp_path / "a.txt")]
    assert result.skipped == 0
    assert (tmp_path / "a.txt").read_bytes() == b"fresh"