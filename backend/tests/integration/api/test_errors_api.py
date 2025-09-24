"""
Integration tests for Errors API
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client


class TestErrorsAPI:
    """Test cases for error handling API endpoints"""

    @pytest.mark.integration
    def test_test_error_endpoint(self, client):
        """Test the test error endpoint"""
        response = client.get("/api/v1/errors/test-error")

        # Should return 500 error as designed
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Test error captured by Sentry" in data["detail"]

    @pytest.mark.integration
    def test_test_manual_error_endpoint(self, client):
        """Test the manual error endpoint"""
        response = client.get("/api/v1/errors/test-manual-error")

        # Should return success with message
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Manual error message sent to Sentry" in data["message"]

    @pytest.mark.integration
    def test_nonexistent_error_endpoint(self, client):
        """Test accessing nonexistent error endpoint"""
        response = client.get("/api/v1/errors/nonexistent")

        # Should return 404 not found
        assert response.status_code == 404

    @pytest.mark.integration
    def test_error_response_format(self, client):
        """Test that error responses follow FastAPI format"""
        response = client.get("/api/v1/errors/test-error")

        assert response.status_code == 500
        data = response.json()

        # FastAPI error format
        assert isinstance(data, dict)
        assert "detail" in data
        assert isinstance(data["detail"], str)

    @pytest.mark.integration
    def test_error_endpoints_methods(self, client):
        """Test that error endpoints only accept GET methods"""
        endpoints = ["/api/v1/errors/test-error", "/api/v1/errors/test-manual-error"]

        for endpoint in endpoints:
            # POST should not be allowed
            post_response = client.post(endpoint)
            assert post_response.status_code == 405  # Method Not Allowed

            # PUT should not be allowed
            put_response = client.put(endpoint)
            assert put_response.status_code == 405

            # DELETE should not be allowed
            delete_response = client.delete(endpoint)
            assert delete_response.status_code == 405


class TestGeneralErrorHandling:
    """Test general error handling across the application"""

    @pytest.mark.integration
    def test_404_error_format(self, client):
        """Test 404 error format consistency"""
        response = client.get("/api/v1/nonexistent/endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    @pytest.mark.integration
    def test_422_validation_error_format(self, client):
        """Test validation error format"""
        # Send invalid data to clusters endpoint
        invalid_data = {"invalid": "data"}
        response = client.post("/api/v1/clusters/", json=invalid_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Validation errors have detailed structure
        assert isinstance(data["detail"], list)

    @pytest.mark.integration
    def test_invalid_json_handling(self, client):
        """Test handling of invalid JSON"""
        # Send malformed JSON
        response = client.post(
            "/api/v1/clusters/",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.integration
    def test_missing_content_type(self, client):
        """Test handling of missing content type"""
        # Send JSON data without proper content type
        response = client.post(
            "/api/v1/clusters/",
            data='{"name": "test"}',
        )

        # Should handle gracefully
        assert response.status_code in [422, 400]

    @pytest.mark.integration
    def test_method_not_allowed_errors(self, client):
        """Test method not allowed errors"""
        # Try POST on GET-only endpoint
        response = client.post("/api/v1/clusters/1")
        assert response.status_code == 405

        # Try DELETE on endpoints that don't support it
        response = client.delete("/api/v1/tasks/stats")
        assert response.status_code == 405

    @pytest.mark.integration
    def test_large_request_handling(self, client):
        """Test handling of very large requests"""
        # Create a large data payload
        large_data = {
            "cluster_id": 1,
            "task_name": "test",
            "database_name": "test",
            "table_name": "test",
            "description": "x" * 10000,  # Very long description
        }

        response = client.post("/api/v1/tasks/", json=large_data)

        # Should handle large data gracefully (might succeed or fail with validation)
        assert response.status_code in [
            201,
            422,
            413,
        ]  # Created, Validation Error, or Payload Too Large

    @pytest.mark.integration
    def test_special_characters_handling(self, client):
        """Test handling of special characters in requests"""
        special_data = {
            "cluster_id": 1,
            "task_name": "test_特殊字符_🎯",
            "database_name": "test_db_中文",
            "table_name": "table_with_emoji_🔥",
        }

        response = client.post("/api/v1/tasks/", json=special_data)

        # Should handle Unicode characters properly
        assert response.status_code in [201, 422]  # Created or validation error

    @pytest.mark.integration
    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection attempts"""
        malicious_inputs = [
            "1'; DROP TABLE clusters; --",
            "1 OR 1=1",
            "'; SELECT * FROM merge_tasks; --",
        ]

        for malicious_input in malicious_inputs:
            # Try SQL injection in path parameters
            response = client.get(f"/api/v1/tables/databases/{malicious_input}")

            # Should return 422 (validation error) not 500 (SQL error)
            assert response.status_code == 422

    @pytest.mark.integration
    def test_xss_protection(self, client):
        """Test protection against XSS attempts"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
        ]

        for payload in xss_payloads:
            task_data = {
                "cluster_id": 1,
                "task_name": payload,
                "database_name": "test",
                "table_name": "test",
            }

            response = client.post("/api/v1/tasks/", json=task_data)

            if response.status_code == 201:
                # If created, verify the payload is properly escaped/sanitized
                data = response.json()
                # The response should not contain executable JavaScript
                assert "<script>" not in str(data)
            else:
                # Validation error is also acceptable
                assert response.status_code == 422

    @pytest.mark.integration
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.get("/api/v1/tasks/")

        # Check for CORS headers (might be set by middleware)
        headers = response.headers
        # CORS headers might be present depending on configuration
        # This is mainly to verify they don't cause errors
        assert response.status_code == 200

    @pytest.mark.integration
    def test_content_type_validation(self, client):
        """Test content type validation"""
        # Try to send XML to JSON endpoint
        xml_data = "<?xml version='1.0'?><root></root>"
        response = client.post(
            "/api/v1/clusters/",
            data=xml_data,
            headers={"Content-Type": "application/xml"},
        )

        # Should reject non-JSON content
        assert response.status_code in [
            415,
            422,
        ]  # Unsupported Media Type or Validation Error

    @pytest.mark.integration
    def test_error_consistency_across_endpoints(self, client):
        """Test that error formats are consistent across different endpoints"""
        # Test 404 errors from different endpoints
        endpoints_404 = [
            "/api/v1/clusters/999999",
            "/api/v1/tasks/999999",
            "/api/v1/tables/databases/999999",
        ]

        for endpoint in endpoints_404:
            response = client.get(endpoint)
            if response.status_code == 404:
                data = response.json()
                assert "detail" in data
                assert isinstance(data["detail"], str)
                # Should contain informative message
                assert len(data["detail"]) > 0
