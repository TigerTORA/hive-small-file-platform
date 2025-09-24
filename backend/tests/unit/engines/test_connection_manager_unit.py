import pytest

from app.engines.connection_manager import HiveConnectionManager
from app.models.cluster import Cluster


def _mk_cluster(hpass=None) -> Cluster:
    return Cluster(
        name="c",
        description="",
        hive_host="localhost",
        hive_port=10000,
        hive_metastore_url="mysql://user:pass@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
        hive_password=hpass,
    )


@pytest.mark.unit
def test_init_hive_password_none(monkeypatch):
    c = _mk_cluster(hpass=None)
    mgr = HiveConnectionManager(c)
    assert mgr.hive_password is None


@pytest.mark.unit
def test_get_hive_connection_and_cleanup(monkeypatch):
    import app.engines.connection_manager as cm_mod

    class _Conn:
        def cursor(self):
            class _Cur:
                def execute(self, sql):
                    return None

                def fetchone(self):
                    return (1,)

            return _Cur()

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Hive:
        def Connection(self, **kw):
            return _Conn()

    class _Meta:
        def __enter__(self):
            class _C:
                def test_connection(self):
                    return True

            return _C()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Web:
        def __init__(self, *a, **k):
            pass

        def test_connection(self):
            return True

        def close(self):
            pass

    monkeypatch.setattr(cm_mod, "hive", _Hive())
    monkeypatch.setattr(cm_mod, "HiveMetastoreConnector", lambda url: _Meta())
    monkeypatch.setattr(cm_mod, "WebHDFSClient", _Web)

    mgr = HiveConnectionManager(_mk_cluster())
    # success path for test_connections
    assert mgr.test_connections() is True

    # reuse cached connection then cleanup
    conn = mgr.get_hive_connection("default")
    assert conn is not None
    mgr.cleanup_connections()
    assert mgr._hive_connection is None
