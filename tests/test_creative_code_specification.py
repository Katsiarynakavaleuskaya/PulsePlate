from __future__ import annotations

from copy import deepcopy
import ast
import json
import os
import re
import shutil
import uuid
from pathlib import Path

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_spec_pipeline, creative_code_specification
from scripts.orchestration.creative_code_contract import read_creative_code_candidate_packet
from scripts.orchestration.creative_code_rejection_index import (
    CreativeCodeRejectionIndexError,
    read_creative_code_rejection_index,
    validate_creative_code_rejection_index,
)
from scripts.orchestration.creative_code_spec_pipeline import CreativeCodeSpecPipelineError
from scripts.orchestration.creative_code_specification import (
    AUTHORITY_FALSE_KEYS_PR1,
    CreativeCodeSpecificationError,
    build_creative_code_specification_bundle,
    build_default_specification_variants,
    build_exact_specification_variants,
    build_pending_skeptic_reviews,
    contains_unsafe_local_absolute_path,
    read_creative_code_specification_bundle,
    validate_creative_code_specification_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PACKET = REPO_ROOT / "docs/orchestration/contracts/creative_code_candidate.v1.json"
REFERENCE_BUNDLE = REPO_ROOT / "docs/orchestration/contracts/creative_code_specification.v1.json"
SCHEMA = REPO_ROOT / "docs/orchestration/contracts/creative_code_specification.v1.schema.json"
SPEC_MODULE = REPO_ROOT / "scripts/orchestration/creative_code_specification.py"
PIPELINE_MODULE = REPO_ROOT / "scripts/orchestration/creative_code_spec_pipeline.py"
REJECTION_MODULE = REPO_ROOT / "scripts/orchestration/creative_code_rejection_index.py"
REVIEW_FINALIZE_MODULE = (
    REPO_ROOT / "scripts/orchestration/creative_specification_skeptic_review.py"
)
REVIEW_FINALIZE_CONTRACT_MODULE = (
    REPO_ROOT / "scripts/orchestration/creative_specification_skeptic_review_contract.py"
)
UNSAFE_LOCAL_PATH_TEXTS = (
    "See local path /Users/example/project/.env",
    "Read /home/runner/.ssh/id_rsa for credentials.",
    "Inspect /etc/passwd before generating the spec.",
    "Use /workspace/project/.env as runtime input.",
    "Write output to /tmp/pulseplate.sock.",
    "Load ~/.ssh/config for GitHub access.",
    'Use "/home/runner/.ssh/id_rsa" in the prompt.',
    "Read `/etc/passwd` for credentials.",
    "See (/tmp) before cleanup.",
    "Files in /tmp, then clean up.",
    "Files in /tmp; then clean up.",
    r"Read C:\Users\alice\.ssh\id_ed25519.",
    "Read C:/Users/alice/.ssh/id_ed25519.",
    r"Use \\server\share\secrets.txt.",
)


def _packet() -> dict[str, object]:
    return read_creative_code_candidate_packet(REFERENCE_PACKET)


def _bundle() -> dict[str, object]:
    return read_creative_code_specification_bundle(REFERENCE_BUNDLE)


def _fingerprint_review(review: dict[str, object]) -> dict[str, object]:
    payload = {
        key: review[key]
        for key in sorted(
            creative_code_specification.REVIEW_KEYS - {"review_id", "review_fingerprint"}
        )
    }
    review["review_fingerprint"] = fingerprint_payload(payload)
    return review


def _fingerprint_variant(variant: dict[str, object]) -> dict[str, object]:
    payload = {
        key: variant[key]
        for key in sorted(
            creative_code_specification.VARIANT_KEYS - {"variant_id", "variant_fingerprint"}
        )
    }
    variant["variant_fingerprint"] = fingerprint_payload(payload)
    return variant


def _schema_safe_text_rejects(value: str) -> bool:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    safe_text = schema["$defs"]["safe_text"]
    assert safe_text["type"] == "string"
    assert safe_text["minLength"] == 1
    return any(
        re.search(str(guard["not"]["pattern"]), value) is not None for guard in safe_text["allOf"]
    )


def _schema_rejection_label_rejects(value: str) -> bool:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    rejection_safe_id = schema["$defs"]["rejection_safe_id"]
    return any(
        re.search(str(guard["not"]["pattern"]), value) is not None
        for guard in rejection_safe_id["allOf"]
        if "not" in guard
    )


def _reviewed_bundle_inputs() -> (
    tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]
):
    packet = _packet()
    variants = build_default_specification_variants(packet)
    reviews: list[dict[str, object]] = []
    for review in build_pending_skeptic_reviews(source_packet=packet, variants=variants):
        review = dict(review)
        if review["variant_id"] == variants[0]["variant_id"]:
            review["decision"] = "pass"
            review["blockers"] = []
        else:
            review["blockers"] = ["skeptic_rejected_variant"]
        reviews.append(_fingerprint_review(review))
    return packet, variants, reviews


