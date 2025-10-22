import os
from types import SimpleNamespace

import pytest

from app.utils import webhdfs_client as module
from app.utils.kerberos_diagnostics import (
    KerberosDiagnosticCode,
    KerberosDiagnosticError,
)


@pytest.mark.unit
def test_webhdfs_client_configures_kerberos(monkeypatch, tmp_path):
    monkeypatch.setattr(module, "REQUESTS_KERBEROS_AVAILABLE", True)
    fake_auth = object()
    monkeypatch.setattr(
        module, "HTTPKerberosAuth", lambda mutual_authentication=None: fake_auth
    )
    monkeypatch.setattr(module, "KRB_OPTIONAL", "OPTIONAL")

    run_calls = []

    def fake_run(cmd, check, stdout, stderr, env, text):
        run_calls.append((cmd, env))

        class Result:
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.delenv("KRB5CCNAME", raising=False)

    keytab = tmp_path / "test.keytab"
    keytab.write_bytes(b"dummy")
    cache_path = tmp_path / "krb5cc_cache"

    cluster = SimpleNamespace(
        hdfs_namenode_url="http://namenode:9870",
        hdfs_user="hdfs",
        auth_type="KERBEROS",
        kerberos_principal="hive/service",
        kerberos_keytab_path=str(keytab),
        kerberos_realm="EXAMPLE.COM",
        kerberos_ticket_cache=str(cache_path),
    )

    client = module.WebHDFSClient.from_cluster(cluster, timeout=15)

    assert client.session.auth is fake_auth
    assert any(cmd[0] == "kinit" for cmd, _ in run_calls)
    assert os.environ.get("KRB5CCNAME") == str(cache_path)
    assert client.kerberos_principal.endswith("@EXAMPLE.COM")

    client.close()


@pytest.mark.unit
def test_webhdfs_client_requires_requests_kerberos(monkeypatch):
    monkeypatch.setattr(module, "REQUESTS_KERBEROS_AVAILABLE", False)

    cluster = SimpleNamespace(
        hdfs_namenode_url="http://namenode:9870",
        hdfs_user="hdfs",
        auth_type="KERBEROS",
        kerberos_principal="hive/service@EXAMPLE.COM",
        kerberos_keytab_path=None,
        kerberos_realm=None,
        kerberos_ticket_cache=None,
    )

    with pytest.raises(KerberosDiagnosticError) as exc:
        module.WebHDFSClient.from_cluster(cluster)

    assert exc.value.diagnostic.code is KerberosDiagnosticCode.CONFIG_MISSING


@pytest.mark.unit
def test_webhdfs_client_test_connection_success(monkeypatch):
    client = module.WebHDFSClient("http://namenode:9870", user="hdfs")

    class _Resp:
        status_code = 200
        text = ""

    monkeypatch.setattr(
        client.session,
        "get",
        lambda url, timeout, allow_redirects=False: _Resp(),
    )

    ok, message = client.test_connection()

    assert ok is True
    assert "succeeded" in message
    assert client.last_diagnostic() is None


@pytest.mark.unit
def test_webhdfs_client_test_connection_auth_failure(monkeypatch):
    client = module.WebHDFSClient("http://namenode:9870", user="hdfs")

    class _Resp:
        status_code = 401
        text = "Unauthorized"

    monkeypatch.setattr(
        client.session,
        "get",
        lambda url, timeout, allow_redirects=False: _Resp(),
    )

    ok, message = client.test_connection()

    diag = client.last_diagnostic()
    assert ok is False
    assert diag is not None
    assert diag.code == KerberosDiagnosticCode.AUTHENTICATION_FAILED
    assert message == diag.message
