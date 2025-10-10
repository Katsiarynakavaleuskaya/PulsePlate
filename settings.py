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

# RU: Минимальный безопасный порог калорий для целей снижения веса.
# EN: Minimum safe calorie floor for weight loss goals.
# Validated bounds: 800-2000 kcal (medical supervision below 1000 kcal recommended).
MIN_CALORIES_DEFAULT: int = int(os.getenv("MIN_CALORIES_DEFAULT", "1200"))
