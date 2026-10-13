from __future__ import annotations

import asyncio
import importlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from fastapi import HTTPException

REPO_ROOT = Path(__file__).resolve().parents[1]
_PROBE_CREDENTIAL_NAMES = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
    "API_KEY",
    "PULSEPLATE_PYTHON_INDEX_URL",
    "FIGMA_ACCESS_TOKEN",
)
_NETWORK_DISABLED_PREAMBLE = textwrap.dedent("""
    import socket

    def _deny_network(*_args, **_kwargs):
        raise AssertionError("network access is disabled for application probe")

    class _NetworkDisabledSocket(socket.socket):
        def connect(self, *_args, **_kwargs):
            _deny_network()

        def connect_ex(self, *_args, **_kwargs):
            _deny_network()

    socket.create_connection = _deny_network
    socket.socket = _NetworkDisabledSocket
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    except AssertionError:
        pass
    else:
        raise AssertionError("application probe connection denial missing")
    with socket.socket() as transport:
        for connect in (transport.connect, transport.connect_ex):
            try:
                connect(("127.0.0.1", 9))
            except AssertionError:
                pass
            else:
                raise AssertionError("application probe socket denial missing")
    """)


def _run_application_probe(
    runtime_env: str,
    *,
    path_present: bool = True,
    pytest_marker: bool = False,
    include_main: bool = False,
    enable_test_routes: bool = False,
    post_bootstrap_env: str | None = None,
) -> dict[str, object]:
    """Observe canonical initialization with finite inputs and safe child diagnostics."""
    main_probe = (
        """
        import app.main as app_main
        from app.effective_routes import iter_effective_route_candidates, route_path
        has_test_route = any(
            route_path(route) == "/api/v1/test/health"
            for route in iter_effective_route_candidates(app_main.app.routes)
        )
        """
        if include_main
        else "has_test_route = None"
    )
    scenario = textwrap.dedent(f"""
        import json
        import logging
        import os
        import sys
        import dotenv
        import fastapi
        import settings
        assert "app.bootstrap.application" not in sys.modules
        assert "legacy_app" not in sys.modules
        assert os.environ["ENVIRONMENT"] == {runtime_env!r}
        credential_free = not any(name in os.environ for name in {_PROBE_CREDENTIAL_NAMES!r})
        assert credential_free
        assert "HOME" not in os.environ and "TESTING" not in os.environ
        counts = {{"resolver": 0, "metadata": 0, "app": 0, "dotenv": 0, "logging": 0}}
        events = []
        original_resolver = settings.get_runtime_env_name
        def resolve_env(*args, **kwargs):
            counts["resolver"] += 1
            events.append("resolver")
            return original_resolver(*args, **kwargs)
        settings.get_runtime_env_name = resolve_env
        import app.application_metadata as metadata_module
        original_factory = metadata_module.build_application_metadata
        def build_metadata(*args, **kwargs):
            counts["metadata"] += 1
            events.append("metadata")
            return original_factory(*args, **kwargs)
        metadata_module.build_application_metadata = build_metadata
        original_fastapi = fastapi.FastAPI
        def create_app(*args, **kwargs):
            counts["app"] += 1
            events.append("app")
            return original_fastapi(*args, **kwargs)
        fastapi.FastAPI = create_app
        original_logging = logging.basicConfig
        def configure_logging(*args, **kwargs):
            counts["logging"] += 1
            events.append("logging")
            return original_logging(*args, **kwargs)
        logging.basicConfig = configure_logging
        def load_dotenv(*args, **kwargs):
            counts["dotenv"] += 1
            events.append("dotenv")
        dotenv.load_dotenv = load_dotenv
        from app.bootstrap import application
        baseline_counts = dict(counts)
        baseline_events = list(events)
        assert baseline_counts["resolver"] > 0
        startup_env = application.RUNTIME_ENV
        startup_metadata = application.APPLICATION_METADATA
        startup_app = application.app
        if {post_bootstrap_env!r} is not None:
            os.environ["ENVIRONMENT"] = {post_bootstrap_env!r}
        import legacy_app
        setup_unchanged = counts == baseline_counts and events == baseline_events
        same_app = legacy_app.app is application.app is startup_app
        metadata_snapshot = (
            application.APPLICATION_METADATA is startup_metadata
            and application.RUNTIME_ENV == startup_env
            and application.app.description == startup_metadata.description
        )
        root_level = logging.getLevelName(logging.getLogger().level)
        assert setup_unchanged and same_app and metadata_snapshot
        fastapi.FastAPI = original_fastapi
        {main_probe}
        print("ENV_RESULT=" + json.dumps({{
            "calls": baseline_counts["dotenv"],
            "runtime_env": startup_env,
            "root_level": root_level,
            "has_test_route": has_test_route,
            "same_app": same_app,
            "metadata_snapshot": metadata_snapshot,
            "setup_unchanged": setup_unchanged,
            "setup_counts": baseline_counts,
            "setup_order": baseline_events,
            "credential_free": credential_free,
        }}, sort_keys=True))
    """)
    passthrough_names = ("LANG", "LC_ALL", "PATH", "PYTHONIOENCODING", "PYTHONUTF8", "TMPDIR")
    env = {name: value for name in passthrough_names if (value := os.environ.get(name)) is not None}
    env.update({"ENVIRONMENT": runtime_env, "PRIVATE_EXPORTS_ENABLED": "false"})
    if not path_present:
        env.pop("PATH", None)
    if pytest_marker:
        env["PYTEST_CURRENT_TEST"] = "ownership-probe"
    if enable_test_routes:
        env["ENABLE_TEST_ROUTES"] = "1"
    try:
        completed = subprocess.run(
            [sys.executable, "-c", _NETWORK_DISABLED_PREAMBLE + scenario],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=30,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        raise AssertionError("application probe timed out") from None
    except OSError:
        raise AssertionError("application probe process unavailable") from None
    if completed.returncode != 0:
        raise AssertionError(f"application probe failed: exit={completed.returncode}")
    result_lines = [
        line for line in completed.stdout.splitlines() if line.startswith("ENV_RESULT=")
    ]
    if len(result_lines) != 1 or len(result_lines[0]) > 2048:
        raise AssertionError("application probe result marker invalid")
    try:
        result = json.loads(result_lines[0].removeprefix("ENV_RESULT="))
    except (ValueError, RecursionError):
        raise AssertionError("application probe result JSON invalid") from None
    expected_keys = {
        "calls",
        "runtime_env",
        "root_level",
        "has_test_route",
        "same_app",
        "metadata_snapshot",
        "setup_unchanged",
        "setup_counts",
        "setup_order",
        "credential_free",
    }
    if type(result) is not dict or set(result) != expected_keys:
        raise AssertionError("application probe result fields invalid")
    if (
        type(result["calls"]) is not int
        or result["calls"] not in {0, 1}
        or type(result["runtime_env"]) is not str
        or result["runtime_env"]
        not in {
            "local",
            "dev",
            "development",
            "production",
            "staging",
            "test",
            "testing",
            "unknown",
        }
        or type(result["root_level"]) is not str
        or result["root_level"] not in {"INFO", "DEBUG"}
        or not (result["has_test_route"] is None or type(result["has_test_route"]) is bool)
        or any(
            type(result[key]) is not bool
            for key in ("same_app", "metadata_snapshot", "setup_unchanged", "credential_free")
        )
    ):
        raise AssertionError("application probe result values invalid")
    counts = result["setup_counts"]
    if (
        type(counts) is not dict
        or set(counts) != {"resolver", "metadata", "app", "dotenv", "logging"}
        or any(type(value) is not int or not 0 <= value <= 8 for value in counts.values())
    ):
        raise AssertionError("application probe initialization counts invalid")
    order = result["setup_order"]
    if (
        type(order) is not list
        or not 1 <= len(order) <= 16
        or any(type(event) is not str or event not in counts for event in order)
    ):
        raise AssertionError("application probe initialization order invalid")
    return result


@pytest.fixture(autouse=True)
def _reset_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep env-based legacy app tests deterministic.

    RU: Жёстко изолируем env, чтобы legacy import-time gates читали только
    нужные значения текущего теста.
    EN: Hard-isolate env so legacy import-time gates only see the values set by
    the current test.
    """

    for name in (
        "APP_ENV",
        "ENVIRONMENT",
        "ENV",
        "ENABLE_TEST_ROUTES",
        "ENABLE_DEBUG_ENDPOINT",
        "PYTEST_CURRENT_TEST",
        "DEBUG",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    ("runtime_env", "dotenv_calls", "root_level"),
    (
        ("local", 1, "INFO"),
        ("dev", 1, "INFO"),
        ("development", 1, "INFO"),
        ("production", 0, "INFO"),
        ("staging", 0, "INFO"),
        ("test", 0, "DEBUG"),
        ("testing", 0, "DEBUG"),
        ("unknown", 0, "INFO"),
    ),
)
def test_canonical_application_owns_environment_setup(
    runtime_env: str, dotenv_calls: int, root_level: str
) -> None:
    result = _run_application_probe(runtime_env)
    assert result["calls"] == dotenv_calls
    assert result["runtime_env"] == runtime_env
    assert result["root_level"] == root_level
    assert result["has_test_route"] is None
    assert result["same_app"] is True
    assert result["metadata_snapshot"] is True
    assert result["setup_unchanged"] is True
    assert result["credential_free"] is True
    counts = result["setup_counts"]
    assert isinstance(counts, dict)
    assert counts["resolver"] > 0
    assert counts["metadata"] == counts["app"] == counts["logging"] == 1
    assert counts["dotenv"] == dotenv_calls
    order = result["setup_order"]
    assert isinstance(order, list)
    assert order[0] == "resolver"
    assert order[-3:] == ["logging", "metadata", "app"]
    if dotenv_calls:
        assert order.index("dotenv") < order.index("logging")


@pytest.mark.parametrize(
    ("path_present", "pytest_marker"),
    ((False, False), (True, True)),
)
def test_local_dotenv_gate_requires_path_and_non_pytest(
    path_present: bool, pytest_marker: bool
) -> None:
    assert (
        _run_application_probe("local", path_present=path_present, pytest_marker=pytest_marker)[
            "calls"
        ]
        == 0
    )


def test_canonical_bootstrap_staging_test_router_respects_environment_flag() -> None:
    assert _run_application_probe("staging", include_main=True)["has_test_route"] is False
    assert (
        _run_application_probe("staging", include_main=True, enable_test_routes=True)[
            "has_test_route"
        ]
        is True
    )


def test_debug_env_uses_environment_when_app_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENABLE_DEBUG_ENDPOINT", raising=False)

    from app.services import admin_operations

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(admin_operations.debug_env())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Not found"

    monkeypatch.setenv("ENABLE_DEBUG_ENDPOINT", "true")
    response = asyncio.run(admin_operations.debug_env())

    assert response.status_code == 200
    assert set(json.loads(response.body)) == {
        "FEATURE_INSIGHT",
        "LLM_PROVIDER",
        "PERPLEXITY_MODEL",
        "PERPLEXITY_ENDPOINT",
        "insight_enabled",
    }


def test_health_prefers_environment_over_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "local")

    health_module = importlib.import_module("app.routers.health")
    response = asyncio.run(health_module.health())
    assert response["environment"] == "production"


def test_test_router_request_gate_prefers_environment_over_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "local")

    from app.routers import test as test_router

    importlib.reload(test_router)

    with pytest.raises(HTTPException) as exc_info:
        test_router._ensure_non_production()

    assert exc_info.value.status_code == 404


def test_test_router_request_gate_blocks_staging_without_enable_even_if_app_env_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("APP_ENV", "local")

    from app.routers import test as test_router

    importlib.reload(test_router)

    with pytest.raises(HTTPException) as exc_info:
        test_router._ensure_non_production()

    assert exc_info.value.status_code == 404

    monkeypatch.setenv("ENABLE_TEST_ROUTES", "1")
    importlib.reload(test_router)
    test_router._ensure_non_production()


@pytest.mark.parametrize(
    "initial_env, changed_env",
    (
        ("production", "development"),
        ("development", "production"),
    ),
)
def test_legacy_import_preserves_bootstrap_snapshot_after_environment_change(
    initial_env: str,
    changed_env: str,
) -> None:
    result = _run_application_probe(initial_env, post_bootstrap_env=changed_env)
    assert result["runtime_env"] == initial_env
    assert result["same_app"] is True
    assert result["metadata_snapshot"] is True
    assert result["setup_unchanged"] is True
    assert result["root_level"] == "INFO"


def test_application_probe_excludes_ambient_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _PROBE_CREDENTIAL_NAMES:
        monkeypatch.setenv(name, "synthetic-credential-must-not-enter-child")
    monkeypatch.setenv("HOME", "/synthetic-home-must-not-enter-child")
    monkeypatch.setenv("TESTING", "true")
    result = _run_application_probe("production")
    assert result["credential_free"] is True
    assert result["runtime_env"] == "production"
    assert result["setup_unchanged"] is True


@pytest.mark.parametrize(
    "failure",
    (
        "exit",
        "missing",
        "duplicate",
        "json",
        "fields",
        "values",
        "counts",
        "order",
        "timeout",
        "process",
    ),
)
def test_application_probe_failure_diagnostics_exclude_child_payload(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    sentinel = "synthetic-sensitive-child-payload"
    valid: dict[str, object] = {
        "calls": 0,
        "runtime_env": "production",
        "root_level": "INFO",
        "has_test_route": None,
        "same_app": True,
        "metadata_snapshot": True,
        "setup_unchanged": True,
        "setup_counts": {"resolver": 1, "metadata": 1, "app": 1, "dotenv": 0, "logging": 1},
        "credential_free": True,
        "setup_order": ["resolver", "logging", "metadata", "app"],
    }
    if failure == "fields":
        valid[sentinel] = sentinel
    if failure == "values":
        valid["runtime_env"] = sentinel
    if failure == "counts":
        valid["setup_counts"] = {
            "resolver": True,
            "metadata": 1,
            "app": 1,
            "dotenv": 0,
            "logging": 1,
        }
    if failure == "order":
        valid["setup_order"] = [sentinel]
    stdout = "ENV_RESULT=" + json.dumps(valid)
    if failure == "missing":
        stdout = sentinel
    elif failure == "duplicate":
        stdout += "\n" + stdout
    elif failure == "json":
        stdout = "ENV_RESULT=" + sentinel

    def run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if failure == "process":
            raise OSError(sentinel)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(sentinel, 30, output=sentinel, stderr=sentinel)
        return subprocess.CompletedProcess(
            args=sentinel,
            returncode=1 if failure == "exit" else 0,
            stdout=stdout,
            stderr=sentinel,
        )

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(AssertionError) as caught:
        _run_application_probe("production")
    assert sentinel not in str(caught.value)
    if failure in {"json", "timeout", "process"}:
        assert caught.value.__suppress_context__ is True
