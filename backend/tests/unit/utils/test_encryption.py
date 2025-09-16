import os
from app.utils.encryption import PasswordEncryptor


def test_encrypt_decrypt_roundtrip(monkeypatch):
    # 固定密钥，确保可重复
    key = PasswordEncryptor.generate_key()
    monkeypatch.setenv("HIVE_PASSWORD_ENCRYPTION_KEY", key)

    secret = "s3cr3t!"
    enc = PasswordEncryptor.encrypt_password(secret)
    assert enc is not None and isinstance(enc, str)

    dec = PasswordEncryptor.decrypt_password(enc)
    assert dec == secret

