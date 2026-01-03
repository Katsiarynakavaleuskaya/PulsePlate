# -*- coding: utf-8 -*-
"""
RU: Тестовый helper для детерминированного патчинга реально зарегистрированных FastAPI endpoints.
EN: Test helper to deterministically patch the actually registered FastAPI endpoints.

Why:
- String-based patch("module.symbol") may not hit the callable used by the registered route
  (aliasing, import/reload patterns, dual-module state, etc.).
- We patch the real endpoint function object that FastAPI registered in app.routes.

Policy:
- No sys.modules mutations.
- Prefer monkeypatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, cast

import pytest


@dataclass(frozen=True)
class RouteMatch:
    """
    RU: Результат поиска маршрута.
    EN: Route match result.
    """

    path: str
    methods: tuple[str, ...]
    endpoint: Callable[..., Any]


def _norm_method(method: str) -> str:
    return method.strip().upper()


def find_route_endpoint(*, app: Any, path: str, method: str) -> Callable[..., Any]:
    """
    RU: Находит endpoint (callable), реально зарегистрированный в FastAPI app.routes,
        по точному path и HTTP method.
    EN: Finds the actual registered endpoint callable in FastAPI app.routes by exact path+method.

    Raises:
        AssertionError: if route is not found or ambiguous.
    """
    wanted_method = _norm_method(method)

    matches: list[RouteMatch] = []
    for r in getattr(app, "routes", []) or []:
        r_path = getattr(r, "path", None)
        r_methods = getattr(r, "methods", None)
        r_endpoint = getattr(r, "endpoint", None)

        if r_path != path:
            continue
        if not r_methods:
            continue

        methods = tuple(sorted({_norm_method(m) for m in cast(Iterable[str], r_methods)}))
        if wanted_method not in methods:
            continue
        if not callable(r_endpoint):
            continue

        matches.append(
            RouteMatch(path=r_path, methods=methods, endpoint=cast(Callable[..., Any], r_endpoint))
        )

    if not matches:
        raise AssertionError(
            f"Route not found: path={path!r}, method={wanted_method!r}. "
            "Check that the router is included and the path/method are correct."
        )

    if len(matches) > 1:
        details = "\n".join([f"- path={m.path!r} methods={m.methods}" for m in matches])
        raise AssertionError(
            "Ambiguous route match (multiple endpoints for same path+method).\n"
            f"path={path!r}, method={wanted_method!r}\n"
            f"Matches:\n{details}\n"
            "Fix: make path more specific or patch all matched endpoints."
        )

    return matches[0].endpoint


def patch_endpoint_global(
    *,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: Callable[..., Any],
    name: str,
    value: Any,
) -> None:
    """
    RU: Патчит глобальную ссылку в endpoint.__globals__[name] = value.
        Это надёжно, когда endpoint вызывает функцию из своего модуля.
    EN: Patches a global symbol used by endpoint via endpoint.__globals__[name] = value.

    Raises:
        AssertionError: if endpoint has no __globals__ or name is absent.
    """
    globals_dict = getattr(endpoint, "__globals__", None)
    if not isinstance(globals_dict, dict):
        raise AssertionError(
            "Endpoint has no __globals__ dict. "
            "It may be a callable object or wrapped function. Use patch_endpoint_attr()."
        )

    if name not in globals_dict:
        raise AssertionError(
            f"Global name {name!r} not found in endpoint.__globals__. "
            "Fix: patch the correct symbol name or use patch_endpoint_attr()."
        )

    # RU: Используем monkeypatch, чтобы pytest корректно откатывал изменения.
    # EN: Use monkeypatch to ensure pytest reverts changes.
    monkeypatch.setitem(globals_dict, name, value)


def patch_endpoint_attr(
    *,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: Callable[..., Any],
    name: str,
    value: Any,
) -> None:
    """
    RU: Фоллбек: патчим атрибут на callable (например, если endpoint — bound method / object).
    EN: Fallback: patch attribute on callable (e.g., endpoint is bound method/object).
    """
    if not hasattr(endpoint, name):
        raise AssertionError(
            f"Endpoint has no attribute {name!r}. "
            "Fix: patch correct attribute or use patch_endpoint_global()."
        )
    monkeypatch.setattr(endpoint, name, value, raising=True)


def patch_route_dependency(
    *,
    app: Any,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    method: str,
    symbol: str,
    value: Any,
    mode: str = "globals",
) -> Callable[..., Any]:
    """
    RU: Высокоуровневый хелпер: находит endpoint по path+method и патчит symbol.
    EN: High-level helper: find endpoint by path+method and patch a symbol.

    mode:
      - "globals": patch endpoint.__globals__[symbol]
      - "attr": patch attribute on endpoint
    """
    endpoint = find_route_endpoint(app=app, path=path, method=method)
    if mode == "globals":
        patch_endpoint_global(monkeypatch=monkeypatch, endpoint=endpoint, name=symbol, value=value)
    elif mode == "attr":
        patch_endpoint_attr(monkeypatch=monkeypatch, endpoint=endpoint, name=symbol, value=value)
    else:
        raise AssertionError(f"Unknown mode: {mode!r}. Use 'globals' or 'attr'.")
    return endpoint
