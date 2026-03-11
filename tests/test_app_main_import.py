import importlib
import subprocess
import sys
import textwrap


def test_app_main_import_smoke() -> None:
    """Smoke: importing canonical app entrypoint should succeed."""
    import app.main  # noqa: F401


def test_app_main_exposes_tracing_bootstrap() -> None:
    """Canonical app module should expose tracing bootstrap wiring."""

    import app.bootstrap

    assert hasattr(app.bootstrap, "register_tracing")


def test_app_main_late_import_restores_metrics_route() -> None:
    """Late canonical bootstrap must restore /metrics after app-first stack build."""

    scenario = textwrap.dedent("""
        import importlib

        from fastapi.testclient import TestClient

        app_package = importlib.import_module("app")

        with TestClient(app_package.app) as client:
            health_response = client.get("/health")
            assert health_response.status_code == 200
            assert client.app.middleware_stack is not None

        main_module = importlib.import_module("app.main")

        with TestClient(main_module.app) as client:
            metrics_response = client.get("/metrics")
            assert metrics_response.status_code == 200
        """)

    result = subprocess.run(
        [sys.executable, "-c", scenario],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
