"""Core database package.

Re-exports from core/db.py file for backward compatibility.
This allows core.db.fallback to be imported as a submodule.

NOTE: When both core/db.py (file) and core/db/ (package) exist,
Python resolves 'core.db' to this package. We need to re-export
from the file module.

Implementation: We use a lazy-loading pattern to access the file module.
The file is loaded via function-scope import in fallback.py (per PLAN 4.3).
For __init__.py, we use a helper function to load and cache the file module.
"""

import sys
import importlib.util
from pathlib import Path
from typing import Any

# Cache for the loaded file module
_db_file_module: Any = None


def _load_db_file_module() -> Any:
    """Load core/db.py file module (function-scope import per PLAN 4.3).

    This is called on-demand to avoid module-level forbidden patterns.
    The file module is cached after first load.
    """
    global _db_file_module

    if _db_file_module is not None:
        return _db_file_module

    # Load the file using function-scope import (allowed per PLAN 4.3)
    _db_py_path = Path(__file__).parent.parent / "db.py"
    _spec = importlib.util.spec_from_file_location("core.db_file_module", _db_py_path)
    if _spec and _spec.loader:
        _db_file_module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_db_file_module)  # type: ignore[union-attr]
        return _db_file_module
    else:
        raise ImportError(f"Could not load core/db.py file from {_db_py_path}")


# Lazy-load and re-export symbols on first access
def __getattr__(name: str) -> Any:
    """Lazy-load symbols from core/db.py file module."""
    _db_file = _load_db_file_module()
    return getattr(_db_file, name)


# Pre-load common symbols for immediate access
_db_file = _load_db_file_module()
AsyncDBNotAvailable = _db_file.AsyncDBNotAvailable
AsyncDBNotConfigured = _db_file.AsyncDBNotConfigured
EngineCompat = _db_file.EngineCompat
SessionLocal = _db_file.SessionLocal
_RAW_ENGINE = _db_file._RAW_ENGINE
engine = _db_file.engine
get_session = _db_file.get_session
init_db = _db_file.init_db
sessionmaker = _db_file.sessionmaker
session_scope = _db_file.session_scope
Base = _db_file.Base

__all__ = [
    "AsyncDBNotAvailable",
    "AsyncDBNotConfigured",
    "Base",
    "EngineCompat",
    "SessionLocal",
    "_RAW_ENGINE",
    "engine",
    "get_session",
    "init_db",
    "sessionmaker",
    "session_scope",
]
