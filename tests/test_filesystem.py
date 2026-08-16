import pytest

import ghdir.filesystem
from ghdir.filesystem import existing_sha, git_blob_sha, sanitize_relative_path, write_file


def test_git_blob_sha_empty_matches_known_value():
    assert git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def test_existing_sha_none_for_missing_file(tmp_path):
    assert existing_sha(str(tmp_path), "nope.txt") is None


def test_existing_sha_for_existing_file(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"hello")
    assert existing_sha(str(tmp_path), "a.txt") == git_blob_sha(b"hello")


def test_write_nested_creates_dirs(tmp_path):
    target = write_file(str(tmp_path), "a/b/c.txt", b"data")
    assert target == str(tmp_path / "a" / "b" / "c.txt")
    assert (tmp_path / "a" / "b" / "c.txt").read_bytes() == b"data"


def test_sanitize_allows_normal_paths():
    assert sanitize_relative_path("src/main.py") == "src/main.py"


@pytest.mark.parametrize("bad", ["../evil", "a/../../evil", "a//b", "a/./b"])
def test_sanitize_rejects_unsafe(tmp_path, bad):
    with pytest.raises(ValueError):
        write_file(str(tmp_path), bad, b"x")


def test_sanitize_rejects_empty():
    with pytest.raises(ValueError):
        sanitize_relative_path("")


def test_write_file_leaves_no_partial_file_on_failure(tmp_path, monkeypatch):
    """If the write itself fails, no temp or target file should remain."""

    class _Boom:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def write(self, data):
            raise OSError("disk full")

    monkeypatch.setattr(
        ghdir.filesystem, "open", lambda *a, **kw: _Boom(), raising=False
    )

    with pytest.raises(OSError):
        write_file(str(tmp_path), "file.txt", b"data")

    assert list(tmp_path.rglob("*")) == []