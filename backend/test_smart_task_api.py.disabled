"""
智能任务创建API端点的单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.engines.engine_factory import MergeEngineFactory


client = TestClient(app)


class TestSmartTaskCreationAPI:
    """测试智能任务创建API端点"""
    
    def setup_method(self):
        """测试前准备"""
        self.cluster_data = {
            "id": 1,
            "name": "test-cluster",
            "hive_metastore_url": "mysql://test:test@localhost:3306/hive",
            "hdfs_namenode_url": "hdfs://localhost:9000",
            "connection_type": "mysql"
        }
        
        self.smart_create_request = {
            "cluster_id": 1,
            "database_name": "test_db",
            "table_name": "test_table",
            "partition_filter": "dt='2023-01-01'"
        }
    
    @patch('app.api.tasks.get_db')
    @patch('app.api.tasks.MergeEngineFactory.create_smart_merge_task')
    def test_create_smart_task_success(self, mock_create_smart, mock_get_db):
        """测试成功创建智能任务"""
        # 模拟数据库会话
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # 模拟集群查询
        mock_cluster = Cluster(**self.cluster_data)
        mock_db.query().filter().first.return_value = mock_cluster
        
        # 模拟智能任务配置
        mock_smart_config = {
            "task_name": "Smart merge for test_table",
            "recommended_strategy": "safe_merge",
            "strategy_reason": "大表且生产环境，推荐安全合并策略",
            "validation": {
                "valid": True,
                "warnings": []
            }
        }
        mock_create_smart.return_value = mock_smart_config
        
        # 模拟创建的任务
        mock_task = MergeTask(
            id=123,
            cluster_id=1,
            task_name="Smart merge for test_table",
            database_name="test_db",
            table_name="test_table",
            merge_strategy="safe_merge",
            status="pending"
        )
        mock_db.add.return_value = None
        mock_db.flush.return_value = None
        mock_task.id = 123  # 模拟flush后获得ID
        
        response = client.post("/api/v1/tasks/smart-create", json=self.smart_create_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "task" in data
        assert "strategy_info" in data
        assert data["strategy_info"]["recommended_strategy"] == "safe_merge"
        assert "大表" in data["strategy_info"]["strategy_reason"]
        
        # 验证调用
        mock_create_smart.assert_called_once_with(
            cluster=mock_cluster,
            database_name="test_db",
            table_name="test_table",
            partition_filter="dt='2023-01-01'"
        )
    
    @patch('app.api.tasks.get_db')
    def test_create_smart_task_cluster_not_found(self, mock_get_db):
        """测试集群不存在的情况"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # 模拟集群不存在
        mock_db.query().filter().first.return_value = None
        
        response = client.post("/api/v1/tasks/smart-create", json=self.smart_create_request)
        
        assert response.status_code == 404
        data = response.json()
        assert "Cluster not found" in data["detail"]
    
    @patch('app.api.tasks.get_db')
    @patch('app.api.tasks.MergeEngineFactory.create_smart_merge_task')
    def test_create_smart_task_validation_failed(self, mock_create_smart, mock_get_db):
        """测试任务验证失败"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_cluster = Cluster(**self.cluster_data)
        mock_db.query().filter().first.return_value = mock_cluster
        
        # 模拟验证失败的智能任务配置
        mock_smart_config = {
            "task_name": "Invalid merge for test_table",
            "recommended_strategy": "concatenate",
            "strategy_reason": "表格式不兼容",
            "validation": {
                "valid": False,
                "message": "Table format not compatible with concatenate strategy",
                "warnings": []
            }
        }
        mock_create_smart.return_value = mock_smart_config
        
        response = client.post("/api/v1/tasks/smart-create", json=self.smart_create_request)
        
        assert response.status_code == 400
        data = response.json()
        assert "Task validation failed" in data["detail"]
    
    @patch('app.api.tasks.get_db')
    @patch('app.api.tasks.MergeEngineFactory.create_smart_merge_task')
    def test_create_smart_task_with_warnings(self, mock_create_smart, mock_get_db):
        """测试创建任务但有警告"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_cluster = Cluster(**self.cluster_data)
        mock_db.query().filter().first.return_value = mock_cluster
        
        # 模拟有警告的智能任务配置
        mock_smart_config = {
            "task_name": "Smart merge for large_table",
            "recommended_strategy": "insert_overwrite",
            "strategy_reason": "文件数量过多，使用insert_overwrite策略",
            "validation": {
                "valid": True,
                "warnings": [
                    "文件数量过多，合并可能需要较长时间",
                    "建议在非业务高峰时段执行"
                ]
            }
        }
        mock_create_smart.return_value = mock_smart_config
        
        mock_task = MergeTask(
            id=124,
            cluster_id=1,
            task_name="Smart merge for large_table",
            database_name="test_db",
            table_name="test_table",
            merge_strategy="insert_overwrite",
            status="pending"
        )
        mock_db.add.return_value = None
        mock_db.flush.return_value = None
        
        response = client.post("/api/v1/tasks/smart-create", json=self.smart_create_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["strategy_info"]["recommended_strategy"] == "insert_overwrite"
        assert len(data["strategy_info"]["validation"]["warnings"]) == 2
        assert "文件数量过多" in data["strategy_info"]["validation"]["warnings"][0]
    
    @patch('app.api.tasks.get_db')
    def test_create_smart_task_missing_required_fields(self, mock_get_db):
        """测试缺少必需字段"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # 缺少table_name字段
        invalid_request = {
            "cluster_id": 1,
            "database_name": "test_db"
        }
        
        response = client.post("/api/v1/tasks/smart-create", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.tasks.get_db')
    @patch('app.api.tasks.MergeEngineFactory.create_smart_merge_task')
    def test_create_smart_task_database_error(self, mock_create_smart, mock_get_db):
        """测试数据库错误"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_cluster = Cluster(**self.cluster_data)
        mock_db.query().filter().first.return_value = mock_cluster
        
        mock_smart_config = {
            "task_name": "Smart merge for test_table",
            "recommended_strategy": "safe_merge",
            "strategy_reason": "推荐安全合并策略",
            "validation": {"valid": True, "warnings": []}
        }
        mock_create_smart.return_value = mock_smart_config
        
        # 模拟数据库错误
        mock_db.add.side_effect = Exception("Database connection failed")
        
        response = client.post("/api/v1/tasks/smart-create", json=self.smart_create_request)
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to create smart merge task" in data["detail"]
    
    @patch('app.api.tasks.get_db')
    @patch('app.api.tasks.MergeEngineFactory.create_smart_merge_task')
    def test_create_smart_task_without_partition_filter(self, mock_create_smart, mock_get_db):
        """测试不带分区过滤器的智能任务创建"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_cluster = Cluster(**self.cluster_data)
        mock_db.query().filter().first.return_value = mock_cluster
        
        mock_smart_config = {
            "task_name": "Smart merge for full_table",
            "recommended_strategy": "concatenate",
            "strategy_reason": "小表且文件格式兼容，推荐concatenate策略",
            "validation": {"valid": True, "warnings": []}
        }
        mock_create_smart.return_value = mock_smart_config
        
        mock_task = MergeTask(
            id=125,
            cluster_id=1,
            task_name="Smart merge for full_table",
            database_name="test_db",
            table_name="test_table",
            merge_strategy="concatenate",
            status="pending"
        )
        mock_db.add.return_value = None
        mock_db.flush.return_value = None
        
        # 不包含partition_filter的请求
        request_without_partition = {
            "cluster_id": 1,
            "database_name": "test_db",
            "table_name": "test_table"
        }
        
        response = client.post("/api/v1/tasks/smart-create", json=request_without_partition)
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证调用时partition_filter为None
        mock_create_smart.assert_called_once_with(
            cluster=mock_cluster,
            database_name="test_db",
            table_name="test_table",
            partition_filter=None
        )


class TestTaskExecutionAPI:
    """测试任务执行相关API端点"""
    
    @patch('app.api.tasks.get_db')
    @patch('app.scheduler.merge_tasks.execute_merge_task.delay')
    def test_execute_task_success(self, mock_execute_delay, mock_get_db):
        """测试成功执行任务"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # 模拟任务查询
        mock_task = MergeTask(
            id=123,
            cluster_id=1,
            task_name="Test merge task",
            database_name="test_db",
            table_name="test_table",
            status="pending"
        )
        mock_db.query().filter().first.return_value = mock_task
        
        # 模拟Celery任务返回
        mock_celery_result = Mock()
        mock_celery_result.id = "celery-task-123"
        mock_execute_delay.return_value = mock_celery_result
        
        response = client.post("/api/v1/tasks/123/execute")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Task execution started"
        assert data["celery_task_id"] == "celery-task-123"
        assert mock_task.status == "running"
        assert mock_task.celery_task_id == "celery-task-123"
    
    @patch('app.api.tasks.get_db')
    def test_execute_task_not_found(self, mock_get_db):
        """测试执行不存在的任务"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query().filter().first.return_value = None
        
        response = client.post("/api/v1/tasks/999/execute")
        
        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data["detail"]
    
    @patch('app.api.tasks.get_db')
    def test_execute_task_already_running(self, mock_get_db):
        """测试执行已在运行的任务"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_task = MergeTask(
            id=123,
            cluster_id=1,
            task_name="Running task",
            database_name="test_db",
            table_name="test_table",
            status="running"
        )
        mock_db.query().filter().first.return_value = mock_task
        
        response = client.post("/api/v1/tasks/123/execute")
        
        assert response.status_code == 400
        data = response.json()
        assert "Task is already running" in data["detail"]
    
    @patch('app.api.tasks.get_db')
    @patch('app.scheduler.merge_tasks.cancel_task.delay')
    def test_cancel_task_success(self, mock_cancel_delay, mock_get_db):
        """测试成功取消任务"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_task = MergeTask(
            id=123,
            cluster_id=1,
            task_name="Running task",
            database_name="test_db",
            table_name="test_table",
            status="running",
            celery_task_id="celery-task-123"
        )
        mock_db.query().filter().first.return_value = mock_task
        
        # 模拟取消任务返回
        mock_cancel_result = {
            "status": "success",
            "message": "Task 123 cancelled"
        }
        mock_cancel_delay.return_value = Mock(get=lambda: mock_cancel_result)
        
        response = client.post("/api/v1/tasks/123/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert "cancellation started" in data["message"]
    
    @patch('app.api.tasks.get_db')
    def test_cancel_task_not_running(self, mock_get_db):
        """测试取消非运行状态的任务"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_task = MergeTask(
            id=123,
            cluster_id=1,
            task_name="Completed task",
            database_name="test_db",
            table_name="test_table",
            status="success"
        )
        mock_db.query().filter().first.return_value = mock_task
        
        response = client.post("/api/v1/tasks/123/cancel")
        
        assert response.status_code == 400
        data = response.json()
        assert "Task is not running" in data["detail"]


