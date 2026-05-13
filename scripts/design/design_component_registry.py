#!/usr/bin/env python3
"""Validate the design component contract registry seed."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
VOCABULARY_PATH = Path("docs/design/ui_component_vocabulary.json")

SCHEMA_VERSION = "design_component_registry.v1"
REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "source_of_truth",
    "authority",
    "components",
}
REQUIRED_CANONICAL_AUTHORITIES = {
    "repo code/docs/tests",
    "docs/design/ui_component_vocabulary.json",
}
REQUIRED_AUTHORITY_FIELDS = {
    "canonical",
    "reference_only",
}
REQUIRED_COMPONENT_FIELDS = {
    "component_id",
    "canonical_name",
    "repo_vocabulary_anchor",
    "web_runtime_anchor",
    "ios_runtime_anchor",
    "token_dependencies",
    "storybook_review_anchor",
    "figma_reference_anchor",
    "penpot_reference_anchor",
    "code_connect_anchor",
    "states",
    "variants",
    "accessibility_contract",
    "visual_regression_contract",
    "owner",
    "status",
}
ALLOWED_STATUS = {"covered", "partial", "missing", "unspecified"}
SEED_UNCONFIRMED_FIELDS = {
    "ios_runtime_anchor",
    "token_dependencies",
    "storybook_review_anchor",
    "figma_reference_anchor",
    "penpot_reference_anchor",
    "code_connect_anchor",
    "states",
    "variants",
    "accessibility_contract",
    "visual_regression_contract",
}
BRIDGE_COVERAGE_FIELDS = {
    "web_runtime_anchor",
    "ios_runtime_anchor",
    "storybook_review_anchor",
    "figma_reference_anchor",
    "penpot_reference_anchor",
    "code_connect_anchor",
    "accessibility_contract",
    "visual_regression_contract",
}
REQUIRED_REFERENCE_ONLY_AUTHORITIES = {
    "kimi",
    "figma",
    "canva",
    "penpot",
    "storybook",
    "code connect",
}
DENIED_CANONICAL_AUTHORITIES = {
    "kimi",
    "figma",
    "canva",
    "penpot",
    "storybook",
    "code connect",
    "google drive",
    "google drive prototype folder",
    "drive folder",
    "prototype folder",
    "screenshot",
    "screenshots",
    "generated code",
    "generated code bundle",
    "generated code bundles",
    "generated brief",
    "generated briefs",
    "external design note",
    "external design notes",
    "desktop export",
    "desktop exports",
}


class RegistryError(ValueError):
    """Raised when the design component registry fails validation."""


def _repo_path(path: str | Path, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def _path_stays_inside_repo(path: Path, repo_root: Path = REPO_ROOT) -> bool:
    try:
        path.resolve(strict=False).relative_to(repo_root.resolve(strict=True))
    except (OSError, ValueError):
        return False
    return True


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise RegistryError(f"{label}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"{label}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise RegistryError(f"{label}: cannot read file: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError(f"{label}: expected JSON object")
    return data


def _load_vocabulary(repo_root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    path = repo_root / VOCABULARY_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise RegistryError(f"{VOCABULARY_PATH}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"{VOCABULARY_PATH}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise RegistryError(f"{VOCABULARY_PATH}: cannot read vocabulary: {exc}") from exc
    if not isinstance(data, list):
        raise RegistryError(f"{VOCABULARY_PATH}: expected JSON array")

    vocabulary: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(data):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise RegistryError(f"{VOCABULARY_PATH}: item {index} requires string id")
        if item["id"] in vocabulary:
            raise RegistryError(f"{VOCABULARY_PATH}: duplicate component id {item['id']!r}")
        vocabulary[item["id"]] = item
    return vocabulary


def _iter_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_iter_string_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_iter_string_values(item))
        return values
    return []


def _check_empty_strings(value: Any, *, path: str, errors: list[str]) -> None:
    if isinstance(value, str):
        if value == "":
            errors.append(f"{path}: empty string is forbidden; use 'unspecified'")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_empty_strings(item, path=f"{path}[{index}]", errors=errors)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _check_empty_strings(item, path=f"{path}.{key}", errors=errors)


def _is_unspecified(value: Any) -> bool:
    return isinstance(value, str) and value == "unspecified"


def _normalize_authority_entries(value: list[str]) -> set[str]:
    return {" ".join(re.sub(r"[^a-z0-9]+", " ", item.lower()).split()) for item in value}


def _promoted_authorities(canonical: list[str]) -> list[str]:
    promoted: set[str] = set()
    canonical_entries = _normalize_authority_entries(canonical)
    for entry in canonical_entries:
        for tool in DENIED_CANONICAL_AUTHORITIES:
            if re.search(rf"(?<![a-z0-9]){re.escape(tool)}(?![a-z0-9])", entry):
                promoted.add(tool)
    return sorted(promoted)


def _validate_authority(authority: Any, errors: list[str]) -> None:
    if not isinstance(authority, dict):
        errors.append("authority: expected object")
        return
    unexpected_authority_fields = authority.keys() - REQUIRED_AUTHORITY_FIELDS
    if unexpected_authority_fields:
        errors.append(
            "authority: unexpected fields: " + ", ".join(sorted(unexpected_authority_fields))
        )

    canonical = authority.get("canonical")
    reference_only = authority.get("reference_only")
    if not isinstance(canonical, list) or not all(isinstance(item, str) for item in canonical):
        errors.append("authority.canonical: expected list of strings")
        canonical = []
    if not isinstance(reference_only, list) or not all(
        isinstance(item, str) for item in reference_only
    ):
        errors.append("authority.reference_only: expected list of strings")
        reference_only = []

    canonical_set = _normalize_authority_entries(canonical)
    reference_set = _normalize_authority_entries(reference_only)
    promoted = _promoted_authorities(canonical)
    if promoted:
        errors.append(
            "authority.canonical: external evidence tools must not be canonical: "
            + ", ".join(promoted)
        )
    required_canonical_set = _normalize_authority_entries(list(REQUIRED_CANONICAL_AUTHORITIES))
    missing_canonical = sorted(
        authority for authority in required_canonical_set if authority not in canonical_set
    )
    if missing_canonical:
        errors.append(
            "authority.canonical: missing repo canonical authorities: "
            + ", ".join(missing_canonical)
        )
    missing_reference = sorted(
        tool for tool in REQUIRED_REFERENCE_ONLY_AUTHORITIES if tool not in reference_set
    )
    if missing_reference:
        errors.append(
            "authority.reference_only: missing external evidence tools: "
            + ", ".join(missing_reference)
        )


def validate_registry(path: str | Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    """Return validation errors for a registry path."""
    registry_path = _repo_path(path, repo_root)
    errors: list[str] = []

    try:
        registry = _load_json_object(registry_path, label=str(registry_path))
    except RegistryError as exc:
        return [str(exc)]

    missing_top_level = REQUIRED_TOP_LEVEL_FIELDS - registry.keys()
    if missing_top_level:
        errors.append("registry: missing required fields: " + ", ".join(sorted(missing_top_level)))
    unexpected_top_level = registry.keys() - REQUIRED_TOP_LEVEL_FIELDS
    if unexpected_top_level:
        errors.append("registry: unexpected fields: " + ", ".join(sorted(unexpected_top_level)))

    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION!r}")
    if registry.get("source_of_truth") != "repo":
        errors.append("source_of_truth: expected 'repo'")

    _validate_authority(registry.get("authority"), errors)
    _check_empty_strings(registry, path="registry", errors=errors)

    components = registry.get("components")
    if not isinstance(components, list):
        errors.append("components: expected non-empty list")
        return errors
    if not components:
        errors.append("components: expected non-empty list")
        return errors

    try:
        vocabulary = _load_vocabulary(repo_root)
    except RegistryError as exc:
        errors.append(str(exc))
        vocabulary = {}
    vocabulary_ids = set(vocabulary)

    seen: set[str] = set()
    for index, component in enumerate(components):
        path_prefix = f"components[{index}]"
        if not isinstance(component, dict):
            errors.append(f"{path_prefix}: expected object")
            continue
        missing_component_fields = REQUIRED_COMPONENT_FIELDS - component.keys()
        if missing_component_fields:
            errors.append(
                f"{path_prefix}: missing required fields: "
                + ", ".join(sorted(missing_component_fields))
            )
        unexpected_component_fields = component.keys() - REQUIRED_COMPONENT_FIELDS
        if unexpected_component_fields:
            errors.append(
                f"{path_prefix}: unexpected fields: "
                + ", ".join(sorted(unexpected_component_fields))
            )
        component_id = component.get("component_id")
        if not isinstance(component_id, str):
            errors.append(f"{path_prefix}.component_id: expected string")
            continue
        if component_id in seen:
            errors.append(f"{path_prefix}.component_id: duplicate id {component_id!r}")
        seen.add(component_id)
        if component_id not in vocabulary_ids:
            errors.append(f"{path_prefix}.component_id: unknown vocabulary id {component_id!r}")

        canonical_name = component.get("canonical_name")
        vocabulary_entry = vocabulary.get(component_id, {})
        expected_name = vocabulary_entry.get("canonical_name")
        if expected_name is not None and canonical_name != expected_name:
            errors.append(
                f"{path_prefix}.canonical_name: expected vocabulary name {expected_name!r}"
            )

        repo_vocabulary_anchor = component.get("repo_vocabulary_anchor")
        expected_vocabulary_anchor = f"{VOCABULARY_PATH}:{component_id}"
        if repo_vocabulary_anchor != expected_vocabulary_anchor:
            errors.append(
                f"{path_prefix}.repo_vocabulary_anchor: expected " f"{expected_vocabulary_anchor!r}"
            )

        web_runtime_anchor = component.get("web_runtime_anchor")
        expected_web_anchor = vocabulary_entry.get("existing_repo_component")
        if expected_web_anchor is None:
            if web_runtime_anchor != "unspecified":
                errors.append(
                    f"{path_prefix}.web_runtime_anchor: expected 'unspecified' "
                    "when vocabulary has no existing repo component"
                )
        elif web_runtime_anchor != expected_web_anchor:
            errors.append(
                f"{path_prefix}.web_runtime_anchor: expected repo-backed anchor "
                f"{expected_web_anchor!r}"
            )
        else:
            if Path(web_runtime_anchor).is_absolute():
                errors.append(
                    f"{path_prefix}.web_runtime_anchor: expected repo-relative anchor, got "
                    f"{web_runtime_anchor!r}"
                )
            else:
                resolved_web_anchor = _repo_path(web_runtime_anchor, repo_root)
                if not _path_stays_inside_repo(resolved_web_anchor, repo_root):
                    errors.append(
                        f"{path_prefix}.web_runtime_anchor: repo-backed anchor escapes repo root: "
                        f"{web_runtime_anchor!r}"
                    )
                elif not resolved_web_anchor.is_file():
                    errors.append(
                        f"{path_prefix}.web_runtime_anchor: repo-backed anchor does not exist: "
                        f"{web_runtime_anchor!r}"
                    )

        status = component.get("status")
        if not isinstance(status, str) or status not in ALLOWED_STATUS:
            errors.append(f"{path_prefix}.status: invalid status {status!r}")
        elif status == "covered":
            errors.append(
                f"{path_prefix}.status: covered requires the dedicated bridge coverage "
                "evidence schema; seed registry rows must stay partial, missing, or unspecified"
            )
        elif status == "partial" and _is_unspecified(component.get("web_runtime_anchor")):
            errors.append(
                f"{path_prefix}.status: partial requires a repo-backed web_runtime_anchor"
            )
        else:
            invented_unconfirmed = sorted(
                field
                for field in SEED_UNCONFIRMED_FIELDS
                if not _is_unspecified(component.get(field))
            )
            if invented_unconfirmed:
                errors.append(
                    f"{path_prefix}: unconfirmed seed fields must be 'unspecified': "
                    + ", ".join(invented_unconfirmed)
                )
        owner = component.get("owner")
        if not isinstance(owner, str):
            errors.append(f"{path_prefix}.owner: expected string")

    missing_ids = sorted(vocabulary_ids - seen)
    if missing_ids:
        errors.append("components: missing vocabulary ids: " + ", ".join(missing_ids))

    return errors


def summarize_registry(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return a deterministic summary for a valid registry."""
    errors = validate_registry(path, repo_root=repo_root)
    if errors:
        raise RegistryError("; ".join(errors))

    registry = _load_json_object(_repo_path(path, repo_root), label=str(path))
    components = registry["components"]
    status_counts = Counter(component["status"] for component in components)
    return {
        "schema_version": registry["schema_version"],
        "component_count": len(components),
        "status_counts": dict(sorted(status_counts.items())),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a registry JSON file")
    validate.add_argument("path")

    summarize = subparsers.add_parser("summarize", help="print a deterministic registry summary")
    summarize.add_argument("path")

    return parser


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        errors = validate_registry(args.path)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("PASS: design component registry valid", file=stdout)
        return 0
    if args.command == "summarize":
        try:
            summary = summarize_registry(args.path)
        except RegistryError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, sort_keys=True), file=stdout)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
