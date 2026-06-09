from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    from app.core.config import get_settings
    key = get_settings().encryption_key
    return Fernet(key.encode())


def encrypt_value(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    return _get_fernet().decrypt(ciphertext.encode()).decode()


encrypt_token = encrypt_value
decrypt_token = decrypt_value


if __name__ == "__main__":
    key = Fernet.generate_key().decode()
    print(f"ENCRYPTION_KEY={key}")