def test_reference_bundle_schema_and_validator_are_aligned() -> None:
    bundle = _bundle()
    normalized = validate_creative_code_specification_bundle(bundle)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert normalized["bundle_type"] == "creative_code_specification_bundle"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["authority"]["$ref"] == "#/$defs/authority"
    assert schema["$defs"]["authority"]["additionalProperties"] is False
    assert schema["$defs"]["variant"]["additionalProperties"] is False
    assert schema["$defs"]["skeptic_review"]["additionalProperties"] is False
    assert schema["$defs"]["rejection_index"]["additionalProperties"] is False
    assert schema["$defs"]["telemetry_summary"]["additionalProperties"] is False
    assert schema["$defs"]["text_array"]["items"]["$ref"] == "#/$defs/safe_text"
    assert schema["$defs"]["variant"]["properties"]["problem_statement"]["$ref"] == (
        "#/$defs/safe_text"
    )
    assert schema["$defs"]["skeptic_review"]["properties"]["duplicate_reason"]["$ref"] == (
        "#/$defs/safe_text"
    )
    assert schema["$defs"]["skeptic_review"]["properties"]["required_revision"]["$ref"] == (
        "#/$defs/safe_text"
    )
    assert schema["$defs"]["variant"]["properties"]["tests_to_add"]["$ref"] == (
        "#/$defs/non_empty_test_paths"
    )
    assert (
        schema["$defs"]["rejection_index"]["properties"]["records"]["items"]["properties"][
            "reason_codes"
        ]["$ref"]
        == "#/$defs/rejection_token_array"
    )
    assert "pattern" in schema["$defs"]["path"]
    assert schema["properties"]["cost_metadata_available"]["const"] is False
    assert normalized["synthesis"]["selected_variant_id"] == "creative-code-pr0-reference:spec-1"


def test_schema_review_count_constraints_scale_with_variant_count() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    constraints: dict[int, tuple[int, int]] = {}
    for rule in schema["allOf"]:
        variant_count = rule["if"]["properties"]["variants"]["minItems"]
        assert rule["if"]["required"] == ["variants"]
        assert rule["if"]["properties"]["variants"]["maxItems"] == variant_count
        review_rules = rule["then"]["properties"]["skeptic_reviews"]
        constraints[variant_count] = (review_rules["minItems"], review_rules["maxItems"])

    assert constraints == {3: (9, 9), 4: (12, 12), 5: (15, 15)}


def test_builder_replays_reference_bundle_deterministically() -> None:
    packet, variants, reviews = _reviewed_bundle_inputs()

    first = build_creative_code_specification_bundle(
        source_packet=packet,
        variants=variants,
        skeptic_reviews=reviews,
    )
    second = build_creative_code_specification_bundle(
        source_packet=packet,
        variants=variants,
        skeptic_reviews=reviews,
    )

    assert first == second
    assert first == _bundle()


