import tempfile
import shutil
import logging
from git import Repo, GitCommandError

logger = logging.getLogger("phase1_cli")

def clone_repo_to_temp(repo_url: str) -> str | None:
    """
    Clones a Git repository to a temporary directory.
    Returns the path to the temp directory or None if it fails.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        logger.info(f"Cloning {repo_url} to {temp_dir}...")
        # Use depth=1 for a shallow clone to save time and space
        Repo.clone_from(repo_url, temp_dir, depth=1)
        logger.info(f"Successfully cloned {repo_url}.")
        return temp_dir
    except GitCommandError as e:
        logger.error(f"Failed to clone repository {repo_url}: {e}")
        shutil.rmtree(temp_dir)  # Clean up the failed clone
        return None