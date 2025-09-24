import pytest


@pytest.mark.unit
def test_dashboard_summary_empty_db(client):
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    data = r.json()
    # 空库下应为 0 或近似 0
    for key in [
        "total_clusters",
        "active_clusters",
        "total_tables",
        "monitored_tables",
        "total_files",
        "total_small_files",
    ]:
        assert data.get(key) == 0
    assert isinstance(data.get("small_file_ratio"), float)
    assert isinstance(data.get("total_size_gb"), float)
    assert isinstance(data.get("small_file_size_gb"), float)
