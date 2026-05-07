"""Pure deterministic exact/fuzzy cache scaffold contracts.

SC-G2 is an offline scaffold only. It derives stable lexical keys and lookup
decisions from explicit inputs; it does not store responses, serve cache hits,
read clocks, call providers, or wire runtime routes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import json
import re
from typing import TypeAlias
import unicodedata

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

NORMALIZATION_VERSION = "exact-fuzzy-nfkc-v1"

MATCH_DECISION_HIT = "hit"
MATCH_DECISION_MISS = "miss"
MATCH_MODE_EXACT = "exact"
MATCH_MODE_REORDERED_TOKENS = "fuzzy_reordered_tokens"
MATCH_MODE_NEAR_DUPLICATE = "fuzzy_near_duplicate"

_TOKEN_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ExactFuzzyCacheLineage:
    """Evidence Graph lineage IDs required by the SC-G2 scaffold."""

    eval_event_ids: tuple[str, ...]
    admission_decision_id: str | None
    promotion_ids: tuple[str, ...]
    replay_entry_ids: tuple[str, ...]
    source_fingerprints: tuple[str, ...]
    policy_version: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "eval_event_ids",
            _normalize_unique_tokens("eval_event_ids", self.eval_event_ids),
        )
        object.__setattr__(
            self,
            "admission_decision_id",
            (
                None
                if self.admission_decision_id is None
                else _validate_token("admission_decision_id", self.admission_decision_id)
            ),
        )
        object.__setattr__(
            self,
            "promotion_ids",
            _normalize_unique_tokens("promotion_ids", self.promotion_ids),
        )
        object.__setattr__(
            self,
            "replay_entry_ids",
            _normalize_unique_tokens("replay_entry_ids", self.replay_entry_ids),
        )
        object.__setattr__(
            self,
            "source_fingerprints",
            _normalize_required_unique_tokens(
                "source_fingerprints",
                self.source_fingerprints,
            ),
        )
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )


@dataclass(frozen=True)
class ExactFuzzyCacheRecord:
    """Derived, non-serving exact/fuzzy cache scaffold record."""

    record_id: str
    surface: str
    normalized_query: str
    token_sort_key: tuple[str, ...]
    context_fingerprint: str
    provider_key: str
    model_key: str
    user_tier: str
    transparency_notice_id: str
    lineage: ExactFuzzyCacheLineage
    response_fingerprint: str
    safety_flags: tuple[str, ...]
    idempotency_key: str
    normalization_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _validate_token("record_id", self.record_id))
        object.__setattr__(self, "surface", _validate_token("surface", self.surface))
        object.__setattr__(
            self,
            "normalized_query",
            _validate_non_empty_text("normalized_query", self.normalized_query),
        )
        object.__setattr__(
            self,
            "token_sort_key",
            _normalize_required_tokens("token_sort_key", self.token_sort_key),
        )
        object.__setattr__(
            self,
            "context_fingerprint",
            _validate_token("context_fingerprint", self.context_fingerprint),
        )
        object.__setattr__(self, "provider_key", _validate_token("provider_key", self.provider_key))
        object.__setattr__(self, "model_key", _validate_token("model_key", self.model_key))
        object.__setattr__(self, "user_tier", _validate_token("user_tier", self.user_tier))
        object.__setattr__(
            self,
            "transparency_notice_id",
            _validate_token("transparency_notice_id", self.transparency_notice_id),
        )
        if not isinstance(self.lineage, ExactFuzzyCacheLineage):
            raise ValueError("lineage must be ExactFuzzyCacheLineage")
        object.__setattr__(
            self,
            "response_fingerprint",
            _validate_token("response_fingerprint", self.response_fingerprint),
        )
        object.__setattr__(
            self,
            "safety_flags",
            _normalize_unique_tokens("safety_flags", self.safety_flags),
        )
        object.__setattr__(
            self,
            "idempotency_key",
            _validate_token("idempotency_key", self.idempotency_key),
        )
        object.__setattr__(
            self,
            "normalization_version",
            _validate_token("normalization_version", self.normalization_version),
        )


@dataclass(frozen=True)
class ExactFuzzyCacheLookupRequest:
    """Explicit lookup request for offline exact/fuzzy matching."""

    surface: str
    raw_query: str
    context_fingerprint: str
    source_fingerprints: tuple[str, ...]
    policy_version: str
    provider_key: str
    model_key: str
    user_tier: str
    transparency_notice_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "surface", _validate_token("surface", self.surface))
        object.__setattr__(self, "raw_query", _validate_non_empty_text("raw_query", self.raw_query))
        object.__setattr__(
            self,
            "context_fingerprint",
            _validate_token("context_fingerprint", self.context_fingerprint),
        )
        object.__setattr__(
            self,
            "source_fingerprints",
            _normalize_required_unique_tokens(
                "source_fingerprints",
                self.source_fingerprints,
            ),
        )
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )
        object.__setattr__(self, "provider_key", _validate_token("provider_key", self.provider_key))
        object.__setattr__(self, "model_key", _validate_token("model_key", self.model_key))
        object.__setattr__(self, "user_tier", _validate_token("user_tier", self.user_tier))
        object.__setattr__(
            self,
            "transparency_notice_id",
            _validate_token("transparency_notice_id", self.transparency_notice_id),
        )


@dataclass(frozen=True)
class ExactFuzzyCacheLookupResult:
    """Deterministic non-serving lookup result."""

    decision: str
    matched_record_id: str | None
    match_mode: str | None
    score_bps: int | None
    checked_record_count: int
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.decision not in {MATCH_DECISION_HIT, MATCH_DECISION_MISS}:
            raise ValueError(f"unsupported decision: {self.decision!r}")
        if self.matched_record_id is not None:
            object.__setattr__(
                self,
                "matched_record_id",
                _validate_token("matched_record_id", self.matched_record_id),
            )
        if self.match_mode not in {
            None,
            MATCH_MODE_EXACT,
            MATCH_MODE_REORDERED_TOKENS,
            MATCH_MODE_NEAR_DUPLICATE,
        }:
            raise ValueError(f"unsupported match_mode: {self.match_mode!r}")
        if self.score_bps is not None:
            _validate_bps("score_bps", self.score_bps)
        if self.checked_record_count < 0:
            raise ValueError("checked_record_count must be non-negative")
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_unique_tokens("reason_codes", self.reason_codes),
        )


@dataclass(frozen=True)
class ExactFuzzyMatchPolicy:
    """Thresholds for deterministic exact/fuzzy matching."""

    policy_version: str
    token_jaccard_min_bps: int
    sequence_ratio_min_bps: int
    max_token_count_delta: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )
        _validate_bps("token_jaccard_min_bps", self.token_jaccard_min_bps)
        _validate_bps("sequence_ratio_min_bps", self.sequence_ratio_min_bps)
        if self.max_token_count_delta < 0:
            raise ValueError("max_token_count_delta must be non-negative")


def normalize_exact_fuzzy_query(text: str) -> tuple[str, tuple[str, ...]]:
    """Normalize text into a deterministic lexical query and token key."""

    normalized = unicodedata.normalize("NFKC", _validate_non_empty_text("text", text)).casefold()
    chars = [
        " " if unicodedata.category(char).startswith(("P", "S")) else char for char in normalized
    ]
    normalized = _TOKEN_RE.sub(" ", "".join(chars)).strip()
    if not normalized:
        raise ValueError("text must contain lexical content after normalization")
    tokens = normalized.split(" ") if normalized else []
    return normalized, tuple(sorted(tokens))


def build_exact_fuzzy_lineage(
    *,
    eval_event_ids: Iterable[str] = (),
    admission_decision_id: str | None,
    promotion_ids: Iterable[str] = (),
    replay_entry_ids: Iterable[str] = (),
    source_fingerprints: Iterable[str],
    policy_version: str,
) -> ExactFuzzyCacheLineage:
    """Build normalized Evidence Graph lineage for an exact/fuzzy record."""

    return ExactFuzzyCacheLineage(
        eval_event_ids=tuple(eval_event_ids),
        admission_decision_id=admission_decision_id,
        promotion_ids=tuple(promotion_ids),
        replay_entry_ids=tuple(replay_entry_ids),
        source_fingerprints=tuple(source_fingerprints),
        policy_version=policy_version,
    )


def build_exact_fuzzy_record_id(
    *,
    surface: str,
    normalized_query: str,
    token_sort_key: Iterable[str],
    context_fingerprint: str,
    provider_key: str,
    model_key: str,
    user_tier: str,
    transparency_notice_id: str,
    lineage: ExactFuzzyCacheLineage,
    response_fingerprint: str,
    safety_flags: Iterable[str] = (),
    normalization_version: str = NORMALIZATION_VERSION,
) -> str:
    """Build a deterministic record ID from derived non-sensitive fields."""

    payload: JsonValue = _record_identity_payload(
        surface=surface,
        normalized_query=normalized_query,
        token_sort_key=tuple(token_sort_key),
        context_fingerprint=context_fingerprint,
        provider_key=provider_key,
        model_key=model_key,
        user_tier=user_tier,
        transparency_notice_id=transparency_notice_id,
        lineage=lineage,
        response_fingerprint=response_fingerprint,
        safety_flags=tuple(safety_flags),
        normalization_version=normalization_version,
    )
    return f"exact-fuzzy-record:{_fingerprint_payload(payload)[:24]}"


def build_exact_fuzzy_idempotency_key(
    *,
    surface: str,
    normalized_query: str,
    context_fingerprint: str,
    provider_key: str,
    model_key: str,
    user_tier: str,
    transparency_notice_id: str,
    lineage: ExactFuzzyCacheLineage,
    response_fingerprint: str,
    normalization_version: str = NORMALIZATION_VERSION,
) -> str:
    """Build a deterministic idempotency key for replay-safe scaffold records."""

    payload: JsonValue = {
        "context_fingerprint": _validate_token("context_fingerprint", context_fingerprint),
        "lineage": _lineage_payload(lineage),
        "model_key": _validate_token("model_key", model_key),
        "normalization_version": _validate_token(
            "normalization_version",
            normalization_version,
        ),
        "normalized_query": _validate_non_empty_text("normalized_query", normalized_query),
        "provider_key": _validate_token("provider_key", provider_key),
        "response_fingerprint": _validate_token("response_fingerprint", response_fingerprint),
        "surface": _validate_token("surface", surface),
        "transparency_notice_id": _validate_token(
            "transparency_notice_id",
            transparency_notice_id,
        ),
        "user_tier": _validate_token("user_tier", user_tier),
    }
    return f"exact-fuzzy-idempotency:{_fingerprint_payload(payload)[:24]}"


def create_exact_fuzzy_cache_record(
    *,
    surface: str,
    raw_query: str,
    context_fingerprint: str,
    provider_key: str,
    model_key: str,
    user_tier: str,
    transparency_notice_id: str,
    lineage: ExactFuzzyCacheLineage,
    response_fingerprint: str,
    safety_flags: Iterable[str] = (),
    normalization_version: str = NORMALIZATION_VERSION,
) -> ExactFuzzyCacheRecord:
    """Create a deterministic exact/fuzzy scaffold record without payload storage."""

    normalized_query, token_sort_key = normalize_exact_fuzzy_query(raw_query)
    normalized_safety_flags = _normalize_unique_tokens("safety_flags", tuple(safety_flags))
    record_id = build_exact_fuzzy_record_id(
        surface=surface,
        normalized_query=normalized_query,
        token_sort_key=token_sort_key,
        context_fingerprint=context_fingerprint,
        provider_key=provider_key,
        model_key=model_key,
        user_tier=user_tier,
        transparency_notice_id=transparency_notice_id,
        lineage=lineage,
        response_fingerprint=response_fingerprint,
        safety_flags=normalized_safety_flags,
        normalization_version=normalization_version,
    )
    idempotency_key = build_exact_fuzzy_idempotency_key(
        surface=surface,
        normalized_query=normalized_query,
        context_fingerprint=context_fingerprint,
        provider_key=provider_key,
        model_key=model_key,
        user_tier=user_tier,
        transparency_notice_id=transparency_notice_id,
        lineage=lineage,
        response_fingerprint=response_fingerprint,
        normalization_version=normalization_version,
    )
    return ExactFuzzyCacheRecord(
        record_id=record_id,
        surface=surface,
        normalized_query=normalized_query,
        token_sort_key=token_sort_key,
        context_fingerprint=context_fingerprint,
        provider_key=provider_key,
        model_key=model_key,
        user_tier=user_tier,
        transparency_notice_id=transparency_notice_id,
        lineage=lineage,
        response_fingerprint=response_fingerprint,
        safety_flags=normalized_safety_flags,
        idempotency_key=idempotency_key,
        normalization_version=normalization_version,
    )


def match_exact_fuzzy_records(
    *,
    request: ExactFuzzyCacheLookupRequest,
    candidate_records: Iterable[ExactFuzzyCacheRecord],
    policy: ExactFuzzyMatchPolicy,
) -> ExactFuzzyCacheLookupResult:
    """Match records deterministically without serving cached output."""

    if request.policy_version != policy.policy_version:
        raise ValueError("request policy_version must match match policy")

    normalized_query, token_sort_key = normalize_exact_fuzzy_query(request.raw_query)
    partitioned = tuple(
        record
        for record in candidate_records
        if _record_partition_matches(request=request, record=record)
    )
    matches: list[tuple[int, int, str, str, int, ExactFuzzyCacheRecord, str]] = []

    for index, record in enumerate(partitioned):
        if record.normalization_version != NORMALIZATION_VERSION:
            continue
        if record.normalized_query == normalized_query:
            matches.append(
                (
                    0,
                    -10000,
                    record.normalized_query,
                    record.record_id,
                    index,
                    record,
                    MATCH_MODE_EXACT,
                )
            )
            continue
        if record.token_sort_key == token_sort_key:
            matches.append(
                (
                    1,
                    -9900,
                    record.normalized_query,
                    record.record_id,
                    index,
                    record,
                    MATCH_MODE_REORDERED_TOKENS,
                )
            )
            continue
        near_score = _near_duplicate_score_bps(
            left_query=normalized_query,
            right_query=record.normalized_query,
            left_tokens=token_sort_key,
            right_tokens=record.token_sort_key,
            policy=policy,
        )
        if near_score is not None:
            matches.append(
                (
                    2,
                    -near_score,
                    record.normalized_query,
                    record.record_id,
                    index,
                    record,
                    MATCH_MODE_NEAR_DUPLICATE,
                )
            )

    if not matches:
        return ExactFuzzyCacheLookupResult(
            decision=MATCH_DECISION_MISS,
            matched_record_id=None,
            match_mode=None,
            score_bps=None,
            checked_record_count=len(partitioned),
            reason_codes=("no_partition_match" if not partitioned else "no_match",),
        )

    best = sorted(matches)[0]
    score_bps = -best[1]
    record = best[5]
    match_mode = best[6]
    return ExactFuzzyCacheLookupResult(
        decision=MATCH_DECISION_HIT,
        matched_record_id=record.record_id,
        match_mode=match_mode,
        score_bps=score_bps,
        checked_record_count=len(partitioned),
        reason_codes=(f"{match_mode}_match", "sc_g2_non_serving_lookup"),
    )


def _near_duplicate_score_bps(
    *,
    left_query: str,
    right_query: str,
    left_tokens: tuple[str, ...],
    right_tokens: tuple[str, ...],
    policy: ExactFuzzyMatchPolicy,
) -> int | None:
    if abs(len(left_tokens) - len(right_tokens)) > policy.max_token_count_delta:
        return None
    jaccard_bps = _token_jaccard_bps(left_tokens, right_tokens)
    if jaccard_bps < policy.token_jaccard_min_bps:
        return None
    ratio_bps = int(SequenceMatcher(None, left_query, right_query, autojunk=False).ratio() * 10000)
    if ratio_bps < policy.sequence_ratio_min_bps:
        return None
    return min(jaccard_bps, ratio_bps)


def _token_jaccard_bps(left_tokens: tuple[str, ...], right_tokens: tuple[str, ...]) -> int:
    left = set(left_tokens)
    right = set(right_tokens)
    union = left | right
    if not union:
        return 0
    return (len(left & right) * 10000) // len(union)


def _record_partition_matches(
    *,
    request: ExactFuzzyCacheLookupRequest,
    record: ExactFuzzyCacheRecord,
) -> bool:
    return (
        record.surface == request.surface
        and record.context_fingerprint == request.context_fingerprint
        and record.lineage.source_fingerprints == request.source_fingerprints
        and record.lineage.policy_version == request.policy_version
        and record.provider_key == request.provider_key
        and record.model_key == request.model_key
        and record.user_tier == request.user_tier
        and record.transparency_notice_id == request.transparency_notice_id
    )


def _record_identity_payload(
    *,
    surface: str,
    normalized_query: str,
    token_sort_key: tuple[str, ...],
    context_fingerprint: str,
    provider_key: str,
    model_key: str,
    user_tier: str,
    transparency_notice_id: str,
    lineage: ExactFuzzyCacheLineage,
    response_fingerprint: str,
    safety_flags: tuple[str, ...],
    normalization_version: str,
) -> dict[str, JsonValue]:
    return {
        "context_fingerprint": _validate_token("context_fingerprint", context_fingerprint),
        "lineage": _lineage_payload(lineage),
        "model_key": _validate_token("model_key", model_key),
        "normalization_version": _validate_token("normalization_version", normalization_version),
        "normalized_query": _validate_non_empty_text("normalized_query", normalized_query),
        "provider_key": _validate_token("provider_key", provider_key),
        "response_fingerprint": _validate_token("response_fingerprint", response_fingerprint),
        "safety_flags": list(_normalize_unique_tokens("safety_flags", safety_flags)),
        "surface": _validate_token("surface", surface),
        "token_sort_key": list(_normalize_required_tokens("token_sort_key", token_sort_key)),
        "transparency_notice_id": _validate_token(
            "transparency_notice_id",
            transparency_notice_id,
        ),
        "user_tier": _validate_token("user_tier", user_tier),
    }


def _lineage_payload(lineage: ExactFuzzyCacheLineage) -> dict[str, JsonValue]:
    if not isinstance(lineage, ExactFuzzyCacheLineage):
        raise ValueError("lineage must be ExactFuzzyCacheLineage")
    return {
        "admission_decision_id": lineage.admission_decision_id,
        "eval_event_ids": list(lineage.eval_event_ids),
        "policy_version": lineage.policy_version,
        "promotion_ids": list(lineage.promotion_ids),
        "replay_entry_ids": list(lineage.replay_entry_ids),
        "source_fingerprints": list(lineage.source_fingerprints),
    }


def _fingerprint_payload(payload: JsonValue) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_required_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = _normalize_unique_tokens(name, values)
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _normalize_required_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted(_validate_token(name, value) for value in values))
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _normalize_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _validate_token(name, value)
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate entries")
        seen.add(normalized)
        normalized_values.append(normalized)
    return tuple(sorted(normalized_values))


def _validate_token(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    return normalized


def _validate_non_empty_text(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _validate_bps(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0 or value > 10000:
        raise ValueError(f"{name} must be between 0 and 10000")


def to_stable_mapping(record: ExactFuzzyCacheRecord) -> Mapping[str, JsonValue]:
    """Serialize a record deterministically for tests and non-runtime review."""

    return {
        "context_fingerprint": record.context_fingerprint,
        "idempotency_key": record.idempotency_key,
        "lineage": _lineage_payload(record.lineage),
        "model_key": record.model_key,
        "normalization_version": record.normalization_version,
        "normalized_query": record.normalized_query,
        "provider_key": record.provider_key,
        "record_id": record.record_id,
        "response_fingerprint": record.response_fingerprint,
        "safety_flags": list(record.safety_flags),
        "surface": record.surface,
        "token_sort_key": list(record.token_sort_key),
        "transparency_notice_id": record.transparency_notice_id,
        "user_tier": record.user_tier,
    }
