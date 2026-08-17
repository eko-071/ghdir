"""Token storage for GitHub authentication."""

from __future__ import annotations

import os
import stat
from pathlib import Path

TOKEN_PATH = Path(
    os.environ.get("GHDIR_CONFIG_DIR", Path.home() / ".config" / "ghdir")
) / "token"


def save_token(token: str) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(token.strip())
    TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600, owner read/write only


def load_token() -> str | None:
    """GHDIR_TOKEN env var wins over the stored file — handy for CI."""
    if env := os.environ.get("GHDIR_TOKEN"):
        return env.strip()
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip() or None
    return None


def clear_token() -> None:
    TOKEN_PATH.unlink(missing_ok=True)