"""Safe filesystem writes: path sanitization and traversal protection."""

from __future__ import annotations

import os


def sanitize_relative_path(rel_path: str) -> str:
    parts = []
    for component in rel_path.split("/"):
        if component in ("", ".", ".."):
            raise ValueError(f"unsafe path component in {rel_path!r}")
        parts.append(component)
    if not parts:
        raise ValueError(f"empty path {rel_path!r}")
    return "/".join(parts)


def ensure_output_dir(dest: str) -> None:
    os.makedirs(dest, exist_ok=True)


def write_file(dest_root: str, rel_path: str, data: bytes) -> str:
    """Write `data` to `dest_root/rel_path`, rejecting paths that escape the root."""
    safe = sanitize_relative_path(rel_path)
    root = os.path.realpath(dest_root)
    target = os.path.realpath(os.path.join(root, safe))
    if target != root and not target.startswith(root + os.sep):
        raise ValueError(f"path escapes output directory: {rel_path!r}")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as f:
        f.write(data)
    return target