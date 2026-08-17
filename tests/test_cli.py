import os

import httpx
import pytest
from conftest import make_transport
from typer.testing import CliRunner

from ghdir.cli import app
from ghdir.github import GitHubClient

runner = CliRunner()

URL = "https://github.com/octo/hello/tree/main/src"


@pytest.fixture
def mock_cli(monkeypatch, tree, tmp_path):
    monkeypatch.chdir(tmp_path)
    real_client = GitHubClient
    monkeypatch.setattr(
        "ghdir.cli.GitHubClient", lambda: real_client(transport=make_transport(tree))
    )
    real_async_client = httpx.AsyncClient
    transport = make_transport(tree)
    monkeypatch.setattr(
        "ghdir.cli.httpx.AsyncClient", lambda **kw: real_async_client(**kw, transport=transport)
    )
    return tree


def test_cli_download_to_output(tmp_path, mock_cli):
    result = runner.invoke(app, [URL, "-o", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "main.py").is_file()
    assert (tmp_path / "out" / "utils.py").is_file()
    assert "Downloaded 2 files" in result.stdout


def test_cli_second_run_skips_up_to_date(tmp_path, mock_cli, monkeypatch):
    shas = {e["path"]: e["sha"] for e in mock_cli["trees"]["sha-src"]}

    def fake_existing_sha(dest_root, rel_path):
        if os.path.isfile(os.path.join(dest_root, rel_path)):
            return shas[rel_path]
        return None

    monkeypatch.setattr("ghdir.downloader.filesystem.existing_sha", fake_existing_sha)
    runner.invoke(app, [URL, "-o", str(tmp_path / "out")])
    result = runner.invoke(app, [URL, "-o", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    assert "Downloaded 0 files, skipped 2 already up to date" in result.stdout


def test_cli_force_redownloads(tmp_path, mock_cli, monkeypatch):
    shas = {e["path"]: e["sha"] for e in mock_cli["trees"]["sha-src"]}
    monkeypatch.setattr(
        "ghdir.downloader.filesystem.existing_sha",
        lambda dest_root, rel_path: shas.get(rel_path),
    )
    result = runner.invoke(app, [URL, "-o", str(tmp_path / "out"), "--force"])
    assert result.exit_code == 0, result.output
    assert "Downloaded 2 files" in result.stdout
    assert "skipped" not in result.stdout


def test_cli_default_output_dir(tmp_path, mock_cli):
    result = runner.invoke(app, [URL])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "src" / "main.py").is_file()


def test_cli_dry_run_writes_nothing(tmp_path, mock_cli):
    result = runner.invoke(app, [URL, "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Found 2 files (125 bytes) in main/src" in result.stdout
    assert not (tmp_path / "src").exists()


def test_cli_dry_run_exclude(tmp_path, mock_cli):
    result = runner.invoke(
        app, ["https://github.com/octo/hello/tree/main", "--dry-run", "--exclude", "*.md"]
    )
    assert result.exit_code == 0, result.output
    assert "Filtered out 2 files; 2 remain" in result.stdout
    assert "Nothing to download" not in result.stdout
    assert not (tmp_path / "hello").exists()


def test_cli_everything_filtered(tmp_path, mock_cli):
    result = runner.invoke(
        app, [URL, "--dry-run", "--exclude", "*.py"]
    )
    assert result.exit_code == 0, result.output
    assert "Filtered out 2 files; 0 remain (0 bytes)" in result.stdout
    assert "Nothing to download after filtering" in result.stdout
    assert not (tmp_path / "src").exists()


def test_cli_empty_directory(tmp_path, mock_cli, monkeypatch):
    from ghdir.models import ResolvedRepo

    monkeypatch.setattr(
        "ghdir.cli.resolve",
        lambda *a, **kw: ResolvedRepo("octo", "hello", "main", "empty", ()),
    )
    result = runner.invoke(app, [URL, "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Nothing to download; directory is empty" in result.stdout
    assert "after filtering" not in result.stdout


def test_cli_branch_override(tmp_path, mock_cli):
    result = runner.invoke(
        app, ["https://github.com/octo/hello/tree/main", "--branch", "dev"]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "hello" / "dev_note.md").is_file()
    assert not (tmp_path / "hello" / "README.md").exists()


def test_cli_branch_override_keeps_slashed_branch_path(tmp_path, mock_cli):
    result = runner.invoke(
        app, ["https://github.com/octo/hello/tree/feature/x/sub", "--branch", "dev"]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "sub" / "data.txt").is_file()


def test_cli_missing_path_error(tmp_path, mock_cli):
    result = runner.invoke(app, ["https://github.com/octo/hello/tree/main/nope"])
    assert result.exit_code == 1
    assert "error:" in result.stderr
    assert "not found" in result.stderr


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ghdir 0.1.0" in result.stdout


def test_cli_completion_not_disabled():
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "200", "LINES": "50"})
    assert result.exit_code == 0
    assert "--install-completion" in result.stdout
    assert "--show-completion" in result.stdout


def test_cli_invalid_url_error(mock_cli):
    result = runner.invoke(app, ["https://example.com/octo/hello"])
    assert result.exit_code == 1
    assert "error:" in result.stderr