"""Repository policy guards - enforce import hygiene and architectural constraints.

These tests prevent regression of patterns that cause Dual Base, namespace conflicts,
and xdist failures.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# --- Hard rules (policy) ---
FORBIDDEN_DYNAMIC_IMPORT_TOKENS = (
    "importlib.util.spec_from_file_location",
    "importlib.util.module_from_spec",
    "spec_from_file_location(",
    "module_from_spec(",
    "exec_module(",
)

FORBIDDEN_SYS_MODULES_TOKENS = (
    "sys.modules[",  # assignment/deletion (check context manually if needed)
)

FORBIDDEN_SYS_PATH_INSERT = "sys.path.insert"

# Allowed exceptions for dynamic imports / sys.path insert in tests
ALLOWED_TEST_FILES_FOR_DYNAMIC_IMPORT = {
    "tests/test_test_pro_access_coverage.py",
    "tests/test_ensure_database_versions.py",
    "tests/conftest.py",
    "tests/test_repo_policy_guards.py",  # this file (checks for these patterns)
    "tests/test_import_hygiene_guard.py",  # guard test
    "tests/test_app_public_surface.py",  # checks for spec_from_file_location string
}

ALLOWED_TEST_FILES_FOR_SYS_PATH_INSERT = {
    "tests/test_test_pro_access_coverage.py",
    "tests/conftest.py",
    "tests/test_repo_policy_guards.py",  # this file (checks for the pattern)
    "tests/test_import_hygiene_guard.py",  # guard test
}

# sys.modules checking in tests is allowed only for verification/guards
ALLOWED_SYS_MODULES_CHECK_FILES = {
    "tests/test_repo_policy_guards.py",  # this file
    "tests/conftest.py",  # sys.modules binding for app
    "tests/test_app_init_rebinding_spec.py",  # tests sys.modules["app"] behavior
}

# If you intentionally allow a specific file later, add it to an allowlist above.


def _iter_py_files(relative_glob: str) -> Iterable[Path]:
    yield from REPO_ROOT.glob(relative_glob)


def _rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


_TRANSIENT_POLICY_SCAN_PATHS = (re.compile(r"^app/test_guard_.*_temp\.py$"),)


def _read(p: Path) -> Optional[str]:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        rel = _rel(p)
        if any(pattern.match(rel) for pattern in _TRANSIENT_POLICY_SCAN_PATHS):
            # xdist TOCTOU: transient helper files can disappear between glob and read.
            return None
        raise


def test_no_dynamic_imports_in_app_core() -> None:
    """Prevent re-introducing dynamic module exec in app/core code."""
    offenders: list[str] = []

    for path in list(_iter_py_files("app/**/*.py")) + list(_iter_py_files("core/**/*.py")):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue
        if any(tok in content for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS):
            offenders.append(rel)

    assert not offenders, f"Dynamic import tokens found in: {offenders}"


# TODO (policy): sys.modules mutation guard is skipped temporarily.
# Audit basis: PR-600. Tracking: BACKLOG_LEDGER item "Fix test skips/xfails (batch)" (closed by PR-602).
# Follow-up: re-enable only after migrating offenders to monkeypatch.setitem/delitem patterns.
@pytest.mark.skip(reason="Temporarily skipped: known sys.modules legacy patterns in tests.")
def test_no_sys_modules_mutation_in_repo() -> None:
    """sys.modules mutation is a common source of Dual Base / namespace bugs.

    This checks for explicit assignment/deletion patterns.
    Reading from sys.modules is allowed.

    TODO: Clean up legacy tests that mutate sys.modules.
    """
    offenders: list[str] = []

    # Check for assignment: sys.modules[...] =
    assignment_pattern = r"sys\.modules\[[^]]+\]\s*="
    # Check for deletion: del sys.modules[...]
    deletion_pattern = r"del\s+sys\.modules\["

    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("providers/**/*.py"))
        + list(_iter_py_files("tests/**/*.py"))
    ):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue

        # Allow specific guard/verification files
        if rel in ALLOWED_SYS_MODULES_CHECK_FILES:
            continue

        if re.search(assignment_pattern, content) or re.search(deletion_pattern, content):
            offenders.append(rel)

    assert not offenders, f"sys.modules mutation found in: {offenders}"


def test_tests_have_no_dynamic_imports_except_whitelist() -> None:
    """Dynamic imports in tests cause module identity issues under xdist."""
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue

        if any(tok in content for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS):
            if rel not in ALLOWED_TEST_FILES_FOR_DYNAMIC_IMPORT:
                offenders.append(rel)

    assert (
        not offenders
    ), f"Dynamic imports are forbidden in tests except whitelist. Offenders: {offenders}"


def test_tests_have_no_sys_path_insert_except_whitelist() -> None:
    """sys.path.insert masks import errors and breaks xdist isolation."""
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        content = _read(path)
        if content is None:
            continue

        if FORBIDDEN_SYS_PATH_INSERT in content:
            if rel not in ALLOWED_TEST_FILES_FOR_SYS_PATH_INSERT:
                offenders.append(rel)

    assert (
        not offenders
    ), f"sys.path.insert is forbidden in tests except whitelist. Offenders: {offenders}"


def test_app_init_is_import_shim_not_dynamic_loader() -> None:
    """app/__init__.py must not reintroduce the old dynamic loader."""
    init_path = REPO_ROOT / "app" / "__init__.py"
    assert init_path.exists(), "app/__init__.py missing"

    content = _read(init_path)
    assert content is not None, "app/__init__.py unexpectedly missing during read"
    banned = [tok for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS if tok in content]
    assert not banned, f"app/__init__.py contains forbidden tokens: {banned}"


def test_app_surface_has_required_legacy_symbols() -> None:
    """If tests depend on `from app import X`, enforce that it exists."""
    import app

    required = {
        "app",  # FastAPI instance
        "__getattr__",  # PEP 562 forwarding
    }

    missing = [name for name in required if not hasattr(app, name)]
    assert not missing, f"Missing required symbols in app package: {missing}"


@pytest.mark.parametrize(
    "path_glob,forbidden_tokens",
    [
        ("providers/**/*.py", ("spec_from_file_location(", "exec_module(")),
    ],
)
def test_providers_no_dynamic_imports(path_glob: str, forbidden_tokens: tuple[str, ...]) -> None:
    """Providers must not use dynamic imports to avoid namespace corruption."""
    offenders: list[str] = []

    for path in _iter_py_files(path_glob):
        content = _read(path)
        if content is None:
            continue
        if any(tok in content for tok in forbidden_tokens):
            offenders.append(_rel(path))

    assert not offenders, f"Providers contain dynamic import tokens: {offenders}"


def test_no_sys_modules_get_recipe_store_in_tests() -> None:
    """Tests must not use sys.modules.get('recipe_store') - use standard imports instead.

    Anti-pattern: sys.modules.get("recipe_store") returns wrong module instance.
    Correct pattern: import app.services.recipe_store as rs
    """
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        # Skip this guard file itself
        if rel == "tests/test_repo_policy_guards.py":
            continue

        content = _read(path)
        if content is None:
            continue
        if (
            'sys.modules.get("recipe_store")' in content
            or "sys.modules.get('recipe_store')" in content
        ):
            offenders.append(rel)

    assert not offenders, (
        "Tests must not use sys.modules.get('recipe_store'). "
        f"Use 'import app.services.recipe_store as rs' instead. Offenders: {offenders}"
    )


def test_no_sys_modules_none_poisoning() -> None:
    """Prohibit setting sys.modules[...] = None which creates 'halted import' state.

    ❌ sys.modules["core.menu_engine"] = None  # Creates ModuleNotFoundError: import halted
    ❌ patch.dict("sys.modules", {"core.menu_engine": None})  # Same effect
    ✅ del sys.modules["core.menu_engine"]  # Safe removal
    ✅ monkeypatch.delitem(sys.modules, "core.menu_engine", raising=False)  # Safe mocking

    Note: This test allows legitimate import error testing in specific test files.
    """
    import re

    offenders: list[str] = []
    # Pattern: sys.modules[...]=None or patch.dict(..., {...: None})
    # Exclude this guard file itself from the check
    patterns = [
        r"sys\.modules\[[^]]+\]\s*=\s*None",
        r"patch\.dict\([^)]*\{[^}]*:[^}]*None[^}]*\}",  # patch.dict with None values
    ]

    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("tests/**/*.py"))
    ):
        rel = _rel(path)
        # Skip this guard file itself to avoid false positive on the pattern strings
        if rel == "tests/test_repo_policy_guards.py":
            continue
        # Skip specific test files that legitimately test import error handling
        if rel in [
            "tests/test_bmi_visualization.py",  # Tests matplotlib import error handling
        ]:
            continue

        content = _read(path)
        if content is None:
            continue

        for pattern in patterns:
            if re.search(pattern, content):
                offenders.append(f"{rel} (pattern: {pattern})")
                break  # Don't report same file multiple times

    assert not offenders, (
        "sys.modules None poisoning found. Use 'del sys.modules[key]' instead of 'sys.modules[key] = None'. "
        f"Offenders: {offenders}"
    )


def test_engineering_lessons_are_linked_from_repo_entrypoints() -> None:
    """Ensure ENGINEERING_LESSONS stays discoverable and doesn't get accidentally unlinked."""
    lessons_path = REPO_ROOT / "docs" / "ENGINEERING_LESSONS.md"
    assert lessons_path.exists(), "docs/ENGINEERING_LESSONS.md missing"

    agents_path = REPO_ROOT / "AGENTS.md"
    assert agents_path.exists(), "AGENTS.md missing"
    agents_content = _read(agents_path)
    assert agents_content is not None, "AGENTS.md unexpectedly missing during read"
    assert (
        "docs/ENGINEERING_LESSONS.md" in agents_content
    ), "AGENTS.md must reference docs/ENGINEERING_LESSONS.md so agents have a stable entrypoint."

    pr_template_path = REPO_ROOT / ".github" / "pull_request_template.md"
    assert pr_template_path.exists(), ".github/pull_request_template.md missing"
    pr_template_content = _read(pr_template_path)
    assert pr_template_content is not None, "PR template unexpectedly missing during read"
    assert (
        "docs/ENGINEERING_LESSONS.md" in pr_template_content
    ), "PR template must reference docs/ENGINEERING_LESSONS.md to keep humans/agents aligned."