def test_cli_valid_reference_bundle_outputs_exact_pass(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = creative_code_specification.main(["--validate", str(REFERENCE_BUNDLE)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "PASS: creative-code specification bundle valid"
    assert captured.err == ""


def test_cli_reports_duplicate_json_keys_on_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    duplicate = tmp_path / "bundle.json"
    duplicate.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    exit_code = creative_code_specification.main(["--validate", str(duplicate)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "duplicate JSON key: schema_version" in captured.err
    assert captured.err.count("\n") == 1


def test_unknown_nested_variant_fields_fail_closed() -> None:
    bundle = _bundle()
    variants = bundle["variants"]
    assert isinstance(variants, list)
    variant = variants[0]
    assert isinstance(variant, dict)
    variant["candidate_patch"] = "not allowed"

    with pytest.raises(CreativeCodeSpecificationError, match="unsupported fields"):
        validate_creative_code_specification_bundle(bundle)


@pytest.mark.parametrize("authority_key", AUTHORITY_FALSE_KEYS_PR1)
def test_authority_flags_fail_closed(authority_key: str) -> None:
    bundle = _bundle()
    authority = bundle["authority"]
    assert isinstance(authority, dict)
    authority[authority_key] = True

    with pytest.raises(
        CreativeCodeSpecificationError,
        match=f"authority.{authority_key} must remain false in PR-1",
    ):
        validate_creative_code_specification_bundle(bundle)


def test_bool_like_telemetry_fields_fail_closed() -> None:
    bundle = _bundle()
    telemetry = bundle["telemetry_summary"]
    assert isinstance(telemetry, dict)
    telemetry["variant_count"] = True

    with pytest.raises(CreativeCodeSpecificationError, match="variant_count must be an integer"):
        validate_creative_code_specification_bundle(bundle)


def test_duplicate_approach_families_fail_closed() -> None:
    bundle = _bundle()
    variants = bundle["variants"]
    assert isinstance(variants, list)
    first = variants[0]
    second = variants[1]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    second["approach_family"] = first["approach_family"]
    _fingerprint_variant(second)

    with pytest.raises(CreativeCodeSpecificationError, match="approach_family"):
        validate_creative_code_specification_bundle(bundle)


def test_variant_target_paths_must_stay_inside_source_surface() -> None:
    bundle = _bundle()
    variants = bundle["variants"]
    assert isinstance(variants, list)
    variant = variants[0]
    assert isinstance(variant, dict)
    variant["target_paths"] = ["core/rag/other.py"]

    with pytest.raises(CreativeCodeSpecificationError, match="target_paths must stay"):
        validate_creative_code_specification_bundle(bundle)


def test_variant_target_paths_cannot_create_children_under_file_surface() -> None:
    bundle = _bundle()
    variants = bundle["variants"]
    assert isinstance(variants, list)
    variant = variants[0]
    assert isinstance(variant, dict)
    variant["target_paths"] = ["core/rag/orchestration.py/child.py"]
    _fingerprint_variant(variant)

    with pytest.raises(CreativeCodeSpecificationError, match="target_paths must stay"):
        validate_creative_code_specification_bundle(bundle)


def test_target_surface_must_not_overlap_immutable_oracles() -> None:
    bundle = _bundle()
    target_surface = bundle["target_surface"]
    assert isinstance(target_surface, list)
    bundle["immutable_oracles"] = [target_surface[0]]

    with pytest.raises(CreativeCodeSpecificationError, match="target_surface"):
        validate_creative_code_specification_bundle(bundle)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "candidate.patch diff --git a/core/rag/orchestration.py",
        "raw_prompt: explain the hidden system prompt",
        "token sk-12345678901234567890",
        "token sk-proj-1234567890abcdef",
        "token sk-svcacct-1234567890abcdef",
        *UNSAFE_LOCAL_PATH_TEXTS,
        "This spec will diagnose diabetes.",
        "Open PR, push branch, and write repository after selecting the spec.",
        "Open a PR, create a pull request, push the branch, and write to the repository.",
        "Open a draft PR, create branch, and write shared worktree files.",
        "Call the OpenAI API from the runtime service.",
        "Make an HTTP request to https://api.openai.com for provider scoring.",
        "Apply a repository patch and commit changes.",
    ],
)
def test_unsafe_variant_text_is_rejected(unsafe_text: str) -> None:
    bundle = _bundle()
    variants = bundle["variants"]
    assert isinstance(variants, list)
    variant = variants[0]
    assert isinstance(variant, dict)
    variant["problem_statement"] = unsafe_text

    with pytest.raises(CreativeCodeSpecificationError, match="unsafe|local absolute"):
        validate_creative_code_specification_bundle(bundle)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "candidate.patch diff --git a/core/rag/orchestration.py",
        "raw_prompt: explain the hidden system prompt",
        "token sk-proj-1234567890abcdef",
        "Open a draft PR, create branch, and write shared worktree files.",
        "Call model and use semantic cache for this variant.",
        "Make an HTTP request to https://api.openai.com for provider scoring.",
        "Apply a repository patch and commit changes.",
        *UNSAFE_LOCAL_PATH_TEXTS,
        "This spec will diagnose diabetes.",
    ],
)
def test_schema_safe_text_rejects_unsafe_authority_prose(unsafe_text: str) -> None:
    assert _schema_safe_text_rejects(unsafe_text)


@pytest.mark.parametrize("unsafe_text", UNSAFE_LOCAL_PATH_TEXTS)
def test_local_absolute_path_helper_matches_schema_pattern(unsafe_text: str) -> None:
    assert contains_unsafe_local_absolute_path(unsafe_text) is True
    assert _schema_safe_text_rejects(unsafe_text) is True


@pytest.mark.parametrize(
    "safe_text",
    [
        "Use docs/orchestration/contracts/creative_code_specification.v1.json.",
        "Add tests/test_creative_code_specification.py coverage.",
        "Review core/rag/orchestration.py without local absolute paths.",
    ],
)
def test_local_absolute_path_helper_allows_repo_relative_text(safe_text: str) -> None:
    assert contains_unsafe_local_absolute_path(safe_text) is False
    assert _schema_safe_text_rejects(safe_text) is False


def test_variant_tests_to_add_must_stay_under_tests() -> None:
    bundle = _bundle()
    variants = bundle["variants"]
    assert isinstance(variants, list)
    variant = variants[0]
    assert isinstance(variant, dict)
    variant["tests_to_add"] = ["ios/PulsePlate/App.swift"]

    with pytest.raises(CreativeCodeSpecificationError, match="tests_to_add"):
        validate_creative_code_specification_bundle(bundle)


def test_all_rejected_is_valid_terminal_state() -> None:
    packet = _packet()
    variants = build_default_specification_variants(packet)
    reviews = build_pending_skeptic_reviews(source_packet=packet, variants=variants)

    bundle = build_creative_code_specification_bundle(
        source_packet=packet,
        variants=variants,
        skeptic_reviews=reviews,
    )

    assert bundle["generation_status"] == "all_rejected"
    assert bundle["oracle_status"] == "skeptic_review_blocked"
    assert bundle["failure_class"] == "review_blocker"
    assert bundle["human_decision"] == "review_required"
    assert bundle["synthesis"]["selected_variant_id"] is None
    assert bundle["rejection_index"]["records"]
    assert validate_creative_code_specification_bundle(bundle) == bundle


def test_selected_rejected_variant_is_banned() -> None:
    bundle = _bundle()
    synthesis = bundle["synthesis"]
    variants = bundle["variants"]
    assert isinstance(synthesis, dict)
    assert isinstance(variants, list)
    rejected = variants[1]
    assert isinstance(rejected, dict)
    synthesis["selected_variant_id"] = rejected["variant_id"]

    with pytest.raises(CreativeCodeSpecificationError, match="deterministic PR-1 synthesis"):
        validate_creative_code_specification_bundle(bundle)


def test_rejection_index_is_fingerprint_only() -> None:
    bundle = _bundle()
    rejection_index = bundle["rejection_index"]
    assert isinstance(rejection_index, dict)
    serialized = json.dumps(rejection_index, sort_keys=True)

    assert "candidate.patch" not in serialized
    assert "raw_prompt" not in serialized
    assert "provider_payload" not in serialized
    assert "/Users/" not in serialized
    assert "sk-" not in serialized
    assert "sha256:" in serialized
    assert validate_creative_code_rejection_index(rejection_index) == rejection_index


def test_rejection_index_duplicate_keys_fail_closed(
    tmp_path: Path,
) -> None:
    duplicate = tmp_path / "rejection-index.json"
    duplicate.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(CreativeCodeRejectionIndexError, match="duplicate JSON key"):
        read_creative_code_rejection_index(duplicate)


@pytest.mark.parametrize(
    ("field", "unsafe_value"),
    [
        ("source_packet_id", "sk-test-placeholder-not-a-secret"),
        ("variant_id", "sk-test-placeholder-not-a-secret"),
        ("variant_id", "github:write"),
        ("reason_codes", "ghp_placeholder_not_a_secret"),
        ("reason_codes", "provider_payload"),
        ("reviewer_roles", "slack:admin"),
    ],
)
def test_rejection_index_rejects_unsafe_ids_and_tokens(
    field: str,
    unsafe_value: str,
) -> None:
    rejection_index = deepcopy(_bundle()["rejection_index"])
    assert isinstance(rejection_index, dict)
    records = rejection_index["records"]
    assert isinstance(records, list)
    first_record = records[0]
    assert isinstance(first_record, dict)
    if field == "source_packet_id":
        rejection_index[field] = unsafe_value
    elif field == "variant_id":
        first_record[field] = unsafe_value
    else:
        first_record[field] = [unsafe_value]

    with pytest.raises(CreativeCodeRejectionIndexError, match="unsafe"):
        validate_creative_code_rejection_index(rejection_index)


def test_spec_rejects_secret_shaped_review_tokens_before_rejection_index() -> None:
    bundle = _bundle()
    reviews = bundle["skeptic_reviews"]
    assert isinstance(reviews, list)
    review = reviews[0]
    assert isinstance(review, dict)
    review["blockers"] = ["ghp_placeholder_not_a_secret"]

    with pytest.raises(CreativeCodeSpecificationError, match="secret-shaped"):
        validate_creative_code_specification_bundle(bundle)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "sk-test-placeholder-not-a-secret",
        "github:write",
        "provider_payload",
        "openai:gpt-5",
        "slack:admin",
    ],
)
def test_schema_rejection_labels_reject_unsafe_authority_tokens(unsafe_value: str) -> None:
    assert _schema_rejection_label_rejects(unsafe_value)


