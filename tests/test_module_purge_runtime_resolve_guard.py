from __future__ import annotations

from module_purge import purge_modules

from tests.helpers.module_resolve import resolve_legacy_app


def test_runtime_resolve_after_purge_returns_new_module_object() -> None:
    """RU: Guard против stale module refs после purge/reload под xdist.
    EN: Guard against stale module refs after purge/reload under xdist.

    Если кто-то снова начнёт держать ссылку на legacy_app, а потом вызывать purge,
    последующие monkeypatch/setattr могут патчить stale объект. Этот тест гарантирует,
    что runtime-resolve действительно возвращает новый объект модуля после purge.
    """
    legacy_before = resolve_legacy_app()

    purge_modules(prefixes=("legacy_app",))

    legacy_after = resolve_legacy_app()

    assert legacy_after.__name__ == "legacy_app"
    assert legacy_after is not legacy_before, (
        "Expected legacy_app module object identity to change after purge_modules(); "
        "otherwise stale module references may persist and monkeypatch.setattr() can patch "
        "a module that is no longer used by the running FastAPI app."
    )
