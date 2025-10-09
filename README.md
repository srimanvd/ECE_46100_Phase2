# Team Names:
Wesley Cameron Todd

Esau Cortez

Ethan Surber

Sam Brahim

# Metrics:

# Ramp_up_time: 

Start latency timer using time.perf_counter().

Look for a local README: if resource contains local_dir (a directory path), we check common README filenames (README.md, README.rst, README.txt, README) in that directory. If found, read it (UTF-8, errors replaced).

If no local README, attempt a best-effort remote fetch (only if requests is installed) for common repo hosts:

For GitHub: tries raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md for main and master.

For Hugging Face: tries similar raw/{branch}/README.md patterns.

Generic fallbacks are also attempted.

Note: this remote fetch is optional and will be skipped if requests is not present. (Testing can mock requests so no network is required.)

If no README content is available, return score 0.0 and the elapsed latency.

If README content is found, compute:

Length score from the word count using thresholds (0.0 / 0.1 / 0.25 / 0.4).

Installation score = +0.35 if README contains an "installation" heading or common install phrases (pip install, conda install, docker, etc.).

Code snippet score = +0.25 if README contains fenced code blocks (```) or indented code lines (4 leading spaces or tabs).

Sum weights (length + install + code) and cap at 1.0. Round score to 4 decimals.

Return (score, latency_ms) where latency_ms is integer milliseconds (rounded).

# License, Purdue GENAI Studio API key must be set as an evironment variable in your cmd or ps before usage

File-reading helpers (_read_local_file)

Prefer LICENSE file in the repo (most authoritative). If not found, the code will try README files. This makes behavior deterministic in grading when prepare_resource supplies a local clone.

Heuristic fallback (heuristic_license_score)

A lightweight rule-based mapping for environments with no API key or when the LLM fails. It maps common keyword signals to scores (MIT=1.0, Apache≈0.95, GPL lower). This ensures the metric never crashes and is testable offline.

LLM prompt builder (_build_prompt_for_license)

Asks the LLM to return only a JSON object with specific fields. This makes parsing easier and keeps the output structured.

Purdue API call (_call_purdue_genai)

Implements an OpenAI-compatible chat-completions POST to https://genai.rcac.purdue.edu/api/chat/completions using Authorization: Bearer <API_KEY> in the header. Example and header style are from RCAC docs. 
RCAC

Parsing (_extract_json_from_assistant)

Extracts the first JSON object found inside the assistant message (handles triple-backticks and single-quote issues). Helps robustness.

Public metric(resource)

Puts it all together: reads local LICENSE/README, tries LLM (if API key present), extracts compatibility_score, or falls back to heuristic. Returns (score_in_[0,1], latency_ms)

# Performance Claims:
Start latency timer using time.perf_counter().

The metric makes an API call to the Hugging Face Hub using the model's repository ID (e.g., google/gemma-2b).

It extracts the total number of downloads from the API response.

The raw download count is converted into a normalized score between 0.0 and 1.0 using a tiered system (e.g., >1M downloads = 1.0, >100k downloads = 0.8, etc.).

If the model cannot be found on the Hub or if there is a network error, the metric gracefully fails and returns a score of 0.0.

Return (score, latency_ms)
