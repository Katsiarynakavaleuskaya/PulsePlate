"""
Deterministic JPTN source identity and license gate.

RU: Файловая проверка статуса JPTN до допуска к preflight или ingest.
EN: File-only JPTN status check before preflight eligibility or ingest.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.source_catalog import (
    SourceCatalog,
    SourceCatalogError,
    SourceCatalogEntry,
    load_source_catalog,
)
from core.food_sources.source_onboarding import (
    SourceOnboarding,
    SourceOnboardingEntry,
    SourceOnboardingError,
    load_source_onboarding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IDENTITY_SCHEMA_RE = re.compile(r"^food-data-jptn-identity\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SAFETY_FLAG_TEMPLATE: dict[str, bool] = {
    "runtime_cutover": False,
    "digitalocean_postgres_load": False,
    "bulk_ingest": False,
    "file_only": True,
    "network_allowed": False,
    "db_writes_allowed": False,
}
_IDENTITY_GATE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "source",
        "catalog_ref",
        "onboarding_ref",
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "file_only",
        "network_allowed",
        "db_writes_allowed",
        "provider_identity_status",
        "source_url_evidence_status",
        "license_status",
        "retrieval_contract_status",
        "schema_unit_normalization_status",
        "attribution_redistribution_status",
        "final_gate_decision",
        "blocking_reasons",
        "reviewed_queries",
        "notes",
    }
)

JPTN_SOURCE = "jptn_food_facts"
BLOCKED_GATE_DECISION = "blocked_until_verified"


class JptnIdentityError(ValueError):
    """Raised when the JPTN identity/license gate is invalid."""


@dataclass(frozen=True)
class JptnIdentityGate:
    """Validated JPTN identity/license decision artifact."""

    schema_version: str
    generated_on: date
    source: str
    catalog_ref: str
    onboarding_ref: str
    runtime_cutover: bool
    digitalocean_postgres_load: bool
    bulk_ingest: bool
    file_only: bool
    network_allowed: bool
    db_writes_allowed: bool
    provider_identity_status: str
    source_url_evidence_status: str
    license_status: str
    retrieval_contract_status: str
    schema_unit_normalization_status: str
    attribution_redistribution_status: str
    final_gate_decision: str
    blocking_reasons: tuple[str, ...]
    reviewed_queries: tuple[str, ...]
    notes: str


def _identity_error(context: str, detail: str) -> JptnIdentityError:
    """Build a stable validation error for the current artifact context."""
    return JptnIdentityError(f"Invalid JPTN identity gate {context}: {detail}")


def _require_mapping(value: object, context: str) -> dict[str, object]:
    """Return an object mapping or fail closed on malformed JSON payloads."""
    if not isinstance(value, dict):
        raise _identity_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _identity_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    """Read a required non-empty string field from a validated object."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _identity_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    """Read a required boolean field without truthy/falsy coercion."""
    value = data.get(key)
    if not isinstance(value, bool):
        raise _identity_error(context, f"'{key}' must be a boolean")
    return value


def _require_string_tuple(
    data: dict[str, object],
    key: str,
    context: str,
) -> tuple[str, ...]:
    """Read a required non-empty string list and reject duplicate values."""
    value = data.get(key)
    if not isinstance(value, list):
        raise _identity_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _identity_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _identity_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    if not items:
        raise _identity_error(context, f"'{key}' must not be empty")
    return tuple(items)


def _parse_date(value: str, context: str) -> date:
    """Parse the canonical YYYY-MM-DD artifact date format."""
    if not _DATE_RE.fullmatch(value):
        raise _identity_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _identity_error(context, "generated_on must use YYYY-MM-DD") from exc


def _require_safety_flags(data: dict[str, object], context: str) -> dict[str, bool]:
    """Extract all safety flags before comparing them with the gate template."""
    return {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}


def _relative_repo_path(path: Path | str) -> str:
    """Normalize a path to the repo-relative form used by canonical artifacts."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _catalog_jptn_entry(catalog: SourceCatalog, context: str) -> SourceCatalogEntry:
    """Find the JPTN catalog entry required by the identity gate."""
    entries = {entry.source: entry for entry in catalog.sources}
    entry = entries.get(JPTN_SOURCE)
    if entry is None:
        raise _identity_error(context, f"catalog must include {JPTN_SOURCE}")
    return entry


