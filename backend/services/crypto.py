"""
services/crypto.py — Fernet symmetric encryption for refresh token storage.
Key is loaded from ENCRYPTION_KEY env var (base64-encoded 32 bytes).
"""
import base64
import os
from cryptography.fernet import Fernet

from config import settings


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        # In dev without a key, auto-generate one (NOT for production)
        key = Fernet.generate_key().decode()
    # Accept both plain and base64-padded keys
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # If the key isn't valid Fernet format, derive one
        padded = base64.urlsafe_b64encode(key.encode()[:32].ljust(32, b"0"))
        return Fernet(padded)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token string; returns base64 ciphertext string."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a previously encrypted token."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
