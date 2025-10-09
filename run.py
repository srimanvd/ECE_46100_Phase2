#!/usr/bin/env python3

# SWE 45000, PIN FALL 2025
# TEAM 4
# PHASE 1 PROJECT

# DISCLAIMER: This file contains code either partially or entirely written by
# Artificial Intelligence.
"""
Executable CLI 'run' for Phase 1.

Usage:
  ./run install        -> installs dependencies from requirements.txt
  ./run test           -> runs test suite
  ./run URL_FILE       -> processes newline-delimited URLs and prints NDJSON
"""
from __future__ import annotations # Allows annotations (like return types) to be postponed and interpreted as strings

# ----------------------------
# Standard library imports
# ----------------------------
import argparse      # for parsing command line arguments
import importlib     # for dynamic module importing
import json          # for encoding/decoding JSON
import logging       # for logging info/errors
import os            # for environment variables & file operations
import pkgutil       # for discovering Python modules
import subprocess    # for running external processes
import sys           # for system-specific functions
import time
import shutil
import stat


from concurrent.futures import ThreadPoolExecutor, as_completed  # for parallel tasks
from pathlib import Path       # for safer path operations
from typing import Any, Dict, List, Tuple, Callable  # type hints

# ----------------------------
# Logging setup (reads env)
# ----------------------------
LOG_FILE = os.environ.get("LOG_FILE") # Location of the log file
try:
    LOG_LEVEL_ENV = int(os.environ.get("LOG_LEVEL", "0")) # Read log level (0,1,2)
except ValueError:
    LOG_LEVEL_ENV = 0

# Map numeric env value -> actual logging level
_log_level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}.get(LOG_LEVEL_ENV, logging.WARNING)

# Configure logging: either to a file or to stderr
if LOG_FILE:
    logging.basicConfig(filename=LOG_FILE, level=_log_level, format="%(asctime)s %(levelname)s %(message)s")
else:
    logging.basicConfig(stream=sys.stderr, level=_log_level, format="%(asctime)s %(levelname)s %(message)s")

logger = logging.getLogger("phase1_cli") # CLI tool named logger

