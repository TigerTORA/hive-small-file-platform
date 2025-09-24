from unittest.mock import MagicMock, patch

from app.services.path_resolver import PathResolver


class DummyCluster:
    def __init__(self, metastore_url: str = "mysql://u:p@localhost:3306/hive"):
        self.hive_metastore_url = metastore_url
        self.hive_host = "localhost"
        self.hive_port = 10000
        self.hive_database = "default"


def test_get_table_location_via_metastore():
    cluster = DummyCluster()

    class _Conn:
        def __enter__(self):
            m = MagicMock()
            m.get_table_location.return_value = "/warehouse/db/table"
            return m

        def __exit__(self, exc_type, exc, tb):
            return False

    with patch(
        "app.services.path_resolver.MySQLHiveMetastoreConnector", return_value=_Conn()
    ):
        loc = PathResolver.get_table_location(cluster, "db", "table")
        assert loc == "/warehouse/db/table"


def test_get_table_location_fallback_default_path():
    # 当 metastore 与 hs2 都失败时，回退到默认仓库路径
    cluster = DummyCluster("postgresql://u:p@localhost:5432/hive")
    with patch(
        "app.services.path_resolver.HiveMetastoreConnector", side_effect=Exception("x")
    ):
        with patch(
            "app.services.path_resolver.PathResolver._resolve_via_hs2",
            return_value=None,
        ):
            loc = PathResolver.get_table_location(cluster, "db2", "tbl2")
            assert loc.endswith("/db2.db/tbl2")
