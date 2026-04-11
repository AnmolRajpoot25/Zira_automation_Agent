import base64
import os
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    from app.core.config import get_settings
    key = get_settings().encryption_key
    try:
        return Fernet(key.encode())
    except Exception:
        raw = bytes.fromhex(key)[:32]
        b64 = base64.urlsafe_b64encode(raw.ljust(32, b"\x00"))
        return Fernet(b64)


def encrypt_token(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


if __name__ == "__main__":
    key = Fernet.generate_key().decode()
    print(f"ENCRYPTION_KEY={key}")