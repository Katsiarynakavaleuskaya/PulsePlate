from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from typing import Any, cast

import pytest

from core.ai.exact_fuzzy_cache import (
    ExactFuzzyCacheLineage,
    ExactFuzzyCacheLookupResult,
    ExactFuzzyCacheRecord,
    ExactFuzzyCacheLookupRequest,
    ExactFuzzyMatchPolicy,
    build_exact_fuzzy_idempotency_key,
    build_exact_fuzzy_lineage,
    build_exact_fuzzy_record_id,
    create_exact_fuzzy_cache_record,
    match_exact_fuzzy_records,
    normalize_exact_fuzzy_query,
    to_stable_mapping,
)
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "core" / "ai" / "exact_fuzzy_cache.py"


def _lineage() -> ExactFuzzyCacheLineage:
    return build_exact_fuzzy_lineage(
        eval_event_ids=("eval-event:2", "eval-event:1"),
        admission_decision_id="admission-decision:1",
        promotion_ids=("promotion:2", "promotion:1"),
        replay_entry_ids=("replay:2", "replay:1"),
        source_fingerprints=("sha256:source-b", "sha256:source-a"),
        policy_version="semantic-cache-sc-g2-v1",
    )


def _record(raw_query: str = "Plan protein breakfast") -> ExactFuzzyCacheRecord:
    return create_exact_fuzzy_cache_record(
        surface="insight",
        raw_query=raw_query,
        context_fingerprint="sha256:context",
        provider_key="provider:test",
        model_key="model:test",
        user_tier="pro",
        transparency_notice_id="notice:insight:v1",
        lineage=_lineage(),
        response_fingerprint="sha256:response",
        safety_flags=("wellness_only",),
    )


def _request(raw_query: str = "Plan protein breakfast") -> ExactFuzzyCacheLookupRequest:
    return ExactFuzzyCacheLookupRequest(
        surface="insight",
        raw_query=raw_query,
        context_fingerprint="sha256:context",
        source_fingerprints=("sha256:source-a", "sha256:source-b"),
        policy_version="semantic-cache-sc-g2-v1",
        provider_key="provider:test",
        model_key="model:test",
        user_tier="pro",
        transparency_notice_id="notice:insight:v1",
    )


def _policy(
    *,
    token_jaccard_min_bps: int = 6000,
    sequence_ratio_min_bps: int = 8000,
    max_token_count_delta: int = 1,
) -> ExactFuzzyMatchPolicy:
    return ExactFuzzyMatchPolicy(
        policy_version="semantic-cache-sc-g2-v1",
        token_jaccard_min_bps=token_jaccard_min_bps,
        sequence_ratio_min_bps=sequence_ratio_min_bps,
        max_token_count_delta=max_token_count_delta,
    )


def test_normalization_is_stable_across_case_whitespace_and_punctuation() -> None:
    normalized, token_key = normalize_exact_fuzzy_query("  PLAN—Protein!!! Breakfast  ")

    assert normalized == "plan protein breakfast"
    assert token_key == ("breakfast", "plan", "protein")


def test_punctuation_only_query_fails_closed_after_normalization() -> None:
    with pytest.raises(ValueError, match="lexical content"):
        normalize_exact_fuzzy_query("!!!")
    with pytest.raises(ValueError, match="lexical content"):
        match_exact_fuzzy_records(
            request=_request("!!!"),
            candidate_records=(_record("Plan protein breakfast"),),
            policy=_policy(token_jaccard_min_bps=0, sequence_ratio_min_bps=0),
        )


def test_exact_hit() -> None:
    record = _record("Plan protein breakfast")

    result = match_exact_fuzzy_records(
        request=_request("plan protein breakfast"),
        candidate_records=(record,),
        policy=_policy(),
    )

    assert result.decision == "hit"
    assert result.matched_record_id == record.record_id
    assert result.match_mode == "exact"
    assert result.score_bps == 10000
    assert result.checked_record_count == 1


