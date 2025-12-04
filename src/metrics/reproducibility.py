# metrics/reproducibility.py

"""
Reproducibility metric.

Goal (per spec):
- 0.0  -> no demo code or cannot run with included demo code
- 0.5  -> can run, but only after "agent" / manual debugging
- 1.0  -> runs out-of-the-box with the provided demo code

This module gives you two pathways:
1. Automatic attempt to run a demo script in the model repo.
2. A helper to map a manual label ("none", "agent", "native") to a score.

In practice, you will probably:
- Do one or more trial runs yourself (or via an LLM "agent"),
- Store the label for each model in your registry DB,
- Use `score_from_label` when computing the metric.

The automatic runner is included so you have *some* concrete behavior
even before you build a more sophisticated agent pipeline.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ReproducibilityLabel = Literal["none", "agent", "native", "unknown"]


@dataclass
class ReproducibilityResult:
    score: float  # 0.0, 0.5, 1.0, or -1.0 for "unknown"
    label: ReproducibilityLabel
    reason: str
    runtime_seconds: float | None = None
    command: str | None = None


def score_from_label(label: ReproducibilityLabel) -> float:
    """Convert a label into the numeric repro score."""
    if label == "none":
        return 0.0
    if label == "agent":
        return 0.5
    if label == "native":
        return 1.0
    # unknown
    return -1.0


def compute_reproducibility_from_label(label: ReproducibilityLabel) -> ReproducibilityResult:
    """
    Simple helper if you store a label in your DB and just want a score object back.
    """
    s = score_from_label(label)
    return ReproducibilityResult(
        score=s,
        label=label,
        reason=f"Reproducibility set from label '{label}'",
        runtime_seconds=None,
        command=None,
    )


def _find_demo_script(model_dir: Path) -> Path | None:
    """
    Heuristic: look for a 'demo' / 'inference' script inside the model directory.

    You can refine this later based on how your HF-style packages are actually structured.
    """
    candidates = [
        "inference.py",
        "demo.py",
        "run.py",
        "app.py",
        "example.py",
    ]
    for name in candidates:
        p = model_dir / name
        if p.is_file():
            return p
    return None


def compute_reproducibility_via_demo(
    model_dir: str | Path,
    demo_entry_point: str | None = None,
    timeout_seconds: int = 120,
) -> ReproducibilityResult:
    """
    Attempt to run the demo script directly.

    This is a "best effort" automatic metric:
    - If we find no demo script -> score 0.0 ("none")
    - If script runs with exit code 0 -> score 1.0 ("native")
    - If script fails / times out -> score 0.0 ("none")

    If you later build an agent that auto-fixes some failures, that agent
    can call this function, attempt fixes, and then call
    `compute_reproducibility_from_label("agent")` on success.
    """
    model_path = Path(model_dir)

    if demo_entry_point is not None:
        demo_path = model_path / demo_entry_point
    else:
        demo_path = _find_demo_script(model_path)

    if demo_path is None or not demo_path.is_file():
        return ReproducibilityResult(
            score=0.0,
            label="none",
            reason="No demo script found in model package",
        )

    cmd = [sys.executable, str(demo_path)]
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=model_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            text=True,
        )
        runtime = time.time() - start
    except subprocess.TimeoutExpired:
        return ReproducibilityResult(
            score=0.0,
            label="none",
            reason=f"Demo script '{demo_path.name}' timed out after {timeout_seconds} seconds",
            runtime_seconds=timeout_seconds,
            command=" ".join(cmd),
        )
    except FileNotFoundError:
        return ReproducibilityResult(
            score=0.0,
            label="none",
            reason=f"Python executable or demo script not found when running '{demo_path}'",
            runtime_seconds=None,
            command=" ".join(cmd),
        )

    if proc.returncode == 0:
        return ReproducibilityResult(
            score=1.0,
            label="native",
            reason=f"Demo script '{demo_path.name}' ran successfully with exit code 0",
            runtime_seconds=runtime,
            command=" ".join(cmd),
        )

    # Non-zero exit: automatic metric says "fails". Human/agent can override.
    return ReproducibilityResult(
        score=0.0,
        label="none",
        reason=f"Demo script '{demo_path.name}' exited with code {proc.returncode}",
        runtime_seconds=runtime,
        command=" ".join(cmd),
    )


# Convenience alias for your net_score import:
def compute_reproducibility(
    model_dir: str | Path,
    manual_label: ReproducibilityLabel | None = None,
    demo_entry_point: str | None = None,
    timeout_seconds: int = 120,
) -> ReproducibilityResult:
    """
    Main API.

    - If `manual_label` is provided, use that (this is what you'll probably use
      in the final system, based on your experiments and/or agent runs).
    - Otherwise, try to run the demo script automatically.
    """
    if manual_label is not None:
        return compute_reproducibility_from_label(manual_label)

    return compute_reproducibility_via_demo(
        model_dir=model_dir,
        demo_entry_point=demo_entry_point,
        timeout_seconds=timeout_seconds,
    )


if __name__ == "__main__":
    # Small CLI for manual testing
    import argparse

    parser = argparse.ArgumentParser(description="Compute reproducibility metric for a model repo.")
    parser.add_argument("model_dir", help="Path to the local model repo directory")
    parser.add_argument("--demo", help="Explicit demo entry point (relative path)", default=None)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    res = compute_reproducibility(args.model_dir, demo_entry_point=args.demo, timeout_seconds=args.timeout)
    print(res)
