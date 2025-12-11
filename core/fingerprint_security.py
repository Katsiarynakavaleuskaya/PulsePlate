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
provides 256-bit (32-byte) entropy for enhanced Blake2s keyed-hash security.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

SALT_ENV_VAR: Final[str] = "FINGERPRINT_SALT"
SALT_FILE_ENV_VAR: Final[str] = "FINGERPRINT_SALT_FILE"
DEFAULT_SALT_PATH: Final[Path] = Path("cache") / "fingerprint_salt.txt"


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
        # Try reading existing salt first
        if path.exists():
            saved = _read_salt(path)
            if saved:
                return saved

        # Ensure parent directory exists
        _ensure_dir_and_perms(path)

        # Generate new salt
        generated = secrets.token_hex(32)  # Generate 256-bit (32-byte) salt

        # Try exclusive write (creates file only if it doesn't exist)
        if _write_salt_exclusive(path, generated):
            # Successfully created file, set permissions and return
            _ensure_dir_and_perms(path)
            return generated

        # File was created by another process - try reading it
        saved = _read_salt(path)
        if saved:
            return saved

        # File exists but is empty - attempt to persist generated salt for stability
        # Note: Race condition possible here; first writer wins, losers will
        # read their value on next restart. Acceptable for this use case.
        try:
            path.write_text(generated)
        except (OSError, IOError, PermissionError):
            # If we cannot write, still return the generated value
            # (process-stable via caller cache)
            logger.debug("Could not persist fingerprint salt", exc_info=True)

        _ensure_dir_and_perms(path)
        return generated
    except (OSError, IOError, PermissionError):
        # Fallback handled by caller - return None if we cannot access filesystem
        return None


@lru_cache(maxsize=1)
def _get_salt() -> str:
    """Return a secret salt used for pseudonymous hashing.

    Provides 256-bit (32-byte) entropy for Blake2s keyed-hash security
    when using fallback generation.
    """
    env_salt = os.getenv(SALT_ENV_VAR)
    if env_salt:
        return env_salt.strip()

    file_path = Path(os.getenv(SALT_FILE_ENV_VAR, DEFAULT_SALT_PATH))
    file_salt = _load_salt_from_file(file_path)
    if file_salt:
        return file_salt

    # Last-resort fallback; keeps process-stable but not persisted
    # Provides 256-bit (32-byte) entropy for Blake2s keyed-hash security
    return secrets.token_hex(32)  # Generate 256-bit (32-byte) salt


def compute_fingerprint(source: str, *, truncate: int = 12) -> str:
    """Return a pseudonymous fingerprint for the given identifier."""
    if not source:
        return ""

    if truncate < 0:
        raise ValueError(f"truncate must be non-negative, got {truncate}")

    salt = _get_salt().encode("utf-8")
    # Blake2s key is limited to 32 bytes; hash longer salts
    if len(salt) > 32:
        salt = hashlib.blake2s(salt, digest_size=32).digest()
    data = source.encode("utf-8")

    digest = hashlib.blake2s(data, key=salt).hexdigest()
    length = truncate if truncate > 0 else len(digest)
    return digest[:length]


__all__ = ["compute_fingerprint"]
