"""Include/exclude glob filtering and max-size filtering."""

from __future__ import annotations

import fnmatch
import re

from ghdir.errors import GhdirError
from ghdir.models import FileEntry

_SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([KMGkmg]?)[Bb]?$")
_SIZE_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}


def parse_size(text: str) -> int:
    """Parse a human size like '50M', '1.5G', or a plain byte count."""
    m = _SIZE_RE.match(text.strip())
    if not m:
        raise GhdirError(f"invalid size {text!r}, expected e.g. '50M', '1.5G', '2048'")
    value, unit = m.groups()
    return int(float(value) * _SIZE_UNITS[unit.upper()])


def apply_filters(
    files: tuple[FileEntry, ...],
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    max_size: int | None = None,
) -> tuple[FileEntry, ...]:
    """Narrow `files` by include globs, then exclude globs, then max size."""
    result = files
    if include:
        result = tuple(f for f in result if any(fnmatch.fnmatchcase(f.path, p) for p in include))
    if exclude:
        result = tuple(
            f for f in result if not any(fnmatch.fnmatchcase(f.path, p) for p in exclude)
        )
    if max_size is not None:
        result = tuple(f for f in result if f.size <= max_size)
    return result
