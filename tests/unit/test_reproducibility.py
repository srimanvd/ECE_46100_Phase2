from unittest.mock import MagicMock, patch

from src.metrics.reproducibility import (
    _find_demo_script,
    compute_reproducibility,
    compute_reproducibility_from_label,
    compute_reproducibility_via_demo,
    score_from_label,
)


def test_score_from_label():
    assert score_from_label("none") == 0.0
    assert score_from_label("agent") == 0.5
    assert score_from_label("native") == 1.0
    assert score_from_label("unknown") == -1.0

def test_compute_reproducibility_from_label():
    res = compute_reproducibility_from_label("agent")
    assert res.score == 0.5
    assert res.label == "agent"
    assert "agent" in res.reason

def test_find_demo_script(tmp_path):
    # No script
    assert _find_demo_script(tmp_path) is None
    
    # Create script
    (tmp_path / "demo.py").touch()
    assert _find_demo_script(tmp_path) == tmp_path / "demo.py"
    
    # Priority check (inference.py > demo.py)
    (tmp_path / "inference.py").touch()
    assert _find_demo_script(tmp_path) == tmp_path / "inference.py"

def test_compute_reproducibility_via_demo_no_script(tmp_path):
    res = compute_reproducibility_via_demo(tmp_path)
    assert res.score == 0.0
    assert res.label == "none"
    assert "No demo script found" in res.reason

@patch("subprocess.run")
def test_compute_reproducibility_via_demo_success(mock_run, tmp_path):
    (tmp_path / "demo.py").touch()
    mock_run.return_value = MagicMock(returncode=0)
    
    res = compute_reproducibility_via_demo(tmp_path)
    assert res.score == 1.0
    assert res.label == "native"
    mock_run.assert_called_once()

@patch("subprocess.run")
def test_compute_reproducibility_via_demo_failure(mock_run, tmp_path):
    (tmp_path / "demo.py").touch()
    mock_run.return_value = MagicMock(returncode=1)
    
    res = compute_reproducibility_via_demo(tmp_path)
    assert res.score == 0.0
    assert res.label == "none"
    assert "exited with code 1" in res.reason

@patch("subprocess.run")
def test_compute_reproducibility_via_demo_timeout(mock_run, tmp_path):
    import subprocess
    (tmp_path / "demo.py").touch()
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="cmd", timeout=1)
    
    res = compute_reproducibility_via_demo(tmp_path)
    assert res.score == 0.0
    assert res.label == "none"
    assert "timed out" in res.reason

def test_compute_reproducibility_main_api():
    # Manual label
    res = compute_reproducibility("path", manual_label="agent")
    assert res.score == 0.5
    
    # Auto (mocked via demo)
    with patch("src.metrics.reproducibility.compute_reproducibility_via_demo") as mock_demo:
        mock_demo.return_value = MagicMock(score=1.0)
        res = compute_reproducibility("path")
        assert res.score == 1.0
