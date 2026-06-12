"""Guard: subprocess must not use short-name binaries (B607-class).

Policy: gh, git, curl, wget, ssh etc. only via shutil.which() or absolute path.
Bare python/python3 subprocesses must use sys.executable or a repo-approved
interpreter path.
"""

from __future__ import annotations

import ast
import re
import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = (
    REPO_ROOT / "app",
    REPO_ROOT / "core",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
    REPO_ROOT / "tools" / "graphmap",
)
DISALLOWED_SHORT_BINARIES: frozenset[str] = frozenset(
    {"curl", "gh", "git", "python", "python3", "ssh", "wget"}
)
PYTHON_SHORT_BINARIES: frozenset[str] = frozenset({"python", "python3"})
SUBPROCESS_FUNCTIONS: frozenset[str] = frozenset(
    {"Popen", "call", "check_call", "check_output", "run"}
)
PYTHON_BINARY_NAME_RE = re.compile(r"^python(?:3(?:\.\d+)?)?$")
SCOPE_NODE_TYPES = (
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.FunctionDef,
    ast.Lambda,
    ast.Module,
)


@dataclass(frozen=True)
class SubprocessViolation:
    relpath: str
    lineno: int
    line: str
    reason: str


@dataclass(frozen=True)
class SubprocessImportContext:
    module_aliases: frozenset[str]
    function_aliases: dict[str, str]


@dataclass(frozen=True)
class AssignmentCandidate:
    value: ast.expr
    branch_dependent: bool


AssignmentResolver = Callable[[ast.expr, int, set[str]], str | None]


def _iter_files() -> list[Path]:
    exclude = {".venv", "venv", "node_modules", "__pycache__", ".git", "disabled_hypothesis"}
    out: list[Path] = []
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(part in p.parts for part in exclude):
                continue
            try:
                p.relative_to(REPO_ROOT)
            except ValueError:
                continue
            out.append(p)
    return sorted(out)


def _subprocess_import_context(tree: ast.AST) -> SubprocessImportContext:
    module_aliases: set[str] = {"subprocess"}
    function_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                if alias.name in SUBPROCESS_FUNCTIONS:
                    function_aliases[alias.asname or alias.name] = alias.name
    return SubprocessImportContext(
        module_aliases=frozenset(module_aliases),
        function_aliases=function_aliases,
    )


def _subprocess_call_name(node: ast.Call, *, imports: SubprocessImportContext) -> str | None:
    function = node.func
    if isinstance(function, ast.Attribute):
        if function.attr not in SUBPROCESS_FUNCTIONS:
            return None
        owner = function.value
        if not isinstance(owner, ast.Name) or owner.id not in imports.module_aliases:
            return None
        return function.attr
    if isinstance(function, ast.Name) and function.id in imports.function_aliases:
        return imports.function_aliases[function.id]
    return None


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _scope_contains_line(scope: ast.AST, lineno: int) -> bool:
    if isinstance(scope, ast.Module):
        return True
    start = getattr(scope, "lineno", None)
    end = getattr(scope, "end_lineno", None)
    return isinstance(start, int) and isinstance(end, int) and start <= lineno <= end


def _nearest_scope(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST:
    current = node
    while current in parents:
        if isinstance(current, SCOPE_NODE_TYPES):
            return current
        current = parents[current]
    return current


def _is_branch_dependent_assignment(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current = node
    while current in parents:
        parent = parents[current]
        if isinstance(
            parent, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)
        ):
            return True
        if isinstance(parent, SCOPE_NODE_TYPES):
            return False
        current = parent
    return False


def _scope_chain_for_lineno(tree: ast.AST, lineno: int) -> tuple[ast.AST, ...]:
    scopes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, SCOPE_NODE_TYPES) and _scope_contains_line(node, lineno)
    ]
    scopes.sort(key=lambda node: getattr(node, "lineno", 0), reverse=True)
    return tuple(scopes) if scopes else (tree,)


