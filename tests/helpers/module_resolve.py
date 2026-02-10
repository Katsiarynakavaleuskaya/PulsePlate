from __future__ import annotations

import importlib
from types import ModuleType


def resolve_module(name: str) -> ModuleType:
    """Resolve a module by name at runtime.

    RU: Всегда резолвим модуль в runtime, чтобы не поймать stale refs после purge/reload.
    EN: Always resolve module at runtime to avoid stale refs after purge/reload.
    """

    return importlib.import_module(name)


def resolve_legacy_app() -> ModuleType:
    return resolve_module("legacy_app")


def resolve_llm() -> ModuleType:
    return resolve_module("llm")
