from unittest.mock import patch, MagicMock

from app.services.path_resolver import PathResolver


class DummyCluster:
    def __init__(self, metastore_url: str = "mysql://u:p@localhost:3306/hive"):
        self.hive_metastore_url = metastore_url
        self.hive_host = "localhost"
        self.hive_port = 10000
        self.hive_database = "default"


def test_get_table_location_via_hs2_fallback():
    cluster = DummyCluster()
    with patch("app.services.path_resolver.PathResolver._resolve_via_metastore", return_value=None):
        with patch("app.services.path_resolver.PathResolver._resolve_via_hs2", return_value="hdfs://nn:9000/wh/db/tbl"):
            loc = PathResolver.get_table_location(cluster, "db", "tbl")
            assert loc.endswith("/db/tbl") or loc.endswith("/wh/db/tbl")


def test_get_partition_locations_via_metastore():
    cluster = DummyCluster()

    class _Conn:
        def __enter__(self):
            m = MagicMock()
            m.get_table_partitions.return_value = [
                {"partition_path": "/warehouse/db/tbl/p1"},
                {"partition_path": "/warehouse/db/tbl/p2"},
                {"partition_path": None},
            ]
            return m

        def __exit__(self, exc_type, exc, tb):
            return False

    with patch(
        "app.services.path_resolver.MySQLHiveMetastoreConnector", return_value=_Conn()
    ):
        paths = PathResolver.get_partition_locations(cluster, "db", "tbl")
        assert "/warehouse/db/tbl/p1" in paths and "/warehouse/db/tbl/p2" in paths
        assert all(isinstance(p, str) for p in paths)

