"""Application configuration values."""

from __future__ import annotations

import os

EXPORT_TOKEN_SECRET: str = os.getenv("EXPORT_TOKEN_SECRET", "dev-insecure-secret-change-me")
EXPORT_TOKEN_TTL_SECONDS: int = int(os.getenv("EXPORT_TOKEN_TTL_SECONDS", "900"))

PRIVATE_EXPORTS_ENABLED: bool = os.getenv("PRIVATE_EXPORTS_ENABLED", "1") not in {
    "0",
    "false",
    "False",
}
