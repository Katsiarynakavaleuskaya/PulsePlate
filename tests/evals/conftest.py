"""Shared pytest configuration for tests/evals/.

RU: Импорты evals используют стандартный путь через pyproject.toml pythonpath.
EN: Evals tests use standard package imports from the repository root,
    as provided by the test runner (pyproject.toml: pythonpath = ".").

Import hygiene policy forbids mutating sys.path from test files.
"""

from __future__ import annotations
