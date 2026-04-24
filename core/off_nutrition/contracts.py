"""
OFF nutrition resolver contracts.

RU: Контракты resolver-слоя для provenance/confidence питания.
EN: Resolver-layer contracts for nutrition provenance and confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

RawNutritionValue = float | int | str | None


@dataclass(frozen=True)
class NutritionInput:
    """
    RU: Сырой вход питания от конкретного источника.
    EN: Raw nutrition input from a single source.
    """

    source: str
    nutrients: Mapping[str, float]
    record_id: str | None = None
    version_ref: str | None = None
    raw_payload: Mapping[str, RawNutritionValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "record_id": self.record_id,
            "version_ref": self.version_ref,
            "nutrients": dict(self.nutrients),
            "raw_payload": dict(self.raw_payload),
        }


@dataclass(frozen=True)
class NutritionResolved:
    """
    RU: Разрешённые нутриенты с provenance/confidence.
    EN: Resolved nutrients with provenance and confidence.
    """

    nutrients: Mapping[str, float]
    provenance: Mapping[str, str]
    nutrient_confidence: Mapping[str, float]
    confidence: float
    raw_inputs: tuple[NutritionInput, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "nutrients": dict(self.nutrients),
            "provenance": dict(self.provenance),
            "nutrient_confidence": dict(self.nutrient_confidence),
            "confidence": self.confidence,
            "raw_inputs": [entry.to_dict() for entry in self.raw_inputs],
        }
