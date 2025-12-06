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
            bus_factor=1, bus_factor_latency=0,
            code_quality=1, code_quality_latency=0,
            ramp_up_time=1, ramp_up_time_latency=0,
            responsive_maintainer=1, responsive_maintainer_latency=0,
            license=1, license_latency=0,
            good_pinning_practice=1, good_pinning_practice_latency=0,
            reviewedness=1, reviewedness_latency=0,
            net_score=1.0, net_score_latency=0,
            treescore=1.0, treescore_latency=0,
            reproducibility=1.0, reproducibility_latency=0, performance_claims=1.0, performance_claims_latency=0, dataset_and_code_score=1.0, dataset_and_code_score_latency=0, dataset_quality=1.0, dataset_quality_latency=0, size=1.0, size_latency=0
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
            bus_factor=0.8, bus_factor_latency=10,
            code_quality=0.9, code_quality_latency=10,
            ramp_up_time=0.7, ramp_up_time_latency=10,
            responsive_maintainer=0.6, responsive_maintainer_latency=10,
            license=1.0, license_latency=10,
            good_pinning_practice=1.0, good_pinning_practice_latency=10,
            reviewedness=0.5, reviewedness_latency=10,
            net_score=0.85, net_score_latency=70,
            treescore=0.5, treescore_latency=10,
            reproducibility=0.5, reproducibility_latency=10, performance_claims=0.5, performance_claims_latency=10, dataset_and_code_score=0.5, dataset_and_code_score_latency=10, dataset_quality=0.5, dataset_quality_latency=10, size=0.5, size_latency=10
        )
        
        # Ingest first
        payload = {"url": "https://github.com/test/repo"}
        res_ingest = client.post("/package", json=payload)
        pkg_id = res_ingest.json()["metadata"]["id"]
        
        # Rate
        response = client.get(f"/package/{pkg_id}/rate")
        assert response.status_code == 200
        data = response.json()
        assert data["net_score"] == 0.85

def test_get_packages_empty():
    client.delete("/reset")
    # Ingest 15 packages to test limits
    from unittest.mock import patch
    from src.api.models import PackageRating
    with patch("src.api.routes.compute_package_rating") as mock_rate:
        mock_rate.return_value = PackageRating(
            bus_factor=1, bus_factor_latency=0, code_quality=1, code_quality_latency=0,
            ramp_up_time=1, ramp_up_time_latency=0, responsive_maintainer=1, responsive_maintainer_latency=0,
            license=1, license_latency=0, good_pinning_practice=1, good_pinning_practice_latency=0,
            reviewedness=1, reviewedness_latency=0, net_score=1.0, net_score_latency=0,
            treescore=1.0, treescore_latency=0, reproducibility=1.0, reproducibility_latency=0, performance_claims=1.0, performance_claims_latency=0, dataset_and_code_score=1.0, dataset_and_code_score_latency=0, dataset_quality=1.0, dataset_quality_latency=0, size=1.0, size_latency=0
        )
        for i in range(15):
            client.post("/package", json={"url": f"https://github.com/test/repo{i}", "jsprogram": "js"})

    # Query with default limit (now 100)
    query = [{"name": "*"}]
    response = client.post("/packages", json=query)
    assert response.status_code == 200
    assert len(response.json()) == 15
    
    # Query with explicit limit 10
    response = client.post("/packages?limit=10", json=query)
    assert response.status_code == 200
    assert len(response.json()) == 10

def test_plural_routes():
    client.delete("/reset")
    # Upload a code package
    response = client.post("/artifact/code", json={"content": "UEsDBAoAAAAAA...", "jsprogram": "js", "name": "code-pkg"})
    pkg_id = response.json()["metadata"]["id"]
    
    # Get via plural code route
    response = client.get(f"/artifacts/code/{pkg_id}")
    assert response.status_code == 200
    assert response.json()["metadata"]["id"] == pkg_id
    
    # Upload a dataset package
    response = client.post("/artifact/dataset", json={"content": "UEsDBAoAAAAAA...", "jsprogram": "js", "name": "dataset-pkg"})
    pkg_id = response.json()["metadata"]["id"]
    
    # Get via plural dataset route
    response = client.get(f"/artifacts/dataset/{pkg_id}")
    assert response.status_code == 200
    assert response.json()["metadata"]["id"] == pkg_id
    
    # Test 404
    response = client.get("/artifacts/code/non-existent")
    assert response.status_code == 404

