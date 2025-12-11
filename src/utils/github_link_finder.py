import logging
import re

from huggingface_hub import hf_hub_download, model_info

logger = logging.getLogger("phase1_cli")

# Well-known model prefixes that map to specific GitHub repos
KNOWN_MODEL_REPOS = {
    "bert": "https://github.com/google-research/bert",
    "distilbert": "https://github.com/huggingface/transformers",
    "roberta": "https://github.com/pytorch/fairseq",
    "gpt2": "https://github.com/openai/gpt-2",
    "bart": "https://github.com/pytorch/fairseq",
    "t5": "https://github.com/google-research/text-to-text-transfer-transformer",
    "vit": "https://github.com/google-research/vision_transformer",
    "clip": "https://github.com/openai/CLIP",
    "llama": "https://github.com/facebookresearch/llama",
    "whisper": "https://github.com/openai/whisper",
    "stable-diffusion": "https://github.com/CompVis/stable-diffusion",
    "swin": "https://github.com/microsoft/Swin-Transformer",
}


def find_github_url_from_hf(repo_id: str) -> str | None:
    """
    Downloads a model's README.md from Hugging Face and searches for a GitHub URL.
    
    Falls back to well-known model repos if no GitHub link in README.
    """
    try:
        # First try to find GitHub link in README
        try:
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
        except Exception as e:
            logger.debug(f"Could not read README for {repo_id}: {e}")
        
        # Fallback: Check if model name matches known prefixes
        model_name_lower = repo_id.lower().split("/")[-1]  # Get just the model name part
        
        for prefix, github_url in KNOWN_MODEL_REPOS.items():
            if prefix in model_name_lower:
                logger.info(f"Using known repo for {repo_id} ({prefix}): {github_url}")
                return github_url
        
        # Last resort: Check if it's from a well-known organization
        org = repo_id.split("/")[0].lower() if "/" in repo_id else ""
        if org in ["google", "google-bert", "facebook", "meta-llama", "openai", "microsoft"]:
            # Default to transformers for HF-hosted well-known models
            logger.info(f"Using transformers repo for well-known org {org}")
            return "https://github.com/huggingface/transformers"
        
        logger.warning(f"No GitHub link found for {repo_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error finding GitHub URL for {repo_id}: {e}")
        return None
