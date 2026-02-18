from __future__ import annotations

import ast
import re
import tokenize
from io import StringIO
from pathlib import Path

from tests.feature_manifest import (
    CP3_SKIP_DRIFT_TARGET_FILES,
    FEATURE_TODO_KEYS,
)


def _read_target(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collect_relevant_source(content: str) -> str:
    """Return token stream text without comments/strings to avoid false positives."""
    relevant: list[str] = []
    for token in tokenize.generate_tokens(StringIO(content).readline):
        if token.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        relevant.append(token.string)
    return " ".join(relevant)


def _collect_pytest_skip_aliases(source_tree: ast.AST) -> tuple[set[str], set[str]]:
    """Collect pytest module aliases and direct skip function aliases."""
    pytest_module_aliases: set[str] = {"pytest"}
    pytest_skip_aliases: set[str] = set()
    for node in ast.walk(source_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pytest":
                    pytest_module_aliases.add(alias.asname or alias.name)
        if isinstance(node, ast.ImportFrom) and node.module == "pytest":
            for alias in node.names:
                if alias.name == "skip":
                    pytest_skip_aliases.add(alias.asname or alias.name)
    return pytest_module_aliases, pytest_skip_aliases


def _is_pytest_skip_call(
    node: ast.Call,
    *,
    pytest_module_aliases: set[str],
    pytest_skip_aliases: set[str],
) -> bool:
    if isinstance(node.func, ast.Attribute):
        return (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id in pytest_module_aliases
            and node.func.attr == "skip"
        )
    return isinstance(node.func, ast.Name) and node.func.id in pytest_skip_aliases


def _extract_key_arg(node: ast.Call) -> str | None:
    if (
        len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        return node.args[1].value
    for keyword in node.keywords:
        if keyword.arg == "key" and isinstance(keyword.value, ast.Constant):
            if isinstance(keyword.value.value, str):
                return keyword.value.value
    return None


def test_cp3_target_files_use_canonical_skip_protocol() -> None:
    """CP3 target suites must use feature-manifest skip protocol only."""
    tests_root = Path(__file__).parent
    missing_files: list[str] = []
    import_violations: list[str] = []
    protocol_violations: list[str] = []
    invalid_keys: list[str] = []

    for filename in CP3_SKIP_DRIFT_TARGET_FILES:
        path = tests_root / filename
        if not path.exists():
            missing_files.append(filename)
            continue

        content = _read_target(path)
        source_tree = ast.parse(content, filename=filename)
        non_string_source = _collect_relevant_source(content)
        pytest_module_aliases, pytest_skip_aliases = _collect_pytest_skip_aliases(source_tree)

        has_manifest_import = False
        has_require_feature_call = False
        has_pytest_skip = False

        for node in ast.walk(source_tree):
            if isinstance(node, ast.ImportFrom) and node.module == "tests.feature_manifest":
                imported_names = {alias.name for alias in node.names}
                if (
                    "FEATURE_REASON" in imported_names
                    and "require_feature_or_raise" in imported_names
                ):
                    has_manifest_import = True
            if isinstance(node, ast.Call):
                if _is_pytest_skip_call(
                    node,
                    pytest_module_aliases=pytest_module_aliases,
                    pytest_skip_aliases=pytest_skip_aliases,
                ):
                    has_pytest_skip = True
                if isinstance(node.func, ast.Name) and node.func.id == "require_feature_or_raise":
                    has_require_feature_call = True
                    key_arg = _extract_key_arg(node)
                    if key_arg is not None and key_arg not in FEATURE_TODO_KEYS:
                        invalid_keys.append(f"{filename}:{key_arg}")

        if not has_manifest_import:
            import_violations.append(f"{filename}: missing canonical tests.feature_manifest import")
        if has_pytest_skip:
            protocol_violations.append(f"{filename}: contains pytest.skip() call")
        if re.search(r"feature_disabled\s*:", non_string_source):
            protocol_violations.append(f"{filename}: contains raw feature_disabled marker in code")
        if not has_require_feature_call:
            protocol_violations.append(f"{filename}: missing require_feature_or_raise call")

    assert not missing_files, f"Missing CP3 target files: {missing_files}"
    assert not import_violations, f"Import protocol violations in CP3 targets: {import_violations}"
    assert (
        not protocol_violations
    ), f"Skip protocol violations in CP3 targets: {protocol_violations}"
    assert not invalid_keys, f"Unknown feature-manifest keys in CP3 targets: {invalid_keys}"


def test_is_pytest_skip_call_detects_direct_skip_import_alias() -> None:
    code = "from pytest import skip as ps\nps('x')\n"
    tree = ast.parse(code)
    aliases, skip_aliases = _collect_pytest_skip_aliases(tree)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert any(
        _is_pytest_skip_call(
            node,
            pytest_module_aliases=aliases,
            pytest_skip_aliases=skip_aliases,
        )
        for node in calls
    )
