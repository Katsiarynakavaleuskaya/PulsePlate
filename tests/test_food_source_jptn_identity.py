"""Tests for the deterministic JPTN source identity/license gate."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources import jptn_identity
from core.food_sources.jptn_identity import (
    JptnIdentityError,
    build_jptn_identity_report,
    load_jptn_identity_gate,
    parse_jptn_identity_gate,
)
from core.food_sources.source_catalog import load_source_catalog
from core.food_sources.source_onboarding import load_source_onboarding

_REPO_ROOT = Path(__file__).parents[1]
_CATALOG_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
)
_ONBOARDING_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"
)
_IDENTITY_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_JPTN_IDENTITY_LICENSE_PR8_2026-04-29.json"
)
_CLI_MODULE = "scripts.food_source_jptn_identity"


def _catalog():
    return load_source_catalog(_CATALOG_PATH)


def _onboarding():
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
    )


def _identity_payload() -> dict[str, object]:
    return json.loads(_IDENTITY_PATH.read_text(encoding="utf-8"))


def _onboarding_payload() -> dict[str, object]:
    return json.loads(_ONBOARDING_PATH.read_text(encoding="utf-8"))


def _mutate_jptn_onboarding(key: str, value: object, tmp_path: Path) -> Path:
    payload = _onboarding_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "jptn_food_facts":
            source[key] = value
            break
    path = tmp_path / "onboarding.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_jptn_identity_gate_accepts_blocked_contract() -> None:
    gate = load_jptn_identity_gate(
        _IDENTITY_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
    )

    assert gate.source == "jptn_food_facts"
    assert gate.provider_identity_status == "not_verified"
    assert gate.license_status == "missing"
    assert gate.final_gate_decision == "blocked_until_verified"
    assert gate.runtime_cutover is False
    assert gate.network_allowed is False
    assert gate.db_writes_allowed is False


@pytest.mark.parametrize(
    ("field_name", "field_value", "match"),
    (
        ("provider_identity_status", "verified", "provider_identity_status"),
        ("source_url_evidence_status", "confirmed_public_source", "source_url_evidence_status"),
        ("license_status", "approved", "license_status"),
        ("retrieval_contract_status", "approved", "retrieval_contract_status"),
        ("schema_unit_normalization_status", "approved", "schema_unit_normalization_status"),
        (
            "attribution_redistribution_status",
            "allowed",
            "attribution_redistribution_status",
        ),
        ("final_gate_decision", "eligible_preflight", "final_gate_decision"),
    ),
)
def test_jptn_identity_gate_rejects_premature_resolution(
    field_name: str,
    field_value: object,
    match: str,
) -> None:
    payload = _identity_payload()
    payload[field_name] = field_value

    with pytest.raises(JptnIdentityError, match=match):
        parse_jptn_identity_gate(payload, catalog=_catalog(), onboarding=_onboarding())


@pytest.mark.parametrize(
    ("flag_name", "flag_value"),
    (
        ("runtime_cutover", True),
        ("digitalocean_postgres_load", True),
        ("bulk_ingest", True),
        ("file_only", False),
        ("network_allowed", True),
        ("db_writes_allowed", True),
    ),
)
def test_jptn_identity_gate_rejects_unsafe_flags(
    flag_name: str,
    flag_value: bool,
) -> None:
    payload = _identity_payload()
    payload[flag_name] = flag_value

    with pytest.raises(JptnIdentityError, match="must be false; file_only must be true"):
        parse_jptn_identity_gate(payload, catalog=_catalog(), onboarding=_onboarding())


def test_jptn_identity_gate_rejects_unexpected_keys() -> None:
    payload = _identity_payload()
    payload["eligible_preflight"] = True

    with pytest.raises(JptnIdentityError, match="unexpected keys: eligible_preflight"):
        parse_jptn_identity_gate(payload, catalog=_catalog(), onboarding=_onboarding())


def test_jptn_identity_report_rejects_onboarding_eligibility_drift(tmp_path: Path) -> None:
    onboarding_path = _mutate_jptn_onboarding(
        "onboarding_status",
        "eligible_preflight",
        tmp_path,
    )

    report = build_jptn_identity_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=onboarding_path,
        identity_path=_IDENTITY_PATH,
    )

    assert report["success"] is False
    assert report["runtime_cutover"] is False
    assert report["network_allowed"] is False
    assert report["db_writes_allowed"] is False
    errors = report["validation_errors"]
    assert isinstance(errors, list)
    assert "jptn_food_facts" in errors[0]


def test_build_jptn_identity_report_is_deterministic_json_contract() -> None:
    report = build_jptn_identity_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        identity_path=_IDENTITY_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "source": "jptn_food_facts",
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "file_only": True,
        "network_allowed": False,
        "db_writes_allowed": False,
        "final_gate_decision": "blocked_until_verified",
        "validation_errors": [],
        "catalog_ref": "docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        "onboarding_ref": "docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        "provider_identity_status": "not_verified",
        "source_url_evidence_status": "no_confirmed_public_source",
        "license_status": "missing",
        "retrieval_contract_status": "missing",
        "schema_unit_normalization_status": "missing",
        "attribution_redistribution_status": "blocked_pending_license",
        "blocking_reasons": [
            "Exact provider identity is not confirmed.",
            "Canonical source URL and retrieval contract are not confirmed.",
            "License, attribution, redistribution, and cache rights are not confirmed.",
            "Schema, primary keys, units, locale, and normalization contract are not confirmed.",
        ],
        "reviewed_query_count": 4,
    }


def test_jptn_identity_cli_is_file_only_and_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://must-not-be-used.invalid/db")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
            "--identity",
            str(_IDENTITY_PATH),
            "--json",
        ],
        cwd=_REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["final_gate_decision"] == "blocked_until_verified"
    assert payload["runtime_cutover"] is False
    assert payload["network_allowed"] is False
    assert payload["db_writes_allowed"] is False
    assert result.stderr == ""
    assert after == before


def test_jptn_identity_cli_returns_nonzero_for_invalid_payload(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad_identity.json"
    payload = _identity_payload()
    payload["network_allowed"] = True
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
            "--identity",
            str(bad_path),
            "--json",
        ],
        cwd=_REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["success"] is False
    assert payload["runtime_cutover"] is False


def test_jptn_identity_cli_prints_validation_errors_without_json(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad_identity.json"
    payload = _identity_payload()
    payload["network_allowed"] = True
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
            "--identity",
            str(bad_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "jptn_identity: FAIL" in result.stdout
    assert "Validation errors:" in result.stdout
    assert "network_allowed" in result.stdout


def test_jptn_identity_has_no_network_or_db_dependencies() -> None:
    source_text = Path(jptn_identity.__file__).read_text(encoding="utf-8")
    syntax_tree = ast.parse(source_text)

    blocked_roots = {
        "requests",
        "httpx",
        "psycopg",
        "sqlalchemy",
        "digitalocean",
        "subprocess",
    }
    blocked_full_imports = {"urllib.request", "sqlite3"}
    imported_roots: set[str] = set()
    imported_full: set[str] = set()
    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_full.add(alias.name)
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_full.add(node.module)
            imported_roots.add(node.module.split(".")[0])
            imported_full.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert imported_roots.isdisjoint(blocked_roots)
    assert imported_full.isdisjoint(blocked_full_imports)
