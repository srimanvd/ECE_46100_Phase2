import logging
import re

from huggingface_hub import hf_hub_download

logger = logging.getLogger("phase1_cli")


def find_github_url_from_hf(repo_id: str) -> str | None:
    """
    Downloads a model's README.md from Hugging Face and searches for a GitHub URL.
    
    Properly parses both Markdown links [text](url) and raw GitHub URLs.
    """
    try:
        # Download the README file from the Hugging Face Hub
        readme_path = hf_hub_download(repo_id=repo_id, filename="README.md")
        with open(readme_path, encoding="utf-8") as f:
            content = f.read()

        # Pattern 1: Markdown links [text](url)
        markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(markdown_link_pattern, content):
            url = match.group(2)
            if "github.com" in url:
                logger.info(f"Found GitHub link (markdown) for {repo_id}: {url}")
                return url

        # Pattern 2: Raw GitHub URLs (not in markdown format)
        raw_url_pattern = r'https?://github\.com/[^\s\)\"\'<>]+'
        for match in re.finditer(raw_url_pattern, content):
            url = match.group(0).rstrip('.,;:!')
            logger.info(f"Found GitHub link (raw) for {repo_id}: {url}")
            return url

        logger.warning(f"No GitHub link found in README for {repo_id}")
        return None
    except Exception as e:
        logger.error(f"Could not process README for {repo_id} to find GitHub link: {e}")
        return None
