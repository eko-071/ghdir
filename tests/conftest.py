"""Shared fixtures: a recorded GitHub API response and an httpx mock transport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from ghdir.github import GitHubClient

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str = "sample_tree.json") -> dict:
    return json.loads((FIXTURES / name).read_text())


def make_transport(tree: dict) -> httpx.MockTransport:
    """Mock transport serving the sample tree: repo info, branches, trees, raw files."""
    owner, repo = tree["repo"].split("/")
    branches = tree["branches"]
    default_branch = tree["default_branch"]

    def resolve_sha(value: str) -> str:
        return branches.get(value, value)

    def recursive(sha: str) -> list[dict]:
        out = []
        for e in tree["trees"][sha]:
            out.append(e)
            if e["type"] == "tree":
                for sub in recursive(e["sha"]):
                    out.append({**sub, "path": f'{e["path"]}/{sub["path"]}'})
        return out

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "raw.githubusercontent.com":
            return httpx.Response(200, content=b"content " + request.url.path.encode())
        path = request.url.path
        if path == f"/repos/{owner}/{repo}":
            return httpx.Response(
                200, json={"full_name": tree["repo"], "default_branch": default_branch}
            )
        if path == f"/repos/{owner}/{repo}/branches":
            return httpx.Response(
                200, json=[{"name": b, "commit": {"sha": branches[b]}} for b in tree["refs"]]
            )
        prefix = f"/repos/{owner}/{repo}/git/trees/"
        if path.startswith(prefix):
            sha = path[len(prefix):].split("?")[0]
            base = resolve_sha(sha)
            if base not in tree["trees"]:
                return httpx.Response(404, json={"message": "Not Found"})
            if request.url.params.get("recursive") == "1":
                return httpx.Response(
                    200, json={"sha": sha, "tree": recursive(base), "truncated": False}
                )
            return httpx.Response(
                200, json={"sha": sha, "tree": tree["trees"][base], "truncated": False}
            )
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


@pytest.fixture
def tree() -> dict:
    return load_fixture()


@pytest.fixture
def client(tree) -> GitHubClient:
    with GitHubClient(transport=make_transport(tree)) as c:
        yield c