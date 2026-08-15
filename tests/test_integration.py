"""End-to-end test against the live GitHub API. Run with `pytest -m integration`."""

from pathlib import Path

import pytest

from ghdir.downloader import download_all
from ghdir.github import GitHubClient
from ghdir.parser import parse_github_url
from ghdir.resolver import resolve


@pytest.mark.integration
def test_download_nvlab_eagle_embodied(tmp_path):
    ref = parse_github_url("https://github.com/NVlabs/Eagle/tree/main/Embodied")
    with GitHubClient() as client:
        resolved = resolve(client, ref)
        assert resolved.files, "no files resolved"
        written = download_all(resolved.files, str(tmp_path), client.http)
    assert len(written) == len(resolved.files)
    assert all(Path(p).is_file() for p in written)