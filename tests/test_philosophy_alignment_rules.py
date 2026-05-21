from __future__ import annotations

import json
from pathlib import Path

from pytest import CaptureFixture

from scripts.ci.check_philosophy_alignment_rules import (
    main as alignment_rules_main,
    schema_hash,
    validate_alignment_rule_schema,
    validate_alignment_rules,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "PHILOSOPHY_ALIGNMENT_RULE.schema.json"
)


def _schema_text() -> str:
    return SCHEMA.read_text(encoding="utf-8")


def _schema() -> dict[str, object]:
    schema = json.loads(_schema_text())
    assert isinstance(schema, dict)
    return schema


def _rule(**overrides: object) -> dict[str, object]:
    rule: dict[str, object] = {
        "rule_id": "wellness_scope.no_medical_claims",
        "rule_text": "PulsePlate must not present wellness planning as diagnosis or treatment.",
        "rule_type": "wellness_scope",
        "severity": "block",
        "provenance": {
            "source_id": "AGENTS.md",
            "source_type": "repo",
            "version": "commit-4d0a54c0",
            "anchor_hash": "wellness-only-boundary-v1",
        },
        "assertion_hints": {
            "boolean_checks": ["semantic_cache_gate_closed"],
            "regexes": ["(?i)diagnosis|treatment"],
        },
        "created_by": "agent-coordinator",
        "created_at": "2026-05-21T00:00:00Z",
        "schema_version": "v1.0.0",
        "schema_hash": schema_hash(_schema()),
        "tags": ["philosophy", "semantic-cache", "wellness"],
    }
    rule.update(overrides)
    return rule


def _validate(rule: dict[str, object]) -> list[str]:
    return validate_alignment_rules(
        schema_text=_schema_text(),
        rule_texts={"rule.json": json.dumps(rule, sort_keys=True)},
    )


def test_alignment_rule_schema_is_current() -> None:
    assert validate_alignment_rule_schema(_schema_text()) == []


def test_valid_alignment_rule_passes() -> None:
    assert _validate(_rule()) == []


def test_alignment_rule_rejects_schema_hash_drift() -> None:
    errors = _validate(_rule(schema_hash="0" * 64))

    assert "rule.json: schema_hash mismatch" in errors


def test_alignment_rule_rejects_invalid_regex() -> None:
    rule = _rule(assertion_hints={"regexes": ["["]})

    errors = _validate(rule)

    assert any("invalid regex '['" in error for error in errors)


def test_alignment_rule_rejects_invalid_created_at() -> None:
    errors = _validate(_rule(created_at="not-a-date"))

    assert "rule.json: created_at must be a valid date-time" in errors


def test_alignment_rule_rejects_date_only_created_at() -> None:
    errors = _validate(_rule(created_at="2026-05-21"))

    assert "rule.json: created_at must be a valid date-time" in errors


def test_alignment_rule_rejects_space_separated_created_at() -> None:
    errors = _validate(_rule(created_at="2026-05-21 00:00:00"))

    assert "rule.json: created_at must be a valid date-time" in errors


def test_alignment_rule_rejects_timestamp_without_timezone() -> None:
    errors = _validate(_rule(created_at="2026-05-21T00:00:00"))

    assert "rule.json: created_at must be a valid date-time" in errors


def test_alignment_rule_rejects_duplicate_rule_ids() -> None:
    rule_text = json.dumps(_rule(), sort_keys=True)

    errors = validate_alignment_rules(
        schema_text=_schema_text(),
        rule_texts={"a.json": rule_text, "b.json": rule_text},
    )

    assert (
        "b.json: duplicate rule_id wellness_scope.no_medical_claims also used by a.json" in errors
    )


def test_alignment_rule_rejects_unknown_provenance_key() -> None:
    provenance = {
        "source_id": "AGENTS.md",
        "source_type": "repo",
        "version": "commit-4d0a54c0",
        "anchor_hash": "wellness-only-boundary-v1",
        "extra": "not allowed",
    }

    errors = _validate(_rule(provenance=provenance))

    assert "rule.json: provenance unknown key extra" in errors


def test_alignment_rule_rejects_non_string_notes() -> None:
    errors = _validate(_rule(notes=123))

    assert "rule.json: notes must be a string" in errors


def test_alignment_rule_schema_rejects_provenance_required_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    provenance = properties["provenance"]
    assert isinstance(provenance, dict)
    provenance["required"] = ["source_id"]

    errors = validate_alignment_rule_schema(json.dumps(schema, sort_keys=True))

    assert "alignment provenance schema required keys mismatch" in errors


def test_alignment_rule_schema_rejects_identity_drift() -> None:
    schema = _schema()
    schema["$id"] = "https://example.invalid/wrong.json"
    schema["title"] = "WrongSchema"

    errors = validate_alignment_rule_schema(json.dumps(schema, sort_keys=True))

    assert "alignment rule schema $id mismatch" in errors
    assert "alignment rule schema title mismatch" in errors


def test_alignment_rule_schema_rejects_created_at_format_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    created_at = properties["created_at"]
    assert isinstance(created_at, dict)
    del created_at["format"]

    errors = validate_alignment_rule_schema(json.dumps(schema, sort_keys=True))

    assert "alignment schema property created_at format mismatch" in errors


def test_alignment_rule_schema_rejects_created_at_pattern_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    created_at = properties["created_at"]
    assert isinstance(created_at, dict)
    del created_at["pattern"]

    errors = validate_alignment_rule_schema(json.dumps(schema, sort_keys=True))

    assert "alignment schema property created_at pattern mismatch" in errors


def test_alignment_rule_schema_rejects_rule_id_pattern_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    rule_id = properties["rule_id"]
    assert isinstance(rule_id, dict)
    del rule_id["pattern"]

    errors = validate_alignment_rule_schema(json.dumps(schema, sort_keys=True))

    assert "alignment schema property rule_id pattern mismatch" in errors


def test_alignment_rule_schema_rejects_regex_item_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assertion_hints = properties["assertion_hints"]
    assert isinstance(assertion_hints, dict)
    hint_props = assertion_hints["properties"]
    assert isinstance(hint_props, dict)
    regexes = hint_props["regexes"]
    assert isinstance(regexes, dict)
    regexes["items"] = {"type": "number"}

    errors = validate_alignment_rule_schema(json.dumps(schema, sort_keys=True))

    assert "alignment schema property regexes.items type must be string" in errors


def test_alignment_rule_schema_rejects_tags_unique_items_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    tags = properties["tags"]
    assert isinstance(tags, dict)
    del tags["uniqueItems"]

    errors = validate_alignment_rule_schema(json.dumps(schema, sort_keys=True))

    assert "alignment schema property tags uniqueItems mismatch" in errors


def test_alignment_rule_cli_prints_schema_hash(capsys: CaptureFixture[str]) -> None:
    exit_code = alignment_rules_main(["--schema", str(SCHEMA)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "philosophy alignment-rule schema passed:" in captured.out
    assert f"schema_hash={schema_hash(_schema())}" in captured.out
