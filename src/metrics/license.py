# src/metrics/license_score.py
"""
License compatibility metric that uses Purdue GenAI Studio (LLM) as the primary
analyzer and falls back to a local heuristic if the API is not available.

Exports:
    def metric(resource: Dict[str, Any]) -> Tuple[float, int]

Environment variables (optional):
    - PURDUE_GENAI_API_KEY: API key (string) obtained from Purdue GenAI Studio UI
    - PURDUE_GENAI_MODEL: model id to use (default "llama3.1:latest")
    - PURDUE_GENAI_ENDPOINT: endpoint override (default "https://genai.rcac.purdue.edu/api/chat/completions")

Notes:
  - The metric prefers a LICENSE file in resource['local_dir'] (if present),
    otherwise it will try resource['url'] + README (best-effort).
  - Returns a float in [0,1] and the latency in integer milliseconds.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, Optional, Tuple

import requests  # add to requirements.txt

# Default Purdue GenAI Studio endpoint (OpenAI-compatible chat completions)
_DEFAULT_ENDPOINT = os.environ.get(
    "PURDUE_GENAI_ENDPOINT", "https://genai.rcac.purdue.edu/api/chat/completions"
)
_DEFAULT_MODEL = os.environ.get("PURDUE_GENAI_MODEL", "llama3.1:latest")
_API_KEY_ENV = "GEN_AI_STUDIO_API_KEY"


# -----------------------
# Helpers: file reading
# -----------------------
def _read_local_file(local_dir: str, names=("LICENSE", "LICENSE.txt", "LICENSE.md", "README.md")) -> Optional[str]:
    if not local_dir:
        return None
    for name in names:
        path = os.path.join(local_dir, name)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    return fh.read()
            except Exception:
                continue
    return None


# -----------------------
# Heuristic fallback
# -----------------------
_LICENSE_KEYWORDS = {
    "mit": ("MIT", 1.0),
    "apache": ("Apache-2.0", 0.95),
    "bsd": ("BSD", 0.9),
    "lgpl": ("LGPL", 0.6),   # moved above gpl
    "gpl": ("GPL", 0.4),
    "mozilla": ("MPL", 0.8),
    "proprietary": ("Proprietary", 0.0),
}

def heuristic_license_score(text: str) -> Tuple[float, str, str]:
    if not text:
        return 0.0, "NO_LICENSE_DETECTED", "missing"
    low = text.lower()
    for k, (label, score) in _LICENSE_KEYWORDS.items():
        if k in low:
            return float(score), label, "heuristic"
    # fallback: if contains "copyright" or "all rights reserved" treat as restrictive
    if "all rights reserved" in low or "copyright" in low:
        return 0.0, "PROPRIETARY-LIKE", "heuristic"
    # unknown
    return 0.0, "UNKNOWN", "heuristic"


# -----------------------
# LLM call and parsing
# -----------------------
def _build_prompt_for_license(text: str) -> str:
    """
    Returns a user prompt instructing the LLM to return a small JSON object.
    The LLM should output parsable JSON (license_spdx, category, compatibility_score, explanation).
    """
    # Keep prompt concise and ask for JSON only (to ease parsing)
    return (
        "You are a helpful assistant that classifies software licenses and assesses their "
        "compatibility for reuse (including commercial use and modification). "
        "Given the following license or README text, respond ONLY with a single valid JSON object "
        "containing the fields: "
        "license_spdx (string or 'UNKNOWN'), "
        "category (one of 'permissive','weak-copyleft','strong-copyleft','proprietary','unknown'), "
        "compatibility_score (number between 0.0 and 1.0), "
        "compatibility_with_commercial_use (true/false), "
        "explanation (short string). "
        "Here is the text to analyze:\n\n"
        f"{text}\n\n"
        "Return only the JSON object and nothing else."
    )


def _call_purdue_genai(prompt: str, model: str = _DEFAULT_MODEL, endpoint: str = _DEFAULT_ENDPOINT,
                       api_key: Optional[str] = None, timeout: int = 20) -> Dict[str, Any]:
    """
    Call Purdue GenAI Studio chat completions endpoint in an OpenAI-compatible way.
    Returns the parsed JSON response body (the whole response) or raises Exception on failure.
    Example endpoint and header usage documented by RCAC. :contentReference[oaicite:2]{index=2}
    """
    if not api_key:
        raise RuntimeError("No Purdue GenAI API key provided")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
    }

    resp = requests.post(endpoint, headers=headers, json=body, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Purdue GenAI API error: {resp.status_code} {resp.text}")
    # response is expected to be JSON
    return resp.json()


def _extract_json_from_assistant(content: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to find a JSON object inside the assistant message. We try to be forgiving.
    """
    # First try to parse the whole content
    content = content.strip()
    # If content starts with ```json ... ``` remove fences
    # remove triple backticks
    content = re.sub(r"(^```json\s*|\s*```$)", "", content, flags=re.I).strip()
    # Simple heuristic: find first { ... } block
    m = re.search(r"(\{(?:.|\s)*\})", content)
    if not m:
        return None
    fragment = m.group(1)
    try:
        return json.loads(fragment)
    except Exception:
        # try to fix common single-quote issues
        try:
            fixed = fragment.replace("'", '"')
            return json.loads(fixed)
        except Exception:
            return None


