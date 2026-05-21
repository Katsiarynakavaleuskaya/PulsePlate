#!/usr/bin/env python3
"""Deterministic guard for Philosophy alignment-rule trust records."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "PHILOSOPHY_ALIGNMENT_RULE.schema.json"
)

SCHEMA_VERSION = "v1.0.0"
SCHEMA_ID = "https://pulseplate.app/schemas/philosophy-alignment-rule.v1.json"
SCHEMA_TITLE = "PhilosophyAlignmentRule"
JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
RULE_TYPES = ("privacy", "harm", "misinfo", "wellness_scope", "copyright", "safety_other")
SEVERITIES = ("block", "warn", "note")
SOURCE_TYPES = ("repo", "policy_doc", "legal", "spec")
REQUIRED_RULE_KEYS = (
    "rule_id",
    "rule_text",
    "rule_type",
    "severity",
    "provenance",
    "assertion_hints",
    "created_by",
    "created_at",
    "schema_version",
    "schema_hash",
)
OPTIONAL_RULE_KEYS = ("notes", "tags")
RULE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
DATE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
ROOT_SCHEMA_KEYS = {
    "$id",
    "$schema",
    "additionalProperties",
    "properties",
    "required",
    "title",
    "type",
}
OBJECT_SCHEMA_KEYS = {"additionalProperties", "properties", "required", "type"}
OPTIONAL_OBJECT_SCHEMA_KEYS = {"additionalProperties", "properties", "type"}
ENUM_SCHEMA_KEYS = {"enum", "type"}
ARRAY_SCHEMA_KEYS = {"items", "type", "uniqueItems"}
ITEM_SCHEMA_KEYS = {"type"}


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def schema_hash(schema: object) -> str:
    return hashlib.sha256(canonical_json_bytes(schema)).hexdigest()


def _load_json_no_duplicate_keys(
    text: str,
    *,
    invalid_prefix: str,
    duplicate_prefix: str,
) -> tuple[object | None, list[str]]:
    def _hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        seen: set[str] = set()
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in seen:
                raise ValueError(f"{duplicate_prefix}: {key}")
            seen.add(key)
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=_hook), []
    except json.JSONDecodeError as exc:
        return None, [f"{invalid_prefix}: {exc}"]
    except ValueError as exc:
        return None, [str(exc)]


def _as_object(value: object, *, label: str) -> tuple[dict[str, object], list[str]]:
    if not isinstance(value, dict):
        return {}, [f"{label} must be an object"]
    return value, []


def _string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{label} must be an array"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(f"{label}[{index}] must be a string")
            continue
        if item in seen:
            errors.append(f"{label} contains duplicate item: {item}")
        seen.add(item)
    return errors


def _validate_enum_property(
    properties: dict[str, object],
    *,
    key: str,
    expected: tuple[str, ...],
) -> list[str]:
    prop, errors = _as_object(properties.get(key), label=f"alignment schema property {key}")
    if errors:
        return errors
    errors.extend(
        _reject_unknown_schema_keys(prop, ENUM_SCHEMA_KEYS, f"alignment schema property {key}")
    )
    if prop.get("type") != "string":
        errors.append(f"alignment schema property {key} type must be string")
    enum = prop.get("enum")
    if enum != list(expected):
        errors.append(f"alignment schema enum mismatch for {key}")
    return errors


def _reject_unknown_schema_keys(
    schema_part: dict[str, object],
    allowed_keys: set[str],
    label: str,
) -> list[str]:
    return [
        f"{label} unknown schema keyword {key}" for key in sorted(set(schema_part) - allowed_keys)
    ]


def _object_property(
    properties: dict[str, object], key: str
) -> tuple[dict[str, object], list[str]]:
    return _as_object(properties.get(key), label=f"alignment schema property {key}")


def _validate_string_property(
    properties: dict[str, object],
    *,
    key: str,
    min_length: int | None = None,
    pattern: str | None = None,
    const: str | None = None,
    format_name: str | None = None,
) -> list[str]:
    prop, errors = _object_property(properties, key)
    if errors:
        return errors
    allowed_keys = {"type"}
    if min_length is not None:
        allowed_keys.add("minLength")
    if pattern is not None:
        allowed_keys.add("pattern")
    if const is not None:
        allowed_keys.add("const")
    if format_name is not None:
        allowed_keys.add("format")
    errors.extend(
        _reject_unknown_schema_keys(prop, allowed_keys, f"alignment schema property {key}")
    )
    if prop.get("type") != "string":
        errors.append(f"alignment schema property {key} type must be string")
    if min_length is not None and prop.get("minLength") != min_length:
        errors.append(f"alignment schema property {key} minLength mismatch")
    if pattern is not None and prop.get("pattern") != pattern:
        errors.append(f"alignment schema property {key} pattern mismatch")
    if const is not None and prop.get("const") != const:
        errors.append(f"alignment schema property {key} const mismatch")
    if format_name is not None and prop.get("format") != format_name:
        errors.append(f"alignment schema property {key} format mismatch")
    return errors


def _validate_string_array_property(
    properties: dict[str, object],
    *,
    key: str,
    unique_items: bool,
) -> list[str]:
    prop, errors = _object_property(properties, key)
    if errors:
        return errors
    errors.extend(
        _reject_unknown_schema_keys(prop, ARRAY_SCHEMA_KEYS, f"alignment schema property {key}")
    )
    if prop.get("type") != "array":
        errors.append(f"alignment schema property {key} type must be array")
    if prop.get("uniqueItems") is not unique_items:
        errors.append(f"alignment schema property {key} uniqueItems mismatch")
    items, item_errors = _as_object(
        prop.get("items"),
        label=f"alignment schema property {key}.items",
    )
    errors.extend(item_errors)
    if not item_errors:
        errors.extend(
            _reject_unknown_schema_keys(
                items,
                ITEM_SCHEMA_KEYS,
                f"alignment schema property {key}.items",
            )
        )
        if items.get("type") != "string":
            errors.append(f"alignment schema property {key}.items type must be string")
    return errors


def _is_date_time(value: str) -> bool:
    if not DATE_TIME_RE.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_alignment_rule_schema(schema_text: str) -> list[str]:
    schema, parse_errors = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="alignment rule schema invalid JSON",
        duplicate_prefix="alignment rule schema duplicate key",
    )
    if parse_errors:
        return parse_errors
    schema_obj, errors = _as_object(schema, label="alignment rule schema")
    if errors:
        return errors

    if schema_obj.get("$schema") != JSON_SCHEMA_DRAFT:
        errors.append("alignment rule schema $schema mismatch")
    if schema_obj.get("$id") != SCHEMA_ID:
        errors.append("alignment rule schema $id mismatch")
    if schema_obj.get("title") != SCHEMA_TITLE:
        errors.append("alignment rule schema title mismatch")
    if schema_obj.get("type") != "object":
        errors.append("alignment rule schema root type must be object")
    if schema_obj.get("additionalProperties") is not False:
        errors.append("alignment rule schema must set additionalProperties false")
    errors.extend(
        _reject_unknown_schema_keys(schema_obj, ROOT_SCHEMA_KEYS, "alignment rule schema")
    )

    required = schema_obj.get("required")
    if required != list(REQUIRED_RULE_KEYS):
        errors.append("alignment rule schema required keys mismatch")

    properties, property_errors = _as_object(
        schema_obj.get("properties"),
        label="alignment rule schema properties",
    )
    errors.extend(property_errors)
    if property_errors:
        return errors

    allowed_keys = set(REQUIRED_RULE_KEYS) | set(OPTIONAL_RULE_KEYS)
    if set(properties) != allowed_keys:
        errors.append("alignment rule schema properties keys mismatch")

    errors.extend(
        _validate_string_property(
            properties,
            key="rule_id",
            min_length=1,
            pattern=RULE_ID_RE.pattern,
        )
    )
    errors.extend(_validate_string_property(properties, key="rule_text", min_length=1))
    errors.extend(_validate_string_property(properties, key="created_by", min_length=1))
    errors.extend(
        _validate_string_property(
            properties,
            key="created_at",
            format_name="date-time",
            pattern=DATE_TIME_RE.pattern,
        )
    )
    errors.extend(_validate_string_property(properties, key="schema_version", const=SCHEMA_VERSION))
    errors.extend(
        _validate_string_property(properties, key="schema_hash", pattern=SHA256_RE.pattern)
    )
    errors.extend(_validate_string_property(properties, key="notes"))
    errors.extend(_validate_string_array_property(properties, key="tags", unique_items=True))
    errors.extend(_validate_enum_property(properties, key="rule_type", expected=RULE_TYPES))
    errors.extend(_validate_enum_property(properties, key="severity", expected=SEVERITIES))

    provenance, provenance_errors = _as_object(
        properties.get("provenance"),
        label="alignment schema property provenance",
    )
    errors.extend(provenance_errors)
    if not provenance_errors:
        errors.extend(
            _reject_unknown_schema_keys(
                provenance,
                OBJECT_SCHEMA_KEYS,
                "alignment provenance schema",
            )
        )
        if provenance.get("type") != "object":
            errors.append("alignment provenance schema type must be object")
        if provenance.get("additionalProperties") is not False:
            errors.append("alignment provenance schema must set additionalProperties false")
        if provenance.get("required") != ["source_id", "source_type", "version", "anchor_hash"]:
            errors.append("alignment provenance schema required keys mismatch")
        provenance_props, provenance_prop_errors = _as_object(
            provenance.get("properties"),
            label="alignment provenance schema properties",
        )
        errors.extend(provenance_prop_errors)
        if not provenance_prop_errors:
            if set(provenance_props) != {"source_id", "source_type", "version", "anchor_hash"}:
                errors.append("alignment provenance schema properties keys mismatch")
            errors.extend(
                _validate_string_property(provenance_props, key="source_id", min_length=1)
            )
            errors.extend(_validate_string_property(provenance_props, key="version", min_length=1))
            errors.extend(
                _validate_string_property(provenance_props, key="anchor_hash", min_length=8)
            )
            errors.extend(
                _validate_enum_property(provenance_props, key="source_type", expected=SOURCE_TYPES)
            )

    assertion_hints, hints_errors = _as_object(
        properties.get("assertion_hints"),
        label="alignment schema property assertion_hints",
    )
    errors.extend(hints_errors)
    if not hints_errors:
        errors.extend(
            _reject_unknown_schema_keys(
                assertion_hints,
                OPTIONAL_OBJECT_SCHEMA_KEYS,
                "alignment assertion_hints schema",
            )
        )
        if assertion_hints.get("type") != "object":
            errors.append("alignment assertion_hints schema type must be object")
        if assertion_hints.get("additionalProperties") is not False:
            errors.append("alignment assertion_hints schema must set additionalProperties false")
        if "required" in assertion_hints:
            errors.append("alignment assertion_hints schema required keys mismatch")
        hint_props, hint_prop_errors = _as_object(
            assertion_hints.get("properties"),
            label="alignment assertion_hints schema properties",
        )
        errors.extend(hint_prop_errors)
        if not hint_prop_errors:
            if set(hint_props) != {"boolean_checks", "regexes"}:
                errors.append("alignment assertion_hints schema properties keys mismatch")
            errors.extend(
                _validate_string_array_property(
                    hint_props,
                    key="boolean_checks",
                    unique_items=True,
                )
            )
            errors.extend(
                _validate_string_array_property(
                    hint_props,
                    key="regexes",
                    unique_items=True,
                )
            )

    return errors


def validate_alignment_rule(
    *,
    rule_text: str,
    expected_schema_hash: str,
    label: str,
) -> tuple[str | None, list[str]]:
    rule, parse_errors = _load_json_no_duplicate_keys(
        rule_text,
        invalid_prefix=f"{label}: invalid JSON",
        duplicate_prefix=f"{label}: duplicate key",
    )
    if parse_errors:
        return None, parse_errors
    rule_obj, errors = _as_object(rule, label=f"{label}: alignment rule")
    if errors:
        return None, errors

    allowed_keys = set(REQUIRED_RULE_KEYS) | set(OPTIONAL_RULE_KEYS)
    for key in REQUIRED_RULE_KEYS:
        if key not in rule_obj:
            errors.append(f"{label}: missing required key {key}")
    for key in sorted(set(rule_obj) - allowed_keys):
        errors.append(f"{label}: unknown key {key}")

    rule_id = rule_obj.get("rule_id")
    if not isinstance(rule_id, str) or not RULE_ID_RE.fullmatch(rule_id):
        errors.append(f"{label}: rule_id must match {RULE_ID_RE.pattern}")

    for key in ("rule_text", "created_by"):
        value = rule_obj.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{label}: {key} must be a non-empty string")
    created_at = rule_obj.get("created_at")
    if not isinstance(created_at, str) or not created_at:
        errors.append(f"{label}: created_at must be a non-empty string")
    elif not _is_date_time(created_at):
        errors.append(f"{label}: created_at must be a valid date-time")

    if rule_obj.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"{label}: schema_version mismatch: expected {SCHEMA_VERSION}, "
            f"got {rule_obj.get('schema_version')!r}"
        )
    if rule_obj.get("schema_hash") != expected_schema_hash:
        errors.append(f"{label}: schema_hash mismatch")

    if rule_obj.get("rule_type") not in RULE_TYPES:
        errors.append(f"{label}: invalid rule_type {rule_obj.get('rule_type')!r}")
    if rule_obj.get("severity") not in SEVERITIES:
        errors.append(f"{label}: invalid severity {rule_obj.get('severity')!r}")

    provenance, provenance_errors = _as_object(
        rule_obj.get("provenance"),
        label=f"{label}: provenance",
    )
    errors.extend(provenance_errors)
    if not provenance_errors:
        provenance_allowed = {"source_id", "source_type", "version", "anchor_hash"}
        for key in sorted(set(provenance) - provenance_allowed):
            errors.append(f"{label}: provenance unknown key {key}")
        for key in ("source_id", "version", "anchor_hash"):
            value = provenance.get(key)
            if not isinstance(value, str) or not value:
                errors.append(f"{label}: provenance.{key} must be a non-empty string")
        if provenance.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{label}: invalid provenance.source_type")
        anchor_hash = provenance.get("anchor_hash")
        if isinstance(anchor_hash, str) and len(anchor_hash) < 8:
            errors.append(f"{label}: provenance.anchor_hash must be at least 8 characters")

    assertion_hints, hints_errors = _as_object(
        rule_obj.get("assertion_hints"),
        label=f"{label}: assertion_hints",
    )
    errors.extend(hints_errors)
    if not hints_errors:
        for key in sorted(set(assertion_hints) - {"boolean_checks", "regexes"}):
            errors.append(f"{label}: assertion_hints unknown key {key}")
        if "boolean_checks" in assertion_hints:
            errors.extend(
                _string_list(
                    assertion_hints["boolean_checks"],
                    label=f"{label}: assertion_hints.boolean_checks",
                )
            )
        if "regexes" in assertion_hints:
            regex_values = assertion_hints["regexes"]
            regex_errors = _string_list(
                regex_values,
                label=f"{label}: assertion_hints.regexes",
            )
            errors.extend(regex_errors)
            if not regex_errors and isinstance(regex_values, list):
                for pattern in [item for item in regex_values if isinstance(item, str)]:
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        errors.append(f"{label}: invalid regex {pattern!r}: {exc}")

    if "tags" in rule_obj:
        errors.extend(_string_list(rule_obj["tags"], label=f"{label}: tags"))
    if "notes" in rule_obj and not isinstance(rule_obj["notes"], str):
        errors.append(f"{label}: notes must be a string")

    return rule_id if isinstance(rule_id, str) else None, errors


def validate_alignment_rules(
    *,
    schema_text: str,
    rule_texts: dict[str, str],
) -> list[str]:
    schema, parse_errors = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="alignment rule schema invalid JSON",
        duplicate_prefix="alignment rule schema duplicate key",
    )
    if parse_errors:
        return parse_errors

    errors = validate_alignment_rule_schema(schema_text)
    if errors:
        return errors

    expected_hash = schema_hash(schema)
    seen_ids: dict[str, str] = {}
    for label, rule_text in sorted(rule_texts.items()):
        rule_id, rule_errors = validate_alignment_rule(
            rule_text=rule_text,
            expected_schema_hash=expected_hash,
            label=label,
        )
        errors.extend(rule_errors)
        if rule_id:
            previous = seen_ids.get(rule_id)
            if previous:
                errors.append(f"{label}: duplicate rule_id {rule_id} also used by {previous}")
            else:
                seen_ids[rule_id] = label

    return errors


def _read_rule_files(paths: list[Path]) -> dict[str, str]:
    return {str(path): path.read_text(encoding="utf-8") for path in paths}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Philosophy alignment-rule records.")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--rule", action="append", type=Path, default=[])
    args = parser.parse_args(argv)

    schema_text = args.schema.read_text(encoding="utf-8")
    errors = validate_alignment_rules(
        schema_text=schema_text,
        rule_texts=_read_rule_files(args.rule),
    )
    if errors:
        print("ERROR: philosophy alignment-rule validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    schema_obj, _ = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="alignment rule schema invalid JSON",
        duplicate_prefix="alignment rule schema duplicate key",
    )
    print(f"philosophy alignment-rule schema passed: {args.schema}")
    print(f"schema_hash={schema_hash(schema_obj)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
