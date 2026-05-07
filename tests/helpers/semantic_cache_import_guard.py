from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_SEMANTIC_CACHE_IMPORT_PREFIXES = (
    "app",
    "legacy_app",
    "fastapi",
    "sqlalchemy",
    "redis",
    "gptcache",
    "cachetools",
    "providers",
    "llm",
    "cache",
    "semantic_cache",
    "core.rag",
    "evals",
    "scripts.evals",
    "numpy",
    "pandas",
    "rapidfuzz",
    "sklearn",
    "faiss",
    "sentence_transformers",
    "openai",
    "anthropic",
)

FORBIDDEN_SEMANTIC_CACHE_CALLS = (
    "datetime.now",
    "datetime.utcnow",
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "uuid.uuid4",
    "time.time",
)


def assert_no_forbidden_semantic_cache_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    import_aliases: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                import_aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
            for alias in node.names:
                qualified_name = f"{node.module}.{alias.name}"
                if alias.name != "*":
                    imports.append(qualified_name)
                import_aliases[alias.asname or alias.name] = qualified_name
        elif isinstance(node, ast.ImportFrom):
            imports.extend(alias.name for alias in node.names)
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
            and isinstance(node.func.value, ast.Name)
            and import_aliases.get(node.func.value.id) == "importlib"
        ):
            name = _constant_string_argument(node)
            if name is not None:
                imports.append(name)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if import_aliases.get(node.func.id) == "importlib.import_module":
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
    assert offenders == [], f"forbidden semantic-cache imports found: {offenders}"


def assert_no_forbidden_semantic_cache_calls(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    import_aliases: dict[str, str] = {}
    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    import_aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Call):
            call_name = _qualified_call_name(node.func, import_aliases)
            if call_name is None:
                continue
            if call_name in FORBIDDEN_SEMANTIC_CACHE_CALLS:
                offenders.append(call_name)
            if call_name.startswith("random.") or call_name.startswith("secrets."):
                offenders.append(call_name)

    assert offenders == [], f"forbidden semantic-cache calls found: {offenders}"


def _constant_string_argument(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value

    for keyword in node.keywords:
        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
            value = keyword.value.value
            if isinstance(value, str):
                return value

    return None


def _qualified_call_name(node: ast.expr, import_aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return import_aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        owner = _qualified_call_name(node.value, import_aliases)
        if owner is None:
            return None
        return f"{owner}.{node.attr}"
    return None
