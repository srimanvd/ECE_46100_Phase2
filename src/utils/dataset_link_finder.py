# src/dataset_link_finder.py
"""Robust dataset link finder for Hugging Face model cards / READMEs.

Functions:
- find_datasets_from_resource(resource: dict) -> list[str]
  Resource may contain:
    - 'local_dir': path to a cloned repo (preferred)
    - 'url': canonical model or repo URL (e.g. huggingface.co/google/bert-base-uncased or github.com/owner/repo)
  Returns a deduplicated list of normalized dataset references. Each item is either:
    - https://huggingface.co/datasets/{owner}/{name}
    - or owner/name (if found only as mention)
"""

from __future__ import annotations
import re
import os
import time
import logging
from typing import List, Tuple, Optional, Dict, Set
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin, quote_plus
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Regexes
INLINE_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(\s*(https?://[^\s\)]+)\s*\)', re.IGNORECASE)
REFERENCE_DEF_RE = re.compile(r'^\s*\[([^\]]+)\]:\s*(https?://\S+)', re.MULTILINE)
REFERENCE_USE_RE = re.compile(r'\[([^\]]+)\]\[([^\]]+)\]')  # [text][id]
URL_RE = re.compile(r'(https?://[^\s\)\]\>]+)')
OWNER_DATASET_RE = re.compile(r'\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b')  # bare owner/name token

HF_DATASETS_HOSTS = {'huggingface.co', 'www.huggingface.co', 'hf.co'}

COMMON_README_NAMES = ("README.md", "README.rst", "README.txt", "README")

HTML_LINK_RE = re.compile(r'href=[\'"]?([^\'" >]+)')

# Helper HTML parser to collect hrefs
class HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            for (k, v) in attrs:
                if k.lower() == 'href' and v:
                    self.hrefs.append(v)

def _read_local_readme(local_dir: str) -> Optional[str]:
    """Look for common README filenames in local_dir"""
    if not local_dir or not os.path.isdir(local_dir):
        return None
    for fname in COMMON_README_NAMES:
        path = os.path.join(local_dir, fname)
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                    return fh.read()
            except Exception as e:
                logger.debug("Could not read %s: %s", path, e)
    return None

def _fetch_url_text(url: str, timeout: float = 6.0) -> Optional[str]:
    """HTTP GET to fetch text content; returns None on failure."""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "dataset-link-finder/1.0"})
        r.raise_for_status()
        # Some HTML pages have scripts etc, but we only need link-extraction so raw text is OK.
        return r.text
    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url, e)
        return None

def _try_fetch_readme_from_repo_url(url: str) -> Optional[str]:
    """
    Given a GitHub or Hugging Face model page URL, try to construct a raw README URL.
    Handles common forms:
     - https://github.com/owner/repo -> raw.githubusercontent.com/owner/repo/main/README.md
     - https://github.com/owner/repo/tree/main/... -> similar
     - https://huggingface.co/{repo}/tree/main -> https://huggingface.co/{repo}/raw/main/README.md
     - HF raw patterns: https://huggingface.co/<repo>/raw/main/README.md
    """
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    parts = [p for p in path.split('/') if p]

    # GitHub handling
    if 'github.com' in host and len(parts) >= 2:
        owner, repo = parts[0], parts[1]
        # try main then master
        for branch in ('main', 'master'):
            raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
            content = _fetch_url_text(raw)
            if content:
                return content
        # fall back to repo page HTML (may contain README in page)
        content = _fetch_url_text(url)
        return content

    # Hugging Face handling
    if host in HF_DATASETS_HOSTS or host.endswith('huggingface.co'):
        # path might be like /google/bert-base-uncased or /google/bert-base-uncased/tree/main
        repo_path = "/".join(parts[:2]) if len(parts) >= 2 else "/".join(parts)
        for branch in ('main', 'master'):
            raw = f"https://huggingface.co/{repo_path}/raw/{branch}/README.md"
            content = _fetch_url_text(raw)
            if content:
                return content
        # fallback to HF page HTML
        content = _fetch_url_text(url)
        return content

    # Generic: try fetch page directly
    return _fetch_url_text(url)

def _extract_urls_from_markdown(text: str) -> List[str]:
    """Extract URLs from inline markdown, reference-style links, and bare URLs."""
    urls: List[str] = []
    # Inline links
    for m in INLINE_MD_LINK_RE.finditer(text):
        urls.append(m.group(2).strip())
    # Reference definitions and uses
    refs: Dict[str, str] = {}
    for m in REFERENCE_DEF_RE.finditer(text):
        refs[m.group(1).strip().lower()] = m.group(2).strip()
    # [text][id] uses
    for m in REFERENCE_USE_RE.finditer(text):
        ref_id = m.group(2).strip().lower()
        if ref_id in refs:
            urls.append(refs[ref_id])
    # Bare URLs
    for m in URL_RE.finditer(text):
        urls.append(m.group(1).strip())
    # HTML anchors inside markdown (some pages embed HTML)
    for m in HTML_LINK_RE.finditer(text):
        urls.append(m.group(1).strip())
    return list(dict.fromkeys(urls))  # dedupe preserving order

