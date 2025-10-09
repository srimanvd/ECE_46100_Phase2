import json
import os
from unittest.mock import patch
from src.metrics.license import metric, _extract_json_from_assistant


FAKE_RESPONSE_BODY = {
    "choices": [
        {"message": {"content": '{"license_spdx":"MIT","category":"permissive","compatibility_score":0.95,"compatibility_with_commercial_use":true,"explanation":"MIT is permissive."}'}}
    ]
}


class FakeResp:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}
    def json(self):
        return self._body
    @property
    def text(self):
        return json.dumps(self._body)


@patch("src.metrics.license.requests.post")
def test_llm_success(mock_post, tmp_path):
    """LLM returns valid JSON → metric uses LLM result."""
    p = tmp_path / "LICENSE"
    p.write_text("MIT License", encoding="utf-8")

    mock_post.return_value = FakeResp(status_code=200, body=FAKE_RESPONSE_BODY)
    os.environ["GEN_AI_STUDIO_API_KEY"] = "fake-key"

    score, _ = metric({"local_dir": str(tmp_path)})
    assert 0.9 <= score <= 1.0


@patch("src.metrics.license.requests.post")
def test_llm_invalid_json_fallback(mock_post, tmp_path):
    """LLM returns invalid JSON → fallback to heuristic."""
    p = tmp_path / "LICENSE"
    p.write_text("Apache License", encoding="utf-8")

    mock_post.return_value = FakeResp(status_code=200, body={"choices": [{"message": {"content": "not json"}}]})
    os.environ["GEN_AI_STUDIO_API_KEY"] = "fake-key"

    score, _ = metric({"local_dir": str(tmp_path)})
    assert abs(score - 0.95) < 1e-6  # Apache heuristic


@patch("src.metrics.license.requests.post")
def test_llm_api_error(mock_post, tmp_path):
    """LLM returns non-200 → heuristic fallback."""
    p = tmp_path / "LICENSE"
    p.write_text("GPL License text", encoding="utf-8")

    mock_post.return_value = FakeResp(status_code=500, body={"error": "fail"})
    os.environ["GEN_AI_STUDIO_API_KEY"] = "fake-key"

    score, _ = metric({"local_dir": str(tmp_path)})
    assert abs(score - 0.4) < 1e-6  # GPL heuristic


def test_extract_json_variants():
    """Covers _extract_json_from_assistant helper."""
    valid = '{"compatibility_score":0.7}'
    fenced = "```json\n{\"compatibility_score\": 0.8}\n```"
    single_quotes = "{'compatibility_score': 0.6}"
    garbage = "no json here"

    assert _extract_json_from_assistant(valid)["compatibility_score"] == 0.7
    assert _extract_json_from_assistant(fenced)["compatibility_score"] == 0.8
    assert _extract_json_from_assistant(single_quotes)["compatibility_score"] == 0.6
    assert _extract_json_from_assistant(garbage) is None
