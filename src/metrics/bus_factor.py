from __future__ import annotations

import math
import time
from collections import Counter

try:
    from git import Repo
except ImportError:
    Repo = None  # gracefully handle missing GitPython


def compute_bus_factor_from_commits(commits: list[str]) -> float:
    """Entropy-based bus factor calculation from a list of commit authors."""
    if not commits:
        return 0.0

    commit_counts = Counter(commits)
    total_commits = sum(commit_counts.values())
    num_contributors = len(commit_counts)

    # Single contributor → bus factor = 0
    if num_contributors <= 1:
        return 0.0

    # Entropy normalized by max possible entropy
    probabilities = [c / total_commits for c in commit_counts.values()]
    entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
    return entropy / math.log2(num_contributors)


def compute_bus_factor(commits: list[str]) -> tuple[float, int]:
    """
    Backward-compatible function used in tests.
    Returns (score ∈ [0,1], latency_ms).
    """
    start = time.perf_counter()
    score = compute_bus_factor_from_commits(commits)
    latency_ms = int((time.perf_counter() - start) * 1000)
    return score, latency_ms


def metric(resource: dict) -> tuple[float, int]:
    """
    Bus Factor metric:
    - Extract authors from the cloned repo at resource['local_path'] or ['local_dir'].
    - Return (score ∈ [0,1], latency_ms).
    """
    start = time.perf_counter()
    commits: list[str] = []

    repo_path = resource.get("local_path") or resource.get("local_dir")
    print(f"DEBUG: bus_factor repo_path={repo_path}")
    if repo_path and Repo is not None:
        try:
            repo = Repo(repo_path)
            # Limit commits for speed (default: 500 latest commits)
            for commit in repo.iter_commits(max_count=500):
                if commit.author and commit.author.email:
                    commits.append(commit.author.email)
                elif commit.author and commit.author.name:
                    commits.append(commit.author.name)
            print(f"DEBUG: bus_factor found {len(commits)} commits")
        except Exception as e:
            print(f"DEBUG: bus_factor error: {e}")
            commits = []
    else:
        print(f"DEBUG: bus_factor skipped (path={repo_path}, Repo={Repo})")

    score = compute_bus_factor_from_commits(commits)
    print(f"DEBUG: bus_factor score={score}")
    latency_ms = int((time.perf_counter() - start) * 1000)
    return float(score), latency_ms
