def test_app_main_import_smoke() -> None:
    """Smoke: importing canonical app entrypoint should succeed."""
    import app.main  # noqa: F401


def test_app_main_exposes_tracing_bootstrap() -> None:
    """Canonical app module should expose tracing bootstrap wiring."""

    import app.bootstrap

    assert hasattr(app.bootstrap, "register_tracing")
