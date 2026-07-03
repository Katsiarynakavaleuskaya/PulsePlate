"""Validate non-runtime route-family migration proof artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath
import re
from typing import Any

SCHEMA_VERSION = "route_family_migration_proof.v1"
ROUTE_FAMILY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
REQUIRED_TOP_LEVEL = (
    "schema_version",
    "route_family",
    "runtime_mutation_allowed",
    "owner_proof",
    "auth_proof",
    "openapi_proof",
    "duplicate_route_proof",
    "partial_registration_proof",
    "legacy_growth_proof",
    "rollback_proof",
)
PROOF_SECTIONS = REQUIRED_TOP_LEVEL[3:]
PROOF_SECTION_FIELDS = ("checked", "summary", "evidence_refs")
LOCAL_ROOTS = {"Users", "private", "tmp", "var", "Volumes", "workspaces", "workspace"}


def _is_repo_relative_ref(value: str) -> bool:
    if not value or value.startswith(("file://", "~", "/", "\\")):
        return False
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        return False
    if path.parts and path.parts[0] in LOCAL_ROOTS:
        return False
    if path.parts and path.parts[0] in {".git", ".venv", "worktrees", "artifacts"}:
        return False
    return True


def validate_route_family_migration_proof(payload: dict[str, Any]) -> list[str]:
    """Return validation errors for a route-family migration proof artifact."""

    errors: list[str] = []
    missing = [field for field in REQUIRED_TOP_LEVEL if field not in payload]
    extra = sorted(set(payload) - set(REQUIRED_TOP_LEVEL))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected fields: {', '.join(extra)}")
    if errors:
        return errors

    if payload["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    route_family = payload["route_family"]
    if not isinstance(route_family, str) or not ROUTE_FAMILY_RE.fullmatch(route_family):
        errors.append("route_family must match ^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
    if payload["runtime_mutation_allowed"] is not False:
        errors.append("runtime_mutation_allowed must be false")

    for section_name in PROOF_SECTIONS:
        section = payload[section_name]
        if not isinstance(section, dict):
            errors.append(f"{section_name} must be a JSON object")
            continue
        section_missing = [field for field in PROOF_SECTION_FIELDS if field not in section]
        section_extra = sorted(set(section) - set(PROOF_SECTION_FIELDS))
        if section_missing:
            errors.append(f"{section_name} missing fields: {', '.join(section_missing)}")
        if section_extra:
            errors.append(f"{section_name} unexpected fields: {', '.join(section_extra)}")
        if section_missing or section_extra:
            continue
        if section["checked"] is not True:
            errors.append(f"{section_name}.checked must be true")
        if (
            not isinstance(section["summary"], str)
            or not section["summary"].strip()
            or len(section["summary"]) > 360
        ):
            errors.append(
                f"{section_name}.summary must be a non-empty string of 360 chars or fewer"
            )
        evidence_refs = section["evidence_refs"]
        if not isinstance(evidence_refs, list) or not evidence_refs:
            errors.append(f"{section_name}.evidence_refs must be a non-empty array")
            continue
        if len(evidence_refs) != len(set(evidence_refs)):
            errors.append(f"{section_name}.evidence_refs must not contain duplicates")
        for index, ref in enumerate(evidence_refs):
            if not isinstance(ref, str) or not _is_repo_relative_ref(ref):
                errors.append(f"{section_name}.evidence_refs[{index}] must be a repo-relative ref")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", help="Path to a route-family migration proof JSON artifact")
    args = parser.parse_args(argv)

    try:
        with open(args.artifact, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: unable to read route-family migration proof: {exc}")
        return 1
    if not isinstance(payload, dict):
        print("FAIL: route-family migration proof must be a JSON object")
        return 1

    errors = validate_route_family_migration_proof(payload)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: route-family migration proof is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
