"""Utilities for creating and verifying time-limited signed URLs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Optional


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sign(secret: str, path: str, exp_ts: int) -> str:
    payload = f"{path}|{exp_ts}".encode("utf-8")
    mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return _b64url(mac)


def verify(
    secret: str, path: str, exp_ts: int, signature: str, *, now_ts: Optional[int] = None
) -> bool:
    now = int(now_ts if now_ts is not None else time.time())
    if now > exp_ts:
        return False
    expected = sign(secret, path, exp_ts)
    try:
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False