def remove_readonly(func, path, excinfo):
    """Error handler for shutil.rmtree that removes read-only permissions."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

# ----------------------------
# Install / Test handlers
# ----------------------------
def run_subprocess(cmd: List[str]) -> int: # cmd is a variable of type: List[string], and (-> int), means return type int
    """Run a subprocess command and return exit code."""
    try:
        result = subprocess.run(cmd, check=False) 
        return result.returncode
    except Exception as exc:  # safety net
        logger.error("Subprocess failed: %s", exc)
        return 1


def handle_install() -> int:
    """Install dependencies from requirements.txt."""
    req = Path("requirements.txt")
    if not req.exists(): # if no requirements.txt, then do nothing
        logger.info("No requirements.txt found; nothing to install.")
        return 0
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req)]
    rc = run_subprocess(cmd)
    if rc != 0:
        logger.error("Dependency installation failed (exit %d)", rc)
    return rc


def handle_test() -> int:
    """Run tests with pytest + coverage if available."""
    try:
        # 1. Run pytest (quiet mode: -q). This executes the test suite.
        rc = run_subprocess([sys.executable, "-m", "pytest", "-q"])

        # 2. Run pytest again, this time under coverage measurement.
        #    "coverage run -m pytest" records line coverage data.
        cov_rc = run_subprocess([sys.executable, "-m", "coverage", "run", "-m", "pytest"])

        if cov_rc == 0:
            # 3. If coverage ran successfully, generate a coverage report.
            #    capture_output=True -> we store the stdout to parse later.
            proc = subprocess.run([sys.executable, "-m", "coverage", "report", "-m"],
                                  capture_output=True, text=True)

            # 4. Split stdout into lines, removing any empty ones.
            lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]

            # 5. Initialize coverage percent as "0" in case parsing fails.
            coverage_percent = "0"

            # 6. If there’s at least one line in the report,
            #    extract the last line (summary row of coverage output).
            if lines:
                last = lines[-1]
                parts = last.split()

                # 7. The last column in the summary usually has coverage like "85%".
                #    If so, strip the "%" and store just the number.
                if parts and parts[-1].endswith("%"):
                    coverage_percent = parts[-1].rstrip("%")

            # 8. Print test results (X/Y is placeholder, coverage% is real).
            print(f"X/Y test cases passed. {coverage_percent}% line coverage achieved.")

            # 9. Return 0 if pytest passed (rc == 0), else return 1 for failure.
            return 0 if rc == 0 else 1
        else:
            # 10. If coverage run failed, print fallback message with 0%.
            print("X/Y test cases passed. 0% line coverage achieved.")
            return 1

    except FileNotFoundError:
        # 11. If pytest or coverage tools are missing, warn the user.
        logger.warning("pytest or coverage not installed.")
        print("0/0 test cases passed. 0% line coverage achieved.")
        return 1


# ----------------------------
# URL classification
# ----------------------------
def classify_url(url: str) -> str:
    """
    Classify URL into one of: MODEL | DATASET | CODE.

    Rules:
      - HuggingFace dataset pages -> DATASET
      - Other HuggingFace pages (models, spaces, etc.) -> MODEL
      - Git hosts (GitHub/GitLab/Bitbucket) -> CODE
      - Everything else -> CODE
    """
    u = (url or "").strip().lower()
    if not u:
        return "CODE"

    # HuggingFace first
    if "huggingface.co" in u:
        if "huggingface.co/datasets/" in u or "/datasets/" in u:
            return "DATASET"
        return "MODEL"

    # Git hosting -> treat as code
    if "github.com" in u or "gitlab.com" in u or "bitbucket.org" in u:
        return "CODE"

    return "CODE"



# ----------------------------
# Dynamic Metric Loader
# ----------------------------
def load_metrics() -> Dict[str, Callable[[Dict[str, Any]], Tuple[float, int]]]:
    """
    Import all metric modules from src/metrics.
    Each must define: metric(resource) -> (score, latency_ms).
    """
    metrics_pkg = "src.metrics"
    metrics: Dict[str, Callable] = {}
    try:
        package = importlib.import_module(metrics_pkg) # Import src.metrics package
    except ModuleNotFoundError:
        logger.error("Could not find metrics package: %s", metrics_pkg)
        return metrics
        
    # Discover all modules inside src.metrics
    for _, mod_name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if is_pkg:
            continue
        module = importlib.import_module(mod_name) # Import each module dynamically
        if hasattr(module, "metric"): # Then check if it has a metric() function
            metric_name = mod_name.split(".")[-1]
            metrics[metric_name] = getattr(module, "metric") # Store in dict
    return metrics


# ----------------------------
# Metric computation
# ----------------------------
def compute_metrics_for_model(resource: Dict[str, Any]) -> Dict[str, Any]:
    # Load all metric functions dynamically
    metrics = load_metrics()
    out: Dict[str, Any] = {
        "name": resource.get("name", "unknown"),
        "category": "MODEL",
    }

    results: Dict[str, Tuple[float, int]] = {}
    # Run each metric function on the resource
    for name, func in metrics.items():
        try:
            score, latency = func(resource) # Each metric returns (score, latency)
            score = float(max(0.0, min(1.0, score))) # Clamp score between 0 and 1
        except Exception as e:
            logger.exception("Metric %s failed on %s: %s", name, resource.get("url"), e)
            score, latency = 0.0, 0
        results[name] = (score, latency)

    # Flatten results into output dictionary
    for name, (score, latency) in results.items():
        if name == "size_score":
            # Special handling: same score for multiple hardware
            out[name] = {
                "raspberry_pi": score,
                "jetson_nano": score,
                "desktop_pc": score,
                "aws_server": score,
            }
        else:
            out[name] = score
        out[f"{name}_latency"] = latency

    # Net score = average (placeholder until team defines weights), We also compute total latency
    net_score = sum(val for val, _ in results.values()) / max(1, len(results))
    net_latency = sum(lat for _, lat in results.values())
    out["net_score"] = round(net_score, 4)
    out["net_score_latency"] = net_latency

    return out


# ----------------------------
# URL File Processing
# ----------------------------
def process_url_file(path_str: str) -> int:
    """Read URL file, find/clone repos, run metrics, and output NDJSON results."""
    from src.utils.repo_cloner import clone_repo_to_temp
    from src.utils.github_link_finder import find_github_url_from_hf
    p = Path(path_str)
    if not p.exists():
        logger.error("URL file not found: %s", path_str)
        print(f"Error: URL file not found: {path_str}", file=sys.stderr)
        return 1

    urls: List[str] = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not urls:
        logger.info("URL file empty.")
        return 0
    
    resources = [
        {
            "url": u,
            "category": classify_url(u),
            "name": (
                "/".join(u.rstrip('/').split('/')[-2:]) if "github.com" in u
                else u.split('huggingface.co/')[-1].rstrip('/')
            )
        }
        for u in urls
    ]
    models = [r for r in resources if r["category"] == "MODEL"]

    for r in models:
        repo_to_clone = None
        if "github.com" in r['url']:
            repo_to_clone = r['url']
        elif "huggingface.co" in r['url']:
            repo_to_clone = find_github_url_from_hf(r['name'])

        if repo_to_clone:
            r['local_path'] = clone_repo_to_temp(repo_to_clone)
        else:
            r['local_path'] = None

    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as exe:
        futures = {exe.submit(compute_metrics_for_model, r): r for r in models}
        for fut in as_completed(futures):
            try:
                result = fut.result()
                print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
                sys.stdout.flush()
            except Exception as exc:
                logger.exception("Failed to compute metrics: %s", exc)
            finally:
                resource_done = futures[fut]
                if resource_done.get('local_path'):
                    logger.info(f"Cleaning up temp directory: {resource_done['local_path']}")
                    shutil.rmtree(resource_done['local_path'], onerror=remove_readonly)
            
    return 0


# ----------------------------
# CLI Entrypoint
# ----------------------------
def main(argv: List[str] | None = None) -> int:
    # Setup command line parser
    parser = argparse.ArgumentParser(prog="run", description="Phase 1 CLI for trustworthy model reuse")
    parser.add_argument("arg", nargs="?", help="install | test | URL_FILE")
    args = parser.parse_args(argv)
    
    # If no arguments -> show help
    if args.arg is None:
        parser.print_help()
        return 1

    # Handle install/test/file
    if args.arg == "install":
        return handle_install()
    if args.arg == "test":
        return handle_test()

    # Otherwise, treat it as a file
    return process_url_file(args.arg)

# If run directly, call main() and exit with this code
if __name__ == "__main__":
    sys.exit(main())