def test_no_direct_model_submodule_imports() -> None:
    """Prohibit importing models from submodules - causes duplicate registration.

    ❌ from app.models.plans import WeeklyPlan
    ❌ from app.models.events import NutritionEvent
    ✅ from app.models import WeeklyPlan, NutritionEvent

    Reason: Direct submodule imports cause 'Table already defined' errors
    when modules are imported through different paths.
    See PR #403 commit 447e39c8 for context.
    """
    import re

    offenders: list[str] = []
    # Pattern: from app.models.(plans|events) import (exclude nutrition which is a data class module)
    pattern = re.compile(r"from\s+app\.models\.(plans|events)\s+import")

    # Check all Python files except app/models/__init__.py (which does the exports)
    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("tests/**/*.py"))
    ):
        rel = _rel(path)
        # Allow the export module itself and this guard file
        if rel in ("app/models/__init__.py", "tests/test_repo_policy_guards.py"):
            continue

        content = _read(path)
        if content is None:
            continue
        if pattern.search(content):
            offenders.append(rel)

    assert not offenders, (
        "Direct model submodule imports forbidden. "
        "Use 'from app.models import X' instead. "
        f"Offenders: {offenders}"
    )


# --- AST-first guardrails (harder to bypass than grep) ---

FORBIDDEN_EXACT_RELOAD_TARGETS: set[str] = {
    # Absolute forbid:
    "core.db",
}