def test_pipeline_prepare_and_finalize_write_valid_bundle() -> None:
    run_dir = creative_code_spec_pipeline.ARTIFACT_ROOT / f"pytest-{uuid.uuid4().hex}"
    try:
        creative_code_spec_pipeline.prepare(REFERENCE_PACKET, run_dir)
        reviews_path = run_dir / "skeptic_reviews.json"
        reviews = json.loads(reviews_path.read_text(encoding="utf-8"))
        variants = json.loads((run_dir / "variants.json").read_text(encoding="utf-8"))
        for review in reviews:
            if review["variant_id"] == variants[0]["variant_id"]:
                review["decision"] = "pass"
                review["blockers"] = []
            review = _fingerprint_review(review)
        reviews_path.write_text(json.dumps(reviews, indent=2, sort_keys=True) + "\n")

        output = run_dir / "bundle.json"
        creative_code_spec_pipeline.finalize(run_dir, output)

        bundle = read_creative_code_specification_bundle(output)
        assert validate_creative_code_specification_bundle(bundle) == bundle
        assert bundle["synthesis"]["selected_variant_id"] == variants[0]["variant_id"]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_default_variants_do_not_share_mutable_lists() -> None:
    variants = build_default_specification_variants(_packet())
    first = variants[0]
    second = variants[1]
    for field in ("target_paths", "tests_to_add", "negative_controls"):
        assert isinstance(first[field], list)
        assert isinstance(second[field], list)
        assert first[field] is not second[field]

    first["target_paths"].append(
        "docs/orchestration/contracts/CREATIVE_CODE_SPECIFICATION_CONTRACT.md"
    )

    assert (
        "docs/orchestration/contracts/CREATIVE_CODE_SPECIFICATION_CONTRACT.md"
        not in second["target_paths"]
    )


