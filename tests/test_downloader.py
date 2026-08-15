import httpx
import pytest

from ghdir.downloader import download_all
from ghdir.models import FileEntry


def _files():
    return [
        FileEntry("a.txt", 3, "s1", "https://raw.githubusercontent.com/octo/hello/main/a.txt"),
        FileEntry(
            "sub/b.txt", 3, "s2", "https://raw.githubusercontent.com/octo/hello/main/sub/b.txt"
        ),
    ]


def test_download_all_writes_files(tmp_path):
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=b"content " + r.url.path.encode())
        )
    )
    try:
        written = download_all(_files(), str(tmp_path), http)
    finally:
        http.close()
    assert (tmp_path / "a.txt").read_bytes() == b"content /octo/hello/main/a.txt"
    assert (tmp_path / "sub" / "b.txt").read_bytes() == b"content /octo/hello/main/sub/b.txt"
    assert written == [str(tmp_path / "a.txt"), str(tmp_path / "sub" / "b.txt")]


def test_download_failure_propagates(tmp_path):
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    try:
        with pytest.raises(httpx.HTTPStatusError):
            download_all(_files(), str(tmp_path), http)
    finally:
        http.close()