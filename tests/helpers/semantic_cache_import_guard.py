from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_SEMANTIC_CACHE_IMPORT_PREFIXES = (
    "app",
    "legacy_app",
    "providers",
    "llm",
    "fastapi",
    "sqlalchemy",
    "redis",
    "cache",
    "semantic_cache",
    "gptcache",
    "scripts.evals",
    "evals",
    "core.rag",
)


def assert_no_forbidden_semantic_cache_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
        ):
            name = _constant_string_argument(node)
            if name is not None:
                imports.append(name)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
        ):
            name = _constant_string_argument(node)
            if name is not None:
                imports.append(name)

    offenders = [
        name
        for name in imports
        if any(
            name == prefix or name.startswith(f"{prefix}.")
            for prefix in FORBIDDEN_SEMANTIC_CACHE_IMPORT_PREFIXES
        )
    ]
    assert offenders == []


def _constant_string_argument(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value

    for keyword in node.keywords:
        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
            value = keyword.value.value
            if isinstance(value, str):
                return value

    return None
