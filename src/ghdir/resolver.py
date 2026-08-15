"""Turn a RepoRef into a concrete list of files to download."""

from __future__ import annotations

from ghdir.errors import BranchNotFoundError, PathNotFoundError
from ghdir.github import GitHubClient
from ghdir.models import FileEntry, RepoRef, ResolvedRepo

RAW_BASE = "https://raw.githubusercontent.com"


def resolve(
    client: GitHubClient, ref: RepoRef, branch_override: str | None = None
) -> ResolvedRepo:
    info = client.repo(ref.owner, ref.repo)
    branch, branch_sha, path = _pick_branch(
        client, ref.owner, ref.repo, ref.tail, info["default_branch"]
    )

    if branch_override:
        override_sha = client.branch(ref.owner, ref.repo, branch_override)
        if override_sha is None:
            raise BranchNotFoundError(f"branch {branch_override!r} not found")
        branch, branch_sha = branch_override, override_sha

    if path:
        subtree = _find_dir(client, ref.owner, ref.repo, branch_sha, path)
        if subtree is None:
            raise PathNotFoundError(f"{path!r} not found in {ref.owner}/{ref.repo}")
        blob_sha = subtree
    else:
        blob_sha = branch_sha

    blobs = client.flatten(ref.owner, ref.repo, blob_sha)
    files = tuple(
        FileEntry(
            path=b["path"],
            size=b["size"],
            sha=b["sha"],
            download_url=_raw_url(ref.owner, ref.repo, branch, path, b["path"]),
        )
        for b in blobs
    )
    return ResolvedRepo(ref.owner, ref.repo, branch, path, files)


def _pick_branch(
    client: GitHubClient,
    owner: str,
    repo: str,
    tail: tuple[str, ...],
    default_branch: str,
) -> tuple[str, str, str]:
    """Try the longest tail prefix that is a real branch, via direct API lookup.

    Longest-prefix-first so `feature/x` is checked before `feature` when both
    happen to exist. Returns (branch, sha, path) where path is the tail left
    over after the branch.
    """
    if not tail:
        sha = client.branch(owner, repo, default_branch)
        if sha is None:
            raise BranchNotFoundError(f"branch {default_branch!r} not found")
        return default_branch, sha, ""
    for i in range(len(tail), 0, -1):
        candidate = "/".join(tail[:i])
        sha = client.branch(owner, repo, candidate)
        if sha is not None:
            return candidate, sha, "/".join(tail[i:])
    raise BranchNotFoundError(f"branch {'/'.join(tail)!r} not found")


def _find_dir(
    client: GitHubClient, owner: str, repo: str, start_sha: str, path: str
) -> str | None:
    """Walk down `path` with non-recursive tree lookups; return the subtree sha."""
    current = start_sha
    for component in path.split("/"):
        entries = client.tree_entries(owner, repo, current)
        match = next((e for e in entries if e["path"] == component), None)
        if match is None or match["type"] != "tree":
            return None
        current = match["sha"]
    return current


def _raw_url(owner: str, repo: str, branch: str, path: str, rel: str) -> str:
    root = f"{RAW_BASE}/{owner}/{repo}/{branch}"
    return f"{root}/{path}/{rel}" if path else f"{root}/{rel}"