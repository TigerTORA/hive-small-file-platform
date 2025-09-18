"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import Base, get_db
from app.models import Cluster, TableMetric, PartitionMetric, MergeTask, TaskLog, ClusterStatusHistory, ScanTask, ScanTaskLogDB

# Test database URL (SQLite in memory)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create test database session"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_cluster_data():
    """Sample cluster data for testing"""
    return {
        "name": "test-cluster",
        "description": "Test cluster for unit tests",
        "hive_host": "localhost",
        "hive_port": 10000,
        "metastore_url": "mysql://user:pass@localhost:3306/hive",
        "hdfs_namenode": "hdfs://localhost:9000",
        "small_file_threshold": 134217728,
        "is_active": True
    }


@pytest.fixture  
def sample_table_metric_data():
    """Sample table metric data for testing"""
    return {
        "database_name": "test_db",
        "table_name": "test_table", 
        "table_type": "MANAGED_TABLE",
        "is_partitioned": False,
        "total_files": 100,
        "small_files": 75,
        "total_size": 1073741824,
        "small_files_size": 536870912,
        "avg_file_size": 10737418.24,
        "compression_ratio": 0.5
    }


@pytest.fixture
def sample_merge_task_data():
    """Sample merge task data for testing"""
    return {
        "database_name": "test_db",
        "table_name": "test_table",
        "partition_spec": "",
        "merge_strategy": "CONCATENATE",
        "estimated_duration": 300,
        "priority": 1,
        "description": "Test merge task"
    }