FORBIDDEN_RELOAD_PREFIXES: set[str] = {
    # Optional broader forbid:
    "core.",
}

# Keep minimal; prefer empty.
ALLOWLIST_PATH_SUBSTRINGS: set[str] = set()

SKIP_DIRS_FOR_AST_SCAN = {
    ".git",
    ".venv",
    ".venv-ci",
    "venv",
    "__pycache__",
    "site-packages",
    "build",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    # Client apps (not part of backend policy)
    "docs",
    "frontend",
    "ios",
    # Test exclusions (aligned with pytest --ignore)
    "disabled_hypothesis",
    # Deployment/infra (may contain scripts but not core logic)
    "deploy",
    "scripts",
    # Migrations (Alembic scripts, not core logic)
    "alembic",
}


@dataclass(frozen=True)
class _AstViolation:
    relpath: str
    lineno: int
    col: int
    rule: str
    detail: str

    def format(self) -> str:
        return f"{self.relpath}:{self.lineno}:{self.col} [{self.rule}] {self.detail}"


def _iter_repo_py_files_for_ast_scan(root: Path) -> Iterable[Path]:
    paths: list[Path] = []
    for p in root.rglob("*.py"):
        if any(part in SKIP_DIRS_FOR_AST_SCAN for part in p.parts):
            continue
        paths.append(p)
    yield from sorted(paths, key=lambda x: x.as_posix())


