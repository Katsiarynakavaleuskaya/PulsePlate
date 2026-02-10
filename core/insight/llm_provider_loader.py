"""LLM provider loader (insight).

RU: Лоадер для ленивого импорта `llm.get_provider`.
EN: Loader for lazily importing `llm.get_provider`.

Hard invariants:
- No import-time side effects (OpenAPI determinism): do NOT import `llm` at module scope.
- Keep the behavior identical to legacy path; HTTP mapping happens in callers.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, cast


class LLMProvider(Protocol):
    """Minimal surface-area required by the insight pipeline.

    RU: В `core/` запрещён `Any`. Этот Protocol описывает только то, что уже реально
    используется (см. `legacy_app.py`: `provider.name`, `await provider.generate(...)`).
    EN: `Any` is forbidden in `core/`. This Protocol only describes what is already used
    (see `legacy_app.py`: `provider.name`, `await provider.generate(...)`).
    """

    name: str

    def generate(self, prompt: str) -> Awaitable[str]: ...


LLMProviderFactory = Callable[[], LLMProvider | None]


def load_llm_get_provider() -> LLMProviderFactory:
    """Load `llm.get_provider` lazily.

    RU: Вынесено из `legacy_app.py` чтобы legacy оставался thin shim и чтобы тесты могли
    детерминированно покрывать ветку import-failure без sys.modules мутаций и без патча
    builtins.__import__.
    EN: Extracted from `legacy_app.py` to keep legacy thin and to allow deterministic testing
    of the import-failure branch without sys.modules mutation and without patching builtins.__import__.
    """
    from llm import get_provider

    # Providers are defined outside `core/`; type surfaces may lag behind runtime behavior.
    # We cast to the minimal Protocol used by the insight pipeline (name + async generate).
    return cast(LLMProviderFactory, get_provider)
