from fastapi.testclient import TestClient

from src.main import app
from src.services.storage import storage

client = TestClient(app)

def test_reset():
    response = client.delete("/reset")
    assert response.status_code == 200
    assert storage.list_packages() == []

def test_ingest_package():
    # Reset first
    client.delete("/reset")
    
    # Ingest a known good package (using a URL that should pass metrics if possible, or mocking)
    # Since we are using real metrics, we need a real URL.
    # Let's use a dummy URL and mock the metrics service if possible, or rely on the real one.
    # The real one requires network and might be flaky or slow.
    # Ideally we should mock `compute_package_rating`.
    
    # For now, let's try to mock it in the test.
    from unittest.mock import patch

    from src.api.models import PackageRating
    
    with patch("src.api.routes.compute_package_rating") as mock_rate:
        mock_rate.return_value = PackageRating(
            BusFactor=1, BusFactorLatency=0,
            Correctness=1, CorrectnessLatency=0,
            RampUp=1, RampUpLatency=0,
            ResponsiveMaintainer=1, ResponsiveMaintainerLatency=0,
            LicenseScore=1, LicenseScoreLatency=0,
            GoodPinningPractice=1, GoodPinningPracticeLatency=0,
            PullRequest=1, PullRequestLatency=0,
            NetScore=1.0, NetScoreLatency=0,
            TreeScore=1.0, TreeScoreLatency=0,
            Reproducibility=1.0, ReproducibilityLatency=0
        )
        
        payload = {
            "url": "https://github.com/test/repo",
            "jsprogram": "console.log('test')"
        }
        response = client.post("/package", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["name"] == "test/repo"
        assert data["metadata"]["id"] is not None
        
        # Verify it's in storage
        pkg = storage.get_package(data["metadata"]["id"])
        assert pkg is not None
        assert pkg.data.url == "https://github.com/test/repo"
        assert data["metadata"]["type"] == "code" # Default for /package

def test_rate_package():
    # Setup
    client.delete("/reset")
    from unittest.mock import patch

    from src.api.models import PackageRating
    
    with patch("src.api.routes.compute_package_rating") as mock_rate:
        mock_rate.return_value = PackageRating(
            BusFactor=0.8, BusFactorLatency=10,
            Correctness=0.9, CorrectnessLatency=10,
            RampUp=0.7, RampUpLatency=10,
            ResponsiveMaintainer=0.6, ResponsiveMaintainerLatency=10,
            LicenseScore=1.0, LicenseScoreLatency=10,
            GoodPinningPractice=1.0, GoodPinningPracticeLatency=10,
            PullRequest=0.5, PullRequestLatency=10,
            NetScore=0.85, NetScoreLatency=70,
            TreeScore=0.5, TreeScoreLatency=10,
            Reproducibility=0.5, ReproducibilityLatency=10
        )
        
        # Ingest first
        payload = {"url": "https://github.com/test/repo"}
        res_ingest = client.post("/package", json=payload)
        pkg_id = res_ingest.json()["metadata"]["id"]
        
        # Rate
        response = client.get(f"/package/{pkg_id}/rate")
        assert response.status_code == 200
        data = response.json()
        assert data["NetScore"] == 0.85

def test_get_packages_empty():
    client.delete("/reset")
    response = client.post("/packages", json=[])
    assert response.status_code == 200
    assert response.json() == []

def test_upload_package():
    # Test uploading a package via Content (Base64)
    client.delete("/reset")
    from unittest.mock import patch

    from src.api.models import PackageRating
    
    with patch("src.api.routes.compute_package_rating") as mock_rate:
        mock_rate.return_value = PackageRating(
            BusFactor=1, BusFactorLatency=0,
            Correctness=1, CorrectnessLatency=0,
            RampUp=1, RampUpLatency=0,
            ResponsiveMaintainer=1, ResponsiveMaintainerLatency=0,
            LicenseScore=1, LicenseScoreLatency=0,
            GoodPinningPractice=1, GoodPinningPracticeLatency=0,
            PullRequest=1, PullRequestLatency=0,
            NetScore=1.0, NetScoreLatency=0,
            TreeScore=1.0, TreeScoreLatency=0,
            Reproducibility=1.0, ReproducibilityLatency=0
        )
        
        payload = {
            "content": "UEsDBAoAAAAAA...", # Dummy zip content
            "jsprogram": "console.log('test')"
        }
        response = client.post("/package", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["name"] == "UploadedPackage"
        assert data["metadata"]["id"] is not None
        
        # Verify storage
        pkg = storage.get_package(data["metadata"]["id"])
        assert pkg.data.content == payload["content"]
        assert data["metadata"]["type"] == "code"

def test_delete_package_not_found():
    client.delete("/reset")
    response = client.delete("/package/non-existent")
    assert response.status_code == 404

def test_update_package():
    # Not implemented yet
    response = client.put("/package/123", json={"metadata": {"name": "n", "version": "v", "id": "i"}, "data": {}})
    assert response.status_code == 501

def test_authenticate():
    payload = {"User": {"name": "admin", "isAdmin": True}, "Secret": "password"}
    response = client.put("/authenticate", json=payload)
    assert response.status_code == 200
    assert "bearerToken" in response.json()

def test_search_by_regex():
    client.delete("/reset")
    # Ingest one
    from unittest.mock import patch

    from src.api.models import PackageRating
    with patch("src.api.routes.compute_package_rating") as mock_rate:
         mock_rate.return_value = PackageRating(
            BusFactor=1, BusFactorLatency=0, Correctness=1, CorrectnessLatency=0,
            RampUp=1, RampUpLatency=0, ResponsiveMaintainer=1, ResponsiveMaintainerLatency=0,
            LicenseScore=1, LicenseScoreLatency=0, GoodPinningPractice=1, GoodPinningPracticeLatency=0,
            PullRequest=1, PullRequestLatency=0, NetScore=1.0, NetScoreLatency=0,
            TreeScore=1.0, TreeScoreLatency=0, Reproducibility=1.0, ReproducibilityLatency=0
         )
         client.post("/package", json={"url": "https://github.com/test/regex", "jsprogram": "js"})
    
    # Search
    response = client.post("/package/byRegEx", json={"RegEx": "test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["name"] == "test/regex"

def test_rate_package_no_url():
    # Test rating a package that has no URL (e.g. uploaded content only)
    client.delete("/reset")
    # Upload content-only package
    payload = {
        "content": "UEsDBAoAAAAAA...", 
        "jsprogram": "console.log('test')"
    }
    # Mock compute_package_rating to avoid error during ingest (though this is upload)
    # Upload path doesn't call compute_package_rating.
    
    res = client.post("/package", json=payload)
    pkg_id = res.json()["metadata"]["id"]
    
    # Rate it
    response = client.get(f"/package/{pkg_id}/rate")
    assert response.status_code == 200
    data = response.json()
    # Expect all 0s
    assert data["NetScore"] == 0

def test_upload_model():
    client.delete("/reset")
    
    # Mock compute_package_rating if needed (though upload path might not use it if content is provided)
    # But wait, upload_package calls compute_package_rating only for ingest (URL).
    # If we upload content, it doesn't call it.
    
    payload = {
        "content": "UEsDBAoAAAAAA...", 
        "jsprogram": "console.log('test')"
    }
    response = client.post("/artifact/model", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["metadata"]["type"] == "model"

def test_query_filtering():
    client.delete("/reset")
    # Upload a model
    client.post("/artifact/model", json={"content": "UEsDBAoAAAAAA...", "jsprogram": "js"})
    # Upload a dataset
    client.post("/artifact/dataset", json={"content": "UEsDBAoAAAAAA...", "jsprogram": "js"})
    
    # Query for model
    query = [{"name": "*", "types": ["model"]}]
    response = client.post("/packages", json=query)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "model"
    
    # Query for dataset
    query = [{"name": "*", "types": ["dataset"]}]
    response = client.post("/packages", json=query)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "dataset"

def test_get_history_by_name():
    client.delete("/reset")
    # Upload a package
    client.post("/artifact/code", json={"content": "UEsDBAoAAAAAA...", "jsprogram": "js", "name": "history-test"})
    
    # Get history
    response = client.get("/package/byName/history-test")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["PackageMetadata"]["name"] == "history-test"
    assert data[0]["Action"] == "CREATE"