def test_reordered_token_fuzzy_hit() -> None:
    record = _record("Plan protein breakfast")

    result = match_exact_fuzzy_records(
        request=_request("Breakfast protein plan"),
        candidate_records=(record,),
        policy=_policy(),
    )

    assert result.decision == "hit"
    assert result.match_mode == "fuzzy_reordered_tokens"
    assert result.score_bps == 9900


def test_near_duplicate_fuzzy_hit() -> None:
    record = _record("reduce evening cravings with protein snack")

    result = match_exact_fuzzy_records(
        request=_request("reduce evening craving with protein snacks"),
        candidate_records=(record,),
        policy=_policy(token_jaccard_min_bps=5000, sequence_ratio_min_bps=8500),
    )

    assert result.decision == "hit"
    assert result.match_mode == "fuzzy_near_duplicate"
    assert result.score_bps is not None
    assert result.score_bps >= 5000


def test_match_precedence_prefers_exact_then_reordered_then_near_duplicate() -> None:
    exact_record = _record("Plan protein breakfast")
    reordered_record = _record("Breakfast protein plan")
    near_duplicate_record = _record("Plan protein breakfast today")
    policy = _policy(token_jaccard_min_bps=5000, sequence_ratio_min_bps=5000)

    exact_result = match_exact_fuzzy_records(
        request=_request("Plan protein breakfast"),
        candidate_records=(near_duplicate_record, reordered_record, exact_record),
        policy=policy,
    )
    reordered_result = match_exact_fuzzy_records(
        request=_request("Plan protein breakfast"),
        candidate_records=(near_duplicate_record, reordered_record),
        policy=policy,
    )
    near_duplicate_result = match_exact_fuzzy_records(
        request=_request("Plan protein breakfast"),
        candidate_records=(near_duplicate_record,),
        policy=policy,
    )

    assert exact_result.decision == "hit"
    assert exact_result.match_mode == "exact"
    assert exact_result.matched_record_id == exact_record.record_id
    assert exact_result.score_bps == 10000
    assert reordered_result.decision == "hit"
    assert reordered_result.match_mode == "fuzzy_reordered_tokens"
    assert reordered_result.matched_record_id == reordered_record.record_id
    assert reordered_result.score_bps == 9900
    assert near_duplicate_result.decision == "hit"
    assert near_duplicate_result.match_mode == "fuzzy_near_duplicate"
    assert near_duplicate_result.matched_record_id == near_duplicate_record.record_id
    assert near_duplicate_result.score_bps is not None
    assert near_duplicate_result.score_bps >= 5000


def test_fuzzy_miss_below_threshold() -> None:
    record = _record("reduce evening cravings with protein snack")

    result = match_exact_fuzzy_records(
        request=_request("plan a low sodium dinner tomorrow"),
        candidate_records=(record,),
        policy=_policy(token_jaccard_min_bps=8000, sequence_ratio_min_bps=9000),
    )

    assert result.decision == "miss"
    assert result.reason_codes == ("no_match",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_fingerprints", ("sha256:source-a", "sha256:other")),
        ("policy_version", "semantic-cache-sc-g2-v2"),
        ("provider_key", "provider:other"),
        ("model_key", "model:other"),
        ("user_tier", "free"),
        ("surface", "other-surface"),
        ("transparency_notice_id", "notice:other"),
        ("context_fingerprint", "sha256:other-context"),
    ],
)
def test_partition_mismatch_is_hard_miss(field: str, value: object) -> None:
    record = _record("Plan protein breakfast")
    base_request = _request("Plan protein breakfast")
    if field == "source_fingerprints":
        assert isinstance(value, tuple)
        assert all(isinstance(item, str) for item in value)
        request = replace(base_request, source_fingerprints=cast(tuple[str, ...], value))
    elif field == "policy_version":
        assert isinstance(value, str)
        request = replace(base_request, policy_version=value)
    elif field == "provider_key":
        assert isinstance(value, str)
        request = replace(base_request, provider_key=value)
    elif field == "model_key":
        assert isinstance(value, str)
        request = replace(base_request, model_key=value)
    elif field == "user_tier":
        assert isinstance(value, str)
        request = replace(base_request, user_tier=value)
    elif field == "surface":
        assert isinstance(value, str)
        request = replace(base_request, surface=value)
    elif field == "transparency_notice_id":
        assert isinstance(value, str)
        request = replace(base_request, transparency_notice_id=value)
    elif field == "context_fingerprint":
        assert isinstance(value, str)
        request = replace(base_request, context_fingerprint=value)
    else:
        raise AssertionError(f"unsupported field: {field}")
    policy = (
        _policy()
        if request.policy_version == "semantic-cache-sc-g2-v1"
        else ExactFuzzyMatchPolicy(
            policy_version=request.policy_version,
            token_jaccard_min_bps=6000,
            sequence_ratio_min_bps=8000,
            max_token_count_delta=1,
        )
    )

    result = match_exact_fuzzy_records(
        request=request,
        candidate_records=(record,),
        policy=policy,
    )

    assert result.decision == "miss"
    assert result.checked_record_count == 0
    assert result.reason_codes == ("no_partition_match",)


