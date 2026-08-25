"""Deterministic regression proof for Alembic package and migration-tree ownership."""

from __future__ import annotations

import ast
import configparser
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
CONTROLLED_CHILD_ENV = {
    "APP_ENV": "test",
    "ENVIRONMENT": "test",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONNOUSERSITE": "1",
    "TESTING": "true",
    "TZ": "UTC",
}
FORBIDDEN_CHILD_ENV_KEYS = (
    "BASH_ENV",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "ENV",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "PULSEPLATE_SENTINEL_SECRET",
    "PYTHONHOME",
    "PYTHONINSPECT",
    "PYTHONPATH",
    "PYTHONPLATLIBDIR",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
)


def _tail(value: str, *, limit: int = 4000) -> str:
    return value[-limit:]


def _database_url_redactions(env: dict[str, str]) -> tuple[str, ...]:
    database_url = env.get("DATABASE_URL", "")
    if not database_url:
        return ()
    parsed = urlsplit(database_url)
    encoded_password = parsed.password or ""
    decoded_password = unquote(encoded_password)
    return tuple(
        value
        for value in dict.fromkeys((database_url, encoded_password, decoded_password))
        if value
    )


def _redact_output(value: str, redactions: tuple[str, ...]) -> str:
    sanitized = value
    for redaction in sorted(redactions, key=len, reverse=True):
        sanitized = sanitized.replace(redaction, "[REDACTED]")
    return sanitized


def _run_python(
    arguments: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        redactions = _database_url_redactions(env)
        pytest.fail(
            "Child Python command failed "
            f"(rc={completed.returncode})\n"
            f"stdout tail:\n{_tail(_redact_output(completed.stdout, redactions))}\n"
            f"stderr tail:\n{_tail(_redact_output(completed.stderr, redactions))}"
        )
    return completed


def _controlled_env(*, pythonpath: str | None) -> dict[str, str]:
    env = dict(CONTROLLED_CHILD_ENV)
    if pythonpath is not None:
        env["PYTHONPATH"] = pythonpath
    return env


def _script_heads() -> tuple[str, ...]:
    scripts = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    return tuple(scripts.get_heads())


def _sqlite_state(path: Path) -> tuple[tuple[str, ...], int]:
    with sqlite3.connect(path) as connection:
        versions = tuple(
            row[0]
            for row in connection.execute(
                "SELECT version_num FROM alembic_version ORDER BY version_num"
            )
        )
        schema_version = int(connection.execute("PRAGMA schema_version").fetchone()[0])
    return versions, schema_version


def _migration_tree_symlinks(root: Path) -> tuple[Path, ...]:
    return tuple(path for path in root.rglob("*") if path.is_symlink())


def test_migration_tree_has_no_top_level_regular_package_carrier() -> None:
    assert not (REPO_ROOT / "alembic/__init__.py").exists()
    assert (REPO_ROOT / "alembic/versions/__init__.py").is_file()


def test_current_repository_carriers_are_regular_and_migration_tree_has_no_symlinks() -> None:
    migration_root = REPO_ROOT / "alembic"
    assert migration_root.is_dir()
    assert not migration_root.is_symlink()
    assert migration_root.resolve() == migration_root
    assert _migration_tree_symlinks(migration_root) == ()

    for carrier in (
        REPO_ROOT / "app/__init__.py",
        REPO_ROOT / "core/__init__.py",
        REPO_ROOT / "settings.py",
    ):
        assert carrier.is_file()
        assert not carrier.is_symlink()
        assert carrier.resolve().is_relative_to(REPO_ROOT)


def test_migration_tree_symlink_census_detects_nested_carrier(tmp_path: Path) -> None:
    migration_root = tmp_path / "alembic"
    migration_root.mkdir()
    target = tmp_path / "outside.py"
    target.write_text("outside = True\n", encoding="utf-8")
    link = migration_root / "linked.py"
    link.symlink_to(target)

    assert _migration_tree_symlinks(migration_root) == (link,)


@pytest.mark.parametrize("variable", FORBIDDEN_CHILD_ENV_KEYS)
def test_controlled_child_environment_does_not_inherit_startup_or_secret_carriers(
    variable: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(variable, "sentinel-value")

    env = _controlled_env(pythonpath=None)

    assert variable not in env
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONHASHSEED"] == "0"
    assert env["APP_ENV"] == "test"
    assert env["ENVIRONMENT"] == "test"
    assert env["TESTING"] == "true"


def test_child_failure_diagnostics_redact_database_url_and_password(tmp_path: Path) -> None:
    credentialed_url = "postgresql+psycopg://migration_user:decoded%40password@localhost:5432/migration_db"  # pragma: allowlist secret
    env = _controlled_env(pythonpath=None)
    env["DATABASE_URL"] = credentialed_url
    probe = r"""
import os
import sys
from urllib.parse import unquote, urlsplit

database_url = os.environ["DATABASE_URL"]
sys.stdout.write(database_url)
sys.stderr.write(unquote(urlsplit(database_url).password or ""))
raise SystemExit(7)
"""

    with pytest.raises(pytest.fail.Exception) as failure:
        _run_python(["-c", probe], cwd=tmp_path, env=env)

    message = str(failure.value)
    assert credentialed_url not in message
    assert "decoded%40password" not in message
    assert "decoded@password" not in message
    assert "[REDACTED]" in message


def test_alembic_config_declares_repository_import_path() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ALEMBIC_INI, encoding="utf-8")

    assert parser.get("alembic", "script_location") == "alembic"
    assert parser.get("alembic", "prepend_sys_path") == "%(here)s"
    assert parser.get("alembic", "path_separator") == "os"


def test_migration_environment_uses_normal_package_imports_only() -> None:
    env_path = REPO_ROOT / "alembic/env.py"
    source = env_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(env_path))

    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "sys" not in imported_modules
    assert "sys.path" not in source
    assert "ROOT_DIR" not in source
    assert "noqa: E402" not in source


