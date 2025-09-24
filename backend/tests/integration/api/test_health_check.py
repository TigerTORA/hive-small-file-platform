"""
Integration tests for health check API
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client


class TestHealthCheckAPI:
    """Test cases for health check endpoints"""

    @pytest.mark.integration
    def test_root_endpoint(self, client):
        """Test root endpoint returns message"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Hive Small File Management Platform API" in data["message"]

    @pytest.mark.integration
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
