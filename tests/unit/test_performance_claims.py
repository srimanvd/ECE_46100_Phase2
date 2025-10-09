# tests/unit/test_performance_claims.py

from src.metrics.performance_claims import metric
from huggingface_hub.utils import HfHubHTTPError
import pytest


class FakeModelInfo:
    def __init__(self, downloads):
        self.downloads = downloads


def test_performance_claims_high_downloads(mocker):
    """Models with >1M downloads should return 1.0 score."""
    mocker.patch('src.metrics.performance_claims.model_info',
                 return_value=FakeModelInfo(5_000_000))
    score, latency = metric({"name": "google/gemma-2b"})
    assert score == 1.0
    assert latency >= 0


def test_performance_claims_api_error(mocker):
    """If HuggingFace API raises HfHubHTTPError, score must be 0.0."""
    mocker.patch('src.metrics.performance_claims.model_info',
                 side_effect=HfHubHTTPError("Not Found"))
    score, latency = metric({"name": "not/a-real-model"})
    assert score == 0.0
    assert latency >= 0


@pytest.mark.parametrize("downloads,expected", [
    (0, 0.1),       # very low
    (150, 0.2),     # >100
    (1500, 0.4),    # >1000
    (15000, 0.6),   # >10000
    (150000, 0.8),  # >100000
])
def test_performance_claims_download_tiers(mocker, downloads, expected):
    """Covers all branches of the tiered scoring logic."""
    mocker.patch('src.metrics.performance_claims.model_info',
                 return_value=FakeModelInfo(downloads))
    score, latency = metric({"name": "some/model"})
    assert score == expected
    assert latency >= 0


def test_performance_claims_missing_name():
    """If resource lacks 'name', function should return score=0.0."""
    score, latency = metric({})
    assert score == 0.0
    assert latency >= 0


def test_performance_claims_generic_exception(mocker):
    """If model_info raises a generic Exception, catch-all should return 0.0."""
    mocker.patch('src.metrics.performance_claims.model_info',
                 side_effect=RuntimeError("Network down"))
    score, latency = metric({"name": "any/model"})
    assert score == 0.0
    assert latency >= 0
