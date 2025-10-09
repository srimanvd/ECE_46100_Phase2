import logging
import pytest
from src.utils.github_link_finder import find_github_url_from_hf


def test_find_github_link_success(mocker):
    """Test that the function correctly finds a GitHub link in a fake README."""
    fake_readme_content = '<a href="https://github.com/some-org/some-repo">GitHub</a>'
    mocker.patch('src.utils.github_link_finder.hf_hub_download', return_value='fake_readme.md')
    mocker.patch('builtins.open', mocker.mock_open(read_data=fake_readme_content))

    repo_id = "some-hf-model/some-model"
    found_url = find_github_url_from_hf(repo_id)

    assert found_url == "https://github.com/some-org/some-repo"


def test_find_github_link_api_failure(mocker):
    """Test that the link finder returns None if hf_hub_download fails."""
    mocker.patch('src.utils.github_link_finder.hf_hub_download', side_effect=Exception("API Error"))
    found_url = find_github_url_from_hf("some/model")
    assert found_url is None


def test_no_github_link_found(mocker, caplog):
    """Test that None is returned when no GitHub link is present."""
    fake_readme_content = "This is our model. No links here."
    mocker.patch('src.utils.github_link_finder.hf_hub_download', return_value='fake_readme.md')
    mocker.patch('builtins.open', mocker.mock_open(read_data=fake_readme_content))

    with caplog.at_level(logging.WARNING):
        found_url = find_github_url_from_hf("some-hf-model/some-model")
        assert found_url is None
        assert "No GitHub link found" in caplog.text


def test_multiple_links_picks_first(mocker):
    """Test that the first valid GitHub link is chosen when multiple are present."""
    fake_content = """
    <a href="https://example.com/some">Other</a>
    <a href="https://github.com/first/repo">First</a>
    <a href="https://github.com/second/repo">Second</a>
    """
    mocker.patch('src.utils.github_link_finder.hf_hub_download', return_value='fake.md')
    mocker.patch('builtins.open', mocker.mock_open(read_data=fake_content))

    url = find_github_url_from_hf("id")
    assert url == "https://github.com/first/repo"


def test_empty_readme_file(mocker):
    """Test that an empty README still safely returns None."""
    mocker.patch('src.utils.github_link_finder.hf_hub_download', return_value='fake.md')
    mocker.patch('builtins.open', mocker.mock_open(read_data=""))

    url = find_github_url_from_hf("id")
    assert url is None


def test_invalid_html_parsing(mocker):
    """Test that invalid HTML does not crash parsing."""
    fake_content = "<<<>>>>"  # not valid HTML
    mocker.patch('src.utils.github_link_finder.hf_hub_download', return_value='fake.md')
    mocker.patch('builtins.open', mocker.mock_open(read_data=fake_content))

    url = find_github_url_from_hf("id")
    assert url is None
