"""
TableLockManager表锁管理器的单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.utils.table_lock_manager import TableLockManager
from app.models.merge_task import MergeTask


class TestTableLockManager:
    """测试TableLockManager的所有功能"""
    
    def setup_method(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.cluster_id = 1
        self.database_name = "test_db"
        self.table_name = "test_table"
        self.task_id = 123
    
    def test_acquire_table_lock_success(self):
        """测试成功获取表锁"""
        # 模拟没有现有锁
        self.mock_db.query().filter().first.return_value = None
        
        # 模拟当前任务
        current_task = MergeTask(
            id=self.task_id,
            cluster_id=self.cluster_id,
            database_name=self.database_name,
            table_name=self.table_name,
            table_lock_acquired=False
        )
        self.mock_db.query().filter().first.return_value = current_task
        
        result = TableLockManager.acquire_table_lock(
            self.mock_db, self.cluster_id, self.database_name, 
            self.table_name, self.task_id
        )
        
        assert result["success"] is True
        assert "Table lock acquired" in result["message"]
        assert result["lock_holder"] == f"task_{self.task_id}"
        assert current_task.table_lock_acquired is True
        assert current_task.lock_holder == f"task_{self.task_id}"
        self.mock_db.commit.assert_called_once()
    
    def test_acquire_table_lock_already_locked(self):
        """测试表已被其他任务锁定"""
        # 模拟存在锁定的任务
        existing_task = MergeTask(
            id=456,
            cluster_id=self.cluster_id,
            database_name=self.database_name,
            table_name=self.table_name,
            table_lock_acquired=True,
            lock_holder="task_456",
            status="running",
            started_time=datetime.utcnow()  # 锁未过期
        )
        
        # 第一次查询返回现有锁，第二次查询不会执行
        query_mock = self.mock_db.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = existing_task
        
        with patch.object(TableLockManager, '_is_lock_expired', return_value=False):
            result = TableLockManager.acquire_table_lock(
                self.mock_db, self.cluster_id, self.database_name, 
                self.table_name, self.task_id
            )
        
        assert result["success"] is False
        assert "is locked by task 456" in result["message"]
        assert result["locked_by_task"] == 456
        assert result["lock_holder"] == "task_456"
    
    def test_acquire_table_lock_expired_lock_cleanup(self):
        """测试清理过期锁并获取新锁"""
        # 模拟过期的锁定任务
        expired_task = MergeTask(
            id=456,
            cluster_id=self.cluster_id,
            database_name=self.database_name,
            table_name=self.table_name,
            table_lock_acquired=True,
            lock_holder="task_456",
            status="running",
            started_time=datetime.utcnow() - timedelta(hours=3)  # 过期锁
        )
        
        # 模拟当前任务
        current_task = MergeTask(
            id=self.task_id,
            cluster_id=self.cluster_id,
            database_name=self.database_name,
            table_name=self.table_name,
            table_lock_acquired=False
        )
        
        # 设置查询返回值
        query_results = [expired_task, current_task]
        self.mock_db.query().filter().first.side_effect = query_results
        
        with patch.object(TableLockManager, '_is_lock_expired', return_value=True) as mock_expired:
            with patch.object(TableLockManager, '_force_release_lock') as mock_release:
                result = TableLockManager.acquire_table_lock(
                    self.mock_db, self.cluster_id, self.database_name, 
                    self.table_name, self.task_id
                )
        
        assert result["success"] is True
        mock_expired.assert_called_once_with(expired_task, 120)
        mock_release.assert_called_once_with(self.mock_db, expired_task)
        assert current_task.table_lock_acquired is True
    
    def test_acquire_table_lock_task_not_found(self):
        """测试任务不存在的情况"""
        # 模拟没有现有锁
        query_mock = self.mock_db.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.side_effect = [None, None]  # 没有现有锁，也没有当前任务
        
        result = TableLockManager.acquire_table_lock(
            self.mock_db, self.cluster_id, self.database_name, 
            self.table_name, self.task_id
        )
        
        assert result["success"] is False
        assert f"Task {self.task_id} not found" in result["message"]
    
    def test_release_table_lock_success(self):
        """测试成功释放表锁"""
        task = MergeTask(
            id=self.task_id,
            cluster_id=self.cluster_id,
            database_name=self.database_name,
            table_name=self.table_name,
            table_lock_acquired=True,
            lock_holder=f"task_{self.task_id}"
        )
        
        self.mock_db.query().filter().first.return_value = task
        
        result = TableLockManager.release_table_lock(self.mock_db, self.task_id)
        
        assert result["success"] is True
        assert "Table lock released" in result["message"]
        assert task.table_lock_acquired is False
        assert task.lock_holder is None
        self.mock_db.commit.assert_called_once()
    
    def test_release_table_lock_no_lock_held(self):
        """测试释放未持有的锁"""
        task = MergeTask(
            id=self.task_id,
            cluster_id=self.cluster_id,
            database_name=self.database_name,
            table_name=self.table_name,
            table_lock_acquired=False,
            lock_holder=None
        )
        
        self.mock_db.query().filter().first.return_value = task
        
        result = TableLockManager.release_table_lock(self.mock_db, self.task_id)
        
        assert result["success"] is True
        assert "No lock was held" in result["message"]
    
    def test_release_table_lock_task_not_found(self):
        """测试释放不存在任务的锁"""
        self.mock_db.query().filter().first.return_value = None
        
        result = TableLockManager.release_table_lock(self.mock_db, self.task_id)
        
        assert result["success"] is False
        assert f"Task {self.task_id} not found" in result["message"]
    
    def test_check_table_lock_status_locked(self):
        """测试检查表锁状态 - 已锁定"""
        locked_task = MergeTask(
            id=456,
            cluster_id=self.cluster_id,
            database_name=self.database_name,
            table_name=self.table_name,
            table_lock_acquired=True,
            lock_holder="task_456",
            status="running",
            started_time=datetime.utcnow()
        )
        
        self.mock_db.query().filter().first.return_value = locked_task
        
        result = TableLockManager.check_table_lock_status(
            self.mock_db, self.cluster_id, self.database_name, self.table_name
        )
        
        assert result["locked"] is True
        assert result["locked_by_task"] == 456
        assert result["lock_holder"] == "task_456"
        assert result["task_status"] == "running"
        assert result["locked_since"] == locked_task.started_time
    
    def test_check_table_lock_status_not_locked(self):
        """测试检查表锁状态 - 未锁定"""
        self.mock_db.query().filter().first.return_value = None
        
        result = TableLockManager.check_table_lock_status(
            self.mock_db, self.cluster_id, self.database_name, self.table_name
        )
        
        assert result["locked"] is False
        assert "is not locked" in result["message"]
    
    def test_cleanup_expired_locks(self):
        """测试清理过期锁"""
        # 创建一个过期任务和一个未过期任务
        expired_task = MergeTask(
            id=456,
            table_lock_acquired=True,
            status="running",
            started_time=datetime.utcnow() - timedelta(hours=3)
        )
        
        active_task = MergeTask(
            id=789,
            table_lock_acquired=True,
            status="running",
            started_time=datetime.utcnow()
        )
        
        self.mock_db.query().filter().all.return_value = [expired_task, active_task]
        
        with patch.object(TableLockManager, '_is_lock_expired') as mock_expired:
            with patch.object(TableLockManager, '_force_release_lock') as mock_release:
                # 第一个任务过期，第二个未过期
                mock_expired.side_effect = [True, False]
                
                result = TableLockManager.cleanup_expired_locks(self.mock_db, 120)
        
        assert result["success"] is True
        assert result["cleaned_locks"] == 1
        mock_release.assert_called_once_with(self.mock_db, expired_task)
        self.mock_db.commit.assert_called_once()
    
    def test_is_lock_expired_true(self):
        """测试锁过期检查 - 已过期"""
        task = MergeTask(
            table_lock_acquired=True,
            started_time=datetime.utcnow() - timedelta(hours=3)
        )
        
        result = TableLockManager._is_lock_expired(task, 120)  # 2小时超时
        assert result is True
    
    def test_is_lock_expired_false(self):
        """测试锁过期检查 - 未过期"""
        task = MergeTask(
            table_lock_acquired=True,
            started_time=datetime.utcnow() - timedelta(minutes=30)
        )
        
        result = TableLockManager._is_lock_expired(task, 120)  # 2小时超时
        assert result is False
    
    def test_is_lock_expired_no_lock(self):
        """测试锁过期检查 - 无锁"""
        task = MergeTask(
            table_lock_acquired=False,
            started_time=datetime.utcnow() - timedelta(hours=3)
        )
        
        result = TableLockManager._is_lock_expired(task, 120)
        assert result is False
    
    def test_is_lock_expired_no_time(self):
        """测试锁过期检查 - 无时间信息"""
        task = MergeTask(
            table_lock_acquired=True,
            started_time=None,
            created_time=None
        )
        
        result = TableLockManager._is_lock_expired(task, 120)
        assert result is False
    
    def test_force_release_lock_running_task(self):
        """测试强制释放运行中任务的锁"""
        task = MergeTask(
            id=456,
            database_name="test_db",
            table_name="test_table",
            table_lock_acquired=True,
            lock_holder="task_456",
            status="running"
        )
        
        TableLockManager._force_release_lock(self.mock_db, task)
        
        assert task.table_lock_acquired is False
        assert task.lock_holder is None
        assert task.status == "failed"
        assert "lock expired" in task.error_message
        assert task.completed_time is not None
    
    def test_force_release_lock_pending_task(self):
        """测试强制释放待执行任务的锁"""
        task = MergeTask(
            id=456,
            database_name="test_db",
            table_name="test_table",
            table_lock_acquired=True,
            lock_holder="task_456",
            status="pending"
        )
        
        TableLockManager._force_release_lock(self.mock_db, task)
        
        assert task.table_lock_acquired is False
        assert task.lock_holder is None
        # pending状态的任务不会被标记为失败
        assert task.status == "pending"
    
    def test_get_all_table_locks(self):
        """测试获取所有表锁信息"""
        task1 = MergeTask(
            id=123,
            cluster_id=1,
            database_name="db1",
            table_name="table1",
            table_lock_acquired=True,
            lock_holder="task_123",
            status="running",
            started_time=datetime.utcnow(),
            merge_strategy="safe_merge"
        )
        
        task2 = MergeTask(
            id=456,
            cluster_id=2,
            database_name="db2",
            table_name="table2",
            table_lock_acquired=True,
            lock_holder="task_456",
            status="pending",
            created_time=datetime.utcnow(),
            merge_strategy="concatenate"
        )
        
        self.mock_db.query().filter().all.return_value = [task1, task2]
        
        result = TableLockManager.get_all_table_locks(self.mock_db)
        
        assert result["success"] is True
        assert result["total_locks"] == 2
        
        locks = result["locks"]
        assert len(locks) == 2
        
        lock1 = locks[0]
        assert lock1["task_id"] == 123
        assert lock1["cluster_id"] == 1
        assert lock1["database_name"] == "db1"
        assert lock1["table_name"] == "table1"
        assert lock1["lock_holder"] == "task_123"
        assert lock1["task_status"] == "running"
        assert lock1["strategy"] == "safe_merge"
    
    def test_get_all_table_locks_with_cluster_filter(self):
        """测试获取指定集群的表锁信息"""
        task1 = MergeTask(id=123, cluster_id=1, table_lock_acquired=True)
        task2 = MergeTask(id=456, cluster_id=2, table_lock_acquired=True)
        
        # 模拟查询链式调用
        query_mock = self.mock_db.query.return_value
        filter_mock1 = query_mock.filter.return_value
        filter_mock2 = filter_mock1.filter.return_value
        filter_mock2.all.return_value = [task1]  # 只返回集群1的任务
        
        result = TableLockManager.get_all_table_locks(self.mock_db, cluster_id=1)
        
        assert result["success"] is True
        assert result["total_locks"] == 1
    
    def test_error_handling_in_acquire_lock(self):
        """测试获取锁时的错误处理"""
        self.mock_db.query.side_effect = Exception("Database error")
        
        result = TableLockManager.acquire_table_lock(
            self.mock_db, self.cluster_id, self.database_name, 
            self.table_name, self.task_id
        )
        
        assert result["success"] is False
        assert "Failed to acquire lock" in result["message"]
        self.mock_db.rollback.assert_called_once()
    
    def test_error_handling_in_release_lock(self):
        """测试释放锁时的错误处理"""
        self.mock_db.query.side_effect = Exception("Database error")
        
        result = TableLockManager.release_table_lock(self.mock_db, self.task_id)
        
        assert result["success"] is False
        assert "Failed to release lock" in result["message"]
        self.mock_db.rollback.assert_called_once()
    
    def test_error_handling_in_cleanup_locks(self):
        """测试清理锁时的错误处理"""
        self.mock_db.query.side_effect = Exception("Database error")
        
        result = TableLockManager.cleanup_expired_locks(self.mock_db)
        
        assert result["success"] is False
        assert "error" in result
        self.mock_db.rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])