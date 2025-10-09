# tests/unit/test_ramp_up_time_local.py
from pathlib import Path
from src.metrics.ramp_up_time import metric

def write_readme(tmp_path: Path, text: str) -> str:
    p = tmp_path / "README.md"
    p.write_text(text, encoding="utf-8")
    return str(tmp_path)

def test_empty_readme(tmp_path):
    d = write_readme(tmp_path, "")
    score, lat = metric({"local_dir": d})
    assert score == 0.0
    assert isinstance(lat, int) and lat >= 0

def test_length_only(tmp_path):
    text = "word " * 250
    d = write_readme(tmp_path, text)
    score, _ = metric({"local_dir": d})
    assert 0.24 <= score <= 0.26
