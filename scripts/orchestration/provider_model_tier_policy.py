"""Deterministic metadata-only provider/model-tier routing telemetry.

PR-O3 records inert labels for future orchestration cost decisions. It never
selects a runtime route, calls providers, reads pricing APIs, or opens
semantic-cache serving.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
import re
from types import MappingProxyType
from typing import TypeAlias

from core.evidence.fingerprints import fingerprint_payload

JsonScalar: TypeAlias = str | int | bool | None
JsonValue: TypeAlias = (
    JsonScalar | list["JsonValue"] | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
)

PROVIDER_MODEL_TIER_POLICY_VERSION = "provider-model-tier-routing-o3-v1"
PROVIDER_MODEL_TIER_AUTHORITY_BOUNDARY = "metadata_only_non_serving"
TELEMETRY_PHASE = "PR-O3"
SELECTED_ROUTE_NONE = "no_runtime_selection"

PROVIDER_GPT = "gpt"
PROVIDER_OLLAMA = "ollama"
PROVIDER_PERPLEXITY_SONAR = "perplexity_sonar"
PROVIDER_PERPLEXITY_AGENT = "perplexity_agent"
PROVIDER_UNKNOWN = "unknown_provider"
PROVIDER_LABELS = frozenset(
    {
        PROVIDER_GPT,
        PROVIDER_OLLAMA,
        PROVIDER_PERPLEXITY_SONAR,
        PROVIDER_PERPLEXITY_AGENT,
        PROVIDER_UNKNOWN,
    }
)

TIER_FRONTIER_REQUIRED = "frontier_required"
TIER_STANDARD_ADVISORY = "standard_advisory"
TIER_LOCAL_PREPROCESS_ADVISORY = "local_preprocess_advisory"
TIER_SEARCH_SYNTHESIS_ADVISORY = "search_synthesis_advisory"
TIER_UNKNOWN = "unknown_tier"
MODEL_TIER_LABELS = frozenset(
    {
        TIER_FRONTIER_REQUIRED,
        TIER_STANDARD_ADVISORY,
        TIER_LOCAL_PREPROCESS_ADVISORY,
        TIER_SEARCH_SYNTHESIS_ADVISORY,
        TIER_UNKNOWN,
    }
)

QUALITY_FLOOR_FRONTIER = "frontier_required"
QUALITY_FLOOR_ADVISORY_ONLY = "advisory_only"
QUALITY_FLOORS = frozenset({QUALITY_FLOOR_FRONTIER, QUALITY_FLOOR_ADVISORY_ONLY})

REASON_GATE_CLOSED = "gate_closed"
REASON_METADATA_ONLY = "metadata_only"
REASON_PROVIDER_LABELS_ONLY = "provider_labels_only"
REASON_NO_RUNTIME_SELECTION = "no_runtime_selection"
REASON_FRONTIER_REVIEW_PRESERVED = "frontier_review_preserved"
REASON_ESTIMATE_ONLY = "estimate_only"
REASON_NO_PROVIDER_CALL = "no_provider_call"
REASON_NO_CACHE_SERVING = "no_cache_serving"
REASON_NO_EMBEDDINGS = "no_embeddings"
REASON_NO_GRAPHRAG_RUNTIME = "no_graphrag_runtime"

DEFAULT_FRONTIER_ROLES = (
    "agent-coordinator",
    "architecture-specialist",
    "security-auditor",
    "qa-engineer-agent",
    "bug-hunter",
    "pulseplate-pr-review",
    "final-synthesis",
    "merge-readiness-review",
)
DEFAULT_PRE_SYNTHESIS_CANDIDATES = (
    "rag-systems-agent",
    "prompt-engineering-eval-agent",
)

MAX_STRING_LENGTH = 512
MAX_METADATA_BYTES = 4096
MAX_METADATA_DEPTH = 8
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DERIVED_ID_RE = re.compile(r"^(?:provider-tier|provider-policy|provider-routing):[0-9a-f]{24}$")
_TOKEN_ECONOMY_ID_RE = re.compile(r"^token-economy:[0-9a-f]{24}$")
_PATH_RE = re.compile(
    r"(?:(?:^|[\s=(;,]|:(?!//))(?:/|~[/\\]|[A-Za-z]:[\\/]|\\\\)|(?:^|[\s=(:;,])file://)"
)
_UNSAFE_METADATA_RE = re.compile(
    r"raw[_ -]?(?:query|prompt|response|answer|context)"
    r"|normalized[_ -]?query"
    r"|provider[_ -]?payload"
    r"|prompt[_ -]?text"
    r"|response[_ -]?text"
    r"|answer[_ -]?text"
    r"|secret"
    r"|credential"
    r"|authorization"
    r"|api[_ -]?key"
    r"|bearer"
    r"|cookie"
    r"|set-cookie"
    r"|session[_ -]?id"
    r"|x-api-key"
    r"|private[_ -]?key"
    r"|sk-[a-z0-9]"
    r"|gh[pousr]_[a-z0-9._-]+"
    r"|github_pat_[a-z0-9._-]+"
    r"|xox[baprs]-[a-z0-9._-]+"
    r"|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"
    r"|\+?\d[\d ()-]{7,}\d"
    r"|healthkit"
    r"|diagnosis"
    r"|symptom"
    r"|medical"
    r"|account[_ -]?(?:id|truth)"
    r"|billing[_ -]?truth"
    r"|entitlement[_ -]?truth"
    r"|coaching[_ -]?state"
    r"|user[_ -]?health"
    r"|provider[_ -]?price"
    r"|pricing[_ -]?truth"
    r"|live[_ -]?savings"
    r"|runtime[_ -]?route"
    r"|runtime[_ -]?selection"
    r"|selected[_ -]?route"
    r"|route[_ -]?decision"
    r"|provider[_ -]?selection"
    r"|model[_ -]?selection"
    r"|runtime[_ -]?model[_ -]?selection"
    r"|model[_ -]?downgrade"
    r"|downgraded[_ -]?model",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ProviderModelTierRecord:
    """Safe inert label record for a future provider/model tier candidate."""

    record_id: str
    provider_label: str
    model_tier_label: str
    allowed_advisory_roles: tuple[str, ...]
    blocked_runtime_roles: tuple[str, ...]
    quality_floor: str
    relative_cost_rank: int
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _validate_derived_id("record_id", self.record_id))
        if self.provider_label not in PROVIDER_LABELS:
            raise ValueError("provider_label contains unsupported value")
        if self.model_tier_label not in MODEL_TIER_LABELS:
            raise ValueError("model_tier_label contains unsupported value")
        object.__setattr__(
            self,
            "allowed_advisory_roles",
            _normalize_unique_role_tokens("allowed_advisory_roles", self.allowed_advisory_roles),
        )
        object.__setattr__(
            self,
            "blocked_runtime_roles",
            _normalize_required_unique_role_tokens(
                "blocked_runtime_roles",
                self.blocked_runtime_roles,
            ),
        )
        if self.quality_floor not in QUALITY_FLOORS:
            raise ValueError("quality_floor contains unsupported value")
        object.__setattr__(
            self,
            "relative_cost_rank",
            _validate_positive_int("relative_cost_rank", self.relative_cost_rank),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))
        if self.model_tier_label != TIER_FRONTIER_REQUIRED and (
            self.quality_floor != QUALITY_FLOOR_ADVISORY_ONLY
        ):
            raise ValueError("non-frontier model tiers must be advisory only")
        if self.model_tier_label == TIER_FRONTIER_REQUIRED and self.allowed_advisory_roles:
            raise ValueError("frontier_required records must not declare advisory-only roles")


@dataclass(frozen=True)
class ProviderModelRoutingPolicySnapshot:
    """Canonical policy snapshot from sorted metadata-only records."""

    policy_id: str
    policy_version: str
    authority_boundary: str
    records: tuple[ProviderModelTierRecord, ...]
    reason_codes: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _validate_derived_id("policy_id", self.policy_id))
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )
        if self.authority_boundary != PROVIDER_MODEL_TIER_AUTHORITY_BOUNDARY:
            raise ValueError("authority_boundary must remain metadata_only_non_serving")
        normalized_records = tuple(sorted(self.records, key=lambda record: record.record_id))
        if not normalized_records:
            raise ValueError("records must be non-empty")
        if len({record.record_id for record in normalized_records}) != len(normalized_records):
            raise ValueError("records must have unique record_id values")
        object.__setattr__(self, "records", normalized_records)
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_reason_codes(self.reason_codes),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class ProviderModelRoutingTelemetry:
    """Packet-level advisory routing telemetry with no runtime selection."""

    telemetry_id: str
    telemetry_phase: str
    policy_snapshot_id: str
    selected_route: str
    required_frontier_roles: tuple[str, ...]
    candidate_pre_synthesis_roles: tuple[str, ...]
    blocked_runtime_roles: tuple[str, ...]
    provider_labels: tuple[str, ...]
    model_tier_labels: tuple[str, ...]
    token_economy_estimate_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "telemetry_id",
            _validate_derived_id("telemetry_id", self.telemetry_id),
        )
        if self.telemetry_phase != TELEMETRY_PHASE:
            raise ValueError("telemetry_phase must be PR-O3")
        object.__setattr__(
            self,
            "policy_snapshot_id",
            _validate_derived_id("policy_snapshot_id", self.policy_snapshot_id),
        )
        if self.selected_route != SELECTED_ROUTE_NONE:
            raise ValueError("selected_route must be no_runtime_selection")
        object.__setattr__(
            self,
            "required_frontier_roles",
            _normalize_required_unique_role_tokens(
                "required_frontier_roles",
                self.required_frontier_roles,
            ),
        )
        object.__setattr__(
            self,
            "candidate_pre_synthesis_roles",
            _normalize_unique_role_tokens(
                "candidate_pre_synthesis_roles",
                self.candidate_pre_synthesis_roles,
            ),
        )
        object.__setattr__(
            self,
            "blocked_runtime_roles",
            _normalize_required_unique_role_tokens(
                "blocked_runtime_roles",
                self.blocked_runtime_roles,
            ),
        )
        object.__setattr__(
            self,
            "provider_labels",
            _normalize_provider_labels(self.provider_labels),
        )
        object.__setattr__(
            self,
            "model_tier_labels",
            _normalize_model_tier_labels(self.model_tier_labels),
        )
        object.__setattr__(
            self,
            "token_economy_estimate_ids",
            _normalize_token_economy_ids(self.token_economy_estimate_ids),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_reason_codes(self.reason_codes),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))
        if TIER_FRONTIER_REQUIRED not in self.model_tier_labels:
            raise ValueError("model_tier_labels must include frontier_required")
        if REASON_NO_RUNTIME_SELECTION not in self.reason_codes:
            raise ValueError("reason_codes must include no_runtime_selection")
        frontier_candidate_overlap = set(self.required_frontier_roles).intersection(
            self.candidate_pre_synthesis_roles
        )
        if frontier_candidate_overlap:
            raise ValueError("candidate_pre_synthesis_roles must not overlap frontier roles")


def build_provider_model_routing_policy_snapshot(
    *,
    records: Sequence[ProviderModelTierRecord] | None = None,
    policy_version: str = PROVIDER_MODEL_TIER_POLICY_VERSION,
    metadata: Mapping[str, JsonValue] | None = None,
) -> ProviderModelRoutingPolicySnapshot:
    """Build a canonical metadata-only policy snapshot."""

    normalized_records = tuple(records or _default_policy_records())
    record_mappings: list[dict[str, JsonValue]] = [
        dict(to_stable_mapping(record)) for record in normalized_records
    ]
    sorted_record_mapping_dicts = sorted(record_mappings, key=_record_mapping_sort_key)
    sorted_record_mappings: list[JsonValue] = list(sorted_record_mapping_dicts)
    payload: JsonValue = {
        "authority_boundary": PROVIDER_MODEL_TIER_AUTHORITY_BOUNDARY,
        "policy_version": _validate_token("policy_version", policy_version),
        "records": sorted_record_mappings,
    }
    return ProviderModelRoutingPolicySnapshot(
        policy_id=_derived_id("provider-policy", payload),
        policy_version=policy_version,
        authority_boundary=PROVIDER_MODEL_TIER_AUTHORITY_BOUNDARY,
        records=normalized_records,
        reason_codes=(
            REASON_GATE_CLOSED,
            REASON_METADATA_ONLY,
            REASON_PROVIDER_LABELS_ONLY,
            REASON_FRONTIER_REVIEW_PRESERVED,
        ),
        metadata=metadata
        or {
            "gate_status": "closed",
            "runtime_allowed": False,
            "provider_calls_allowed": False,
        },
    )


def build_provider_model_routing_telemetry(
    *,
    requested_agents: Iterable[str],
    primary_agent: str,
    reviewer: str,
    secondary_agents: Iterable[str] = (),
    token_economy_estimate_ids: Iterable[str] = (),
    policy_snapshot: ProviderModelRoutingPolicySnapshot | None = None,
    metadata: Mapping[str, JsonValue] | None = None,
) -> ProviderModelRoutingTelemetry:
    """Build packet-level PR-O3 routing telemetry without selecting a route."""

    snapshot = policy_snapshot or build_provider_model_routing_policy_snapshot()
    requested = _normalize_unique_role_tokens("requested_agents", requested_agents)
    frontier_roles = _normalize_required_unique_role_tokens(
        "required_frontier_roles",
        (
            *DEFAULT_FRONTIER_ROLES,
            primary_agent,
            reviewer,
            *secondary_agents,
        ),
    )
    advisory_role_candidates = tuple(
        role for record in snapshot.records for role in record.allowed_advisory_roles
    )
    candidates = tuple(
        role
        for role in _normalize_unique_role_tokens(
            "candidate_pre_synthesis_roles",
            (*DEFAULT_PRE_SYNTHESIS_CANDIDATES, *advisory_role_candidates),
        )
        if role not in frontier_roles
    )
    blocked_runtime_roles = tuple(sorted(set(frontier_roles).union(requested)))
    provider_labels = tuple(sorted({record.provider_label for record in snapshot.records}))
    tier_labels = tuple(sorted({record.model_tier_label for record in snapshot.records}))
    estimate_ids = _normalize_token_economy_ids(token_economy_estimate_ids)
    payload: JsonValue = {
        "candidate_pre_synthesis_roles": candidates,
        "model_tier_labels": tier_labels,
        "policy_snapshot_id": snapshot.policy_id,
        "provider_labels": provider_labels,
        "required_frontier_roles": frontier_roles,
        "selected_route": SELECTED_ROUTE_NONE,
        "token_economy_estimate_ids": estimate_ids,
    }
    return ProviderModelRoutingTelemetry(
        telemetry_id=_derived_id("provider-routing", payload),
        telemetry_phase=TELEMETRY_PHASE,
        policy_snapshot_id=snapshot.policy_id,
        selected_route=SELECTED_ROUTE_NONE,
        required_frontier_roles=frontier_roles,
        candidate_pre_synthesis_roles=candidates,
        blocked_runtime_roles=blocked_runtime_roles,
        provider_labels=provider_labels,
        model_tier_labels=tier_labels,
        token_economy_estimate_ids=estimate_ids,
        reason_codes=(
            REASON_ESTIMATE_ONLY,
            REASON_FRONTIER_REVIEW_PRESERVED,
            REASON_GATE_CLOSED,
            REASON_METADATA_ONLY,
            REASON_NO_CACHE_SERVING,
            REASON_NO_EMBEDDINGS,
            REASON_NO_GRAPHRAG_RUNTIME,
            REASON_NO_PROVIDER_CALL,
            REASON_NO_RUNTIME_SELECTION,
            REASON_PROVIDER_LABELS_ONLY,
        ),
        metadata=metadata
        or {
            "gate_status": "closed",
            "runtime_allowed": False,
            "provider_calls_allowed": False,
            "frontier_review_preserved": True,
        },
    )


def to_stable_mapping(value: object) -> Mapping[str, JsonValue]:
    """Return a deterministic JSON-ready mapping for PR-O3 records."""

    if isinstance(value, ProviderModelTierRecord):
        return _freeze_mapping(
            {
                "allowed_advisory_roles": list(value.allowed_advisory_roles),
                "blocked_runtime_roles": list(value.blocked_runtime_roles),
                "metadata": _json_safe_copy(value.metadata),
                "model_tier_label": value.model_tier_label,
                "provider_label": value.provider_label,
                "quality_floor": value.quality_floor,
                "record_id": value.record_id,
                "relative_cost_rank": value.relative_cost_rank,
            }
        )
    if isinstance(value, ProviderModelRoutingPolicySnapshot):
        return _freeze_mapping(
            {
                "authority_boundary": value.authority_boundary,
                "metadata": _json_safe_copy(value.metadata),
                "policy_id": value.policy_id,
                "policy_version": value.policy_version,
                "reason_codes": list(value.reason_codes),
                "records": [dict(to_stable_mapping(record)) for record in value.records],
            }
        )
    if isinstance(value, ProviderModelRoutingTelemetry):
        return _freeze_mapping(
            {
                "blocked_runtime_roles": list(value.blocked_runtime_roles),
                "candidate_pre_synthesis_roles": list(value.candidate_pre_synthesis_roles),
                "metadata": _json_safe_copy(value.metadata),
                "model_tier_labels": list(value.model_tier_labels),
                "policy_snapshot_id": value.policy_snapshot_id,
                "provider_labels": list(value.provider_labels),
                "reason_codes": list(value.reason_codes),
                "required_frontier_roles": list(value.required_frontier_roles),
                "selected_route": value.selected_route,
                "telemetry_id": value.telemetry_id,
                "telemetry_phase": value.telemetry_phase,
                "token_economy_estimate_ids": list(value.token_economy_estimate_ids),
            }
        )
    raise ValueError(f"unsupported stable mapping value: {type(value).__name__}")


def _default_policy_records() -> tuple[ProviderModelTierRecord, ...]:
    return (
        _build_record(
            provider_label=PROVIDER_GPT,
            model_tier_label=TIER_FRONTIER_REQUIRED,
            allowed_advisory_roles=(),
            blocked_runtime_roles=DEFAULT_FRONTIER_ROLES,
            quality_floor=QUALITY_FLOOR_FRONTIER,
            relative_cost_rank=4,
        ),
        _build_record(
            provider_label=PROVIDER_OLLAMA,
            model_tier_label=TIER_LOCAL_PREPROCESS_ADVISORY,
            allowed_advisory_roles=("prompt-engineering-eval-agent",),
            blocked_runtime_roles=DEFAULT_FRONTIER_ROLES,
            quality_floor=QUALITY_FLOOR_ADVISORY_ONLY,
            relative_cost_rank=1,
        ),
        _build_record(
            provider_label=PROVIDER_PERPLEXITY_SONAR,
            model_tier_label=TIER_SEARCH_SYNTHESIS_ADVISORY,
            allowed_advisory_roles=("rag-systems-agent",),
            blocked_runtime_roles=DEFAULT_FRONTIER_ROLES,
            quality_floor=QUALITY_FLOOR_ADVISORY_ONLY,
            relative_cost_rank=2,
        ),
        _build_record(
            provider_label=PROVIDER_PERPLEXITY_AGENT,
            model_tier_label=TIER_STANDARD_ADVISORY,
            allowed_advisory_roles=("rag-systems-agent", "prompt-engineering-eval-agent"),
            blocked_runtime_roles=DEFAULT_FRONTIER_ROLES,
            quality_floor=QUALITY_FLOOR_ADVISORY_ONLY,
            relative_cost_rank=3,
        ),
        _build_record(
            provider_label=PROVIDER_UNKNOWN,
            model_tier_label=TIER_UNKNOWN,
            allowed_advisory_roles=(),
            blocked_runtime_roles=DEFAULT_FRONTIER_ROLES,
            quality_floor=QUALITY_FLOOR_ADVISORY_ONLY,
            relative_cost_rank=99,
        ),
    )


def _record_mapping_sort_key(item: Mapping[str, JsonValue]) -> str:
    return str(item["record_id"])


def _build_record(
    *,
    provider_label: str,
    model_tier_label: str,
    allowed_advisory_roles: Iterable[str],
    blocked_runtime_roles: Iterable[str],
    quality_floor: str,
    relative_cost_rank: int,
) -> ProviderModelTierRecord:
    allowed = _normalize_unique_role_tokens("allowed_advisory_roles", allowed_advisory_roles)
    blocked = _normalize_required_unique_role_tokens("blocked_runtime_roles", blocked_runtime_roles)
    payload: JsonValue = {
        "allowed_advisory_roles": allowed,
        "blocked_runtime_roles": blocked,
        "model_tier_label": model_tier_label,
        "provider_label": provider_label,
        "quality_floor": quality_floor,
        "relative_cost_rank": relative_cost_rank,
    }
    return ProviderModelTierRecord(
        record_id=_derived_id("provider-tier", payload),
        provider_label=provider_label,
        model_tier_label=model_tier_label,
        allowed_advisory_roles=allowed,
        blocked_runtime_roles=blocked,
        quality_floor=quality_floor,
        relative_cost_rank=relative_cost_rank,
        metadata={"runtime_allowed": False, "provider_calls_allowed": False},
    )


def _derived_id(prefix: str, payload: JsonValue) -> str:
    fingerprint = fingerprint_payload(payload)
    return f"{prefix}:{fingerprint.removeprefix('sha256:')[:24]}"


def _validate_derived_id(name: str, value: str) -> str:
    normalized = value.strip()
    if not _DERIVED_ID_RE.match(normalized):
        raise ValueError(f"{name} must be a provider/model-tier derived id")
    return normalized


def _validate_token_economy_id(name: str, value: str) -> str:
    normalized = value.strip()
    if not _TOKEN_ECONOMY_ID_RE.match(normalized):
        raise ValueError(f"{name} must be a TokenEconomyEstimate id")
    return normalized


def _validate_token(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if len(normalized) > MAX_STRING_LENGTH:
        raise ValueError(f"{name} exceeds maximum length")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    if _UNSAFE_METADATA_RE.search(normalized) or _PATH_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe metadata")
    return normalized


def _validate_role_token(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if len(normalized) > MAX_STRING_LENGTH:
        raise ValueError(f"{name} exceeds maximum length")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    if _PATH_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe metadata")
    return normalized


def _normalize_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({_validate_token(name, value) for value in values}))


def _normalize_required_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = _normalize_unique_tokens(name, values)
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _normalize_unique_role_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({_validate_role_token(name, value) for value in values}))


def _normalize_required_unique_role_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = _normalize_unique_role_tokens(name, values)
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _normalize_required_reason_codes(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({_validate_reason_code(value) for value in values}))
    if not normalized:
        raise ValueError("reason_codes must be non-empty")
    return normalized


def _validate_reason_code(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("reason_codes must be non-empty")
    if len(normalized) > MAX_STRING_LENGTH:
        raise ValueError("reason_codes exceeds maximum length")
    if any(char.isspace() for char in normalized):
        raise ValueError("reason_codes must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError("reason_codes contains unsupported characters")
    if _PATH_RE.search(normalized):
        raise ValueError("reason_codes contains unsafe metadata")
    return normalized


def _normalize_provider_labels(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({value.strip() for value in values}))
    if not normalized:
        raise ValueError("provider_labels must be non-empty")
    unsupported = [value for value in normalized if value not in PROVIDER_LABELS]
    if unsupported:
        raise ValueError("provider_labels contains unsupported value")
    return normalized


def _normalize_model_tier_labels(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({value.strip() for value in values}))
    if not normalized:
        raise ValueError("model_tier_labels must be non-empty")
    unsupported = [value for value in normalized if value not in MODEL_TIER_LABELS]
    if unsupported:
        raise ValueError("model_tier_labels contains unsupported value")
    return normalized


def _normalize_token_economy_ids(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {_validate_token_economy_id("token_economy_estimate_ids", value) for value in values}
        )
    )


def _validate_positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def _freeze_metadata(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    copied = _json_safe_copy(value)
    if not isinstance(copied, dict):
        raise ValueError("metadata must be a mapping")
    _validate_metadata_is_safe(copied)
    _validate_metadata_budget(copied)
    frozen = _deep_freeze_json(copied)
    if not isinstance(frozen, Mapping):
        raise ValueError("metadata must be a mapping")
    return frozen


def _freeze_mapping(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    return MappingProxyType(dict(sorted(value.items())))


def _deep_freeze_json(value: JsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _deep_freeze_json(item) for key, item in sorted(value.items())}
        )
    if isinstance(value, list | tuple):
        return tuple(_deep_freeze_json(item) for item in value)
    return value


def _json_safe_copy(value: JsonValue | Mapping[str, JsonValue]) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_copy(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_json_safe_copy(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_copy(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    raise ValueError(f"metadata contains unsupported value: {type(value).__name__}")


def _validate_metadata_is_safe(value: JsonValue, *, path: str = "metadata", depth: int = 0) -> None:
    if depth > MAX_METADATA_DEPTH:
        raise ValueError("metadata exceeds maximum depth")
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_safe_metadata_string(f"{path}.key", key)
            _validate_metadata_is_safe(item, path=f"{path}.{key}", depth=depth + 1)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_metadata_is_safe(item, path=f"{path}[{index}]", depth=depth + 1)
    elif isinstance(value, str):
        _validate_safe_metadata_string(path, value)


def _validate_metadata_budget(value: Mapping[str, JsonValue]) -> None:
    serialized = json.dumps(_json_safe_copy(value), sort_keys=True, separators=(",", ":"))
    if len(serialized) > MAX_METADATA_BYTES:
        raise ValueError("metadata exceeds maximum size")


def _validate_safe_metadata_string(name: str, value: str) -> None:
    if len(value) > MAX_STRING_LENGTH:
        raise ValueError(f"{name} exceeds maximum length")
    if _DERIVED_ID_RE.match(value) or _TOKEN_ECONOMY_ID_RE.match(value):
        return
    if _UNSAFE_METADATA_RE.search(value) or _PATH_RE.search(value):
        raise ValueError(f"{name} contains unsafe metadata")
