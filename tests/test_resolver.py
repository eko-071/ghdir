import httpx
import pytest

from ghdir.errors import BranchNotFoundError, PathNotFoundError, RepoNotFoundError
from ghdir.github import GitHubClient
from ghdir.models import RepoRef
from ghdir.resolver import _raw_url, resolve


def test_resolve_repo_root(client):
    resolved = resolve(client, RepoRef("octo", "hello"))
    assert resolved.branch == "main"
    assert resolved.path == ""
    assert {f.path for f in resolved.files} == {
        "README.md",
        "src/main.py",
        "src/utils.py",
        "docs/guide.md",
    }


def test_resolve_subdir(client):
    resolved = resolve(client, RepoRef("octo", "hello", ("main", "src")))
    assert resolved.branch == "main"
    assert resolved.path == "src"
    assert {f.path for f in resolved.files} == {"main.py", "utils.py"}
    assert {f.download_url for f in resolved.files} == {
        "https://raw.githubusercontent.com/octo/hello/main/src/main.py",
        "https://raw.githubusercontent.com/octo/hello/main/src/utils.py",
    }


def test_resolve_branch_with_slash(client):
    resolved = resolve(client, RepoRef("octo", "hello", ("feature", "x")))
    assert resolved.branch == "feature/x"
    assert resolved.path == ""
    assert {f.path for f in resolved.files} == {"nested.py"}


def test_resolve_branch_with_slash_and_path(client):
    with pytest.raises(PathNotFoundError):
        resolve(client, RepoRef("octo", "hello", ("feature", "x", "sub")))


def test_branch_override_keeps_path_after_slashed_branch(client):
    resolved = resolve(
        client, RepoRef("octo", "hello", ("feature", "x", "sub")), branch_override="dev"
    )
    assert resolved.branch == "dev"
    assert resolved.path == "sub"
    assert {f.path for f in resolved.files} == {"data.txt"}
    assert {f.download_url for f in resolved.files} == {
        "https://raw.githubusercontent.com/octo/hello/dev/sub/data.txt"
    }


def test_branch_override_unknown_raises(client):
    with pytest.raises(BranchNotFoundError):
        resolve(client, RepoRef("octo", "hello", ("main",)), branch_override="nope")


def test_missing_branch_raises(client):
    with pytest.raises(BranchNotFoundError):
        resolve(client, RepoRef("octo", "hello", ("nope",)))


def test_missing_path_raises(client):
    with pytest.raises(PathNotFoundError):
        resolve(client, RepoRef("octo", "hello", ("main", "nope")))


def test_missing_repo_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    with GitHubClient(transport=httpx.MockTransport(handler)) as c, pytest.raises(RepoNotFoundError):
        resolve(c, RepoRef("nope", "nope"))


def test_total_bytes_and_default_output_dir(client):
    resolved = resolve(client, RepoRef("octo", "hello", ("main", "src")))
    assert resolved.total_bytes == 125
    assert resolved.default_output_dir == "src"
    assert resolve(client, RepoRef("octo", "hello")).default_output_dir == "hello"


def test_raw_url_encodes_fragment_in_filename():
    url = _raw_url("octo", "hello", "main", "docs", "notes#draft.md")
    assert "notes%23draft.md" in url
    assert "#" not in url


def test_raw_url_encodes_space_in_filename():
    assert "%20" in _raw_url("octo", "hello", "main", "", "a b.txt")


def test_raw_url_keeps_branch_slashes_literal():
    assert _raw_url("octo", "hello", "feature/x", "", "nested.py") == (
        "https://raw.githubusercontent.com/octo/hello/feature/x/nested.py"
    )


def test_raw_url_encodes_special_chars_in_branch():
    url = _raw_url("octo", "hello", "notes#draft", "", "a.txt")
    assert "notes%23draft" in url