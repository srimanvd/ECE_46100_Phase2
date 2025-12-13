import logging
import time
from typing import Any

from huggingface_hub import dataset_info, model_info

from src.utils.dataset_link_finder import find_datasets_from_resource

logger = logging.getLogger("phase1_cli")

# Dataset name normalization - common variations that need mapping
DATASET_ALIASES = {
    'imagenet': 'imagenet-1k',
    'imagenet1k': 'imagenet-1k',
    'ilsvrc': 'imagenet-1k',
    'ilsvrc2012': 'imagenet-1k',
    'coco': 'detection-datasets/coco',
    'mscoco': 'detection-datasets/coco',
}


def _normalize_dataset_id(dataset_id: str) -> str:
    """Normalize dataset ID to handle common aliases."""
    lower_id = dataset_id.lower().strip()
    return DATASET_ALIASES.get(lower_id, dataset_id)


def _extract_dataset_id(dataset_ref: str) -> str:
    """
    Normalize a dataset reference (URL or owner/name) to a dataset_id
    usable with huggingface_hub.dataset_info().
    """
    if dataset_ref.startswith("http"):
        parts = dataset_ref.rstrip("/").split("/")
        if "datasets" in parts:
            idx = parts.index("datasets")
            if idx + 1 < len(parts):
                ds_id = "/".join(parts[idx+1:])
                return _normalize_dataset_id(ds_id)
        if len(parts) >= 2:
            ds_id = "/".join(parts[-2:])
            return _normalize_dataset_id(ds_id)
    return _normalize_dataset_id(dataset_ref)


def _score_dataset(dataset_id: str) -> float:
    """Calculate dataset quality score for a single dataset_id."""
    # Normalize the ID first
    normalized_id = _normalize_dataset_id(dataset_id)
    print(f"DEBUG dataset_quality: scoring '{dataset_id}' as '{normalized_id}'")
    
    try:
        info = dataset_info(normalized_id)
        
        # Base score for dataset existing on HuggingFace
        base_score = 0.5
        
        # Bonus for having card data
        card_bonus = 0.2 if info.cardData else 0.0
        
        # Bonus for downloads (more generous thresholds)
        downloads_bonus = 0.0
        if info.downloads:
            if info.downloads > 100:
                downloads_bonus = 0.15
            if info.downloads > 10000:
                downloads_bonus = 0.25
        
        # Bonus for likes (more generous)
        likes_bonus = 0.1 if info.likes and info.likes > 5 else 0.0
        
        score = min(1.0, base_score + card_bonus + downloads_bonus + likes_bonus)
        print(f"DEBUG dataset_quality: '{normalized_id}' score={score}")
        return score
    except Exception as e:
        logger.debug(f"Failed to get info for dataset {normalized_id}: {e}")
        return 0.0


def _get_datasets_from_model_card(url: str) -> list[str]:
    """
    Get datasets directly from the model's HuggingFace card data.
    """
    if "huggingface.co" not in url:
        return []
    
    try:
        model_id = url.split("huggingface.co/")[-1].strip("/")
        info = model_info(model_id)
        
        if info.cardData:
            datasets = getattr(info.cardData, 'datasets', None)
            if datasets:
                print(f"DEBUG dataset_quality: found datasets in model card: {datasets}")
                return datasets if isinstance(datasets, list) else [datasets]
    except Exception as e:
        print(f"DEBUG dataset_quality: failed to get model card: {e}")
    
    return []


# Backward compatibility
def find_dataset_url_from_hf(model_name: str) -> str | None:
    datasets = []
    if "github.com" not in model_name:
        resource = {"name": model_name, "url": f"https://huggingface.co/{model_name}"}
        datasets, _ = find_datasets_from_resource(resource)
    return datasets[0] if datasets else None


def metric(resource: dict[str, Any]) -> tuple[float, int]:
    """
    Dataset quality metric.
    """
    start_time = time.perf_counter()
    score = 0.0

    category = resource.get("category", "").upper()
    print(f"DEBUG dataset_quality: category={category}")
    
    if category == "CODE":
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return 0.0, latency_ms

    datasets = []
    
    # Method 1: Get datasets from HuggingFace model card (most reliable)
    url = resource.get("url", "")
    card_datasets = _get_datasets_from_model_card(url)
    if card_datasets:
        datasets.extend(card_datasets)
    
    # Method 2: Fallback to README parsing
    if not datasets:
        try:
            readme_datasets, _ = find_datasets_from_resource(resource)
            print(f"DEBUG dataset_quality: found {len(readme_datasets)} datasets from README")
            datasets.extend(readme_datasets)
        except Exception as e:
            print(f"DEBUG dataset_quality: find_datasets failed: {e}")

    if datasets:
        dataset_ids = [_extract_dataset_id(d) for d in datasets]
        scores = [_score_dataset(ds_id) for ds_id in dataset_ids if ds_id]
        if scores:
            score = max(scores)
            print(f"DEBUG dataset_quality: max score={score}")

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    return score, latency_ms
