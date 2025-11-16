"""
Client Fingerprint Security Module.

RU: Модуль безопасности для клиентских отпечатков.
EN: Client fingerprint security module.

This module provides:
- Secure storage and retrieval of fingerprint salt
- Salt rotation functionality
- Documentation for salt rotation procedures
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional

try:
    from secure_config import decrypt_value
except ImportError:  # pragma: no cover - optional dependency
    decrypt_value = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Environment variable name for the fingerprint salt
FINGERPRINT_SALT_ENV_VAR = "CLIENT_FINGERPRINT_SALT"
# Fallback: if salt is not set, generate a warning but don't fail
# In production, this MUST be set as a secret


def _is_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_test_context() -> bool:
    """Detect whether we are running under pytest or explicit test flags."""

    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if _is_truthy(os.getenv("TESTING")) or _is_truthy(os.getenv("UNIT_TESTING")):
        return True
    return False


def get_fingerprint_salt() -> str:
    """Get the client fingerprint salt from secure storage.

    RU: Получает соль для клиентских отпечатков из безопасного хранилища.
    EN: Gets the client fingerprint salt from secure storage.

    Returns:
        The salt value as a string

    Raises:
        RuntimeError: If salt is not configured and we're in production
    """
    # Try to get from environment (may be encrypted)
    salt_value = os.getenv(FINGERPRINT_SALT_ENV_VAR)

    if not salt_value:
        # Check if we're in production - if so, this is an error outside of tests
        is_production = (
            os.getenv("APP_ENV") == "production" or os.getenv("ENVIRONMENT") == "production"
        )
        if is_production and not _is_test_context():
            raise RuntimeError(
                f"{FINGERPRINT_SALT_ENV_VAR} must be set in production. "
                "This is a security-critical secret and must be stored securely."
            )

        # In development, generate a warning
        logger.warning(
            "%s is not set. Using empty salt (INSECURE - for development only). "
            "Set this environment variable in production.",
            FINGERPRINT_SALT_ENV_VAR,
        )
        return ""

    # Decrypt if encrypted
    if salt_value.startswith("encrypted:"):
        if decrypt_value is None:
            logger.warning(
                "Fingerprint salt appears encrypted but secure_config is unavailable; "
                "using encrypted value directly."
            )
            return salt_value
        decrypted = decrypt_value(salt_value)
        if decrypted == salt_value:
            logger.warning("Failed to decrypt fingerprint salt, using as-is (may be plain text)")
        return decrypted

    return salt_value


def generate_new_salt() -> str:
    """Generate a new cryptographically secure salt.

    RU: Генерирует новую криптографически безопасную соль.
    EN: Generates a new cryptographically secure salt.

    Returns:
        A new random salt value (32 bytes, hex-encoded = 64 characters)
    """
    import secrets

    # Generate 32 bytes of random data (256 bits)
    salt_bytes = secrets.token_bytes(32)
    return salt_bytes.hex()


def rotate_salt(new_salt: Optional[str] = None) -> tuple[str, str]:
    """Rotate the fingerprint salt.

    RU: Ротирует соль для клиентских отпечатков.
    EN: Rotates the fingerprint salt.

    Args:
        new_salt: Optional new salt value. If not provided, generates a new one.

    Returns:
        Tuple of (old_salt, new_salt)

    Note:
        After rotation, old fingerprints will no longer match new ones.
        This is expected behavior for security. Historical logs may need
        to be re-identified if correlation is needed.

    WARNING:
        Salt rotation breaks correlation of fingerprints across rotation events.
        Plan rotation carefully and document the rotation date.
    """
    old_salt = get_fingerprint_salt()
    new_salt_value = new_salt or generate_new_salt()

    logger.info(
        "Fingerprint salt rotation initiated. "
        "Old fingerprints will no longer match new ones after this rotation."
    )

    # In production, the new salt should be stored in a secrets manager
    # This function just generates/returns it - actual storage is environment-specific
    return (old_salt, new_salt_value)


def compute_fingerprint(source_ip: str, salt: Optional[str] = None) -> str:
    """Compute a client fingerprint from an IP address.

    RU: Вычисляет клиентский отпечаток из IP-адреса.
    EN: Computes a client fingerprint from an IP address.

    Args:
        source_ip: Source IP address
        salt: Optional salt value (uses get_fingerprint_salt() if not provided)

    Returns:
        12-character hexadecimal fingerprint
    """
    if salt is None:
        salt = get_fingerprint_salt()

    payload = f"{salt}:{source_ip}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return digest[:12]
