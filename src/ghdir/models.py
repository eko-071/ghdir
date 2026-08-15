"""Core dataclasses shared across modules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RepoRef:
    """A parsed GitHub repository URL.

    `tail` holds the raw segments after `/tree/`. The branch can contain
    slashes (e.g. `feature/x`), so which segments form the branch vs the path
    is resolved against the repo's actual refs in `resolver.py`.
    """

    owner: str
    repo: str
    tail: tuple[str, ...] = ()

    @property
    def branch(self) -> str | None:
        return self.tail[0] if self.tail else None

    @property
    def path(self) -> str:
        return "/".join(self.tail[1:])


@dataclass(frozen=True)
class FileEntry:
    """A single file to download, with its path relative to the output dir."""

    path: str
    size: int
    sha: str
    download_url: str


@dataclass(frozen=True)
class ResolvedRepo:
    """The outcome of resolving a RepoRef against the GitHub API."""

    owner: str
    repo: str
    branch: str
    path: str
    files: tuple[FileEntry, ...]

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def default_output_dir(self) -> str:
        return self.path.rstrip("/").split("/")[-1] or self.repo