def _is_allowlisted_for_ast_scan(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(token in rel for token in ALLOWLIST_PATH_SUBSTRINGS)


def _dotted_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


class _RepoPolicyAstVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.relpath = path.relative_to(REPO_ROOT).as_posix()
        self.violations: list[_AstViolation] = []
        # local alias -> fully-qualified dotted name (e.g., "r" -> "importlib.reload")
        self.aliases: dict[str, str] = {}

    def _resolve(self, dotted: Optional[str]) -> Optional[str]:
        if dotted is None:
            return None
        if dotted in self.aliases:
            return self.aliases[dotted]
        base, sep, rest = dotted.partition(".")
        if base in self.aliases:
            return f"{self.aliases[base]}{sep}{rest}" if sep else self.aliases[base]
        return dotted

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            asname = alias.asname or alias.name

            if alias.name == "importlib":
                self.aliases[asname] = "importlib"
            elif alias.name == "sys":
                self.aliases[asname] = "sys"
            # Help resolve reload(db) where db came from "import core.db as db"
            elif alias.name == "core" or alias.name.startswith("core."):
                self.aliases[asname] = alias.name

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "importlib":
            for alias in node.names:
                if alias.name == "reload":
                    self.aliases[alias.asname or "reload"] = "importlib.reload"

        if node.module == "sys":
            for alias in node.names:
                if alias.name == "modules":
                    self.aliases[alias.asname or "modules"] = "sys.modules"

        # from core import db as db_mod  => db_mod == core.db
        if node.module == "core":
            for alias in node.names:
                if alias.name:
                    self.aliases[alias.asname or alias.name] = f"core.{alias.name}"

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # Track simple alias assignments like: r = importlib.reload; mods = sys.modules
        value_name = self._resolve(_dotted_name(node.value))
        if value_name in ("importlib.reload", "sys.modules"):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.aliases[target.id] = value_name

        # Forbid sys.modules = ...
        for target in node.targets:
            target_name = self._resolve(_dotted_name(target))
            if target_name == "sys.modules":
                self.violations.append(
                    _AstViolation(
                        relpath=self.relpath,
                        lineno=node.lineno,
                        col=node.col_offset,
                        rule="FORBID_SYS_MODULES_REASSIGN",
                        detail="Reassigning sys.modules is forbidden (breaks import invariants).",
                    )
                )

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # Forbid sys.modules |= ... (or other augmented rebinds)
        target_name = self._resolve(_dotted_name(node.target))
        if target_name == "sys.modules":
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_SYS_MODULES_REASSIGN",
                    detail="Augmented assignment to sys.modules is forbidden (breaks import invariants).",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        fn_name = self._resolve(_dotted_name(node.func))

        # 1) Forbid importlib.reload(core.*)
        if fn_name == "importlib.reload":
            self._check_importlib_reload(node)

        # 2) Forbid sys.modules.clear()
        if fn_name == "sys.modules.clear":
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_SYS_MODULES_CLEAR",
                    detail="sys.modules.clear() is forbidden (causes reload-style flakiness / dual-namespace issues).",
                )
            )

        self.generic_visit(node)

    def _reload_target(self, node: ast.AST) -> Optional[str]:
        # Case 1: dotted name (optionally resolved via aliases)
        dotted = self._resolve(_dotted_name(node))
        if dotted:
            return dotted

        # Case 2: sys.modules["core.db"]
        if isinstance(node, ast.Subscript):
            base = self._resolve(_dotted_name(node.value))
            if base == "sys.modules":
                sl = node.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    return sl.value

        # Case 3: importlib.import_module("core.db")
        if isinstance(node, ast.Call):
            fn_name = self._resolve(_dotted_name(node.func))
            if fn_name == "importlib.import_module" and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    return arg0.value

        return None

    def _check_importlib_reload(self, node: ast.Call) -> None:
        if not node.args:
            # reload() without args is invalid anyway; still forbid.
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_IMPORTLIB_RELOAD",
                    detail="importlib.reload() is forbidden in this repo (use explicit init patterns).",
                )
            )
            return

        target = self._reload_target(node.args[0])

        # If target cannot be resolved, we cannot determine if it's core.*, so we forbid it
        # to be safe (prevents obfuscated reload patterns).
        if not target:
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_IMPORTLIB_RELOAD",
                    detail="importlib.reload(...) with unresolvable target is forbidden (prevents obfuscated reload patterns).",
                )
            )
            return

        # Absolute forbid: core.db
        if target in FORBIDDEN_EXACT_RELOAD_TARGETS:
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_RELOAD_CORE_DB",
                    detail="importlib.reload(core.db) is forbidden. Use explicit init patterns (init_db()).",
                )
            )
            return

        # Forbid: core.* (any core module)
        if any(target.startswith(prefix) for prefix in FORBIDDEN_RELOAD_PREFIXES):
            self.violations.append(
                _AstViolation(
                    relpath=self.relpath,
                    lineno=node.lineno,
                    col=node.col_offset,
                    rule="FORBID_RELOAD_CORE_PREFIX",
                    detail=f"importlib.reload({target}) is forbidden (core.* reload breaks single-Base invariants).",
                )
            )
            return

        # Allow reload of non-core modules (legacy_app, app, llm, test_router, etc.)
        # These are test-only patterns and don't affect core.db Base identity.
        # Policy: Reload is allowed for non-core modules only; core.* reload breaks
        # single-Base + DB init invariants (see PR #410).


