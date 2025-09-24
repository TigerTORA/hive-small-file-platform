"""
Integration tests for complete workflow scenarios
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_cluster_data():
    """Sample cluster data for workflow tests"""
    return {
        "name": "workflow-test-cluster",
        "description": "Test cluster for workflow scenarios",
        "hive_host": "localhost",
        "hive_port": 10000,
        "metastore_url": "mysql://user:pass@localhost:3306/hive",
        "hdfs_namenode": "hdfs://localhost:9000",
        "small_file_threshold": 134217728,
        "is_active": True,
    }


class TestCompleteWorkflowScenarios:
    """Test complete user workflow scenarios"""

    @pytest.mark.integration
    def test_health_check_workflow(self, client):
        """Test basic health check workflow"""
        # 1. Check API root
        root_response = client.get("/")
        assert root_response.status_code == 200

        # 2. Check health endpoint
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"

    @pytest.mark.integration
    def test_cluster_discovery_workflow(self, client):
        """Test cluster discovery and exploration workflow"""
        # 1. List all clusters
        clusters_response = client.get("/api/v1/clusters/")
        assert clusters_response.status_code == 200
        clusters = clusters_response.json()

        if len(clusters) > 0:
            cluster_id = clusters[0]["id"]

            # 2. Get cluster details
            detail_response = client.get(f"/api/v1/clusters/{cluster_id}")
            # This endpoint might not exist, that's okay

            # 3. Get small file summary for cluster
            summary_response = client.get(
                f"/api/v1/tables/small-files?cluster_id={cluster_id}"
            )
            assert summary_response.status_code == 200
            summary = summary_response.json()

            # Verify summary structure
            assert "total_tables" in summary
            assert "total_files" in summary
            assert "small_file_ratio" in summary

            # 4. Get table metrics for cluster
            metrics_response = client.get(
                f"/api/v1/tables/metrics?cluster_id={cluster_id}"
            )
            assert metrics_response.status_code == 200

        else:
            # No clusters exist - this is a valid state
            assert len(clusters) == 0

    @pytest.mark.integration
    def test_task_management_workflow(self, client):
        """Test task creation and management workflow"""
        # 1. Get initial task stats
        initial_stats_response = client.get("/api/v1/tasks/stats")
        assert initial_stats_response.status_code == 200
        initial_stats = initial_stats_response.json()

        # 2. List current tasks
        tasks_response = client.get("/api/v1/tasks/")
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()

        # 3. Filter tasks by status
        pending_tasks_response = client.get("/api/v1/tasks/?status=pending")
        assert pending_tasks_response.status_code == 200
        pending_tasks = pending_tasks_response.json()

        # All returned tasks should have pending status
        for task in pending_tasks:
            assert task["status"] == "pending"

        # 4. Get stats after filtering
        final_stats_response = client.get("/api/v1/tasks/stats")
        assert final_stats_response.status_code == 200
        final_stats = final_stats_response.json()

        # Stats should be consistent
        assert final_stats["total_tasks"] == initial_stats["total_tasks"]

    @pytest.mark.integration
    def test_error_handling_workflow(self, client):
        """Test error handling across different scenarios"""
        # 1. Test error monitoring endpoints
        manual_error_response = client.get("/api/v1/errors/test-manual-error")
        assert manual_error_response.status_code == 200

        test_error_response = client.get("/api/v1/errors/test-error")
        assert test_error_response.status_code == 500

        # 2. Test 404 errors across different endpoints
        not_found_endpoints = [
            "/api/v1/clusters/999999",
            "/api/v1/tasks/999999",
            "/api/v1/tables/databases/999999",
        ]

        for endpoint in not_found_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    @pytest.mark.integration
    def test_data_consistency_workflow(self, client):
        """Test data consistency across related endpoints"""
        # 1. Get all clusters
        clusters_response = client.get("/api/v1/clusters/")
        assert clusters_response.status_code == 200
        clusters = clusters_response.json()

        for cluster in clusters:
            cluster_id = cluster["id"]

            # 2. Get tasks for this cluster
            cluster_tasks_response = client.get(
                f"/api/v1/tasks/?cluster_id={cluster_id}"
            )
            assert cluster_tasks_response.status_code == 200
            cluster_tasks = cluster_tasks_response.json()

            # All tasks should belong to this cluster
            for task in cluster_tasks:
                assert task["cluster_id"] == cluster_id

            # 3. Get table metrics for this cluster
            metrics_response = client.get(
                f"/api/v1/tables/metrics?cluster_id={cluster_id}"
            )
            assert metrics_response.status_code == 200
            metrics = metrics_response.json()

            # All metrics should belong to this cluster
            for metric in metrics:
                assert metric["cluster_id"] == cluster_id

    @pytest.mark.integration
    def test_pagination_and_filtering_workflow(self, client):
        """Test pagination and filtering across endpoints"""
        # 1. Test task listing with different limits
        limits = [1, 5, 10, 50]

        for limit in limits:
            response = client.get(f"/api/v1/tasks/?limit={limit}")
            assert response.status_code == 200
            tasks = response.json()
            assert len(tasks) <= limit

        # 2. Test task filtering by status
        statuses = ["pending", "running", "success", "failed"]

        for status in statuses:
            response = client.get(f"/api/v1/tasks/?status={status}")
            assert response.status_code == 200
            tasks = response.json()

            # All returned tasks should have the filtered status
            for task in tasks:
                assert task["status"] == status

        # 3. Test combined filtering
        response = client.get("/api/v1/tasks/?status=pending&limit=5")
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) <= 5

        for task in tasks:
            assert task["status"] == "pending"

    @pytest.mark.integration
    def test_api_versioning_workflow(self, client):
        """Test API versioning consistency"""
        # All API endpoints should be under /api/v1/
        v1_endpoints = [
            "/api/v1/clusters/",
            "/api/v1/tables/metrics",
            "/api/v1/tasks/",
            "/api/v1/errors/test-manual-error",
        ]

        for endpoint in v1_endpoints:
            response = client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404

    @pytest.mark.integration
    def test_monitoring_workflow(self, client):
        """Test monitoring and observability workflow"""
        # 1. Check health status
        health_response = client.get("/health")
        assert health_response.status_code == 200

        # 2. Get task statistics for monitoring
        stats_response = client.get("/api/v1/tasks/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()

        # Verify monitoring metrics are available
        assert "total_tasks" in stats
        assert "status_distribution" in stats
        assert "completed_tasks" in stats

        # 3. Test error monitoring endpoint
        error_response = client.get("/api/v1/errors/test-manual-error")
        assert error_response.status_code == 200

    @pytest.mark.integration
    def test_security_workflow(self, client):
        """Test security-related workflow"""
        # 1. Test that dangerous operations require proper methods
        dangerous_endpoints = ["/api/v1/tasks/1/execute", "/api/v1/tasks/1/cancel"]

        for endpoint in dangerous_endpoints:
            # GET should not be allowed for operations
            get_response = client.get(endpoint)
            assert get_response.status_code == 405  # Method Not Allowed

        # 2. Test input validation
        invalid_inputs = ["<script>", "'; DROP TABLE", "../../../etc/passwd"]

        for invalid_input in invalid_inputs:
            # Try in path parameter
            response = client.get(f"/api/v1/tables/databases/{invalid_input}")
            assert response.status_code == 422  # Validation error, not server error

    @pytest.mark.integration
    def test_performance_workflow(self, client):
        """Test performance-related workflow"""
        # 1. Test that large result sets are handled properly
        large_limit_response = client.get("/api/v1/tasks/?limit=1000")
        assert large_limit_response.status_code == 200

        # 2. Test that multiple concurrent requests work
        import concurrent.futures

        def make_request():
            return client.get("/api/v1/tasks/stats")

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

    @pytest.mark.integration
    def test_end_to_end_scenario(self, client):
        """Test complete end-to-end user scenario"""
        # Scenario: User wants to monitor small files and create merge tasks

        # 1. Start by checking system health
        health_response = client.get("/health")
        assert health_response.status_code == 200

        # 2. Discover available clusters
        clusters_response = client.get("/api/v1/clusters/")
        assert clusters_response.status_code == 200
        clusters = clusters_response.json()

        if len(clusters) > 0:
            cluster_id = clusters[0]["id"]

            # 3. Analyze small files in the cluster
            analysis_response = client.get(
                f"/api/v1/tables/small-file-analysis/{cluster_id}"
            )
            assert analysis_response.status_code == 200
            analysis = analysis_response.json()

            # 4. Get detailed metrics
            metrics_response = client.get(
                f"/api/v1/tables/metrics?cluster_id={cluster_id}"
            )
            assert metrics_response.status_code == 200

            # 5. Check existing merge tasks for this cluster
            tasks_response = client.get(f"/api/v1/tasks/?cluster_id={cluster_id}")
            assert tasks_response.status_code == 200

            # 6. Get task statistics
            stats_response = client.get(f"/api/v1/tasks/stats?cluster_id={cluster_id}")
            assert stats_response.status_code == 200

            # All steps should complete successfully
            assert all(
                [
                    health_response.status_code == 200,
                    clusters_response.status_code == 200,
                    analysis_response.status_code == 200,
                    metrics_response.status_code == 200,
                    tasks_response.status_code == 200,
                    stats_response.status_code == 200,
                ]
            )

        else:
            # No clusters available - still a valid scenario
            # User would need to add clusters first
            assert len(clusters) == 0
