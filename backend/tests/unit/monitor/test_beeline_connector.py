import os
from unittest.mock import patch

import pytest

from app.monitor.beeline_connector import BeelineConnector


@pytest.mark.unit
def test_build_beeline_command_simple():
    connector = BeelineConnector(host='localhost', username='user', password='pw')
    cmd = connector._build_beeline_command(connector.get_jdbc_url())
    assert '-n' in cmd
    assert '-p' in cmd


@pytest.mark.unit
def test_build_beeline_command_kerberos(monkeypatch):
    connector = BeelineConnector(
        host='localhost',
        auth_type='KERBEROS',
        kerberos_principal='hive/host',
        kerberos_realm='EXAMPLE.COM',
        kerberos_keytab_path='/tmp/keytab',
        kerberos_ticket_cache='/tmp/cache',
    )
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    original_cache = os.environ.get('KRB5CCNAME')
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = type('Proc', (), {'stdout': '', 'stderr': '', 'returncode': 0})()
        connector._ensure_kerberos_ticket()
    cmd = connector._build_beeline_command(connector.get_jdbc_url())
    assert '-p' not in cmd
    assert '-n' in cmd
    assert any('EXAMPLE.COM' in arg for arg in cmd)
    # cleanup env to avoid cross-test contamination
    os.environ.pop('KRB5CCNAME', None)
    if original_cache is not None:
        os.environ['KRB5CCNAME'] = original_cache


@pytest.mark.unit
def test_get_jdbc_url_kerberos():
    connector = BeelineConnector(
        host='localhost',
        auth_type='KERBEROS',
        kerberos_principal='hive/host',
        kerberos_realm='EXAMPLE.COM'
    )
    url = connector.get_jdbc_url()
    assert ';principal=' in url
