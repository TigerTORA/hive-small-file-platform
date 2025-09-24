import pytest


@pytest.mark.unit
def test_metastore_and_hdfs_and_hs2_probes(monkeypatch):
    from app.services.enhanced_connection_service import EnhancedConnectionService

    svc = EnhancedConnectionService()

    class _C:
        hive_metastore_url = "mysql://user:pass@localhost:3306/hive"
        hdfs_namenode_url = "hdfs://localhost:9000"
        hdfs_user = "hdfs"
        hive_host = "127.0.0.1"
        hive_port = 10000

    cluster = _C()

    # metastore success
    import app.services.enhanced_connection_service as ecs

    class _MetaOK:
        def __init__(self, url):
            pass

        def test_connection(self):
            return {"status": "success"}

    monkeypatch.setattr(ecs, "MySQLHiveMetastoreConnector", _MetaOK)
    r1 = svc._test_metastore_connection(cluster)
    assert r1.status == "success"

    # metastore exception -> classified failure
    class _MetaFail:
        def __init__(self, url):
            pass

        def test_connection(self):
            raise Exception("timeout occurred")

    monkeypatch.setattr(ecs, "MySQLHiveMetastoreConnector", _MetaFail)
    r2 = svc._test_metastore_connection(cluster)
    assert r2.status == "failed" and r2.failure_type is not None

    # hdfs success and failure
    class _Hdfs:
        def __init__(self, url, user):
            pass

        def connect(self):
            return True

        def disconnect(self):
            pass

    monkeypatch.setattr(ecs, "WebHDFSScanner", _Hdfs)
    h1 = svc._test_hdfs_connection(cluster)
    assert h1.status == "success"

    class _HdfsBoom:
        def __init__(self, url, user):
            pass

        def connect(self):
            raise Exception("connection refused")

        def disconnect(self):
            pass

    monkeypatch.setattr(ecs, "WebHDFSScanner", _HdfsBoom)
    h2 = svc._test_hdfs_connection(cluster)
    assert h2.status == "failed" and h2.failure_type is not None

    # hs2 tcp refused path
    class _Sock:
        def __init__(self, *a, **k):
            pass

        def settimeout(self, t):
            pass

        def connect_ex(self, addr):
            return 111  # non-zero => refused

        def close(self):
            pass

    import socket as socket_mod

    monkeypatch.setattr(socket_mod, "socket", lambda *a, **k: _Sock())
    sres = svc._test_hiveserver2_connection(cluster)
    assert sres.status == "failed"


@pytest.mark.unit
def test_hs2_success_default_and_ldap(monkeypatch):
    import sys
    import types

    from app.services.enhanced_connection_service import EnhancedConnectionService

    svc = EnhancedConnectionService()

    class _SockOK:
        def __init__(self, *a, **k):
            pass

        def settimeout(self, t):
            pass

        def connect_ex(self, addr):
            return 0

        def close(self):
            pass

    class _Conn:
        def cursor(self):
            class C:
                def execute(self, q):
                    return None

                def fetchone(self):
                    return None

                def close(self):
                    return None

            return C()

        def close(self):
            pass

    class _Hive:
        def Connection(self, **kw):
            # ensure username present in either branch
            assert "username" in kw
            return _Conn()

    # inject fake pyhive.hive
    fake_pyhive = types.ModuleType("pyhive")
    fake_pyhive.hive = _Hive()
    sys.modules["pyhive"] = fake_pyhive

    import socket as socket_mod

    monkeypatch.setattr(socket_mod, "socket", lambda *a, **k: _SockOK())

    class _Cluster:
        hive_host = "127.0.0.1"
        hive_port = 10000
        auth_type = "NONE"
        hive_username = None
        hive_password = None

    # default auth path
    ok1 = svc._test_hiveserver2_connection(_Cluster())
    assert ok1.status == "success"

    # LDAP path
    class _ClusterLDAP(_Cluster):
        auth_type = "LDAP"
        hive_username = "u"
        hive_password = "p"

    ok2 = svc._test_hiveserver2_connection(_ClusterLDAP())
    assert ok2.status == "success"