def _extract_urls_from_html(html_text: str) -> List[str]:
    parser = HrefParser()
    try:
        parser.feed(html_text)
    except Exception:
        # feed may raise for invalid markup; fall back to regex
        return _extract_urls_from_markdown(html_text)
    return list(dict.fromkeys(parser.hrefs))

def _normalize_hf_dataset_url(url_or_owner_name: str) -> Optional[str]:
    """Normalize discovered candidate into https://huggingface.co/datasets/owner/name format if possible."""
    if not url_or_owner_name:
        return None
    # If it's already an HF datasets URL
    try:
        parsed = urlparse(url_or_owner_name)
        if parsed.scheme and parsed.netloc and parsed.netloc.lower() in HF_DATASETS_HOSTS:
            # paths like /datasets/owner/name or /owner/name (rare)
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) >= 3 and path_parts[0].lower() == 'datasets':
                owner, name = path_parts[1], path_parts[2]
                return f"https://huggingface.co/datasets/{owner}/{name}"
            # sometimes people link via huggingface.co/owner/name (less common)
            if len(path_parts) >= 2:
                owner, name = path_parts[0], path_parts[1]
                return f"https://huggingface.co/datasets/{owner}/{name}"
        # If input is of the form owner/name -> return hf URL
        m = OWNER_DATASET_RE.search(url_or_owner_name)
        if m:
            owner_name = m.group(1)
            return f"https://huggingface.co/datasets/{owner_name}"
    except Exception:
        return None
    return None

def _scan_text_for_dataset_mentions(text: str) -> List[str]:
    """Scan free text for likely dataset mentions (owner/name) when near 'dataset' words."""
    results: List[str] = []
    lower = text.lower()
    # find owner/name tokens
    for m in OWNER_DATASET_RE.finditer(text):
        token = m.group(1)
        # ensure it's near 'dataset' keyword within a short window
        span_start = max(0, m.start() - 120)
        context = lower[span_start:m.end() + 120]
        if any(k in context for k in ('dataset', 'datasets', 'trained on', 'trained with', 'train on', 'dataset:')):
            results.append(token)
    return list(dict.fromkeys(results))

# ---- Public function ----
def find_datasets_from_resource(resource: Dict) -> Tuple[List[str], int]:
    """
    Given a resource dict, find dataset links / mentions.
    resource may include:
      - 'local_dir': local path to a repo clone
      - 'url': a remote URL to a model or repo page
    Returns (list_of_normalized_dataset_urls_or_owner_names, latency_ms)
    """
    start = time.perf_counter()
    found: List[str] = []
    text: Optional[str] = None

    # 1) Try local README first (preferred)
    local_dir = resource.get('local_dir') or resource.get('local_dir_path')
    if local_dir:
        text = _read_local_readme(local_dir)
        if text:
            logger.debug("Found local README in %s", local_dir)

    # 2) If no local README, try to fetch README/raw from resource URL
    if text is None:
        url = resource.get('url')
        if url:
            text = _try_fetch_readme_from_repo_url(url)

    # If we have no text now, return empty list (latency recorded)
    if not text:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ([], elapsed_ms)

    # 3) Extract candidate URLs from both markdown and HTML parsing
    candidates: Set[str] = set()
    candidates.update(_extract_urls_from_markdown(text))
    candidates.update(_extract_urls_from_html(text))

    # 4) Normalize and filter for HF dataset links
    normalized: List[str] = []
    for c in candidates:
        norm = _normalize_hf_dataset_url(c)
        if norm:
            normalized.append(norm)

    # 5) If none found, scan for bare owner/name mentions near dataset words
    if not normalized:
        owner_names = _scan_text_for_dataset_mentions(text)
        for o in owner_names:
            norm = _normalize_hf_dataset_url(o)
            if norm:
                normalized.append(norm)
            else:
                # keep owner/name as fallback
                normalized.append(o)

    # dedupe preserving order
    seen = set()
    deduped = []
    for item in normalized:
        if item and item not in seen:
            deduped.append(item)
            seen.add(item)

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return (deduped, elapsed_ms)

# When executed directly, a simple demo
if __name__ == "__main__":
    import argparse, json
    p = argparse.ArgumentParser()
    p.add_argument("--url", help="Model/repo URL to scan (e.g. huggingface.co/owner/model or github.com/owner/repo)")
    p.add_argument("--local", help="Local directory to read README from")
    args = p.parse_args()
    resource = {}
    if args.local:
        resource['local_dir'] = args.local
    elif args.url:
        resource['url'] = args.url
    else:
        print("Usage: dataset_link_finder.py --url <url> | --local <dir>")
        raise SystemExit(2)
    found, latency = find_datasets_from_resource(resource)
    print(json.dumps({"datasets": found, "latency_ms": latency}, indent=2))
