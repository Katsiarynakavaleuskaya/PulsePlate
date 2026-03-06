"""Utilities for generating pseudonymous client fingerprints.

The goal is to provide a stable identifier for a client (e.g. hashed IP) without
ever logging or storing the raw value. A secret salt is used to prevent reverse
lookups and is loaded from an environment variable when available. If the env var
is absent, the module attempts to use a cache file under ``cache/`` to persist the
salt across process restarts.

If both the environment variable and cache file are unavailable (e.g., file creation
fails or is disabled), a process-local salt is generated as a last-resort fallback.
Note that this process-local salt is NOT persisted across restarts, so fingerprints
will not be stable between processes unless a persistent salt is provided via
environment variable or a successfully written cache file. The fallback salt
provides 256-bit (32-byte) entropy for HMAC-SHA256 pseudonymous hashing.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

SALT_ENV_VAR: Final[str] = "FINGERPRINT_SALT"
SALT_FILE_ENV_VAR: Final[str] = "FINGERPRINT_SALT_FILE"
DEFAULT_SALT_PATH: Final[Path] = Path("cache") / "fingerprint_salt.txt"
SECRET_MARKER_ITERATIONS: Final[int] = 120_000


def _read_salt(path: Path) -> str | None:
    """Read and return salt from file, or None if file doesn't exist or is invalid."""
    try:
        saved = path.read_text().strip()
        return saved if saved else None
    except (ValueError, FileNotFoundError, OSError, PermissionError):
        return None


def _write_salt_exclusive(path: Path, value: str) -> bool:
    """Attempt exclusive write of salt value. Returns True if successful, False if file exists."""
    try:
        with path.open("x") as f:
            f.write(value)
        return True
    except FileExistsError:
        return False
    except (OSError, IOError, PermissionError):
        return False


def _ensure_dir_and_perms(path: Path) -> None:
    """Create parent directory and set file permissions to 0o600. Logs but doesn't raise on errors."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.debug(f"Could not create salt file directory: {e}")

    try:
        path.chmod(0o600)
    except OSError:
        pass  # Permission setting is best-effort


def _load_salt_from_file(path: Path) -> str | None:
    """Return the salt stored on disk, creating it if necessary.

    Note: Potential TOCTOU race between path.exists() and path.write_text(),
    but acceptable for this use case as concurrent writes will result in the
    same stable salt being used process-wide via lru_cache.
    """
    try:
        if path.exists():
            saved = _read_salt(path)
            if saved:
                return saved

        _ensure_dir_and_perms(path)
        generated = secrets.token_hex(32)

        if _write_salt_exclusive(path, generated):
            _ensure_dir_and_perms(path)
            return generated

        saved = _read_salt(path)
        if saved:
            return saved

        try:
            path.write_text(generated)
        except (OSError, IOError, PermissionError):
            logger.debug("Could not persist fingerprint salt", exc_info=True)

        _ensure_dir_and_perms(path)
        return generated
    except (OSError, IOError, PermissionError):
        return None


@lru_cache(maxsize=1)
def _get_salt() -> str:
    """Return a secret salt used for pseudonymous hashing.

    Provides 256-bit (32-byte) entropy for HMAC-SHA256 keyed hashing
    when using fallback generation.
    """
    env_salt = os.getenv(SALT_ENV_VAR)
    if env_salt:
        return env_salt.strip()

    file_path = Path(os.getenv(SALT_FILE_ENV_VAR, DEFAULT_SALT_PATH))
    file_salt = _load_salt_from_file(file_path)
    if file_salt:
        return file_salt

    # Last-resort fallback; keeps process-stable but not persisted.
    # Provides 256-bit (32-byte) entropy for HMAC-SHA256 keyed hashing.
    return secrets.token_hex(32)


def compute_fingerprint(source: str, *, truncate: int = 12) -> str:
    """Return a salted pseudonymous fingerprint for the given identifier."""
    if not source:
        return ""

    if truncate < 0:
        raise ValueError(f"truncate must be non-negative, got {truncate}")

    salt = _get_salt().encode("utf-8")
    data = source.encode("utf-8")
    digest = hmac.new(salt, data, hashlib.sha256).hexdigest()
    length = truncate if truncate > 0 else len(digest)
    return digest[:length]


def compute_secret_marker(secret: str, *, truncate: int = 32) -> str:
    """Return a PBKDF2-based opaque marker for limited-input secrets.

    RU: Возвращает opaque marker для секретов с ограниченным пространством значений.
    EN: Returns an opaque marker for limited-input secrets using PBKDF2-HMAC-SHA256.
    """
    if not secret:
        return ""

    if truncate < 0:
        raise ValueError(f"truncate must be non-negative, got {truncate}")

    salt = _get_salt().encode("utf-8")
    secret_bytes = secret.encode("utf-8")
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret_bytes,
        salt,
        SECRET_MARKER_ITERATIONS,
        dklen=32,
    ).hex()
    length = truncate if truncate > 0 else len(digest)
    return digest[:length]


@runtime_checkable
class _ClientLike(Protocol):
    """Protocol for request.client attribute."""

    @property
    def host(self) -> str | None: ...  # pragma: no cover


@runtime_checkable
class ClientFingerprintRequest(Protocol):
    """Protocol for request objects used by _client_fingerprint.

    Avoids FastAPI dependency in core module while providing type safety.
    """

    @property
    def client(self) -> _ClientLike | None: ...  # pragma: no cover

    @property
    def headers(self) -> Mapping[str, str]: ...  # pragma: no cover


def _client_fingerprint(request: ClientFingerprintRequest) -> str | None:
    """Return a stable, non-PII identifier for the requesting client.

    RU: Возвращает стабильный, не-ПДН идентификатор для запрашивающего клиента.
    EN: Returns a stable, non-PII identifier for the requesting client.

    This function produces pseudonymous identifiers (hashed+truncated IPs)
    that must be treated as pseudonymous data per GDPR and privacy regulations.

    Args:
        request: Request object with `client.host` and `headers.get()` attributes.
                Uses Protocol to avoid FastAPI dependency in core module.

    Returns:
        Pseudonymous fingerprint string or None if source IP cannot be determined.
    """
    import ipaddress

    trusted_proxies_str = os.getenv("TRUSTED_PROXIES", "")
    trusted_proxies = {proxy.strip() for proxy in trusted_proxies_str.split(",") if proxy.strip()}

    remote_host = request.client.host if request.client else ""

    source = remote_host
    if remote_host in trusted_proxies:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            forwarded_ips = [ip.strip() for ip in forwarded_for.split(",")]
            if forwarded_ips:
                try:
                    ipaddress.ip_address(forwarded_ips[0])
                    source = forwarded_ips[0]
                except ValueError:
                    pass

    if not source:
        return None
    # Hash with salt so raw IP is never logged while keeping ability to correlate requests.
    # Uses secure salt storage - see core.fingerprint_security for details.
    return compute_fingerprint(source)


__all__ = ["compute_fingerprint", "compute_secret_marker", "_client_fingerprint"]
