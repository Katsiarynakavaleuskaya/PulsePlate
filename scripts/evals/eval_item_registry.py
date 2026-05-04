#!/usr/bin/env python3
"""Evaluation item metadata registry contract.

RU: Реестр метаданных eval-элементов для психометрической готовности.
EN: Item metadata registry for psychometric readiness — maps every
    canonical eval item to stable metadata needed before future IRT,
    item weighting, or adaptive eval design.

This module does NOT implement IRT, psychometric scoring, or adaptive
item selection.  It provides only a registry schema, validation, and
coverage helpers.  All computation is deterministic, offline, and
stdlib-only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Sequence, TypedDict, get_args

# ---------------------------------------------------------------------------
# Literal types
# ---------------------------------------------------------------------------

Lane = Literal["rag", "judgment"]
LANES: tuple[str, ...] = get_args(Lane)

DifficultyBand = Literal["low", "medium", "high"]
DIFFICULTY_BANDS: tuple[str, ...] = get_args(DifficultyBand)

ScoreBand = Literal["fail", "partial", "pass"]
SCORE_BANDS: tuple[str, ...] = get_args(ScoreBand)

# ---------------------------------------------------------------------------
# Registry record schema
# ---------------------------------------------------------------------------


class EvalItemMetadataRecord(TypedDict):
    """Stable metadata for one canonical eval item.

    RU: Стабильные метаданные для одного канонического eval-элемента.
    EN: Maps a canonical_id to lane, domain, skill dimension, difficulty
        band, expected decision/score band, variant coverage, anchor
        status, source fixture, and human-readable notes.

    These fields are psychometric-readiness metadata.  Difficulty bands
    are explicit heuristic labels derived from observable score patterns,
    NOT calibrated IRT difficulty parameters.
    """

    canonical_id: str
    lane: Lane
    domain: str
    skill_dimension: str
    difficulty_band: DifficultyBand
    expected_decision: str
    expected_score_band: ScoreBand
    variant_family_coverage: list[str]
    anchor_item: bool
    source_fixture: str
    notes: str


# ---------------------------------------------------------------------------
# Required keys (for fail-closed validation)
# ---------------------------------------------------------------------------

_REQUIRED_KEYS: frozenset[str] = frozenset(EvalItemMetadataRecord.__annotations__)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_eval_item_metadata_record(
    raw: dict[str, Any],
) -> EvalItemMetadataRecord:
    """Parse and validate a raw dict into an ``EvalItemMetadataRecord``.

    Raises ``ValueError`` on missing keys, invalid enum values, or
    wrong types.  Fail-closed: rejects unknown enum values.
    """
    if not isinstance(raw, dict):
        raise ValueError(f"EvalItemMetadataRecord expects dict, got {type(raw).__name__}")

    missing = _REQUIRED_KEYS - raw.keys()
    if missing:
        raise ValueError(f"EvalItemMetadataRecord missing keys: {sorted(missing)}")

    extra = raw.keys() - _REQUIRED_KEYS
    if extra:
        raise ValueError(f"EvalItemMetadataRecord has unexpected keys: {sorted(extra)}")

    if raw["lane"] not in LANES:
        raise ValueError(f"Invalid lane={raw['lane']!r}; expected one of {LANES}")
    if raw["difficulty_band"] not in DIFFICULTY_BANDS:
        raise ValueError(
            f"Invalid difficulty_band={raw['difficulty_band']!r}; "
            f"expected one of {DIFFICULTY_BANDS}"
        )
    if raw["expected_score_band"] not in SCORE_BANDS:
        raise ValueError(
            f"Invalid expected_score_band={raw['expected_score_band']!r}; "
            f"expected one of {SCORE_BANDS}"
        )
    if not isinstance(raw["anchor_item"], bool):
        raise ValueError(f"anchor_item must be bool, got {type(raw['anchor_item']).__name__}")
    if not isinstance(raw["variant_family_coverage"], list):
        raise ValueError(
            f"variant_family_coverage must be list, "
            f"got {type(raw['variant_family_coverage']).__name__}"
        )
    if not raw["variant_family_coverage"]:
        raise ValueError("variant_family_coverage must not be empty")
    if not all(isinstance(item, str) for item in raw["variant_family_coverage"]):
        raise ValueError("variant_family_coverage must contain only strings")

    for key in (
        "canonical_id",
        "domain",
        "skill_dimension",
        "expected_decision",
        "source_fixture",
        "notes",
    ):
        if not isinstance(raw[key], str):
            raise ValueError(f"{key} must be str, got {type(raw[key]).__name__}")

    return EvalItemMetadataRecord(
        canonical_id=raw["canonical_id"],
        lane=raw["lane"],
        domain=raw["domain"],
        skill_dimension=raw["skill_dimension"],
        difficulty_band=raw["difficulty_band"],
        expected_decision=raw["expected_decision"],
        expected_score_band=raw["expected_score_band"],
        variant_family_coverage=raw["variant_family_coverage"],
        anchor_item=raw["anchor_item"],
        source_fixture=raw["source_fixture"],
        notes=raw["notes"],
    )


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_eval_item_registry(
    path: Path,
) -> list[EvalItemMetadataRecord]:
    """Load and validate registry from a JSONL file.

    Raises ``ValueError`` on duplicate canonical_id or invalid records.
    Returns records in file order.
    """
    records: list[EvalItemMetadataRecord] = []
    seen_ids: set[str] = set()

    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc

            record = validate_eval_item_metadata_record(raw)
            cid = record["canonical_id"]
            if cid in seen_ids:
                raise ValueError(f"{path}:{line_no}: duplicate canonical_id={cid!r}")
            seen_ids.add(cid)
            records.append(record)

    return records


def index_registry_by_canonical_id(
    records: Sequence[EvalItemMetadataRecord],
) -> dict[str, EvalItemMetadataRecord]:
    """Build a dict keyed by canonical_id for O(1) lookups."""
    index: dict[str, EvalItemMetadataRecord] = {}
    for rec in records:
        cid = rec["canonical_id"]
        if cid in index:
            raise ValueError(f"Duplicate canonical_id in registry: {cid!r}")
        index[cid] = rec
    return index


# ---------------------------------------------------------------------------
# Fixture canonical_id extraction
# ---------------------------------------------------------------------------


def extract_canonical_ids_from_outcome_fixture(
    path: Path,
) -> set[str]:
    """Extract unique canonical_id values from an EvalOutcomeRecord JSONL.

    Only considers rows with ``variant_family == "canonical"`` to avoid
    counting variant rows as separate items.
    """
    ids: set[str] = set()
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if raw.get("variant_family") == "canonical":
                cid = raw["canonical_id"]
                if not isinstance(cid, str):
                    raise ValueError(
                        f"{path}:{line_no}: canonical_id must be str, got {type(cid).__name__}"
                    )
                ids.add(cid)
    return ids


# ---------------------------------------------------------------------------
# Coverage validation
# ---------------------------------------------------------------------------


def validate_registry_coverage(
    records: Sequence[EvalItemMetadataRecord],
    fixture_canonical_ids: set[str],
) -> None:
    """Validate exact bidirectional coverage between registry and fixtures.

    Raises ``ValueError`` if:
    - Any fixture canonical_id is missing from the registry.
    - Any registry canonical_id is not present in fixtures (orphan).
    """
    registry_ids = {rec["canonical_id"] for rec in records}

    missing = fixture_canonical_ids - registry_ids
    if missing:
        raise ValueError(f"Fixture canonical_ids missing from registry: {sorted(missing)}")

    orphans = registry_ids - fixture_canonical_ids
    if orphans:
        raise ValueError(f"Orphan registry canonical_ids not in fixtures: {sorted(orphans)}")
