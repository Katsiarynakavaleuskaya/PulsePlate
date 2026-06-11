"""Deterministic metadata-only embedding/retrieval admission telemetry.

PR-O4 records safe labels, fingerprints, and closed-gate reason codes for
future embedding/retrieval admission review. It never generates embeddings,
executes retrieval, calls providers, reads or writes caches, or serves payloads.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
import re
from types import MappingProxyType
from typing import TypeAlias

from core.evidence.fingerprints import fingerprint_payload
from core.evidence.policies import validate_fingerprint

JsonScalar: TypeAlias = str | int | bool | None
JsonValue: TypeAlias = (
    JsonScalar | list["JsonValue"] | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
)

EMBEDDING_RETRIEVAL_ADMISSION_POLICY_VERSION = "embedding-retrieval-admission-o4-v1"
EMBEDDING_RETRIEVAL_AUTHORITY_BOUNDARY = "metadata_only_non_serving"
TELEMETRY_PHASE = "PR-O4"
GATE_STATUS_CLOSED = "closed"
ADMISSION_STATE_DEFERRED = "deferred_gate_closed"
SELECTED_BACKEND_NONE = "none"
SELECTED_RUNTIME_NONE = "none"

REF_CHANGED_FILE = "changed_file"
REF_CONTRACT = "contract"
REF_TEST = "test"
REF_AGENT_RULE = "agent_rule"
REF_REVIEW_ARTIFACT = "review_artifact"
REF_ROADMAP = "roadmap"
REF_ORCHESTRATION_PACKET = "orchestration_packet"
EVIDENCE_REF_TYPES = frozenset(
    {
        REF_CHANGED_FILE,
        REF_CONTRACT,
        REF_TEST,
        REF_AGENT_RULE,
        REF_REVIEW_ARTIFACT,
        REF_ROADMAP,
        REF_ORCHESTRATION_PACKET,
    }
)

CANDIDATE_EMBEDDING = "embedding_candidate"
CANDIDATE_RETRIEVAL = "retrieval_candidate"
CANDIDATE_HYBRID = "hybrid_candidate"
CANDIDATE_TYPES = frozenset({CANDIDATE_EMBEDDING, CANDIDATE_RETRIEVAL, CANDIDATE_HYBRID})

SURFACE_ORCHESTRATION_CONTEXT = "orchestration_context"
SURFACE_MERGE_READINESS_CONTEXT = "merge_readiness_context"
SURFACE_PROMPT_MODULE_REGISTRY = "prompt_module_registry"
SURFACE_EVIDENCE_GRAPH_REFERENCE = "evidence_graph_reference"
SURFACE_LABELS = frozenset(
    {
        SURFACE_ORCHESTRATION_CONTEXT,
        SURFACE_MERGE_READINESS_CONTEXT,
        SURFACE_PROMPT_MODULE_REGISTRY,
        SURFACE_EVIDENCE_GRAPH_REFERENCE,
    }
)

REASON_GATE_CLOSED = "gate_closed"
REASON_METADATA_ONLY = "metadata_only"
REASON_ADMISSION_DEFERRED = "admission_deferred"
REASON_NO_EMBEDDINGS = "no_embeddings"
REASON_NO_VECTOR_SEARCH = "no_vector_search"
REASON_NO_RUNTIME_RETRIEVAL = "no_runtime_retrieval"
REASON_NO_PROVIDER_CALL = "no_provider_call"
REASON_NO_CACHE_SERVING = "no_cache_serving"
REASON_FUTURE_GATE_REQUIRED = "future_gate_required"
REASON_NO_SEMANTIC_SIMILARITY = "no_semantic_similarity"
REASON_NO_CACHE_READ = "no_cache_read"
REASON_NO_CACHE_WRITE = "no_cache_write"
REASON_NO_PROVIDER_WIRING = "no_provider_wiring"
REASON_ESTIMATE_ONLY = "estimate_only"

REQUIRED_REASON_CODES = (
    REASON_GATE_CLOSED,
    REASON_METADATA_ONLY,
    REASON_ADMISSION_DEFERRED,
    REASON_NO_EMBEDDINGS,
    REASON_NO_VECTOR_SEARCH,
    REASON_NO_RUNTIME_RETRIEVAL,
    REASON_NO_PROVIDER_CALL,
    REASON_NO_CACHE_SERVING,
    REASON_FUTURE_GATE_REQUIRED,
)
DEFAULT_REASON_CODES = tuple(
    sorted(
        {
            *REQUIRED_REASON_CODES,
            REASON_ESTIMATE_ONLY,
            REASON_NO_CACHE_READ,
            REASON_NO_CACHE_WRITE,
            REASON_NO_PROVIDER_WIRING,
            REASON_NO_SEMANTIC_SIMILARITY,
        }
    )
)

DEFAULT_FOLLOWUPS = (
    "semantic_cache_gate_open_pr",
    "embedding_runtime_review",
    "retrieval_runtime_review",
    "false_hit_harness_review",
)

MAX_STRING_LENGTH = 512
MAX_METADATA_BYTES = 4096
MAX_METADATA_DEPTH = 8
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_REPO_PATH_RE = re.compile(r"^[A-Za-z0-9.][A-Za-z0-9_./-]*$")
_DERIVED_ID_RE = re.compile(
    r"^(?:embedding-retrieval-ref|embedding-retrieval-candidate|"
    r"embedding-retrieval-policy|embedding-retrieval-admission):[0-9a-f]{24}$"
)
_PATH_RE = re.compile(
    r"(?:(?:^|[\s=(;,]|:(?!//))(?:/|~[/\\]|[A-Za-z]:[\\/]|\\\\)|(?:^|[\s=(:;,])file://)"
)
_UNSAFE_METADATA_RE = re.compile(
    r"raw[_ -]?(?:query|prompt|response|answer|context)"
    r"|(?:^|[_ -])(?:prompt|query|similarity[_ -]?scores?)(?:$|[_ -])"
    r"|normalized[_ -]?query"
    r"|provider[_ -]?(?:payload|request|response|client|price|selection|routing)"
    r"|prompt[_ -]?text"
    r"|query[_ -]?text"
    r"|context[_ -]?snippet"
    r"|response[_ -]?text"
    r"|answer[_ -]?text"
    r"|embedding[_ -]?(?:vector|value|payload|model|generation)"
    r"|vector[_ -]?(?:payload|index|search)"
    r"|semantic[_ -]?similarity"
    r"|retrieval[_ -]?(?:runtime|query|route|payload|execution)"
    r"|runtime[_ -]?(?:admission|retrieval|handoff|route|selection)"
    r"|selected[_ -]?(?:backend|runtime|retriever|route)"
    r"|cache[_ -]?(?:hit|read|write|serving|payload)"
    r"|provider[_ -]?calls?[_ -]?avoided"
    r"|cost[_ -]?saved"
    r"|live[_ -]?savings"
    r"|latency[_ -]?saved"
    r"|quota[_ -]?(?:delta|improvement|consumption)"
    r"|quality[_ -]?(?:score|downgrade)"
    r"|model[_ -]?downgrade"
    r"|downgraded[_ -]?model"
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
    r"|user[_ -]?health"
    r"|account[_ -]?(?:id|truth)"
    r"|billing[_ -]?truth"
    r"|entitlement[_ -]?truth",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EmbeddingRetrievalEvidenceRef:
    """Safe evidence reference for future embedding/retrieval admission review."""

    ref_id: str
    ref_type: str
    source_path: str
    source_fingerprint: str
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref_id", _validate_derived_id("ref_id", self.ref_id))
        if self.ref_type not in EVIDENCE_REF_TYPES:
            raise ValueError("ref_type contains unsupported value")
        object.__setattr__(
            self,
            "source_path",
            _validate_repo_relative_path("source_path", self.source_path),
        )
        object.__setattr__(
            self,
            "source_fingerprint",
            validate_fingerprint(self.source_fingerprint),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class EmbeddingRetrievalAdmissionCandidate:
    """Closed-gate candidate label for future admission evaluation."""

    candidate_id: str
    candidate_type: str
    surface_label: str
    evidence_ref_ids: tuple[str, ...]
    admission_state: str
    reason_codes: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _validate_derived_id("candidate_id", self.candidate_id),
        )
        if self.candidate_type not in CANDIDATE_TYPES:
            raise ValueError("candidate_type contains unsupported value")
        if self.surface_label not in SURFACE_LABELS:
            raise ValueError("surface_label contains unsupported value")
        object.__setattr__(
            self,
            "evidence_ref_ids",
            _normalize_required_derived_ids("evidence_ref_ids", self.evidence_ref_ids),
        )
        if self.admission_state != ADMISSION_STATE_DEFERRED:
            raise ValueError("admission_state must remain deferred_gate_closed")
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_reason_codes(self.reason_codes),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class EmbeddingRetrievalAdmissionPolicySnapshot:
    """Canonical closed-gate policy snapshot for PR-O4 telemetry."""

    policy_id: str
    policy_version: str
    authority_boundary: str
    gate_status: str
    evidence_ref_types: tuple[str, ...]
    candidate_types: tuple[str, ...]
    reason_codes: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _validate_derived_id("policy_id", self.policy_id))
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )
        if self.authority_boundary != EMBEDDING_RETRIEVAL_AUTHORITY_BOUNDARY:
            raise ValueError("authority_boundary must remain metadata_only_non_serving")
        if self.gate_status != GATE_STATUS_CLOSED:
            raise ValueError("gate_status must remain closed")
        object.__setattr__(
            self,
            "evidence_ref_types",
            _normalize_enum_values(
                "evidence_ref_types", self.evidence_ref_types, EVIDENCE_REF_TYPES
            ),
        )
        object.__setattr__(
            self,
            "candidate_types",
            _normalize_enum_values("candidate_types", self.candidate_types, CANDIDATE_TYPES),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_reason_codes(self.reason_codes),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class EmbeddingRetrievalAdmissionTelemetry:
    """Packet-level PR-O4 telemetry with no admission or runtime selection."""

    telemetry_id: str
    telemetry_phase: str
    policy_snapshot_id: str
    evidence_refs: tuple[EmbeddingRetrievalEvidenceRef, ...]
    candidates: tuple[EmbeddingRetrievalAdmissionCandidate, ...]
    admission_allowed: bool
    embedding_allowed: bool
    retrieval_runtime_allowed: bool
    semantic_similarity_allowed: bool
    vector_search_allowed: bool
    provider_calls_allowed: bool
    cache_read_allowed: bool
    cache_write_allowed: bool
    serving_allowed: bool
    selected_embedding_backend: str
    selected_retrieval_runtime: str
    required_followups: tuple[str, ...]
    reason_codes: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "telemetry_id",
            _validate_derived_id("telemetry_id", self.telemetry_id),
        )
        if self.telemetry_phase != TELEMETRY_PHASE:
            raise ValueError("telemetry_phase must be PR-O4")
        object.__setattr__(
            self,
            "policy_snapshot_id",
            _validate_derived_id("policy_snapshot_id", self.policy_snapshot_id),
        )
        normalized_refs = tuple(sorted(self.evidence_refs, key=lambda ref: ref.ref_id))
        if not normalized_refs:
            raise ValueError("evidence_refs must be non-empty")
        if len({ref.ref_id for ref in normalized_refs}) != len(normalized_refs):
            raise ValueError("evidence_refs must have unique ref_id values")
        object.__setattr__(self, "evidence_refs", normalized_refs)
        normalized_candidates = tuple(
            sorted(self.candidates, key=lambda candidate: candidate.candidate_id)
        )
        if not normalized_candidates:
            raise ValueError("candidates must be non-empty")
        if len({candidate.candidate_id for candidate in normalized_candidates}) != len(
            normalized_candidates
        ):
            raise ValueError("candidates must have unique candidate_id values")
        ref_ids = {ref.ref_id for ref in normalized_refs}
        unknown_refs = sorted(
            set().union(*(candidate.evidence_ref_ids for candidate in normalized_candidates))
            - ref_ids
        )
        if unknown_refs:
            raise ValueError("candidates reference unknown evidence refs")
        object.__setattr__(self, "candidates", normalized_candidates)
        for field in (
            "admission_allowed",
            "embedding_allowed",
            "retrieval_runtime_allowed",
            "semantic_similarity_allowed",
            "vector_search_allowed",
            "provider_calls_allowed",
            "cache_read_allowed",
            "cache_write_allowed",
            "serving_allowed",
        ):
            _validate_false(field, getattr(self, field))
        if self.selected_embedding_backend != SELECTED_BACKEND_NONE:
            raise ValueError("selected_embedding_backend must remain none")
        if self.selected_retrieval_runtime != SELECTED_RUNTIME_NONE:
            raise ValueError("selected_retrieval_runtime must remain none")
        object.__setattr__(
            self,
            "required_followups",
            _normalize_required_followups(self.required_followups),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_reason_codes(self.reason_codes),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


def build_embedding_retrieval_admission_policy_snapshot(
    *,
    policy_version: str = EMBEDDING_RETRIEVAL_ADMISSION_POLICY_VERSION,
    metadata: Mapping[str, JsonValue] | None = None,
) -> EmbeddingRetrievalAdmissionPolicySnapshot:
    """Build the canonical gate-closed PR-O4 policy snapshot."""

    evidence_ref_types = tuple(sorted(EVIDENCE_REF_TYPES))
    candidate_types = tuple(sorted(CANDIDATE_TYPES))
    payload: JsonValue = {
        "authority_boundary": EMBEDDING_RETRIEVAL_AUTHORITY_BOUNDARY,
        "candidate_types": candidate_types,
        "evidence_ref_types": evidence_ref_types,
        "gate_status": GATE_STATUS_CLOSED,
        "policy_version": _validate_token("policy_version", policy_version),
        "reason_codes": DEFAULT_REASON_CODES,
    }
    return EmbeddingRetrievalAdmissionPolicySnapshot(
        policy_id=_derived_id("embedding-retrieval-policy", payload),
        policy_version=policy_version,
        authority_boundary=EMBEDDING_RETRIEVAL_AUTHORITY_BOUNDARY,
        gate_status=GATE_STATUS_CLOSED,
        evidence_ref_types=evidence_ref_types,
        candidate_types=candidate_types,
        reason_codes=DEFAULT_REASON_CODES,
        metadata=metadata
        or {
            "metadata_contract": "non_serving",
            "policy_generation": 1,
        },
    )


def build_embedding_retrieval_admission_telemetry(
    *,
    candidate_paths: Iterable[str],
    required_context: Iterable[str],
    pr_phase: str,
    domain: str,
    cluster: str,
    policy_snapshot: EmbeddingRetrievalAdmissionPolicySnapshot | None = None,
    metadata: Mapping[str, JsonValue] | None = None,
) -> EmbeddingRetrievalAdmissionTelemetry:
    """Build PR-O4 packet telemetry without admitting runtime behavior."""

    snapshot = policy_snapshot or build_embedding_retrieval_admission_policy_snapshot()
    evidence_refs = _build_evidence_refs(
        candidate_paths=candidate_paths,
        required_context=required_context,
    )
    evidence_ref_ids = tuple(ref.ref_id for ref in evidence_refs)
    candidates = _build_candidates(evidence_ref_ids)
    payload: JsonValue = {
        "candidate_ids": tuple(candidate.candidate_id for candidate in candidates),
        "evidence_ref_ids": evidence_ref_ids,
        "policy_snapshot_id": snapshot.policy_id,
        "selected_embedding_backend": SELECTED_BACKEND_NONE,
        "selected_retrieval_runtime": SELECTED_RUNTIME_NONE,
    }
    return EmbeddingRetrievalAdmissionTelemetry(
        telemetry_id=_derived_id("embedding-retrieval-admission", payload),
        telemetry_phase=TELEMETRY_PHASE,
        policy_snapshot_id=snapshot.policy_id,
        evidence_refs=evidence_refs,
        candidates=candidates,
        admission_allowed=False,
        embedding_allowed=False,
        retrieval_runtime_allowed=False,
        semantic_similarity_allowed=False,
        vector_search_allowed=False,
        provider_calls_allowed=False,
        cache_read_allowed=False,
        cache_write_allowed=False,
        serving_allowed=False,
        selected_embedding_backend=SELECTED_BACKEND_NONE,
        selected_retrieval_runtime=SELECTED_RUNTIME_NONE,
        required_followups=DEFAULT_FOLLOWUPS,
        reason_codes=DEFAULT_REASON_CODES,
        metadata=metadata
        or {
            "cluster": _validate_token("cluster", cluster),
            "domain": _validate_token("domain", domain),
            "evidence_ref_count": len(evidence_refs),
            "candidate_count": len(candidates),
            "pr_phase": _validate_token("pr_phase", pr_phase),
        },
    )


def embedding_retrieval_admission_to_stable_mapping(
    value: object,
) -> Mapping[str, JsonValue]:
    """Return a deterministic JSON-ready mapping for PR-O4 records."""

    if isinstance(value, EmbeddingRetrievalEvidenceRef):
        return _freeze_mapping(
            {
                "metadata": _json_safe_copy(value.metadata),
                "ref_id": value.ref_id,
                "ref_type": value.ref_type,
                "source_fingerprint": value.source_fingerprint,
                "source_path": value.source_path,
            }
        )
    if isinstance(value, EmbeddingRetrievalAdmissionCandidate):
        return _freeze_mapping(
            {
                "admission_state": value.admission_state,
                "candidate_id": value.candidate_id,
                "candidate_type": value.candidate_type,
                "evidence_ref_ids": list(value.evidence_ref_ids),
                "metadata": _json_safe_copy(value.metadata),
                "reason_codes": list(value.reason_codes),
                "surface_label": value.surface_label,
            }
        )
    if isinstance(value, EmbeddingRetrievalAdmissionPolicySnapshot):
        return _freeze_mapping(
            {
                "authority_boundary": value.authority_boundary,
                "candidate_types": list(value.candidate_types),
                "evidence_ref_types": list(value.evidence_ref_types),
                "gate_status": value.gate_status,
                "metadata": _json_safe_copy(value.metadata),
                "policy_id": value.policy_id,
                "policy_version": value.policy_version,
                "reason_codes": list(value.reason_codes),
            }
        )
    if isinstance(value, EmbeddingRetrievalAdmissionTelemetry):
        return _freeze_mapping(
            {
                "admission_allowed": value.admission_allowed,
                "cache_read_allowed": value.cache_read_allowed,
                "cache_write_allowed": value.cache_write_allowed,
                "candidates": [
                    dict(embedding_retrieval_admission_to_stable_mapping(candidate))
                    for candidate in value.candidates
                ],
                "embedding_allowed": value.embedding_allowed,
                "evidence_refs": [
                    dict(embedding_retrieval_admission_to_stable_mapping(ref))
                    for ref in value.evidence_refs
                ],
                "metadata": _json_safe_copy(value.metadata),
                "policy_snapshot_id": value.policy_snapshot_id,
                "provider_calls_allowed": value.provider_calls_allowed,
                "reason_codes": list(value.reason_codes),
                "required_followups": list(value.required_followups),
                "retrieval_runtime_allowed": value.retrieval_runtime_allowed,
                "selected_embedding_backend": value.selected_embedding_backend,
                "selected_retrieval_runtime": value.selected_retrieval_runtime,
                "semantic_similarity_allowed": value.semantic_similarity_allowed,
                "serving_allowed": value.serving_allowed,
                "telemetry_id": value.telemetry_id,
                "telemetry_phase": value.telemetry_phase,
                "vector_search_allowed": value.vector_search_allowed,
            }
        )
    raise ValueError(f"unsupported stable mapping value: {type(value).__name__}")


def _build_evidence_refs(
    *,
    candidate_paths: Iterable[str],
    required_context: Iterable[str],
) -> tuple[EmbeddingRetrievalEvidenceRef, ...]:
    normalized_paths = sorted(
        {
            _validate_repo_relative_path("candidate_paths", path)
            for path in candidate_paths
            if path.strip()
        }
        | {
            _validate_repo_relative_path("required_context", path)
            for path in required_context
            if path.strip()
        }
    )
    if not normalized_paths:
        normalized_paths = ["scripts/orchestration/task_bootstrap.py"]

    refs: list[EmbeddingRetrievalEvidenceRef] = []
    for index, path in enumerate(normalized_paths, start=1):
        ref_type = _classify_source_path(path)
        source_fingerprint = fingerprint_payload({"path": path, "ref_type": ref_type})
        payload: JsonValue = {
            "ref_type": ref_type,
            "source_fingerprint": source_fingerprint,
            "source_path": path,
        }
        refs.append(
            EmbeddingRetrievalEvidenceRef(
                ref_id=_derived_id("embedding-retrieval-ref", payload),
                ref_type=ref_type,
                source_path=path,
                source_fingerprint=source_fingerprint,
                metadata={
                    "source_index": index,
                    "source_path_chars": len(path),
                },
            )
        )
    return tuple(sorted(refs, key=lambda ref: ref.ref_id))


def _build_candidates(
    evidence_ref_ids: Sequence[str],
) -> tuple[EmbeddingRetrievalAdmissionCandidate, ...]:
    normalized_ref_ids = _normalize_required_derived_ids("evidence_ref_ids", evidence_ref_ids)
    specs = (
        (CANDIDATE_EMBEDDING, SURFACE_ORCHESTRATION_CONTEXT),
        (CANDIDATE_RETRIEVAL, SURFACE_MERGE_READINESS_CONTEXT),
        (CANDIDATE_HYBRID, SURFACE_EVIDENCE_GRAPH_REFERENCE),
    )
    candidates: list[EmbeddingRetrievalAdmissionCandidate] = []
    for index, (candidate_type, surface_label) in enumerate(specs, start=1):
        payload: JsonValue = {
            "candidate_type": candidate_type,
            "evidence_ref_ids": normalized_ref_ids,
            "surface_label": surface_label,
            "admission_state": ADMISSION_STATE_DEFERRED,
        }
        candidates.append(
            EmbeddingRetrievalAdmissionCandidate(
                candidate_id=_derived_id("embedding-retrieval-candidate", payload),
                candidate_type=candidate_type,
                surface_label=surface_label,
                evidence_ref_ids=normalized_ref_ids,
                admission_state=ADMISSION_STATE_DEFERRED,
                reason_codes=DEFAULT_REASON_CODES,
                metadata={
                    "candidate_index": index,
                    "evidence_ref_count": len(normalized_ref_ids),
                },
            )
        )
    return tuple(sorted(candidates, key=lambda candidate: candidate.candidate_id))


def _classify_source_path(path: str) -> str:
    if path == "AGENTS.md" or path.endswith("/AGENTS.md") or path == "RUNBOOK_AGENT.md":
        return REF_AGENT_RULE
    if path.startswith("docs/orchestration/contracts/"):
        return REF_CONTRACT
    if path.startswith("tests/"):
        return REF_TEST
    if path.startswith("docs/review/"):
        return REF_REVIEW_ARTIFACT
    if path.startswith("docs/roadmap/"):
        return REF_ROADMAP
    if path.startswith("artifacts/orchestration/task_packets/"):
        return REF_ORCHESTRATION_PACKET
    return REF_CHANGED_FILE


def _derived_id(prefix: str, payload: JsonValue) -> str:
    fingerprint = fingerprint_payload(payload)
    return f"{prefix}:{fingerprint.removeprefix('sha256:')[:24]}"


def _validate_derived_id(name: str, value: str) -> str:
    normalized = value.strip()
    if not _DERIVED_ID_RE.match(normalized):
        raise ValueError(f"{name} must be an embedding/retrieval derived id")
    return normalized


def _validate_token(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if len(normalized) > MAX_STRING_LENGTH:
        raise ValueError(f"{name} exceeds maximum length")
    if normalized in {".", ".."}:
        raise ValueError(f"{name} contains unsafe metadata")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    if _UNSAFE_METADATA_RE.search(normalized) or _PATH_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe metadata")
    return normalized


def _validate_token_shape(name: str, value: str) -> str:
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


def _validate_repo_relative_path(name: str, value: str) -> str:
    normalized = value.strip().removeprefix("./")
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if len(normalized) > MAX_STRING_LENGTH:
        raise ValueError(f"{name} exceeds maximum length")
    if "\\" in normalized or normalized.startswith("../") or "/../" in normalized:
        raise ValueError(f"{name} contains unsafe metadata")
    if _PATH_RE.search(normalized) or not _REPO_PATH_RE.match(normalized):
        raise ValueError(f"{name} contains unsafe metadata")
    return normalized


def _normalize_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({_validate_token(name, value) for value in values}))


def _normalize_required_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = _normalize_unique_tokens(name, values)
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _normalize_required_derived_ids(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({_validate_derived_id(name, value) for value in values}))
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _normalize_required_followups(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(
        sorted({_validate_token_shape("required_followups", value) for value in values})
    )
    if not normalized:
        raise ValueError("required_followups must be non-empty")
    unsupported = [value for value in normalized if value not in DEFAULT_FOLLOWUPS]
    if unsupported:
        raise ValueError("required_followups contains unsupported value")
    return normalized


def _normalize_enum_values(
    name: str,
    values: Iterable[str],
    allowed_values: frozenset[str],
) -> tuple[str, ...]:
    normalized = tuple(sorted({_validate_token(name, value) for value in values}))
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    unsupported = [value for value in normalized if value not in allowed_values]
    if unsupported:
        raise ValueError(f"{name} contains unsupported value")
    return normalized


def _normalize_required_reason_codes(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({_validate_reason_code(value) for value in values}))
    if not normalized:
        raise ValueError("reason_codes must be non-empty")
    missing = sorted(set(REQUIRED_REASON_CODES) - set(normalized))
    if missing:
        raise ValueError("reason_codes missing required closed-gate values")
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


def _validate_false(name: str, value: bool) -> None:
    if value is not False:
        raise ValueError(f"{name} must remain false")


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
    if value.startswith("sha256:"):
        validate_fingerprint(value)
        return
    if _DERIVED_ID_RE.match(value):
        return
    if _UNSAFE_METADATA_RE.search(value) or _PATH_RE.search(value):
        raise ValueError(f"{name} contains unsafe metadata")
