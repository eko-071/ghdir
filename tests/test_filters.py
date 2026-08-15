import pytest

from ghdir.errors import GhdirError
from ghdir.filters import apply_filters, parse_size
from ghdir.models import FileEntry


def _files(*paths: str) -> tuple[FileEntry, ...]:
    return tuple(
        FileEntry(p, i + 1, f"sha-{i}", f"https://raw.githubusercontent.com/o/r/main/{p}")
        for i, p in enumerate(paths)
    )


def test_parse_size():
    assert parse_size("50M") == 50 * 1024**2
    assert parse_size("1.5G") == int(1.5 * 1024**3)
    assert parse_size("2048") == 2048


def test_parse_size_invalid():
    with pytest.raises(GhdirError):
        parse_size("big")


def test_include_matches_at_any_depth():
    files = _files("models/train.py", "train.py", "README.md")
    assert apply_filters(files, include=["*.py"]) == (files[0], files[1])


def test_exclude_drops_matches():
    files = _files("models/train.py", "README.md", "data.pth")
    assert apply_filters(files, exclude=["*.pth"]) == (files[0], files[1])


def test_exclude_wins_over_include():
    files = _files("models/train.py", "README.md")
    assert apply_filters(files, include=["*.py", "*.md"], exclude=["*.md"]) == (files[0],)


def test_max_size_boundary_is_inclusive():
    big = FileEntry("big.bin", 100, "sha", "url")
    at_limit = FileEntry("at.bin", 50, "sha", "url")
    small = FileEntry("small.bin", 10, "sha", "url")
    assert apply_filters((big, at_limit, small), max_size=50) == (at_limit, small)


def test_no_filters_returns_input():
    files = _files("a.py", "b.md")
    assert apply_filters(files) == files