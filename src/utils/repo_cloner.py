import logging
import os
import shutil
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from git import GitCommandError, Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    class GitCommandError(Exception):
        pass
    class Repo:
        pass
    logger.warning("Git executable not found. Cloning will be disabled.")

def clone_repo_to_temp(repo_url: str) -> str:
    """
    Clones a git repository to a temporary directory.
    Returns the path to the temporary directory.
    """
    if not GIT_AVAILABLE:
        logger.warning(f"Git not available. Skipping clone for {repo_url}")
        # Create an empty temp dir to satisfy return type, but it will be empty
        return tempfile.mkdtemp()

    temp_dir = None # Initialize temp_dir to None
    try:
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Cloning {repo_url} to {temp_dir}")
        Repo.clone_from(repo_url, temp_dir, depth=1)
        return temp_dir
    except GitCommandError as e:
        logger.error(f"Error cloning repository: {e}")
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during cloning: {e}")
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise e
