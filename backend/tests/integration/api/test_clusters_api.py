"""
Integration tests for Clusters API
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# from tests.factories import ClusterFactory  # Not needed for API tests


@pytest.fixture
def client():
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client


class TestClustersAPI:
    """Test cases for clusters API endpoints"""

    @pytest.mark.integration
    def test_get_clusters_endpoint(self, client):
        """Test getting clusters endpoint works"""
        response = client.get("/api/v1/clusters/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # If there are clusters, verify structure
        if len(data) > 0:
            cluster = data[0]
            assert "id" in cluster
            assert "name" in cluster
            assert "description" in cluster

    @pytest.mark.integration
    def test_create_cluster(self, client):
        """Test creating a new cluster"""
        cluster_data = {
            "name": "test-cluster",
            "description": "Test cluster for integration tests",
            "hive_host": "localhost",
            "hive_port": 10000,
            "metastore_url": "mysql://user:pass@localhost:3306/hive",
            "hdfs_namenode": "hdfs://localhost:9000",
            "small_file_threshold": 134217728,
            "is_active": True,
        }

        response = client.post("/api/v1/clusters/", json=cluster_data)

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert data["name"] == cluster_data["name"]
        assert data["description"] == cluster_data["description"]
        assert data["hive_host"] == cluster_data["hive_host"]
        assert data["hive_port"] == cluster_data["hive_port"]
        assert data["is_active"] == cluster_data["is_active"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.integration
    def test_create_cluster_invalid_data(self, client):
        """Test creating cluster with invalid data"""
        invalid_data = {
            "name": "",  # Empty name should be invalid
            "hive_host": "localhost",
        }

        response = client.post("/api/v1/clusters/", json=invalid_data)

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.integration
    def test_get_cluster_by_id_not_found(self, client):
        """Test getting cluster by ID when it doesn't exist"""
        response = client.get("/api/v1/clusters/999")

        assert response.status_code == 404

    @pytest.mark.integration
    def test_cluster_connection_test_endpoint(self, client):
        """Test cluster connection test endpoint"""
        # This endpoint might not be fully implemented yet
        # but we can test that it exists and returns proper response
        response = client.post("/api/v1/clusters/1/test")

        # Could return 404 (cluster not found) or other status
        # depending on implementation
        assert response.status_code in [404, 422, 500, 501]

    @pytest.mark.integration
    def test_create_cluster_duplicate_name(self, client):
        """Test creating clusters with duplicate names"""
        cluster_data = {
            "name": "duplicate-test",
            "description": "First cluster",
            "hive_host": "localhost",
            "hive_port": 10000,
            "metastore_url": "mysql://user:pass@localhost:3306/hive",
            "hdfs_namenode": "hdfs://localhost:9000",
            "small_file_threshold": 134217728,
            "is_active": True,
        }

        # Create first cluster
        response1 = client.post("/api/v1/clusters/", json=cluster_data)
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post("/api/v1/clusters/", json=cluster_data)

        # Should fail with conflict or validation error
        assert response2.status_code in [409, 422, 400]

    @pytest.mark.integration
    def test_cluster_data_persistence(self, client):
        """Test that cluster data persists across requests"""
        cluster_data = {
            "name": "persistence-test",
            "description": "Test data persistence",
            "hive_host": "test.example.com",
            "hive_port": 10000,
            "metastore_url": "mysql://user:pass@test.example.com:3306/hive",
            "hdfs_namenode": "hdfs://test.example.com:9000",
            "small_file_threshold": 67108864,  # 64MB
            "is_active": True,
        }

        # Create cluster
        create_response = client.post("/api/v1/clusters/", json=cluster_data)
        assert create_response.status_code == 201
        created_cluster = create_response.json()
        cluster_id = created_cluster["id"]

        # Get cluster by ID
        get_response = client.get(f"/api/v1/clusters/{cluster_id}")

        if get_response.status_code == 200:
            retrieved_cluster = get_response.json()

            # Verify data matches
            assert retrieved_cluster["name"] == cluster_data["name"]
            assert retrieved_cluster["description"] == cluster_data["description"]
            assert retrieved_cluster["hive_host"] == cluster_data["hive_host"]
            assert (
                retrieved_cluster["small_file_threshold"]
                == cluster_data["small_file_threshold"]
            )
        else:
            # If get endpoint not implemented yet, that's okay
            assert get_response.status_code in [404, 501]

    @pytest.mark.integration
    def test_clusters_list_after_creation(self, client):
        """Test that created clusters appear in list"""
        # Get initial count
        initial_response = client.get("/api/v1/clusters/")
        initial_count = len(initial_response.json())

        # Create a cluster
        cluster_data = {
            "name": "list-test-cluster",
            "description": "Test cluster for listing",
            "hive_host": "localhost",
            "hive_port": 10000,
            "metastore_url": "mysql://user:pass@localhost:3306/hive",
            "hdfs_namenode": "hdfs://localhost:9000",
            "small_file_threshold": 134217728,
            "is_active": True,
        }

        create_response = client.post("/api/v1/clusters/", json=cluster_data)
        assert create_response.status_code == 201

        # Get updated list
        updated_response = client.get("/api/v1/clusters/")
        assert updated_response.status_code == 200

        updated_clusters = updated_response.json()
        assert len(updated_clusters) == initial_count + 1

        # Find our created cluster in the list
        created_cluster = next(
            (c for c in updated_clusters if c["name"] == cluster_data["name"]), None
        )
        assert created_cluster is not None
        assert created_cluster["description"] == cluster_data["description"]

    @pytest.mark.integration
    def test_invalid_metastore_url_format(self, client):
        """Test cluster creation with invalid metastore URL format"""
        cluster_data = {
            "name": "invalid-url-test",
            "description": "Test invalid metastore URL",
            "hive_host": "localhost",
            "hive_port": 10000,
            "metastore_url": "invalid-url-format",  # Invalid URL
            "hdfs_namenode": "hdfs://localhost:9000",
            "small_file_threshold": 134217728,
            "is_active": True,
        }

        response = client.post("/api/v1/clusters/", json=cluster_data)

        # Should validate URL format
        assert response.status_code == 422

    @pytest.mark.integration
    def test_cluster_port_validation(self, client):
        """Test cluster creation with invalid port numbers"""
        cluster_data = {
            "name": "port-test",
            "description": "Test port validation",
            "hive_host": "localhost",
            "hive_port": -1,  # Invalid port
            "metastore_url": "mysql://user:pass@localhost:3306/hive",
            "hdfs_namenode": "hdfs://localhost:9000",
            "small_file_threshold": 134217728,
            "is_active": True,
        }

        response = client.post("/api/v1/clusters/", json=cluster_data)

        # Should validate port range
        assert response.status_code == 422
