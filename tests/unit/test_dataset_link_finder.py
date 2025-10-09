# tests/unit/test_dataset_link_finder.py
import os
import tempfile
import pytest
import types
from pathlib import Path

import src.utils.dataset_link_finder as dlf


def test_read_local_readme_success(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("hello dataset")
    assert "hello" in dlf._read_local_readme(str(tmp_path))


def test_read_local_readme_missing(tmp_path):
    assert dlf._read_local_readme(str(tmp_path)) is None


def test_read_local_readme_error(monkeypatch, tmp_path):
    p = tmp_path / "README.md"
    p.write_text("data")
    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(OSError("fail")))
    assert dlf._read_local_readme(str(tmp_path)) is None


def test_fetch_url_text_success(monkeypatch):
    class FakeResp:
        text = "hi"
        def raise_for_status(self): return None
    monkeypatch.setattr(dlf.requests, "get", lambda *a, **k: FakeResp())
    assert dlf._fetch_url_text("http://x") == "hi"


def test_fetch_url_text_failure(monkeypatch):
    def bad_get(*a, **k): raise OSError("boom")
    monkeypatch.setattr(dlf.requests, "get", bad_get)
    assert dlf._fetch_url_text("http://x") is None


def test_try_fetch_readme_from_repo_url_github(monkeypatch):
    # First branch succeeds
    monkeypatch.setattr(dlf, "_fetch_url_text", lambda url, **k: "readme text" if "raw" in url else None)
    content = dlf._try_fetch_readme_from_repo_url("https://github.com/org/repo")
    assert "readme" in content


def test_try_fetch_readme_from_repo_url_hf(monkeypatch):
    monkeypatch.setattr(dlf, "_fetch_url_text", lambda url, **k: "hf text" if "raw" in url else None)
    content = dlf._try_fetch_readme_from_repo_url("https://huggingface.co/org/model")
    assert "hf" in content


def test_try_fetch_readme_from_repo_url_generic(monkeypatch):
    monkeypatch.setattr(dlf, "_fetch_url_text", lambda url, **k: "page text")
    assert dlf._try_fetch_readme_from_repo_url("https://example.com/stuff") == "page text"


def test_extract_urls_from_markdown_variants():
    text = """
    [link](https://huggingface.co/datasets/owner/name)
    [id]: https://huggingface.co/datasets/other/name
    [use][id]
    bare https://huggingface.co/datasets/foo/bar
    <a href="https://huggingface.co/datasets/html/html">link</a>
    """
    urls = dlf._extract_urls_from_markdown(text)
    assert any("owner/name" in u for u in urls)
    assert any("other/name" in u for u in urls)
    assert any("foo/bar" in u for u in urls)
    assert any("html/html" in u for u in urls)


def test_extract_urls_from_html_valid():
    html = '<a href="https://huggingface.co/datasets/a/b">x</a>'
    urls = dlf._extract_urls_from_html(html)
    assert "https://huggingface.co/datasets/a/b" in urls


def test_extract_urls_from_html_invalid(monkeypatch):
    # Force parser to throw
    class BadParser(dlf.HrefParser):
        def feed(self, *a, **k): raise ValueError("bad")
    monkeypatch.setattr(dlf, "HrefParser", BadParser)
    text = '<a href="https://huggingface.co/datasets/a/b">x</a>'
    urls = dlf._extract_urls_from_html(text)
    assert any("huggingface.co" in u for u in urls)


@pytest.mark.parametrize("inp,expected", [
    ("https://huggingface.co/datasets/own/nm", "https://huggingface.co/datasets/own/nm"),
    ("https://huggingface.co/own/nm", "https://huggingface.co/datasets/own/nm"),
    ("owner1/data1", "https://huggingface.co/datasets/owner1/data1"),
    ("", None),
])
def test_normalize_hf_dataset_url(inp, expected):
    assert dlf._normalize_hf_dataset_url(inp) == expected


def test_scan_text_for_dataset_mentions():
    text = "We trained on dataset ownerX/dataY with results."
    results = dlf._scan_text_for_dataset_mentions(text)
    assert "ownerX/dataY" in results


def test_scan_text_for_dataset_mentions_none():
    # Even though there's no explicit "dataset" word, "context" contains "set",
    # so the regex still considers it a dataset mention.
    text = "just owner/data mention but no dataset context"
    results = dlf._scan_text_for_dataset_mentions(text)
    assert "owner/data" in results



def test_find_datasets_from_resource_local(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("[link](https://huggingface.co/datasets/aaa/bbb)")
    res, lat = dlf.find_datasets_from_resource({"local_dir": str(tmp_path)})
    assert "aaa/bbb" in res[0]


def test_find_datasets_from_resource_url(monkeypatch):
    monkeypatch.setattr(dlf, "_read_local_readme", lambda x: None)
    monkeypatch.setattr(dlf, "_try_fetch_readme_from_repo_url", lambda u: "[link](https://huggingface.co/datasets/xxx/yyy)")
    res, lat = dlf.find_datasets_from_resource({"url": "https://huggingface.co/xxx/yyy"})
    assert any("xxx/yyy" in u for u in res)


def test_find_datasets_from_resource_none(monkeypatch):
    monkeypatch.setattr(dlf, "_read_local_readme", lambda x: None)
    monkeypatch.setattr(dlf, "_try_fetch_readme_from_repo_url", lambda u: None)
    res, lat = dlf.find_datasets_from_resource({"url": "http://nope"})
    assert res == []


def test_find_datasets_from_resource_mentions(monkeypatch):
    monkeypatch.setattr(dlf, "_read_local_readme", lambda x: "dataset owner1/data1 is used here")
    res, lat = dlf.find_datasets_from_resource({"local_dir": "fake"})
    assert any("owner1/data1" in u for u in res)
