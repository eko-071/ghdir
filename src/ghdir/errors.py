"""Typed errors raised by ghdir, mapped to clean CLI messages."""


class GhdirError(Exception):
    """Base class for all ghdir errors."""


class RepoNotFoundError(GhdirError):
    """The repository does not exist (or the token cannot see it)."""


class PathNotFoundError(GhdirError):
    """The requested path does not exist in the tree."""


class PrivateRepoError(GhdirError):
    """The repository is private and the current credentials cannot access it."""


class BranchNotFoundError(GhdirError):
    """The requested branch does not exist in the repository."""