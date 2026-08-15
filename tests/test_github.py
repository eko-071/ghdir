import httpx
import pytest
from conftest import make_transport

from ghdir.errors import PrivateRepoError, RepoNotFoundError
from ghdir.github import GitHubClient


def test_repo_404_raises_repo_not_found():
    with GitHubClient(transport=httpx.MockTransport(lambda r: httpx.Response(404, json={}))) as c, pytest.raises(
        RepoNotFoundError
    ):
        c.repo("nope", "nope")


def test_retries_transient_503_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"full_name": "octo/hello", "default_branch": "main"})

    with GitHubClient(transport=httpx.MockTransport(handler)) as c:
        assert c.repo("octo", "hello")["default_branch"] == "main"
    assert calls["n"] == 3


def test_retries_do_not_retry_404():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, json={})

    with GitHubClient(transport=httpx.MockTransport(handler)) as c, pytest.raises(
        RepoNotFoundError
    ):
        c.repo("nope", "nope")
    assert calls["n"] == 1


def test_repo_403_raises_private():
    with GitHubClient(transport=httpx.MockTransport(lambda r: httpx.Response(403, json={}))) as c, pytest.raises(
        PrivateRepoError
    ):
        c.repo("secret", "repo")


def test_branch_lookup_existing(tree):
    with GitHubClient(transport=make_transport(tree)) as c:
        assert c.branch("octo", "hello", "main") == "abc123"


def test_branch_lookup_slashed_name(tree):
    with GitHubClient(transport=make_transport(tree)) as c:
        assert c.branch("octo", "hello", "feature/x") == "xyz789"


def test_branch_lookup_missing_returns_none(tree):
    with GitHubClient(transport=make_transport(tree)) as c:
        assert c.branch("octo", "hello", "nope") is None


def test_flatten_full_recursive(tree):
    with GitHubClient(transport=make_transport(tree)) as c:
        blobs = c.flatten("octo", "hello", "abc123")
    assert {b["path"] for b in blobs} == {
        "README.md",
        "src/main.py",
        "src/utils.py",
        "docs/guide.md",
    }


def test_flatten_subtree(tree):
    with GitHubClient(transport=make_transport(tree)) as c:
        blobs = c.flatten("octo", "hello", "sha-src")
    assert {b["path"] for b in blobs} == {"main.py", "utils.py"}


def test_flatten_truncated_recurse_into_subtrees():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("recursive") == "1" and request.url.path.endswith("big"):
            return httpx.Response(
                200,
                json={
                    "sha": "big",
                    "truncated": True,
                    "tree": [
                        {"path": "sub", "mode": "040000", "type": "tree", "sha": "sub1"},
                        {
                            "path": "sub/inner.txt",
                            "mode": "100644",
                            "type": "blob",
                            "sha": "s1",
                            "size": 1,
                        },
                    ],
                },
            )
        if request.url.path.endswith("sub1"):
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {
                            "path": "inner.txt",
                            "mode": "100644",
                            "type": "blob",
                            "sha": "s1",
                            "size": 1,
                        },
                        {
                            "path": "other.txt",
                            "mode": "100644",
                            "type": "blob",
                            "sha": "s2",
                            "size": 2,
                        },
                    ],
                    "truncated": False,
                },
            )
        return httpx.Response(404, json={})

    with GitHubClient(transport=httpx.MockTransport(handler)) as c:
        blobs = c.flatten("o", "r", "big")
    assert {b["path"] for b in blobs} == {"sub/inner.txt", "sub/other.txt"}