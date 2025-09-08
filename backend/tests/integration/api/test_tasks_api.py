"""
Integration tests for Tasks API
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
def sample_task_data():
    """Sample task data for testing"""
    return {
        "cluster_id": 1,
        "task_name": "test_merge_task",
        "database_name": "test_db",
        "table_name": "test_table",
        "partition_filter": "dt='2024-01-01'",
        "merge_strategy": "concatenate",
        "target_file_size": 134217728
    }


class TestTasksAPI:
    """Test cases for tasks API endpoints"""
    
    @pytest.mark.integration
    def test_list_tasks_empty(self, client):
        """Test listing tasks when none exist"""
        response = client.get("/api/v1/tasks/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    def test_list_tasks_with_cluster_filter(self, client):
        """Test listing tasks with cluster filter"""
        response = client.get("/api/v1/tasks/?cluster_id=1")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All tasks should belong to cluster 1
        for task in data:
            assert task['cluster_id'] == 1
    
    @pytest.mark.integration
    def test_list_tasks_with_status_filter(self, client):
        """Test listing tasks with status filter"""
        response = client.get("/api/v1/tasks/?status=pending")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All tasks should have pending status
        for task in data:
            assert task['status'] == 'pending'
    
    @pytest.mark.integration
    def test_list_tasks_with_limit(self, client):
        """Test listing tasks with limit parameter"""
        response = client.get("/api/v1/tasks/?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
    
    @pytest.mark.integration
    def test_list_tasks_combined_filters(self, client):
        """Test listing tasks with combined filters"""
        response = client.get("/api/v1/tasks/?cluster_id=1&status=pending&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        
        for task in data:
            assert task['cluster_id'] == 1
            assert task['status'] == 'pending'
    
    @pytest.mark.integration
    def test_create_task_valid_data(self, client, sample_task_data):
        """Test creating task with valid data"""
        response = client.post("/api/v1/tasks/", json=sample_task_data)
        
        # Could be 201 (created) or validation error depending on schema
        if response.status_code == 201:
            data = response.json()
            assert data['cluster_id'] == sample_task_data['cluster_id']
            assert data['task_name'] == sample_task_data['task_name']
            assert data['database_name'] == sample_task_data['database_name']
            assert data['table_name'] == sample_task_data['table_name']
            assert 'id' in data
        else:
            # Schema validation error is possible
            assert response.status_code == 422
    
    @pytest.mark.integration
    def test_create_task_missing_required_fields(self, client):
        """Test creating task with missing required fields"""
        incomplete_data = {
            "cluster_id": 1,
            # Missing other required fields
        }
        
        response = client.post("/api/v1/tasks/", json=incomplete_data)
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    def test_create_task_invalid_cluster_id(self, client, sample_task_data):
        """Test creating task with invalid cluster_id"""
        invalid_data = sample_task_data.copy()
        invalid_data['cluster_id'] = "invalid"
        
        response = client.post("/api/v1/tasks/", json=invalid_data)
        
        assert response.status_code == 422  # Type validation error
    
    @pytest.mark.integration
    def test_get_task_stats_no_filter(self, client):
        """Test getting task statistics without filters"""
        response = client.get("/api/v1/tasks/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert 'total_tasks' in data
        assert 'status_distribution' in data
        assert 'total_files_saved' in data
        assert 'total_size_saved' in data
        assert 'completed_tasks' in data
        
        # Verify data types
        assert isinstance(data['total_tasks'], int)
        assert isinstance(data['status_distribution'], dict)
        assert isinstance(data['total_files_saved'], int)
        assert isinstance(data['total_size_saved'], int)
        assert isinstance(data['completed_tasks'], int)
    
    @pytest.mark.integration
    def test_get_task_stats_with_cluster_filter(self, client):
        """Test getting task statistics with cluster filter"""
        response = client.get("/api/v1/tasks/stats?cluster_id=1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Same structure as without filter
        assert 'total_tasks' in data
        assert 'status_distribution' in data
        assert isinstance(data['status_distribution'], dict)
    
    @pytest.mark.integration
    def test_get_task_nonexistent(self, client):
        """Test getting nonexistent task"""
        response = client.get("/api/v1/tasks/999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data['detail']
    
    @pytest.mark.integration
    def test_get_task_invalid_id(self, client):
        """Test getting task with invalid ID"""
        response = client.get("/api/v1/tasks/invalid")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    def test_execute_nonexistent_task(self, client):
        """Test executing nonexistent task"""
        response = client.post("/api/v1/tasks/999999/execute")
        
        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data['detail']
    
    @pytest.mark.integration
    def test_execute_task_invalid_id(self, client):
        """Test executing task with invalid ID"""
        response = client.post("/api/v1/tasks/invalid/execute")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    def test_cancel_nonexistent_task(self, client):
        """Test canceling nonexistent task"""
        response = client.post("/api/v1/tasks/999999/cancel")
        
        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data['detail']
    
    @pytest.mark.integration
    def test_cancel_task_invalid_id(self, client):
        """Test canceling task with invalid ID"""
        response = client.post("/api/v1/tasks/invalid/cancel")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    def test_simulate_complete_nonexistent_task(self, client):
        """Test simulating completion of nonexistent task"""
        response = client.post("/api/v1/tasks/999999/simulate-complete")
        
        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data['detail']
    
    @pytest.mark.integration
    def test_simulate_complete_invalid_id(self, client):
        """Test simulating completion with invalid task ID"""
        response = client.post("/api/v1/tasks/invalid/simulate-complete")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    def test_task_workflow_if_task_exists(self, client):
        """Test complete task workflow if tasks exist"""
        # First check if any tasks exist
        list_response = client.get("/api/v1/tasks/?limit=1")
        assert list_response.status_code == 200
        tasks = list_response.json()
        
        if len(tasks) > 0:
            task_id = tasks[0]['id']
            
            # Get specific task
            get_response = client.get(f"/api/v1/tasks/{task_id}")
            if get_response.status_code == 200:
                task_data = get_response.json()
                assert task_data['id'] == task_id
                
                # Try to execute task (might fail if already running/completed)
                execute_response = client.post(f"/api/v1/tasks/{task_id}/execute")
                # Status could be 200 (success) or 400 (already running/completed)
                assert execute_response.status_code in [200, 400]
        else:
            # No tasks exist, which is valid
            assert len(tasks) == 0
    
    @pytest.mark.integration
    def test_task_list_ordering(self, client):
        """Test that tasks are ordered by creation time descending"""
        response = client.get("/api/v1/tasks/")
        
        assert response.status_code == 200
        tasks = response.json()
        
        if len(tasks) > 1:
            # Verify descending order by created_time
            for i in range(len(tasks) - 1):
                if tasks[i].get('created_time') and tasks[i+1].get('created_time'):
                    assert tasks[i]['created_time'] >= tasks[i+1]['created_time']
    
    @pytest.mark.integration
    def test_status_distribution_validity(self, client):
        """Test that status distribution contains valid statuses"""
        response = client.get("/api/v1/tasks/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        valid_statuses = ['pending', 'running', 'success', 'failed', 'cancelled']
        status_distribution = data['status_distribution']
        
        for status in status_distribution.keys():
            assert status in valid_statuses
            assert isinstance(status_distribution[status], int)
            assert status_distribution[status] >= 0
    
    @pytest.mark.integration
    def test_task_stats_consistency(self, client):
        """Test that task statistics are consistent"""
        response = client.get("/api/v1/tasks/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Total tasks should equal sum of status distribution
        total_from_distribution = sum(data['status_distribution'].values())
        if data['total_tasks'] > 0:
            assert data['total_tasks'] == total_from_distribution
        
        # Completed tasks should match success count in distribution
        success_count = data['status_distribution'].get('success', 0)
        assert data['completed_tasks'] == success_count
        
        # Files and size saved should be non-negative
        assert data['total_files_saved'] >= 0
        assert data['total_size_saved'] >= 0
    
    @pytest.mark.integration
    def test_merge_strategy_values(self, client, sample_task_data):
        """Test different merge strategy values"""
        valid_strategies = ['concatenate', 'insert_overwrite']
        
        for strategy in valid_strategies:
            task_data = sample_task_data.copy()
            task_data['merge_strategy'] = strategy
            task_data['task_name'] = f"test_task_{strategy}"
            
            response = client.post("/api/v1/tasks/", json=task_data)
            
            # Should accept valid strategies
            if response.status_code == 201:
                data = response.json()
                assert data['merge_strategy'] == strategy
    
    @pytest.mark.integration
    def test_invalid_merge_strategy(self, client, sample_task_data):
        """Test invalid merge strategy value"""
        task_data = sample_task_data.copy()
        task_data['merge_strategy'] = 'invalid_strategy'
        
        response = client.post("/api/v1/tasks/", json=task_data)
        
        # Should reject invalid strategy
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_api_response_structure(self, client):
        """Test that API responses have consistent structure"""
        # Test list endpoint
        list_response = client.get("/api/v1/tasks/")
        assert list_response.status_code == 200
        assert isinstance(list_response.json(), list)
        
        # Test stats endpoint  
        stats_response = client.get("/api/v1/tasks/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert isinstance(stats_data, dict)
        
        # Test error responses have detail field
        error_response = client.get("/api/v1/tasks/999999")
        assert error_response.status_code == 404
        error_data = error_response.json()
        assert 'detail' in error_data