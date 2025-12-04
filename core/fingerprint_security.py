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
environment variable or a successfully written cache file.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Final

SALT_ENV_VAR: Final[str] = "FINGERPRINT_SALT"
SALT_FILE_ENV_VAR: Final[str] = "FINGERPRINT_SALT_FILE"
DEFAULT_SALT_PATH: Final[Path] = Path("cache") / "fingerprint_salt.txt"


def _load_salt_from_file(path: Path) -> str | None:
    """Return the salt stored on disk, creating it if necessary.

    Note: Potential TOCTOU race between path.exists() and path.write_text(),
    but acceptable for this use case as concurrent writes will result in the
    same stable salt being used process-wide via lru_cache.
    """
    try:
        if path.exists():
            saved = path.read_text().strip()
            if saved:
                return saved

        path.parent.mkdir(parents=True, exist_ok=True)
        generated = secrets.token_hex(16)
        try:
            with path.open("x") as f:
                f.write(generated)
        except FileExistsError:
            # Another process created it, read the existing value
            try:
                saved = path.read_text().strip()
                if saved:
                    return saved
                # If the file exists but is still empty, persist our generated salt now
                path.write_text(generated)
            except Exception:
                # If we can't read or write the file, return our generated salt
                # but don't persist it
                logging.debug("Could not read/write fingerprint salt file", exc_info=True)

        try:
            path.chmod(0o600)
        except OSError:
            pass
        return generated
    except Exception:
        # Fallback handled by caller
        return None


@lru_cache(maxsize=1)
def _get_salt() -> str:
    """Return a secret salt used for pseudonymous hashing."""
    env_salt = os.getenv(SALT_ENV_VAR)
    if env_salt:
        return env_salt.strip()

    file_path = Path(os.getenv(SALT_FILE_ENV_VAR, DEFAULT_SALT_PATH))
    file_salt = _load_salt_from_file(file_path)
    if file_salt:
        return file_salt

    # Last-resort fallback; keeps process-stable but not persisted
    return secrets.token_hex(16)


def compute_fingerprint(source: str, *, truncate: int = 12) -> str:
    """Return a pseudonymous fingerprint for the given identifier."""
    if not source:
        return ""

    salt = _get_salt().encode("utf-8")
    # Blake2s key is limited to 32 bytes; hash longer salts
    if len(salt) > 32:
        salt = hashlib.blake2s(salt, digest_size=32).digest()
    data = source.encode("utf-8")

    digest = hashlib.blake2s(data, key=salt).hexdigest()
    length = truncate if truncate > 0 else len(digest)
    return digest[:length]


__all__ = ["compute_fingerprint"]
