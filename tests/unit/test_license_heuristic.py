from pathlib import Path
from src.metrics.license import metric, heuristic_license_score


def test_heuristic_mit(tmp_path: Path):
    p = tmp_path / "LICENSE"
    p.write_text("MIT License", encoding="utf-8")
    score, _ = metric({"local_dir": str(tmp_path)})
    assert score == 1.0


def test_heuristic_bsd(tmp_path: Path):
    p = tmp_path / "LICENSE"
    p.write_text("BSD 3-Clause", encoding="utf-8")
    score, _ = metric({"local_dir": str(tmp_path)})
    assert score == 0.9


def test_heuristic_lgpl(tmp_path: Path):
    p = tmp_path / "LICENSE"
    p.write_text("GNU LGPL", encoding="utf-8")
    score, _ = metric({"local_dir": str(tmp_path)})
    assert score == 0.6


def test_heuristic_proprietary_keywords(tmp_path: Path):
    p = tmp_path / "LICENSE"
    p.write_text("All Rights Reserved 2024", encoding="utf-8")
    score, _ = metric({"local_dir": str(tmp_path)})
    assert score == 0.0


def test_heuristic_unknown(tmp_path: Path):
    p = tmp_path / "LICENSE"
    p.write_text("Some random license text", encoding="utf-8")
    score, _ = metric({"local_dir": str(tmp_path)})
    assert score == 0.0


def test_no_license_file(tmp_path: Path):
    """No LICENSE file → returns float and latency (0.0, latency)."""
    score, lat = metric({"local_dir": str(tmp_path)})
    assert score == 0.0
    assert isinstance(lat, int)


def test_heuristic_direct_function():
    """Direct call to heuristic_license_score helper."""
    score, label, method = heuristic_license_score("Apache License 2.0")
    assert score == 0.95
    assert label == "Apache-2.0"
    assert method == "heuristic"