def _find_recent_assignments(
    tree: ast.AST, upto_lineno: int, name: str
) -> list[AssignmentCandidate]:
    matches: list[tuple[int, AssignmentCandidate]] = []
    parents = _parent_map(tree)
    allowed_scopes = {id(scope) for scope in _scope_chain_for_lineno(tree, upto_lineno)}
    for node in ast.walk(tree):
        target: ast.expr | None
        value: ast.expr
        if isinstance(node, ast.Assign):
            target = next((item for item in node.targets if isinstance(item, ast.Name)), None)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if node.value is None:
                continue
            value = node.value
        else:
            continue
        if not isinstance(target, ast.Name) or target.id != name:
            continue
        if not (1 <= node.lineno < upto_lineno):
            continue
        if id(_nearest_scope(node, parents)) not in allowed_scopes:
            continue
        matches.append(
            (
                node.lineno,
                AssignmentCandidate(
                    value=value,
                    branch_dependent=_is_branch_dependent_assignment(node, parents),
                ),
            )
        )
    # Resolver callers depend on newest-to-oldest order when treating the first
    # unconditional assignment as the safe overwrite boundary.
    matches.sort(key=lambda item: item[0], reverse=True)
    return [value for _, value in matches]


def _literal_subscript_key(expr: ast.Subscript) -> str | None:
    key = expr.slice
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return key.value
    return None


def _is_os_environ_subscript(expr: ast.Subscript) -> bool:
    value = expr.value
    return (
        isinstance(value, ast.Attribute)
        and value.attr == "environ"
        and isinstance(value.value, ast.Name)
        and value.value.id == "os"
    ) or (isinstance(value, ast.Name) and value.id == "environ")


def _is_disallowed_binary_token(value: str) -> bool:
    if value.startswith("/"):
        return _is_disallowed_absolute_python(value)
    return value in DISALLOWED_SHORT_BINARIES or _is_python_binary_name(value)


def _is_env_assignment_token(value: str) -> bool:
    key, sep, _ = value.partition("=")
    return bool(sep and key and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key))


def _env_launcher_target_from_tokens(tokens: list[str]) -> str | None:
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "-S":
            if index + 1 >= len(tokens):
                return None
            split_target = shlex.split(tokens[index + 1].strip())
            return split_target[0] if split_target else None
        if token in {"-u", "--unset"}:
            index += 2
            continue
        if token.startswith("-u") and len(token) > 2:
            index += 1
            continue
        if token in {"-i", "--ignore-environment"} or token.startswith("-"):
            index += 1
            continue
        if _is_env_assignment_token(token):
            index += 1
            continue
        return token
    return None


def _shell_command_binary_from_tokens(tokens: list[str]) -> str | None:
    candidates: list[str] = []
    index = 0
    command_start = True
    control_operators = {"&&", "||", ";", "|"}
    while index < len(tokens):
        token = tokens[index]
        if token in control_operators:
            command_start = True
            index += 1
            continue
        if not command_start:
            index += 1
            continue
        if _is_env_assignment_token(token):
            index += 1
            continue
        candidates.append(token)
        command_start = False
        index += 1

    for candidate in candidates:
        if _is_disallowed_binary_token(candidate):
            return candidate
    return candidates[0] if candidates else None


def _expr_resolution_hits_name_cycle(
    tree: ast.AST, expr: ast.expr, *, upto_lineno: int, seen_names: set[str]
) -> bool:
    if isinstance(expr, ast.Name):
        if expr.id in seen_names:
            return True
        assignments = _find_recent_assignments(tree, upto_lineno, expr.id)
        if not assignments:
            return False
        latest = assignments[0]
        if latest.branch_dependent:
            return any(
                _expr_resolution_hits_name_cycle(
                    tree,
                    assignment.value,
                    upto_lineno=getattr(assignment.value, "lineno", upto_lineno),
                    seen_names=seen_names | {expr.id},
                )
                for assignment in assignments
            )
        return _expr_resolution_hits_name_cycle(
            tree,
            latest.value,
            upto_lineno=getattr(latest.value, "lineno", upto_lineno),
            seen_names=seen_names | {expr.id},
        )
    if isinstance(expr, (ast.List, ast.Tuple)) and expr.elts:
        return _expr_resolution_hits_name_cycle(
            tree, expr.elts[0], upto_lineno=upto_lineno, seen_names=seen_names
        )
    if isinstance(expr, ast.Call) and expr.args:
        function = expr.func
        is_string_or_path_wrapper = (
            isinstance(function, ast.Name) and function.id in {"Path", "str"}
        ) or (isinstance(function, ast.Attribute) and function.attr == "Path")
        if is_string_or_path_wrapper:
            return _expr_resolution_hits_name_cycle(
                tree, expr.args[0], upto_lineno=upto_lineno, seen_names=seen_names
            )
    return False


