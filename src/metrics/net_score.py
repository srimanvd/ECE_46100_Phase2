# metrics/net_score.py

from collections.abc import Mapping

# Phase 1 metric weights (you can tweak these if your team decided differently)
BASE_WEIGHTS: Mapping[str, float] = {
    "ramp_up_time": 0.15,
    "bus_factor": 0.15,
    "license": 0.15,
    "dataset_and_code_score": 0.20,
    "dataset_quality": 0.15,
    "code_quality": 0.10,
    "performance_claims": 0.10,
}

# New trust metrics (you can adjust weights to match your design doc)
TRUST_WEIGHTS: Mapping[str, float] = {
    "reproducibility": 0.20,
    "reviewedness": 0.20,
    "treescore": 0.20,
}

# Final weight map
WEIGHTS: Mapping[str, float] = {
    **BASE_WEIGHTS,
    **TRUST_WEIGHTS,
}


def compute_net_score(metric_scores: dict[str, float]) -> float:
    """
    Compute a weighted net_score from individual metric scores.

    metric_scores is a dict like:
        {
          "ramp_up_time": 0.8,
          "bus_factor": 0.6,
          "reproducibility": 0.9,
          ...
        }

    Any metric in WEIGHTS that is missing from metric_scores is ignored.
    All scores are clamped to [0, 1] before weighting.
    """
    weighted_sum = 0.0
    total_weight = 0.0

    for name, weight in WEIGHTS.items():
        if name not in metric_scores:
            continue

        score = float(metric_scores[name])
        # Clamp to [0, 1] just in case
        if score < 0.0:
            score = 0.0
        elif score > 1.0:
            score = 1.0

        weighted_sum += weight * score
        total_weight += weight

    if total_weight == 0.0:
        return 0.0

    return weighted_sum / total_weight
