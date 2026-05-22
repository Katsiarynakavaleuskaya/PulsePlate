#!/usr/bin/env python3
"""Fail-closed guard for PR-A8 recursive speed optimization closeout truth."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterator
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

TITLE = "feat(ai-runtime): add philosophical speed optimization to recursive stack"
PR_1506 = {
    "number": "1506",
    "merged_at": "2026-04-23T20:41:25Z",
    "merge_date": "2026-04-23",
    "merge_commit": "".join(("19fdbd30", "98a6aef7", "80a71e94", "e94980cb", "3d0f61ee")),
    "branch": "codex/ai-recursive-speed-optimization-w1",
}
PR_1578 = {
    "number": "1578",
    "merged_at": "2026-04-29T20:32:42Z",
    "merge_date": "2026-04-29",
    "merge_commit": "".join(("37995a6e", "8d4e9451", "b85e7e62", "84e9bd0c", "d5afff45")),
    "branch": "codex/wave6-a8-recursive-speed-optimization",
}

DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
DEFAULT_PR1506_MAPPING = REPO_ROOT / "docs" / "review" / "PR_1506_FIXED_MAPPING.md"
DEFAULT_PR1578_MAPPING = REPO_ROOT / "docs" / "review" / "PR_1578_FIXED_MAPPING.md"
DEFAULT_SEMANTIC_CACHE_GATE = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
)

REQUIRED_GATE_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

REQUIRED_SYMBOLS = {
    "core/ai/insight_runtime.py": (
        "RecursiveRolloutPolicy",
        "_build_recursive_optimization_hints",
    ),
    "core/rag/contracts.py": ("RecursiveOptimizationHints",),
    "core/rag/orchestration.py": ("recursive_optimization_hints",),
    "core/rag/recursive_retrieval.py": ("_should_short_circuit_from_hints",),
    "app/services/insight_runtime.py": ("recursive_optimization_hints",),
}

RECURSIVE_RETRIEVAL_PATH = "core/rag/recursive_retrieval.py"
RECURSIVE_EARLY_STOP_LITERALS = frozenset(
    {
        "early_stop_aggressive_short_circuit",
        "early_stop_pragmatic_usefulness",
    }
)
RECURSIVE_EARLY_STOP_LITERAL_FUNCTIONS = frozenset(
    {
        "_should_short_circuit_from_hints",
        "_make_optimization_stats",
    }
)

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

NEGATION_RE = re.compile(
    r"\b(no|not|never|does\s+not|do\s+not|must\s+not|cannot|can't|"
    r"out\s+of\s+scope|deferred|remains?\s+closed|remained\s+closed|"
    r"gate[-\s]+closed|without|no\s+default)\b",
    re.I,
)
FORBIDDEN_SURFACE_PATTERN = (
    r"semantic[-\s]?(?:cache|caching)|semanticcache|redis|gpt[-\s]?cache|"
    r"graph[-\s]?rag|context[-\s]?manifest|contextmanifest|"
    r"(?:db|database)\s+persistence|public\s+(?:routes?|endpoints?|api)(?:\s+changes?)?|"
    r"openapi|dtos?|recursive\s+learning|chain[-\s]?of[-\s]?thought|"
    r"tree[-\s]?of[-\s]?thought|default\s+activation|default[-\s]?on|"
    r"production[-\s]?ready|rollout[-\s]?ready"
)

LOCAL_NEGATED_CLAIM_RE = re.compile(
    r"\b(no|not|never|does\s+not|do\s+not|must\s+not|cannot|can't|"
    r"out\s+of\s+scope|deferred|remains?\s+closed|remained\s+closed|"
    r"gate[-\s]+closed|without|no\s+default)\b"
    r"[^,;.()[\]{}]{0,140}"
    rf"\b({FORBIDDEN_SURFACE_PATTERN})\b",
    re.I,
)
BENCHMARK_CLAIM_RE = re.compile(
    r"(?=.*\b(?:latency|quality|reduction|maintained|accuracy)\b)"
    r"(?=.*(?:\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?%|"
    r">=?\s*\d+(?:\.\d+)?%|<=?\s*\d+(?:\.\d+)?%|"
    r"\d+(?:\.\d+)?\s*percent|under\s+\d+(?:\.\d+)?\s*ms)).+",
    re.I,
)
FORBIDDEN_SURFACE_RE = re.compile(rf"\b({FORBIDDEN_SURFACE_PATTERN})\b", re.I)
POSITIVE_ACTION_RE = re.compile(
    r"\b(opens?|opened|opening|enables?|enabled|introduces?|introduced|introducing|"
    r"implements?|implemented|approves?|approved|exposes?|exposed|exposing|"
    r"authorizes?|authorized|permits?|permitted|allows?|allowed|adds?|added|ships?|shipped|"
    r"selects?|selected|activates?|activated|activating|rolls?\s+out|"
    r"uses?|used|using|supports?|supported|supporting|includes?|included|including|"
    r"turns?\s+(?:[A-Za-z0-9_/-]+\s+){0,8}on(?:\s+by\s+default)?|"
    r"wired|wires|"
    r"production[-\s]?ready|rollout[-\s]?ready|default[-\s]?on|"
    r"default\s+activation|active|live)\b",
    re.I,
)
A8_REF_RE = re.compile(r"\b(?:pr[-\s]?a8|a8|pr\s*#?\s*(?:1506|1578)|#(?:1506|1578))\b", re.I)
_PENDING_LOOKAHEAD = (
    r"pending(?!\s+(?:review|approval|merge|verification|audit|validation|closeout))"
)
STALE_A8_RE = re.compile(
    rf"\b(?:pr[-\s]?a8|#1506|#1578)\b.*\b({_PENDING_LOOKAHEAD}(?:[-\s]+active)?|in[-\s]+progress|active(?:\s+implementation\s+lane|-implementation-lane)?|next\s+logical|will\s+implement|implementation[-\s]+lane|open[-\s]+runtime)\b",
    re.I,
)
STALE_A8_REVERSED_RE = re.compile(
    rf"\b({_PENDING_LOOKAHEAD}(?:[-\s]+active)?|in[-\s]+progress|active(?:\s+implementation\s+lane|-implementation-lane)?|next\s+logical|will\s+implement|implementation[-\s]+lane|open[-\s]+runtime)\b.*\b(?:pr[-\s]?a8|#1506|#1578)\b",
    re.I,
)
CONTRAST_SPLIT_RE = re.compile(
    r"\b(?:but|however|though|although|yet|and|or|while|whereas|because|since|as|unless)\b|[;]",
    re.I,
)
COMMA_SPLIT_RE = re.compile(r",\s*")
PHASE_SPLIT_RE = re.compile(r"\s*[:|/]\s*")
DASH_SPLIT_RE = re.compile(r"\s+[-—–]\s+" r"|(?<=[a-zA-Z])[—–](?=[a-zA-Z])")
SYMBOL_SPLIT_RE = re.compile(r"(?:\s+|(?<=\w))(?:[+&]|\band\b)(?:\s+|(?=\w))", re.I)
BRACKETED_FRAGMENT_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]|\{[^}]*\}")


PARAM_ONLY_SYMBOLS = frozenset({"recursive_optimization_hints"})
PARAM_ONLY_PATHS = frozenset(
    {
        "core/rag/orchestration.py",
        "app/services/insight_runtime.py",
    }
)
PARAM_ONLY_ALLOWED_FUNCTIONS = {
    "core/rag/orchestration.py": frozenset({"retrieve_and_validate_rag", "_run_orchestration"}),
    "app/services/insight_runtime.py": frozenset({"_traced_retrieve_and_validate_rag"}),
}


OVERCLAIM_RE = re.compile(
    r"\b(proves?|proved|scientifically\s+validated|validated|guarantees?|"
    r"guaranteed|maintains?|maintained|achieves?|achieved|delivers?|delivered)\b",
    re.I,
)

PROOF_OVERCLAIM_RE = re.compile(
    r"\b(proves?|proved|scientifically\s+validated|validated|guarantees?|"
    r"guaranteed|achieves?|achieved|delivers?|delivered)\b",
    re.I,
)
METRIC_MAINTAINED_RE = re.compile(
    r"\b(?:quality\s+)?maintains?\b[^,;.]{0,20}(?:>=|≥|\d)",
    re.I,
)


def _read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: unable to read: {exc}")
        return ""


def _normalize(text: str) -> str:
    text = re.sub(r"(?<=[a-zA-Z])[\u2013\u2014](?=[a-zA-Z])", " - ", text)
    return text.translate(UNICODE_TRANSLATION)


def _sentences(text: str) -> list[str]:
    normalized = _normalize(text)
    parts: list[str] = []
    for paragraph in re.split(r"\n{2,}", normalized):
        soft_wrapped = re.sub(r"[ \t]*\n[ \t]*", " ", paragraph.strip())
        parts.extend(re.split(r"(?<=[.!?])\s+", soft_wrapped))
    return [part.strip() for part in parts if part.strip()]


def _markdown_list_units(text: str) -> list[str]:
    normalized = _normalize(text)
    units: list[str] = []
    chunks = re.split(r"(?:^|\n)\s*- ", normalized)
    for index, chunk in enumerate(chunks):
        trimmed = chunk.strip()
        if not trimmed:
            continue
        if index > 0:
            trimmed = f"- {trimmed}"
        units.extend(_sentences(trimmed))
    if not units:
        return _sentences(normalized)
    return [unit for unit in units if unit.strip()]


def _eval_text_units(text: str, *, assume_a8_context: bool = False) -> list[str]:
    if assume_a8_context:
        return _markdown_list_units(text)
    return _sentences(text)


def _parent_disqualifies_claims(sentence: str) -> bool:
    """Skip only pure disclaimer sentences; never skip mixed benchmark claims."""
    if BENCHMARK_CLAIM_RE.search(sentence):
        return False
    lowered = sentence.lower()
    if "гипотез" in lowered and (
        "benchmark validation" in lowered or "валидац" in lowered or "валидацией" in lowered
    ):
        return True
    if "hypotheses only" in lowered and "benchmark validation" in lowered:
        return True
    if "hypothesis" in lowered and "not shipped performance claims" in lowered:
        return True
    return False


def _bracket_fragments(text: str) -> list[str]:
    fragments: list[str] = []
    last_end = 0
    for match in BRACKETED_FRAGMENT_RE.finditer(text):
        outer = text[last_end : match.start()].strip()
        if outer:
            fragments.append(outer)
        inner = match.group(0)[1:-1].strip()
        if inner:
            fragments.append(inner)
        last_end = match.end()
    tail = text[last_end:].strip()
    if tail:
        fragments.append(tail)
    stripped = text.strip()
    return fragments if fragments else ([stripped] if stripped else [])


def _iter_eval_subclauses(clause: str) -> list[str]:
    subclauses: list[str] = []
    for contrast_part in CONTRAST_SPLIT_RE.split(clause):
        for comma_part in COMMA_SPLIT_RE.split(contrast_part):
            for dash_part in DASH_SPLIT_RE.split(comma_part):
                for symbol_part in SYMBOL_SPLIT_RE.split(dash_part):
                    for bracket_part in _bracket_fragments(symbol_part):
                        for phase_part in PHASE_SPLIT_RE.split(bracket_part):
                            trimmed = phase_part.strip()
                            if trimmed:
                                subclauses.append(trimmed)
    return subclauses


def _claim_is_locally_negated(text: str) -> bool:
    normalized = _normalize(text)
    for match in LOCAL_NEGATED_CLAIM_RE.finditer(normalized):
        neg_text = match.group(1)
        if neg_text.lower() == "not":
            after = normalized[match.end(1) : match.end(1) + 10]
            if re.match(r"\s+only\b", after, re.I):
                continue
        return True
    return False


def _surface_claim_is_negated(text: str) -> bool:
    normalized = _normalize(text)
    if _claim_is_locally_negated(normalized):
        return True
    if (
        re.search(
            r"\b(" + FORBIDDEN_SURFACE_PATTERN + r")\b[^,;\.]{0,100}"
            r"\b(?:is|are|was|were|remains?|remained)?\s*"
            r"(?:not|never)\s+"
            r"(?:active|live|enabled|opened|allowed|approved|selected|"
            r"production[-\s]?ready|rollout[-\s]?ready)\b",
            normalized,
            re.I,
        )
        is not None
    ):
        return True
    return (
        re.search(
            r"\b(" + FORBIDDEN_SURFACE_PATTERN + r")\b[^,;\.]{0,140}"
            r"\b(?:remain|remains|remained)\s+(?:out\s+of\s+scope|closed)\b",
            normalized,
            re.I,
        )
        is not None
    )


STALE_STATUS_RE = re.compile(
    rf"\b(?:{_PENDING_LOOKAHEAD}(?:[-\s]+active)?|in[-\s]+progress|active(?:\s+implementation\s+lane|-implementation-lane)?|next\s+logical|will\s+implement|implementation[-\s]+lane|open[-\s]+runtime)\b",
    re.I,
)


def _stale_status_is_negated(clause: str) -> bool:
    normalized = _normalize(clause)
    match = re.search(
        rf"\b((?:not|no|never|does\s+not|do\s+not|must\s+not|cannot|can't))\b"
        rf"[^,;.]{{0,80}}\b(?:{_PENDING_LOOKAHEAD}(?:[-\s]+active)?|in[-\s]+progress|active(?:\s+implementation\s+lane|-implementation-lane)?|next\s+logical|will\s+implement|implementation[-\s]+lane|open[-\s]+runtime)\b",
        normalized,
        re.I,
    )
    if match is None:
        return False
    neg_text = match.group(1)
    if neg_text.lower() == "not":
        after = normalized[match.end(1) : match.end(1) + 10]
        if re.match(r"\s+only\b", after, re.I):
            return False
    return True


def _subclause_has_actionable_forbidden(
    sub_clause: str, *, sentence_has_a8: bool, sentence_has_forbidden_surface: bool = False
) -> bool:
    normalized = _normalize(sub_clause)
    has_a8_ref = A8_REF_RE.search(normalized) is not None or sentence_has_a8
    if not has_a8_ref:
        return False
    has_local_surface = FORBIDDEN_SURFACE_RE.search(normalized) is not None
    if not (has_local_surface or sentence_has_forbidden_surface):
        return False
    if has_local_surface and _surface_claim_is_negated(normalized):
        return False
    if POSITIVE_ACTION_RE.search(normalized):
        return True
    if (
        (has_local_surface or sentence_has_forbidden_surface)
        and re.search(r"\bsemantic[-\s]?cache|semanticcache\b", normalized, re.I)
        and re.search(
            r"\b(?:active|live|enabled|opened|allowed|approved|selected|"
            r"production[-\s]?ready|rollout[-\s]?ready)\b",
            normalized,
            re.I,
        )
    ):
        return True
    if re.search(r"\b(redis|gpt[-\s]?cache)\b", normalized, re.I) and re.search(
        r"\b(approved|selected|production[-\s]?ready|rollout[-\s]?ready|enabled)\b",
        normalized,
        re.I,
    ):
        return True
    return False


def _default_repo_path(repo_root: Path, default_path: Path) -> Path:
    return repo_root / default_path.relative_to(REPO_ROOT)


def _find_pr_a8_section(roadmap_text: str) -> str:
    normalized = _normalize(roadmap_text)
    match = re.search(r"^## PR-A8\b.*?(?=^---\s*$|^## PR-A9\b|\Z)", normalized, re.M | re.S)
    return match.group(0) if match else ""


def _find_anchor_section(text: str, anchor: str) -> str:
    normalized = _normalize(text)
    match = re.search(
        rf'^<a id="{re.escape(anchor)}"></a>.*?(?=^<a id="|\Z)',
        normalized,
        re.M | re.S,
    )
    return match.group(0) if match else ""


def _require_contains(text: str, needle: str, label: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(f"missing {label}: {needle}")


def _validate_pr_evidence(
    *,
    active_text: str,
    mapping_text: str,
    evidence: dict[str, str],
    errors: list[str],
) -> None:
    number = evidence["number"]
    _require_contains(active_text, f"#{number}", f"PR #{number} active docs evidence", errors)
    for needle, label in (
        (f"#{number}", f"PR #{number} number"),
        (TITLE, f"PR #{number} title"),
    ):
        _require_contains(mapping_text, needle, label, errors)
    for needle, label in (
        (evidence["merged_at"], "merge timestamp"),
        (evidence["merge_date"], "merge date"),
        (evidence["merge_commit"], "merge commit"),
        (evidence["branch"], "original branch"),
    ):
        _require_contains(mapping_text, needle, f"PR #{number} {label}", errors)
        _require_contains(active_text, needle, f"PR #{number} active docs {label}", errors)


def _validate_required_symbols(repo_root: Path, errors: list[str]) -> None:
    for relpath, symbols in REQUIRED_SYMBOLS.items():
        path = repo_root / relpath
        text = _read_text(path, errors)
        discovered_symbols = _python_ast_symbols(text, relpath, errors)
        for symbol in symbols:
            if symbol not in discovered_symbols:
                errors.append(f"missing {relpath} landed symbol declaration: {symbol}")


def _function_param_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    params: set[str] = set()
    args = node.args
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        params.add(arg.arg)
    if args.vararg is not None:
        params.add(args.vararg.arg)
    if args.kwarg is not None:
        params.add(args.kwarg.arg)
    return params


def _assign_target_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_assign_target_names(element))
        return names
    return set()


def _collect_param_only_call_keywords(node: ast.Call) -> set[str]:
    return {keyword.arg for keyword in node.keywords if keyword.arg in PARAM_ONLY_SYMBOLS}


def _iter_calls_in_expr(expr: ast.expr | None) -> list[ast.Call]:
    if expr is None:
        return []
    return [node for node in ast.walk(expr) if isinstance(node, ast.Call)]


def _collect_param_only_wiring(statements: list[ast.stmt]) -> set[str]:
    found: set[str] = set()
    for stmt in statements:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                found.update(_assign_target_names(target) & PARAM_ONLY_SYMBOLS)
            for call in _iter_calls_in_expr(stmt.value):
                found.update(_collect_param_only_call_keywords(call))
        elif isinstance(stmt, ast.AnnAssign) and stmt.target is not None:
            found.update(_assign_target_names(stmt.target) & PARAM_ONLY_SYMBOLS)
            for call in _iter_calls_in_expr(stmt.value):
                found.update(_collect_param_only_call_keywords(call))
        elif isinstance(stmt, ast.Return):
            for call in _iter_calls_in_expr(stmt.value):
                found.update(_collect_param_only_call_keywords(call))
        elif isinstance(stmt, ast.Expr):
            for call in _iter_calls_in_expr(stmt.value):
                found.update(_collect_param_only_call_keywords(call))
        elif isinstance(stmt, ast.If):
            if _constant_is_false(stmt.test):
                found.update(_collect_param_only_wiring(stmt.orelse))
                continue
            found.update(_collect_param_only_wiring(stmt.body))
            found.update(_collect_param_only_wiring(stmt.orelse))
        elif isinstance(stmt, ast.With):
            found.update(_collect_param_only_wiring(stmt.body))
        elif isinstance(stmt, ast.Try):
            found.update(_collect_param_only_wiring(stmt.body))
            for handler in stmt.handlers:
                found.update(_collect_param_only_wiring(handler.body))
            found.update(_collect_param_only_wiring(stmt.orelse))
            found.update(_collect_param_only_wiring(stmt.finalbody))
        elif isinstance(stmt, (ast.For, ast.While)):
            found.update(_collect_param_only_wiring(stmt.body))
            found.update(_collect_param_only_wiring(stmt.orelse))
        elif isinstance(stmt, ast.Match):
            for case in stmt.cases:
                found.update(_collect_param_only_wiring(case.body))
    return found


def _python_ast_symbols(text: str, relpath: str, errors: list[str]) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        errors.append(f"{relpath}: unable to parse Python for landed symbols: {exc}")
        return set()

    symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            symbols.add(node.name)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbols.add(node.name)
            if relpath in PARAM_ONLY_PATHS:
                allowed_functions = PARAM_ONLY_ALLOWED_FUNCTIONS.get(relpath, frozenset())
                if node.name in allowed_functions:
                    for param in _function_param_names(node):
                        if param in PARAM_ONLY_SYMBOLS:
                            symbols.add(param)
                    symbols.update(_collect_param_only_wiring(node.body))
        elif isinstance(node, ast.Assign):
            if not (isinstance(node.value, ast.Constant) and node.value.value is None):
                for target in node.targets:
                    if isinstance(target, (ast.Name, ast.Tuple, ast.List)):
                        symbols.update(_assign_target_names(target))
        elif isinstance(node, ast.AnnAssign):
            if node.target is not None:
                if not (isinstance(node.value, ast.Constant) and node.value.value is None):
                    if isinstance(node.target, (ast.Name, ast.Tuple, ast.List)):
                        symbols.update(_assign_target_names(node.target))
        elif hasattr(ast, "TypeAlias") and isinstance(node, ast.TypeAlias):
            if isinstance(node.name, ast.Name):
                symbols.add(node.name.id)
    return symbols


def _walk_executable_nodes(node: ast.AST) -> Iterator[ast.AST]:
    if isinstance(node, ast.If):
        if _constant_is_false(node.test):
            for stmt in node.orelse:
                yield from _walk_executable_nodes(stmt)
            return
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.arg):
            continue
        if isinstance(child, ast.AnnAssign):
            yield child.target
            if child.value is not None:
                yield from _walk_executable_nodes(child.value)
            continue
        yield child
        yield from _walk_executable_nodes(child)


def _collect_string_literals_from_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    literals: set[str] = set()
    start_index = 0
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        start_index = 1
    for stmt in node.body[start_index:]:
        for child in _walk_executable_nodes(stmt):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                literals.add(child.value)
    return literals


def _constant_is_false(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value in (False, 0, "", None)


def _validate_recursive_retrieval_early_stop_literals(repo_root: Path, errors: list[str]) -> None:
    relpath = RECURSIVE_RETRIEVAL_PATH
    path = repo_root / relpath
    text = _read_text(path, errors)
    if not text:
        return
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        errors.append(f"{relpath}: unable to parse Python for early-stop literals: {exc}")
        return

    module_level_spoof: set[str] = set()
    function_literals: dict[str, set[str]] = {}

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name in RECURSIVE_EARLY_STOP_LITERAL_FUNCTIONS:
                function_literals[node.name] = _collect_string_literals_from_function(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                module_level_spoof.update(
                    _assign_target_names(target) & RECURSIVE_EARLY_STOP_LITERALS
                )
        elif isinstance(node, ast.AnnAssign) and node.target is not None:
            module_level_spoof.update(
                _assign_target_names(node.target) & RECURSIVE_EARLY_STOP_LITERALS
            )

    for spoof in sorted(module_level_spoof):
        errors.append(
            f"{relpath}: module-level assign for early-stop literal symbol is forbidden: {spoof}"
        )

    all_function_literals: set[str] = set()
    for func_name in sorted(RECURSIVE_EARLY_STOP_LITERAL_FUNCTIONS):
        if func_name not in function_literals:
            errors.append(f"{relpath}: missing required early-stop literal function: {func_name}")
            continue
        all_function_literals.update(function_literals[func_name])

    for literal in sorted(RECURSIVE_EARLY_STOP_LITERALS):
        if literal not in all_function_literals:
            errors.append(
                f"{relpath}: missing early-stop string literal in whitelisted functions: {literal}"
            )


def _validate_semantic_cache_gate(gate_text: str, errors: list[str]) -> None:
    for marker, expected in REQUIRED_GATE_MARKERS.items():
        pattern = re.compile(rf"{re.escape(marker)}:\s*([A-Za-z0-9_-]+)")
        matches = pattern.findall(gate_text)
        if not matches:
            errors.append(f"missing semantic-cache marker: {marker}")
            continue
        normalized_values = {value.lower() for value in matches}
        if len(normalized_values) > 1:
            errors.append(
                f"conflicting semantic-cache marker values for {marker}: "
                f"{', '.join(sorted(normalized_values))}"
            )
            continue
        actual = next(iter(normalized_values))
        if actual != expected:
            errors.append(f"{marker} expected {expected!r}, got {actual!r}")


def _validate_parent_checkbox(ledger_text: str, errors: list[str]) -> None:
    if not re.search(r"- \[ \] P1: Recursive methods for LLM/RAG/AI assistant", ledger_text):
        errors.append("parent P1 checkbox is closed or missing for recursive methods")


def _validate_roadmap_section(roadmap_text: str, errors: list[str]) -> None:
    section = _find_pr_a8_section(roadmap_text)
    if not section:
        errors.append("missing PR-A8 roadmap section")
        return
    for heading in (
        "#### Current status",
        "#### Landed and hardened scope",
        "#### Benchmark boundary",
        "#### Out of scope",
    ):
        if heading not in section:
            errors.append(f"PR-A8 roadmap section missing heading: {heading}")
    if "#### In scope" in section:
        errors.append("PR-A8 roadmap section still uses implementation in-scope wording")
    _validate_stale_a8_wording(section, errors, assume_a8_context=True)


def _validate_stale_a8_wording(
    active_text: str, errors: list[str], *, assume_a8_context: bool = False
) -> None:
    for sentence in _eval_text_units(active_text, assume_a8_context=assume_a8_context):
        sentence_has_a8 = assume_a8_context or A8_REF_RE.search(sentence) is not None
        for clause in _iter_eval_subclauses(sentence):
            clause_lower = clause.strip().lower()
            contextual_clause = clause
            if sentence_has_a8 and not A8_REF_RE.search(clause):
                if not clause_lower.startswith(("not ", "no ", "never ", "nor ")):
                    contextual_clause = f"PR-A8 {clause}"
            if _stale_status_is_negated(contextual_clause):
                continue
            if (
                STALE_A8_RE.search(contextual_clause)
                or STALE_A8_REVERSED_RE.search(contextual_clause)
                or (assume_a8_context and STALE_STATUS_RE.search(contextual_clause))
            ):
                errors.append(f"stale PR-A8 active/pending wording: {sentence}")
                break


def _validate_mapping_closeout(mapping_text: str, number: str, errors: list[str]) -> None:
    if "## Post-Merge Closeout" not in mapping_text:
        errors.append(f"PR #{number} mapping missing Post-Merge Closeout section")
    if "historical evidence only" not in mapping_text.lower():
        errors.append(f"PR #{number} mapping must mark old readiness checklist as historical")


def _validate_forbidden_claims(
    active_text: str, errors: list[str], *, assume_a8_context: bool = False
) -> None:
    for sentence in _eval_text_units(active_text, assume_a8_context=assume_a8_context):
        sentence_has_a8 = assume_a8_context or A8_REF_RE.search(sentence) is not None
        sentence_has_forbidden_surface = FORBIDDEN_SURFACE_RE.search(sentence) is not None
        for sub_clause in _iter_eval_subclauses(sentence):
            if not _subclause_has_actionable_forbidden(
                sub_clause,
                sentence_has_a8=sentence_has_a8,
                sentence_has_forbidden_surface=sentence_has_forbidden_surface,
            ):
                continue
            normalized = _normalize(sub_clause)
            if POSITIVE_ACTION_RE.search(normalized):
                errors.append(f"forbidden PR-A8 runtime expansion claim: {sentence}")
                break
            if re.search(r"\bsemantic[-\s]?cache|semanticcache\b", normalized, re.I) and re.search(
                r"\b(?:active|live|enabled|opened|allowed|approved|selected|"
                r"production[-\s]?ready|rollout[-\s]?ready)\b",
                normalized,
                re.I,
            ):
                errors.append(f"semantic cache direct activation claim: {sentence}")
                break
            if re.search(r"\b(redis|gpt[-\s]?cache)\b", normalized, re.I) and re.search(
                r"\b(approved|selected|production[-\s]?ready|rollout[-\s]?ready|enabled)\b",
                normalized,
                re.I,
            ):
                errors.append(f"backend rollout approval claim: {sentence}")
                break


def _validate_benchmark_claims(
    active_text: str, errors: list[str], *, assume_a8_context: bool = False
) -> None:
    for sentence in _eval_text_units(active_text, assume_a8_context=assume_a8_context):
        if _parent_disqualifies_claims(sentence):
            continue
        if not assume_a8_context and A8_REF_RE.search(sentence) is None:
            continue
        if not BENCHMARK_CLAIM_RE.search(sentence):
            continue
        if _benchmark_claim_is_qualified(sentence) and not _has_proof_style_overclaim(sentence):
            continue
        subclauses = _iter_eval_subclauses(sentence)
        claim_clauses = [clause for clause in subclauses if BENCHMARK_CLAIM_RE.search(clause)]
        if not claim_clauses and subclauses:
            claim_clauses = subclauses
        elif not claim_clauses:
            stripped = sentence.strip()
            if stripped:
                claim_clauses = [stripped]
        if any(
            _benchmark_clause_is_overclaim(clause, assume_a8_context=assume_a8_context)
            for clause in claim_clauses
        ):
            errors.append(f"unvalidated benchmark claim: {sentence}")
            continue
        if not all(_benchmark_claim_is_qualified(clause) for clause in claim_clauses):
            errors.append(f"unvalidated benchmark claim: {sentence}")


def _has_proof_style_overclaim(text: str) -> bool:
    normalized = _normalize(text)
    if METRIC_MAINTAINED_RE.search(normalized):
        return False
    return any(
        not _overclaim_match_is_negated(normalized, match)
        for match in PROOF_OVERCLAIM_RE.finditer(normalized)
    )


def _benchmark_claim_is_qualified(text: str) -> bool:
    if _benchmark_clause_is_negated_disclaimer(text):
        return True
    lowered = text.lower()
    has_hypothesis = (
        "hypothesis target" in lowered
        or "hypothesized impact" in lowered
        or "hypothesis" in lowered
        or "гипотез" in lowered
    )
    has_validation = (
        "requires benchmark validation" in lowered
        or "benchmark validation" in lowered
        or "benchmark-validated" in lowered
        or "benchmark hypotheses" in lowered
        or "валидац" in lowered
        or "валидацией" in lowered
    )
    return has_hypothesis and has_validation


def _benchmark_clause_is_overclaim(text: str, *, assume_a8_context: bool = False) -> bool:
    if _benchmark_claim_is_qualified(text):
        return False
    if not _has_unnegated_overclaim(text):
        return False
    if assume_a8_context or A8_REF_RE.search(text):
        return True
    return not _benchmark_claim_is_qualified(text)


def _benchmark_clause_is_negated_disclaimer(text: str) -> bool:
    return (
        A8_REF_RE.search(text) is not None
        and _has_negated_overclaim(text)
        and not _has_unnegated_overclaim(text)
    )


def _has_negated_overclaim(text: str) -> bool:
    normalized = _normalize(text)
    return any(
        _overclaim_match_is_negated(normalized, match)
        for match in OVERCLAIM_RE.finditer(normalized)
    )


def _has_unnegated_overclaim(text: str) -> bool:
    normalized = _normalize(text)
    return any(
        not _overclaim_match_is_negated(normalized, match)
        for match in OVERCLAIM_RE.finditer(normalized)
    )


def _overclaim_match_is_negated(text: str, match: re.Match[str]) -> bool:
    verb = match.group(0)
    immediate_prefix = text[max(0, match.start() - 80) : match.start()]
    if re.search(r"\bnot\s+only\b\s*$", immediate_prefix, re.I):
        return False
    scoped = f"{immediate_prefix}{verb}"
    neg_match = re.search(
        rf"\b((?:does\s+not|do\s+not|not|never|cannot|can't|doesn't))\s+"
        rf"(?:[\w-]+\s+){{0,4}}{re.escape(verb)}\b",
        scoped,
        re.I,
    )
    if neg_match is None:
        return False
    between = scoped[neg_match.end(1) : neg_match.start() + len(neg_match.group(0)) - len(verb)]
    if re.search(
        r"\b(because|unless|while|although|though|but|yet|whereas|however)\b|[,;]",
        between,
        re.I,
    ):
        return False
    return True


def validate_closeout(
    *,
    repo_root: Path = REPO_ROOT,
    ledger_path: Path | None = None,
    roadmap_path: Path | None = None,
    mapping1506_path: Path | None = None,
    mapping1578_path: Path | None = None,
    semantic_cache_gate_path: Path | None = None,
) -> list[str]:
    """Return closeout contract errors; empty means pass."""

    errors: list[str] = []
    ledger = _read_text(ledger_path or _default_repo_path(repo_root, DEFAULT_LEDGER), errors)
    roadmap = _read_text(roadmap_path or _default_repo_path(repo_root, DEFAULT_ROADMAP), errors)
    mapping1506 = _read_text(
        mapping1506_path or _default_repo_path(repo_root, DEFAULT_PR1506_MAPPING), errors
    )
    mapping1578 = _read_text(
        mapping1578_path or _default_repo_path(repo_root, DEFAULT_PR1578_MAPPING), errors
    )
    gate = _read_text(
        semantic_cache_gate_path or _default_repo_path(repo_root, DEFAULT_SEMANTIC_CACHE_GATE),
        errors,
    )

    normalized_ledger = _normalize(ledger)
    normalized_roadmap = _normalize(roadmap)
    normalized_mapping1506 = _normalize(mapping1506)
    normalized_mapping1578 = _normalize(mapping1578)
    active_docs = "\n".join((normalized_ledger, normalized_roadmap))
    roadmap_a8_section = _find_pr_a8_section(normalized_roadmap)
    stale_scan_text = "\n".join(
        (
            normalized_roadmap,
            normalized_ledger,
            normalized_mapping1506,
            normalized_mapping1578,
        )
    )
    claim_scan_text = "\n".join(
        (normalized_roadmap, normalized_ledger, normalized_mapping1506, normalized_mapping1578)
    )

    _validate_pr_evidence(
        active_text=active_docs,
        mapping_text=normalized_mapping1506,
        evidence=PR_1506,
        errors=errors,
    )
    _validate_pr_evidence(
        active_text=active_docs,
        mapping_text=normalized_mapping1578,
        evidence=PR_1578,
        errors=errors,
    )
    _validate_required_symbols(repo_root, errors)
    _validate_recursive_retrieval_early_stop_literals(repo_root, errors)
    _validate_semantic_cache_gate(gate, errors)
    _validate_parent_checkbox(normalized_ledger, errors)
    _validate_roadmap_section(normalized_roadmap, errors)
    _validate_stale_a8_wording(stale_scan_text, errors)
    _validate_mapping_closeout(normalized_mapping1506, "1506", errors)
    _validate_mapping_closeout(normalized_mapping1578, "1578", errors)
    ledger_a8_section = _find_anchor_section(normalized_ledger, "ledger-p1-recursive-methods")
    if not ledger_a8_section:
        errors.append("missing ledger anchor for PR-A8 recursive methods")
    _validate_forbidden_claims(claim_scan_text, errors)
    _validate_forbidden_claims(roadmap_a8_section, errors, assume_a8_context=True)
    if ledger_a8_section:
        _validate_forbidden_claims(ledger_a8_section, errors, assume_a8_context=True)
        _validate_benchmark_claims(ledger_a8_section, errors, assume_a8_context=True)
        _validate_stale_a8_wording(ledger_a8_section, errors, assume_a8_context=True)
    _validate_benchmark_claims(claim_scan_text, errors)
    _validate_benchmark_claims(roadmap_a8_section, errors, assume_a8_context=True)

    return errors


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--roadmap", type=Path, default=None)
    parser.add_argument("--mapping-1506", type=Path, default=None)
    parser.add_argument("--mapping-1578", type=Path, default=None)
    parser.add_argument("--semantic-cache-gate", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    errors = validate_closeout(
        repo_root=args.repo_root,
        ledger_path=args.ledger,
        roadmap_path=args.roadmap,
        mapping1506_path=args.mapping_1506,
        mapping1578_path=args.mapping_1578,
        semantic_cache_gate_path=args.semantic_cache_gate,
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("OK: PR-A8 recursive speed optimization closeout remains reconciled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