def _resolve_name_from_assignments(
    tree: ast.AST,
    expr: ast.Name,
    *,
    upto_lineno: int,
    seen_names: set[str],
    resolver: AssignmentResolver,
) -> str | None:
    if expr.id in seen_names:
        return None
    assignments = _find_recent_assignments(tree, upto_lineno, expr.id)
    if not assignments:
        return None
    latest = assignments[0]
    latest_lineno = getattr(latest.value, "lineno", upto_lineno)
    if not latest.branch_dependent:
        candidate = resolver(latest.value, latest_lineno, seen_names | {expr.id})
        if candidate is not None:
            return candidate
        if _expr_resolution_hits_name_cycle(
            tree,
            latest.value,
            upto_lineno=latest_lineno,
            seen_names=seen_names | {expr.id},
        ):
            return resolver(expr, latest_lineno, seen_names)
        return candidate

    resolved: str | None = None
    # Branch-dependent self-cycles are bounded by seen_names; continue scanning
    # reachable older assignments until an unconditional overwrite stops the chain.
    for assignment in assignments:
        candidate = resolver(
            assignment.value,
            getattr(assignment.value, "lineno", upto_lineno),
            seen_names | {expr.id},
        )
        if candidate is not None and _is_disallowed_binary_token(candidate):
            return candidate
        if resolved is None:
            resolved = candidate
        if not assignment.branch_dependent:
            break
    return resolved


def _resolve_binary_expr(
    tree: ast.AST, expr: ast.expr, *, upto_lineno: int, seen_names: set[str]
) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value.strip()
    if isinstance(expr, ast.Name):
        return _resolve_name_from_assignments(
            tree,
            expr,
            upto_lineno=upto_lineno,
            seen_names=seen_names,
            resolver=lambda value, line, names: _resolve_binary_expr(
                tree, value, upto_lineno=line, seen_names=names
            ),
        )
    if isinstance(expr, ast.Subscript) and _is_os_environ_subscript(expr):
        key = _literal_subscript_key(expr)
        if key in {"DEV_PYTHON", "VENV_PYTHON"}:
            return None
        if key is not None and "PYTHON" in key.upper():
            return "python"
        return None
    if isinstance(expr, ast.Call) and expr.args:
        function = expr.func
        is_string_or_path_wrapper = (
            isinstance(function, ast.Name) and function.id in {"Path", "str"}
        ) or (isinstance(function, ast.Attribute) and function.attr == "Path")
        if is_string_or_path_wrapper:
            return _resolve_binary_expr(
                tree,
                expr.args[0],
                upto_lineno=upto_lineno,
                seen_names=seen_names,
            )
    return None


