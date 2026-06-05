"""Guard: subprocess must not use short-name binaries (B607-class).

Policy: gh, git, curl, wget, ssh etc. only via shutil.which() or absolute path.
Bare python/python3 subprocesses must use sys.executable or a repo-approved
interpreter path.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = (
    REPO_ROOT / "app",
    REPO_ROOT / "core",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
)
DISALLOWED_SHORT_BINARIES: frozenset[str] = frozenset(
    {"curl", "gh", "git", "python", "python3", "ssh", "wget"}
)
PYTHON_SHORT_BINARIES: frozenset[str] = frozenset({"python", "python3"})


@dataclass(frozen=True)
class SubprocessViolation:
    relpath: str
    lineno: int
    line: str
    reason: str


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


def _subprocess_call_name(node: ast.Call) -> str | None:
    function = node.func
    if not isinstance(function, ast.Attribute):
        return None
    if function.attr not in {"run", "Popen"}:
        return None
    owner = function.value
    if not isinstance(owner, ast.Name) or owner.id != "subprocess":
        return None
    return function.attr


def _first_argv_binary(node: ast.Call) -> str | None:
    if not node.args:
        return None
    argv = node.args[0]
    if not isinstance(argv, (ast.List, ast.Tuple)) or not argv.elts:
        return None
    first_arg = argv.elts[0]
    if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
        return None
    return first_arg.value.strip()


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


def _reason_for_short_binary(tree: ast.AST, *, lineno: int, bin_token: str) -> str:
    if bin_token in PYTHON_SHORT_BINARIES:
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
    lines = source.splitlines()
    violations: list[SubprocessViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _subprocess_call_name(node) is None:
            continue
        bin_token = _first_argv_binary(node)
        if bin_token is None:
            continue
        if bin_token.startswith("/"):
            continue
        if bin_token not in DISALLOWED_SHORT_BINARIES:
            continue
        line = lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
        violations.append(
            SubprocessViolation(
                relpath=relpath,
                lineno=node.lineno,
                line=line,
                reason=_reason_for_short_binary(tree, lineno=node.lineno, bin_token=bin_token),
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
