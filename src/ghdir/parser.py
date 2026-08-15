"""GitHub URL parsing: `github.com/{owner}/{repo}[/tree/{branch}/{path}]`."""

import re

from ghdir.errors import GhdirError
from ghdir.models import RepoRef

_TREE_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?"
    r"(?:/tree/(?P<tail>.*))?$"
)


def parse_github_url(url: str) -> RepoRef:
    m = _TREE_URL_RE.match(url.strip().rstrip("/"))
    if not m:
        raise GhdirError(f"not a valid GitHub repository URL: {url!r}")
    tail = tuple(p for p in m["tail"].split("/") if p) if m["tail"] else ()
    return RepoRef(m["owner"], m["repo"], tail)