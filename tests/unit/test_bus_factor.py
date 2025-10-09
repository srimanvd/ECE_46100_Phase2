import pytest
from src.metrics.bus_factor import compute_bus_factor


def test_single_contributor_low_score():
    """
    A repository with commits from only one person
    should have a bus factor score of 0.0.
    """
    commit_history = ["alice"] * 10  # All commits from Alice
    score, latency = compute_bus_factor(commit_history)

    assert score == 0.0
    assert isinstance(latency, int)
    assert latency >= 0


def test_multiple_contributors_equal_work():
    """
    A repository with evenly distributed commits
    should have a bus factor score close to 1.0.
    """
    commit_history = ["alice", "bob", "carol", "dave"] * 5
    score, latency = compute_bus_factor(commit_history)

    # Should be very close to 1.0
    assert pytest.approx(score, rel=1e-3) == 1.0
    assert isinstance(latency, int)
    assert latency >= 0


def test_skewed_contributions_intermediate_score():
    """
    A repository where one contributor dominates the commits
    should have a bus factor between 0.0 and 1.0.
    """
    commit_history = ["alice"] * 90 + ["bob"] * 10  # Alice 90%, Bob 10%
    score, latency = compute_bus_factor(commit_history)

    assert 0.0 < score < 1.0
    assert isinstance(latency, int)
    assert latency >= 0