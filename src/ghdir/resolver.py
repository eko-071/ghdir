"""Turn a RepoRef into a concrete list of files to download."""

from __future__ import annotations

from ghdir.errors import BranchNotFoundError, PathNotFoundError
from ghdir.github import GitHubClient
from ghdir.models import FileEntry, RepoRef, ResolvedRepo

RAW_BASE = "https://raw.githubusercontent.com"


def resolve(client: GitHubClient, ref: RepoRef) -> ResolvedRepo:
    info = client.repo(ref.owner, ref.repo)
    branches = client.branches(ref.owner, ref.repo)
    branch, branch_sha, path = _pick_branch(ref.tail, branches, info["default_branch"])

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
    tail: tuple[str, ...], branches: dict[str, str], default_branch: str
) -> tuple[str, str, str]:
    """Branches can contain slashes; try the longest tail prefix that is a real branch.

    Returns (branch, sha, path) where path is the tail remaining after the branch.
    """
    if not tail:
        return default_branch, branches.get(default_branch, default_branch), ""
    for i in range(len(tail), 0, -1):
        candidate = "/".join(tail[:i])
        if candidate in branches:
            return candidate, branches[candidate], "/".join(tail[len(candidate.split("/")):])
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