class TestTaskRetryAPI:
    """测试任务重试API端点"""
    
    @patch('app.api.tasks.get_db')
    @patch('app.scheduler.merge_tasks.execute_merge_task.delay')
    def test_retry_task_success(self, mock_execute_delay, mock_get_db):
        """测试成功重试失败的任务"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_task = MergeTask(
            id=123,
            cluster_id=1,
            task_name="Failed task",
            database_name="test_db",
            table_name="test_table",
            status="failed",
            error_message="Previous error"
        )
        mock_db.query().filter().first.return_value = mock_task
        
        mock_celery_result = Mock()
        mock_celery_result.id = "celery-retry-123"
        mock_execute_delay.return_value = mock_celery_result
        
        response = client.post("/api/v1/tasks/123/retry")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Task retry started"
        assert mock_task.status == "pending"  # 重置为pending状态
        assert mock_task.error_message is None  # 清除之前的错误信息
    
    @patch('app.api.tasks.get_db')
    def test_retry_task_not_failed(self, mock_get_db):
        """测试重试非失败状态的任务"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_task = MergeTask(
            id=123,
            cluster_id=1,
            task_name="Success task",
            database_name="test_db",
            table_name="test_table",
            status="success"
        )
        mock_db.query().filter().first.return_value = mock_task
        
        response = client.post("/api/v1/tasks/123/retry")
        
        assert response.status_code == 400
        data = response.json()
        assert "Only failed tasks can be retried" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])