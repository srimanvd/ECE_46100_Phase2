# metrics/reviewedness.py

"""
Reviewedness metric.

Spec summary:
- Fraction of all *code* (not weights) in the associated GitHub repo
  that was introduced via pull requests with a code review.
- If there is no linked GitHub repo, use -1.

This implementation approximates that as:

- Clone / open the local git repo.
- Walk commits reachable from the main branch.
- For each commit, determine if it likely came from a reviewed PR
  using patterns in the commit message (e.g., "Merge pull request",
  "Reviewed-by:", "Pull Request #123").
- Sum added lines for code files (ignoring known "weights" extensions).
- reviewedness = reviewed_loc / total_loc  (or -1.0 if total_loc == 0)

This is not perfect, but matches the intent and is explainable in your report.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# Extensions that are clearly *not* code and should be excluded.
WEIGHT_EXTENSIONS = {
    ".bin",
    ".pt",
    ".safetensors",
    ".onnx",
    ".h5",
    ".tflite",
}

# Very rough heuristic for commit messages that indicate a reviewed PR.
REVIEW_KEYWORDS = [
    "Merge pull request",
    "Reviewed-by:",
    "Code-Review+",
    "pull request #",
]


@dataclass
class ReviewednessResult:
    score: float  # in [0, 1], or -1.0 for "no repo / no code"
    total_code_lines: int
    reviewed_code_lines: int
    repo_path: Path | None = None
    reason: str = ""


def _run_git(repo_path: Path, args: Iterable[str]) -> str:
    """Run a git command and return stdout as text."""
    cmd = ["git"] + list(args)
    proc = subprocess.run(
        cmd,
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _get_main_branch(repo_path: Path) -> str:
    """
    Try to detect the primary branch name. Fallback to 'main' or 'master'.
    """
    try:
        # This works on many Git setups
        symbolic = _run_git(repo_path, ["symbolic-ref", "--short", "HEAD"]).strip()
        if symbolic:
            return symbolic
    except subprocess.CalledProcessError:
        pass

    for candidate in ("main", "master"):
        try:
            _run_git(repo_path, ["rev-parse", candidate])
            return candidate
        except subprocess.CalledProcessError:
            continue

    # Last resort: use HEAD
    return "HEAD"


def _iter_commits_with_messages(
    repo_path: Path, branch: str
) -> Iterable[tuple[str, str]]:
    """
    Yield (commit_hash, commit_message) for all commits reachable from branch.
    """
    log_output = _run_git(
        repo_path,
        ["log", "--pretty=format:%H%x09%s", branch],
    )
    for line in log_output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        commit_hash, message = parts
        yield commit_hash, message


def _is_reviewed_commit(message: str) -> bool:
    """Heuristic: does the commit message look like a reviewed PR merge?"""
    lower = message.lower()
    for kw in REVIEW_KEYWORDS:
        if kw.lower() in lower:
            return True
    return False


def _is_code_file(path: str) -> bool:
    """
    Decide if a file path looks like "code" rather than "weights".
    Conservative: we just exclude clearly weight-like files by extension.
    """
    p = Path(path)
    if p.suffix in WEIGHT_EXTENSIONS:
        return False
    # You can add more logic here (e.g., ignore large binary blobs).
    return True


def _count_loc_for_commit(repo_path: Path, commit_hash: str) -> tuple[int, int]:
    """
    Return (total_code_loc, reviewed_code_loc) for a single commit.

    This function uses `git show --numstat` to get added/removed lines per file.
    We count only the "added" lines for code files as an approximation of
    "code introduced by this commit".
    """
    show_output = _run_git(
        repo_path,
        ["show", "--numstat", "--format=", commit_hash],
    )

    total = 0
    for line in show_output.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        try:
            added = int(parts[0])
            # removed = int(parts[1])  # not used
        except ValueError:
            # This happens for binary files ("-  -  path")
            continue

        file_path = parts[2]
        if not _is_code_file(file_path):
            continue

        total += added

    return total, total  # we decide "reviewed" or not outside


def compute_reviewedness(
    repo_path: str | Path | None,
) -> ReviewednessResult:
    """
    Compute the reviewedness metric for a local git repository.

    If repo_path is None or not a git repo, returns score -1.0.
    """
    if repo_path is None:
        return ReviewednessResult(
            score=-1.0,
            total_code_lines=0,
            reviewed_code_lines=0,
            repo_path=None,
            reason="No associated GitHub/Git repo provided",
        )

    repo = Path(repo_path)
    if not (repo / ".git").exists():
        return ReviewednessResult(
            score=-1.0,
            total_code_lines=0,
            reviewed_code_lines=0,
            repo_path=repo,
            reason="Provided path is not a git repository",
        )

    branch = _get_main_branch(repo)
    total_code = 0
    reviewed_code = 0

    for commit_hash, message in _iter_commits_with_messages(repo, branch):
        commit_total, commit_code = _count_loc_for_commit(repo, commit_hash)
        total_code += commit_total
        if _is_reviewed_commit(message):
            reviewed_code += commit_code

    if total_code == 0:
        return ReviewednessResult(
            score=-1.0,
            total_code_lines=0,
            reviewed_code_lines=0,
            repo_path=repo,
            reason="Repository has no measurable code changes",
        )

    score = reviewed_code / total_code
    return ReviewednessResult(
        score=score,
        total_code_lines=total_code,
        reviewed_code_lines=reviewed_code,
        repo_path=repo,
        reason="Reviewedness computed from git history using commit message heuristics",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute reviewedness metric for a git repo."
    )
    parser.add_argument("repo_path", help="Path to the local git repository")
    args = parser.parse_args()

    res = compute_reviewedness(args.repo_path)
    print(res)
