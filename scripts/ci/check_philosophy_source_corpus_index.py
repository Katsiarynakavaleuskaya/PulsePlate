#!/usr/bin/env python3
"""Deterministic guard for the Philosophy Epic V2 source-corpus index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INDEX = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "PHILOSOPHY_SOURCE_CORPUS_INDEX.json"
)
DEFAULT_SCHEMA = DEFAULT_INDEX.with_suffix(".schema.json")
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
DEFAULT_GATE_REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"
)

CONTRACT_ID = "philosophy_source_corpus_index"
CONTRACT_VERSION = "2026-05-24"
ROLLOUT_PHASE = "PHILOSOPHY-PR5"
GENERATED_AT = "static-2026-05-24"
EXPECTED_TOTAL_PAGES = 102

EXPECTED_INDEX_KEYS = (
    "contract_id",
    "contract_version",
    "generated_at",
    "rollout_phase",
    "gate_status",
    "runtime_allowed",
    "implementation_allowed",
    "requires_dedicated_gate",
    "semantic_cache_markers",
    "source_policy",
    "source_count",
    "total_pages",
    "sources",
    "research_basis",
    "repo_truth_links",
    "out_of_scope_paths",
)
EXPECTED_SEMANTIC_MARKER_KEYS = (
    "gate_status_closed",
    "runtime_allowed_false",
    "implementation_allowed_false",
    "dedicated_gate_required",
)
EXPECTED_SOURCE_POLICY_KEYS = (
    "authority",
    "local_path_policy",
    "text_policy",
    "promotion_policy",
    "credential_policy",
    "wellness_boundary",
)
EXPECTED_SOURCE_KEYS = (
    "source_id",
    "title",
    "sanitized_filename",
    "language",
    "page_count",
    "sha256",
    "source_family",
    "extraction_status",
    "summary",
    "theme_families",
    "discipline_rails",
    "linked_repo_anchors",
    "future_handoff",
    "runtime_flags",
)
EXPECTED_SOURCE_FAMILIES = (
    "socratic_cbt_semantic_cache",
    "leibniz_information_theory",
    "analytic_linguistic_audit",
    "full_philosophy_roadmap",
    "philosophy_cbt_correlation",
    "philosophy_cbt_plan_adaptation",
)
EXPECTED_RESEARCH_BASIS_KEYS = (
    "id",
    "label",
    "url",
    "rail",
    "source_kind",
    "accessed_on",
    "verification_status",
    "boundary_note",
    "use",
)
EXPECTED_RESEARCH_BASIS: dict[str, dict[str, str]] = {
    "sep_socrates": {
        "label": "Stanford Encyclopedia of Philosophy: Socrates",
        "url": "https://plato.stanford.edu/entries/socrates/",
        "rail": "socratic_questioning_and_interpretation",
        "source_kind": "external_research_reference",
        "accessed_on": "2026-05-24",
        "verification_status": "verified_stable_public_reference",
        "boundary_note": "philosophy_context_only_repo_truth_and_closed_gate_markers_remain_authoritative",
        "use": "rationale_only_not_runtime_truth",
    },
    "sep_leibniz": {
        "label": "Stanford Encyclopedia of Philosophy: Leibniz",
        "url": "https://plato.stanford.edu/entries/leibniz/",
        "rail": "leibnizian_state_and_possible_worlds",
        "source_kind": "external_research_reference",
        "accessed_on": "2026-05-24",
        "verification_status": "verified_stable_public_reference",
        "boundary_note": "philosophy_context_only_repo_truth_and_closed_gate_markers_remain_authoritative",
        "use": "rationale_only_not_runtime_truth",
    },
    "sep_wittgenstein": {
        "label": "Stanford Encyclopedia of Philosophy: Wittgenstein",
        "url": "https://plato.stanford.edu/entries/wittgenstein/",
        "rail": "language_games_and_meaning_as_use",
        "source_kind": "external_research_reference",
        "accessed_on": "2026-05-24",
        "verification_status": "verified_stable_public_reference",
        "boundary_note": "linguistics_context_only_repo_truth_and_closed_gate_markers_remain_authoritative",
        "use": "rationale_only_not_runtime_truth",
    },
    "sep_semantic_information": {
        "label": "Stanford Encyclopedia of Philosophy: Semantic Conceptions of Information",
        "url": "https://plato.stanford.edu/entries/information-semantic/",
        "rail": "semantic_information_and_uncertainty",
        "source_kind": "external_research_reference",
        "accessed_on": "2026-05-24",
        "verification_status": "verified_stable_public_reference",
        "boundary_note": "information_theory_context_only_repo_truth_and_closed_gate_markers_remain_authoritative",
        "use": "rationale_only_not_runtime_truth",
    },
    "nist_ai_600_1": {
        "label": "NIST AI 600-1 Generative AI Profile",
        "url": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
        "rail": "ai_governance_and_red_team_framing",
        "source_kind": "external_research_reference",
        "accessed_on": "2026-05-24",
        "verification_status": "verified_stable_public_reference",
        "boundary_note": "governance_risk_frame_only_repo_truth_and_closed_gate_markers_remain_authoritative",
        "use": "rationale_only_not_runtime_truth",
    },
    "pubmed_socratic_questioning_cbt": {
        "label": "PubMed: Socratic Questions With Children",
        "url": "https://pubmed.ncbi.nlm.nih.gov/32755910/",
        "rail": "cbt_socratic_questioning_context",
        "source_kind": "external_research_reference",
        "accessed_on": "2026-05-24",
        "verification_status": "verified_stable_public_reference",
        "boundary_note": "clinical_cbt_children_context_caution_only_not_product_efficacy_therapy_diagnosis_treatment_or_runtime_authority",
        "use": "rationale_only_not_runtime_truth",
    },
}

EXPECTED_SOURCES: dict[str, tuple[int, str]] = {
    "analytic_linguistic_audit": (
        22,
        "ccdb02fb-ec4f3348-d108b505-36ce9175-e35564d4-4dfa599b-bcb3a2fb-6221a938",
    ),
    "leibniz_information_theory": (
        12,
        "4e8f5ab1-3e8fcd37-c61981af-d31c9e73-c008a68e-cc480939-2c3ecfa7-b314b705",
    ),
    "philosophy_cbt_correlation_matrix": (
        13,
        "d6ae043d-a9de22ac-0ad825e4-3e0021e8-3cc4680d-59a9eabe-353d9e60-57d7d560",
    ),
    "philosophy_cbt_plan_adaptation_epic": (
        24,
        "d81cd0fd-753cf6d7-bcd58028-43d0e292-c41d83ac-08df1c63-fb0434e6-4035231f",
    ),
    "philosophy_full_roadmap": (
        19,
        "fdb0c06a-5fbad392-a8bab29e-423c551e-d0b25911-c3bb9ac9-7ecd3bbc-3c687fdf",
    ),
    "socratic_method_rag_llm_semantic_cache_cbt": (
        12,
        "b0ce7010-b3d45288-377e7a09-a39f2d34-8d89b1c8-e9048515-befac769-faf3f2fb",
    ),
}

REQUIRED_THEMES_BY_SOURCE: dict[str, set[str]] = {
    "analytic_linguistic_audit": {
        "analytic_falsification",
        "linguistic_meaning_as_use",
        "speech_acts",
        "hermeneutic_context",
    },
    "leibniz_information_theory": {
        "leibniz_monad_state",
        "information_uncertainty",
        "temporal_semantics",
        "evidence_compression",
    },
    "philosophy_cbt_correlation_matrix": {
        "cbt_mapping",
        "coaching_structure",
        "contradiction_review",
        "pragmatic_actionability",
    },
    "philosophy_cbt_plan_adaptation_epic": {
        "plan_adaptation",
        "next_best_action",
        "wellness_only_coaching",
        "verification_bundle_boundary",
    },
    "philosophy_full_roadmap": {
        "epic_sequence",
        "runtime_foundation_inventory",
        "semantic_cache_deferral",
        "rollout_governance",
    },
    "socratic_method_rag_llm_semantic_cache_cbt": {
        "socratic_questioning",
        "elenchus",
        "rag_verification",
        "cbt_reflection",
    },
}

REQUIRED_DISCIPLINES_BY_SOURCE: dict[str, set[str]] = {
    "analytic_linguistic_audit": {
        "philosophy",
        "linguistics",
        "ai_governance",
        "wellness_product",
    },
    "leibniz_information_theory": {
        "philosophy",
        "information_theory",
        "mathematics",
        "ai_governance",
    },
    "philosophy_cbt_correlation_matrix": {
        "philosophy",
        "cbt_coaching",
        "linguistics",
        "wellness_product",
    },
    "philosophy_cbt_plan_adaptation_epic": {
        "philosophy",
        "cbt_coaching",
        "wellness_product",
        "ai_governance",
    },
    "philosophy_full_roadmap": {
        "philosophy",
        "ai_governance",
        "cbt_coaching",
        "wellness_product",
    },
    "socratic_method_rag_llm_semantic_cache_cbt": {
        "philosophy",
        "cbt_coaching",
        "ai_governance",
        "wellness_product",
    },
}

REQUIRED_GLOBAL_THEMES = {
    "socratic_questioning",
    "leibniz_monad_state",
    "analytic_falsification",
    "linguistic_meaning_as_use",
    "cbt_mapping",
    "plan_adaptation",
    "semantic_cache_deferral",
}

REQUIRED_GLOBAL_DISCIPLINES = {
    "philosophy",
    "linguistics",
    "cbt_coaching",
    "information_theory",
    "mathematics",
    "ai_governance",
    "wellness_product",
}

ROADMAP_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

RUNTIME_FLAG_KEYS = (
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
    "runtime_activation_allowed",
    "provider_call_allowed",
    "insight_route_change_allowed",
)

FORBIDDEN_RUNTIME_PATHS = (
    "app/**",
    "core/ai/**",
    "core/insight/**",
    "core/knowledge/**",
    "core/rag/**",
    "core/verification/**",
    "core/evidence/**",
    "legacy_app.py",
    "mcp_pulseplate_server.py",
    "providers/**",
    "frontend/**",
    "ios/**",
    "alembic/**",
    "openapi/**",
)

_LOCAL_PATH_PREFIXES = (
    "/" + "Users/",
    "/" + "home/",
    "/" + "tmp/",
    "/private" + "/" + "tmp/",
    "/var" + "/folders/",
    "file" + "://",
    "C:" + "\\Users" + "\\",
)
_AWS_PARAMETER_PREFIX = "x-" + "amz-"
_AWS_CREDENTIAL_NAMES = (
    "aws" + "access" + "key" + "id",
    "access" + "_key" + "_id",
    "secret" + "access" + "key",
    "secret" + "_access" + "_key",
)
SECRET_OR_LOCAL_PATTERNS = (
    *(re.compile(re.escape(prefix), re.IGNORECASE) for prefix in _LOCAL_PATH_PREFIXES),
    re.compile(
        r"(?i)"
        + re.escape(_AWS_PARAMETER_PREFIX)
        + r"(?:credential|signature|security-token|algorithm)"
    ),
    re.compile(r"(?i)(?:" + "|".join(re.escape(name) for name in _AWS_CREDENTIAL_NAMES) + r")"),
    re.compile(r"(?i)(?:token|signature|credential)=[A-Za-z0-9_%./+=-]{12,}"),
    re.compile(r"(?i)(?<![A-Za-z0-9])" + "sk" + r"-[A-Za-z0-9_-]{16,}"),
)

FORBIDDEN_WELLNESS_CLAIMS = (
    re.compile(r"(?i)\bclinical\b"),
    re.compile(r"(?i)\bdiagnos(?:e|is|tic|tics)\b"),
    re.compile(r"(?i)\btreat(?:ment|s|ing)?\b"),
    re.compile(r"(?i)\btherapeutic\b"),
    re.compile(r"(?i)\bmedical care\b"),
    re.compile(r"(?i)\bpatient(?:s)?\b"),
)
ALLOWED_WELLNESS_BOUNDARY = (
    "cbt_inspired_reflective_wellness_coaching_not_medical_diagnosis_treatment_or_therapy"
)


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


def _object_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _validate_exact_keys(
    value: object,
    *,
    label: str,
    expected_keys: tuple[str, ...],
) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} must be an object"]
    actual = set(value)
    expected = set(expected_keys)
    errors: list[str] = []
    missing = [key for key in expected_keys if key not in actual]
    extra = sorted(actual - expected)
    if missing:
        errors.append(f"{label} missing required keys: {missing}")
    if extra:
        errors.append(f"{label} has unexpected keys: {extra}")
    return errors


def _schema_object_at(schema: dict[str, object], path: tuple[str, ...]) -> dict[str, object] | None:
    value: object = schema
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, dict) else None


def _schema_const_at(
    schema: dict[str, object],
    path: tuple[str, ...],
    expected: object,
) -> list[str]:
    target = _schema_object_at(schema, path)
    dotted = ".".join(path)
    if target is None:
        return [f"schema {dotted} must be an object with const {expected!r}"]
    if target.get("const") != expected:
        return [f"schema {dotted}.const must be {expected!r}"]
    return []


def _roadmap_markers(roadmap_text: str) -> dict[str, str]:
    markers: dict[str, str] = {}
    for match in re.finditer(r"<!--\s*([A-Z0-9_]+):\s*([^>]+?)\s*-->", roadmap_text):
        markers[match.group(1)] = match.group(2).strip()
    return markers


def _matches_forbidden_runtime_path(path: str) -> str | None:
    for pattern in FORBIDDEN_RUNTIME_PATHS:
        if pattern.endswith("/**"):
            if path.startswith(pattern.removesuffix("**")):
                return pattern
        elif path == pattern:
            return pattern
    return None


def _normalize_touched_path(raw_path: str) -> tuple[str | None, str | None]:
    path = raw_path.strip().replace("\\", "/")
    if not path:
        return None, "empty changed path is not allowed"
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            path = (
                candidate.resolve(strict=False)
                .relative_to(REPO_ROOT.resolve(strict=False))
                .as_posix()
            )
        except ValueError:
            return None, f"changed path is outside repo: {raw_path}"

    normalized = PurePosixPath(posixpath.normpath(path)).as_posix()
    if normalized in {".", ".."} or normalized.startswith("../"):
        return None, f"changed path escapes repo root: {raw_path}"
    return normalized, None


def validate_touched_paths(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for raw_path in paths:
        path, error = _normalize_touched_path(raw_path)
        if error is not None:
            errors.append(error)
            continue
        if path is None:
            errors.append(f"changed path could not be normalized: {raw_path}")
            continue
        forbidden = _matches_forbidden_runtime_path(path)
        if forbidden is not None:
            errors.append(
                f"{path}: PR-5 is docs/governance/test-only; forbidden runtime path {forbidden}"
            )
    return errors


def _validate_schema_object(schema: dict[str, object]) -> list[str]:
    errors: list[str] = []
    errors.extend(
        _validate_exact_keys(
            schema,
            label="source corpus schema",
            expected_keys=(
                "$schema",
                "$id",
                "title",
                "type",
                "additionalProperties",
                "required",
                "properties",
            ),
        )
    )
    if schema.get("$id") != "PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json":
        errors.append("schema $id must be PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json")
    if schema.get("title") != "Philosophy Source Corpus Index":
        errors.append("schema title must be Philosophy Source Corpus Index")
    if schema.get("type") != "object":
        errors.append("schema type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append("schema must be closed with additionalProperties=false")
    required = schema.get("required")
    if required != list(EXPECTED_INDEX_KEYS):
        errors.append(f"schema required keys must be {list(EXPECTED_INDEX_KEYS)}")
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        errors.append("schema properties must be an object")
        return errors
    errors.extend(
        _validate_exact_keys(
            properties, label="schema properties", expected_keys=EXPECTED_INDEX_KEYS
        )
    )
    for key, expected in (
        ("contract_id", CONTRACT_ID),
        ("contract_version", CONTRACT_VERSION),
        ("generated_at", GENERATED_AT),
        ("rollout_phase", ROLLOUT_PHASE),
        ("gate_status", "closed"),
        ("runtime_allowed", False),
        ("implementation_allowed", False),
        ("requires_dedicated_gate", True),
        ("source_count", len(EXPECTED_SOURCES)),
        ("total_pages", EXPECTED_TOTAL_PAGES),
    ):
        errors.extend(_schema_const_at(schema, ("properties", key), expected))

    semantic_markers = _schema_object_at(schema, ("properties", "semantic_cache_markers"))
    if semantic_markers is None:
        errors.append("schema semantic_cache_markers must be an object")
    else:
        if semantic_markers.get("additionalProperties") is not False:
            errors.append("schema semantic_cache_markers must be closed")
        if semantic_markers.get("required") != list(EXPECTED_SEMANTIC_MARKER_KEYS):
            errors.append("schema semantic_cache_markers required keys drifted")
        errors.extend(
            _validate_exact_keys(
                semantic_markers.get("properties"),
                label="schema semantic_cache_markers properties",
                expected_keys=EXPECTED_SEMANTIC_MARKER_KEYS,
            )
        )
        for key in EXPECTED_SEMANTIC_MARKER_KEYS:
            errors.extend(
                _schema_const_at(
                    schema,
                    ("properties", "semantic_cache_markers", "properties", key),
                    True,
                )
            )

    source_policy = _schema_object_at(schema, ("properties", "source_policy"))
    if source_policy is None:
        errors.append("schema source_policy must be an object")
    else:
        if source_policy.get("additionalProperties") is not False:
            errors.append("schema source_policy must be closed")
        if source_policy.get("required") != list(EXPECTED_SOURCE_POLICY_KEYS):
            errors.append("schema source_policy required keys drifted")
        errors.extend(
            _validate_exact_keys(
                source_policy.get("properties"),
                label="schema source_policy properties",
                expected_keys=EXPECTED_SOURCE_POLICY_KEYS,
            )
        )
        for key, expected in (
            ("authority", "operator_pdf_design_evidence_repo_truth_wins"),
            ("local_path_policy", "no_absolute_local_paths_committed"),
            ("text_policy", "metadata_and_paraphrase_only_no_full_pdf_text"),
            ("promotion_policy", "not_runtime_truth_without_reviewed_contract"),
            ("credential_policy", "credential_like_urls_forbidden"),
            ("wellness_boundary", ALLOWED_WELLNESS_BOUNDARY),
        ):
            errors.extend(
                _schema_const_at(
                    schema, ("properties", "source_policy", "properties", key), expected
                )
            )

    sources = _schema_object_at(schema, ("properties", "sources"))
    if sources is None:
        errors.append("schema sources must be an object")
    else:
        if sources.get("minItems") != len(EXPECTED_SOURCES):
            errors.append(f"schema sources.minItems must be {len(EXPECTED_SOURCES)}")
        if sources.get("maxItems") != len(EXPECTED_SOURCES):
            errors.append(f"schema sources.maxItems must be {len(EXPECTED_SOURCES)}")
    source_item = _schema_object_at(schema, ("properties", "sources", "items"))
    if source_item is None:
        errors.append("schema sources.items must be an object")
    else:
        if source_item.get("additionalProperties") is not False:
            errors.append("schema sources.items must be closed")
        if source_item.get("required") != list(EXPECTED_SOURCE_KEYS):
            errors.append("schema sources.items required keys drifted")
        errors.extend(
            _validate_exact_keys(
                source_item.get("properties"),
                label="schema sources.items properties",
                expected_keys=EXPECTED_SOURCE_KEYS,
            )
        )
        errors.extend(
            _schema_const_at(
                schema, ("properties", "sources", "items", "properties", "language"), "ru"
            )
        )
        errors.extend(
            _schema_const_at(
                schema,
                ("properties", "sources", "items", "properties", "extraction_status"),
                "metadata_and_text_extract_verified",
            )
        )
        source_family = _schema_object_at(
            schema, ("properties", "sources", "items", "properties", "source_family")
        )
        if source_family is None or source_family.get("enum") != list(EXPECTED_SOURCE_FAMILIES):
            errors.append("schema source_family enum drifted")

    runtime_flags = _schema_object_at(
        schema, ("properties", "sources", "items", "properties", "runtime_flags")
    )
    if runtime_flags is None:
        errors.append("schema runtime_flags must be an object")
    else:
        if runtime_flags.get("additionalProperties") is not False:
            errors.append("schema runtime_flags must be closed")
        if runtime_flags.get("required") != list(RUNTIME_FLAG_KEYS):
            errors.append("schema runtime_flags required keys drifted")
        errors.extend(
            _validate_exact_keys(
                runtime_flags.get("properties"),
                label="schema runtime_flags properties",
                expected_keys=RUNTIME_FLAG_KEYS,
            )
        )
        for key in RUNTIME_FLAG_KEYS:
            errors.extend(
                _schema_const_at(
                    schema,
                    (
                        "properties",
                        "sources",
                        "items",
                        "properties",
                        "runtime_flags",
                        "properties",
                        key,
                    ),
                    False,
                )
            )

    research_basis = _schema_object_at(schema, ("properties", "research_basis"))
    if research_basis is None:
        errors.append("schema research_basis must be an object")
    else:
        if research_basis.get("minItems") != len(EXPECTED_RESEARCH_BASIS):
            errors.append(f"schema research_basis.minItems must be {len(EXPECTED_RESEARCH_BASIS)}")
        if research_basis.get("maxItems") != len(EXPECTED_RESEARCH_BASIS):
            errors.append(f"schema research_basis.maxItems must be {len(EXPECTED_RESEARCH_BASIS)}")
    research_item = _schema_object_at(schema, ("properties", "research_basis", "items"))
    if research_item is None:
        errors.append("schema research_basis.items must be an object")
    else:
        if research_item.get("additionalProperties") is not False:
            errors.append("schema research_basis.items must be closed")
        if research_item.get("required") != list(EXPECTED_RESEARCH_BASIS_KEYS):
            errors.append("schema research_basis.items required keys drifted")
        errors.extend(
            _validate_exact_keys(
                research_item.get("properties"),
                label="schema research_basis.items properties",
                expected_keys=EXPECTED_RESEARCH_BASIS_KEYS,
            )
        )
        errors.extend(
            _schema_const_at(
                schema,
                ("properties", "research_basis", "items", "properties", "use"),
                "rationale_only_not_runtime_truth",
            )
        )
    return errors


def _validate_no_secret_or_local_paths(text: str, *, label: str) -> list[str]:
    errors: list[str] = []
    for pattern in SECRET_OR_LOCAL_PATTERNS:
        match = pattern.search(text)
        if match:
            errors.append(
                f"{label}: forbidden local path or credential-like token: {match.group(0)}"
            )
    return errors


def validate_file_contents(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for raw_path in paths:
        path, error = _normalize_touched_path(raw_path)
        if error is not None:
            errors.append(error)
            continue
        if path is None:
            errors.append(f"changed path could not be normalized: {raw_path}")
            continue
        candidate = REPO_ROOT / path
        if not candidate.exists() or not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{path}: PR-5 file must be UTF-8 text for leakage scan")
            continue
        errors.extend(_validate_no_secret_or_local_paths(text, label=path))
    return errors


def _validate_runtime_flags(index: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for key in (
        "runtime_allowed",
        "implementation_allowed",
    ):
        if index.get(key) is not False:
            errors.append(f"{key} must be false")
    if index.get("gate_status") != "closed":
        errors.append("gate_status must stay closed")
    if index.get("requires_dedicated_gate") is not True:
        errors.append("requires_dedicated_gate must stay true")

    semantic_markers, marker_errors = _as_object(
        index.get("semantic_cache_markers"), label="semantic_cache_markers"
    )
    errors.extend(marker_errors)
    errors.extend(
        _validate_exact_keys(
            semantic_markers,
            label="semantic_cache_markers",
            expected_keys=EXPECTED_SEMANTIC_MARKER_KEYS,
        )
    )
    for key in (
        "gate_status_closed",
        "runtime_allowed_false",
        "implementation_allowed_false",
        "dedicated_gate_required",
    ):
        if semantic_markers.get(key) is not True:
            errors.append(f"semantic_cache_markers.{key} must be true")

    for source in _object_items(index.get("sources")):
        source_id = source.get("source_id", "<unknown>")
        flags, flag_errors = _as_object(
            source.get("runtime_flags"), label=f"{source_id}.runtime_flags"
        )
        errors.extend(flag_errors)
        errors.extend(
            _validate_exact_keys(
                flags,
                label=f"{source_id}.runtime_flags",
                expected_keys=RUNTIME_FLAG_KEYS,
            )
        )
        for key in RUNTIME_FLAG_KEYS:
            if flags.get(key) is not False:
                errors.append(f"{source_id}.runtime_flags.{key} must be false")
    return errors


def _validate_sources(index: dict[str, object]) -> list[str]:
    errors: list[str] = []
    sources = _object_items(index.get("sources"))
    if len(sources) != len(EXPECTED_SOURCES):
        errors.append(f"sources must contain {len(EXPECTED_SOURCES)} entries")

    source_ids = [str(source.get("source_id", "")) for source in sources]
    if len(source_ids) != len(set(source_ids)):
        errors.append("sources must not contain duplicate source_id values")
    if source_ids != sorted(EXPECTED_SOURCES):
        errors.append(f"sources must be sorted and complete: {sorted(EXPECTED_SOURCES)}")

    total_pages = 0
    global_themes: set[str] = set()
    global_disciplines: set[str] = set()
    for source in sources:
        errors.extend(
            _validate_exact_keys(
                source,
                label=f"{source.get('source_id', '<unknown>')}",
                expected_keys=EXPECTED_SOURCE_KEYS,
            )
        )
        source_id = str(source.get("source_id", ""))
        if source_id not in EXPECTED_SOURCES:
            errors.append(f"unexpected source_id: {source_id}")
            continue
        expected_pages, expected_sha = EXPECTED_SOURCES[source_id]
        if source.get("page_count") != expected_pages:
            errors.append(f"{source_id}.page_count must be {expected_pages}")
        if source.get("sha256") != expected_sha:
            errors.append(f"{source_id}.sha256 must match verified PDF hash")
        page_count = source.get("page_count")
        if isinstance(page_count, int):
            total_pages += page_count

        sanitized_filename = source.get("sanitized_filename")
        if not isinstance(sanitized_filename, str) or "/" in sanitized_filename:
            errors.append(
                f"{source_id}.sanitized_filename must be a basename without path separators"
            )
        if source.get("extraction_status") != "metadata_and_text_extract_verified":
            errors.append(
                f"{source_id}.extraction_status must be metadata_and_text_extract_verified"
            )
        if len(_string_items(source.get("linked_repo_anchors"))) == 0:
            errors.append(f"{source_id}.linked_repo_anchors must not be empty")
        themes = set(_string_items(source.get("theme_families")))
        disciplines = set(_string_items(source.get("discipline_rails")))
        missing_themes = sorted(REQUIRED_THEMES_BY_SOURCE[source_id] - themes)
        missing_disciplines = sorted(REQUIRED_DISCIPLINES_BY_SOURCE[source_id] - disciplines)
        if missing_themes:
            errors.append(f"{source_id}.theme_families missing required themes: {missing_themes}")
        if missing_disciplines:
            errors.append(
                f"{source_id}.discipline_rails missing required disciplines: {missing_disciplines}"
            )
        global_themes.update(themes)
        global_disciplines.update(disciplines)

    if index.get("source_count") != len(EXPECTED_SOURCES):
        errors.append(f"source_count must be {len(EXPECTED_SOURCES)}")
    if index.get("total_pages") != EXPECTED_TOTAL_PAGES:
        errors.append(f"total_pages must be {EXPECTED_TOTAL_PAGES}")
    if total_pages != EXPECTED_TOTAL_PAGES:
        errors.append(f"sources page_count sum must be {EXPECTED_TOTAL_PAGES}")
    missing_global_themes = sorted(REQUIRED_GLOBAL_THEMES - global_themes)
    missing_global_disciplines = sorted(REQUIRED_GLOBAL_DISCIPLINES - global_disciplines)
    if missing_global_themes:
        errors.append(f"source corpus missing global theme coverage: {missing_global_themes}")
    if missing_global_disciplines:
        errors.append(
            f"source corpus missing global discipline coverage: {missing_global_disciplines}"
        )
    return errors


def _validate_wellness_boundary(index: dict[str, object]) -> list[str]:
    errors: list[str] = []
    policy, policy_errors = _as_object(index.get("source_policy"), label="source_policy")
    errors.extend(policy_errors)
    errors.extend(
        _validate_exact_keys(
            policy,
            label="source_policy",
            expected_keys=EXPECTED_SOURCE_POLICY_KEYS,
        )
    )
    if policy.get("wellness_boundary") != ALLOWED_WELLNESS_BOUNDARY:
        errors.append(f"source_policy.wellness_boundary must be {ALLOWED_WELLNESS_BOUNDARY}")

    for source in _object_items(index.get("sources")):
        source_id = str(source.get("source_id", "<unknown>"))
        candidate_text = " ".join(
            str(source.get(field, ""))
            for field in ("summary", "future_handoff", "title", "source_family")
        )
        for pattern in FORBIDDEN_WELLNESS_CLAIMS:
            match = pattern.search(candidate_text)
            if match:
                errors.append(
                    f"{source_id}: forbidden medical/therapy positioning: {match.group(0)}"
                )
    return errors


def _validate_research_basis(index: dict[str, object]) -> list[str]:
    errors: list[str] = []
    basis = _object_items(index.get("research_basis"))
    if len(basis) != len(EXPECTED_RESEARCH_BASIS):
        errors.append(f"research_basis must contain {len(EXPECTED_RESEARCH_BASIS)} sources")
    ids = [str(item.get("id", "")) for item in basis]
    if len(ids) != len(set(ids)):
        errors.append("research_basis ids must be unique")
    expected_ids = list(EXPECTED_RESEARCH_BASIS)
    if ids != expected_ids:
        errors.append(f"research_basis must be sorted and complete: {expected_ids}")
    for item in basis:
        errors.extend(
            _validate_exact_keys(
                item,
                label=f"{item.get('id', '<unknown>')}",
                expected_keys=EXPECTED_RESEARCH_BASIS_KEYS,
            )
        )
        item_id = str(item.get("id", "<unknown>"))
        expected = EXPECTED_RESEARCH_BASIS.get(item_id)
        if expected is None:
            errors.append(f"unexpected research_basis id: {item_id}")
            continue
        for key, expected_value in expected.items():
            if item.get(key) != expected_value:
                errors.append(f"{item_id}.{key} must be {expected_value}")
        if item.get("use") != "rationale_only_not_runtime_truth":
            errors.append(f"{item_id}.use must be rationale_only_not_runtime_truth")
        url = item.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            errors.append(f"{item_id}.url must be an https URL")
    return errors


def _validate_roadmap_markers(roadmap_text: str) -> list[str]:
    markers = _roadmap_markers(roadmap_text)
    errors: list[str] = []
    for marker, expected_value in ROADMAP_MARKERS.items():
        if markers.get(marker) != expected_value:
            errors.append(f"roadmap marker {marker} must be {expected_value}")
    return errors


def _validate_gate_report(gate_report_text: str) -> list[str]:
    gate_report, errors = _load_json_no_duplicate_keys(
        gate_report_text,
        invalid_prefix="invalid gate report JSON",
        duplicate_prefix="duplicate gate report key",
    )
    if errors:
        return errors
    report, object_errors = _as_object(gate_report, label="gate report")
    errors.extend(object_errors)
    for key in (
        "gate_open_allowed",
        "runtime_handoff_allowed",
        "cache_read_allowed",
        "cache_write_allowed",
        "serving_allowed",
    ):
        if report.get(key) is not False:
            errors.append(f"gate report {key} must remain false")
    return errors


def validate_philosophy_source_corpus_index(
    *,
    index_text: str,
    schema_text: str,
    roadmap_text: str,
    gate_report_text: str,
) -> list[str]:
    errors: list[str] = []
    index_json, index_errors = _load_json_no_duplicate_keys(
        index_text,
        invalid_prefix="invalid source corpus index JSON",
        duplicate_prefix="duplicate source corpus index key",
    )
    schema_json, schema_errors = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="invalid source corpus schema JSON",
        duplicate_prefix="duplicate source corpus schema key",
    )
    errors.extend(index_errors)
    errors.extend(schema_errors)
    if errors:
        return errors

    index, object_errors = _as_object(index_json, label="source corpus index")
    schema, schema_object_errors = _as_object(schema_json, label="source corpus schema")
    errors.extend(object_errors)
    errors.extend(schema_object_errors)
    if errors:
        return errors

    if index.get("contract_id") != CONTRACT_ID:
        errors.append(f"contract_id must be {CONTRACT_ID}")
    if index.get("contract_version") != CONTRACT_VERSION:
        errors.append(f"contract_version must be {CONTRACT_VERSION}")
    if index.get("generated_at") != GENERATED_AT:
        errors.append(f"generated_at must be {GENERATED_AT}")
    if index.get("rollout_phase") != ROLLOUT_PHASE:
        errors.append(f"rollout_phase must be {ROLLOUT_PHASE}")
    errors.extend(
        _validate_exact_keys(
            index,
            label="source corpus index",
            expected_keys=EXPECTED_INDEX_KEYS,
        )
    )

    canonical_index = json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    canonical_schema = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
    if index_text != canonical_index:
        errors.append("source corpus index JSON must be canonical two-space JSON")
    if schema_text != canonical_schema:
        errors.append("source corpus schema JSON must be canonical two-space JSON")

    errors.extend(_validate_schema_object(schema))
    errors.extend(_validate_runtime_flags(index))
    errors.extend(_validate_sources(index))
    errors.extend(_validate_wellness_boundary(index))
    errors.extend(_validate_research_basis(index))
    errors.extend(_validate_roadmap_markers(roadmap_text))
    errors.extend(_validate_gate_report(gate_report_text))
    errors.extend(_validate_no_secret_or_local_paths(index_text, label="source corpus index"))
    errors.extend(_validate_no_secret_or_local_paths(schema_text, label="source corpus schema"))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the source corpus index.")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--roadmap", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--gate-report", type=Path, default=DEFAULT_GATE_REPORT)
    parser.add_argument("--files", nargs="*", default=[], help="Optional PR-touched paths.")
    args = parser.parse_args(argv)

    if not args.check:
        parser.error("--check is required")

    errors = validate_philosophy_source_corpus_index(
        index_text=args.index.read_text(encoding="utf-8"),
        schema_text=args.schema.read_text(encoding="utf-8"),
        roadmap_text=args.roadmap.read_text(encoding="utf-8"),
        gate_report_text=args.gate_report.read_text(encoding="utf-8"),
    )
    errors.extend(validate_touched_paths(list(args.files)))
    errors.extend(validate_file_contents(list(args.files)))
    if errors:
        print("ERROR: philosophy source corpus index check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("philosophy-source-corpus-index: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