def test_installed_alembic_and_repository_modules_have_distinct_owners() -> None:
    probe = r"""
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sysconfig

modules = ("alembic", "alembic.config", "alembic.context", "alembic.op")
origins = {}
for name in modules + ("app", "core", "settings"):
    spec = importlib.util.find_spec(name)
    origins[name] = str(Path(spec.origin or "").resolve()) if spec is not None else None
distribution = importlib.metadata.distribution("alembic")
print(json.dumps({
    "origins": origins,
    "purelib": str(Path(sysconfig.get_path("purelib")).resolve()),
    "distribution_root": str(Path(distribution.locate_file("")).resolve()),
    "alembic_root": str(Path(distribution.locate_file("alembic")).resolve()),
}, sort_keys=True))
"""
    completed = _run_python(
        ["-c", probe],
        cwd=REPO_ROOT,
        env=_controlled_env(pythonpath=str(REPO_ROOT)),
    )
    payload: dict[str, Any] = json.loads(completed.stdout)
    origins = payload["origins"]
    purelib = Path(payload["purelib"])
    distribution_root = Path(payload["distribution_root"])
    installed_alembic_root = Path(payload["alembic_root"])

    assert distribution_root == purelib
    assert installed_alembic_root.is_relative_to(purelib)
    for module_name in ("alembic", "alembic.config", "alembic.context", "alembic.op"):
        assert Path(origins[module_name]).is_relative_to(installed_alembic_root)
        assert not Path(origins[module_name]).is_relative_to(REPO_ROOT / "alembic")
    assert Path(origins["app"]) == (REPO_ROOT / "app/__init__.py").resolve()
    assert Path(origins["core"]) == (REPO_ROOT / "core/__init__.py").resolve()
    assert Path(origins["settings"]) == (REPO_ROOT / "settings.py").resolve()