def test_policy_mismatch_between_request_and_match_policy_fails_closed() -> None:
    with pytest.raises(ValueError, match="request policy_version must match"):
        match_exact_fuzzy_records(
            request=_request("Plan protein breakfast"),
            candidate_records=(_record("Plan protein breakfast"),),
            policy=ExactFuzzyMatchPolicy(
                policy_version="semantic-cache-sc-g2-v2",
                token_jaccard_min_bps=6000,
                sequence_ratio_min_bps=8000,
                max_token_count_delta=1,
            ),
        )


def test_threshold_boundary_uses_integer_basis_points() -> None:
    record = _record("alpha beta gamma delta")
    request = _request("alpha beta gamma epsilon")

    at_threshold = match_exact_fuzzy_records(
        request=request,
        candidate_records=(record,),
        policy=_policy(token_jaccard_min_bps=6000, sequence_ratio_min_bps=0),
    )
    above_threshold = match_exact_fuzzy_records(
        request=request,
        candidate_records=(record,),
        policy=_policy(token_jaccard_min_bps=6001, sequence_ratio_min_bps=0),
    )
    below_threshold = match_exact_fuzzy_records(
        request=request,
        candidate_records=(record,),
        policy=_policy(token_jaccard_min_bps=5999, sequence_ratio_min_bps=0),
    )

    assert at_threshold.decision == "hit"
    assert at_threshold.score_bps == 6000
    assert above_threshold.decision == "miss"
    assert below_threshold.decision == "hit"


def test_deterministic_record_id_and_idempotency_key() -> None:
    first = _record("Plan protein breakfast")
    second = _record("PLAN!!! protein breakfast")

    assert first.record_id == second.record_id
    assert first.idempotency_key == second.idempotency_key
    assert first.record_id == build_exact_fuzzy_record_id(
        surface=first.surface,
        normalized_query=first.normalized_query,
        token_sort_key=first.token_sort_key,
        context_fingerprint=first.context_fingerprint,
        provider_key=first.provider_key,
        model_key=first.model_key,
        user_tier=first.user_tier,
        transparency_notice_id=first.transparency_notice_id,
        lineage=first.lineage,
        response_fingerprint=first.response_fingerprint,
        safety_flags=first.safety_flags,
        normalization_version=first.normalization_version,
    )
    assert first.idempotency_key == build_exact_fuzzy_idempotency_key(
        surface=first.surface,
        normalized_query=first.normalized_query,
        context_fingerprint=first.context_fingerprint,
        provider_key=first.provider_key,
        model_key=first.model_key,
        user_tier=first.user_tier,
        transparency_notice_id=first.transparency_notice_id,
        lineage=first.lineage,
        response_fingerprint=first.response_fingerprint,
        normalization_version=first.normalization_version,
    )


