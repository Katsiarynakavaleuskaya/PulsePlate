"""Tests for non-runtime route-family migration proof artifacts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from scripts.orchestration.check_route_family_migration_proof import (
    validate_route_family_migration_proof,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "route_family_migration_proof.v1.schema.json"
)


def _section(summary: str) -> dict[str, object]:
    return {
        "checked": True,
        "summary": summary,
        "evidence_refs": ["tests/test_route_family_migration_proof.py"],
    }


def _valid_proof() -> dict[str, object]:
    return {
        "schema_version": "route_family_migration_proof.v1",
        "route_family": "shopping-list",
        "runtime_mutation_allowed": False,
        "owner_proof": _section("canonical owner registered through bootstrap"),
        "auth_proof": _section("auth dependency checked"),
        "openapi_proof": _section("OpenAPI visibility checked"),
        "duplicate_route_proof": _section("duplicate method/path checked"),
        "partial_registration_proof": _section("partial registration checked"),
        "legacy_growth_proof": _section("legacy alias growth checked"),
        "rollback_proof": _section("rollback path recorded"),
    }


def test_route_family_migration_proof_schema_pins_non_runtime_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == "route_family_migration_proof.v1"
    assert schema["properties"]["runtime_mutation_allowed"]["const"] is False
    assert set(schema["required"]) == set(_valid_proof())
    for section_name in (
        "owner_proof",
        "auth_proof",
        "openapi_proof",
        "duplicate_route_proof",
        "partial_registration_proof",
        "legacy_growth_proof",
        "rollback_proof",
    ):
        assert schema["properties"][section_name]["$ref"] == "#/$defs/proof_section"


def test_route_family_migration_proof_accepts_minimal_valid_payload() -> None:
    assert validate_route_family_migration_proof(_valid_proof()) == []


def test_route_family_migration_proof_rejects_runtime_mutation_authority() -> None:
    payload = _valid_proof()
    payload["runtime_mutation_allowed"] = True

    assert "runtime_mutation_allowed must be false" in validate_route_family_migration_proof(
        payload
    )


def test_route_family_migration_proof_rejects_schema_invalid_route_family() -> None:
    payload = _valid_proof()
    payload["route_family"] = "route family with spaces"

    errors = validate_route_family_migration_proof(payload)
    assert any("route_family must match" in error for error in errors)

    payload["route_family"] = "a" * 97
    errors = validate_route_family_migration_proof(payload)
    assert any("route_family must match" in error for error in errors)


def test_route_family_migration_proof_requires_each_section_checked() -> None:
    payload = _valid_proof()
    payload["duplicate_route_proof"] = deepcopy(payload["duplicate_route_proof"])
    payload["duplicate_route_proof"]["checked"] = False

    errors = validate_route_family_migration_proof(payload)
    assert "duplicate_route_proof.checked must be true" in errors


def test_route_family_migration_proof_rejects_long_summaries() -> None:
    payload = _valid_proof()
    payload["owner_proof"] = deepcopy(payload["owner_proof"])
    payload["owner_proof"]["summary"] = "x" * 361

    errors = validate_route_family_migration_proof(payload)
    assert "owner_proof.summary must be a non-empty string of 360 chars or fewer" in errors


def test_route_family_migration_proof_rejects_duplicate_evidence_refs() -> None:
    payload = _valid_proof()
    payload["auth_proof"] = deepcopy(payload["auth_proof"])
    payload["auth_proof"]["evidence_refs"] = [
        "tests/test_route_family_migration_proof.py",
        "tests/test_route_family_migration_proof.py",
    ]

    errors = validate_route_family_migration_proof(payload)
    assert "auth_proof.evidence_refs must not contain duplicates" in errors


def test_route_family_migration_proof_rejects_local_evidence_refs() -> None:
    payload = _valid_proof()
    payload["openapi_proof"] = deepcopy(payload["openapi_proof"])
    payload["openapi_proof"]["evidence_refs"] = ["/Users/example/project/openapi.json"]

    errors = validate_route_family_migration_proof(payload)
    assert "openapi_proof.evidence_refs[0] must be a repo-relative ref" in errors
