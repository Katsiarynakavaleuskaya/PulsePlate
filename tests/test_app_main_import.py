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


def test_app_facade_then_main_preserves_metrics_route() -> None:
    """Package facade and canonical main preserve metrics across managed lifecycles."""

    scenario = textwrap.dedent("""
        import importlib

        app_package = importlib.import_module("app")
        open_test_client = importlib.import_module("tests._client").open_test_client

        with open_test_client(app_package.app) as client:
            health_response = client.get("/health")
            assert health_response.status_code == 200
            assert client.app.middleware_stack is not None

        main_module = importlib.import_module("app.main")

        with open_test_client(main_module.app) as client:
            metrics_response = client.get(
                "/metrics",
                headers={"X-API-Key": "test_key"},
            )
            assert metrics_response.status_code == 200
        """)

    result = subprocess.run(
        [sys.executable, "-c", scenario],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
