import logging
from huggingface_hub import hf_hub_download
from bs4 import BeautifulSoup

logger = logging.getLogger("phase1_cli")

def find_github_url_from_hf(repo_id: str) -> str | None:
    """
    Downloads a model's README.md from Hugging Face and searches for a GitHub URL.
    """
    try:
        # Download the README file from the Hugging Face Hub
        readme_path = hf_hub_download(repo_id=repo_id, filename="README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Use BeautifulSoup to parse the HTML/Markdown content
        soup = BeautifulSoup(content, "html.parser")
        # Find all anchor tags (links)
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Return the first link that points to github.com
            if "github.com" in href:
                logger.info(f"Found GitHub link for {repo_id}: {href}")
                return href

        logger.warning(f"No GitHub link found in README for {repo_id}")
        return None
    except Exception as e:
        logger.error(f"Could not process README for {repo_id} to find GitHub link: {e}")
        return None