# -----------------------
# Public metric API
# -----------------------
def metric(resource: Dict[str, Any]) -> Tuple[float, int]:
    """
    Compute license compatibility score for a given resource.
    Input 'resource' keys used:
      - 'local_dir' (optional): local path to repo snapshot
      - 'url' (optional): original repo URL (used as fallback)
    Output:
      - (score_float_in_[0,1], latency_ms_int)
    """
    t0 = time.perf_counter()
    # 1) Get license or README text (prefer LICENSE)
    local_dir = resource.get("local_dir") or resource.get("local_path") or None
    text = None
    if local_dir:
        text = _read_local_file(local_dir, names=("LICENSE", "LICENSE.txt", "LICENSE.md", "LICENSE.rst"))
    # fallback to README if no license
    if not text and local_dir:
        text = _read_local_file(local_dir, names=("README.md", "README.rst", "README.txt", "README"))
    # if still nothing, optionally we could attempt remote read (omitted here for determinism)
    if not text:
        # fallback to resource 'url' presence (we choose not to fetch network READMEs here)
        # We will still attempt LLM only if API key is present and resource.url has some brief text
        text = ""

    # 2) Try LLM if API key is present (Purdue GenAI)
    api_key = os.environ.get(_API_KEY_ENV)
    if api_key and text is not None:
        # build prompt and call LLM
        prompt = _build_prompt_for_license(text if text else "No license text found.")
        try:
            resp_json = _call_purdue_genai(prompt, model=os.environ.get("PURDUE_GENAI_MODEL", _DEFAULT_MODEL),
                                           endpoint=os.environ.get("PURDUE_GENAI_ENDPOINT", _DEFAULT_ENDPOINT),
                                           api_key=api_key, timeout=25)
            # Parse assistant content. Response structure expected to follow chat completion
            # Example: resp_json['choices'][0]['message']['content'] or resp_json['choices'][0]['text']
            assistant_content = None
            choices = resp_json.get("choices") or []
            if choices:
                first = choices[0]
                # new-style chat message
                if isinstance(first.get("message"), dict):
                    assistant_content = first["message"].get("content")
                else:
                    assistant_content = first.get("text") or first.get("message")
            if assistant_content:
                parsed = _extract_json_from_assistant(assistant_content)
                if parsed:
                    # expected fields: compatibility_score (0.0-1.0), license_spdx, category, explanation
                    score = parsed.get("compatibility_score")
                    # normalize / validate
                    if isinstance(score, (int, float)):
                        scoref = float(score)
                        if scoref < 0.0:
                            scoref = 0.0
                        if scoref > 1.0:
                            scoref = 1.0
                        latency_ms = int(round((time.perf_counter() - t0) * 1000.0))
                        return scoref, latency_ms
            # If parsing failed, fall through to heuristic
        except Exception:
            # LLM call failed -> fall back to heuristic
            pass

    # 3) Heuristic fallback (local deterministic)
    heuristic_score, label, method = heuristic_license_score(text)
    latency_ms = int(round((time.perf_counter() - t0) * 1000.0))
    return float(heuristic_score), latency_ms
