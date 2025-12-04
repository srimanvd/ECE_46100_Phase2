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
            "URL": "https://github.com/test/repo",
            "JSProgram": "console.log('test')"
        }
        response = client.post("/package", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["Name"] == "test/repo"
        assert data["ID"] is not None
        
        # Verify it's in storage
        pkg = storage.get_package(data["ID"])
        assert pkg is not None
        assert pkg.data.URL == "https://github.com/test/repo"

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
        payload = {"URL": "https://github.com/test/repo"}
        res_ingest = client.post("/package", json=payload)
        pkg_id = res_ingest.json()["ID"]
        
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
            "Content": "UEsDBAoAAAAAA...", # Dummy zip content
            "JSProgram": "console.log('test')"
        }
        response = client.post("/package", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["Name"] == "UploadedPackage"
        assert data["ID"] is not None
        
        # Verify storage
        pkg = storage.get_package(data["ID"])
        assert pkg.data.Content == payload["Content"]

def test_delete_package_not_found():
    client.delete("/reset")
    response = client.delete("/package/non-existent")
    assert response.status_code == 404

def test_update_package():
    # Not implemented yet
    response = client.put("/package/123", json={"metadata": {"Name": "n", "Version": "v", "ID": "i"}, "data": {}})
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
         client.post("/package", json={"URL": "https://github.com/test/regex", "JSProgram": "js"})
    
    # Search
    response = client.post("/package/byRegEx", json={"RegEx": "test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["Name"] == "test/regex"

def test_rate_package_no_url():
    # Test rating a package that has no URL (e.g. uploaded content only)
    client.delete("/reset")
    # Upload content-only package
    payload = {
        "Content": "UEsDBAoAAAAAA...", 
        "JSProgram": "console.log('test')"
    }
    # Mock compute_package_rating to avoid error during ingest (though this is upload)
    # Upload path doesn't call compute_package_rating.
    
    res = client.post("/package", json=payload)
    pkg_id = res.json()["ID"]
    
    # Rate it
    response = client.get(f"/package/{pkg_id}/rate")
    assert response.status_code == 200
    data = response.json()
    # Expect all 0s
    assert data["NetScore"] == 0
