"""
测试重构后的表管理API模块
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.table_management import router
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/tables")
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """创建模拟数据库会话"""
    return Mock(spec=Session)


@pytest.fixture
def sample_table_metrics():
    """创建示例表指标数据"""
    metrics = []
    for i in range(3):
        metric = Mock(spec=TableMetric)
        metric.id = i + 1
        metric.cluster_id = 1
        metric.database_name = f"test_db_{i}"
        metric.table_name = f"test_table_{i}"
        metric.total_files = 100 + i * 10
        metric.small_files = 50 + i * 5
        metric.total_size = 1024 * 1024 * (100 + i * 50)
        metric.avg_file_size = 1024 * 1024
        metric.table_type = "MANAGED"
        metric.storage_format = "PARQUET"
        metric.table_path = f"/warehouse/test_db_{i}.db/test_table_{i}"
        metric.is_partitioned = False
        metric.partition_count = 0
        metric.scan_time = "2024-01-01T10:00:00"
        metric.scan_duration = 30.5
        metrics.append(metric)
    return metrics


class TestTableManagementAPI:
    """测试表管理API"""

    @patch("app.api.table_management.get_db")
    def test_get_table_metrics_success(
        self, mock_get_db, client, mock_db_session, sample_table_metrics
    ):
        """测试获取表指标成功"""
        mock_get_db.return_value = mock_db_session

        # 模拟查询最新记录的逻辑
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [Mock(max_id=1), Mock(max_id=2), Mock(max_id=3)]

        mock_final_query = Mock()
        mock_final_query.filter.return_value = mock_final_query
        mock_final_query.order_by.return_value = mock_final_query
        mock_final_query.all.return_value = sample_table_metrics

        mock_db_session.query.side_effect = [mock_query, mock_final_query]

        response = client.get("/api/v1/tables/metrics?cluster_id=1")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["cluster_id"] == 1
        assert data[0]["database_name"] == "test_db_0"

    @patch("app.api.table_management.get_db")
    def test_get_table_metrics_with_database_filter(
        self, mock_get_db, client, mock_db_session, sample_table_metrics
    ):
        """测试带数据库过滤的表指标查询"""
        mock_get_db.return_value = mock_db_session

        # 模拟过滤特定数据库的查询
        filtered_metrics = [
            m for m in sample_table_metrics if m.database_name == "test_db_1"
        ]

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [Mock(max_id=2)]

        mock_final_query = Mock()
        mock_final_query.filter.return_value = mock_final_query
        mock_final_query.order_by.return_value = mock_final_query
        mock_final_query.all.return_value = filtered_metrics

        mock_db_session.query.side_effect = [mock_query, mock_final_query]

        response = client.get(
            "/api/v1/tables/metrics?cluster_id=1&database_name=test_db_1"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["database_name"] == "test_db_1"

    @patch("app.api.table_management.get_db")
    def test_get_table_metrics_no_data(self, mock_get_db, client, mock_db_session):
        """测试没有数据时的表指标查询"""
        mock_get_db.return_value = mock_db_session

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = []

        mock_db_session.query.return_value = mock_query

        response = client.get("/api/v1/tables/metrics?cluster_id=999")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    @patch("app.api.table_management.get_db")
    def test_get_small_file_summary(
        self, mock_get_db, client, mock_db_session, sample_table_metrics
    ):
        """测试获取小文件统计摘要"""
        mock_get_db.return_value = mock_db_session

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = sample_table_metrics

        mock_db_session.query.return_value = mock_query

        response = client.get("/api/v1/tables/small-files?cluster_id=1")

        assert response.status_code == 200
        data = response.json()

        assert "total_tables" in data
        assert "tables_with_small_files" in data
        assert "total_small_files" in data
        assert "small_file_ratio" in data

        assert data["total_tables"] == 3
        assert data["tables_with_small_files"] == 3  # 所有测试表都有小文件
        assert data["total_small_files"] == 165  # 50 + 55 + 60

    @patch("app.api.table_management.get_db")
    def test_get_databases(self, mock_get_db, client, mock_db_session):
        """测试获取数据库列表"""
        mock_get_db.return_value = mock_db_session

        # 模拟集群存在检查
        mock_cluster = Mock(spec=Cluster)
        mock_cluster.id = 1
        mock_cluster.name = "test-cluster"

        # 模拟数据库查询
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = [("test_db_1",), ("test_db_2",), ("test_db_3",)]

        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_cluster)))),
            mock_query,
        ]

        response = client.get("/api/v1/tables/databases/1")

        assert response.status_code == 200
        data = response.json()
        assert "databases" in data
        assert len(data["databases"]) == 3
        assert "test_db_1" in data["databases"]

    @patch("app.api.table_management.get_db")
    def test_get_databases_cluster_not_found(
        self, mock_get_db, client, mock_db_session
    ):
        """测试集群不存在时获取数据库列表"""
        mock_get_db.return_value = mock_db_session

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/api/v1/tables/databases/999")

        assert response.status_code == 404
        assert "Cluster not found" in response.json()["detail"]

    @patch("app.api.table_management.get_db")
    def test_get_tables(self, mock_get_db, client, mock_db_session):
        """测试获取表列表"""
        mock_get_db.return_value = mock_db_session

        # 模拟集群存在检查
        mock_cluster = Mock(spec=Cluster)
        mock_cluster.id = 1

        # 模拟表查询
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = [("table_1",), ("table_2",), ("table_3",)]

        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_cluster)))),
            mock_query,
        ]

        response = client.get("/api/v1/tables/tables/1/test_database")

        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert len(data["tables"]) == 3
        assert "table_1" in data["tables"]

    @patch("app.api.table_management.get_db")
    def test_get_table_detail_success(self, mock_get_db, client, mock_db_session):
        """测试获取表详细信息成功"""
        mock_get_db.return_value = mock_db_session

        # 创建模拟的最新表指标
        latest_metric = Mock(spec=TableMetric)
        latest_metric.cluster_id = 1
        latest_metric.database_name = "test_db"
        latest_metric.table_name = "test_table"
        latest_metric.table_type = "MANAGED"
        latest_metric.storage_format = "PARQUET"
        latest_metric.table_path = "/warehouse/test_db.db/test_table"
        latest_metric.is_partitioned = True
        latest_metric.partition_count = 10
        latest_metric.table_owner = "hive"
        latest_metric.table_create_time = "2024-01-01T00:00:00"
        latest_metric.total_files = 100
        latest_metric.small_files = 50
        latest_metric.total_size = 1024 * 1024 * 100
        latest_metric.avg_file_size = 1024 * 1024
        latest_metric.scan_time = "2024-01-01T10:00:00"
        latest_metric.scan_duration = 30.5
        latest_metric.is_cold_data = False
        latest_metric.last_access_time = "2024-01-01T09:00:00"
        latest_metric.days_since_last_access = 1
        latest_metric.archive_status = "active"
        latest_metric.archive_location = None
        latest_metric.archived_at = None

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = latest_metric

        mock_db_session.query.return_value = mock_query

        response = client.get("/api/v1/tables/table-detail/1/test_db/test_table")

        assert response.status_code == 200
        data = response.json()

        assert "table_info" in data
        assert "file_metrics" in data
        assert "scan_info" in data
        assert "cold_data_info" in data

        assert data["table_info"]["cluster_id"] == 1
        assert data["table_info"]["database_name"] == "test_db"
        assert data["table_info"]["table_name"] == "test_table"
        assert data["file_metrics"]["total_files"] == 100
        assert data["file_metrics"]["small_files"] == 50

    @patch("app.api.table_management.get_db")
    def test_get_table_detail_not_found(self, mock_get_db, client, mock_db_session):
        """测试表详情不存在"""
        mock_get_db.return_value = mock_db_session

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        mock_db_session.query.return_value = mock_query

        response = client.get(
            "/api/v1/tables/table-detail/1/nonexistent_db/nonexistent_table"
        )

        assert response.status_code == 404
        assert "not found or not scanned" in response.json()["detail"]

    @patch("app.api.table_management.get_db")
    def test_get_table_scan_history(
        self, mock_get_db, client, mock_db_session, sample_table_metrics
    ):
        """测试获取表扫描历史"""
        mock_get_db.return_value = mock_db_session

        # 创建历史记录（按时间倒序）
        history_metrics = sample_table_metrics[:2]  # 只返回前两条作为历史记录

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = history_metrics

        mock_db_session.query.return_value = mock_query

        response = client.get(
            "/api/v1/tables/table-history/1/test_db/test_table?limit=5"
        )

        assert response.status_code == 200
        data = response.json()

        assert "table_name" in data
        assert "scan_count" in data
        assert "history" in data

        assert data["table_name"] == "test_db.test_table"
        assert data["scan_count"] == 2
        assert len(data["history"]) == 2

    def test_missing_cluster_id_parameter(self, client):
        """测试缺少cluster_id参数"""
        response = client.get("/api/v1/tables/metrics")

        assert response.status_code == 422  # FastAPI validation error

    @patch("app.api.table_management.get_db")
    def test_database_error_handling(self, mock_get_db, client, mock_db_session):
        """测试数据库错误处理"""
        mock_get_db.return_value = mock_db_session
        mock_db_session.query.side_effect = Exception("Database connection error")

        response = client.get("/api/v1/tables/metrics?cluster_id=1")

        assert response.status_code == 500
