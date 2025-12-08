import io
import zipfile
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.services.metrics_service import compute_package_rating
from src.api.models import PackageRating

client = TestClient(app)

def create_dummy_zip():
    """Creates a dummy zip file in memory with a README.md"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("repo-main/README.md", "# Installation\n\nRun `pip install foo`\n\n```python\nimport foo\n```")
        z.writestr("repo-main/LICENSE", "MIT License")
    buffer.seek(0)
    return buffer.read()

def test_zip_download_fallback():
    """
    Test that compute_package_rating falls back to zip download when git is missing/fails,
    and computes metrics based on the downloaded content.
    """
    # Mock GIT_AVAILABLE to False in repo_cloner
    with patch("src.utils.repo_cloner.GIT_AVAILABLE", False):
        # Mock requests.get to return our dummy zip
        with patch("src.utils.repo_cloner.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = create_dummy_zip()
            mock_get.return_value = mock_response
            
            # Call compute_package_rating
            rating = compute_package_rating("https://github.com/test/repo")
            
            # Verify results
            # RampUp should be > 0 because of README content
            assert rating.ramp_up_time > 0
            # License should be 1.0 (MIT)
            assert rating.license == 1.0
            # BusFactor will be 0 because no git history
            assert rating.bus_factor == 0.0
            
            # Verify zip download was attempted
            mock_get.assert_called()
            # Check if ANY call was for the zip
            zip_calls = [args[0] for args, _ in mock_get.call_args_list if "archive/HEAD.zip" in args[0]]
            assert len(zip_calls) > 0, f"Zip download not attempted. Calls: {mock_get.call_args_list}"

def test_zip_download_with_git_failure():
    """
    Test that it falls back to zip download if git clone raises an exception.
    """
    with patch("src.utils.repo_cloner.GIT_AVAILABLE", True):
        with patch("src.utils.repo_cloner.Repo.clone_from", side_effect=Exception("Git clone failed")):
             with patch("src.utils.repo_cloner.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.content = create_dummy_zip()
                mock_get.return_value = mock_response
                
                rating = compute_package_rating("https://github.com/test/repo")
                
                assert rating.ramp_up_time > 0
                assert rating.license == 1.0
                
                mock_get.assert_called()
