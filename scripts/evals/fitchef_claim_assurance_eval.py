#!/usr/bin/env python3
"""Offline, bounded comparison of FitChef answer claims with an accepted reference.

The reference and candidate are human/model supplied annotations. This program
checks their bindings and counts agreement; it never infers semantic support.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
import copy
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any, cast

from app.services.fitchef_claim_evidence_assurance import (
    FitChefSourceOccurrenceV1,
    build_fitchef_source_items,
    freeze_fitchef_source_snapshot,
)
from core.evidence.relations import audit_snapshot, parse_snapshot
from core.judgment import CLAIM_TYPES, EVIDENCE_MODES, SUPPORT_STATUSES
from core.insight.fitchef_companion import _extract_json_payload, _normalize_structured_string
from scripts.evals.evidence_relation_audit import _parent_fd, _read_input, read_jsonl, write_report

LEGACY_CASE_SCHEMA = "fitchef_claim_case.v1"
CASE_SCHEMA = "fitchef_claim_case.v2"
PACKET_SCHEMA = "fitchef_claim_candidate_packet.v2"
ANNOTATION_SCHEMA = "fitchef_claim_annotation.v1"
ACCEPTANCE_SCHEMA = "fitchef_claim_reference_acceptance.v1"
REPORT_SCHEMA = "fitchef_claim_evaluation.v1"
FAMILIES = (
    "cautious_explanation",
    "causal_overclaim",
    "contradicting_source",
    "irrelevant_citation",
    "context_time_mismatch",
    "absent_evidence",
)
LANGUAGES = ("ru", "en", "es")
SPLITS = ("development", "holdout")
PROVENANCES = ("manual_control", "saved_replay", "mock_integration", "provider_run")
FIELD_ORIGINS = ("provider", "fallback", "unknown")
POSITIVE = frozenset(("supported", "partially_supported"))
NEGATIVE = frozenset(("unsupported", "contradicted"))
_CASE_KEYS = frozenset(
    (
        "schema_version",
        "case_id",
        "canonical_id",
        "split",
        "family",
        "language",
        "input_provenance",
        "field_origin",
        "answer",
        "context",
        "sources",
        "raw_response",
        "result",
        "run",
        "material_fingerprint",
    )
)
_CASE_V2_KEYS = _CASE_KEYS | {"source_snapshot_fingerprint"}
_OPAQUE_ID_DOMAIN = b"fitchef_claim_candidate_packet.v2\0"
_PACKET_KEYS = frozenset(
    (
        "schema_version",
        "opaque_id",
        "material_fingerprint",
        "answer",
        "context",
        "sources",
        "rubric_sha256",
        "requested_language",
    )
)
_CLAIM_KEYS = frozenset(
    (
        "start",
        "end",
        "quote",
        "claim_type",
        "support_status",
        "evidence_mode",
        "source_refs",
        "rationale",
    )
)
_SOURCE_REF_KEYS = frozenset(("source_ref", "start", "end", "quote"))
_ANNOTATION_KEYS = frozenset(
    (
        "schema_version",
        "opaque_id",
        "material_fingerprint",
        "abstain",
        "claims",
        "answer_quality",
    )
)
_QUALITY_KEYS = frozenset(
    (
        "observed_language",
        "language_fit",
        "usefulness",
        "confidence_proportionality",
        "wellness_wording",
        "rationale",
        "quote",
    )
)
_OBSERVED_LANGUAGES = (*LANGUAGES, "mixed", "other", "unknown")
_QUALITY_STATUSES = ("appropriate", "mixed", "inappropriate", "unknown")
_QUALITY_DIMENSIONS = ("usefulness", "confidence_proportionality", "wellness_wording")
_MAX_CASES = 256
_MAX_CLAIMS = 128
_MAX_SOURCES = 5


def _object(value: object, keys: frozenset[str], name: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ValueError(f"{name}_shape")
    return cast(dict[str, Any], value)


def _string(value: object, name: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise ValueError(f"{name}_type")
    return value


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def _jsonl(rows: Sequence[object]) -> bytes:
    return b"".join(_canonical(row) + b"\n" for row in rows)


def _rubric_hash(path: Path) -> str:
    # The owning Markdown contract is the exact versioned rubric byte sequence.
    data = _read_input(path)
    if not data or b"# FitChef Claim Evidence Eval v1" not in data[:100]:
        raise ValueError("rubric_shape")
    return _sha(data)


def _validate_context(value: object) -> dict[str, Any]:
    context = _object(
        value,
        frozenset(("situation", "automatic_thought", "emotion", "goal")),
        "context",
    )
    for key in ("situation", "automatic_thought", "emotion"):
        if not _string(context[key], key).strip():
            raise ValueError("context_whitespace")
    if context["goal"] is not None:
        if not _string(context["goal"], "goal").strip():
            raise ValueError("context_whitespace")
    return context


def _validate_sources(value: object) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) > _MAX_SOURCES:
        raise ValueError("sources_shape")
    result: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(value):
        source = _object(
            raw,
            frozenset(("ordinal", "chunk_id", "file", "content", "preview", "score")),
            "source",
        )
        if type(source["ordinal"]) is not int or source["ordinal"] != ordinal:
            raise ValueError("source_ordinal")
        for key in ("chunk_id", "file", "content", "preview"):
            _string(source[key], key, allow_empty=key == "preview")
        score = source["score"]
        if type(score) not in (int, float) or not 0 <= score <= 1 or not math.isfinite(score):
            raise ValueError("source_score")
        result.append(source)
    return result


def _validate_run(value: object, provenance: str) -> dict[str, Any]:
    run = _object(
        value,
        frozenset(
            (
                "id",
                "code_sha",
                "code_hashes",
                "model",
                "parameters",
                "attempts",
                "reserved_usd",
                "cost_usd",
                "cost_status",
                "usage",
            )
        ),
        "run",
    )
    for key in ("id", "code_sha", "model"):
        _string(run[key], key)
    if provenance == "provider_run" and (
        run["model"] != "sonar"
        or type(run["code_sha"]) is not str
        or len(run["code_sha"]) != 40
        or any(char not in "0123456789abcdef" for char in run["code_sha"])
    ):
        raise ValueError("provider_identity")
    hashes = run["code_hashes"]
    if type(hashes) is not dict or any(
        type(name) is not str
        or type(digest) is not str
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
        for name, digest in hashes.items()
    ):
        raise ValueError("code_hashes")
    if provenance == "provider_run" and set(hashes) != {
        "collector",
        "evaluator",
        "fitchef_runtime",
        "fitchef_companion",
        "perplexity_adapter",
    }:
        raise ValueError("provider_code_hashes")
    if type(run["parameters"]) is not dict:
        raise ValueError("parameters_shape")
    if provenance == "provider_run" and _canonical(run["parameters"]) != _canonical(
        {
            "max_tokens": 1024,
            "web_search_options": {"disable_search": True},
        }
    ):
        raise ValueError("provider_parameters")
    if type(run["attempts"]) is not int or not 0 <= run["attempts"] <= 32:
        raise ValueError("attempts_range")
    if provenance == "provider_run" and run["attempts"] == 0:
        raise ValueError("provider_attempts_required")
    reserved = run["reserved_usd"]
    if type(reserved) not in (int, float) or not 0 <= reserved <= 4.8:
        raise ValueError("reserve_range")
    if run["cost_status"] not in ("known", "unknown", "not_applicable"):
        raise ValueError("cost_status")
    usage = run["usage"]
    if usage is not None:
        if (
            type(usage) is not dict
            or not set(usage) <= {"prompt_tokens", "completion_tokens", "total_tokens"}
            or any(type(count) is not int or count < 0 for count in usage.values())
        ):
            raise ValueError("usage_shape")
    cost = run["cost_usd"]
    if (
        (cost is not None and (type(cost) not in (int, float) or not 0 <= cost <= 5))
        or (run["cost_status"] == "known" and cost is None)
        or (run["cost_status"] != "known" and cost is not None)
    ):
        raise ValueError("cost_value")
    if provenance == "provider_run" and (
        run["cost_status"] == "not_applicable"
        or (
            run["cost_status"] == "known"
            and (run["attempts"] != 1 or not math.isfinite(cost) or cost > 0.15)
        )
    ):
        raise ValueError("provider_cost_status")
    if provenance == "provider_run" and reserved != round(run["attempts"] * 0.15, 2):
        raise ValueError("reserve_mismatch")
    if provenance != "provider_run" and (
        run["attempts"] != 0
        or reserved != 0
        or cost is not None
        or usage is not None
        or run["cost_status"] != "not_applicable"
    ):
        raise ValueError("nonprovider_accounting")
    return run


def case_fingerprint(case: dict[str, Any], rubric_sha256: str) -> str:
    """Bind all material case fields, including raw and public result, to rubric."""
    material = {key: value for key, value in case.items() if key != "material_fingerprint"}
    return _sha(_canonical({"case": material, "rubric_sha256": rubric_sha256}))


def validate_cases(rows: list[object], rubric_sha256: str) -> list[dict[str, Any]]:
    if not rows or len(rows) > _MAX_CASES:
        raise ValueError("case_limit")
    cases: list[dict[str, Any]] = []
    ids: set[str] = set()
    canonical_ids: set[str] = set()
    for row in rows:
        if type(row) is not dict or row.get("schema_version") not in (
            LEGACY_CASE_SCHEMA,
            CASE_SCHEMA,
        ):
            raise ValueError("case_version")
        case = _object(
            row, _CASE_V2_KEYS if row["schema_version"] == CASE_SCHEMA else _CASE_KEYS, "case"
        )
        case_id = _string(case["case_id"], "case_id")
        _string(case["canonical_id"], "canonical_id")
        if case_id in ids or case["canonical_id"] in canonical_ids:
            raise ValueError("duplicate_case")
        ids.add(case_id)
        canonical_ids.add(case["canonical_id"])
        for key, choices in (
            ("split", SPLITS),
            ("family", FAMILIES),
            ("language", LANGUAGES),
            ("input_provenance", PROVENANCES),
            ("field_origin", FIELD_ORIGINS),
        ):
            if type(case[key]) is not str or case[key] not in choices:
                raise ValueError(f"{key}_value")
        _string(case["answer"], "answer")
        _string(case["raw_response"], "raw_response", allow_empty=True)
        _validate_context(case["context"])
        sources = _validate_sources(case["sources"])
        snapshot = freeze_fitchef_source_snapshot(
            tuple(FitChefSourceOccurrenceV1(**source) for source in sources)
        )
        if case["schema_version"] == CASE_SCHEMA and (
            snapshot.source_snapshot_fingerprint is None
            or case["source_snapshot_fingerprint"] != snapshot.source_snapshot_fingerprint
        ):
            raise ValueError("captured_source_fingerprint_mismatch")
        _validate_run(case["run"], case["input_provenance"])
        if type(case["result"]) is not dict:
            raise ValueError("result_shape")
        if case["result"].get("balanced_reframe") != case["answer"]:
            raise ValueError("final_answer_mismatch")
        if case["input_provenance"] == "provider_run":
            expected_sources = [
                item.model_dump(mode="json") for item in build_fitchef_source_items(snapshot)
            ]
            if case["result"].get("sources") != expected_sources:
                raise ValueError("result_source_projection_mismatch")
            if case["field_origin"] == "provider":
                try:
                    payload = _extract_json_payload(case["raw_response"])
                    provider_answer = _normalize_structured_string(payload.get("balanced_reframe"))
                except ValueError as exc:
                    raise ValueError("provider_field_origin_mismatch") from exc
                if provider_answer != case["answer"]:
                    raise ValueError("provider_field_origin_mismatch")
        if case["material_fingerprint"] != case_fingerprint(case, rubric_sha256):
            raise ValueError("stale_case_fingerprint")
        cases.append(copy.deepcopy(case))
    if (
        sum(case["run"]["attempts"] for case in cases if case["input_provenance"] == "provider_run")
        > 32
    ):
        raise ValueError("aggregate_attempt_limit")
    if sum(case["run"]["reserved_usd"] for case in cases) > 4.8 + 1e-9:
        raise ValueError("aggregate_reserve_limit")
    provider_identities = {
        _canonical(
            {
                key: case["run"][key]
                for key in ("id", "code_sha", "code_hashes", "model", "parameters")
            }
        )
        for case in cases
        if case["input_provenance"] == "provider_run"
    }
    if len(provider_identities) > 1:
        raise ValueError("mixed_provider_run_identity")
    return cases


def _opaque_id(case: dict[str, Any], blind_key: bytes) -> str:
    if type(blind_key) is not bytes or len(blind_key) != 32:
        raise ValueError("blind_key_length")
    return hmac.new(
        blind_key,
        _OPAQUE_ID_DOMAIN + _canonical((case["case_id"], case["material_fingerprint"])),
        hashlib.sha256,
    ).hexdigest()


def prepare_packet(
    cases: list[dict[str, Any]], rubric_sha256: str, blind_key: bytes
) -> list[dict[str, Any]]:
    return [
        {
            "schema_version": PACKET_SCHEMA,
            "opaque_id": _opaque_id(case, blind_key),
            "material_fingerprint": case["material_fingerprint"],
            "answer": case["answer"],
            "context": case["context"],
            "sources": [
                {"source_ref": f"source-{source['ordinal']}", "content": source["content"]}
                for source in case["sources"]
            ],
            "rubric_sha256": rubric_sha256,
            "requested_language": case["language"],
        }
        for case in cases
    ]


def validate_packet(
    rows: list[object], cases: list[dict[str, Any]], rubric_sha256: str, blind_key: bytes
) -> None:
    expected = prepare_packet(cases, rubric_sha256, blind_key)
    if len(rows) != len(expected):
        raise ValueError("packet_count")
    for row, wanted in zip(rows, expected):
        _object(row, _PACKET_KEYS, "packet")
        if row != wanted:
            raise ValueError("packet_binding")


def _validate_claim(
    raw: object, answer: str, sources: list[dict[str, Any]], *, reference: bool
) -> dict[str, Any]:
    claim = _object(raw, _CLAIM_KEYS, "claim")
    start, end = claim["start"], claim["end"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(answer):
        raise ValueError("claim_span")
    if type(claim["quote"]) is not str or claim["quote"] != answer[start:end]:
        raise ValueError("claim_quote")
    for key, choices in (
        ("claim_type", CLAIM_TYPES),
        ("support_status", SUPPORT_STATUSES if reference else (*SUPPORT_STATUSES, "abstain")),
        ("evidence_mode", EVIDENCE_MODES),
    ):
        if type(claim[key]) is not str or claim[key] not in choices:
            raise ValueError(f"claim_{key}")
    _string(claim["rationale"], "rationale")
    refs = claim["source_refs"]
    if type(refs) is not list or len(refs) > 512:
        raise ValueError("source_refs")
    seen: set[tuple[int, int, int]] = set()
    for ref_raw in refs:
        ref = _object(ref_raw, _SOURCE_REF_KEYS, "source_ref")
        source_ref, source_start, source_end = ref["source_ref"], ref["start"], ref["end"]
        if type(source_ref) is not str or source_ref not in {
            f"source-{index}" for index in range(len(sources))
        }:
            raise ValueError("unknown_source_ref")
        ordinal = int(source_ref.removeprefix("source-"))
        content = sources[ordinal]["content"]
        if (
            type(source_start) is not int
            or type(source_end) is not int
            or not 0 <= source_start < source_end <= len(content)
        ):
            raise ValueError("source_span")
        if type(ref["quote"]) is not str or ref["quote"] != content[source_start:source_end]:
            raise ValueError("source_quote")
        identity = (ordinal, source_start, source_end)
        if identity in seen:
            raise ValueError("duplicate_source_ref")
        seen.add(identity)
    return claim


def _validate_answer_quality(value: object, *, answer: str, requested_language: str) -> None:
    quality = _object(value, _QUALITY_KEYS, "answer_quality")
    observed = quality["observed_language"]
    fit = quality["language_fit"]
    if type(observed) is not str or observed not in _OBSERVED_LANGUAGES:
        raise ValueError("observed_language")
    if type(fit) is not str or fit not in ("match", "mismatch", "unknown"):
        raise ValueError("language_fit")
    if observed == "unknown" and fit != "unknown":
        raise ValueError("language_fit_binding")
    if observed in LANGUAGES and fit != ("match" if observed == requested_language else "mismatch"):
        raise ValueError("language_fit_binding")
    if observed in ("mixed", "other") and fit == "match":
        raise ValueError("language_fit_binding")
    for dimension in _QUALITY_DIMENSIONS:
        if type(quality[dimension]) is not str or quality[dimension] not in _QUALITY_STATUSES:
            raise ValueError("quality_status")
    _string(quality["rationale"], "quality_rationale")
    quote = _string(quality["quote"], "quality_quote")
    if quote not in answer:
        raise ValueError("quality_quote_binding")


def validate_annotations(
    rows: list[object],
    cases: list[dict[str, Any]],
    *,
    reference: bool,
    blind_key: bytes,
) -> dict[str, dict[str, Any]]:
    by_id = {_opaque_id(case, blind_key): case for case in cases}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        annotation = _object(row, _ANNOTATION_KEYS, "annotation")
        if annotation["schema_version"] != ANNOTATION_SCHEMA:
            raise ValueError("annotation_version")
        opaque = _string(annotation["opaque_id"], "opaque_id")
        if opaque not in by_id or opaque in result:
            raise ValueError("unknown_or_duplicate_annotation")
        case = by_id[opaque]
        if annotation["material_fingerprint"] != case["material_fingerprint"]:
            raise ValueError("stale_annotation")
        if type(annotation["abstain"]) is not bool or type(annotation["claims"]) is not list:
            raise ValueError("annotation_shape")
        if len(annotation["claims"]) > _MAX_CLAIMS:
            raise ValueError("claim_limit")
        if annotation["abstain"] and annotation["claims"]:
            raise ValueError("abstain_with_claims")
        if reference and annotation["abstain"]:
            raise ValueError("reference_abstain")
        if annotation["abstain"]:
            if annotation["answer_quality"] is not None:
                raise ValueError("abstain_with_quality")
        else:
            _validate_answer_quality(
                annotation["answer_quality"],
                answer=case["answer"],
                requested_language=case["language"],
            )
        spans: set[tuple[int, int, str]] = set()
        for raw_claim in annotation["claims"]:
            claim = _validate_claim(raw_claim, case["answer"], case["sources"], reference=reference)
            identity = (claim["start"], claim["end"], claim["quote"])
            if identity in spans:
                raise ValueError("duplicate_claim")
            spans.add(identity)
        result[opaque] = copy.deepcopy(annotation)
    if reference and set(result) != set(by_id):
        raise ValueError("reference_missing_case")
    return result


def validate_acceptance(path: Path, reference_sha256: str) -> None:
    rows = read_private_jsonl(path)
    if len(rows) != 1:
        raise ValueError("acceptance_shape")
    receipt = _object(
        rows[0],
        frozenset(("schema_version", "reference_sha256", "accepted_by", "accepted_at")),
        "acceptance",
    )
    if receipt["schema_version"] != ACCEPTANCE_SCHEMA or receipt["accepted_by"] != "OWNER":
        raise ValueError("acceptance_authority")
    _string(receipt["accepted_at"], "accepted_at")
    if receipt["reference_sha256"] != reference_sha256:
        raise ValueError("reference_not_accepted")


def _input_identity(path: Path) -> tuple[int, int]:
    parent, name = _parent_fd(path)
    try:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("unsafe_annotation_input")
        return info.st_dev, info.st_ino
    except OSError as exc:
        raise ValueError("unsafe_annotation_input") from exc
    finally:
        os.close(parent)


def _private_input_identity(path: Path) -> tuple[int, ...]:
    """Require current owner plus a private file or private containing directory."""
    parent, name = _parent_fd(path)
    try:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        parent_info = os.fstat(parent)
        private_parent = parent_info.st_uid == os.getuid() and not parent_info.st_mode & 0o077
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.getuid()
            or (info.st_mode & 0o077 and not private_parent)
        ):
            raise ValueError("unsafe_private_input")
        return (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_uid,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
            info.st_nlink,
            parent_info.st_dev,
            parent_info.st_ino,
            parent_info.st_mode,
            parent_info.st_uid,
            parent_info.st_mtime_ns,
            parent_info.st_ctime_ns,
        )
    except OSError as exc:
        raise ValueError("unsafe_private_input") from exc
    finally:
        os.close(parent)


def read_private_jsonl(path: Path) -> list[object]:
    before = _private_input_identity(path)
    rows: list[object] = read_jsonl(path)
    if before != _private_input_identity(path):
        raise ValueError("private_input_changed")
    return rows


def _read_private_input(path: Path) -> bytes:
    before = _private_input_identity(path)
    data: bytes = _read_input(path)
    if before != _private_input_identity(path):
        raise ValueError("private_input_changed")
    return data


def load_blind_key(path: Path) -> bytes:
    key = _read_private_input(path)
    if len(key) != 32:
        raise ValueError("blind_key_length")
    return key


def _ratio(numerator: int, denominator: int) -> dict[str, int | float | str]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else "not_measured",
    }


def _metrics(
    cases: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    references: dict[str, dict[str, Any]],
    blind_key: bytes,
) -> dict[str, Any]:
    matrix = {ref: {candidate: 0 for candidate in SUPPORT_STATUSES} for ref in SUPPORT_STATUSES}
    reference_claims = matched = unmatched_candidate = abstained_cases = missing_cases = 0
    abstained_claims = reference_omissions = 0
    language_counts: Counter[str] = Counter()
    observed_counts: Counter[str] = Counter()
    quality_counts: dict[str, Counter[str]] = {
        dimension: Counter() for dimension in _QUALITY_DIMENSIONS
    }
    quality_agreement: dict[str, list[int]] = {
        dimension: [0, 0] for dimension in _QUALITY_DIMENSIONS
    }
    language_agreement = [0, 0]
    language_mismatch_cases: list[str] = []
    false_accept = false_reject = severe_false_accept = negative_matched = positive_matched = 0
    for case in cases:
        opaque = _opaque_id(case, blind_key)
        ref_claims = references[opaque]["claims"]
        ref_quality = references[opaque]["answer_quality"]
        language_counts[ref_quality["language_fit"]] += 1
        observed_counts[ref_quality["observed_language"]] += 1
        if ref_quality["language_fit"] == "mismatch":
            language_mismatch_cases.append(case["case_id"])
        for dimension in _QUALITY_DIMENSIONS:
            quality_counts[dimension][ref_quality[dimension]] += 1
        reference_claims += len(ref_claims)
        candidate_row = candidates.get(opaque)
        if candidate_row is None:
            missing_cases += 1
            reference_omissions += len(ref_claims)
            continue
        if candidate_row["abstain"]:
            abstained_cases += 1
            abstained_claims += len(ref_claims)
            continue
        candidate_quality = candidate_row["answer_quality"]
        if (
            ref_quality["language_fit"] != "unknown"
            and candidate_quality["language_fit"] != "unknown"
        ):
            language_agreement[1] += 1
            language_agreement[0] += int(
                ref_quality["language_fit"] == candidate_quality["language_fit"]
            )
        for dimension in _QUALITY_DIMENSIONS:
            if ref_quality[dimension] != "unknown" and candidate_quality[dimension] != "unknown":
                quality_agreement[dimension][1] += 1
                quality_agreement[dimension][0] += int(
                    ref_quality[dimension] == candidate_quality[dimension]
                )
        candidate_claims = {
            (item["start"], item["end"], item["quote"]): item for item in candidate_row["claims"]
        }
        ref_ids = {(item["start"], item["end"], item["quote"]) for item in ref_claims}
        unmatched_candidate += len(candidate_claims.keys() - ref_ids)
        abstained_claims += sum(
            item["support_status"] == "abstain" for item in candidate_claims.values()
        )
        for ref in ref_claims:
            key = (ref["start"], ref["end"], ref["quote"])
            cand = candidate_claims.get(key)
            if cand is None:
                reference_omissions += 1
                continue
            if cand["support_status"] == "abstain":
                continue
            matched += 1
            ref_status, cand_status = ref["support_status"], cand["support_status"]
            matrix[ref_status][cand_status] += 1
            if ref_status in NEGATIVE:
                negative_matched += 1
                if cand_status in POSITIVE:
                    false_accept += 1
                if cand_status == "supported":
                    severe_false_accept += 1
            else:
                positive_matched += 1
                if cand_status in NEGATIVE:
                    false_reject += 1
    return {
        "confusion_4x4": matrix,
        "reference_claims": reference_claims,
        "matched_claims": matched,
        "reference_omissions": reference_omissions,
        "abstained_claims": abstained_claims,
        "unmatched_candidate_claims": unmatched_candidate,
        "abstained_cases": abstained_cases,
        "missing_candidate_cases": missing_cases,
        "answer_quality": {
            "reference_language_fit": {
                label: language_counts[label] for label in ("match", "mismatch", "unknown")
            },
            "reference_observed_language": {
                label: observed_counts[label] for label in _OBSERVED_LANGUAGES
            },
            "reference_dimensions": {
                dimension: {label: quality_counts[dimension][label] for label in _QUALITY_STATUSES}
                for dimension in _QUALITY_DIMENSIONS
            },
            "language_fit_agreement": _ratio(*language_agreement),
            "dimension_agreement": {
                dimension: _ratio(*quality_agreement[dimension])
                for dimension in _QUALITY_DIMENSIONS
            },
            "language_mismatch_case_ids": language_mismatch_cases,
        },
        "coverage": _ratio(matched, reference_claims),
        "false_acceptance": _ratio(false_accept, negative_matched),
        "severe_false_acceptance": _ratio(severe_false_accept, negative_matched),
        "false_rejection": _ratio(false_reject, positive_matched),
    }


def build_report(
    cases: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    references: dict[str, dict[str, Any]],
    *,
    blind_key: bytes,
    structural: object | None = None,
    rubric_sha256: str | None = None,
    accepted_reference_sha256: str | None = None,
    acceptance_sha256: str | None = None,
    structural_input_sha256: str | None = None,
) -> dict[str, Any]:
    slices: dict[str, dict[str, Any]] = {}
    for field in ("split", "family", "language", "input_provenance", "field_origin"):
        slices[field] = {
            label: _metrics(
                [case for case in cases if case[field] == label], candidates, references, blind_key
            )
            for label in sorted({case[field] for case in cases})
        }
    known_costs = [
        case["run"]["cost_usd"] for case in cases if case["run"]["cost_status"] == "known"
    ]
    unknown_cost_cases = sum(case["run"]["cost_status"] == "unknown" for case in cases)
    report = {
        "schema_version": REPORT_SCHEMA,
        "cases": len(cases),
        "metrics": _metrics(cases, candidates, references, blind_key),
        "capture_integrity": {
            "historical_fingerprint_not_recorded_cases": sum(
                case["schema_version"] == LEGACY_CASE_SCHEMA for case in cases
            ),
            "recorded_fingerprint_consistent_cases": sum(
                case["schema_version"] == CASE_SCHEMA for case in cases
            ),
            "authenticated_capture": False,
        },
        "slices": slices,
        "spend": {
            "reserved_usd": round(sum(case["run"]["reserved_usd"] for case in cases), 2),
            "known_usd": round(sum(known_costs), 6),
            "unknown_cost_cases": unknown_cost_cases,
        },
        "structural_advisory": structural,
        "input_fingerprints": {
            "cases_sha256": _sha(_canonical(cases)),
            "candidate_sha256": _sha(_canonical(candidates)),
            "reference_sha256": _sha(_canonical(references)),
            "rubric_sha256": rubric_sha256,
            "accepted_reference_sha256": accepted_reference_sha256,
            "acceptance_sha256": acceptance_sha256,
            "structural_input_sha256": structural_input_sha256,
        },
        "authority": {"answer_changed": False, "promotion": False, "causal_truth": False},
    }
    report["report_fingerprint"] = _sha(_canonical(report))
    return report


def _load(args: argparse.Namespace) -> tuple[list[dict[str, Any]], str]:
    rubric_sha256 = _rubric_hash(args.rubric)
    cases = validate_cases(read_private_jsonl(args.cases), rubric_sha256)
    return cases, rubric_sha256


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--cases", type=Path, required=True)
    prepare.add_argument("--rubric", type=Path, required=True)
    prepare.add_argument("--blind-key", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    for command in ("validate", "report"):
        sub = commands.add_parser(command)
        sub.add_argument("--cases", type=Path, required=True)
        sub.add_argument("--rubric", type=Path, required=True)
        sub.add_argument("--blind-key", type=Path, required=True)
        sub.add_argument("--packet", type=Path, required=True)
        sub.add_argument("--candidate", type=Path, required=True)
        sub.add_argument("--reference", type=Path, required=True)
        sub.add_argument("--reference-acceptance", type=Path, required=True)
        if command == "report":
            sub.add_argument("--output", type=Path, required=True)
            sub.add_argument("--relation-snapshot", type=Path)
    args = parser.parse_args(argv)
    try:
        blind_key = load_blind_key(args.blind_key)
        cases, rubric_sha256 = _load(args)
        if args.command == "prepare":
            write_report(args.output, _jsonl(prepare_packet(cases, rubric_sha256, blind_key)))
            return 0
        validate_packet(read_private_jsonl(args.packet), cases, rubric_sha256, blind_key)
        if _input_identity(args.reference) == _input_identity(args.candidate):
            raise ValueError("candidate_is_reference")
        reference_bytes = _read_private_input(args.reference)
        reference = validate_annotations(
            read_private_jsonl(args.reference), cases, reference=True, blind_key=blind_key
        )
        if _read_private_input(args.reference) != reference_bytes:
            raise ValueError("reference_changed_during_read")
        acceptance_bytes = _read_private_input(args.reference_acceptance)
        validate_acceptance(args.reference_acceptance, _sha(reference_bytes))
        if _read_private_input(args.reference_acceptance) != acceptance_bytes:
            raise ValueError("acceptance_changed_during_read")
        candidate_bytes = _read_private_input(args.candidate)
        candidate = validate_annotations(
            read_private_jsonl(args.candidate), cases, reference=False, blind_key=blind_key
        )
        if _read_private_input(args.candidate) != candidate_bytes:
            raise ValueError("candidate_changed_during_read")
        if args.command == "report":
            structural = None
            structural_input_sha256 = None
            if args.relation_snapshot is not None:
                structural_bytes = _read_input(args.relation_snapshot)
                structural = audit_snapshot(
                    parse_snapshot(read_jsonl(args.relation_snapshot))
                ).to_dict()
                if _read_input(args.relation_snapshot) != structural_bytes:
                    raise ValueError("structural_changed_during_read")
                structural_input_sha256 = _sha(structural_bytes)
            write_report(
                args.output,
                _canonical(
                    build_report(
                        cases,
                        candidate,
                        reference,
                        blind_key=blind_key,
                        structural=structural,
                        rubric_sha256=rubric_sha256,
                        accepted_reference_sha256=_sha(reference_bytes),
                        acceptance_sha256=_sha(acceptance_bytes),
                        structural_input_sha256=structural_input_sha256,
                    )
                )
                + b"\n",
            )
    except (ValueError, OSError) as exc:
        print(f"fitchef_claim_assurance_eval: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
