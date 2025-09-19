import pytest

from app.utils.encryption import PasswordEncryptor


@pytest.mark.unit
def test_encrypt_password_none_returns_none():
    assert PasswordEncryptor.encrypt_password("") is None


@pytest.mark.unit
def test_decrypt_password_none_returns_none():
    assert PasswordEncryptor.decrypt_password("") is None