def _onboarding_jptn_entry(
    onboarding: SourceOnboarding,
    context: str,
) -> SourceOnboardingEntry:
    """Find the JPTN onboarding entry required by the identity gate."""
    entries = {entry.source: entry for entry in onboarding.sources}
    entry = entries.get(JPTN_SOURCE)
    if entry is None:
        raise _identity_error(context, f"onboarding must include {JPTN_SOURCE}")
    return entry


def _validate_jptn_catalog_policy(entry: SourceCatalogEntry, context: str) -> None:
    """Ensure the catalog still treats JPTN as unresolved and blocked."""
    if entry.source_classification != "unresolved":
        raise _identity_error(context, "JPTN must remain source_classification=unresolved")
    if entry.source_family != "unresolved":
        raise _identity_error(context, "JPTN must remain source_family=unresolved")
    if entry.status != "blocked_unresolved":
        raise _identity_error(context, "JPTN must remain blocked_unresolved in catalog")
    if entry.license_review != "unresolved_required":
        raise _identity_error(context, "JPTN must require unresolved license review")
    if entry.active_update_source:
        raise _identity_error(context, "JPTN cannot be an active update source")


def _validate_jptn_onboarding_policy(entry: SourceOnboardingEntry, context: str) -> None:
    """Ensure onboarding cannot make JPTN preflight-eligible before verification."""
    expected: dict[str, object] = {
        "source_classification": "unresolved",
        "source_family": "unresolved",
        "onboarding_status": "unresolved_blocked",
        "ingestion_path": "unresolved_identity_required",
        "cache_decision": "blocked_unresolved",
        "redistribution_decision": "blocked_unresolved",
        "display_decision": "blocked_unresolved",
        "attribution_required": True,
        "commercial_risk": "unresolved",
        "provider_policy_ref": None,
        "source_specific_policy_required": True,
    }
    actual: dict[str, object] = {
        "source_classification": entry.source_classification,
        "source_family": entry.source_family,
        "onboarding_status": entry.onboarding_status,
        "ingestion_path": entry.ingestion_path,
        "cache_decision": entry.cache_decision,
        "redistribution_decision": entry.redistribution_decision,
        "display_decision": entry.display_decision,
        "attribution_required": entry.attribution_required,
        "commercial_risk": entry.commercial_risk,
        "provider_policy_ref": entry.provider_policy_ref,
        "source_specific_policy_required": entry.source_specific_policy_required,
    }
    mismatches = [key for key, value in expected.items() if actual[key] != value]
    if mismatches:
        joined = ", ".join(mismatches)
        raise _identity_error(context, f"JPTN onboarding must remain blocked: {joined}")


