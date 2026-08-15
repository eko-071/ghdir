"""Cross-cutting security: path traversal and symlink escapes."""

import pytest

from ghdir.filesystem import write_file


def test_traversal_outside_root_rejected(tmp_path):
    with pytest.raises(ValueError):
        write_file(str(tmp_path), "..", b"x")
    with pytest.raises(ValueError):
        write_file(str(tmp_path), "../outside.txt", b"x")


def test_symlink_escape_rejected(tmp_path):
    escape = tmp_path.parent / "escape_dir"
    escape.mkdir(exist_ok=True)
    (tmp_path / "link").symlink_to(escape)
    with pytest.raises(ValueError):
        write_file(str(tmp_path), "link/evil.txt", b"x")


def test_normal_file_inside_root_ok(tmp_path):
    target = write_file(str(tmp_path), "docs/readme.md", b"hi")
    assert target == str(tmp_path / "docs" / "readme.md")
    assert (tmp_path / "docs" / "readme.md").read_bytes() == b"hi"