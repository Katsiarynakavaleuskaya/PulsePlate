"""Guard test: ensure app module maintains legacy public API surface.

This test prevents accidental removal of backward-compatible exports that
6000+ tests depend on. Only modify if intentionally breaking the public API.
"""


def test_app_public_surface_smoke() -> None:
    """Verify app module exports core legacy API symbols."""
    import app

    # Core FastAPI instance
    assert hasattr(app, "app"), "app.app (FastAPI instance) must be exported"

    # Key legacy functions used across test suite
    assert hasattr(app, "get_api_key"), "app.get_api_key must be exported"
    assert hasattr(app, "lifespan"), "app.lifespan must be exported"

    # Schemas commonly imported by tests
    assert hasattr(app, "BMIRequest"), "app.BMIRequest must be exported"

    # Internal utilities (used by legacy tests)
    assert hasattr(app, "_is_truthy"), "app._is_truthy must be exported"
    assert hasattr(app, "_macros_to_kcal"), "app._macros_to_kcal must be exported"

    # Core utilities (added in import hygiene PR)
    assert hasattr(app, "resolve_attr"), "app.resolve_attr must be exported"
    assert hasattr(app, "make_weekly_menu"), "app.make_weekly_menu must be exported"
    assert hasattr(app, "build_nutrition_targets"), "app.build_nutrition_targets must be exported"
    assert hasattr(app, "get_update_scheduler"), "app.get_update_scheduler must be exported"

    # Visualization flags (optional but must be present)
    assert hasattr(app, "MATPLOTLIB_AVAILABLE"), "app.MATPLOTLIB_AVAILABLE must be exported"
    assert hasattr(
        app, "generate_bmi_visualization"
    ), "app.generate_bmi_visualization must be exported"

    # Observability endpoints (for patch-based tests)
    assert hasattr(app, "metrics"), "app.metrics must be exported (for patch('app.metrics'))"


def test_no_dynamic_exec_module_in_app_package() -> None:
    """Prevent regression to dynamic import patterns (spec.loader.exec_module).

    Import hygiene PR #403 eliminated these anti-patterns. This test ensures
    they never return.
    """
    import pathlib

    app_init = pathlib.Path("app/__init__.py").read_text(encoding="utf-8")

    # No dynamic module execution
    assert "exec_module" not in app_init, "app/__init__.py must not use exec_module"
    assert (
        "spec_from_file_location" not in app_init
    ), "app/__init__.py must not use spec_from_file_location"

    # __getattr__ is allowed for PEP 562 forwarding to legacy_app
    # (standard pattern for backward-compatible module aliasing)


def test_dockerfile_uses_legacy_app_not_app_py() -> None:
    """Verify Dockerfile copies legacy_app.py (not app.py which was renamed)."""
    import pathlib

    dockerfile = pathlib.Path("Dockerfile").read_text(encoding="utf-8")

    # Should copy legacy_app.py
    assert "legacy_app.py" in dockerfile, "Dockerfile must COPY legacy_app.py"

    # Should NOT copy app.py (renamed file)
    assert (
        "COPY --chown=pulseplate:pulseplate app.py" not in dockerfile
    ), "Dockerfile must not COPY app.py (file renamed to legacy_app.py)"