def test_deterministic_candidate_ordering_on_ties() -> None:
    record_b = _record("alpha beta y")
    record_a = _record("alpha beta x")

    result = match_exact_fuzzy_records(
        request=_request("alpha beta z"),
        candidate_records=(record_b, record_a),
        policy=_policy(token_jaccard_min_bps=5000, sequence_ratio_min_bps=0),
    )

    assert result.decision == "hit"
    assert result.matched_record_id == record_a.record_id


def test_duplicate_equivalent_candidates_do_not_compare_record_objects() -> None:
    record = _record("Plan protein breakfast")

    result = match_exact_fuzzy_records(
        request=_request("Plan protein breakfast"),
        candidate_records=(record, record),
        policy=_policy(),
    )

    assert result.decision == "hit"
    assert result.matched_record_id == record.record_id
    assert result.checked_record_count == 2


def test_lineage_inputs_are_defensively_normalized_and_frozen() -> None:
    lineage = _lineage()

    assert lineage.eval_event_ids == ("eval-event:1", "eval-event:2")
    assert lineage.source_fingerprints == ("sha256:source-a", "sha256:source-b")
    with pytest.raises(FrozenInstanceError):
        setattr(lineage, "policy_version", "changed")


def test_stable_serialization_contains_no_raw_prompt_or_response_payload() -> None:
    record = _record("Plan protein breakfast")
    payload = json.dumps(to_stable_mapping(record), sort_keys=True)

    assert "Plan protein breakfast" not in payload
    assert "raw_prompt" not in payload
    assert "raw_response" not in payload
    assert "secret" not in payload
    assert "healthkit" not in payload.lower()
    assert record.normalized_query == "plan protein breakfast"


def test_rejects_invalid_thresholds_and_blank_inputs() -> None:
    with pytest.raises(ValueError, match="between 0 and 10000"):
        _policy(token_jaccard_min_bps=10001)
    with pytest.raises(ValueError, match="must be an integer"):
        ExactFuzzyMatchPolicy(
            policy_version="semantic-cache-sc-g2-v1",
            token_jaccard_min_bps=cast(Any, 1.5),
            sequence_ratio_min_bps=8000,
            max_token_count_delta=1,
        )
    with pytest.raises(ValueError, match="max_token_count_delta"):
        _policy(max_token_count_delta=-1)
    with pytest.raises(ValueError, match="raw_query must be non-empty"):
        _request(" ")
    with pytest.raises(ValueError, match="source_fingerprints must be non-empty"):
        ExactFuzzyCacheLookupRequest(
            surface="insight",
            raw_query="Plan protein breakfast",
            context_fingerprint="sha256:context",
            source_fingerprints=(),
            policy_version="semantic-cache-sc-g2-v1",
            provider_key="provider:test",
            model_key="model:test",
            user_tier="pro",
            transparency_notice_id="notice:insight:v1",
        )
    with pytest.raises(ValueError, match="source_fingerprints must be non-empty"):
        build_exact_fuzzy_lineage(
            eval_event_ids=(),
            admission_decision_id=None,
            promotion_ids=(),
            replay_entry_ids=(),
            source_fingerprints=(),
            policy_version="semantic-cache-sc-g2-v1",
        )
    with pytest.raises(ValueError, match="contains duplicate"):
        build_exact_fuzzy_lineage(
            eval_event_ids=(),
            admission_decision_id=None,
            promotion_ids=(),
            replay_entry_ids=(),
            source_fingerprints=("sha256:source", "sha256:source"),
            policy_version="semantic-cache-sc-g2-v1",
        )
    with pytest.raises(ValueError, match="provider_key must not contain whitespace"):
        ExactFuzzyCacheLookupRequest(
            surface="insight",
            raw_query="Plan protein breakfast",
            context_fingerprint="sha256:context",
            source_fingerprints=("sha256:source",),
            policy_version="semantic-cache-sc-g2-v1",
            provider_key="provider test",
            model_key="model:test",
            user_tier="pro",
            transparency_notice_id="notice:insight:v1",
        )


