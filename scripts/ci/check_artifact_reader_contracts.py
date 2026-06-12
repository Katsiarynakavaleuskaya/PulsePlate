#!/usr/bin/env python3
"""Fail-closed guard for local artifact-reader boundaries."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_BOUNDARY_DOC = "docs/architecture/ARTIFACT_VALIDATION_BOUNDARY.md"
RUNTIME_SCAN_TARGETS: tuple[str, ...] = ("legacy_app.py", "app", "core", "providers")
FORBIDDEN_ARTIFACT_PREFIXES: tuple[tuple[str, str], ...] = (
    ("artifacts", "agent_runs"),
    ("artifacts", "orchestration"),
    ("artifacts", "security_lab"),
)
READ_METHODS = frozenset(
    {
        "exists",
        "glob",
        "is_dir",
        "is_file",
        "iterdir",
        "lstat",
        "read_bytes",
        "read_text",
        "rglob",
        "stat",
    }
)
OPEN_METHODS = frozenset({"open"})
OS_ENUMERATION_METHODS = frozenset({"listdir", "scandir", "walk"})
OS_PATH_CHECK_METHODS = frozenset({"exists", "isdir", "isfile", "islink", "lexists"})
GLOB_METHODS = frozenset({"glob", "iglob"})

REQUIRED_DOC_MARKERS: Mapping[str, str] = {
    "ARTIFACT_BOUNDARY_STATUS": "accepted_guardrail",
    "ARTIFACT_BOUNDARY_RUNTIME_READS_ALLOWED": "false",
    "ARTIFACT_BOUNDARY_RAW_PUBLICATION_ALLOWED": "false",
    "ARTIFACT_BOUNDARY_MISSING_OR_MALFORMED": "fail_closed",
    "ARTIFACT_BOUNDARY_SEMANTIC_CACHE_SERVING": "false",
}
REQUIRED_DOC_TOKENS = (
    "git_sha",
    "source_fingerprint",
    "policy_version",
    "sanitized summary",
    "legacy adapters",
    "artifacts/orchestration/",
    "artifacts/agent_runs/",
    "artifacts/security_lab/",
)
MARKER_RE = re.compile(r"<!--\s*([A-Z0-9_]+):\s*(.*?)\s*-->")


@dataclass(frozen=True, order=True)
class ArtifactReadFinding:
    """One forbidden local artifact read or enumeration."""

    path: str
    line: int
    operation: str
    artifact_root: str

    def display(self) -> str:
        return f"{self.path}:{self.line}: {self.operation} reads local {self.artifact_root}"


def _collapse_path_parts(raw_parts: Sequence[str]) -> tuple[str, ...]:
    parts: list[str] = []
    for part in raw_parts:
        if not part or part == ".":
            continue
        if part == "..":
            if parts and parts[-1] != "..":
                parts.pop()
            else:
                parts.append(part)
            continue
        parts.append(part)
    return tuple(parts)


def _normalize_path_parts(value: str) -> tuple[str, ...]:
    normalized = value.replace("\\", "/")
    return _collapse_path_parts(normalized.split("/"))


def _forbidden_root(parts: tuple[str, ...]) -> str | None:
    lowered = tuple(part.casefold() for part in parts)
    if len(lowered) < 2:
        return None
    for first, second in FORBIDDEN_ARTIFACT_PREFIXES:
        if lowered[0] == first and lowered[1] == second:
            return f"{first}/{second}"
    return None


def _extend_literal_path_parts_until_dynamic(
    args: Sequence[ast.AST],
    names: Mapping[str, tuple[str, ...]],
    path_constructors: frozenset[str],
    path_modules: frozenset[str],
    os_modules: frozenset[str],
    os_path_modules: frozenset[str],
    *,
    initial_parts: Sequence[str] = (),
) -> tuple[str, ...] | None:
    parts = list(_collapse_path_parts(initial_parts))
    for arg in args:
        arg_parts = _literal_path_parts(
            arg,
            names,
            path_constructors,
            path_modules,
            os_modules,
            os_path_modules,
        )
        if arg_parts is None:
            return tuple(parts) if _forbidden_root(tuple(parts)) else None
        parts.extend(arg_parts)
        parts = list(_collapse_path_parts(parts))
    return tuple(parts)


def _literal_path_parts(
    node: ast.AST,
    names: Mapping[str, tuple[str, ...]],
    path_constructors: frozenset[str] = frozenset({"Path"}),
    path_modules: frozenset[str] = frozenset({"pathlib"}),
    os_modules: frozenset[str] = frozenset({"os"}),
    os_path_modules: frozenset[str] = frozenset(),
) -> tuple[str, ...] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _normalize_path_parts(node.value)
    if isinstance(node, ast.JoinedStr):
        literal_parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                literal_parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                literal_parts.append("<dynamic>")
            else:
                return None
        return _normalize_path_parts("".join(literal_parts))
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Div)):
        left = _literal_path_parts(
            node.left,
            names,
            path_constructors,
            path_modules,
            os_modules,
            os_path_modules,
        )
        right = _literal_path_parts(
            node.right,
            names,
            path_constructors,
            path_modules,
            os_modules,
            os_path_modules,
        )
        if left is not None and right is not None:
            return _collapse_path_parts((*left, *right))
        if left is not None and _forbidden_root(left):
            return left
    if isinstance(node, ast.Call):
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "cwd"
            and isinstance(func.value, ast.Name)
            and func.value.id in path_constructors
        ):
            return ()
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "cwd"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "Path"
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id in path_modules
        ):
            return ()
        if isinstance(func, ast.Name) and func.id in path_constructors and node.args:
            return _extend_literal_path_parts_until_dynamic(
                node.args,
                names,
                path_constructors,
                path_modules,
                os_modules,
                os_path_modules,
            )
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "Path"
            and isinstance(func.value, ast.Name)
            and func.value.id in path_modules
            and node.args
        ):
            return _extend_literal_path_parts_until_dynamic(
                node.args,
                names,
                path_constructors,
                path_modules,
                os_modules,
                os_path_modules,
            )
        if isinstance(func, ast.Attribute) and func.attr == "joinpath":
            base = _literal_path_parts(
                func.value,
                names,
                path_constructors,
                path_modules,
                os_modules,
                os_path_modules,
            )
            if base is None:
                return None
            return _extend_literal_path_parts_until_dynamic(
                node.args,
                names,
                path_constructors,
                path_modules,
                os_modules,
                os_path_modules,
                initial_parts=base,
            )
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "join"
            and (
                (
                    isinstance(func.value, ast.Attribute)
                    and func.value.attr == "path"
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id in os_modules
                )
                or (isinstance(func.value, ast.Name) and func.value.id in os_path_modules)
            )
        ):
            return _extend_literal_path_parts_until_dynamic(
                node.args,
                names,
                path_constructors,
                path_modules,
                os_modules,
                os_path_modules,
            )
    return None


def _call_arg(call: ast.Call, index: int, keyword_names: tuple[str, ...]) -> ast.AST | None:
    if len(call.args) > index:
        return call.args[index]
    for keyword in call.keywords:
        if keyword.arg in keyword_names:
            return keyword.value
    return None


def _mode_from_call(call: ast.Call, *, path_method: bool = False) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            value = keyword.value.value
            return value if isinstance(value, str) else None
    if (
        path_method
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "open"
        and call.args
        and isinstance(call.args[0], ast.Constant)
    ):
        value = call.args[0].value
        return value if isinstance(value, str) else None
    if (
        isinstance(call.func, ast.Name)
        and call.func.id == "open"
        and len(call.args) >= 2
        and isinstance(call.args[1], ast.Constant)
    ):
        value = call.args[1].value
        return value if isinstance(value, str) else None
    return None


def _mode_reads(mode: str | None) -> bool:
    if mode is None:
        return True
    stripped = mode.strip()
    if not stripped:
        return True
    if "+" in stripped:
        return True
    return stripped[0] not in {"a", "w", "x"}


class ArtifactReadVisitor(ast.NodeVisitor):
    """AST visitor that flags static reads from local governance artifact roots."""

    def __init__(self, *, rel_path: str) -> None:
        self.rel_path = rel_path
        self.builtins_modules: set[str] = {"builtins"}
        self.name_paths: dict[str, tuple[str, ...]] = {}
        self.glob_functions: dict[str, str] = {}
        self.glob_modules: set[str] = {"glob"}
        self.io_modules: set[str] = {"io"}
        self.open_functions: dict[str, str] = {}
        self.os_enum_functions: dict[str, str] = {}
        self.os_modules: set[str] = {"os"}
        self.os_path_functions: dict[str, str] = {}
        self.os_path_modules: set[str] = set()
        self.path_constructors: set[str] = {"Path"}
        self.path_modules: set[str] = {"pathlib"}
        self.findings: list[ArtifactReadFinding] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "builtins":
                self.builtins_modules.add(alias.asname or "builtins")
            if alias.name == "glob":
                self.glob_modules.add(alias.asname or "glob")
            if alias.name == "io":
                self.io_modules.add(alias.asname or "io")
            if alias.name == "os":
                self.os_modules.add(alias.asname or "os")
            if alias.name == "os.path":
                self.os_path_modules.add(alias.asname or "path")
            if alias.name == "pathlib":
                self.path_modules.add(alias.asname or "pathlib")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "glob":
            for alias in node.names:
                if alias.name in GLOB_METHODS:
                    self.glob_functions[alias.asname or alias.name] = alias.name
        if node.module == "builtins":
            for alias in node.names:
                if alias.name == "open":
                    self.open_functions[alias.asname or alias.name] = "builtins.open"
        if node.module == "io":
            for alias in node.names:
                if alias.name == "open":
                    self.open_functions[alias.asname or alias.name] = "io.open"
        if node.module == "os":
            for alias in node.names:
                if alias.name in OS_ENUMERATION_METHODS:
                    self.os_enum_functions[alias.asname or alias.name] = alias.name
                if alias.name == "path":
                    self.os_path_modules.add(alias.asname or "path")
        if node.module == "os.path":
            for alias in node.names:
                if alias.name in OS_PATH_CHECK_METHODS:
                    self.os_path_functions[alias.asname or alias.name] = alias.name
        if node.module == "pathlib":
            for alias in node.names:
                if alias.name == "Path":
                    self.path_constructors.add(alias.asname or "Path")
        self.generic_visit(node)

    def _literal_path_parts(self, node: ast.AST) -> tuple[str, ...] | None:
        return _literal_path_parts(
            node,
            self.name_paths,
            frozenset(self.path_constructors),
            frozenset(self.path_modules),
            frozenset(self.os_modules),
            frozenset(self.os_path_modules),
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        parts = self._literal_path_parts(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name) and parts is not None:
                self.name_paths[target.id] = parts
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            parts = self._literal_path_parts(node.value)
            if parts is not None:
                self.name_paths[node.target.id] = parts
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_call(node)
        self.generic_visit(node)

    def _add(self, node: ast.AST, *, operation: str, artifact_root: str) -> None:
        self.findings.append(
            ArtifactReadFinding(
                path=self.rel_path,
                line=getattr(node, "lineno", 0),
                operation=operation,
                artifact_root=artifact_root,
            )
        )

    def _check_call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and (func.id == "open" or func.id in self.open_functions):
            path_node = _call_arg(node, 0, ("file",))
            if path_node is not None:
                self._check_open_like(
                    node,
                    path_node,
                    operation=self.open_functions.get(func.id, "open"),
                )
            return
        if isinstance(func, ast.Name) and func.id in self.os_enum_functions:
            original = self.os_enum_functions[func.id]
            keyword_names = ("top",) if original == "walk" else ("path",)
            path_node = _call_arg(node, 0, keyword_names)
            if path_node is not None:
                self._check_path_operation(node, path_node, operation=f"os.{original}")
            return
        if isinstance(func, ast.Name) and func.id in self.os_path_functions:
            original = self.os_path_functions[func.id]
            path_node = _call_arg(node, 0, ("path",))
            if path_node is not None:
                self._check_path_operation(node, path_node, operation=f"os.path.{original}")
            return
        if isinstance(func, ast.Name) and func.id in self.glob_functions:
            original = self.glob_functions[func.id]
            path_node = _call_arg(node, 0, ("pathname",))
            if path_node is not None:
                self._check_path_operation(node, path_node, operation=f"glob.{original}")
            return

        if isinstance(func, ast.Attribute):
            if (
                isinstance(func.value, ast.Attribute)
                and func.value.attr == "path"
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id in self.os_modules
                and func.attr in OS_PATH_CHECK_METHODS
            ):
                path_node = _call_arg(node, 0, ("path",))
                if path_node is not None:
                    self._check_path_operation(node, path_node, operation=f"os.path.{func.attr}")
            elif (
                isinstance(func.value, ast.Name)
                and func.value.id in self.os_path_modules
                and func.attr in OS_PATH_CHECK_METHODS
            ):
                path_node = _call_arg(node, 0, ("path",))
                if path_node is not None:
                    self._check_path_operation(node, path_node, operation=f"os.path.{func.attr}")

            receiver_parts = self._literal_path_parts(func.value)
            if receiver_parts is not None:
                artifact_root = _forbidden_root(receiver_parts)
                if artifact_root and func.attr in READ_METHODS:
                    self._add(node, operation=func.attr, artifact_root=artifact_root)
                elif (
                    artifact_root
                    and func.attr in OPEN_METHODS
                    and _mode_reads(_mode_from_call(node, path_method=True))
                ):
                    self._add(node, operation=func.attr, artifact_root=artifact_root)

            if (
                isinstance(func.value, ast.Name)
                and func.value.id in self.builtins_modules
                and func.attr == "open"
            ):
                path_node = _call_arg(node, 0, ("file",))
                if path_node is not None:
                    self._check_open_like(node, path_node, operation="builtins.open")
            if (
                isinstance(func.value, ast.Name)
                and func.value.id in self.io_modules
                and func.attr == "open"
            ):
                path_node = _call_arg(node, 0, ("file",))
                if path_node is not None:
                    self._check_open_like(node, path_node, operation="io.open")
            if (
                isinstance(func.value, ast.Name)
                and func.value.id in self.os_modules
                and func.attr in OS_ENUMERATION_METHODS
            ):
                keyword_names = ("top",) if func.attr == "walk" else ("path",)
                path_node = _call_arg(node, 0, keyword_names)
                if path_node is not None:
                    self._check_path_operation(node, path_node, operation=f"os.{func.attr}")
            if (
                isinstance(func.value, ast.Name)
                and func.value.id in self.glob_modules
                and func.attr in GLOB_METHODS
            ):
                path_node = _call_arg(node, 0, ("pathname",))
                if path_node is not None:
                    self._check_path_operation(node, path_node, operation=f"glob.{func.attr}")

    def _check_open_like(self, node: ast.Call, path_node: ast.AST, *, operation: str) -> None:
        parts = self._literal_path_parts(path_node)
        if parts is None:
            return
        artifact_root = _forbidden_root(parts)
        if artifact_root and _mode_reads(_mode_from_call(node)):
            self._add(node, operation=operation, artifact_root=artifact_root)

    def _check_path_operation(self, node: ast.Call, path_node: ast.AST, *, operation: str) -> None:
        parts = self._literal_path_parts(path_node)
        if parts is None:
            return
        artifact_root = _forbidden_root(parts)
        if artifact_root:
            self._add(node, operation=operation, artifact_root=artifact_root)


def collect_artifact_read_findings_for_source(
    source_text: str,
    *,
    rel_path: str,
) -> tuple[list[ArtifactReadFinding], list[str]]:
    """Return forbidden artifact-read findings for one Python source string."""

    try:
        tree = ast.parse(source_text, filename=rel_path)
    except SyntaxError as exc:
        line = exc.lineno or 0
        return [], [f"{rel_path}:{line}: syntax error: {exc.msg}"]
    visitor = ArtifactReadVisitor(rel_path=rel_path)
    visitor.visit(tree)
    return sorted(visitor.findings), []


def _display(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<external-path>"


def _runtime_python_files(repo_root: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    errors: list[str] = []
    for target in RUNTIME_SCAN_TARGETS:
        path = repo_root / target
        if not path.exists():
            errors.append(f"{target}: configured runtime scan target missing")
            continue
        if path.is_file():
            files.append(path)
            continue
        files.extend(
            candidate
            for candidate in sorted(path.rglob("*.py"))
            if "__pycache__" not in candidate.parts
        )
    return files, errors


def collect_artifact_read_findings(repo_root: Path) -> tuple[list[ArtifactReadFinding], list[str]]:
    """Return all forbidden runtime artifact-read findings for the repo."""

    files, errors = _runtime_python_files(repo_root)
    findings: list[ArtifactReadFinding] = []
    for path in files:
        rel_path = _display(path, repo_root)
        try:
            source_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{rel_path}: unable to read: {type(exc).__name__}")
            continue
        file_findings, file_errors = collect_artifact_read_findings_for_source(
            source_text,
            rel_path=rel_path,
        )
        findings.extend(file_findings)
        errors.extend(file_errors)
    return sorted(findings), errors


def _markers(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in MARKER_RE.finditer(text)}


def validate_artifact_boundary_doc(
    text: str,
    *,
    filename: str = ARTIFACT_BOUNDARY_DOC,
) -> list[str]:
    """Return deterministic errors for the artifact validation boundary document."""

    errors: list[str] = []
    markers = _markers(text)
    for key, expected in REQUIRED_DOC_MARKERS.items():
        actual = markers.get(key)
        if actual is None:
            errors.append(f"{filename}: missing marker {key}")
        elif actual != expected:
            errors.append(f"{filename}: marker {key} must be {expected}, got {actual}")
    lowered = text.casefold()
    for token in REQUIRED_DOC_TOKENS:
        if token.casefold() not in lowered:
            errors.append(f"{filename}: missing required artifact-boundary token: {token}")
    return errors


def _read(path: Path, repo_root: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{_display(path, repo_root)}: unable to read: {type(exc).__name__}")
        return None


def validate_repo(repo_root: Path) -> list[str]:
    """Validate local artifact-reader boundaries for product runtime code."""

    errors: list[str] = []
    findings, scan_errors = collect_artifact_read_findings(repo_root)
    errors.extend(scan_errors)
    errors.extend(finding.display() for finding in findings)

    doc_path = repo_root / ARTIFACT_BOUNDARY_DOC
    doc_text = _read(doc_path, repo_root, errors)
    if doc_text is not None:
        errors.extend(
            validate_artifact_boundary_doc(doc_text, filename=_display(doc_path, repo_root))
        )
    return sorted(errors)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root to validate. Defaults to this script's repo.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    errors = validate_repo(repo_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("artifact validation boundary guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
