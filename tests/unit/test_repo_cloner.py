from src.utils.repo_cloner import clone_repo_to_temp
from git import GitCommandError

def test_clone_repo_failure(mocker):
    """
    Tests that clone_repo_to_temp returns None when GitPython fails.
    """
    # Mock the Repo.clone_from function to raise a GitCommandError,
    # simulating a failed clone.
    mocker.patch('git.Repo.clone_from', side_effect=GitCommandError("clone", "failed"))
    
    # Also mock shutil.rmtree to prevent it from trying to delete a real directory
    mock_rmtree = mocker.patch('shutil.rmtree')

    # Call the function with a fake URL
    result = clone_repo_to_temp("https://invalid/repo.git")

    # Assert that the function returned None as expected
    assert result is None
    # Assert that the cleanup function (shutil.rmtree) was called
    mock_rmtree.assert_called_once()
    
