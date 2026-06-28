"""
core/encryption.py
==================
Master Password security module.

- First launch: admin sets a Master Password.
- Derives a 32-byte Fernet key via PBKDF2HMAC (SHA-256, 390,000 iterations,
  random 16-byte salt).
- Stores ONLY the salt + a verification ciphertext in the DB (app_config table).
- Subsequent launches: re-derive key → decrypt verification token → confirm.
- Exposes encrypt() / decrypt() used throughout the app for storing secrets.
"""

import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# -----------------------------------------------------------------
# Module-level state (populated once on successful password verify)
# -----------------------------------------------------------------
_fernet: Fernet | None = None

_VERIFICATION_PLAINTEXT = "STAGGERED_GTT_OMS_VERIFICATION_TOKEN_2024"
_PBKDF2_ITERATIONS = 390_000
_SALT_LENGTH = 16


# -----------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte URL-safe base64-encoded Fernet key from password+salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    key_bytes = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(key_bytes)


def _make_fernet(password: str, salt: bytes) -> Fernet:
    """Create a Fernet cipher from password + salt."""
    key = _derive_key(password, salt)
    return Fernet(key)


# -----------------------------------------------------------------
# Public API — called from ui/login_screen.py
# -----------------------------------------------------------------

def is_initialized() -> bool:
    """Return True if a Master Password salt+token have been saved to the DB."""
    from core.database import get_config
    return get_config("master_salt") is not None


def setup_master_password(password: str) -> None:
    """
    First-launch: generate salt, derive key, store salt + verification token.
    Raises ValueError if called when a password is already configured.
    """
    global _fernet
    from core.database import set_config

    if is_initialized():
        raise ValueError("Master password already configured.")

    salt = os.urandom(_SALT_LENGTH)
    fernet = _make_fernet(password, salt)

    # Encrypt a known constant so we can verify the password later
    token = fernet.encrypt(_VERIFICATION_PLAINTEXT.encode("utf-8"))

    set_config("master_salt", base64.b64encode(salt).decode("utf-8"))
    set_config("master_token", token.decode("utf-8"))

    _fernet = fernet


def verify_and_unlock(password: str) -> bool:
    """
    Subsequent launches: re-derive key, try to decrypt the stored token.
    Returns True and populates _fernet on success; returns False otherwise.
    """
    global _fernet
    from core.database import get_config

    salt_b64 = get_config("master_salt")
    stored_token = get_config("master_token")

    if salt_b64 is None or stored_token is None:
        return False

    salt = base64.b64decode(salt_b64)
    try:
        fernet = _make_fernet(password, salt)
        plaintext = fernet.decrypt(stored_token.encode("utf-8")).decode("utf-8")
        if plaintext == _VERIFICATION_PLAINTEXT:
            _fernet = fernet
            return True
    except (InvalidToken, Exception):
        pass

    return False


# -----------------------------------------------------------------
# Encrypt / Decrypt — used by database.py when storing API keys
# -----------------------------------------------------------------

def encrypt(plaintext: str) -> str:
    """Encrypt a UTF-8 string. Returns a UTF-8 Fernet token string."""
    if _fernet is None:
        raise RuntimeError("Encryption module not unlocked. Call verify_and_unlock() first.")
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token string. Returns the original UTF-8 plaintext."""
    if _fernet is None:
        raise RuntimeError("Encryption module not unlocked. Call verify_and_unlock() first.")
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError(f"Decryption failed — data may be corrupt or tampered: {e}") from e