def _resolve_argv_binary(
    tree: ast.AST, expr: ast.expr, *, upto_lineno: int, seen_names: set[str]
) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        parts = shlex.split(expr.value.strip())
        if parts and Path(parts[0]).name == "env":
            return _env_launcher_target_from_tokens(parts) or parts[0]
        return _shell_command_binary_from_tokens(parts)
    if isinstance(expr, (ast.List, ast.Tuple)) and expr.elts:
        first_binary = _resolve_binary_expr(
            tree, expr.elts[0], upto_lineno=upto_lineno, seen_names=seen_names
        )
        if first_binary is not None and Path(first_binary).name == "env" and len(expr.elts) > 1:
            resolved_tokens = [
                first_binary,
                *[
                    token
                    for token in (
                        _resolve_binary_expr(
                            tree,
                            item,
                            upto_lineno=upto_lineno,
                            seen_names=seen_names,
                        )
                        for item in expr.elts[1:]
                    )
                    if token is not None
                ],
            ]
            env_target = _env_launcher_target_from_tokens(resolved_tokens)
            return env_target or first_binary
        return first_binary
    if isinstance(expr, ast.Name):
        return _resolve_name_from_assignments(
            tree,
            expr,
            upto_lineno=upto_lineno,
            seen_names=seen_names,
            resolver=lambda value, line, names: _resolve_argv_binary(
                tree, value, upto_lineno=line, seen_names=names
            ),
        )
    return None


def _is_python_binary_name(value: str) -> bool:
    return bool(PYTHON_BINARY_NAME_RE.fullmatch(value))


def _is_repo_approved_python_literal(value: str) -> bool:
    path = Path(value)
    if not path.is_absolute() or not _is_python_binary_name(path.name):
        return False
    if ".." in path.parts:
        return False
    try:
        path.relative_to(REPO_ROOT / ".venv" / "bin")
    except ValueError:
        return False
    return True


def _is_disallowed_absolute_python(value: str) -> bool:
    path = Path(value)
    if not path.is_absolute() or not _is_python_binary_name(path.name):
        return False
    return not _is_repo_approved_python_literal(value)


def _argv_expr(node: ast.Call) -> ast.expr | None:
    if node.args:
        return node.args[0]
    return next((keyword.value for keyword in node.keywords if keyword.arg == "args"), None)


def _keyword_expr(node: ast.Call, name: str) -> ast.expr | None:
    return next((keyword.value for keyword in node.keywords if keyword.arg == name), None)


def _first_argv_binary(tree: ast.AST, node: ast.Call) -> str | None:
    argv = _argv_expr(node)
    if argv is None:
        return None
    return _resolve_argv_binary(tree, argv, upto_lineno=node.lineno, seen_names=set())


def _executable_override_binary(tree: ast.AST, node: ast.Call) -> str | None:
    executable = _keyword_expr(node, "executable")
    if executable is None:
        return None
    return _resolve_binary_expr(tree, executable, upto_lineno=node.lineno, seen_names=set())


def _find_recent_which_var(tree: ast.AST, upto_lineno: int, bin_name: str) -> str | None:
    """Find a variable assigned from shutil.which(bin_name) within 80 lines above."""
    best: tuple[int, str] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not (upto_lineno - 80 <= node.lineno < upto_lineno):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        function = value.func
        if not (
            isinstance(function, ast.Attribute)
            and function.attr == "which"
            and isinstance(function.value, ast.Name)
            and function.value.id == "shutil"
        ):
            continue
        if not value.args:
            continue
        first_arg = value.args[0]
        if not (
            isinstance(first_arg, ast.Constant)
            and isinstance(first_arg.value, str)
            and first_arg.value == bin_name
        ):
            continue
        target = next((item for item in node.targets if isinstance(item, ast.Name)), None)
        if target is None:
            continue
        if best is None or node.lineno > best[0]:
            best = (node.lineno, target.id)
    if best is not None:
        return best[1]
    return None


def _reason_for_binary(tree: ast.AST, *, lineno: int, bin_token: str) -> str:
    if _is_disallowed_absolute_python(bin_token):
        return (
            f"calls '{bin_token}' as an absolute Python interpreter outside repo-approved "
            "paths; use sys.executable for current-interpreter subprocesses or a "
            "repo-approved interpreter path such as VENV_PYTHON, DEV_PYTHON, "
            "repo .venv/bin/python, or the Experiment Runner resolver pattern"
        )
    if _is_python_binary_name(bin_token):
        return (
            f"calls '{bin_token}' by short name; use sys.executable for current-interpreter "
            "subprocesses or a repo-approved interpreter path such as VENV_PYTHON, "
            "DEV_PYTHON, repo .venv/bin/python, or the Experiment Runner resolver pattern"
        )

    which_var = _find_recent_which_var(tree, lineno, bin_token)
    if which_var:
        return (
            f"calls '{bin_token}' by short name; use [{which_var}, ...] "
            f"from shutil.which('{bin_token}')"
        )
    return (
        f"calls '{bin_token}' by short name; resolve with shutil.which('{bin_token}') "
        "or use an absolute path"
    )


