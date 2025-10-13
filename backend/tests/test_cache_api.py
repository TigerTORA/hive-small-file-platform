import os

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app


@pytest.fixture(autouse=True)
def enable_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    settings.DEMO_MODE = True


client = TestClient(app)


def test_dashboard_summary_cache_only():
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_clusters" in data
    assert "total_tables" in data
    assert data["total_clusters"] >= 0


def test_table_cached_info():
    resp = client.get("/api/v1/tables/3/cdp14_lab/cdp14_archive_01/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["table_name"] == "cdp14_archive_01"
    assert data["database_name"] in {"cdp14_lab", "default"}


def test_partition_metrics_disabled_demo():
    resp = client.get(
        "/api/v1/tables/partition-metrics",
        params={
            "cluster_id": 3,
            "database_name": "cdp14_lab",
            "table_name": "cdp14_archive_01",
        },
    )
    assert resp.status_code == 503
    data = resp.json()
    assert "require Hive" in data["detail"]