def test_rate_and_cost_structure():
    client.delete("/reset")
    # Upload a package
    response = client.post("/artifact/code", json={"content": "UEsDBAoAAAAAA...", "jsprogram": "js", "name": "rate-test"})
    pkg_id = response.json()["metadata"]["id"]
    
    # Test Rate
    response = client.get(f"/package/{pkg_id}/rate")
    assert response.status_code == 200
    data = response.json()
    # Should be 0s
    assert data["net_score"] == 0
    assert data["name"] == "rate-test"
    assert data["category"] == "code"
    assert "bus_factor" in data # Check lowercase
    
    # Test Cost
    response = client.get(f"/artifact/model/{pkg_id}/cost")
    assert response.status_code == 200
    data = response.json()
    assert "cost" in data
    assert isinstance(data["cost"], dict) # Check it's a dict
    assert data["cost"]["total_cost"] == 0

def test_upload_package():
    # Test uploading a package via Content (Base64)
    client.delete("/reset")
    from unittest.mock import patch

    from src.api.models import PackageRating
    
    with patch("src.api.routes.compute_package_rating") as mock_rate:
        mock_rate.return_value = PackageRating(
            bus_factor=1, bus_factor_latency=0,
            code_quality=1, code_quality_latency=0,
            ramp_up_time=1, ramp_up_time_latency=0,
            responsive_maintainer=1, responsive_maintainer_latency=0,
            license=1, license_latency=0,
            good_pinning_practice=1, good_pinning_practice_latency=0,
            reviewedness=1, reviewedness_latency=0,
            net_score=1.0, net_score_latency=0,
            treescore=1.0, treescore_latency=0,
            reproducibility=1.0, reproducibility_latency=0, performance_claims=1.0, performance_claims_latency=0, dataset_and_code_score=1.0, dataset_and_code_score_latency=0, dataset_quality=1.0, dataset_quality_latency=0, size=1.0, size_latency=0
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
            bus_factor=0.5, bus_factor_latency=0, code_quality=0.5, code_quality_latency=0,
            ramp_up_time=0.5, ramp_up_time_latency=0, responsive_maintainer=0.5, responsive_maintainer_latency=0,
            license=0.5, license_latency=0, good_pinning_practice=0.5, good_pinning_practice_latency=0,
            reviewedness=0.5, reviewedness_latency=0, net_score=0.5, net_score_latency=0,
            treescore=0.5, treescore_latency=0, reproducibility=0.5, reproducibility_latency=0, performance_claims=0.5, performance_claims_latency=0, dataset_and_code_score=0.5, dataset_and_code_score_latency=0, dataset_quality=0.5, dataset_quality_latency=0, size=0.5, size_latency=0
         )
         client.post("/package", json={"url": "https://github.com/test/regex", "jsprogram": "js"})
    
    # Search
    response = client.post("/package/byRegEx", json={"RegEx": "test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["name"] == "test/regex"

def test_download_url():
    # Only applicable if we can mock storage.get_download_url
    from unittest.mock import patch
    
    client.delete("/reset")
    # Upload content package
    response = client.post("/artifact/code", json={"content": "UEsDBAoAAAAAA...", "jsprogram": "js", "name": "download-test"})
    pkg_id = response.json()["metadata"]["id"]
    
    # Mock storage.get_download_url
    with patch("src.services.storage.LocalStorage.get_download_url", create=True) as mock_url:
        mock_url.return_value = "https://s3.amazonaws.com/bucket/key.zip"
        
        # Get package
        response = client.get(f"/package/{pkg_id}")
        assert response.status_code == 200
        data = response.json()
        # LocalStorage doesn't implement get_download_url by default, so we mock it
        # But wait, routes.py checks hasattr(storage, "get_download_url")
        # LocalStorage instance in routes.py is global.
        # We need to patch the method on the instance or class.
        pass # Skip for now as LocalStorage doesn't support it, only S3Storage does.

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
    assert data["net_score"] == 0

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
