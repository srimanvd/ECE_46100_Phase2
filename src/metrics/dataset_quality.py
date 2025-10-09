import time
import logging
from typing import Any, Dict, Tuple, List

from huggingface_hub import dataset_info
from src.utils.dataset_link_finder import find_datasets_from_resource

logger = logging.getLogger("phase1_cli")


def _extract_dataset_id(dataset_ref: str) -> str:
    """
    Normalize a dataset reference (URL or owner/name) to a dataset_id
    usable with huggingface_hub.dataset_info().
    """
    if dataset_ref.startswith("http"):
        parts = dataset_ref.rstrip("/").split("/")
        if len(parts) >= 2:
            return "/".join(parts[-2:])  # owner/name
    return dataset_ref  # already looks like owner/name


def _score_dataset(dataset_id: str) -> float:
    """
    Calculate dataset quality score for a single dataset_id.
    """
    try:
        info = dataset_info(dataset_id)

        card_score = 0.5 if (info.cardData and "dataset_card" in info.cardData) else 0.0
        downloads_score = 0.3 if info.downloads and info.downloads > 1000 else 0.0
        likes_score = 0.2 if info.likes and info.likes > 10 else 0.0

        return card_score + downloads_score + likes_score
    except Exception as e:
        logger.error(f"Failed to get info for dataset {dataset_id}: {e}")
        return 0.0


# ---------------------------------------------------------------------
# Backward compatibility shim for old tests
def find_dataset_url_from_hf(model_name: str) -> str | None:
    """
    Old compatibility function for tests.
    Uses new find_datasets_from_resource internally.
    Returns the first dataset URL if available, else None.
    """
    resource = {"name": model_name, "url": f"https://huggingface.co/{model_name}"}
    datasets, _ = find_datasets_from_resource(resource)
    return datasets[0] if datasets else None
# ---------------------------------------------------------------------


def metric(resource: Dict[str, Any]) -> Tuple[float, int]:
    """
    Calculates a dataset quality score by finding linked dataset(s)
    and assessing their metadata on the Hugging Face Hub.
    """
    start_time = time.perf_counter()
    score = 0.0

    datasets, _ = find_datasets_from_resource(resource)

    if datasets:
        # Score all found datasets and take the max (best-case quality)
        dataset_ids: List[str] = [_extract_dataset_id(d) for d in datasets]
        scores = [_score_dataset(ds_id) for ds_id in dataset_ids if ds_id]
        if scores:
            score = max(scores)

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    return score, latency_ms
