# SWE 45000, PIN FALL 2025
# TEAM 4
# PHASE 1 PROJECT

#METRIC: ramp_up_time
#REQUIREMENTS SATISFIED: latency score, ramp_up_time metric score

# DISCLAIMER: This file contains code either partially or entirely written by
# Artificial Intelligence
"""
src/metrics/ramp_up_time.py

Metric signature:
    def metric(resource: Dict[str, Any]) -> Tuple[float, int]

The metric returns:
    (score_in_[0.0,1.0], latency_ms_int)

Scoring (total = 1.0):
 - README length --> up to 0.40 (raw word count of readme)
 - Installation section keyword --> up to 0.35 (does the readme include installation/startup related keywords/headers?)
 - Code snippets (fenced or indented) --> up to 0.25 (are there any code snippets/examples included?)
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, Optional, Tuple

# Threshold-based length scoring (words -> score)
def _length_score(word_count: int) -> float:
    if word_count < 50:
        return 0.0
    if 50 <= word_count <= 199:
        return 0.1
    if 200 <= word_count <= 499:
        return 0.25
    return 0.4  # >= 500 words

# Detect installation section by heading or common install phrases
_INSTALL_RE = re.compile(
    r"(^|\n)\s*(?:#{1,6}\s*)?(installation|install|setup|getting started|quickstart|usage)\b",
    flags=re.I,
)
_INSTALL_PHRASES = [
    "pip install",
    "conda install",
    "docker",
    "docker-compose",
    "requirements.txt",
    "setup.py",
    "poetry add",
]

# Detect code fences or indented code blocks
_CODE_FENCE_RE = re.compile(r"```")  # fenced blocks
_INDENTED_CODE_RE = re.compile(r"(?m)^( {4}|\t).+")  # lines starting with 4 spaces or a tab


def _read_local_readme(local_dir: str) -> Optional[str]:
    if not local_dir:
        return None
    candidates = ["README.md", "README.rst", "README.txt", "README"]
    for name in candidates:
        p = os.path.join(local_dir, name)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    return fh.read()
            except Exception:
                # reading error -> skip to next candidate
                continue
    return None


def _try_fetch_remote_readme(url: str, timeout: float = 6.0) -> Optional[str]:
    """
    Best-effort attempt to fetch README over HTTP for common hosts (GitHub, Hugging Face).
    This is best-effort and optional — remote fetching is used only if requests is available.
    """
    try:
        import requests  # requests is optional dependency; if missing, we skip remote fetch
    except Exception:
        return None

    url = url.rstrip("/")
    # Try GitHub raw patterns
    if "github.com/" in url:
        # attempt to grab owner/repo from the URL
        try:
            parts = url.split("github.com/")[-1].split("/")
            owner, repo = parts[0], parts[1]
            repo = repo.replace(".git", "")
            for branch in ("main", "master"):
                raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
                try:
                    r = requests.get(raw, timeout=timeout)
                    if r.status_code == 200 and r.text.strip():
                        return r.text
                except Exception:
                    pass
        except Exception:
            pass

    # Try Hugging Face pattern
    if "huggingface.co/" in url:
        try:
            hf_path = url.split("huggingface.co/")[-1].strip("/")
            # try common raw endpoints
            for branch in ("main", "master"):
                raw = f"https://huggingface.co/{hf_path}/raw/{branch}/README.md"
                try:
                    r = requests.get(raw, timeout=timeout)
                    if r.status_code == 200 and r.text.strip():
                        return r.text
                except Exception:
                    pass
        except Exception:
            pass

    # Generic attempt: try /raw/main/README.md and /raw/master/README.md
    for suffix in ("/raw/main/README.md", "/raw/master/README.md", "/README.md"):
        candidate = url + suffix
        try:
            r = requests.get(candidate, timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                return r.text
        except Exception:
            pass

    return None


def _has_install_section(content: str) -> bool:
    if _INSTALL_RE.search(content):
        return True
    low = content.lower()
    for phrase in _INSTALL_PHRASES:
        if phrase in low:
            return True
    return False


def _has_code_snippet(content: str) -> bool:
    if _CODE_FENCE_RE.search(content):
        return True
    if _INDENTED_CODE_RE.search(content):
        return True
    return False


def metric(resource: Dict[str, Any]) -> Tuple[float, int]:
    """
    Compute ramp-up-time proxy score for a model resource.

    resource keys used:
      - 'local_dir' (optional): path to a local clone; metric prioritizes reading README from here.
      - 'url' (optional): model repo URL; used for best-effort remote fetch if local README not found.

    Returns:
      (score, latency_ms)
    """
    t0 = time.perf_counter()
    try:
        content: Optional[str] = None

        # 1) Prefer local README if present (fast and deterministic)
        local_dir = resource.get("local_dir") or resource.get("local_path") or None
        if local_dir and isinstance(local_dir, str):
            content = _read_local_readme(local_dir)

        # 2) If no local README, try remote fetch (best-effort; requires 'requests' in env)
        if content is None:
            url = resource.get("url") or ""
            if url:
                try:
                    content = _try_fetch_remote_readme(url)
                except Exception:
                    content = None  # degrade gracefully

        # 3) If still none, produce score 0.0
        if not content:
            score = 0.0
            latency_ms = int(round((time.perf_counter() - t0) * 1000.0))
            return float(score), int(latency_ms)

        # Normalize content
        # Word count for length-based scoring
        words = re.findall(r"\w+", content)
        wc = len(words)

        len_score = _length_score(wc)
        install_score = 0.35 if _has_install_section(content) else 0.0
        code_score = 0.25 if _has_code_snippet(content) else 0.0

        total = len_score + install_score + code_score
        if total > 1.0:
            total = 1.0

        latency_ms = int(round((time.perf_counter() - t0) * 1000.0))
        return float(round(total, 4)), latency_ms

    except Exception:
        # Any unexpected error should degrade to safe default (score 0.0),
        # but still measure elapsed time.
        latency_ms = int(round((time.perf_counter() - t0) * 1000.0))
        return 0.0, latency_ms