def parse_jptn_identity_gate(
    payload: object,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    context: str = "<jptn-identity>",
) -> JptnIdentityGate:
    """Parse and validate the JPTN source identity/license gate."""
    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _IDENTITY_GATE_KEYS)
    if unexpected_keys:
        joined = ", ".join(unexpected_keys)
        raise _identity_error(context, f"unexpected keys: {joined}")

    schema_version = _require_string(data, "schema_version", context)
    if not _IDENTITY_SCHEMA_RE.fullmatch(schema_version):
        raise _identity_error(context, "schema_version must look like food-data-jptn-identity.vN")

    source = _require_string(data, "source", context)
    if source != JPTN_SOURCE:
        raise _identity_error(context, f"source must be {JPTN_SOURCE!r}")

    catalog_ref = _require_string(data, "catalog_ref", context)
    if expected_catalog_ref is not None and catalog_ref != expected_catalog_ref:
        raise _identity_error(context, f"catalog_ref must be {expected_catalog_ref!r}")
    onboarding_ref = _require_string(data, "onboarding_ref", context)
    if expected_onboarding_ref is not None and onboarding_ref != expected_onboarding_ref:
        raise _identity_error(context, f"onboarding_ref must be {expected_onboarding_ref!r}")

    safety_flags = _require_safety_flags(data, context)
    if safety_flags != _SAFETY_FLAG_TEMPLATE:
        raise _identity_error(
            context,
            "runtime_cutover, digitalocean_postgres_load, bulk_ingest, "
            "network_allowed, and db_writes_allowed must be false; file_only must be true",
        )

    gate = JptnIdentityGate(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        source=source,
        catalog_ref=catalog_ref,
        onboarding_ref=onboarding_ref,
        runtime_cutover=safety_flags["runtime_cutover"],
        digitalocean_postgres_load=safety_flags["digitalocean_postgres_load"],
        bulk_ingest=safety_flags["bulk_ingest"],
        file_only=safety_flags["file_only"],
        network_allowed=safety_flags["network_allowed"],
        db_writes_allowed=safety_flags["db_writes_allowed"],
        provider_identity_status=_require_string(data, "provider_identity_status", context),
        source_url_evidence_status=_require_string(data, "source_url_evidence_status", context),
        license_status=_require_string(data, "license_status", context),
        retrieval_contract_status=_require_string(data, "retrieval_contract_status", context),
        schema_unit_normalization_status=_require_string(
            data,
            "schema_unit_normalization_status",
            context,
        ),
        attribution_redistribution_status=_require_string(
            data,
            "attribution_redistribution_status",
            context,
        ),
        final_gate_decision=_require_string(data, "final_gate_decision", context),
        blocking_reasons=_require_string_tuple(data, "blocking_reasons", context),
        reviewed_queries=_require_string_tuple(data, "reviewed_queries", context),
        notes=_require_string(data, "notes", context),
    )
    if gate.provider_identity_status != "not_verified":
        raise _identity_error(context, "provider_identity_status must be not_verified")
    if gate.source_url_evidence_status != "no_confirmed_public_source":
        raise _identity_error(
            context,
            "source_url_evidence_status must be no_confirmed_public_source",
        )
    if gate.license_status != "missing":
        raise _identity_error(context, "license_status must be missing")
    if gate.retrieval_contract_status != "missing":
        raise _identity_error(context, "retrieval_contract_status must be missing")
    if gate.schema_unit_normalization_status != "missing":
        raise _identity_error(context, "schema_unit_normalization_status must be missing")
    if gate.attribution_redistribution_status != "blocked_pending_license":
        raise _identity_error(
            context,
            "attribution_redistribution_status must be blocked_pending_license",
        )
    if gate.final_gate_decision != BLOCKED_GATE_DECISION:
        raise _identity_error(context, f"final_gate_decision must be {BLOCKED_GATE_DECISION}")

    _validate_jptn_catalog_policy(_catalog_jptn_entry(catalog, context), context)
    _validate_jptn_onboarding_policy(_onboarding_jptn_entry(onboarding, context), context)
    return gate


def load_jptn_identity_gate(
    identity_path: Path | str,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
) -> JptnIdentityGate:
    """Load and validate a JPTN identity/license JSON artifact."""
    path = Path(identity_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise JptnIdentityError(f"Cannot read JPTN identity gate {path}: {exc}") from exc
    return parse_jptn_identity_gate(
        payload,
        catalog=catalog,
        onboarding=onboarding,
        expected_catalog_ref=expected_catalog_ref,
        expected_onboarding_ref=expected_onboarding_ref,
        context=str(path),
    )


def build_jptn_identity_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    identity_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the JPTN identity gate."""
    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "source": JPTN_SOURCE,
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "file_only": True,
        "network_allowed": False,
        "db_writes_allowed": False,
        "final_gate_decision": BLOCKED_GATE_DECISION,
        "validation_errors": [],
    }
    try:
        catalog = load_source_catalog(catalog_path)
        onboarding = load_source_onboarding(
            onboarding_path,
            catalog=catalog,
            expected_catalog_ref=expected_catalog_ref,
        )
        gate = load_jptn_identity_gate(
            identity_path,
            catalog=catalog,
            onboarding=onboarding,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
        )
    except (JptnIdentityError, SourceCatalogError, SourceOnboardingError) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "catalog_ref": gate.catalog_ref,
            "onboarding_ref": gate.onboarding_ref,
            "provider_identity_status": gate.provider_identity_status,
            "source_url_evidence_status": gate.source_url_evidence_status,
            "license_status": gate.license_status,
            "retrieval_contract_status": gate.retrieval_contract_status,
            "schema_unit_normalization_status": gate.schema_unit_normalization_status,
            "attribution_redistribution_status": gate.attribution_redistribution_status,
            "blocking_reasons": list(gate.blocking_reasons),
            "reviewed_query_count": len(gate.reviewed_queries),
        }
    )
    return report
