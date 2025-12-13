import logging
import os
import shutil
import tempfile
import requests
import zipfile
import io

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
    logger.warning("Git executable not found. Cloning will be disabled, falling back to zip download.")

def download_repo_zip(repo_url: str) -> str:
    """
    Downloads a repository as a zip file and extracts it to a temporary directory.
    Supports GitHub URLs.
    """
    # Normalize URL
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    
    # Construct zip URL (assuming GitHub for now)
    # Try HEAD first, then main, then master
    branches = ["HEAD", "main", "master"]
    
    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token and not token.startswith("ghp_REPLACE"):
        headers["Authorization"] = f"token {token}"
    
    for branch in branches:
        zip_url = f"{url}/archive/refs/heads/{branch}.zip"
        if branch == "HEAD":
             zip_url = f"{url}/archive/HEAD.zip"
            
        logger.info(f"Attempting to download zip from {zip_url}")
    try:
        # Normalize URL
        url = repo_url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        
        # Construct zip URL (assuming GitHub for now)
        # Try HEAD first, then main, then master
        branches = ["HEAD", "main", "master"]
        
        headers = {}
        token = os.environ.get("GITHUB_TOKEN")
        if token and not token.startswith("ghp_REPLACE"):
            headers["Authorization"] = f"token {token}"
        
        response = None # Initialize response
        for branch in branches:
            zip_url = f"{url}/archive/refs/heads/{branch}.zip"
            if branch == "HEAD":
                 zip_url = f"{url}/archive/HEAD.zip"
                
            logger.info(f"Attempting to download zip from {zip_url}")
            
            try:
                response = requests.get(zip_url, headers=headers, stream=True, timeout=30)
                if response.status_code == 200:
                    break
            except Exception:
                continue
        else:
            # If loop finishes without break
            raise Exception(f"Could not download zip from {url} (tried HEAD, main, master)")

        response.raise_for_status()
            
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(temp_dir)
                
        # The zip usually contains a top-level directory (e.g., repo-main)
        # We want to return the path to that directory, or the temp_dir if flat
        entries = os.listdir(temp_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
            return os.path.join(temp_dir, entries[0])
        
        return temp_dir
            
    except Exception as e:
        logger.error(f"Failed to download zip: {e}")
        raise e

def clone_repo_to_temp(repo_url: str) -> str:
    """
    Clones a git repository to a temporary directory.
    Falls back to zip download if git is unavailable or fails.
    Returns the path to the temporary directory.
    """
    temp_dir = None
    
    # Try Git Clone first if available
    if GIT_AVAILABLE:
        try:
            temp_dir = tempfile.mkdtemp()
            logger.info(f"Cloning {repo_url} to {temp_dir}")
            # Use depth=100 to get enough commit history for bus_factor
            # (depth=1 only gets 1 commit which gives bus_factor=0)
            Repo.clone_from(repo_url, temp_dir, depth=100)
            return temp_dir
        except Exception as e:
            logger.warning(f"Git clone failed: {e}. Falling back to zip download.")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            # Fall through to zip download
    
    # Fallback to Zip Download
    try:
        return download_repo_zip(repo_url)
    except Exception as e:
        logger.error(f"Zip download also failed: {e}")
        raise e

