"""
Unit tests for Sidecar API adapter download endpoints.

Tests the universal wrapper functionality that enables zero-touch integration
by dynamically serving framework adapters.
"""

import pytest
import tempfile
import tarfile
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from services.sidecar_api import SidecarAPIServer
from core.sidecar.observer import SidecarObserver
from core.sidecar.sampler import Sampler


@pytest.fixture
def mock_observer():
    """Create a mock observer for testing"""
    sampler = Sampler(default_rate=1.0)
    observer = SidecarObserver(sampler=sampler)
    observer._running = True
    return observer


@pytest.fixture
def api_client(mock_observer):
    """Create test client for Sidecar API"""
    server = SidecarAPIServer(observer=mock_observer, host="localhost", port=8765)
    return TestClient(server.app)


class TestAdapterListEndpoint:
    """Tests for GET /adapters endpoint"""
    
    def test_list_adapters_success(self, api_client):
        """Test successful adapter listing"""
        response = api_client.get("/adapters")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "adapters" in data
        assert "total" in data
        assert isinstance(data["adapters"], list)
        assert data["total"] > 0
        
        # Verify adapter structure
        if data["adapters"]:
            adapter = data["adapters"][0]
            assert "name" in adapter
            assert "description" in adapter
            assert "download_url" in adapter
            assert adapter["download_url"].startswith("/adapters/")
    
    def test_list_adapters_includes_all_frameworks(self, api_client):
        """Test that all expected frameworks are listed"""
        response = api_client.get("/adapters")
        data = response.json()
        
        adapter_names = [a["name"] for a in data["adapters"]]
        
        # Verify critical frameworks are present
        expected_frameworks = ["robot", "pytest", "cypress", "restassured_java"]
        for framework in expected_frameworks:
            assert framework in adapter_names, f"Framework {framework} not found in adapter list"
    
    def test_list_adapters_excludes_hidden_dirs(self, api_client):
        """Test that hidden directories are excluded"""
        response = api_client.get("/adapters")
        data = response.json()
        
        adapter_names = [a["name"] for a in data["adapters"]]
        
        # Should not include directories starting with _
        for name in adapter_names:
            assert not name.startswith("_")


class TestAdapterDownloadEndpoint:
    """Tests for GET /adapters/{framework} endpoint"""
    
    def test_download_robot_adapter(self, api_client):
        """Test downloading Robot Framework adapter"""
        response = api_client.get("/adapters/robot")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/gzip"
        assert "robot-adapter.tar.gz" in response.headers.get("content-disposition", "")
        
        # Verify it's a valid tar.gz
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        try:
            with tarfile.open(tmp_path, 'r:gz') as tar:
                members = tar.getmembers()
                assert len(members) > 0
                
                # Should contain robot adapter files
                member_names = [m.name for m in members]
                assert any('robot' in name.lower() for name in member_names)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_download_pytest_adapter(self, api_client):
        """Test downloading Pytest adapter"""
        response = api_client.get("/adapters/pytest")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/gzip"
    
    def test_download_cypress_adapter(self, api_client):
        """Test downloading Cypress adapter"""
        response = api_client.get("/adapters/cypress")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/gzip"
    
    def test_download_restassured_adapter(self, api_client):
        """Test downloading REST Assured adapter"""
        response = api_client.get("/adapters/restassured_java")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/gzip"
    
    def test_download_nonexistent_adapter(self, api_client):
        """Test downloading non-existent adapter returns 404"""
        response = api_client.get("/adapters/nonexistent_framework")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_download_adapter_tar_structure(self, api_client):
        """Test that downloaded adapter has correct structure"""
        response = api_client.get("/adapters/robot")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        try:
            with tarfile.open(tmp_path, 'r:gz') as tar:
                members = tar.getmembers()
                
                # Should have Python files
                py_files = [m for m in members if m.name.endswith('.py')]
                assert len(py_files) > 0, "No Python files in adapter"
                
                # Should not have .pyc files
                pyc_files = [m for m in members if m.name.endswith('.pyc')]
                assert len(pyc_files) == 0, "Should not include .pyc files"
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestConfigEndpoint:
    """Tests for GET /config endpoint"""
    
    def test_config_includes_frameworks(self, api_client):
        """Test config endpoint lists supported frameworks"""
        response = api_client.get("/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "frameworks_supported" in data
        assert isinstance(data["frameworks_supported"], list)
        assert len(data["frameworks_supported"]) > 0
        
        # Should be sorted
        frameworks = data["frameworks_supported"]
        assert frameworks == sorted(frameworks)
    
    def test_config_includes_features(self, api_client):
        """Test config includes feature flags"""
        response = api_client.get("/config")
        data = response.json()
        
        assert "features" in data
        features = data["features"]
        
        # Verify universal wrapper features are enabled
        assert features.get("adapter_download") is True
        assert features.get("universal_wrapper") is True
        assert features.get("batch_events") is True
        assert features.get("enhanced_logging") is True


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""
    
    def test_universal_wrapper_workflow(self, api_client):
        """Test complete universal wrapper workflow"""
        # Step 1: Check health
        health_response = api_client.get("/health")
        assert health_response.status_code == 200
        
        # Step 2: List adapters
        list_response = api_client.get("/adapters")
        assert list_response.status_code == 200
        adapters = list_response.json()["adapters"]
        assert len(adapters) > 0
        
        # Step 3: Download adapter
        framework = adapters[0]["name"]
        download_response = api_client.get(f"/adapters/{framework}")
        assert download_response.status_code == 200
        
        # Step 4: Verify tar is valid
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp:
            tmp.write(download_response.content)
            tmp_path = tmp.name
        
        try:
            with tarfile.open(tmp_path, 'r:gz') as tar:
                assert len(tar.getmembers()) > 0
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_all_listed_adapters_downloadable(self, api_client):
        """Test that all listed adapters can be downloaded"""
        # Get adapter list
        list_response = api_client.get("/adapters")
        adapters = list_response.json()["adapters"]
        
        # Try downloading each adapter
        for adapter in adapters:
            framework = adapter["name"]
            response = api_client.get(f"/adapters/{framework}")
            assert response.status_code == 200, f"Failed to download {framework}"
            assert response.headers["content-type"] == "application/gzip"


class TestErrorHandling:
    """Tests for error conditions"""
    
    def test_adapter_download_with_invalid_characters(self, api_client):
        """Test adapter download with invalid framework name"""
        response = api_client.get("/adapters/../../../etc/passwd")
        assert response.status_code == 404
    
    def test_adapter_list_when_adapters_missing(self, api_client, monkeypatch):
        """Test adapter list when adapters directory doesn't exist"""
        # Mock Path.exists to return False
        with patch('pathlib.Path.exists', return_value=False):
            response = api_client.get("/adapters")
            assert response.status_code == 200
            data = response.json()
            assert data["adapters"] == []
            assert data["total"] == 0


class TestPerformance:
    """Performance tests"""
    
    def test_adapter_download_response_time(self, api_client):
        """Test adapter download completes within reasonable time"""
        import time
        
        start = time.time()
        response = api_client.get("/adapters/robot")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Download took {elapsed:.2f}s, should be < 5s"
    
    def test_multiple_concurrent_downloads(self, api_client):
        """Test handling multiple concurrent adapter downloads"""
        import concurrent.futures
        
        def download_adapter(framework):
            return api_client.get(f"/adapters/{framework}")
        
        frameworks = ["robot", "pytest", "cypress"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(download_adapter, fw) for fw in frameworks]
            responses = [f.result() for f in futures]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
