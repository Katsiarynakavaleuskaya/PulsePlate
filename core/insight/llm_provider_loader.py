"""LLM provider loader (insight).

RU: Лоадер для ленивого импорта `llm.get_provider`.
EN: Loader for lazily importing `llm.get_provider`.

Hard invariants:
- No import-time side effects (OpenAPI determinism): do NOT import `llm` at module scope.
- Keep the behavior identical to legacy path; HTTP mapping happens in callers.
"""

from __future__ import annotations

from typing import Any, Callable


def load_llm_get_provider() -> Callable[[], Any]:
    """Load `llm.get_provider` lazily.

    RU: Вынесено из `legacy_app.py` чтобы legacy оставался thin shim и чтобы тесты могли
    детерминированно покрывать ветку import-failure без sys.modules мутаций и без патча
    builtins.__import__.
    EN: Extracted from `legacy_app.py` to keep legacy thin and to allow deterministic testing
    of the import-failure branch without sys.modules mutation and without patching builtins.__import__.
    """
    from llm import get_provider

    return get_provider
