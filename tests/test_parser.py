import pytest

from ghdir.errors import GhdirError
from ghdir.parser import parse_github_url


def test_repo_root():
    ref = parse_github_url("https://github.com/octo/hello")
    assert (ref.owner, ref.repo, ref.tail) == ("octo", "hello", ())
    assert ref.branch is None
    assert ref.path == ""


def test_branch_only():
    ref = parse_github_url("https://github.com/octo/hello/tree/main")
    assert ref.tail == ("main",)
    assert ref.branch == "main"
    assert ref.path == ""


def test_branch_and_path():
    ref = parse_github_url("https://github.com/octo/hello/tree/main/Embodied/src")
    assert ref.tail == ("main", "Embodied", "src")
    assert ref.path == "Embodied/src"


def test_scheme_variants():
    assert parse_github_url("github.com/octo/hello").repo == "hello"
    assert parse_github_url("http://www.github.com/octo/hello/tree/dev").branch == "dev"


def test_trailing_slash_ignored():
    ref = parse_github_url("https://github.com/octo/hello/tree/main/src/")
    assert ref.tail == ("main", "src")


def test_git_suffix_stripped():
    assert parse_github_url("https://github.com/octo/hello.git").repo == "hello"


def test_branch_with_slash_kept_as_tail():
    ref = parse_github_url("https://github.com/octo/hello/tree/feature/x/docs")
    assert ref.tail == ("feature", "x", "docs")
    assert ref.branch == "feature"  # best guess; resolver disambiguates against real refs
    assert ref.path == "x/docs"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/octo/hello",
        "git@github.com:octo/hello.git",
        "not a url",
        "",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(GhdirError):
        parse_github_url(url)