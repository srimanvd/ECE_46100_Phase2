import logging
import time
from typing import Any

from huggingface_hub import dataset_info

from src.utils.dataset_link_finder import find_datasets_from_resource

logger = logging.getLogger("phase1_cli")

# Well-known datasets that are commonly used for training
WELL_KNOWN_DATASETS = [
    "glue", "squad", "squad_v2", "wikitext", "wikipedia", "bookcorpus",
    "imagenet", "coco", "mnist", "cifar10", "cifar100",
    "imdb", "sst2", "mrpc", "qqp", "mnli", "qnli", "rte", "wnli",
    "conll2003", "wmt14", "wmt16", "common_voice", "librispeech"
]


def _extract_dataset_id(dataset_ref: str) -> str:
    """
    Normalize a dataset reference (URL or owner/name) to a dataset_id
    usable with huggingface_hub.dataset_info().
    """
    if dataset_ref.startswith("http"):
        parts = dataset_ref.rstrip("/").split("/")
        # For HuggingFace dataset URLs, extract the dataset ID
        if "datasets" in parts:
            idx = parts.index("datasets")
            if idx + 1 < len(parts):
                # Return everything after 'datasets'
                return "/".join(parts[idx+1:])
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
        logger.debug(f"Failed to get info for dataset {dataset_id}: {e}")
        return 0.0


def _find_well_known_datasets(resource: dict, readme_text: str = "") -> list[str]:
    """
    Search for well-known dataset names in the model name, URL, or README text.
    Returns list of dataset IDs that match.
    """
    name = resource.get("name", "").lower()
    url = resource.get("url", "").lower()
    text = f"{name} {url} {readme_text.lower()}"
    
    found = []
    for ds in WELL_KNOWN_DATASETS:
        if ds in text:
            found.append(ds)
    return found


# ---------------------------------------------------------------------
# Backward compatibility shim for old tests
def find_dataset_url_from_hf(model_name: str) -> str | None:
    """
    Old compatibility function for tests.
    Uses new find_datasets_from_resource internally.
    Returns the first dataset URL if available, else None.
    """
    datasets = []
    if "github.com" not in model_name:
        resource = {"name": model_name, "url": f"https://huggingface.co/{model_name}"}
        datasets, _ = find_datasets_from_resource(resource)
    return datasets[0] if datasets else None


# ---------------------------------------------------------------------


def metric(resource: dict[str, Any]) -> tuple[float, int]:
    """
    Dataset quality metric.
    
    For MODELS: Searches README for dataset mentions and scores those datasets
    For DATASETS: Scores the dataset directly
    For CODE: Returns 0 (code doesn't have associated datasets)
    """
    start_time = time.perf_counter()
    score = 0.0

    category = resource.get("category", "").upper()
    print(f"DEBUG dataset_quality: category={category}")
    
    # Only CODE artifacts get 0 (they don't reference datasets)
    if category == "CODE":
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return 0.0, latency_ms

    # For MODELS and DATASETS: search for dataset references
    try:
        datasets, _ = find_datasets_from_resource(resource)
        print(f"DEBUG dataset_quality: found {len(datasets)} datasets from README")
    except Exception as e:
        print(f"DEBUG dataset_quality: find_datasets failed: {e}")
        datasets = []

    # Also check for well-known dataset names in model name/URL
    well_known = _find_well_known_datasets(resource)
    if well_known:
        print(f"DEBUG dataset_quality: found {len(well_known)} well-known datasets: {well_known}")
        datasets.extend(well_known)

    if datasets:
        # Score all found datasets and take the max (best-case quality)
        dataset_ids: list[str] = [_extract_dataset_id(d) for d in datasets]
        scores = [_score_dataset(ds_id) for ds_id in dataset_ids if ds_id]
        if scores:
            score = max(scores)
            print(f"DEBUG dataset_quality: max score={score}")

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    return score, latency_ms
