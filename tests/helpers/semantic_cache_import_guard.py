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
    "urllib",
    "http.client",
    "socket",
    "requests",
    "aiohttp",
    "httpx",
    "subprocess",
    "io",
    "shutil",
    "builtins",
)
ALLOWED_SEMANTIC_CACHE_IMPORTS = (
    "core.ai.bounded_insight_semantic_cache",
    "core.ai.cache_observability",
    "core.ai.exact_fuzzy_cache",
    "core.ai.semantic_cache_backend_selection",
)

FORBIDDEN_SEMANTIC_CACHE_CALLS = (
    "datetime.now",
    "datetime.utcnow",
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "uuid.uuid4",
    "time.time",
    "time.monotonic",
    "time.perf_counter",
    "open",
    "builtins.open",
    "io.open",
    "Path.write_text",
    "Path.write_bytes",
    "pathlib.Path.write_text",
    "pathlib.Path.write_bytes",
    "Path.touch",
    "Path.mkdir",
    "Path.rename",
    "Path.replace",
    "Path.unlink",
    "Path.rmdir",
    "pathlib.Path.touch",
    "pathlib.Path.mkdir",
    "pathlib.Path.rename",
    "pathlib.Path.replace",
    "pathlib.Path.unlink",
    "pathlib.Path.rmdir",
    "os.open",
    "os.mkdir",
    "os.makedirs",
    "os.remove",
    "os.unlink",
    "os.rename",
    "os.replace",
    "os.rmdir",
    "urllib.request.urlopen",
    "http.client.HTTPConnection",
    "http.client.HTTPSConnection",
    "socket.create_connection",
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.patch",
    "requests.delete",
    "httpx.get",
    "httpx.post",
    "aiohttp.ClientSession",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "os.system",
    "os.popen",
    "os.spawnl",
    "os.spawnle",
    "os.spawnlp",
    "os.spawnlpe",
    "os.spawnv",
    "os.spawnve",
    "os.spawnvp",
    "os.spawnvpe",
    "os.execl",
    "os.execle",
    "os.execlp",
    "os.execlpe",
    "os.execv",
    "os.execve",
    "os.execvp",
    "os.execvpe",
    "shutil.copy",
    "shutil.copy2",
    "shutil.copyfile",
    "shutil.copyfileobj",
    "shutil.copytree",
    "shutil.move",
    "os.getenv",
    "os.environ.get",
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
            else:
                imports.append("__dynamic_import__")
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
            else:
                imports.append("__dynamic_import__")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if import_aliases.get(node.func.id) == "importlib.import_module":
                name = _constant_string_argument(node)
                if name is not None:
                    imports.append(name)
                else:
                    imports.append("__dynamic_import__")

    offenders = [
        name
        for name in imports
        if not any(
            name == allowed or name.startswith(f"{allowed}.")
            for allowed in ALLOWED_SEMANTIC_CACHE_IMPORTS
        )
        if any(
            name == prefix or name.startswith(f"{prefix}.")
            for prefix in FORBIDDEN_SEMANTIC_CACHE_IMPORT_PREFIXES
        )
        or name == "__dynamic_import__"
        or _contains_forbidden_cache_segment(name)
    ]
    assert offenders == [], f"forbidden semantic-cache imports found: {offenders}"


def assert_no_forbidden_semantic_cache_calls(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    import_aliases: dict[str, str] = {}
    path_aliases: set[str] = set()
    file_handle_aliases: set[str] = set()
    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    import_aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Assign):
            if _is_path_expr(node.value, import_aliases, path_aliases):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        path_aliases.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.value is not None
                and _is_path_expr(node.value, import_aliases, path_aliases)
            ):
                path_aliases.add(node.target.id)
        elif isinstance(node, ast.With):
            _collect_path_open_context_aliases(
                node,
                import_aliases=import_aliases,
                path_aliases=path_aliases,
                file_handle_aliases=file_handle_aliases,
            )
        elif isinstance(node, ast.Call):
            call_name = _qualified_call_name(node.func, import_aliases)
            if call_name in FORBIDDEN_SEMANTIC_CACHE_CALLS:
                offenders.append(call_name)
            if _is_network_call_name(call_name):
                offenders.append(call_name or "network.call")
            if _is_path_write_call(node.func, import_aliases, path_aliases):
                offenders.append("Path.write")
            if _is_path_mutation_call(node.func, import_aliases, path_aliases):
                offenders.append("Path.mutate")
            if _is_file_handle_write_call(node.func, file_handle_aliases):
                offenders.append("Path.open.write")
            if call_name and (call_name.startswith("random.") or call_name.startswith("secrets.")):
                offenders.append(call_name)
            if _is_path_open_write_mode_call(node, import_aliases, path_aliases):
                offenders.append("Path.open.write-mode")
        elif isinstance(node, ast.Subscript):
            if _qualified_call_name(node.value, import_aliases) == "os.environ":
                offenders.append("os.environ[]")

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


