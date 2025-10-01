"""
Secure configuration management with encryption support.

This module provides utilities for securely storing and retrieving
sensitive configuration values like API keys.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet

    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


def get_encryption_key() -> Optional[bytes]:
    """Get the encryption key if it exists."""
    key_file = Path.home() / ".cursor" / ".key"

    if not key_file.exists():
        return None

    try:
        with open(key_file, "rb") as f:
            return f.read()
    except Exception:
        return None


def decrypt_value(value: str) -> str:
    """
    Decrypt a sensitive value if it's encrypted.

    Args:
        value: The value to decrypt (may be plain text or encrypted)

    Returns:
        Decrypted value, or original value if not encrypted or decryption fails
    """
    if not value or not value.startswith("encrypted:"):
        return value  # Already plain text

    if not ENCRYPTION_AVAILABLE:
        return value  # Cannot decrypt without cryptography

    try:
        encrypted_data = value.replace("encrypted:", "")
        key = get_encryption_key()

        if key is None:
            return value  # No key available

        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception:
        return value  # Decryption failed, return as-is


def get_api_key_from_env(env_var: str = "OPENAI_API_KEY") -> Optional[str]:
    """
    Get API key from environment, decrypting if necessary.

    Args:
        env_var: Environment variable name

    Returns:
        Decrypted API key or None if not found
    """
    value = os.getenv(env_var)

    if value is None:
        return None

    return decrypt_value(value)