def _exact_declarations(packet: dict[str, object]) -> list[dict[str, object]]:
    targets = list(packet["target_surface"])
    tests = list(packet["evidence_bundle"]["required_tests"])
    return [
        {
            "approach_family": family,
            "problem_statement": f"Bounded exact {family} specification.",
            "implementation_steps": [f"Apply only the declared {family} contract."],
            "target_paths": list(targets),
            "tests_to_add": list(tests),
            "negative_controls": ["runtime_behavior_unchanged", "immutable_oracles_unchanged"],
            "rollback_plan": "Discard the specification before patch generation.",
            "falsifier": "Reject any changed runtime value or extra path.",
            "risk_notes": ["Specification-only control-plane artifact."],
            "wellness_boundary": "No medical or health outcome claim.",
            "estimated_changed_files": len(targets),
        }
        for family in ("fail_closed_guard", "minimal_surgical_change", "seam_extraction")
    ]


def test_exact_variants_are_canonical_and_tokenized() -> None:
    packet = _packet()
    variants = build_exact_specification_variants(packet, _exact_declarations(packet))
    assert [row["approach_family"] for row in variants] == [
        "minimal_surgical_change",
        "seam_extraction",
        "fail_closed_guard",
    ]
    assert all(set(row) == creative_code_specification.VARIANT_KEYS for row in variants)
    assert all(
        row["negative_controls"] == ["runtime_behavior_unchanged", "immutable_oracles_unchanged"]
        for row in variants
    )

    invalid = _exact_declarations(packet)
    invalid[0]["negative_controls"] = [
        "runtime behavior unchanged",
        "immutable_oracles_unchanged",
    ]
    with pytest.raises(CreativeCodeSpecificationError, match="must be a safe token"):
        build_exact_specification_variants(packet, invalid)

    substituted = _exact_declarations(packet)
    substituted[0]["approach_family"] = "observable_metadata_only"
    with pytest.raises(
        CreativeCodeSpecificationError,
        match=r"APPROACH_FAMILIES\[:variant_count\]",
    ):
        build_exact_specification_variants(packet, substituted)