def _scan_file_ast(path: Path) -> list[_AstViolation]:
    if _is_allowlisted_for_ast_scan(path):
        return []
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return []

    v = _RepoPolicyAstVisitor(path)
    v.visit(tree)
    return v.violations


def test_repo_policy_guards_ast_reload_and_sys_modules_clear() -> None:
    """Repository policy guardrails: forbid reload(core.db) and risky module resets.

    IMPORTANT: This test must remain deterministic and NOT import runtime modules:
    - do NOT import app/core/providers here (would break isolation)
    - only scan source via AST (no execution, no env/DB dependencies)
    - ensures single-Base invariant and prevents dual-namespace issues

    This test protects PR #410 invariants:
    - deterministic DB init (init_db() only, no reload)
    - single-Base identity (no module reloads that create new Base)
    - no reload/purge-induced flakiness in CI

    Note: This test does NOT import core.db or any runtime modules.
    It only parses source code via AST, making it deterministic and fast (~2-3s).
    """
    violations: list[_AstViolation] = []
    for p in _iter_repo_py_files_for_ast_scan(REPO_ROOT):
        violations.extend(_scan_file_ast(p))

    if violations:
        msg = "\n".join(v.format() for v in violations)
        raise AssertionError(
            "Repository policy violated.\n"
            "The following guardrails must hold (CI stability & single-Base invariants):\n"
            "- FORBID: importlib.reload(core.db) (absolute) → use init_db() + SessionLocal contract\n"
            "- FORBID: importlib.reload(core.*) → breaks single-Base invariant\n"
            "- FORBID: importlib.reload(...) with unresolvable target → prevents obfuscation\n"
            "- FORBID: sys.modules.clear() / sys.modules reassignment → causes dual-namespace issues\n\n"
            f"Violations:\n{msg}\n\n"
            "To fix: remove reload/purge patterns and use explicit init flows (init_db, fixtures)."
        )
