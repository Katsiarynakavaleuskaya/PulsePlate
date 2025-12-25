def test_app_main_import_smoke() -> None:
    """Smoke: importing canonical app entrypoint should succeed."""
    import app.main  # noqa: F401
