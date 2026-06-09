from __future__ import annotations

import json
from pathlib import Path
from collections.abc import MutableMapping
from typing import cast

import pytest

import core.ai.prompt_modules as prompt_modules
from core.ai.prompt_modules import (
    JsonValue,
    PromptModuleRecord,
    PromptModuleRegistry,
    build_prompt_module_record,
    build_prompt_module_registry,
    prompt_module_fingerprints,
    to_stable_mapping,
)
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "core" / "ai" / "prompt_modules.py"
TEXT_FINGERPRINT = "sha256:" + "1" * 64
UNSAFE_METADATA_CASES: tuple[dict[str, JsonValue], ...] = (
    {"raw_prompt": "unsafe"},
    {"nested": {"answer": "unsafe"}},
    {"items": ["Bearer secret"]},
    {"path": "/Users/name/private.txt"},
    {"github": "ghs_header.payload.signature"},
    {"slack": "xoxb-secret"},
    {"contact": "user@example.com"},
    {"phone": "+1 555 123 4567"},
    {"health": "HealthKit diagnosis"},
    {"note": "see(/Users/alice/raw.txt)"},
    {"note": "see:/Users/alice/raw.txt"},
    {"note": "see:file:///tmp/raw.txt"},
)


def _record(module_id: str = "coach-module") -> PromptModuleRecord:
    return build_prompt_module_record(
        module_id=module_id,
        module_version="v1",
        surface="orchestration",
        text_fingerprint=TEXT_FINGERPRINT,
        char_count=120,
        token_estimate=30,
        token_estimate_version="heuristic-tokens-v1",
        policy_version="semantic-cache-cost-o1-v1",
        metadata={"role": "coordinator"},
    )


def test_prompt_module_record_serializes_metadata_only() -> None:
    raw_text = "private instruction body"
    record = _record()
    serialized = json.dumps(dict(to_stable_mapping(record)), sort_keys=True)

    assert record.text_fingerprint == TEXT_FINGERPRINT
    assert raw_text not in serialized
    assert "char_count" in serialized
    assert "token_estimate" in serialized


def test_prompt_module_record_allows_safe_prompt_label_ids() -> None:
    record = build_prompt_module_record(
        module_id="system-prompt",
        module_version="prompt-module-v1",
        surface="orchestration",
        text_fingerprint=TEXT_FINGERPRINT,
        char_count=120,
        token_estimate=30,
        token_estimate_version="heuristic-tokens-v1",
        policy_version="semantic-cache-cost-o1-v1",
        metadata={"role": "coordinator"},
    )

    assert record.module_id == "system-prompt"
    assert record.module_version == "prompt-module-v1"


def test_prompt_module_metadata_allows_non_path_url_like_labels() -> None:
    record = build_prompt_module_record(
        module_id="system-prompt",
        module_version="prompt-module-v1",
        surface="orchestration",
        text_fingerprint=TEXT_FINGERPRINT,
        char_count=120,
        token_estimate=30,
        token_estimate_version="heuristic-tokens-v1",
        policy_version="semantic-cache-cost-o1-v1",
        metadata={"profile_ref": "profile://safe-label"},
    )

    assert record.metadata["profile_ref"] == "profile://safe-label"


def test_prompt_module_metadata_is_deep_frozen_after_validation() -> None:
    record = build_prompt_module_record(
        module_id="system-prompt",
        module_version="prompt-module-v1",
        surface="orchestration",
        text_fingerprint=TEXT_FINGERPRINT,
        char_count=120,
        token_estimate=30,
        token_estimate_version="heuristic-tokens-v1",
        policy_version="semantic-cache-cost-o1-v1",
        metadata={"nested": {"safe": ["label"]}},
    )
    nested = cast(MutableMapping[str, JsonValue], record.metadata["nested"])
    safe_values = cast(list[JsonValue], nested["safe"])

    with pytest.raises(TypeError):
        nested["raw_prompt"] = "unsafe"
    with pytest.raises(AttributeError):
        safe_values.append("unsafe")


def test_prompt_module_metadata_copies_tuple_and_int_values() -> None:
    record = build_prompt_module_record(
        module_id="system-prompt",
        module_version="prompt-module-v1",
        surface="orchestration",
        text_fingerprint=TEXT_FINGERPRINT,
        char_count=120,
        token_estimate=30,
        token_estimate_version="heuristic-tokens-v1",
        policy_version="semantic-cache-cost-o1-v1",
        metadata={"nested": ("safe",), "count": 1},
    )

    assert record.metadata["nested"] == ("safe",)
    assert record.metadata["count"] == 1


def test_prompt_module_registry_identity_is_deterministic() -> None:
    first = build_prompt_module_registry(
        policy_version="semantic-cache-cost-o1-v1",
        records=(_record("b-module"), _record("a-module")),
    )
    second = build_prompt_module_registry(
        policy_version="semantic-cache-cost-o1-v1",
        records=(_record("a-module"), _record("b-module")),
    )

    assert first.registry_id == second.registry_id
    assert tuple(record.module_id for record in first.records) == ("a-module", "b-module")
    assert prompt_module_fingerprints(first.records) == (TEXT_FINGERPRINT,)


