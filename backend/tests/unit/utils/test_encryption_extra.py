import os
import pytest

from app.utils.encryption import PasswordEncryptor, encrypt_cluster_password, decrypt_cluster_password
from app.config.settings import settings


@pytest.mark.unit
def test_encrypt_without_env_key_uses_ephemeral_key(monkeypatch):
    # 清空已有实例，确保走初始化路径
    PasswordEncryptor._fernet_instance = None  # type: ignore
    # 确保在开发/测试环境
    monkeypatch.setattr(settings, "SENTRY_ENVIRONMENT", "development")
    monkeypatch.delenv("HIVE_PASSWORD_ENCRYPTION_KEY", raising=False)

    secret = "abc123!"
    enc = PasswordEncryptor.encrypt_password(secret)
    assert enc and isinstance(enc, str)
    dec = PasswordEncryptor.decrypt_password(enc)
    assert dec == secret


@pytest.mark.unit
def test_decrypt_invalid_token_returns_none(monkeypatch):
    PasswordEncryptor._fernet_instance = None  # type: ignore
    monkeypatch.setattr(settings, "SENTRY_ENVIRONMENT", "development")
    monkeypatch.delenv("HIVE_PASSWORD_ENCRYPTION_KEY", raising=False)

    # 无法解密的 token
    assert PasswordEncryptor.decrypt_password("not-a-valid-token") is None


@pytest.mark.unit
def test_invalid_key_format_fallback(monkeypatch):
    PasswordEncryptor._fernet_instance = None  # type: ignore
    monkeypatch.setattr(settings, "SENTRY_ENVIRONMENT", "development")
    # 设置一个非法 key，触发回退
    monkeypatch.setenv("HIVE_PASSWORD_ENCRYPTION_KEY", "invalid-base64-key!!")

    secret = "hello-world"
    enc = PasswordEncryptor.encrypt_password(secret)
    dec = PasswordEncryptor.decrypt_password(enc)
    assert dec == secret


@pytest.mark.unit
def test_encrypt_decrypt_cluster_password(monkeypatch):
    PasswordEncryptor._fernet_instance = None  # type: ignore
    monkeypatch.setattr(settings, "SENTRY_ENVIRONMENT", "development")
    monkeypatch.delenv("HIVE_PASSWORD_ENCRYPTION_KEY", raising=False)

    class _C:
        hive_password = None

    c = _C()
    ok = encrypt_cluster_password(c, "pwd!")
    assert ok is True and isinstance(c.hive_password, str)
    dec = decrypt_cluster_password(c)
    assert dec == "pwd!"

