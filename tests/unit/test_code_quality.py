from src.metrics.code_quality import metric

def test_code_quality_perfect_score(tmp_path):
    """Test a repo that has all the quality indicator files."""
    # tmp_path is a pytest feature that creates a temporary directory for the test
    (tmp_path / "requirements.txt").touch() # Creates an empty file
    (tmp_path / "tests").mkdir()             # Creates a directory
    (tmp_path / ".github").mkdir()
    (tmp_path / "Dockerfile").touch()

    # Pass the path of this fake repo to the metric
    resource = {"local_path": str(tmp_path)}
    score, latency = metric(resource)

    # With all 4 items, the score should be 1.0
    assert score == 1.0

def test_code_quality_zero_score(tmp_path):
    """Test an empty repo with no quality indicators."""
    resource = {"local_path": str(tmp_path)}
    score, latency = metric(resource)

    # With none of the items, the score should be 0.0
    assert score == 0.0

def test_code_quality_half_score(tmp_path):
    """Test a repo with two of the four indicators."""
    (tmp_path / "requirements.txt").touch()
    (tmp_path / "tests").mkdir()

    resource = {"local_path": str(tmp_path)}
    score, latency = metric(resource)

    # With 2 of 4 items, the score should be 0.5
    assert score == 0.5