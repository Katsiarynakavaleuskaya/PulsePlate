# -*- coding: utf-8 -*-
"""Unit tests for ShoplistEngine orchestrator.

RU: Модульные тесты для ShoplistEngine orchestrator.
EN: Unit tests for ShoplistEngine orchestrator.

These tests validate pipeline wiring, determinism, and error propagation
without re-testing lower-layer business logic.

RU: Эти тесты проверяют связывание пайплайна, детерминизм и проброс ошибок
без перепроверки бизнес-логики нижних слоёв.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import pytest

from core.shoplist_engine.engine import ShoplistEngine, generate_shoplist


@dataclass(frozen=True)
class _Spec:
    """Fake spec for testing wiring (not real IngredientSpec)."""

    food_id: str
    qty: int
    unit: str


@dataclass(frozen=True)
class _Rule:
    """Fake rule for testing wiring (not real PackageRule)."""

    food_id: str
    pack_size: int
    unit: str


@dataclass(frozen=True)
class _Result:
    """Fake result for testing wiring (not real PackagingResult)."""

    packed: tuple[Any, ...]
    unpacked: tuple[Any, ...]


def test_engine_pipeline_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that engine calls normalize → aggregate → package in correct order."""
    calls: list[str] = []

    def fake_normalize(specs: Sequence[_Spec]) -> list[_Spec]:
        calls.append("normalize")
        return list(specs)

    def fake_aggregate(specs: Sequence[_Spec]) -> list[_Spec]:
        calls.append("aggregate")
        return list(specs)

    def fake_package(lines: Sequence[_Spec], packaging_rules: Sequence[_Rule]) -> _Result:
        calls.append("package")
        # возвращаем что-то детерминированное
        return _Result(packed=tuple(lines), unpacked=tuple(packaging_rules))

    # Подменяем функции внутри модуля engine
    monkeypatch.setattr("core.shoplist_engine.engine.normalize_specs", fake_normalize)
    monkeypatch.setattr("core.shoplist_engine.engine.aggregate_specs", fake_aggregate)
    monkeypatch.setattr("core.shoplist_engine.engine.apply_packaging", fake_package)

    specs = [_Spec(food_id="A", qty=0, unit="G")]
    rules = [_Rule(food_id="A", pack_size=100, unit="G")]

    out = ShoplistEngine.generate(specs, packaging_rules=rules)  # type: ignore[arg-type]

    assert calls == ["normalize", "aggregate", "package"]
    assert out == _Result(packed=tuple(specs), unpacked=tuple(rules))