def test_old_top_level_package_carrier_recreates_the_collision(tmp_path: Path) -> None:
    package_root = tmp_path / "alembic"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("# old repository carrier\n", encoding="utf-8")
    probe = r"""
import importlib.util
import json
from pathlib import Path

parent = importlib.util.find_spec("alembic")
try:
    child = importlib.util.find_spec("alembic.config")
except ModuleNotFoundError:
    child = None
print(json.dumps({
    "parent": str(Path(parent.origin or "").resolve()) if parent is not None else None,
    "child": child is not None,
}, sort_keys=True))
"""
    completed = _run_python(
        ["-c", probe],
        cwd=tmp_path,
        env=_controlled_env(pythonpath=str(tmp_path)),
    )
    payload = json.loads(completed.stdout)

    assert Path(payload["parent"]) == (package_root / "__init__.py").resolve()
    assert payload["child"] is False


def test_fresh_sqlite_upgrade_current_and_second_upgrade_are_deterministic(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "alembic-contract.sqlite3"
    database_url = f"sqlite:///{database_path.as_posix()}"
    env = _controlled_env(pythonpath=None)
    env["DATABASE_URL"] = database_url
    command_prefix = ["-m", "alembic", "-c", str(ALEMBIC_INI)]

    _run_python([*command_prefix, "upgrade", "head"], cwd=REPO_ROOT, env=env)
    heads = _script_heads()
    assert len(heads) == 1
    assert heads[0]
    first_state = _sqlite_state(database_path)
    assert first_state[0] == heads

    current = _run_python(
        [*command_prefix, "current", "--check-heads"],
        cwd=REPO_ROOT,
        env=env,
    )
    assert heads[0] in current.stdout

    _run_python([*command_prefix, "upgrade", "head"], cwd=REPO_ROOT, env=env)
    assert _sqlite_state(database_path) == first_state


def test_final_image_guard_is_in_production_non_root_stage() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    production = dockerfile.split("FROM runtime-base AS production", maxsplit=1)[1]
    guard_start = production.index("# ALEMBIC-IMPORT-OWNERSHIP-GUARD-START")
    guard_end = production.index("# ALEMBIC-IMPORT-OWNERSHIP-GUARD-END")
    staging_start = production.index("FROM production AS staging")
    final_user = production.rindex("USER pulseplate", 0, guard_start)
    guard = production[guard_start:guard_end]

    assert final_user < guard_start < guard_end < staging_start
    assert "USER root" not in production[final_user:guard_start]
    assert "RUN /opt/venv/bin/python - <<'PY'" in guard
    assert 'literal_app_root = Path("/app")' in guard
    assert 'literal_migration_root = Path("/app/alembic")' in guard
    assert "path.is_symlink() or not path.is_dir()" in guard
    assert "app_root != literal_app_root" in guard
    assert "migration_root != literal_migration_root" in guard
    assert "migration_root.is_relative_to(app_root)" in guard
    assert 'migration_root.rglob("*")' in guard
    assert "if path.is_symlink()" in guard
    assert "venv_root = Path(sys.prefix).resolve()" in guard
    assert 'if venv_root != Path("/opt/venv"):' in guard
    assert 'importlib.metadata.distribution("alembic")' in guard
    assert 'sysconfig.get_path("purelib")' in guard
    assert "ScriptDirectory.from_config(config)" in guard
    assert "len(heads) != 1" in guard
    assert "if package_carrier.exists() or package_carrier.is_symlink():" in guard
    assert 'migration_root.rglob("__pycache__")' in guard
    assert 'migration_root.rglob("*.pyc")' in guard
    assert 'migration_root.rglob("*.pyo")' in guard
    assert "RUN /opt/venv/bin/alembic -c /app/alembic.ini heads" in guard
    assert all(name in guard for name in ("alembic.config", "alembic.context", "alembic.op"))
    assert all(name in guard for name in ('"app"', '"core"', '"settings"'))
    assert "not expected_origin.is_file() or expected_origin.is_symlink()" in guard
    assert "upgrade" not in guard.lower()
    assert "DATABASE_URL" not in guard
    assert "urllib" not in guard
    assert "socket" not in guard
    assert re.search(r"python3\.\d+", guard) is None


def test_docker_context_excludes_python_bytecode_after_allowlists() -> None:
    lines = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    allowlist_end = lines.index("!bodyfat.py")

    for pattern in ("**/__pycache__/", "**/*.pyc", "**/*.pyo"):
        assert lines.index(pattern) > allowlist_end
