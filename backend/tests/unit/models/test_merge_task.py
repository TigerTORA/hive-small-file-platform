"""
Unit tests for MergeTask model
"""
import pytest
from datetime import datetime, timezone

from app.models.merge_task import MergeTask
from tests.factories import ClusterFactory, MergeTaskFactory


class TestMergeTaskModel:
    """Test cases for MergeTask model"""
    
    @pytest.mark.unit
    def test_create_merge_task(self, db_session):
        """Test creating a new merge task"""
        cluster = ClusterFactory()
        db_session.add(cluster)
        db_session.commit()
        
        merge_task = MergeTask(
            cluster_id=cluster.id,
            task_name="test_merge_task",
            database_name="test_db",
            table_name="test_table",
            partition_filter="dt='2024-01-01'",
            merge_strategy="concatenate",
            target_file_size=134217728,
            status="pending"
        )
        
        db_session.add(merge_task)
        db_session.commit()
        
        # Verify task was created
        assert merge_task.id is not None
        assert merge_task.task_name == "test_merge_task"
        assert merge_task.database_name == "test_db"
        assert merge_task.table_name == "test_table"
        assert merge_task.status == "pending"
        assert merge_task.merge_strategy == "concatenate"
        assert merge_task.created_time is not None
    
    @pytest.mark.unit
    def test_merge_task_factory(self, db_session):
        """Test merge task factory creation"""
        task = MergeTaskFactory()
        db_session.add(task)
        db_session.commit()
        
        assert task.id is not None
        assert task.task_name.startswith("merge_task_")
        assert task.database_name.startswith("database_")
        assert task.table_name.startswith("table_")
        assert task.status == "pending"
        assert task.merge_strategy in ["concatenate", "insert_overwrite"]
    
    @pytest.mark.unit
    def test_task_status_values(self, db_session):
        """Test different task status values"""
        statuses = ["pending", "running", "success", "failed"]
        
        for status in statuses:
            task = MergeTaskFactory(status=status)
            db_session.add(task)
            db_session.commit()
            
            assert task.status == status
            db_session.delete(task)
            db_session.commit()
    
    @pytest.mark.unit
    def test_merge_strategy_values(self, db_session):
        """Test different merge strategies"""
        strategies = ["concatenate", "insert_overwrite"]
        
        for strategy in strategies:
            task = MergeTaskFactory(merge_strategy=strategy)
            db_session.add(task)
            db_session.commit()
            
            assert task.merge_strategy == strategy
            db_session.delete(task)
            db_session.commit()
    
    @pytest.mark.unit
    def test_partition_filter_handling(self, db_session):
        """Test partition filter handling"""
        # Non-partitioned table (no filter)
        task1 = MergeTaskFactory(partition_filter=None)
        db_session.add(task1)
        db_session.commit()
        
        assert task1.partition_filter is None
        
        # Partitioned table with filter
        task2 = MergeTaskFactory(
            table_name="partitioned_table",
            partition_filter="year=2024 AND month=12"
        )
        db_session.add(task2)
        db_session.commit()
        
        assert task2.partition_filter == "year=2024 AND month=12"
    
    @pytest.mark.unit
    def test_task_timing_fields(self, db_session):
        """Test task timing related fields"""
        task = MergeTaskFactory()
        db_session.add(task)
        db_session.commit()
        
        # Initially only created_time should be set
        assert task.created_time is not None
        assert task.started_time is None
        assert task.completed_time is None
        
        # Simulate task progression
        current_time = datetime.now(timezone.utc)
        task.status = "running"
        task.started_time = current_time
        db_session.commit()
        
        assert task.started_time is not None
        assert task.started_time >= task.created_time
    
    @pytest.mark.unit
    def test_target_file_size_setting(self, db_session):
        """Test target file size configuration"""
        # Default size
        task1 = MergeTaskFactory()
        db_session.add(task1)
        db_session.commit()
        
        assert task1.target_file_size is not None
        assert task1.target_file_size > 0
        
        # Custom size (256MB)
        task2 = MergeTaskFactory(
            table_name="custom_table",
            target_file_size=268435456
        )
        db_session.add(task2)
        db_session.commit()
        
        assert task2.target_file_size == 268435456
    
    @pytest.mark.unit
    def test_task_cluster_relationship(self, db_session):
        """Test relationship with cluster"""
        cluster = ClusterFactory()
        db_session.add(cluster)
        db_session.commit()
        
        task = MergeTaskFactory(cluster_id=cluster.id)
        db_session.add(task)
        db_session.commit()
        
        assert task.cluster_id == cluster.id
    
    @pytest.mark.unit
    def test_celery_task_id_tracking(self, db_session):
        """Test Celery task ID tracking"""
        task = MergeTaskFactory()
        db_session.add(task)
        db_session.commit()
        
        # Initially no Celery task ID
        assert task.celery_task_id is None
        
        # Set Celery task ID when task starts
        celery_id = "12345-abcde-67890-fghij"
        task.celery_task_id = celery_id
        task.status = "running"
        db_session.commit()
        
        assert task.celery_task_id == celery_id
    
    @pytest.mark.unit
    def test_error_message_handling(self, db_session):
        """Test error message storage"""
        task = MergeTaskFactory()
        db_session.add(task)
        db_session.commit()
        
        # Initially no error
        assert task.error_message is None
        
        # Set error when task fails
        error_msg = "Failed to connect to HDFS NameNode"
        task.status = "failed"
        task.error_message = error_msg
        db_session.commit()
        
        assert task.error_message == error_msg
    
    @pytest.mark.unit
    def test_files_before_after_tracking(self, db_session):
        """Test file count tracking"""
        task = MergeTaskFactory(files_before=100)
        db_session.add(task)
        db_session.commit()
        
        assert task.files_before == 100
        assert task.files_after is None
        assert task.size_saved is None
        
        # Complete task and set results
        task.files_after = 25
        task.size_saved = 1073741824  # 1GB saved
        task.status = "success"
        db_session.commit()
        
        assert task.files_after == 25
        assert task.size_saved == 1073741824
        
        # Verify improvement
        assert task.files_after < task.files_before
    
    @pytest.mark.unit
    def test_task_name_requirement(self, db_session):
        """Test that task name is required"""
        cluster = ClusterFactory()
        db_session.add(cluster)
        db_session.commit()
        
        # Task name should be required
        task = MergeTask(
            cluster_id=cluster.id,
            task_name="required_task_name",
            database_name="test_db",
            table_name="test_table"
        )
        
        db_session.add(task)
        db_session.commit()
        
        assert task.task_name == "required_task_name"
    
    @pytest.mark.unit
    def test_default_merge_strategy(self, db_session):
        """Test default merge strategy"""
        cluster = ClusterFactory()
        db_session.add(cluster)
        db_session.commit()
        
        task = MergeTask(
            cluster_id=cluster.id,
            task_name="default_strategy_test",
            database_name="test_db",
            table_name="test_table"
        )
        
        db_session.add(task)
        db_session.commit()
        
        # Should default to "concatenate"
        assert task.merge_strategy == "concatenate"
    
    @pytest.mark.unit
    def test_default_status(self, db_session):
        """Test default task status"""
        cluster = ClusterFactory()
        db_session.add(cluster)
        db_session.commit()
        
        task = MergeTask(
            cluster_id=cluster.id,
            task_name="default_status_test",
            database_name="test_db",
            table_name="test_table"
        )
        
        db_session.add(task)
        db_session.commit()
        
        # Should default to "pending"
        assert task.status == "pending"