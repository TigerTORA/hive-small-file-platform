from app.services.path_resolver import PathResolver


class DummyCluster:
    def __init__(self):
        self.hive_host = "localhost"
        self.hive_port = 10000
        self.hive_metastore_url = "mysql://u:p@localhost:3306/hive"


def test_resolve_via_hs2_import_error_returns_none():
    # 未安装 pyhive 时应捕获异常并返回 None
    cluster = DummyCluster()
    loc = PathResolver._resolve_via_hs2(cluster, "db", "tbl")
    assert loc is None

