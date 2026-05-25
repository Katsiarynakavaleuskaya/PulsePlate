#!/usr/bin/env python3
"""Fail-closed guard for PR-A2 RAG hardening closeout truth."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterator
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

PR_NUMBER = "1415"
TITLE = "feat(rag): harden degraded retrieval paths and keep contracts additive"
MERGE_DATE = "2026-04-14"
MERGE_TIMESTAMP = "2026-04-14T20:59:47Z"
MERGE_COMMIT = "146da0e0d269acea5ba946d239997705ebaf62c3"  # pragma: allowlist secret
ORIGINAL_BRANCH = "feat/rag-hardening-followthrough"

DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
DEFAULT_MAPPING = REPO_ROOT / "docs" / "review" / "PR_1415_FIXED_MAPPING.md"
DEFAULT_SEMANTIC_CACHE_GATE = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
)

REQUIRED_GATE_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

REQUIRED_ENUM_MEMBERS = {
    "core/rag/contracts.py": {
        "RAGDegradedReason": {
            "VECTOR_FALLBACK_NO_RESULTS": "vector_fallback_no_results",
            "VECTOR_FALLBACK_EXCEPTION": "vector_fallback_exception",
            "VECTOR_FALLBACK_SUBJECT_MISSING": "vector_fallback_subject_missing",
            "FORMATTED_CONTEXT_MALFORMED": "formatted_context_malformed",
            "REDACTED_CONTEXT_MALFORMED": "redacted_context_malformed",
        },
    },
}

REQUIRED_FUNCTIONS = {
    "core/rag/orchestration.py": (
        "def _resolve_confidence",
        "def _non_rag_result",
    ),
    "core/rag/vector_rag.py": (
        "def _normalize_embedding_vector",
        "def _retrieve_vector_from_db",
        "def _retrieve_vector_postgres",
        "def _retrieve_vector_sqlite",
    ),
}

REQUIRED_ATTRIBUTE_REFS = {
    "core/rag/orchestration.py": (
        "RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED",
        "RAGDegradedReason.REDACTED_CONTEXT_MALFORMED",
    ),
    "core/rag/vector_rag.py": (
        "RAGDegradedReason.VECTOR_FALLBACK_SUBJECT_MISSING",
        "RAGDegradedReason.VECTOR_FALLBACK_NO_RESULTS",
    ),
}

REQUIRED_KEYWORD_NAME_REFS = {
    "core/rag/orchestration.py": (("subject_id", "subject_id"),),
}

REQUIRED_CALL_KEYWORD_NAME_REFS = {
    "core/rag/vector_rag.py": (
        ("_retrieve_vector_from_db", "apply_user_rls_context", "user_id", "subject_id"),
    ),
}

REQUIRED_TEST_FUNCTIONS = {
    "tests/test_rag_orchestration.py": {
        "test_validation_disabled_ignores_stale_retriever_confidence",
        "test_vector_path_propagates_subject_id",
        "test_empty_formatted_context_returns_fail_safe_non_rag_result",
        "test_non_string_redacted_context_returns_fail_safe_non_rag_result",
        "test_rag_orchestration_denies_canonical_candidates_when_retrieval_is_degraded",
    },
    "tests/test_vector_rag.py": {
        "test_missing_subject_id_returns_empty_without_encoding",
        "test_wrong_query_dimensions_return_empty_without_db_work",
        "test_retrieve_vector_sqlite_binds_subject_id",
        "test_vector_success_skips_malformed_rows_without_poisoning_whole_result",
    },
    "tests/test_insight_rag_response_fields.py": {
        "test_rag_late_context_collapse_returns_non_rag_contract",
        "test_rag_late_redaction_collapse_returns_non_rag_contract",
        "test_rag_response_confidence_uses_active_output_chunks",
        "test_rag_response_confidence_uses_filtered_subset_chunks",
    },
}

UNICODE_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
        "\u2007": " ",
        "\u202f": " ",
    }
)

CLAUSE_SPLIT_RE = re.compile(
    r"\b(?:but|however|though|although|yet|while|whereas|therefore|thus|so|hence|"
    r"and|also|plus|despite|notwithstanding|nevertheless)\b|[;]",
    re.I,
)
CONTRAST_SPLIT_RE = re.compile(
    r"\b(?:but|however|though|although|yet|while|whereas|therefore|thus|so|hence|"
    r"despite|notwithstanding|nevertheless)\b|[;]",
    re.I,
)
NEGATION_RE = re.compile(
    r"\b(no|not|never|does\s+not|do\s+not|must\s+not|cannot|can't|without|"
    r"out\s+of\s+scope|deferred|blocked|"
    r"does\s+not\s+claim)\b",
    re.I,
)
PR_A2_RE = re.compile(r"\b(?:PR[-\s]?A2|A2|PR\s*#?\s*1415|#1415)\b", re.I)
STALE_A2_WORD_RE = re.compile(
    r"\b(planned|pending|in[-\s]+progress|active\s+(?:implementation|runtime|lane)|"
    r"next\s+runtime|next\s+logical|"
    r"will\s+implement|missing\s+implementation|still\s+requires\s+PR[-\s]?A2|"
    r"PR-TBD-RAG-HARDENING-FOLLOWTHROUGH|residual\s+RAG\s+technical\s+debt)\b",
    re.I,
)
STALE_SECTION_RE = re.compile(
    r"\b(Status:\s*[^\n]*(?:Planned|in[-\s]+progress|pending)|"
    r"PR-TBD-RAG-HARDENING-FOLLOWTHROUGH|residual\s+RAG\s+technical\s+debt|"
    r"still\s+requires\s+PR[-\s]?A2|next\s+runtime|will\s+implement|"
    r"missing\s+implementation)\b",
    re.I,
)
MAPPING_STALE_RE = re.compile(
    r"\b(merge-readiness\s+stays\s+open|full\s+local\s+`?make\s+verify`?\s+completes|"
    r"re-check\s+on\s+current\s+head\s+before\s+merge|all\s+required\s+checks\s+pass)\b",
    re.I,
)
FORBIDDEN_SURFACE_RE = re.compile(
    r"\b(semantic[-\s]?cache|redis|gpt[-\s]?cache|graph[-\s]?rag|"
    r"context[-\s]?manifest|contextmanifest|db\s+persistence|database\s+persistence|"
    r"public\s+(?:route|routes|api|endpoint|endpoints)|openapi|dtos?|"
    r"provider\s+integration|provider[-\s]+side|chain[-\s]?of[-\s]?thought|"
    r"tree[-\s]?of[-\s]?thought|recursive\s+learning|default\s+activation|"
    r"default[-\s]?on)\b",
    re.I,
)
POSITIVE_ACTION_RE = re.compile(
    r"\b(opens?|opened|enables?|enabled|implements?|implemented|approves?|approved|"
    r"allows?|allowed|permits?|permitted|authorizes?|authorized|selects?|selected|"
    r"activates?|activated|rolls?\s+out|wires?|wired|adds?|added|available|"
    r"production[-\s]?ready|rollout[-\s]?ready|default[-\s]?on)\b",
    re.I,
)
OVERCLAIM_RE = re.compile(
    r"\b(benchmark[-\s]?proven|scientifically\s+validated|new\s+benchmark\s+results?|"
    r"latency\s+(?:wins?|optimized|improved|reduced)|accuracy\s+(?:gains?|improved)|"
    r"RAGAS\s+(?:pass|quality\s+proof|proves?)|production\s+RAG\s+robustness|"
    r"proves?\s+production\s+quality|guarantees?\s+retrieval\s+quality)\b",
    re.I,
)
LOCAL_PATH_RE = re.compile(r"(/Users/|(?:^|[\s`])worktrees/|artifacts/orchestration)")


def _display(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return "<external-path>"


def _read_text(path: Path, repo_root: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{_display(path, repo_root)}: unable to read: {type(exc).__name__}")
        return ""


def _normalize(text: str) -> str:
    return text.translate(UNICODE_TRANSLATION)


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", _normalize(text)).strip()


def _sentences(text: str) -> list[str]:
    normalized = _normalize(text)
    units: list[str] = []
    for paragraph in re.split(r"\n{2,}", normalized):
        line = re.sub(r"[ \t]*\n[ \t]*", " ", paragraph.strip())
        units.extend(re.split(r"(?<=[.!?])\s+", line))
    return [unit.strip() for unit in units if unit.strip()]


def _line_units(text: str) -> list[str]:
    return [line.strip() for line in _normalize(text).splitlines() if line.strip()]


def _clauses(text: str, *, split_soft: bool = False) -> list[str]:
    clauses: list[str] = []
    for sentence in _sentences(text):
        splitter = CLAUSE_SPLIT_RE if split_soft else CONTRAST_SPLIT_RE
        clauses.extend(splitter.split(sentence))
    return [clause.strip() for clause in clauses if clause.strip()]


def _slice(text: str, start: str, end_pattern: str, *, label: str, errors: list[str]) -> str:
    start_index = text.find(start)
    if start_index == -1:
        errors.append(f"{label}: missing start anchor {start!r}")
        return ""
    match = re.search(end_pattern, text[start_index + len(start) :])
    if not match:
        errors.append(f"{label}: missing end anchor {end_pattern!r}")
        return text[start_index:]
    end_index = start_index + len(start) + match.start()
    return text[start_index:end_index]


def _require_tokens(text: str, label: str, tokens: tuple[str, ...], errors: list[str]) -> None:
    compacted = _compact(text).lower()
    for token in tokens:
        if token.lower() not in compacted:
            errors.append(f"{label}: missing {token}")


def _require_pr1415_evidence(text: str, label: str, errors: list[str]) -> None:
    _require_tokens(
        text,
        label,
        (
            f"PR #{PR_NUMBER}",
            TITLE,
            MERGE_DATE,
            MERGE_TIMESTAMP,
            MERGE_COMMIT,
            ORIGINAL_BRANCH,
        ),
        errors,
    )


def _gate_markers(text: str) -> dict[str, list[str]]:
    markers: dict[str, list[str]] = {}
    for match in re.finditer(r"<!--\s*([A-Z0-9_]+):\s*([^>]+?)\s*-->", text):
        markers.setdefault(match.group(1), []).append(match.group(2).strip())
    return markers


def _check_gate_markers(gate_text: str, errors: list[str]) -> None:
    markers = _gate_markers(gate_text)
    for key, expected in REQUIRED_GATE_MARKERS.items():
        values = markers.get(key, [])
        if values != [expected]:
            errors.append(
                f"semantic-cache gate marker {key}: expected exactly {[expected]!r}, got {values!r}"
            )


def _parse_python(path: Path, repo_root: Path, errors: list[str]) -> ast.Module | None:
    text = _read_text(path, repo_root, errors)
    if not text:
        return None
    try:
        return ast.parse(text, filename=_display(path, repo_root))
    except SyntaxError as exc:
        errors.append(f"{_display(path, repo_root)}: invalid Python syntax: {exc}")
        return None


def _constant_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _module_function_nodes(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _module_function_names(tree: ast.Module) -> set[str]:
    return set(_module_function_nodes(tree))


def _module_class_nodes(tree: ast.Module) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _enum_members(class_node: ast.ClassDef) -> dict[str, str]:
    members: dict[str, str] = {}
    for stmt in class_node.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            continue
        value = _constant_string(stmt.value)
        if value is not None:
            members[stmt.targets[0].id] = value
    return members


def _full_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _full_name(node.value)
        if prefix is None:
            return None
        return f"{prefix}.{node.attr}"
    return None


def _decorator_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _full_name(node.func)
    return _full_name(node)


def _is_false_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _is_disabling_test_marker_name(name: str | None) -> bool:
    if name is None:
        return False
    normalized = name.lower()
    return normalized.endswith((".skip", ".skipif", ".xfail")) or normalized in {
        "skip",
        "skipif",
        "xfail",
    }


def _node_has_disabling_test_marker(node: ast.AST, aliases: set[str]) -> bool:
    marker_name = _decorator_name(node)
    if _is_disabling_test_marker_name(marker_name) or marker_name in aliases:
        return True
    if isinstance(node, (ast.List, ast.Tuple)):
        return any(_node_has_disabling_test_marker(item, aliases) for item in node.elts)
    return False


def _assigned_names(statement: ast.stmt) -> tuple[str, ...]:
    if isinstance(statement, ast.Assign):
        return tuple(target.id for target in statement.targets if isinstance(target, ast.Name))
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return (statement.target.id,)
    return ()


def _assigned_value(statement: ast.stmt) -> ast.AST | None:
    if isinstance(statement, ast.Assign):
        return statement.value
    if isinstance(statement, ast.AnnAssign):
        return statement.value
    return None


def _iter_scope_statements(statements: list[ast.stmt]) -> Iterator[ast.stmt]:
    for statement in statements:
        yield statement
        if isinstance(statement, ast.If):
            yield from _iter_scope_statements(statement.body)
            yield from _iter_scope_statements(statement.orelse)


def _disabling_marker_aliases(statements: list[ast.stmt]) -> set[str]:
    aliases: set[str] = set()
    changed = True
    while changed:
        changed = False
        for statement in _iter_scope_statements(statements):
            value = _assigned_value(statement)
            if value is None:
                continue
            if not _node_has_disabling_test_marker(value, aliases):
                continue
            for name in _assigned_names(statement):
                if name != "pytestmark" and name not in aliases:
                    aliases.add(name)
                    changed = True
    return aliases


def _has_disabled_test_collection(statements: list[ast.stmt], aliases: set[str]) -> bool:
    for statement in _iter_scope_statements(statements):
        value = _assigned_value(statement)
        names = _assigned_names(statement)
        if value is not None:
            if "__test__" in names and _is_false_constant(value):
                return True
            if "pytestmark" in names and _node_has_disabling_test_marker(value, aliases):
                return True
        if isinstance(statement, ast.Expr) and _module_level_skip_call(statement.value):
            return True
    return False


def _test_function_is_disabled(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    aliases: set[str],
) -> bool:
    return any(
        _node_has_disabling_test_marker(decorator, aliases) for decorator in node.decorator_list
    )


def _module_level_skip_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if _full_name(node.func) != "pytest.skip":
        return False
    return any(
        keyword.arg == "allow_module_level"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in node.keywords
    )


def _class_has_uncollectable_constructor(class_node: ast.ClassDef) -> bool:
    return any(
        isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        and statement.name in {"__init__", "__new__"}
        for statement in class_node.body
    )


def _test_class_is_disabled(class_node: ast.ClassDef, inherited_aliases: set[str]) -> bool:
    aliases = inherited_aliases | _disabling_marker_aliases(class_node.body)
    return (
        any(
            _node_has_disabling_test_marker(decorator, aliases)
            for decorator in class_node.decorator_list
        )
        or _has_disabled_test_collection(class_node.body, aliases)
        or _class_has_uncollectable_constructor(class_node)
    )


def _discoverable_test_function_nodes(
    tree: ast.Module,
    *,
    relative_path: str,
    required_test_functions: set[str],
    errors: list[str],
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    discovered: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    module_aliases = _disabling_marker_aliases(tree.body)
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if statement.name in required_test_functions:
                discovered[statement.name] = statement
            continue
        if not isinstance(statement, ast.ClassDef) or not statement.name.startswith("Test"):
            continue
        class_aliases = module_aliases | _disabling_marker_aliases(statement.body)
        class_disabled = _test_class_is_disabled(statement, module_aliases)
        for item in statement.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name not in required_test_functions:
                continue
            if class_disabled:
                errors.append(
                    f"{relative_path}: required test {item.name} must not live in disabled or uncollectable class"
                )
                continue
            if _test_function_is_disabled(item, class_aliases):
                errors.append(
                    f"{relative_path}: required test {item.name} must not be skipped or xfailed"
                )
                continue
            discovered[item.name] = item
    return discovered


def _attribute_refs(tree: ast.AST) -> set[str]:
    refs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            name = _full_name(node)
            if name is not None:
                refs.add(name)
    return refs


def _keyword_name_refs(tree: ast.AST) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg and isinstance(keyword.value, ast.Name):
                refs.add((keyword.arg, keyword.value.id))
    return refs


def _call_keyword_name_refs(tree: ast.AST) -> set[tuple[str, str, str]]:
    refs: set[tuple[str, str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _full_name(node.func)
        if call_name is None:
            continue
        for keyword in node.keywords:
            if keyword.arg and isinstance(keyword.value, ast.Name):
                refs.add((call_name.split(".")[-1], keyword.arg, keyword.value.id))
    return refs


def _call_keyword_name_refs_in_function(
    tree: ast.Module,
    function_name: str,
) -> set[tuple[str, str, str, str]]:
    function_node = _module_function_nodes(tree).get(function_name)
    if function_node is None:
        return set()
    return {
        (function_name, call_name, keyword, value)
        for call_name, keyword, value in _call_keyword_name_refs(function_node)
    }


def _check_landed_markers(repo_root: Path, errors: list[str]) -> None:
    parsed: dict[str, ast.Module] = {}

    def tree_for(relative_path: str) -> ast.Module | None:
        if relative_path in parsed:
            return parsed[relative_path]
        tree = _parse_python(repo_root / relative_path, repo_root, errors)
        if tree is not None:
            parsed[relative_path] = tree
        return tree

    for relative_path, class_specs in REQUIRED_ENUM_MEMBERS.items():
        tree = tree_for(relative_path)
        if tree is None:
            continue
        classes = _module_class_nodes(tree)
        for class_name, expected_members in class_specs.items():
            class_node = classes.get(class_name)
            if class_node is None:
                errors.append(f"{relative_path}: missing class {class_name} at module scope")
                continue
            members = _enum_members(class_node)
            for member_name, expected_value in expected_members.items():
                actual_value = members.get(member_name)
                if actual_value != expected_value:
                    errors.append(
                        f"{relative_path}: {class_name}.{member_name} expected "
                        f"{expected_value!r}, got {actual_value!r}"
                    )

    for relative_path, required_functions in REQUIRED_FUNCTIONS.items():
        tree = tree_for(relative_path)
        if tree is None:
            continue
        functions = _module_function_names(tree)
        for marker in required_functions:
            function_name = marker.removeprefix("def ").strip()
            if function_name not in functions:
                errors.append(f"{relative_path}: missing module-level function {function_name}")

    for relative_path, expected_attribute_refs in REQUIRED_ATTRIBUTE_REFS.items():
        tree = tree_for(relative_path)
        if tree is None:
            continue
        attribute_refs = _attribute_refs(tree)
        for expected_attribute_ref in expected_attribute_refs:
            if expected_attribute_ref not in attribute_refs:
                errors.append(f"{relative_path}: missing AST reference {expected_attribute_ref}")

    for relative_path, expected_keyword_refs in REQUIRED_KEYWORD_NAME_REFS.items():
        tree = tree_for(relative_path)
        if tree is None:
            continue
        keyword_refs = _keyword_name_refs(tree)
        for expected_keyword_ref in expected_keyword_refs:
            if expected_keyword_ref not in keyword_refs:
                keyword, value = expected_keyword_ref
                errors.append(f"{relative_path}: missing keyword proof {keyword}={value}")

    for relative_path, expected_call_refs in REQUIRED_CALL_KEYWORD_NAME_REFS.items():
        tree = tree_for(relative_path)
        if tree is None:
            continue
        call_refs: set[tuple[str, str, str, str]] = set()
        for expected_call_ref in expected_call_refs:
            function_name, _call_name, _keyword, _value = expected_call_ref
            call_refs.update(_call_keyword_name_refs_in_function(tree, function_name))
            if expected_call_ref not in call_refs:
                function_name, call_name, keyword, value = expected_call_ref
                errors.append(
                    f"{relative_path}: missing call proof {function_name}->{call_name}(..., {keyword}={value})"
                )

    for relative_path, required_test_functions in REQUIRED_TEST_FUNCTIONS.items():
        tree = tree_for(relative_path)
        if tree is None:
            continue
        module_aliases = _disabling_marker_aliases(tree.body)
        if _has_disabled_test_collection(tree.body, module_aliases):
            errors.append(
                f"{relative_path}: required test module must not disable pytest collection"
            )
        test_functions = _discoverable_test_function_nodes(
            tree,
            relative_path=relative_path,
            required_test_functions=required_test_functions,
            errors=errors,
        )
        for expected_function in sorted(required_test_functions):
            function_node = test_functions.get(expected_function)
            if function_node is None:
                errors.append(f"{relative_path}: missing test function {expected_function}")
                continue
            if _test_function_is_disabled(function_node, module_aliases):
                errors.append(
                    f"{relative_path}: required test {expected_function} must not be skipped or xfailed"
                )


def _check_stale_a2_claims(label: str, text: str, errors: list[str]) -> None:
    for unit in _line_units(text):
        if STALE_SECTION_RE.search(unit) and not NEGATION_RE.search(unit):
            errors.append(f"{label}: stale A2 active/pending claim: {unit}")
        elif (
            PR_A2_RE.search(unit) and STALE_A2_WORD_RE.search(unit) and not NEGATION_RE.search(unit)
        ):
            errors.append(f"{label}: stale A2 active/pending claim: {unit}")
    for match in MAPPING_STALE_RE.finditer(text):
        errors.append(f"{label}: stale PR #1415 merge-readiness wording: {match.group(0)}")


def _check_forbidden_expansion_claims(label: str, text: str, errors: list[str]) -> None:
    for clause in _clauses(text, split_soft=True):
        has_surface = FORBIDDEN_SURFACE_RE.search(clause)
        has_action = POSITIVE_ACTION_RE.search(clause)
        if has_surface and has_action and not NEGATION_RE.search(clause):
            errors.append(f"{label}: forbidden runtime/scope expansion claim: {clause}")


def _check_overclaims(label: str, text: str, errors: list[str]) -> None:
    for clause in _clauses(text):
        if OVERCLAIM_RE.search(clause) and not NEGATION_RE.search(clause):
            errors.append(f"{label}: benchmark/scientific overclaim: {clause}")


def _check_local_path_leakage(label: str, text: str, errors: list[str]) -> None:
    for match in LOCAL_PATH_RE.finditer(text):
        errors.append(f"{label}: local path leakage: {match.group(0)}")


def validate_closeout(
    *,
    repo_root: Path = REPO_ROOT,
    ledger: Path | None = None,
    roadmap: Path | None = None,
    mapping: Path | None = None,
    semantic_cache_gate: Path | None = None,
) -> list[str]:
    """Return closeout violations for PR-A2 governance truth."""

    repo_root = repo_root.resolve()
    ledger_path = ledger or repo_root / DEFAULT_LEDGER.relative_to(REPO_ROOT)
    roadmap_path = roadmap or repo_root / DEFAULT_ROADMAP.relative_to(REPO_ROOT)
    mapping_path = mapping or repo_root / DEFAULT_MAPPING.relative_to(REPO_ROOT)
    gate_path = semantic_cache_gate or repo_root / DEFAULT_SEMANTIC_CACHE_GATE.relative_to(
        REPO_ROOT
    )

    errors: list[str] = []
    ledger_text = _read_text(ledger_path, repo_root, errors)
    roadmap_text = _read_text(roadmap_path, repo_root, errors)
    mapping_text = _read_text(mapping_path, repo_root, errors)
    gate_text = _read_text(gate_path, repo_root, errors)

    ledger_slice = _slice(
        ledger_text,
        '<a id="ledger-p1-rag-hardening-followthrough"></a>',
        r"\n<a id=",
        label="A2 ledger entry",
        errors=errors,
    )
    roadmap_slice = _slice(
        roadmap_text,
        "## PR-A2",
        r"\n## PR-A3\b",
        label="A2 roadmap section",
        errors=errors,
    )
    gate_slice = _slice(
        gate_text,
        "Current `main` already contains:",
        r"\n## Rail Boundary\b",
        label="semantic-cache prerequisite section",
        errors=errors,
    )

    _check_gate_markers(gate_text, errors)
    _check_landed_markers(repo_root, errors)

    for label, text in (
        ("A2 ledger entry", ledger_slice),
        ("A2 roadmap section", roadmap_slice),
        ("PR #1415 mapping", mapping_text),
        ("semantic-cache prerequisite section", gate_slice),
    ):
        _require_pr1415_evidence(text, label, errors)
        _check_stale_a2_claims(label, text, errors)
        _check_forbidden_expansion_claims(label, text, errors)
        _check_overclaims(label, text, errors)
        _check_local_path_leakage(label, text, errors)

    if "- [x] P1: RAG hardening follow-through" not in ledger_slice:
        errors.append("A2 ledger entry: parent checkbox must be closed for landed PR #1415")
    if "## Post-Merge Closeout" not in mapping_text:
        errors.append("PR #1415 mapping: missing Post-Merge Closeout section")
    if "## Historical Merge Readiness" not in mapping_text:
        errors.append("PR #1415 mapping: missing Historical Merge Readiness section")

    return errors


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--roadmap", type=Path, default=None)
    parser.add_argument("--mapping", type=Path, default=None)
    parser.add_argument("--semantic-cache-gate", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    errors = validate_closeout(
        repo_root=args.repo_root,
        ledger=args.ledger,
        roadmap=args.roadmap,
        mapping=args.mapping,
        semantic_cache_gate=args.semantic_cache_gate,
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("A2 RAG hardening closeout contract: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
