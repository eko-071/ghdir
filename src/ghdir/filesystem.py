"""Safe filesystem writes: path sanitization and traversal protection."""

from __future__ import annotations

import contextlib
import hashlib
import os


def git_blob_sha(data: bytes) -> str:
    """Git's content hash for a blob: sha1("blob {len}\\0" + content)."""
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def sanitize_relative_path(rel_path: str) -> str:
    parts = []
    for component in rel_path.split("/"):
        if component in ("", ".", ".."):
            raise ValueError(f"unsafe path component in {rel_path!r}")
        parts.append(component)
    if not parts:
        raise ValueError(f"empty path {rel_path!r}")
    return "/".join(parts)


def _target_path(dest_root: str, rel_path: str) -> str:
    safe = sanitize_relative_path(rel_path)
    root = os.path.realpath(dest_root)
    target = os.path.realpath(os.path.join(root, safe))
    if target != root and not target.startswith(root + os.sep):
        raise ValueError(f"path escapes output directory: {rel_path!r}")
    return target


def existing_sha(dest_root: str, rel_path: str) -> str | None:
    """Blob SHA of the local file at rel_path, or None if it doesn't exist."""
    target = _target_path(dest_root, rel_path)
    if not os.path.isfile(target):
        return None
    with open(target, "rb") as f:
        return git_blob_sha(f.read())


def write_file(dest_root: str, rel_path: str, data: bytes) -> str:
    """Write `data` to `dest_root/rel_path`, rejecting paths that escape the root.

    Writes to a temp file first and renames it into place, so a killed
    process never leaves a truncated file at the final path.
    """
    target = _target_path(dest_root, rel_path)

    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + f".{os.getpid()}.tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, target)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.remove(tmp)
        raise
    return target