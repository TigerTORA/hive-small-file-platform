import pytest

from app.utils.encryption import PasswordEncryptor
from app.config.settings import settings


@pytest.mark.unit
def test_is_encrypted_true_for_ciphertext(monkeypatch):
    PasswordEncryptor._fernet_instance = None  # type: ignore
    monkeypatch.setattr(settings, "SENTRY_ENVIRONMENT", "development")
    monkeypatch.delenv("HIVE_PASSWORD_ENCRYPTION_KEY", raising=False)

    secret = "s3cr3t!"
    token = PasswordEncryptor.encrypt_password(secret)
    assert token and PasswordEncryptor.is_encrypted(token)


@pytest.mark.unit
def test_is_encrypted_false_for_plaintext(monkeypatch):
    PasswordEncryptor._fernet_instance = None  # type: ignore
    monkeypatch.setattr(settings, "SENTRY_ENVIRONMENT", "development")
    monkeypatch.delenv("HIVE_PASSWORD_ENCRYPTION_KEY", raising=False)

    assert PasswordEncryptor.is_encrypted("plain-text") is False


@pytest.mark.unit
def test_is_encrypted_false_for_invalid_token(monkeypatch):
    PasswordEncryptor._fernet_instance = None  # type: ignore
    monkeypatch.setattr(settings, "SENTRY_ENVIRONMENT", "development")
    monkeypatch.delenv("HIVE_PASSWORD_ENCRYPTION_KEY", raising=False)

    assert PasswordEncryptor.is_encrypted("not-a-valid-token") is False

