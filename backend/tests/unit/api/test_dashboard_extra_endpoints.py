import pytest


@pytest.mark.unit
def test_dashboard_trends_empty(client):
    r = client.get("/api/v1/dashboard/trends")
    assert r.status_code == 200
    assert isinstance(r.json(), list) and len(r.json()) == 0


@pytest.mark.unit
def test_dashboard_file_distribution_empty(client):
    r = client.get("/api/v1/dashboard/file-distribution")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    # 默认 4 个区间
    assert len(body) == 4
    assert set(body[0].keys()) >= {"size_range", "count", "size_gb", "percentage"}


@pytest.mark.unit
def test_dashboard_top_tables_empty(client):
    r = client.get("/api/v1/dashboard/top-tables")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.unit
def test_dashboard_recent_tasks_empty(client):
    r = client.get("/api/v1/dashboard/recent-tasks")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.unit
def test_dashboard_cluster_stats_empty(client):
    r = client.get("/api/v1/dashboard/cluster-stats")
    assert r.status_code == 200
    body = r.json()
    assert "clusters" in body and isinstance(body["clusters"], list)
    assert "summary" in body and isinstance(body["summary"], dict)


@pytest.mark.unit
def test_dashboard_table_file_counts_empty(client):
    r = client.get("/api/v1/dashboard/table-file-counts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.unit
def test_dashboard_table_file_trends_invalid_format(client):
    r = client.get("/api/v1/dashboard/table-file-trends/invalid-format")
    assert r.status_code == 400


@pytest.mark.unit
def test_dashboard_trends_cluster_not_found_404(client):
    r = client.get("/api/v1/dashboard/trends", params={"cluster_id": 1})
    assert r.status_code == 404


@pytest.mark.unit
def test_dashboard_file_distribution_cluster_not_found_404(client):
    r = client.get("/api/v1/dashboard/file-distribution", params={"cluster_id": 1})
    assert r.status_code == 404


@pytest.mark.unit
def test_dashboard_top_tables_cluster_not_found_404(client):
    r = client.get("/api/v1/dashboard/top-tables", params={"cluster_id": 1})
    assert r.status_code == 404


@pytest.mark.unit
def test_dashboard_table_file_counts_cluster_not_found_404(client):
    r = client.get("/api/v1/dashboard/table-file-counts", params={"cluster_id": 1})
    assert r.status_code == 404


@pytest.mark.unit
def test_dashboard_table_file_trends_cluster_not_found_404(client):
    # 合法格式，但集群不存在
    r = client.get("/api/v1/dashboard/table-file-trends/1:db:tbl")
    assert r.status_code == 404
