"""Targeted production-invariant coverage for extracted application services."""


class TestAppErrorPaths97:
    """Tests for app.py error paths and edge cases."""

    def test_plate_service_has_no_mutable_global_registry(self) -> None:
        """Canonical Plate dependencies are call-scoped, not process-global."""
        from app.services import pro_nutrition_plate

        assert not hasattr(pro_nutrition_plate, "_plate_deps")
        assert not hasattr(pro_nutrition_plate, "_targets_disabled_cache")
