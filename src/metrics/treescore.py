# metrics/treescore.py

"""
Treescore metric.

Spec summary:
- Treescore is the average of the *total model scores* of all parents
  of the model, according to the lineage graph.

This file assumes that:
- The lineage graph has already been computed elsewhere (e.g., from
  config.json) and you can supply a list of parent model IDs.
- You have a mapping from model_id -> total_score (e.g., stored in
  your registry database when you rate each model).

Behavior:
- If there are no parents, or none of the parents have a known score,
  we return -1.0.
- Otherwise we return the average of the known parent scores.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass
class TreescoreResult:
    score: float  # in [0, 1] or -1.0 if no parents / no data
    num_parents: int  # total parents listed
    num_scored_parents: int  # how many had known scores
    missing_parents: list[str]


def compute_treescore(
    model_id: str,
    parent_ids: Sequence[str],
    total_scores_by_model_id: Mapping[str, float],
) -> TreescoreResult:
    """
    Compute the treescore for a model, given its parents and a map of total scores.

    Args:
        model_id: ID of the model being scored. (Only used for logging/debugging.)
        parent_ids: List of parent model IDs from the lineage graph.
        total_scores_by_model_id: Mapping from model ID to its overall score
                                  (e.g., your Phase 1 net score or an extended score).

    Returns:
        TreescoreResult with score and some diagnostics.
    """
    if not parent_ids:
        return TreescoreResult(
            score=-1.0,
            num_parents=0,
            num_scored_parents=0,
            missing_parents=[],
        )

    scored_values = []
    missing: list[str] = []

    for pid in parent_ids:
        if (
            pid in total_scores_by_model_id
            and total_scores_by_model_id[pid] is not None
        ):
            scored_values.append(total_scores_by_model_id[pid])
        else:
            missing.append(pid)

    if not scored_values:
        # No parent had a known score.
        return TreescoreResult(
            score=-1.0,
            num_parents=len(parent_ids),
            num_scored_parents=0,
            missing_parents=missing,
        )

    avg = sum(scored_values) / len(scored_values)
    return TreescoreResult(
        score=avg,
        num_parents=len(parent_ids),
        num_scored_parents=len(scored_values),
        missing_parents=missing,
    )


if __name__ == "__main__":
    # Tiny demo
    parents = ["modelA", "modelB", "modelC"]
    scores = {"modelA": 0.8, "modelB": 0.6}  # modelC missing
    res = compute_treescore("childModel", parents, scores)
    print(res)
