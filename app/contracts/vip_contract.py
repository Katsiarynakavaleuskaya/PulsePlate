# -*- coding: utf-8 -*-
"""
RU: Минимальный контракт ответов VIP (без FastAPI).
EN: Minimal VIP response contract (no FastAPI).

Invariants:
- Stable top-level "status"
- Backward-compatible aliases: "error" == code, "detail" == message
"""

from __future__ import annotations

from typing import Any


def vip_success(**data: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    RU: Успешный ответ (envelope).
    EN: Success envelope.
    """
    return {"status": "success", **data}


def vip_error(code: str, message: str, **extra: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    RU: Ошибка (envelope) + legacy aliases.
    EN: Error envelope + legacy aliases.

    Backward compatibility:
    - error == code
    - detail == message
    """
    return {
        "status": "error",
        "code": code,
        "message": message,
        "detail": message,  # Legacy alias: detail == message
        "error": code,  # Legacy alias: error == code
        **extra,
    }


__all__ = ["vip_success", "vip_error"]
