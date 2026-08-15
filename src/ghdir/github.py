"""Thin httpx wrapper around the GitHub REST API."""

from __future__ import annotations

from typing import Self
from urllib.parse import quote

import httpx

from ghdir.errors import GhdirError, PrivateRepoError, RepoNotFoundError

BASE = "https://api.github.com"


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.http = httpx.Client(headers=headers, timeout=30, transport=transport)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self.http.close()

    def repo(self, owner: str, repo: str) -> dict:
        return self._get(f"/repos/{owner}/{repo}", f"repository {owner}/{repo}")

    def branch(self, owner: str, repo: str, name: str) -> str | None:
        """Return the branch's head commit SHA, or None if it doesn't exist.

        Direct single lookup; works on repos with any number of branches and
        with slash-containing branch names (percent-encoded as one path segment).
        """
        url = f"/repos/{owner}/{repo}/branches/{quote(name, safe='')}"
        resp = self.http.get(BASE + url)
        if resp.status_code == 404:
            return None
        if resp.status_code == 403:
            raise PrivateRepoError(f"access denied to {owner}/{repo} (private repo or rate limit)")
        if resp.status_code != 200:
            raise GhdirError(f"GitHub API error {resp.status_code} for branch {name!r}")
        return resp.json()["commit"]["sha"]

    def tree_entries(self, owner: str, repo: str, sha: str) -> list[dict]:
        data = self._get(
            f"/repos/{owner}/{repo}/git/trees/{sha}",
            f"tree {sha} of {owner}/{repo}",
        )
        return data["tree"]

    def flatten(self, owner: str, repo: str, sha: str, prefix: str = "") -> list[dict]:
        """All blob entries under `sha`, as {path, size, sha} with full relative paths.

        Handles truncated recursive trees by re-flattening each top-level subtree.
        """
        data = self._get(
            f"/repos/{owner}/{repo}/git/trees/{sha}?recursive=1",
            f"tree {sha} of {owner}/{repo}",
        )
        entries, truncated = data["tree"], data.get("truncated", False)
        out: list[dict] = []
        if truncated:
            for e in entries:
                if "/" in e["path"]:  # partial nested entry, covered by recursion below
                    continue
                if e["type"] == "blob":
                    out.append(
                        {"path": prefix + e["path"], "size": e.get("size", 0), "sha": e["sha"]}
                    )
                elif e["type"] == "tree":
                    out.extend(self.flatten(owner, repo, e["sha"], prefix + e["path"] + "/"))
            return out
        for e in entries:
            if e["type"] == "blob":
                out.append({"path": prefix + e["path"], "size": e.get("size", 0), "sha": e["sha"]})
        return out

    def _get(self, url: str, what: str) -> dict:
        resp = self.http.get(BASE + url)
        if resp.status_code == 404:
            raise RepoNotFoundError(f"{what} not found")
        if resp.status_code == 403:
            raise PrivateRepoError(f"access denied to {what} (private repo or rate limit)")
        if resp.status_code != 200:
            raise GhdirError(f"GitHub API error {resp.status_code} for {what}")
        return resp.json()