def _is_network_call_name(call_name: str | None) -> bool:
    if call_name is None:
        return False
    return (
        call_name.endswith(".urlopen")
        or call_name.endswith(".HTTPConnection")
        or call_name.endswith(".HTTPSConnection")
        or call_name.endswith(".create_connection")
    )


def _qualified_call_name(node: ast.expr, import_aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return import_aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        owner = _qualified_call_name(node.value, import_aliases)
        if owner is None:
            return None
        return f"{owner}.{node.attr}"
    return None


def _is_path_constructor_call(node: ast.expr, import_aliases: dict[str, str]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    name = _qualified_call_name(node.func, import_aliases)
    return name in {"Path", "pathlib.Path"}


def _is_path_write_call(
    node: ast.expr,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if not isinstance(node, ast.Attribute):
        return False
    if node.attr in {"write_text", "write_bytes"}:
        return _is_path_expr(node.value, import_aliases, path_aliases)
    if node.attr == "write" and _is_path_open_call(node.value, import_aliases, path_aliases):
        return True
    return False


def _is_path_mutation_call(
    node: ast.expr,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if not isinstance(node, ast.Attribute):
        return False
    if node.attr not in {"touch", "mkdir", "rename", "replace", "unlink", "rmdir"}:
        return False
    return _is_path_expr(node.value, import_aliases, path_aliases)


def _is_path_open_write_mode_call(
    node: ast.Call,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if not _is_path_open_call(node, import_aliases, path_aliases):
        return False
    mode = _path_open_mode(node)
    if mode is None:
        return True
    return any(flag in mode for flag in ("w", "a", "x", "+"))


def _path_open_mode(node: ast.Call) -> str | None:
    if node.args:
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            return first_arg.value
        return None
    for keyword in node.keywords:
        if keyword.arg is None:
            return None
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            value = keyword.value.value
            if isinstance(value, str):
                return value
            return None
        if keyword.arg == "mode":
            return None
    return "r"


def _is_path_expr(
    node: ast.expr,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if isinstance(node, ast.Call):
        if _is_path_constructor_call(node, import_aliases):
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":
            return _is_path_expr(node.func.value, import_aliases, path_aliases)
        return False
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_path_expr(node.left, import_aliases, path_aliases)
    if isinstance(node, ast.Name):
        return node.id in path_aliases
    return False


def _is_path_open_call(
    node: ast.expr,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "open":
        return False
    return _is_path_expr(node.func.value, import_aliases, path_aliases)


def _collect_path_open_context_aliases(
    node: ast.With,
    *,
    import_aliases: dict[str, str],
    path_aliases: set[str],
    file_handle_aliases: set[str],
) -> None:
    for item in node.items:
        if (
            item.optional_vars is not None
            and isinstance(item.optional_vars, ast.Name)
            and _is_path_open_call(item.context_expr, import_aliases, path_aliases)
        ):
            file_handle_aliases.add(item.optional_vars.id)


def _is_file_handle_write_call(node: ast.expr, file_handle_aliases: set[str]) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "write"
        and isinstance(node.value, ast.Name)
        and node.value.id in file_handle_aliases
    )


def _contains_forbidden_cache_segment(name: str) -> bool:
    return any(
        segment in {"cache", "semantic_cache"} or segment.startswith("cache_")
        for segment in name.split(".")
    )
