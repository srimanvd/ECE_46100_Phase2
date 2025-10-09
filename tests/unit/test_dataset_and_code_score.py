# tests/unit/test_dataset_and_code_score.py
from src.metrics.dataset_and_code_score import metric

def test_both_links_found(mocker):
    """Test that the score is 1.0 when both dataset and code links are found."""
    mocker.patch(
        'src.metrics.dataset_and_code_score.find_datasets_from_resource',
        return_value=(["some_dataset_url"], 5),
    )
    mocker.patch(
        'src.metrics.dataset_and_code_score.find_github_url_from_hf',
        return_value="some_github_url",
    )

    resource = {"url": "https://huggingface.co/some/model", "name": "some/model"}
    score, latency = metric(resource)
    assert score == 1.0

def test_only_one_link_found(mocker):
    """Test that the score is 0.5 when only one of the two links is found."""
    mocker.patch(
        'src.metrics.dataset_and_code_score.find_datasets_from_resource',
        return_value=(["some_dataset_url"], 5),
    )
    mocker.patch(
        'src.metrics.dataset_and_code_score.find_github_url_from_hf',
        return_value=None,
    )  # No GitHub link

    resource = {"url": "https://huggingface.co/some/model", "name": "some/model"}
    score, latency = metric(resource)
    assert score == 0.5

def test_no_links_found(mocker):
    """Test that the score is 0.0 when no links are found."""
    mocker.patch(
        'src.metrics.dataset_and_code_score.find_datasets_from_resource',
        return_value=([], 5),
    )
    mocker.patch(
        'src.metrics.dataset_and_code_score.find_github_url_from_hf',
        return_value=None,
    )

    resource = {"url": "https://huggingface.co/some/model", "name": "some/model"}
    score, latency = metric(resource)
    assert score == 0.0
