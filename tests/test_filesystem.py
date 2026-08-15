import pytest

from ghdir.filesystem import sanitize_relative_path, write_file


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