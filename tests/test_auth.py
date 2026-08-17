import stat

import pytest

from ghdir import auth


@pytest.fixture
def token_path(tmp_path, monkeypatch):
    monkeypatch.delenv("GHDIR_TOKEN", raising=False)
    path = tmp_path / "token"
    monkeypatch.setattr(auth, "TOKEN_PATH", path)
    return path


def test_save_load_roundtrip(token_path):
    auth.save_token(" abc123 ")
    assert token_path.read_text() == "abc123"
    assert auth.load_token() == "abc123"


def test_save_sets_0600_permissions(token_path):
    auth.save_token("abc")
    assert stat.S_IMODE(token_path.stat().st_mode) == 0o600


def test_env_var_wins_over_stored_file(token_path, monkeypatch):
    auth.save_token("stored")
    monkeypatch.setenv("GHDIR_TOKEN", "envtoken")
    assert auth.load_token() == "envtoken"


def test_clear_token(token_path):
    auth.save_token("abc")
    auth.clear_token()
    assert not token_path.exists()
    assert auth.load_token() is None