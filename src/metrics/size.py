from __future__ import annotations

import time
import requests
from typing import Any

from huggingface_hub import model_info
from huggingface_hub.utils import HfHubHTTPError


def normalize(value: float, min_val: float, max_val: float) -> float:
    """Linearly scale size into [0,1], clamped."""
    if value <= min_val:
        return 1.0
    elif value >= max_val:
        return 0.0
    return 1 - ((value - min_val) / (max_val - min_val))


def get_model_size_via_http(model_id: str, siblings: list) -> int:
    """
    Fallback: Get model file sizes via HTTP HEAD requests.
    This works even when HuggingFace API doesn't expose file sizes.
    """
    total_size = 0
    
    # Common model file patterns
    model_files = []
    for sibling in siblings:
        filename = getattr(sibling, 'rfilename', '')
        if any(ext in filename for ext in ['.bin', '.safetensors', '.onnx', '.pt', '.pth']):
            model_files.append(filename)
    
    # If no model files found, try common names
    if not model_files:
        model_files = ['pytorch_model.bin', 'model.safetensors', 'tf_model.h5']
    
    for filename in model_files[:3]:  # Limit to 3 requests
        try:
            url = f"https://huggingface.co/{model_id}/resolve/main/{filename}"
            resp = requests.head(url, allow_redirects=True, timeout=5)
            if resp.status_code == 200:
                content_length = resp.headers.get('Content-Length')
                if content_length:
                    size = int(content_length)
                    print(f"DEBUG SIZE: Got {filename} size={size} via HTTP HEAD")
                    total_size += size
        except Exception as e:
            print(f"DEBUG SIZE: HTTP HEAD failed for {filename}: {e}")
            continue
    
    return total_size


def metric(resource: dict[str, Any]) -> tuple[dict[str, float], int]:
    """
    Model size metric - returns scores for different hardware types.
    Uses HuggingFace API to get actual model size.
    Falls back to HTTP HEAD requests if API doesn't have size info.
    Returns (dict with 4 hardware scores, latency_ms)
    
    Force deployment: 2025-12-10
    """
    start = time.perf_counter()
    
    default_scores = {
        "raspberry_pi": 0.0,
        "jetson_nano": 0.0,
        "desktop_pc": 0.0,
        "aws_server": 0.0
    }
    
    category = resource.get("category", "").upper()
    if category != "MODEL":
        latency_ms = int((time.perf_counter() - start) * 1000)
        return default_scores, latency_ms
    
    url = resource.get("url", "")
    print(f"DEBUG SIZE: url='{url}', name='{resource.get('name', '')}'")
    
    # Only use URL to get model_id - NEVER use name field
    model_id = None
    if "huggingface.co" in url:
        try:
            # Extract from URL like https://huggingface.co/org/model
            model_id = url.split("huggingface.co/")[-1].strip("/")
            print(f"DEBUG SIZE: extracted model_id='{model_id}' from URL")
        except:
            pass
    
    if not model_id:
        # No valid HuggingFace URL - return zeros
        print(f"DEBUG SIZE: No HuggingFace URL found, returning zeros")
        latency_ms = int((time.perf_counter() - start) * 1000)
        return default_scores, latency_ms
    
    try:
        info = model_info(model_id)
        print(f"DEBUG SIZE: HuggingFace API call successful for '{model_id}'")
        
        size_bytes = 0
        
        # Method 1: Try safetensors info
        if hasattr(info, 'safetensors') and info.safetensors:
            if hasattr(info.safetensors, 'total'):
                size_bytes = info.safetensors.total
                print(f"DEBUG SIZE: Got size from safetensors: {size_bytes}")
        
        # Method 2: Try siblings with size
        if size_bytes == 0 and hasattr(info, 'siblings') and info.siblings:
            for sibling in info.siblings:
                if hasattr(sibling, 'size') and sibling.size:
                    size_bytes += sibling.size
            if size_bytes > 0:
                print(f"DEBUG SIZE: Got size from siblings: {size_bytes}")
        
        # Method 3: Fallback to HTTP HEAD requests
        if size_bytes == 0 and hasattr(info, 'siblings') and info.siblings:
            print(f"DEBUG SIZE: Trying HTTP HEAD fallback")
            size_bytes = get_model_size_via_http(model_id, info.siblings)
        
        print(f"DEBUG SIZE: final size_bytes={size_bytes}")
        
        if size_bytes == 0:
            # Model found but no size info even after fallback
            print(f"DEBUG SIZE: Model found but no size info, returning zeros")
            latency_ms = int((time.perf_counter() - start) * 1000)
            return default_scores, latency_ms
        
        size_gb = size_bytes / (1024 ** 3)
        
        scores = {
            "raspberry_pi": normalize(size_gb, 0.0, 4.0),    # ~4GB RAM limit
            "jetson_nano": normalize(size_gb, 0.0, 8.0),     # ~8GB RAM limit
            "desktop_pc": normalize(size_gb, 0.0, 32.0),     # ~32GB RAM typical
            "aws_server": normalize(size_gb, 0.0, 100.0),    # ~100GB+ for cloud
        }
        
        print(f"DEBUG SIZE: Returning scores={scores}")
        latency_ms = int((time.perf_counter() - start) * 1000)
        return scores, latency_ms
        
    except (HfHubHTTPError, Exception) as e:
        print(f"DEBUG SIZE: HuggingFace API failed for '{model_id}': {e}")
        latency_ms = int((time.perf_counter() - start) * 1000)
        return default_scores, latency_ms