def test_exact_variant_declaration_requires_two_negative_controls() -> None:
    packet = _packet()
    declarations = _exact_declarations(packet)
    declarations[0]["negative_controls"] = ["runtime_behavior_unchanged"]
    with pytest.raises(
        CreativeCodeSpecificationError,
        match="require at least two negative_controls",
    ):
        build_exact_specification_variants(packet, declarations)


def test_prepare_exact_preserves_legacy_prepare_and_rejects_test_drift() -> None:
    packet = _packet()
    root = creative_code_spec_pipeline.ARTIFACT_ROOT / f"pytest-{uuid.uuid4().hex}"
    declarations_path = root / "declarations.json"
    exact_dir = root / "exact"
    legacy_dir = root / "legacy"
    try:
        root.mkdir(parents=True)
        declarations_path.write_text(json.dumps(_exact_declarations(packet)), encoding="utf-8")
        creative_code_spec_pipeline.prepare_exact(REFERENCE_PACKET, declarations_path, exact_dir)
        creative_code_spec_pipeline.prepare(REFERENCE_PACKET, legacy_dir)
        exact = json.loads((exact_dir / "variants.json").read_text(encoding="utf-8"))
        legacy = json.loads((legacy_dir / "variants.json").read_text(encoding="utf-8"))
        assert exact[0]["problem_statement"].startswith("Bounded exact")
        assert legacy[0]["problem_statement"].startswith("Convert the promoted")
        creative_code_spec_pipeline.validate_exact_prepare_artifacts(
            run_dir=exact_dir,
            expected_packet=packet,
            expected_variants=exact,
        )
        tamper_cases = {
            "source_packet.json": "adaptive_prepare_source_packet_mismatch",
            "variants.json": "adaptive_prepare_variants_mismatch",
            "skeptic_reviews.json": "adaptive_prepare_reviews_mismatch",
            "context_pack.json": "adaptive_prepare_context_mismatch",
        }
        for filename, failure_code in tamper_cases.items():
            sidecar = exact_dir / filename
            original = sidecar.read_bytes()
            payload = json.loads(original)
            if isinstance(payload, list):
                payload.append(deepcopy(payload[-1]))
            else:
                payload["tampered"] = True
            sidecar.write_text(json.dumps(payload), encoding="utf-8")
            with pytest.raises(CreativeCodeSpecPipelineError, match=failure_code):
                creative_code_spec_pipeline.validate_exact_prepare_artifacts(
                    run_dir=exact_dir,
                    expected_packet=packet,
                    expected_variants=exact,
                )
            sidecar.write_bytes(original)

        drifted = _exact_declarations(packet)
        drifted[0]["tests_to_add"] = ["tests/test_other.py"]
        declarations_path.write_text(json.dumps(drifted), encoding="utf-8")
        with pytest.raises(CreativeCodeSpecificationError, match="equal source required_tests"):
            creative_code_spec_pipeline.prepare_exact(
                REFERENCE_PACKET, declarations_path, root / "drifted"
            )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_prepare_snapshot_validation_rejects_json_number_type_drift() -> None:
    packet = _packet()
    default_snapshots = creative_code_spec_pipeline.build_default_prepare_artifacts(packet)
    default_snapshots["source_packet.json"]["variant_count"] = 3.0
    with pytest.raises(
        CreativeCodeSpecPipelineError,
        match="retained source_packet.json is not canonical",
    ):
        creative_code_spec_pipeline.validate_default_prepare_artifact_snapshots(
            default_snapshots,
            expected_packet=packet,
        )

    variants = build_exact_specification_variants(packet, _exact_declarations(packet))
    exact_snapshots = {
        "source_packet.json": {**packet, "variant_count": 3.0},
        "variants.json": variants,
        "skeptic_reviews.json": build_pending_skeptic_reviews(
            source_packet=packet,
            variants=variants,
        ),
        "context_pack.json": creative_code_spec_pipeline._context_pack_for_packet(packet),
    }
    with pytest.raises(
        CreativeCodeSpecPipelineError,
        match="adaptive_prepare_source_packet_mismatch",
    ):
        creative_code_spec_pipeline.validate_exact_prepare_artifact_snapshots(
            snapshots=exact_snapshots,
            expected_packet=packet,
            expected_variants=variants,
        )

    for non_finite in (float("nan"), float("inf"), float("-inf")):
        non_finite_snapshots = creative_code_spec_pipeline.build_default_prepare_artifacts(packet)
        non_finite_snapshots["source_packet.json"]["variant_count"] = non_finite
        with pytest.raises(
            CreativeCodeSpecPipelineError,
            match="retained source_packet.json is not canonical",
        ):
            creative_code_spec_pipeline.validate_default_prepare_artifact_snapshots(
                non_finite_snapshots,
                expected_packet=packet,
            )


