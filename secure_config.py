"""
Secure configuration management with encryption support.

This module provides utilities for securely storing and retrieving
sensitive configuration values like API keys.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken

    ENCRYPTION_AVAILABLE = True
except ImportError:  # pragma: no cover
    ENCRYPTION_AVAILABLE = False  # pragma: no cover

    # Placeholder when cryptography is unavailable
    InvalidToken = Exception  # pragma: no cover


def get_encryption_key() -> Optional[bytes]:
    """Get the encryption key if it exists."""
    key_file = Path.home() / ".cursor" / ".key"

    if not key_file.exists():
        return None

    try:
        with open(key_file, "rb") as f:
            key = f.read()
            if not key:
                logger.error("Encryption key file at %s is empty", key_file)
                return None
            return key
    except OSError as e:
        logger.exception("Failed to read encryption key from %s: %s", key_file, e)
        return None


def get_or_create_encryption_key() -> bytes:
    """
    Get or create encryption key for secure storage.

    Returns:
        The encryption key as bytes

    Raises:
        OSError: If key file operations fail

    Note:
        On Unix/Linux/macOS, file permissions are set to 0o600 (owner read/write only).
        On Windows, os.chmod() only affects the read-only flag and does NOT provide
        full POSIX permission semantics. For strict file ACL enforcement on Windows,
        use platform-specific tools (e.g., pywin32, icacls).
    """
    if not ENCRYPTION_AVAILABLE:
        raise ImportError("cryptography package is required for encryption")

    key_file = Path.home() / ".cursor" / ".key"

    # Attempt to read existing key file
    if key_file.exists():
        try:
            with open(key_file, "rb") as f:
                return f.read()
        except (OSError, IOError) as e:
            raise OSError(
                f"Failed to read encryption key file at {key_file}: {type(e).__name__}: {e}"
            ) from e

    # Generate new key
    key: bytes = Fernet.generate_key()

    # Ensure directory exists with error handling
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, IOError) as e:
        raise OSError(
            f"Failed to create directory for encryption key at {key_file.parent}: "
            f"{type(e).__name__}: {e}"
        ) from e

    # Write key atomically using temporary file to prevent partial writes
    temp_file = key_file.with_suffix(".key.tmp")
    try:
        # Write to temporary file first
        with open(temp_file, "wb") as f:
            f.write(key)

        # Atomically replace target file
        os.replace(temp_file, key_file)
    except (OSError, IOError) as e:
        # Clean up temporary file if it exists
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:  # nosec B110
                pass  # Best effort cleanup
        raise OSError(
            f"Failed to write encryption key to {key_file}: {type(e).__name__}: {e}"
        ) from e

    # Set file permissions to 600 (owner read/write only)
    # NOTE: On Windows, os.chmod() only affects the read-only flag; it does NOT
    # provide full POSIX permission semantics. For strict ACL enforcement on Windows,
    # use platform-specific tools (e.g., pywin32, icacls).
    try:
        os.chmod(key_file, 0o600)
        if os.name == "nt":
            # On Windows, chmod has limited effect - warn user
            logger.warning(
                "On Windows, file permissions are limited. "
                "Key file at %s may be accessible to other users. "
                "For strict access control, consider using Windows ACLs (e.g., icacls or pywin32).",
                key_file,
            )
    except (OSError, IOError) as e:
        # Log/report but don't fail - key is already written
        logger.warning(
            "Failed to set secure permissions on %s: %s: %s. "
            "Key file may be accessible to other users. Please manually set permissions to 600.",
            key_file,
            type(e).__name__,
            e,
        )

    return key


def encrypt_value(value: str) -> str:
    """
    Encrypt a sensitive value.

    Args:
        value: The plain text value to encrypt

    Returns:
        Encrypted value prefixed with "encrypted:"

    Raises:
        RuntimeError: If cryptography is not available
        Exception: If encryption fails for any reason

    Note:
        This function NEVER returns plain text. It either returns encrypted data
        or raises an exception. This ensures that sensitive data is never accidentally
        stored in plain text.
    """
    if not ENCRYPTION_AVAILABLE:
        raise RuntimeError(
            "cryptography library not installed - encryption is required for secure storage. "
            "Install with: pip install cryptography"
        )

    try:
        key = get_or_create_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(value.encode())
        return f"encrypted:{encrypted.decode()}"
    except Exception as e:
        logger.error("Encryption failed: %s", e)
        raise RuntimeError(f"Failed to encrypt value: {e}") from e


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
        decrypted: bytes = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except (InvalidToken, ValueError, TypeError, UnicodeDecodeError) as e:
        # Expected decryption failures - return original value
        logger.debug(
            "Decryption failed for value (expected error): %s: %s",
            type(e).__name__,
            str(e),
        )
        return value


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