def test_engine_determinism_same_input_same_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that engine produces deterministic output for same inputs."""

    def fake_normalize(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_aggregate(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_assemble(lines: Sequence[_Spec], packaging_rules: Sequence[_Rule]) -> _Result:
        # детерминированная сортировка по food_id
        packed = tuple(sorted(lines, key=lambda x: x.food_id))
        unpacked = tuple(sorted(packaging_rules, key=lambda x: x.food_id))
        return _Result(packed=packed, unpacked=unpacked)

    monkeypatch.setattr("core.shoplist_engine.engine.normalize_specs", fake_normalize)
    monkeypatch.setattr("core.shoplist_engine.engine.aggregate_specs", fake_aggregate)
    monkeypatch.setattr("core.shoplist_engine.engine.apply_packaging", fake_assemble)

    specs = [_Spec("B", 1, "G"), _Spec("A", 0, "G")]
    rules = [_Rule("B", 100, "G"), _Rule("A", 100, "G")]

    out1 = generate_shoplist(specs, packaging_rules=rules)  # type: ignore[arg-type]
    out2 = generate_shoplist(specs, packaging_rules=rules)  # type: ignore[arg-type]

    assert out1 == out2


def test_engine_zero_quantity_flows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that zero quantity passes through pipeline without being dropped."""

    # RU: Проверяем, что engine не режет zero — он просто пропускает через pipeline.
    # EN: Ensure engine doesn't drop zeros.
    def fake_normalize(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_aggregate(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_package(lines: Sequence[_Spec], packaging_rules: Sequence[_Rule]) -> _Result:  # noqa: ARG001
        # если qty=0 дошло — тест пройдёт
        assert any(s.qty == 0 for s in lines)
        return _Result(packed=tuple(lines), unpacked=())

    monkeypatch.setattr("core.shoplist_engine.engine.normalize_specs", fake_normalize)
    monkeypatch.setattr("core.shoplist_engine.engine.aggregate_specs", fake_aggregate)
    monkeypatch.setattr("core.shoplist_engine.engine.apply_packaging", fake_package)

    out = generate_shoplist([_Spec("A", 0, "G")])  # type: ignore[arg-type]
    assert len(out.packed) == 1


def test_engine_bubble_up_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that engine does not catch exceptions from lower layers."""

    class Boom(RuntimeError):
        """Test exception."""

    def fake_normalize(_: Sequence[_Spec]) -> list[_Spec]:
        raise Boom("normalize failed")

    monkeypatch.setattr("core.shoplist_engine.engine.normalize_specs", fake_normalize)

    with pytest.raises(Boom):
        generate_shoplist([_Spec("A", 1, "G")])  # type: ignore[arg-type]


def test_engine_never_catches_packager_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that packager errors bubble up through engine."""

    class PackError(ValueError):
        """Test exception."""

    def fake_normalize(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_aggregate(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_package(_: Sequence[_Spec], packaging_rules: Sequence[_Rule]) -> _Result:  # noqa: ARG001
        raise PackError("packager failed")

    monkeypatch.setattr("core.shoplist_engine.engine.normalize_specs", fake_normalize)
    monkeypatch.setattr("core.shoplist_engine.engine.aggregate_specs", fake_aggregate)
    monkeypatch.setattr("core.shoplist_engine.engine.apply_packaging", fake_package)

    with pytest.raises(PackError):
        generate_shoplist(  # type: ignore[arg-type]
            [_Spec("A", 1, "G")], packaging_rules=[_Rule("A", 100, "G")]
        )


def test_engine_empty_specs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that engine handles empty specs gracefully."""

    def fake_normalize(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_aggregate(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_package(lines: Sequence[_Spec], packaging_rules: Sequence[_Rule]) -> _Result:  # noqa: ARG001
        return _Result(packed=tuple(lines), unpacked=())

    monkeypatch.setattr("core.shoplist_engine.engine.normalize_specs", fake_normalize)
    monkeypatch.setattr("core.shoplist_engine.engine.aggregate_specs", fake_aggregate)
    monkeypatch.setattr("core.shoplist_engine.engine.apply_packaging", fake_package)

    out = generate_shoplist([])  # type: ignore[arg-type]
    assert len(out.packed) == 0
    assert len(out.unpacked) == 0


def test_engine_none_packaging_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that engine handles None packaging_rules (defaults to empty)."""

    def fake_normalize(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_aggregate(specs: Sequence[_Spec]) -> list[_Spec]:
        return list(specs)

    def fake_package(lines: Sequence[_Spec], packaging_rules: Sequence[_Rule]) -> _Result:
        # Проверяем, что передаётся пустой tuple, а не None
        assert packaging_rules == ()
        return _Result(packed=tuple(lines), unpacked=())

    monkeypatch.setattr("core.shoplist_engine.engine.normalize_specs", fake_normalize)
    monkeypatch.setattr("core.shoplist_engine.engine.aggregate_specs", fake_aggregate)
    monkeypatch.setattr("core.shoplist_engine.engine.apply_packaging", fake_package)

    out = generate_shoplist([_Spec("A", 1, "G")], packaging_rules=None)  # type: ignore[arg-type]
    assert len(out.packed) == 1
    assert len(out.unpacked) == 0


def test_engine_integration_real_pipeline() -> None:
    """Integration test with real normalizer/aggregator/packager (no monkeypatch)."""
    from decimal import Decimal

    from core.shoplist_engine.models import (
        FoodForm,
        FoodRef,
        IngredientSpec,
        PackageRule,
        Quantity,
        RoundingMode,
        Unit,
    )

    # Создаём реальные данные
    specs = [
        IngredientSpec(
            food=FoodRef(food_id="flour"),
            qty=Quantity(value=Decimal("1.5"), unit=Unit.KG),  # будет нормализовано в G
            form=FoodForm.RAW,
        ),
        IngredientSpec(
            food=FoodRef(food_id="flour"),
            qty=Quantity(value=Decimal("500"), unit=Unit.G),
            form=FoodForm.RAW,
        ),
        IngredientSpec(
            food=FoodRef(food_id="eggs"),
            qty=Quantity(value=Decimal("6"), unit=Unit.PCS),
            form=FoodForm.RAW,
        ),
    ]

    rules = [
        PackageRule(
            food_id="flour",
            pack_size=Quantity(value=Decimal("1000"), unit=Unit.G),
            rounding=RoundingMode.CEIL,
            min_packs=1,
        ),
        PackageRule(
            food_id="eggs",
            pack_size=Quantity(value=Decimal("6"), unit=Unit.PCS),
            rounding=RoundingMode.CEIL,
            min_packs=1,
        ),
    ]

    # Запускаем реальный пайплайн
    result = generate_shoplist(specs, packaging_rules=rules)

    # Проверяем результаты
    assert len(result.packed) == 2
    assert len(result.unpacked) == 0

    # Находим flour и eggs в packed
    flour_plan = next(p for p in result.packed if p.food.food_id == "flour")
    eggs_plan = next(p for p in result.packed if p.food.food_id == "eggs")

    # Flour: 1.5kg + 500g = 2000g → 2 packs по 1000g
    assert flour_plan.packs == 2
    assert flour_plan.provided.value == Decimal("2000")

    # Eggs: 6 pcs → 1 pack по 6 pcs
    assert eggs_plan.packs == 1
    assert eggs_plan.provided.value == Decimal("6")

