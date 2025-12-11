"""Size metric - estimates model deployability on different hardware."""
from __future__ import annotations

import time
from typing import Any


def metric(resource: dict[str, Any]) -> tuple[dict[str, float], int]:
    """
    Model size metric - returns scores for different hardware types.
    Uses heuristics based on model name since HF API is unreliable in Lambda.
    
    Returns (dict with 4 hardware scores, latency_ms)
    """
    start = time.perf_counter()
    
    # DEBUG
    print(f"DEBUG SIZE METRIC: resource = {resource}")
    
    default_scores = {
        "raspberry_pi": 0.0,
        "jetson_nano": 0.0,
        "desktop_pc": 0.0,
        "aws_server": 0.0
    }
    
    category = resource.get("category", "")
    print(f"DEBUG SIZE METRIC: category = '{category}'")
    
    if category.upper() != "MODEL":
        latency_ms = int((time.perf_counter() - start) * 1000)
        print(f"DEBUG SIZE METRIC: Not a MODEL, returning defaults")
        return default_scores, latency_ms
    
    # Get model name for heuristic sizing
    name = resource.get("name", "").lower()
    url = resource.get("url", "").lower()
    print(f"DEBUG SIZE METRIC: name = '{name}', url = '{url}'")
    
    # Size heuristics based on common model name patterns
    # Tiny models (<100MB) - great on all hardware
    tiny_patterns = ["tiny", "mini", "small", "distil", "mobile", "lite"]
    # Base models (~500MB-1GB) - moderate
    base_patterns = ["base", "small"]
    # Large models (1-5GB) - needs good hardware
    large_patterns = ["large", "xl", "xxl", "7b", "13b"]
    # Huge models (>10GB) - server only  
    huge_patterns = ["70b", "175b", "llama-2-70", "falcon-40", "gpt-j", "gpt-neo"]
    
    # Determine size category
    combined = name + " " + url
    
    if any(p in combined for p in huge_patterns):
        # Huge model - only works on servers
        scores = {
            "raspberry_pi": 0.0,
            "jetson_nano": 0.0,
            "desktop_pc": 0.2,
            "aws_server": 0.5,
        }
        print(f"DEBUG SIZE METRIC: Matched HUGE pattern")
    elif any(p in combined for p in large_patterns):
        # Large model
        scores = {
            "raspberry_pi": 0.0,
            "jetson_nano": 0.1,
            "desktop_pc": 0.5,
            "aws_server": 0.8,
        }
        print(f"DEBUG SIZE METRIC: Matched LARGE pattern")
    elif any(p in combined for p in tiny_patterns):
        # Tiny model - works everywhere
        scores = {
            "raspberry_pi": 0.8,
            "jetson_nano": 0.9,
            "desktop_pc": 1.0,
            "aws_server": 1.0,
        }
        print(f"DEBUG SIZE METRIC: Matched TINY pattern")
    else:
        # Default: assume base/medium sized model (~500MB-1GB)
        # This covers bert-base, gpt2, etc.
        scores = {
            "raspberry_pi": 0.1,
            "jetson_nano": 0.4,
            "desktop_pc": 0.8,
            "aws_server": 0.9,
        }
        print(f"DEBUG SIZE METRIC: Matched BASE/DEFAULT pattern")
    
    latency_ms = int((time.perf_counter() - start) * 1000)
    print(f"DEBUG SIZE METRIC: returning scores = {scores}, latency = {latency_ms}")
    return scores, latency_ms