def test_pipeline_rejects_symlinked_artifact_directory(tmp_path: Path) -> None:
    creative_code_spec_pipeline.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    link = creative_code_spec_pipeline.ARTIFACT_ROOT / f"pytest-link-{uuid.uuid4().hex}"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(CreativeCodeSpecPipelineError, match="symlinks"):
            creative_code_spec_pipeline.prepare(REFERENCE_PACKET, link)
    finally:
        if link.is_symlink():
            link.unlink()


def test_pipeline_rejects_symlinked_artifact_root_before_creating_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "artifact-root-link"
    link.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(
        creative_code_spec_pipeline,
        "ARTIFACT_ROOT",
        link / "orchestration" / "creative_code",
    )

    with pytest.raises(CreativeCodeSpecPipelineError, match="artifact root"):
        creative_code_spec_pipeline.prepare(REFERENCE_PACKET, Path("pytest-run"))

    assert not (outside / "orchestration").exists()


def test_pipeline_rejects_absolute_artifact_paths_without_creating_them(
    tmp_path: Path,
) -> None:
    outside_run_dir = tmp_path / "outside-run-dir"
    outside_output_dir = tmp_path / "outside-output"

    with pytest.raises(CreativeCodeSpecPipelineError, match="artifact directory"):
        creative_code_spec_pipeline.prepare(REFERENCE_PACKET, outside_run_dir)

    assert not outside_run_dir.exists()

    run_dir = creative_code_spec_pipeline.ARTIFACT_ROOT / f"pytest-{uuid.uuid4().hex}"
    try:
        creative_code_spec_pipeline.prepare(REFERENCE_PACKET, run_dir)
        with pytest.raises(CreativeCodeSpecPipelineError, match="artifact file"):
            creative_code_spec_pipeline.finalize(run_dir, outside_output_dir / "bundle.json")
        assert not outside_output_dir.exists()
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_pipeline_rejects_traversal_artifact_paths_without_creating_them() -> None:
    traversal_name = f"pytest-traversal-{uuid.uuid4().hex}"
    traversal_parent = creative_code_spec_pipeline.ARTIFACT_ROOT.parent / traversal_name

    with pytest.raises(CreativeCodeSpecPipelineError, match="artifact directory"):
        creative_code_spec_pipeline.prepare(REFERENCE_PACKET, Path("..") / traversal_name)

    assert not traversal_parent.exists()


