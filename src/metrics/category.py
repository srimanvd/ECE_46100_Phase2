import time
from typing import Any, Dict, Tuple
from huggingface_hub import model_info
from huggingface_hub.utils import HfHubHTTPError

def metric(resource: Dict[str, Any]) -> Tuple[str, int]:
    """
    Determines a specific category for a model, using the Hugging Face
    pipeline_tag if available.
    """
    start_time = time.perf_counter()
    category = "Model" # Default fallback category

    if "huggingface.co" in resource['url']:
        try:
            info = model_info(resource['name'])
            if info.pipeline_tag:
                category = info.pipeline_tag
        except HfHubHTTPError:
            category = "Model (Not Found)"
    elif "github.com" in resource['url']:
        category = "Code Repository"

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    return category, latency_ms