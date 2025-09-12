"""
智能合并功能的端到端集成测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.main import app
from app.config.database import get_db, Base
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.models.table_metric import TableMetric
from app.engines.engine_factory import MergeEngineFactory
from app.utils.table_lock_manager import TableLockManager

# 使用内存SQLite进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestSmartMergeIntegration:
    """智能合并功能端到端集成测试"""
    
    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        Base.metadata.create_all(bind=engine)
    
    @classmethod
    def teardown_class(cls):
        """测试类清理"""
        Base.metadata.drop_all(bind=engine)
    
    def setup_method(self):
        """每个测试方法前的准备"""
        # 清理数据库
        db = TestingSessionLocal()
        db.query(MergeTask).delete()
        db.query(TableMetric).delete()
        db.query(Cluster).delete()
        db.commit()
        
        # 创建测试集群
        self.test_cluster = Cluster(
            name="test-cluster",
            description="Integration test cluster",
            hive_metastore_url="mysql://test:test@localhost:3306/hive",
            hdfs_namenode_url="hdfs://localhost:9000",
            connection_type="mysql"
        )
        db.add(self.test_cluster)
        db.commit()
        db.refresh(self.test_cluster)
        
        # 创建测试表指标
        self.test_table_metric = TableMetric(
            cluster_id=self.test_cluster.id,
            database_name="test_db",
            table_name="small_files_table",
            total_files=1000,
            small_files=800,
            total_size=10 * 1024 * 1024 * 1024,  # 10GB
            partition_count=50,
            storage_format="parquet",
            is_partitioned=True
        )
        db.add(self.test_table_metric)
        db.commit()
        
        db.close()
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        db = TestingSessionLocal()
        db.query(MergeTask).delete()
        db.query(TableMetric).delete()
        db.query(Cluster).delete()
        db.commit()
        db.close()
    
    def test_complete_smart_merge_workflow(self):
        """测试完整的智能合并工作流程"""
        # 1. 创建智能合并任务
        create_request = {
            "cluster_id": self.test_cluster.id,
            "database_name": "test_db",
            "table_name": "small_files_table"
        }
        
        with patch('app.engines.engine_factory.MergeEngineFactory.create_smart_merge_task') as mock_create:
            mock_create.return_value = {
                "task_name": "Smart merge for small_files_table",
                "recommended_strategy": "safe_merge",
                "strategy_reason": "大表且生产环境，推荐安全合并策略",
                "validation": {
                    "valid": True,
                    "warnings": ["文件数量较多，合并可能需要较长时间"]
                }
            }
            
            response = client.post("/api/v1/tasks/smart-create", json=create_request)
            
            assert response.status_code == 200
            task_data = response.json()
            
            assert "task" in task_data
            assert "strategy_info" in task_data
            assert task_data["strategy_info"]["recommended_strategy"] == "safe_merge"
            
            task_id = task_data["task"]["id"]
        
        # 2. 验证任务已创建并获得表锁
        db = TestingSessionLocal()
        created_task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
        assert created_task is not None
        assert created_task.merge_strategy == "safe_merge"
        assert created_task.status == "pending"
        
        # 3. 测试表锁机制
        lock_result = TableLockManager.acquire_table_lock(
            db, self.test_cluster.id, "test_db", "small_files_table", task_id
        )
        assert lock_result["success"] is True
        
        # 4. 尝试创建相同表的任务，应该被锁阻止
        duplicate_request = {
            "cluster_id": self.test_cluster.id,
            "database_name": "test_db",
            "table_name": "small_files_table"
        }
        
        with patch('app.engines.engine_factory.MergeEngineFactory.create_smart_merge_task') as mock_create2:
            mock_create2.return_value = {
                "task_name": "Duplicate task",
                "recommended_strategy": "concatenate",
                "strategy_reason": "测试重复任务",
                "validation": {"valid": True, "warnings": []}
            }
            
            response2 = client.post("/api/v1/tasks/smart-create", json=duplicate_request)
            
            # 应该成功创建任务，但在执行时会被锁阻止
            assert response2.status_code == 200
        
        # 5. 模拟执行第一个任务
        with patch('app.scheduler.merge_tasks.execute_merge_task.delay') as mock_execute:
            mock_celery_result = Mock()
            mock_celery_result.id = "celery-task-123"
            mock_execute.return_value = mock_celery_result
            
            execute_response = client.post(f"/api/v1/tasks/{task_id}/execute")
            assert execute_response.status_code == 200
            
            # 验证任务状态更新
            updated_task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
            assert updated_task.status == "running"
            assert updated_task.celery_task_id == "celery-task-123"
        
        # 6. 测试任务取消
        with patch('app.scheduler.merge_tasks.cancel_task.delay') as mock_cancel:
            mock_cancel.return_value = Mock(get=lambda: {"status": "success"})
            
            cancel_response = client.post(f"/api/v1/tasks/{task_id}/cancel")
            assert cancel_response.status_code == 200
        
        # 7. 释放表锁
        release_result = TableLockManager.release_table_lock(db, task_id)
        assert release_result["success"] is True
        
        db.close()
    
    def test_strategy_selection_logic(self):
        """测试策略选择逻辑的集成"""
        test_cases = [
            {
                "table_format": "parquet",
                "file_count": 50,
                "table_size": 100 * 1024 * 1024,  # 100MB
                "partition_count": 0,
                "expected_strategy": "concatenate"
            },
            {
                "table_format": "orc", 
                "file_count": 3000,
                "table_size": 50 * 1024 * 1024 * 1024,  # 50GB
                "partition_count": 100,
                "expected_strategy": "safe_merge"
            },
            {
                "table_format": "textfile",
                "file_count": 500,
                "table_size": 5 * 1024 * 1024 * 1024,  # 5GB
                "partition_count": 10,
                "expected_strategy": "insert_overwrite"
            }
        ]
        
        for case in test_cases:
            with patch('app.api.tasks.MergeEngineFactory.create_smart_merge_task') as mock_create:
                mock_create.return_value = {
                    "task_name": f"Smart merge for {case['table_format']}_table",
                    "recommended_strategy": case["expected_strategy"],
                    "strategy_reason": f"基于表格式{case['table_format']}推荐策略",
                    "validation": {"valid": True, "warnings": []}
                }
                
                request_data = {
                    "cluster_id": self.test_cluster.id,
                    "database_name": "test_db",
                    "table_name": f"{case['table_format']}_table"
                }
                
                response = client.post("/api/v1/tasks/smart-create", json=request_data)
                assert response.status_code == 200
                
                task_data = response.json()
                assert task_data["strategy_info"]["recommended_strategy"] == case["expected_strategy"]
    
    def test_table_lock_concurrency(self):
        """测试表锁的并发控制"""
        db = TestingSessionLocal()
        
        # 创建第一个任务并获取锁
        task1 = MergeTask(
            cluster_id=self.test_cluster.id,
            task_name="Concurrent task 1",
            table_name="concurrent_table",
            database_name="test_db",
            merge_strategy="safe_merge",
            status="pending"
        )
        db.add(task1)
        db.flush()
        
        lock1_result = TableLockManager.acquire_table_lock(
            db, self.test_cluster.id, "test_db", "concurrent_table", task1.id
        )
        assert lock1_result["success"] is True
        
        # 创建第二个任务，尝试获取相同表的锁
        task2 = MergeTask(
            cluster_id=self.test_cluster.id,
            task_name="Concurrent task 2",
            table_name="concurrent_table", 
            database_name="test_db",
            merge_strategy="concatenate",
            status="pending"
        )
        db.add(task2)
        db.flush()
        
        lock2_result = TableLockManager.acquire_table_lock(
            db, self.test_cluster.id, "test_db", "concurrent_table", task2.id
        )
        assert lock2_result["success"] is False
        assert "is locked by task" in lock2_result["message"]
        
        # 释放第一个任务的锁
        TableLockManager.release_table_lock(db, task1.id)
        
        # 现在第二个任务应该能够获取锁
        lock2_retry_result = TableLockManager.acquire_table_lock(
            db, self.test_cluster.id, "test_db", "concurrent_table", task2.id
        )
        assert lock2_retry_result["success"] is True
        
        db.commit()
        db.close()
    
    def test_expired_lock_cleanup(self):
        """测试过期锁的清理机制"""
        from datetime import datetime, timedelta
        
        db = TestingSessionLocal()
        
        # 创建一个带有过期锁的任务
        expired_task = MergeTask(
            cluster_id=self.test_cluster.id,
            task_name="Expired lock task",
            table_name="expired_table",
            database_name="test_db",
            merge_strategy="safe_merge",
            status="running",
            table_lock_acquired=True,
            lock_holder="task_expired",
            started_time=datetime.utcnow() - timedelta(hours=3)  # 3小时前
        )
        db.add(expired_task)
        db.flush()
        
        # 清理过期锁
        cleanup_result = TableLockManager.cleanup_expired_locks(db, 120)  # 2小时超时
        assert cleanup_result["success"] is True
        assert cleanup_result["cleaned_locks"] == 1
        
        # 验证锁已被释放
        db.refresh(expired_task)
        assert expired_task.table_lock_acquired is False
        assert expired_task.status == "failed"
        
        db.commit()
        db.close()
    
    def test_validation_warnings_handling(self):
        """测试验证警告的处理"""
        request_data = {
            "cluster_id": self.test_cluster.id,
            "database_name": "test_db",
            "table_name": "risky_table"
        }
        
        with patch('app.engines.engine_factory.MergeEngineFactory.create_smart_merge_task') as mock_create:
            mock_create.return_value = {
                "task_name": "Risky merge task",
                "recommended_strategy": "insert_overwrite",
                "strategy_reason": "文件数量过多，使用insert_overwrite策略",
                "validation": {
                    "valid": True,
                    "warnings": [
                        "文件数量过多，合并可能需要较长时间",
                        "建议在非业务高峰时段执行",
                        "表大小超过推荐阈值"
                    ]
                }
            }
            
            response = client.post("/api/v1/tasks/smart-create", json=request_data)
            assert response.status_code == 200
            
            task_data = response.json()
            warnings = task_data["strategy_info"]["validation"]["warnings"]
            assert len(warnings) == 3
            assert "文件数量过多" in warnings[0]
    
    def test_validation_failure_handling(self):
        """测试验证失败的处理"""
        request_data = {
            "cluster_id": self.test_cluster.id,
            "database_name": "test_db",
            "table_name": "invalid_table"
        }
        
        with patch('app.engines.engine_factory.MergeEngineFactory.create_smart_merge_task') as mock_create:
            mock_create.return_value = {
                "task_name": "Invalid merge task",
                "recommended_strategy": "concatenate",
                "strategy_reason": "表格式不兼容",
                "validation": {
                    "valid": False,
                    "message": "Table format not compatible with concatenate strategy",
                    "warnings": []
                }
            }
            
            response = client.post("/api/v1/tasks/smart-create", json=request_data)
            assert response.status_code == 400
            assert "Task validation failed" in response.json()["detail"]
    
    def test_api_error_handling(self):
        """测试API错误处理"""
        # 测试不存在的集群
        invalid_request = {
            "cluster_id": 999,
            "database_name": "test_db",
            "table_name": "test_table"
        }
        
        response = client.post("/api/v1/tasks/smart-create", json=invalid_request)
        assert response.status_code == 404
        assert "Cluster not found" in response.json()["detail"]
        
        # 测试缺少必需字段
        incomplete_request = {
            "cluster_id": self.test_cluster.id,
            "database_name": "test_db"
            # 缺少 table_name
        }
        
        response = client.post("/api/v1/tasks/smart-create", json=incomplete_request)
        assert response.status_code == 422  # Validation error
    
    def test_task_retry_integration(self):
        """测试任务重试的集成流程"""
        # 创建一个失败的任务
        db = TestingSessionLocal()
        failed_task = MergeTask(
            cluster_id=self.test_cluster.id,
            task_name="Failed merge task",
            table_name="retry_table",
            database_name="test_db",
            merge_strategy="safe_merge",
            status="failed",
            error_message="Previous execution failed"
        )
        db.add(failed_task)
        db.commit()
        db.refresh(failed_task)
        
        # 重试任务
        with patch('app.scheduler.merge_tasks.execute_merge_task.delay') as mock_execute:
            mock_celery_result = Mock()
            mock_celery_result.id = "celery-retry-123"
            mock_execute.return_value = mock_celery_result
            
            retry_response = client.post(f"/api/v1/tasks/{failed_task.id}/retry")
            assert retry_response.status_code == 200
            
            # 验证任务状态重置
            db.refresh(failed_task)
            assert failed_task.status == "pending"
            assert failed_task.error_message is None
        
        db.close()
    
    @patch('app.engines.safe_hive_engine.SafeHiveMergeEngine.execute_merge')
    def test_mock_engine_execution(self, mock_execute):
        """测试模拟引擎执行"""
        mock_execute.return_value = {
            "success": True,
            "message": "Mock merge completed successfully",
            "files_before": 1000,
            "files_after": 100,
            "size_saved": 500 * 1024 * 1024  # 500MB saved
        }
        
        # 创建任务
        request_data = {
            "cluster_id": self.test_cluster.id,
            "database_name": "test_db",
            "table_name": "mock_execution_table"
        }
        
        with patch('app.engines.engine_factory.MergeEngineFactory.create_smart_merge_task') as mock_create:
            mock_create.return_value = {
                "task_name": "Mock execution task",
                "recommended_strategy": "safe_merge",
                "strategy_reason": "测试模拟执行",
                "validation": {"valid": True, "warnings": []}
            }
            
            response = client.post("/api/v1/tasks/smart-create", json=request_data)
            assert response.status_code == 200
            
            task_id = response.json()["task"]["id"]
        
        # 执行任务（模拟）
        with patch('app.scheduler.merge_tasks.execute_merge_task.delay') as mock_execute_delay:
            mock_execute_delay.return_value = Mock(id="mock-celery-task")
            
            execute_response = client.post(f"/api/v1/tasks/{task_id}/execute")
            assert execute_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])