def _find_subprocess_violations_in_source(
    source: str, *, relpath: str
) -> list[SubprocessViolation]:
    tree = ast.parse(source, filename=relpath)
    imports = _subprocess_import_context(tree)
    lines = source.splitlines()
    violations: list[SubprocessViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _subprocess_call_name(node, imports=imports) is None:
            continue
        bin_tokens = [
            token
            for token in (
                _first_argv_binary(tree, node),
                _executable_override_binary(tree, node),
            )
            if token is not None
        ]
        if not bin_tokens:
            continue
        for bin_token in dict.fromkeys(bin_tokens):
            if bin_token.startswith("/"):
                if _is_disallowed_absolute_python(bin_token):
                    line = lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
                    violations.append(
                        SubprocessViolation(
                            relpath=relpath,
                            lineno=node.lineno,
                            line=line,
                            reason=_reason_for_binary(
                                tree, lineno=node.lineno, bin_token=bin_token
                            ),
                        )
                    )
                continue
            if bin_token not in DISALLOWED_SHORT_BINARIES and not _is_python_binary_name(bin_token):
                continue
            line = lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
            violations.append(
                SubprocessViolation(
                    relpath=relpath,
                    lineno=node.lineno,
                    line=line,
                    reason=_reason_for_binary(tree, lineno=node.lineno, bin_token=bin_token),
                )
            )
    return violations


def test_guard_flags_bare_python_subprocess_literals() -> None:
    source = 'import subprocess\nsubprocess.run(["python", "-c", "print(42)"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 2
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_multiline_bare_python3_popen_literals() -> None:
    source = """\
import subprocess

subprocess.Popen(
    ["python3", "-c", "print(42)"],
)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 3
    assert "calls 'python3' by short name" in violations[0].reason


def test_guard_flags_keyword_args_bare_python_subprocess_literals() -> None:
    source = 'import subprocess\nsubprocess.run(args=["python", "-c", "print(42)"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 2
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_keyword_args_short_external_binary() -> None:
    source = """\
import subprocess

subprocess.Popen(args=["git", "status"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 3
    assert "resolve with shutil.which('git')" in violations[0].reason


def test_guard_flags_subprocess_argv_list_variable() -> None:
    source = """\
import subprocess

args = ["git", "status"]
subprocess.run(args)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 4
    assert "resolve with shutil.which('git')" in violations[0].reason


def test_guard_flags_subprocess_argv_binary_variable() -> None:
    source = """\
import subprocess

cmd = "python"
subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 4
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_ignores_assignments_from_unrelated_scopes() -> None:
    source = """\
import subprocess

def unrelated() -> None:
    cmd = "python"

def target() -> None:
    subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_resolves_assignments_from_parent_scope() -> None:
    source = """\
import subprocess

cmd = "python"

def target() -> None:
    subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 6
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_string_form_subprocess_commands() -> None:
    source = """\
import subprocess

subprocess.run("python -c pass", shell=True)
subprocess.check_output("git status", shell=True)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 2
    assert violations[0].lineno == 3
    assert "repo-approved interpreter path" in violations[0].reason
    assert violations[1].lineno == 4
    assert "resolve with shutil.which('git')" in violations[1].reason


def test_guard_flags_shell_string_command_prefixes_without_substring_matching() -> None:
    source = """\
import subprocess

subprocess.run("FOO=bar python -c pass", shell=True)
subprocess.run("cd /tmp && python3 -c pass", shell=True)
subprocess.run("echo python", shell=True)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 2
    assert {violation.lineno for violation in violations} == {3, 4}
    assert all("repo-approved interpreter path" in violation.reason for violation in violations)


def test_guard_flags_unapproved_python_environment_variable() -> None:
    source = """\
import os
from pathlib import Path
import subprocess

cmd = Path(os.environ["PYTHON"])
subprocess.run([str(cmd), "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 6
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_allows_approved_python_environment_variable() -> None:
    source = """\
import os
from pathlib import Path
import subprocess

cmd = Path(os.environ["VENV_PYTHON"])
subprocess.run([str(cmd), "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_flags_any_reaching_disallowed_assignment() -> None:
    source = """\
import subprocess
import sys

cmd = "python"
if use_current:
    cmd = sys.executable
subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 7
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_self_assigned_binary_variable_bypass() -> None:
    source = """\
import subprocess

cmd = "python"
cmd = cmd
subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 5
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_self_assigned_argv_variable_bypass() -> None:
    source = """\
import subprocess

args = ["git", "status"]
args = args
subprocess.run(args)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 5
    assert "resolve with shutil.which('git')" in violations[0].reason


def test_guard_allows_safe_binary_overwrite_before_self_assignment() -> None:
    source = """\
import subprocess
import sys

cmd = "python"
cmd = sys.executable
cmd = cmd
subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_allows_safe_binary_overwrite_before_wrapped_self_assignment() -> None:
    source = """\
import subprocess
import sys

cmd = "python"
cmd = sys.executable
cmd = str(cmd)
subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_allows_safe_argv_overwrite_before_self_assignment() -> None:
    source = """\
import subprocess
import sys

args = ["git", "status"]
args = [sys.executable, "-c", "print(42)"]
args = args
subprocess.run(args)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_allows_safe_overwrite_before_branch_dependent_self_assignment() -> None:
    source = """\
import subprocess
import sys

cmd = "python"
cmd = sys.executable
if keep_current:
    cmd = cmd
subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_allows_safe_argv_overwrite_before_branch_dependent_self_assignment() -> None:
    source = """\
import subprocess
import sys

args = ["git", "status"]
args = [sys.executable, "-c", "print(42)"]
if keep_current:
    args = args
subprocess.run(args)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_flags_branch_alias_self_cycle_binary_bypass() -> None:
    source = """\
import subprocess
import sys

cmd = sys.executable
other = "python"
if keep_other:
    other = other
if use_other:
    cmd = other
subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 10
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_branch_alias_self_cycle_argv_bypass() -> None:
    source = """\
import subprocess
import sys

args = [sys.executable, "-c", "print(42)"]
other = ["git", "status"]
if keep_other:
    other = other
if use_other:
    args = other
subprocess.run(args)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 10
    assert "resolve with shutil.which('git')" in violations[0].reason


def test_guard_allows_linear_safe_assignment_overwrite() -> None:
    source = """\
import subprocess
import sys

cmd = "python"
cmd = sys.executable
subprocess.run([cmd, "-c", "print(42)"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_flags_usr_bin_env_python_launcher() -> None:
    source = 'import subprocess\nsubprocess.run(["/usr/bin/env", "python", "-c", "pass"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 2
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_usr_bin_env_python_launcher_after_options_and_assignments() -> None:
    source = """\
import subprocess

subprocess.run(["/usr/bin/env", "-S", "python -c pass"])
subprocess.run(["/usr/bin/env", "FOO=bar", "python3", "-c", "pass"])
subprocess.run("/usr/bin/env -S python3.12 -c pass", shell=True)
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 3
    assert {violation.lineno for violation in violations} == {3, 4, 5}
    assert all("repo-approved interpreter path" in violation.reason for violation in violations)


def test_guard_flags_absolute_system_python_literal() -> None:
    source = 'import subprocess\nsubprocess.run(["/usr/bin/python3", "-c", "pass"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 2
    assert "outside repo-approved paths" in violations[0].reason


def test_guard_flags_versioned_python_short_name() -> None:
    source = 'import subprocess\nsubprocess.run(["python3.12", "-c", "pass"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 2
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_path_wrapped_absolute_system_python_literal() -> None:
    source = """\
from pathlib import Path
import subprocess

subprocess.run([Path("/usr/bin/python3"), "-c", "pass"])
subprocess.run([str("/usr/bin/python3"), "-c", "pass"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 2
    assert violations[0].lineno == 4
    assert "outside repo-approved paths" in violations[0].reason
    assert violations[1].lineno == 5
    assert "outside repo-approved paths" in violations[1].reason


def test_guard_rejects_parent_traversal_under_repo_venv_python_literal() -> None:
    traversing_python = (
        REPO_ROOT / ".venv" / "bin" / ".." / ".." / ".." / ".." / "usr" / "bin" / "python3"
    ).as_posix()
    source = f'import subprocess\nsubprocess.run(["{traversing_python}", "-c", "pass"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 2
    assert "outside repo-approved paths" in violations[0].reason


def test_guard_flags_executable_override_short_python() -> None:
    source = """\
import subprocess
import sys

subprocess.run([sys.executable, "-c", "pass"], executable="python3")
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 4
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_allows_absolute_repo_venv_python_literal() -> None:
    repo_python = (REPO_ROOT / ".venv" / "bin" / "python").as_posix()
    source = f'import subprocess\nsubprocess.run(["{repo_python}", "-c", "pass"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_flags_subprocess_module_alias() -> None:
    source = 'import subprocess as sp\nsp.run(["python", "-c", "print(42)"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert violations[0].lineno == 2
    assert "repo-approved interpreter path" in violations[0].reason


def test_guard_flags_imported_subprocess_helpers() -> None:
    source = """\
from subprocess import check_call, check_output

check_call(["python", "-c", "print(42)"])
check_output(["git", "status"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 2
    assert violations[0].lineno == 3
    assert "repo-approved interpreter path" in violations[0].reason
    assert violations[1].lineno == 4
    assert "resolve with shutil.which('git')" in violations[1].reason


def test_guard_allows_current_interpreter_subprocess() -> None:
    source = 'import subprocess\nimport sys\nsubprocess.run([sys.executable, "-c", "pass"])\n'

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_allows_repo_approved_interpreter_variable() -> None:
    source = """\
import os
import subprocess
from pathlib import Path

repo_python = Path(os.environ["VENV_PYTHON"])
subprocess.run([str(repo_python), "-m", "pytest"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_allows_shutil_which_resolved_binary_variable() -> None:
    source = """\
import shutil
import subprocess

git_binary = shutil.which("git")
subprocess.run([git_binary, "status"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert violations == []


def test_guard_reports_which_guidance_for_short_external_binary() -> None:
    source = """\
import shutil
import subprocess

git_binary = shutil.which("git")
subprocess.run(["git", "status"])
"""

    violations = _find_subprocess_violations_in_source(source, relpath="sample.py")

    assert len(violations) == 1
    assert "use [git_binary, ...]" in violations[0].reason


def test_subprocess_requires_absolute_or_which_resolved_binary() -> None:
    """subprocess.run/Popen must not use short-name binaries; use shutil.which or abs path."""
    violations: list[SubprocessViolation] = []
    for path in _iter_files():
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        violations.extend(_find_subprocess_violations_in_source(source, relpath=rel))

    if violations:
        msg_lines = [
            "Subprocess short-name binary violations (B607-class).",
            "Fix: use shutil.which('<bin>') for external tools, sys.executable for current "
            "Python, or an explicit repo-approved Python interpreter path.",
            "",
        ]
        for v in violations:
            msg_lines.append(f"- {v.relpath}:{v.lineno}: {v.reason}")
            msg_lines.append(f"  {v.line[:100]}{'...' if len(v.line) > 100 else ''}")
        raise AssertionError("\n".join(msg_lines))
