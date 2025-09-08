"""
Integration tests for Tables API
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client


class TestTablesAPI:
    """Test cases for tables API endpoints"""
    
    @pytest.mark.integration
    def test_get_table_metrics_missing_cluster_id(self, client):
        """Test getting table metrics without cluster_id parameter"""
        response = client.get("/api/v1/tables/metrics")
        
        # Should require cluster_id parameter
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_get_table_metrics_nonexistent_cluster(self, client):
        """Test getting table metrics for nonexistent cluster"""
        response = client.get("/api/v1/tables/metrics?cluster_id=999999")
        
        # Should return empty list for nonexistent cluster
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    @pytest.mark.integration
    def test_get_table_metrics_with_cluster_id(self, client):
        """Test getting table metrics with valid cluster_id"""
        response = client.get("/api/v1/tables/metrics?cluster_id=1")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # If there are metrics, verify structure
        if len(data) > 0:
            metric = data[0]
            assert 'id' in metric
            assert 'cluster_id' in metric
            assert 'database_name' in metric
            assert 'table_name' in metric
    
    @pytest.mark.integration
    def test_get_table_metrics_with_database_filter(self, client):
        """Test getting table metrics with database filter"""
        response = client.get("/api/v1/tables/metrics?cluster_id=1&database_name=default")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All results should be from default database if any exist
        for metric in data:
            assert metric['database_name'] == 'default'
    
    @pytest.mark.integration
    def test_get_small_file_summary_missing_cluster_id(self, client):
        """Test small file summary without cluster_id"""
        response = client.get("/api/v1/tables/small-files")
        
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_get_small_file_summary_valid(self, client):
        """Test small file summary with valid cluster_id"""
        response = client.get("/api/v1/tables/small-files?cluster_id=1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert 'total_tables' in data
        assert 'total_files' in data
        assert 'total_small_files' in data
        assert 'avg_file_size' in data
        assert 'small_file_ratio' in data
        
        # Verify data types
        assert isinstance(data['total_tables'], int)
        assert isinstance(data['total_files'], int) 
        assert isinstance(data['total_small_files'], int)
        assert isinstance(data['avg_file_size'], (int, float))
        assert isinstance(data['small_file_ratio'], (int, float))
        
        # Verify data consistency
        assert data['total_small_files'] <= data['total_files']
        assert 0 <= data['small_file_ratio'] <= 100
    
    @pytest.mark.integration
    def test_get_databases_nonexistent_cluster(self, client):
        """Test getting databases for nonexistent cluster"""
        response = client.get("/api/v1/tables/databases/999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Cluster not found" in data['detail']
    
    @pytest.mark.integration
    def test_get_databases_valid_cluster(self, client):
        """Test getting databases for valid cluster"""
        response = client.get("/api/v1/tables/databases/1")
        
        # Could be 200 (success) or 500 (connection error) depending on cluster setup
        if response.status_code == 200:
            data = response.json()
            assert 'databases' in data
            assert isinstance(data['databases'], list)
        else:
            # Connection error is expected if cluster is not properly configured
            assert response.status_code == 500
            assert "Failed to get databases" in response.json()['detail']
    
    @pytest.mark.integration
    def test_get_tables_nonexistent_cluster(self, client):
        """Test getting tables for nonexistent cluster"""
        response = client.get("/api/v1/tables/tables/999999/default")
        
        assert response.status_code == 404
        data = response.json()
        assert "Cluster not found" in data['detail']
    
    @pytest.mark.integration
    def test_get_tables_valid_cluster(self, client):
        """Test getting tables for valid cluster and database"""
        response = client.get("/api/v1/tables/tables/1/default")
        
        # Could be 200 (success) or 500 (connection error)
        if response.status_code == 200:
            data = response.json()
            assert 'database' in data
            assert 'tables' in data
            assert data['database'] == 'default'
            assert isinstance(data['tables'], list)
        else:
            # Connection error expected if cluster not configured
            assert response.status_code == 500
            assert "Failed to get tables" in response.json()['detail']
    
    @pytest.mark.integration
    def test_scan_tables_missing_request_body(self, client):
        """Test scan endpoint without request body"""
        response = client.post("/api/v1/tables/scan")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    def test_scan_tables_invalid_cluster(self, client):
        """Test scan endpoint with invalid cluster"""
        scan_data = {
            "cluster_id": 999999,
            "database_name": "default"
        }
        
        response = client.post("/api/v1/tables/scan", json=scan_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "Cluster not found" in data['detail']
    
    @pytest.mark.integration
    def test_scan_tables_missing_parameters(self, client):
        """Test scan endpoint with missing required parameters"""
        scan_data = {
            "cluster_id": 1
            # Missing database_name
        }
        
        response = client.post("/api/v1/tables/scan", json=scan_data)
        
        assert response.status_code in [400, 422, 500]
    
    @pytest.mark.integration 
    def test_scan_database_tables_nonexistent_cluster(self, client):
        """Test database scan with nonexistent cluster"""
        response = client.post("/api/v1/tables/scan/999999/default")
        
        assert response.status_code == 404
        data = response.json()
        assert "Cluster not found" in data['detail']
    
    @pytest.mark.integration
    def test_scan_database_tables_valid_cluster(self, client):
        """Test database scan with valid cluster"""
        response = client.post("/api/v1/tables/scan/1/default")
        
        # Could succeed or fail depending on cluster configuration
        if response.status_code == 200:
            data = response.json()
            assert 'cluster_id' in data
            assert 'database_name' in data
            assert 'scan_result' in data
            assert 'status' in data
            assert data['cluster_id'] == 1
            assert data['database_name'] == 'default'
        else:
            # Scan failure is expected if cluster not properly configured
            assert response.status_code == 500
            assert "Scan failed" in response.json()['detail']
    
    @pytest.mark.integration
    def test_scan_single_table_nonexistent_cluster(self, client):
        """Test single table scan with nonexistent cluster"""
        response = client.post("/api/v1/tables/scan-table/999999/default/test_table")
        
        assert response.status_code == 404
        data = response.json()
        assert "Cluster not found" in data['detail']
    
    @pytest.mark.integration
    def test_scan_single_table_valid_cluster(self, client):
        """Test single table scan with valid cluster"""
        response = client.post("/api/v1/tables/scan-table/1/default/test_table")
        
        # Could succeed, fail with table not found, or connection error
        if response.status_code == 200:
            data = response.json()
            assert 'cluster_id' in data
            assert 'database_name' in data
            assert 'table_name' in data
            assert 'scan_result' in data
            assert data['cluster_id'] == 1
            assert data['database_name'] == 'default'
            assert data['table_name'] == 'test_table'
        else:
            # Various errors are expected
            assert response.status_code in [404, 500]
    
    @pytest.mark.integration
    def test_test_connection_nonexistent_cluster(self, client):
        """Test connection test with nonexistent cluster"""
        response = client.get("/api/v1/tables/test-connection/999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Cluster not found" in data['detail']
    
    @pytest.mark.integration
    def test_test_connection_valid_cluster(self, client):
        """Test connection test with valid cluster"""
        response = client.get("/api/v1/tables/test-connection/1")
        
        if response.status_code == 200:
            data = response.json()
            assert 'cluster_id' in data
            assert 'cluster_name' in data
            assert 'connections' in data
            assert data['cluster_id'] == 1
        else:
            # Connection failure expected if cluster not configured
            assert response.status_code == 500
            assert "Connection test failed" in response.json()['detail']
    
    @pytest.mark.integration
    def test_small_file_analysis_nonexistent_cluster(self, client):
        """Test small file analysis with nonexistent cluster"""
        response = client.get("/api/v1/tables/small-file-analysis/999999")
        
        assert response.status_code == 200  # Should return empty results, not error
        data = response.json()
        assert data['message'] == "No table data found"
        assert data['tables'] == []
    
    @pytest.mark.integration
    def test_small_file_analysis_valid_cluster(self, client):
        """Test small file analysis with valid cluster"""
        response = client.get("/api/v1/tables/small-file-analysis/1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'cluster_id' in data
        assert 'summary' in data
        assert 'recommendations' in data
        assert 'tables' in data
        
        # Verify summary structure
        summary = data['summary']
        assert 'total_tables' in summary
        assert 'critical_tables' in summary
        assert 'high_priority_tables' in summary
        assert 'overall_small_file_ratio' in summary
        assert 'total_estimated_savings_gb' in summary
        
        # Verify data types
        assert isinstance(data['recommendations'], list)
        assert isinstance(data['tables'], list)
    
    @pytest.mark.integration
    def test_table_metrics_ordering(self, client):
        """Test that table metrics are ordered by scan time"""
        response = client.get("/api/v1/tables/metrics?cluster_id=1")
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 1:
            # Verify ordering - newer scans should come first
            for i in range(len(data) - 1):
                if data[i].get('scan_time') and data[i+1].get('scan_time'):
                    assert data[i]['scan_time'] >= data[i+1]['scan_time']
    
    @pytest.mark.integration
    def test_api_error_handling_consistency(self, client):
        """Test that all endpoints handle errors consistently"""
        endpoints_to_test = [
            ("/api/v1/tables/databases/999999", 404),
            ("/api/v1/tables/tables/999999/default", 404), 
            ("/api/v1/tables/test-connection/999999", 404),
        ]
        
        for endpoint, expected_status in endpoints_to_test:
            response = client.get(endpoint)
            assert response.status_code == expected_status
            
            if expected_status == 404:
                data = response.json()
                assert 'detail' in data
                assert "Cluster not found" in data['detail']
    
    @pytest.mark.integration
    def test_parameter_validation(self, client):
        """Test parameter validation across endpoints"""
        # Test invalid cluster_id types
        invalid_cluster_ids = ["abc", "-1", "0.5"]
        
        for invalid_id in invalid_cluster_ids:
            response = client.get(f"/api/v1/tables/databases/{invalid_id}")
            assert response.status_code == 422  # Validation error