def test_pipeline_writer_rejects_parent_swap_without_writing_outside(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = creative_code_spec_pipeline.ARTIFACT_ROOT / f"pytest-{uuid.uuid4().hex}"
    moved_dir = run_dir.with_name(f"{run_dir.name}-pinned")
    outside = tmp_path / "outside"
    outside.mkdir()
    run_dir.mkdir(parents=True)
    target = run_dir / "result.json"
    real_resolve = creative_code_spec_pipeline._resolve_artifact_file

    def resolve_then_swap(path: Path, *, for_write: bool) -> Path:
        output = real_resolve(path, for_write=for_write)
        run_dir.rename(moved_dir)
        run_dir.symlink_to(outside, target_is_directory=True)
        return output

    try:
        monkeypatch.setattr(
            creative_code_spec_pipeline, "_resolve_artifact_file", resolve_then_swap
        )
        with pytest.raises(CreativeCodeSpecPipelineError, match="symlinks"):
            creative_code_spec_pipeline._write_json_atomic(target, {"safe": True})
        assert not (outside / "result.json").exists()
    finally:
        if run_dir.is_symlink():
            run_dir.unlink()
        shutil.rmtree(moved_dir, ignore_errors=True)


def test_pipeline_pinned_traversal_closes_child_on_transfer_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = creative_code_spec_pipeline.ARTIFACT_ROOT / "fd-transfer" / "result.json"
    real_open = creative_code_spec_pipeline.os.open
    real_close = creative_code_spec_pipeline.os.close
    opened: list[int] = []
    fail_next_close = True

    def capture_open(*args: object, **kwargs: object) -> int:
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def fail_first_close(descriptor: int) -> None:
        nonlocal fail_next_close
        if fail_next_close:
            fail_next_close = False
            raise OSError("simulated descriptor transfer failure")
        real_close(descriptor)

    with monkeypatch.context() as context:
        context.setattr(creative_code_spec_pipeline.os, "open", capture_open)
        context.setattr(creative_code_spec_pipeline.os, "close", fail_first_close)
        with pytest.raises(CreativeCodeSpecPipelineError, match="transfer pinned"):
            creative_code_spec_pipeline._open_pinned_parent(
                target,
                allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
                create=True,
                label="artifact file",
            )

    assert opened
    with pytest.raises(OSError):
        os.fstat(opened[-1])


def test_pipeline_duplicate_keys_in_artifacts_fail_closed() -> None:
    run_dir = creative_code_spec_pipeline.ARTIFACT_ROOT / f"pytest-{uuid.uuid4().hex}"
    try:
        creative_code_spec_pipeline.prepare(REFERENCE_PACKET, run_dir)
        (run_dir / "variants.json").write_text(
            '[{"variant_id":"one","variant_id":"two"}]',
            encoding="utf-8",
        )

        with pytest.raises(CreativeCodeSpecPipelineError, match="duplicate JSON key"):
            creative_code_spec_pipeline.finalize(run_dir, run_dir / "bundle.json")
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_pipeline_json_reader_translates_parser_limits_to_domain_error() -> None:
    run_dir = creative_code_spec_pipeline.ARTIFACT_ROOT / f"pytest-{uuid.uuid4().hex}"
    path = run_dir / "oversized.json"
    try:
        run_dir.mkdir(parents=True)
        path.write_text('{"value":' + ("9" * 5000) + "}", encoding="utf-8")
        with pytest.raises(CreativeCodeSpecPipelineError, match="Unable to read safe test JSON"):
            creative_code_spec_pipeline._read_json_file(
                path,
                allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
                label="test",
            )
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_pipeline_json_reader_translates_recursion_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = creative_code_spec_pipeline.ARTIFACT_ROOT / f"pytest-{uuid.uuid4().hex}"
    path = run_dir / "recursive.json"
    try:
        run_dir.mkdir(parents=True)
        path.write_text("{}", encoding="utf-8")

        def raise_recursion(*_args: object, **_kwargs: object) -> object:
            raise RecursionError("simulated parser depth limit")

        monkeypatch.setattr(creative_code_spec_pipeline.json, "loads", raise_recursion)
        with pytest.raises(CreativeCodeSpecPipelineError, match="Unable to read safe test JSON"):
            creative_code_spec_pipeline._read_json_file(
                path,
                allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
                label="test",
            )
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_pr1_modules_do_not_import_network_provider_or_runtime_modules() -> None:
    forbidden_roots = {"app", "requests", "httpx", "urllib", "slack_sdk", "github", "openai"}
    for module_path in (
        SPEC_MODULE,
        PIPELINE_MODULE,
        REJECTION_MODULE,
        REVIEW_FINALIZE_MODULE,
        REVIEW_FINALIZE_CONTRACT_MODULE,
    ):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert not (forbidden_roots & imported_roots), module_path
