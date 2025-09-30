"""
Shared test helpers for dynamic FastAPI app loading.

RU: Общие утилиты для загрузки приложения в тестах.
EN: Common utilities for loading the app in tests.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def resolve_repo_root(start: Path | None = None) -> Path:
    """Resolve repository root by traversing parents until marker files are found.

    Falls back to three parents up from tests/ directory if no markers present.
    """
    base = (start or Path(__file__).resolve()).parent
    return next(
        (
            parent
            for parent in [base, *base.parents]
            if (parent / "app.py").exists()
            and (parent / "pyproject.toml").exists()
        ),
        base.parents[1],
    )


def load_app() -> object:
    """Dynamically load FastAPI app from app.py using an absolute path.

    Raises ImportError with a descriptive message including the resolved path if loading fails.
    """
    repo_root = resolve_repo_root()
    app_path = repo_root / "app.py"
    if not app_path.exists():
        raise ImportError(f"app.py not found at resolved path: {app_path}")

    spec = importlib.util.spec_from_file_location("app_module", str(app_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create import spec for app.py at: {app_path}")

    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)

    try:
        return app_module.app
    except AttributeError as exc:
        raise ImportError(f"Loaded module lacks 'app' attribute at: {app_path}") from exc