def test_record_and_result_contracts_fail_closed_on_invalid_values() -> None:
    record = _record("Plan protein breakfast")
    with pytest.raises(ValueError, match="lineage must be ExactFuzzyCacheLineage"):
        ExactFuzzyCacheRecord(
            record_id=record.record_id,
            surface=record.surface,
            normalized_query=record.normalized_query,
            token_sort_key=record.token_sort_key,
            context_fingerprint=record.context_fingerprint,
            provider_key=record.provider_key,
            model_key=record.model_key,
            user_tier=record.user_tier,
            transparency_notice_id=record.transparency_notice_id,
            lineage=cast(Any, "not-lineage"),
            response_fingerprint=record.response_fingerprint,
            safety_flags=record.safety_flags,
            idempotency_key=record.idempotency_key,
            normalization_version=record.normalization_version,
        )
    with pytest.raises(ValueError, match="unsupported decision"):
        ExactFuzzyCacheLookupResult(
            decision="maybe",
            matched_record_id=None,
            match_mode=None,
            score_bps=None,
            checked_record_count=0,
            reason_codes=("no_match",),
        )
    with pytest.raises(ValueError, match="unsupported match_mode"):
        ExactFuzzyCacheLookupResult(
            decision="miss",
            matched_record_id=None,
            match_mode="semantic",
            score_bps=None,
            checked_record_count=0,
            reason_codes=("no_match",),
        )
    with pytest.raises(ValueError, match="checked_record_count"):
        ExactFuzzyCacheLookupResult(
            decision="miss",
            matched_record_id=None,
            match_mode=None,
            score_bps=None,
            checked_record_count=-1,
            reason_codes=("no_match",),
        )


def test_lineage_payload_and_record_id_reject_non_lineage() -> None:
    record = _record("Plan protein breakfast")

    with pytest.raises(ValueError, match="lineage must be ExactFuzzyCacheLineage"):
        build_exact_fuzzy_record_id(
            surface=record.surface,
            normalized_query=record.normalized_query,
            token_sort_key=record.token_sort_key,
            context_fingerprint=record.context_fingerprint,
            provider_key=record.provider_key,
            model_key=record.model_key,
            user_tier=record.user_tier,
            transparency_notice_id=record.transparency_notice_id,
            lineage=cast(ExactFuzzyCacheLineage, "not-lineage"),
            response_fingerprint=record.response_fingerprint,
            safety_flags=record.safety_flags,
            normalization_version=record.normalization_version,
        )


def test_unsupported_record_normalization_version_is_ignored() -> None:
    record = replace(_record("Plan protein breakfast"), normalization_version="legacy-v0")

    result = match_exact_fuzzy_records(
        request=_request("Plan protein breakfast"),
        candidate_records=(record,),
        policy=_policy(),
    )

    assert result.decision == "miss"
    assert result.checked_record_count == 1
    assert result.reason_codes == ("no_match",)


def test_near_duplicate_misses_on_token_delta_and_sequence_threshold() -> None:
    record = _record("alpha beta gamma")
    request = _request("alpha beta gamma delta")

    delta_miss = match_exact_fuzzy_records(
        request=request,
        candidate_records=(record,),
        policy=_policy(token_jaccard_min_bps=0, sequence_ratio_min_bps=0, max_token_count_delta=0),
    )
    ratio_miss = match_exact_fuzzy_records(
        request=request,
        candidate_records=(record,),
        policy=_policy(
            token_jaccard_min_bps=0,
            sequence_ratio_min_bps=9999,
            max_token_count_delta=3,
        ),
    )

    assert delta_miss.decision == "miss"
    assert ratio_miss.decision == "miss"


def test_scaffold_module_has_no_forbidden_imports_or_nondeterministic_calls() -> None:
    assert_no_forbidden_semantic_cache_imports(MODULE)
    assert_no_forbidden_semantic_cache_calls(MODULE)