def test_prompt_module_registry_hashes_normalized_policy_version() -> None:
    first = build_prompt_module_registry(
        policy_version="semantic-cache-cost-o1-v1",
        records=(_record("a-module"),),
    )
    second = build_prompt_module_registry(
        policy_version=" semantic-cache-cost-o1-v1 ",
        records=(_record("a-module"),),
    )

    assert first.policy_version == second.policy_version
    assert first.registry_id == second.registry_id


def test_prompt_module_registry_derives_id_for_public_constructor() -> None:
    canonical = build_prompt_module_registry(
        policy_version="semantic-cache-cost-o1-v1",
        records=(_record("b-module"), _record("a-module")),
    )
    direct = PromptModuleRegistry(
        registry_id="pm-registry:stale",
        policy_version=" semantic-cache-cost-o1-v1 ",
        records=(_record("a-module"), _record("b-module")),
    )

    assert direct.registry_id == canonical.registry_id
    assert tuple(record.module_id for record in direct.records) == ("a-module", "b-module")


def test_prompt_module_registry_stable_mapping_serializes_registry() -> None:
    registry = build_prompt_module_registry(
        policy_version="semantic-cache-cost-o1-v1",
        records=(_record("b-module"), _record("a-module")),
    )

    stable = to_stable_mapping(registry)

    assert stable["registry_id"] == registry.registry_id
    assert [record["module_id"] for record in stable["records"]] == [
        "a-module",
        "b-module",
    ]


@pytest.mark.parametrize(
    "metadata",
    UNSAFE_METADATA_CASES,
)
def test_prompt_module_metadata_rejects_unsafe_nested_values(
    metadata: dict[str, JsonValue],
) -> None:
    with pytest.raises(ValueError, match="unsafe metadata"):
        build_prompt_module_record(
            module_id="safe-module",
            module_version="v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=120,
            token_estimate=30,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
            metadata=metadata,
        )


def test_prompt_module_validation_fails_closed_for_bad_shapes() -> None:
    with pytest.raises(ValueError, match="sha256 fingerprint"):
        build_prompt_module_record(
            module_id="safe-module",
            module_version="v1",
            surface="orchestration",
            text_fingerprint="not-a-fingerprint",
            char_count=1,
            token_estimate=1,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
        )
    with pytest.raises(ValueError, match="non-negative"):
        build_prompt_module_record(
            module_id="safe-module",
            module_version="v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=-1,
            token_estimate=1,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
        )
    with pytest.raises(ValueError, match="unsupported value"):
        build_prompt_module_record(
            module_id="safe-module",
            module_version="v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=1,
            token_estimate=1,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
            metadata=cast(dict[str, JsonValue], {"bad": 1.2}),
        )


@pytest.mark.parametrize(
    ("module_id", "match"),
    [
        ("", "non-empty"),
        ("safe module", "must not contain whitespace"),
        ("*safe-module", "unsupported characters"),
        ("raw_prompt", "unsafe metadata"),
    ],
)
def test_prompt_module_token_validation_fails_closed(
    module_id: str,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        build_prompt_module_record(
            module_id=module_id,
            module_version="v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=1,
            token_estimate=1,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
        )


def test_prompt_module_validation_rejects_bool_numeric_fields() -> None:
    with pytest.raises(ValueError, match="char_count must be an integer"):
        build_prompt_module_record(
            module_id="safe-module",
            module_version="v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=True,
            token_estimate=1,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
        )


def test_prompt_module_registry_rejects_duplicate_modules() -> None:
    with pytest.raises(ValueError, match="duplicate prompt module"):
        build_prompt_module_registry(
            policy_version="semantic-cache-cost-o1-v1",
            records=(_record("same-module"), _record("same-module")),
        )


def test_prompt_module_registry_rejects_empty_or_malformed_records() -> None:
    with pytest.raises(ValueError, match="records must be non-empty"):
        build_prompt_module_registry(
            policy_version="semantic-cache-cost-o1-v1",
            records=(),
        )
    with pytest.raises(ValueError, match="records must contain PromptModuleRecord"):
        build_prompt_module_registry(
            policy_version="semantic-cache-cost-o1-v1",
            records=(cast(PromptModuleRecord, "not-record"),),
        )
    with pytest.raises(ValueError, match="records must contain PromptModuleRecord"):
        PromptModuleRegistry(
            registry_id="pm-registry:stale",
            policy_version="semantic-cache-cost-o1-v1",
            records=(cast(PromptModuleRecord, "not-record"),),
        )


def test_prompt_module_stable_mapping_rejects_unsupported_values() -> None:
    with pytest.raises(ValueError, match="unsupported stable mapping"):
        to_stable_mapping(object())


def test_prompt_module_metadata_validation_rejects_non_mapping_input() -> None:
    with pytest.raises(ValueError, match="metadata must be a mapping"):
        prompt_modules._freeze_metadata(cast(dict[str, JsonValue], "not-mapping"))


def test_prompt_module_metadata_validation_rejects_non_mapping_freeze(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompt_modules, "_deep_freeze_json", lambda value: "not-mapping")

    with pytest.raises(ValueError, match="metadata must be a mapping"):
        prompt_modules._freeze_metadata({"safe": "label"})


def test_prompt_modules_have_no_runtime_imports_or_calls() -> None:
    assert_no_forbidden_semantic_cache_imports(MODULE)
    assert_no_forbidden_semantic_cache_calls(MODULE)
