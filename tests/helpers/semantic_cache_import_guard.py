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
    "core.ai",
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
    "importlib",
    "os",
    "shutil",
    "builtins",
)
FORBIDDEN_CORE_AI_FACADE_IMPORTS = (
    "core.ai",
    "core.ai.DirectInsightProviderStub",
    "core.ai.InsightProviderLoadError",
    "core.ai.KnowledgePolicy",
    "core.ai.PhilosophyRolloutPolicy",
    "core.ai.InsightTransparencyNotice",
    "core.ai.InsightTransparencyUnavailableError",
    "core.ai.PreparedInsightRuntime",
    "core.ai.load_insight_provider",
    "core.ai.prepare_insight_runtime",
    "core.ai.require_ai_generated_insight_notice",
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
    "__builtins__.open",
    "io.open",
    "Path.write_text",
    "Path.write_bytes",
    "Path.open",
    "Path.chmod",
    "Path.hardlink_to",
    "Path.lchmod",
    "Path.link_to",
    "Path.symlink_to",
    "pathlib.Path.write_text",
    "pathlib.Path.write_bytes",
    "pathlib.Path.open",
    "pathlib.Path.chmod",
    "pathlib.Path.hardlink_to",
    "pathlib.Path.lchmod",
    "pathlib.Path.link_to",
    "pathlib.Path.symlink_to",
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
PATH_CONSTRUCTOR_NAMES = frozenset(
    {
        "Path",
        "pathlib.Path",
        "PosixPath",
        "pathlib.PosixPath",
        "WindowsPath",
        "pathlib.WindowsPath",
    }
)
PATH_MUTATION_METHODS = frozenset(
    {
        "chmod",
        "hardlink_to",
        "lchmod",
        "link_to",
        "mkdir",
        "rename",
        "replace",
        "rmdir",
        "symlink_to",
        "touch",
        "unlink",
    }
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
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for target_name, target_value in _target_names_for_value(target, node.value):
                    alias_ref = _qualified_call_name(target_value, import_aliases)
                    if alias_ref in {"__import__", "importlib.import_module"}:
                        import_aliases[target_name] = alias_ref
        elif isinstance(node, ast.Call) and _is_builtin_import_ref(node.func, import_aliases):
            name = _constant_string_argument(node)
            if name is not None:
                imports.append(name)
            else:
                imports.append("__dynamic_import__")
        elif isinstance(node, ast.Call) and _is_import_module_call_from_dynamic_receiver(
            node,
            import_aliases,
        ):
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
            elif import_aliases.get(node.func.id) == "__import__":
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
        or name in FORBIDDEN_CORE_AI_FACADE_IMPORTS
    ]
    assert offenders == [], f"forbidden semantic-cache imports found: {offenders}"


def assert_no_forbidden_semantic_cache_calls(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    import_aliases: dict[str, str] = {}
    path_aliases: set[str] = set()
    file_handle_aliases: set[str] = set()
    environ_aliases: set[str] = set()
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
            for target in node.targets:
                for target_name, target_value in _target_names_for_value(target, node.value):
                    if _is_open_effect_ref(target_value, import_aliases):
                        offenders.append("open.alias")
                    if _is_path_effect_method_ref(target_value, import_aliases, path_aliases):
                        offenders.append("Path.method-alias")
                    effect_ref = _qualified_call_name(target_value, import_aliases)
                    if effect_ref in {"getattr", "__import__", "importlib.import_module"}:
                        import_aliases[target_name] = effect_ref
                    if _is_os_effect_ref(effect_ref):
                        offenders.append(f"{effect_ref}.alias")
                    os_getattr_ref = _os_getattr_effect_name(target_value, import_aliases)
                    if os_getattr_ref is not None:
                        offenders.append(f"{os_getattr_ref}.alias")
                    if _qualified_call_name(target_value, import_aliases) == "os.getenv":
                        offenders.append("os.getenv.alias")
                    if _qualified_call_name(
                        target_value, import_aliases
                    ) == "os.environ" or _is_os_environ_value_ref(
                        target_value, import_aliases, environ_aliases
                    ):
                        offenders.append("os.environ.value")
                        environ_aliases.add(target_name)
                    dynamic_import = _dynamic_import_name(target_value, import_aliases)
                    if dynamic_import is not None:
                        import_aliases[target_name] = dynamic_import
                    if effect_ref is not None and (
                        _is_os_environ_call_name(effect_ref)
                        or _is_os_effect_ref(effect_ref)
                        or effect_ref == "os.getenv"
                    ):
                        import_aliases[target_name] = effect_ref
                if isinstance(target, ast.Attribute):
                    if _is_open_effect_ref(node.value, import_aliases):
                        offenders.append("open.alias")
                    if _is_path_effect_method_ref(node.value, import_aliases, path_aliases):
                        offenders.append("Path.method-alias")
                    effect_ref = _qualified_call_name(node.value, import_aliases)
                    if _is_os_effect_ref(effect_ref):
                        offenders.append(f"{effect_ref}.alias")
                    dynamic_import = _dynamic_import_name(node.value, import_aliases)
                    if dynamic_import is not None:
                        offenders.append("__dynamic_import__")
            _collect_path_constructor_aliases(
                node.targets,
                node.value,
                import_aliases=import_aliases,
            )
            _collect_path_expr_aliases(
                node.targets,
                node.value,
                import_aliases=import_aliases,
                path_aliases=path_aliases,
            )
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None and _is_open_effect_ref(node.value, import_aliases):
                offenders.append("open.alias")
            if node.value is not None and _is_path_effect_method_ref(
                node.value,
                import_aliases,
                path_aliases,
            ):
                offenders.append("Path.method-alias")
            effect_ref = (
                _qualified_call_name(node.value, import_aliases) if node.value is not None else None
            )
            if isinstance(node.target, ast.Name) and effect_ref in {
                "getattr",
                "__import__",
                "importlib.import_module",
            }:
                import_aliases[node.target.id] = effect_ref
            if _is_os_effect_ref(effect_ref):
                offenders.append(f"{effect_ref}.alias")
            if node.value is not None:
                os_getattr_ref = _os_getattr_effect_name(node.value, import_aliases)
                if os_getattr_ref is not None:
                    offenders.append(f"{os_getattr_ref}.alias")
            if (
                node.value is not None
                and _qualified_call_name(node.value, import_aliases) == "os.getenv"
            ):
                offenders.append("os.getenv.alias")
            if (
                isinstance(node.target, ast.Name)
                and node.value is not None
                and (
                    _qualified_call_name(node.value, import_aliases) == "os.environ"
                    or _is_os_environ_value_ref(node.value, import_aliases, environ_aliases)
                )
            ):
                offenders.append("os.environ.value")
                environ_aliases.add(node.target.id)
            if isinstance(node.target, ast.Name) and node.value is not None:
                dynamic_import = _dynamic_import_name(node.value, import_aliases)
                if dynamic_import is not None:
                    import_aliases[node.target.id] = dynamic_import
                if effect_ref is not None and (
                    _is_os_environ_call_name(effect_ref)
                    or _is_os_effect_ref(effect_ref)
                    or effect_ref == "os.getenv"
                ):
                    import_aliases[node.target.id] = effect_ref
            if isinstance(node.target, ast.Name) and node.value is not None:
                path_constructor_ref = _qualified_call_name(node.value, import_aliases)
                if path_constructor_ref in {"Path", "pathlib.Path"}:
                    import_aliases[node.target.id] = path_constructor_ref
            if (
                isinstance(node.target, ast.Name)
                and node.value is not None
                and _is_path_expr(node.value, import_aliases, path_aliases)
            ):
                path_aliases.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for default in _callable_defaults(node):
                if _is_open_effect_ref(default, import_aliases):
                    offenders.append("open.alias")
                if _is_path_effect_method_ref(default, import_aliases, path_aliases):
                    offenders.append("Path.method-alias")
                effect_ref = _qualified_call_name(default, import_aliases)
                if _is_os_effect_ref(effect_ref):
                    offenders.append(f"{effect_ref}.alias")
                os_getattr_ref = _os_getattr_effect_name(default, import_aliases)
                if os_getattr_ref is not None:
                    offenders.append(f"{os_getattr_ref}.alias")
                dynamic_import = _dynamic_import_name(default, import_aliases)
                if dynamic_import is not None:
                    offenders.append("__dynamic_import__")
        elif isinstance(node, ast.With):
            _collect_path_open_context_aliases(
                node,
                import_aliases=import_aliases,
                path_aliases=path_aliases,
                file_handle_aliases=file_handle_aliases,
            )
        elif isinstance(node, ast.Call):
            call_name = _qualified_call_name(node.func, import_aliases)
            if isinstance(node.func, ast.NamedExpr):
                if _is_open_effect_ref(node.func.value, import_aliases):
                    offenders.append("open.alias")
                if _is_path_effect_method_ref(node.func.value, import_aliases, path_aliases):
                    offenders.append("Path.method-alias")
                effect_ref = _qualified_call_name(node.func.value, import_aliases)
                if effect_ref is not None and _is_os_effect_ref(effect_ref):
                    offenders.append(effect_ref)
            if call_name in {"__import__", "importlib.import_module"} or _is_builtin_import_ref(
                node.func,
                import_aliases,
            ):
                offenders.append("__dynamic_import__")
            if call_name == "__dynamic_import__" or (
                call_name is not None and call_name.startswith("__dynamic_import__.")
            ):
                offenders.append("__dynamic_import__")
            if call_name in FORBIDDEN_SEMANTIC_CACHE_CALLS:
                offenders.append(call_name)
            if _is_network_call_name(call_name):
                offenders.append(call_name or "network.call")
            if _is_os_environ_call_name(call_name):
                offenders.append(call_name or "os.environ.call")
            if _is_os_environ_alias_call_name(call_name, environ_aliases):
                offenders.append(call_name or "os.environ.alias.call")
            os_getattr_ref = _os_getattr_effect_name(node.func, import_aliases)
            if os_getattr_ref is not None:
                offenders.append(os_getattr_ref)
            if any(
                _is_os_environ_value_ref(argument, import_aliases, environ_aliases)
                for argument in node.args
            ):
                offenders.append("os.environ.value")
            if any(
                _is_os_environ_value_ref(keyword.value, import_aliases, environ_aliases)
                for keyword in node.keywords
            ):
                offenders.append("os.environ.value")
            if _is_path_write_call(node.func, import_aliases, path_aliases):
                offenders.append("Path.write")
            if _is_path_getattr_effect_call(node.func, import_aliases, path_aliases):
                offenders.append("Path.getattr")
            if _is_path_mutation_call(node.func, import_aliases, path_aliases):
                offenders.append("Path.mutate")
            if _is_file_handle_write_call(node.func, file_handle_aliases):
                offenders.append("Path.open.write")
            if call_name and (call_name.startswith("random.") or call_name.startswith("secrets.")):
                offenders.append(call_name)
            if _is_path_open_write_mode_call(node, import_aliases, path_aliases):
                offenders.append("Path.open.write-mode")
            if _is_path_getattr_effect_call(node, import_aliases, path_aliases):
                offenders.append("Path.getattr")
        elif isinstance(node, ast.Subscript):
            subscript_name = _qualified_call_name(node.value, import_aliases)
            if subscript_name == "os.environ" or subscript_name in environ_aliases:
                offenders.append("os.environ[]")
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            if _is_os_environ_value_ref(node.iter, import_aliases, environ_aliases):
                offenders.append("os.environ.value")
        elif isinstance(node, ast.comprehension):
            if _is_os_environ_value_ref(node.iter, import_aliases, environ_aliases):
                offenders.append("os.environ.value")
        elif isinstance(node, ast.expr) and _is_os_environ_value_ref(
            node,
            import_aliases,
            environ_aliases,
        ):
            offenders.append("os.environ.value")

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


def _is_os_environ_call_name(call_name: str | None) -> bool:
    return call_name is not None and call_name.startswith("os.environ.")


def _is_os_environ_alias_call_name(call_name: str | None, environ_aliases: set[str]) -> bool:
    if call_name is None:
        return False
    return any(call_name == alias or call_name.startswith(f"{alias}.") for alias in environ_aliases)


def _is_os_environ_value_ref(
    node: ast.expr,
    import_aliases: dict[str, str],
    environ_aliases: set[str],
) -> bool:
    name = _qualified_call_name(node, import_aliases)
    return (
        name == "os.environ"
        or (name is not None and name in environ_aliases)
        or _os_getattr_effect_name(node, import_aliases) == "os.environ"
        or _is_os_environ_dict_subscript(node, import_aliases)
    )


def _qualified_call_name(node: ast.expr, import_aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return import_aliases.get(node.id, node.id)
    if isinstance(node, ast.NamedExpr):
        return _qualified_call_name(node.value, import_aliases)
    if isinstance(node, ast.Attribute):
        owner = _qualified_call_name(node.value, import_aliases)
        if owner is None and isinstance(node.value, ast.Call):
            owner = _dynamic_import_name(node.value, import_aliases)
        if owner is None:
            return None
        qualified = f"{owner}.{node.attr}"
        if qualified in {"builtins.__import__", "__builtins__.__import__"}:
            return "__import__"
        return qualified
    return None


def _dynamic_import_name(node: ast.expr, import_aliases: dict[str, str]) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if _is_builtin_import_ref(node.func, import_aliases):
        return _constant_string_argument(node) or "__dynamic_import__"
    if _is_import_module_call_from_dynamic_receiver(node, import_aliases):
        return "__dynamic_import__"
    if _qualified_call_name(node.func, import_aliases) == "importlib.import_module":
        return _constant_string_argument(node) or "__dynamic_import__"
    return None


def _is_builtin_import_ref(node: ast.expr, import_aliases: dict[str, str]) -> bool:
    name = _qualified_call_name(node, import_aliases)
    if name in {"__import__", "builtins.__import__", "__builtins__.__import__"}:
        return True
    return (
        isinstance(node, ast.Subscript)
        and _qualified_call_name(node.value, import_aliases) == "__builtins__"
        and _constant_subscript_key(node) == "__import__"
    )


def _is_import_module_call_from_dynamic_receiver(
    node: ast.expr,
    import_aliases: dict[str, str],
) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "import_module"
        and isinstance(node.func.value, ast.Call)
        and _qualified_call_name(node.func.value.func, import_aliases) == "__import__"
    )


def _os_getattr_effect_name(node: ast.expr, import_aliases: dict[str, str]) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if _qualified_call_name(node.func, import_aliases) != "getattr":
        return None
    if len(node.args) < 2:
        return None
    owner_name = _qualified_call_name(node.args[0], import_aliases)
    if owner_name != "os":
        return None
    attr_name = _constant_string_argument_at(node, 1)
    if attr_name == "environ":
        return "os.environ"
    if attr_name is None:
        return None
    effect_name = f"os.{attr_name}"
    if _is_os_effect_ref(effect_name) or effect_name == "os.getenv":
        return effect_name
    return None


def _constant_string_argument_at(node: ast.Call, index: int) -> str | None:
    if len(node.args) <= index:
        return None
    argument = node.args[index]
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value
    return None


def _is_os_environ_dict_subscript(node: ast.expr, import_aliases: dict[str, str]) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    key = _constant_subscript_key(node)
    if key != "environ":
        return False
    if _qualified_call_name(node.value, import_aliases) == "os.__dict__":
        return True
    return _is_vars_os_call(node.value, import_aliases)


def _constant_subscript_key(node: ast.Subscript) -> str | None:
    if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
        return node.slice.value
    return None


def _callable_defaults(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda,
) -> tuple[ast.expr, ...]:
    defaults: list[ast.expr] = list(node.args.defaults)
    defaults.extend(default for default in node.args.kw_defaults if default is not None)
    return tuple(defaults)


def _is_vars_os_call(node: ast.expr, import_aliases: dict[str, str]) -> bool:
    return (
        isinstance(node, ast.Call)
        and _qualified_call_name(node.func, import_aliases) == "vars"
        and len(node.args) == 1
        and _qualified_call_name(node.args[0], import_aliases) == "os"
    )


def _is_os_effect_ref(call_name: str | None) -> bool:
    if call_name is None:
        return False
    return call_name in FORBIDDEN_SEMANTIC_CACHE_CALLS and call_name.startswith("os.")


def _target_names_for_value(target: ast.expr, value: ast.expr) -> tuple[tuple[str, ast.expr], ...]:
    if isinstance(target, ast.Name):
        return ((target.id, value),)
    if (
        isinstance(target, (ast.Tuple, ast.List))
        and isinstance(value, (ast.Tuple, ast.List))
        and len(target.elts) == len(value.elts)
    ):
        names: list[tuple[str, ast.expr]] = []
        for target_item, value_item in zip(target.elts, value.elts, strict=True):
            names.extend(_target_names_for_value(target_item, value_item))
        return tuple(names)
    return ()


def _collect_path_constructor_aliases(
    targets: list[ast.expr],
    value: ast.expr,
    *,
    import_aliases: dict[str, str],
) -> None:
    for target in targets:
        for target_name, target_value in _target_names_for_value(target, value):
            path_constructor_ref = _qualified_call_name(target_value, import_aliases)
            if path_constructor_ref in PATH_CONSTRUCTOR_NAMES:
                import_aliases[target_name] = path_constructor_ref


def _collect_path_expr_aliases(
    targets: list[ast.expr],
    value: ast.expr,
    *,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> None:
    for target in targets:
        for target_name, target_value in _target_names_for_value(target, value):
            if _is_path_expr(
                target_value,
                import_aliases,
                path_aliases,
            ) or _is_path_container_expr(target_value, import_aliases, path_aliases):
                path_aliases.add(target_name)


def _is_path_constructor_call(node: ast.expr, import_aliases: dict[str, str]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    name = _qualified_call_name(node.func, import_aliases)
    return name in PATH_CONSTRUCTOR_NAMES


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
    if node.attr not in PATH_MUTATION_METHODS:
        return False
    return _is_path_expr(node.value, import_aliases, path_aliases)


def _is_path_effect_method_ref(
    node: ast.expr,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if not isinstance(node, ast.Attribute):
        return False
    if node.attr in {"write_text", "write_bytes", "open"}:
        return _is_path_expr(node.value, import_aliases, path_aliases)
    if node.attr in PATH_MUTATION_METHODS:
        return _is_path_expr(node.value, import_aliases, path_aliases)
    return False


def _is_open_effect_ref(node: ast.expr, import_aliases: dict[str, str]) -> bool:
    return _qualified_call_name(node, import_aliases) in {
        "open",
        "builtins.open",
        "__builtins__.open",
        "io.open",
    }


def _is_path_getattr_effect_call(
    node: ast.expr,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if _qualified_call_name(node.func, import_aliases) != "getattr":
        return False
    if len(node.args) < 2:
        return False
    method_name = node.args[1]
    if not isinstance(method_name, ast.Constant) or not isinstance(method_name.value, str):
        return False
    if method_name.value not in PATH_MUTATION_METHODS | {"open", "write_bytes", "write_text"}:
        return False
    return _is_path_expr(node.args[0], import_aliases, path_aliases)


def _is_path_open_write_mode_call(
    node: ast.Call,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if _is_path_open_call(node, import_aliases, path_aliases):
        mode = _path_open_mode(node)
    elif _is_path_open_class_call(node, import_aliases, path_aliases):
        mode = _path_open_class_mode(node)
    else:
        return False
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


def _path_open_class_mode(node: ast.Call) -> str | None:
    if len(node.args) > 1:
        mode_arg = node.args[1]
        if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
            return mode_arg.value
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
    if isinstance(node, ast.Subscript):
        return _is_path_expr(node.value, import_aliases, path_aliases)
    if isinstance(node, ast.Name):
        return node.id in path_aliases
    return False


def _is_path_container_expr(
    node: ast.expr,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(_is_path_expr(item, import_aliases, path_aliases) for item in node.elts)
    if isinstance(node, ast.Dict):
        return any(_is_path_expr(item, import_aliases, path_aliases) for item in node.values)
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


def _is_path_open_class_call(
    node: ast.expr,
    import_aliases: dict[str, str],
    path_aliases: set[str],
) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "open":
        return False
    if _qualified_call_name(node.func, import_aliases) not in {"Path.open", "pathlib.Path.open"}:
        return False
    if not node.args:
        return True
    return _is_path_expr(node.args[0], import_aliases, path_aliases)


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
