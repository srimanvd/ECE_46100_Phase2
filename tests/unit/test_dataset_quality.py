# tests/unit/test_dataset_quality.py
from src.metrics.dataset_quality import metric

class FakeDatasetInfo:
    def __init__(self, cardData=None, downloads=0, likes=0):
        self.cardData = cardData
        self.downloads = downloads
        self.likes = likes

def test_dataset_quality_high_score(mocker):
    """Test a dataset with all quality indicators."""
    mocker.patch(
        'src.metrics.dataset_quality.find_datasets_from_resource',
        return_value=(["https://huggingface.co/datasets/squad"], 5),
    )
    mocker.patch(
        'src.metrics.dataset_quality.dataset_info',
        return_value=FakeDatasetInfo(
            cardData={"dataset_card": "some content"}, downloads=5000, likes=50
        ),
    )

    score, latency = metric({"name": "some/model"})
    assert score == 1.0  # 0.5 (card) + 0.3 (downloads) + 0.2 (likes)

def test_dataset_quality_no_link_found(mocker):
    """Test when no dataset link is found."""
    mocker.patch(
        'src.metrics.dataset_quality.find_datasets_from_resource',
        return_value=([], 5),
    )

    score, latency = metric({"name": "some/model"})
    assert score == 0.0
