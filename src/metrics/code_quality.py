import time
from pathlib import Path
from typing import Any, Dict, Tuple

def metric(resource: Dict[str, Any]) -> Tuple[float, int]:
    """
    Calculates a code quality score based on the presence of key
    repository files and directories in a pre-cloned local path.
    """
    start_time = time.perf_counter()
    score = 0.0

    # This metric expects run.py to have already cloned the repo
    # and provided the path in the 'local_path' key.
    local_repo_path = resource.get("local_path")

    if local_repo_path:
        repo_path = Path(local_repo_path)
        checks = {
            "dependencies": (repo_path / "requirements.txt").exists() or (repo_path / "pyproject.toml").exists(),
            "testing": (repo_path / "tests").is_dir(),
            "ci_cd": (repo_path / ".github").is_dir() or (repo_path / ".gitlab-ci.yml").exists(),
            "containerization": (repo_path / "Dockerfile").exists(),
        }
        # The score is the fraction of successful checks
        score = sum(checks.values()) / len(checks)

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    return score, latency_ms