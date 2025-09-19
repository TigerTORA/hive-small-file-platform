import pytest

from app.utils.encryption import (
    PasswordEncryptor,
    encrypt_cluster_password,
    decrypt_cluster_password,
)
from app.config.settings import settings


@pytest.mark.unit
def test_encrypt_cluster_password_empty_sets_none(monkeypatch):
    PasswordEncryptor._fernet_instance = None  # type: ignore
    monkeypatch.setattr(settings, "SENTRY_ENVIRONMENT", "development")
    monkeypatch.delenv("HIVE_PASSWORD_ENCRYPTION_KEY", raising=False)

    class _C:
        hive_password = "some"

    c = _C()
    ok = encrypt_cluster_password(c, "")
    assert ok is True
    assert c.hive_password is None


@pytest.mark.unit
def test_decrypt_cluster_password_none_returns_none():
    class _C:
        hive_password = None

    c = _C()
    assert decrypt_cluster_password(c) is None

