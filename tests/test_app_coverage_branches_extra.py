from dataclasses import FrozenInstanceError

import pytest

from app.services import pro_nutrition_plate as plate_service


def test_plate_dependencies_are_resolved_per_call() -> None:
    """Production dependency sets are fresh and bound to canonical modules."""
    first = plate_service._default_dependencies()
    second = plate_service._default_dependencies()

    assert first is not second
    assert first.make_plate is plate_service.nutrition_plate.make_plate
    assert first.calculate_all_bmr is plate_service.nutrition_bmr.calculate_all_bmr
    assert first.calculate_all_tdee is plate_service.nutrition_bmr.calculate_all_tdee


def test_plate_dependencies_are_immutable_without_facade_registry() -> None:
    """Dependency overrides cannot mutate process-global Plate behavior."""
    dependencies = plate_service._default_dependencies()

    with pytest.raises(FrozenInstanceError):
        setattr(dependencies, "make_plate", None)

    assert not hasattr(plate_service, "_plate_deps")
    assert not hasattr(plate_service, "_targets_disabled_cache")
