import pytest
from conftest import make_transport
from typer.testing import CliRunner

from ghdir.cli import app
from ghdir.github import GitHubClient

runner = CliRunner()

URL = "https://github.com/octo/hello/tree/main/src"


class _FakeClient:
    def __init__(self, transport):
        self._real = GitHubClient(transport=transport)

    def __enter__(self):
        return self._real

    def __exit__(self, *exc):
        self._real.http.close()


@pytest.fixture
def mock_cli(monkeypatch, tree, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("ghdir.cli.GitHubClient", lambda: _FakeClient(make_transport(tree)))
    return tree


def test_cli_download_to_output(tmp_path, mock_cli):
    result = runner.invoke(app, [URL, "-o", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "main.py").is_file()
    assert (tmp_path / "out" / "utils.py").is_file()
    assert "Downloaded 2 files" in result.stdout


def test_cli_default_output_dir(tmp_path, mock_cli):
    result = runner.invoke(app, [URL])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "src" / "main.py").is_file()


def test_cli_dry_run_writes_nothing(tmp_path, mock_cli):
    result = runner.invoke(app, [URL, "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Found 2 files (125 bytes) in main/src" in result.stdout
    assert not (tmp_path / "src").exists()


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


def test_cli_invalid_url_error(mock_cli):
    result = runner.invoke(app, ["https://example.com/octo/hello"])
    assert result.exit_code == 1
    assert "error:" in result.stderr