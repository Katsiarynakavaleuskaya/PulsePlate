"""Deterministic advisory wiki bridge contracts for Evidence Graph."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Literal, TypeAlias, cast

from core.evidence.admission import AdmissionInput, ValidationStatus
from core.evidence.assets import EvidenceAssetRef, create_evidence_asset_ref
from core.evidence.fingerprints import (
    fingerprint_payload,
)
from core.evidence.policies import (
    normalize_upstream_ids,
    validate_fingerprint,
    validate_non_empty_token,
    validate_upstream_ids_for_rail,
)

WikiBridgeAssetType: TypeAlias = Literal[
    "knowledge_candidate", "context_bundle", "verification_bundle"
]
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
FrozenJson: TypeAlias = JsonScalar | tuple["FrozenJson", ...] | tuple[tuple[str, "FrozenJson"], ...]

_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_CURRENT_DIR_VALUES = {".", "./", "./."}
_FORBIDDEN_METADATA_KEY_FRAGMENTS = (
    "access_token",
    "api_key",
    "apikey",
    "answer_text",
    "health_payload",
    "medical_record",
    "password",
    "prompt",
    "query",
    "raw_prompt",
    "raw_query",
    "raw_response",
    "refresh_token",
    "response",
    "secret",
    "token",
    "user_health",
    "user_payload",
)
_FORBIDDEN_METADATA_STRING_FRAGMENTS = (
    "api_key=",
    "bearer ",
    "health payload",
    "medical record",
    "password=",
    "private key",
    "prompt:",
    "query:",
    "raw prompt",
    "raw query",
    "raw response",
    "response:",
    "sk-",
    "user health",
    "user payload",
)
_AUTHORITY_KEY_FRAGMENTS = (
    "authority",
    "canonical",
    "product_truth",
    "rail",
    "runtime",
    "source_of_truth",
)
_AUTHORITY_VALUE_FRAGMENTS = (
    "authoritative",
    "canonical",
    "product truth",
    "product_runtime",
    "runtime",
    "source of truth",
    "source_of_truth",
    "user-facing",
)
_PATH_VALUE_PREFIXES = (
    "./",
    "../",
    "~/",
    "/",
    "app/",
    "core/",
    "docs/",
    "evals/",
    "scripts/",
    "tests/",
)
_PATH_VALUE_SUFFIXES = (".json", ".jsonl", ".md", ".py", ".txt", ".yaml", ".yml")


@dataclass(frozen=True, slots=True)
class WikiEvidenceBridgePolicy:
    """Policy for mapping advisory wiki artifacts into evidence references."""

    policy_version: str
    allowed_corpora: tuple[str, ...]
    require_content_hash: bool = True
    require_source_rel_path: bool = True
    allow_promoted_only: bool = False
    allowed_admission_statuses: tuple[ValidationStatus, ...] = ("valid",)
    advisory_only_enforced: bool = True
    allowed_asset_types: tuple[WikiBridgeAssetType, ...] = (
        "knowledge_candidate",
        "context_bundle",
        "verification_bundle",
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "policy_version", validate_non_empty_token("policy_version", self.policy_version)
        )
        if not self.advisory_only_enforced:
            raise ValueError("advisory_only_enforced must be true")
        corpora = tuple(
            sorted({validate_non_empty_token("allowed_corpus", c) for c in self.allowed_corpora})
        )
        if not corpora:
            raise ValueError("allowed_corpora must not be empty")
        object.__setattr__(self, "allowed_corpora", corpora)

        statuses = tuple(sorted(set(self.allowed_admission_statuses)))
        if not statuses:
            raise ValueError("allowed_admission_statuses must not be empty")
        unsupported_statuses = set(statuses) - {"valid", "invalid", "degraded", "deferred"}
        if unsupported_statuses:
            raise ValueError(f"unsupported admission statuses: {sorted(unsupported_statuses)}")
        object.__setattr__(self, "allowed_admission_statuses", statuses)

        asset_types = tuple(sorted(set(self.allowed_asset_types)))
        if not asset_types:
            raise ValueError("allowed_asset_types must not be empty")
        unsupported_asset_types = set(asset_types) - {
            "knowledge_candidate",
            "context_bundle",
            "verification_bundle",
        }
        if unsupported_asset_types:
            raise ValueError(
                f"unsupported wiki bridge asset types: {sorted(unsupported_asset_types)}"
            )
        object.__setattr__(self, "allowed_asset_types", asset_types)


@dataclass(frozen=True, init=False, slots=True)
class AdvisoryWikiArtifactRef:
    """Immutable reference to an advisory-only wiki artifact."""

    artifact_id: str
    corpus: str
    slug: str
    source_rel_path: str
    page_path: str
    promoted_path: str | None
    content_hash: str
    policy_version: str
    idempotency_key: str
    advisory_only: bool
    promoted: bool
    upstream_ids: tuple[str, ...]
    _metadata: FrozenJson

    def __init__(
        self,
        *,
        artifact_id: str,
        corpus: str,
        slug: str,
        source_rel_path: str,
        page_path: str,
        promoted_path: str | None,
        content_hash: str,
        policy_version: str,
        idempotency_key: str,
        advisory_only: bool,
        promoted: bool,
        upstream_ids: Iterable[str],
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> None:
        if not advisory_only:
            raise ValueError("advisory_only must be true")
        normalized_hash = _normalize_content_hash(content_hash)
        validate_fingerprint(normalized_hash)

        object.__setattr__(
            self, "artifact_id", _validate_non_empty_identifier(artifact_id, "artifact_id")
        )
        object.__setattr__(self, "corpus", _validate_sluglike_token(corpus, "corpus"))
        object.__setattr__(self, "slug", _validate_sluglike_token(slug, "slug"))
        object.__setattr__(
            self,
            "source_rel_path",
            _validate_bridge_path("source_rel_path", source_rel_path, allow_docs_authority=True),
        )
        object.__setattr__(
            self,
            "page_path",
            _validate_bridge_path("page_path", page_path, allow_docs_authority=False),
        )
        normalized_promoted_path = (
            None
            if promoted_path is None
            else _validate_bridge_path("promoted_path", promoted_path, allow_docs_authority=False)
        )
        object.__setattr__(self, "promoted_path", normalized_promoted_path)
        object.__setattr__(self, "content_hash", normalized_hash)
        object.__setattr__(
            self, "policy_version", validate_non_empty_token("policy_version", policy_version)
        )
        object.__setattr__(
            self,
            "idempotency_key",
            _validate_non_empty_identifier(idempotency_key, "idempotency_key"),
        )
        object.__setattr__(self, "advisory_only", True)
        object.__setattr__(self, "promoted", bool(promoted))
        normalized_upstream_ids = normalize_upstream_ids(tuple(upstream_ids))
        validate_upstream_ids_for_rail(rail="advisory", upstream_ids=normalized_upstream_ids)
        object.__setattr__(self, "upstream_ids", normalized_upstream_ids)
        object.__setattr__(self, "_metadata", _freeze_metadata(metadata or {}))

    @property
    def metadata(self) -> dict[str, JsonValue]:
        return cast(dict[str, JsonValue], _thaw_json(self._metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "advisory_only": self.advisory_only,
            "artifact_id": self.artifact_id,
            "content_hash": self.content_hash,
            "corpus": self.corpus,
            "idempotency_key": self.idempotency_key,
            "metadata": self.metadata,
            "page_path": self.page_path,
            "policy_version": self.policy_version,
            "promoted": self.promoted,
            "promoted_path": self.promoted_path,
            "slug": self.slug,
            "source_rel_path": self.source_rel_path,
            "upstream_ids": list(self.upstream_ids),
        }
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def create_advisory_wiki_artifact_ref(
    *,
    corpus: str,
    slug: str,
    source_rel_path: str,
    page_path: str,
    content_hash: str,
    policy_version: str,
    promoted_path: str | None = None,
    promoted: bool = False,
    upstream_ids: Iterable[str] = (),
    metadata: Mapping[str, JsonValue] | None = None,
    policy: WikiEvidenceBridgePolicy | None = None,
) -> AdvisoryWikiArtifactRef:
    """Create a deterministic advisory wiki artifact reference."""

    normalized_corpus = _validate_sluglike_token(corpus, "corpus")
    normalized_slug = _validate_sluglike_token(slug, "slug")
    normalized_policy_version = validate_non_empty_token("policy_version", policy_version)
    normalized_hash = _normalize_content_hash(content_hash)
    normalized_source_path = _validate_bridge_path(
        "source_rel_path", source_rel_path, allow_docs_authority=True
    )
    normalized_page_path = _validate_bridge_path("page_path", page_path, allow_docs_authority=False)
    normalized_promoted_path = (
        None
        if promoted_path is None
        else _validate_bridge_path("promoted_path", promoted_path, allow_docs_authority=False)
    )
    normalized_upstream_ids = normalize_upstream_ids(tuple(upstream_ids))
    validate_upstream_ids_for_rail(rail="advisory", upstream_ids=normalized_upstream_ids)
    _validate_policy(policy, normalized_policy_version, normalized_corpus, bool(promoted))

    identity_payload: dict[str, JsonValue] = {
        "advisory_only": True,
        "content_hash": normalized_hash,
        "corpus": normalized_corpus,
        "page_path": normalized_page_path,
        "policy_version": normalized_policy_version,
        "promoted": bool(promoted),
        "promoted_path": normalized_promoted_path,
        "slug": normalized_slug,
        "source_rel_path": normalized_source_path,
        "upstream_ids": list(normalized_upstream_ids),
    }
    digest = fingerprint_payload(identity_payload).removeprefix("sha256:")
    artifact_id = f"advisory-wiki:{digest[:24]}"
    idempotency_key = f"idem:advisory-wiki:{digest}"
    return AdvisoryWikiArtifactRef(
        artifact_id=artifact_id,
        corpus=normalized_corpus,
        slug=normalized_slug,
        source_rel_path=normalized_source_path,
        page_path=normalized_page_path,
        promoted_path=normalized_promoted_path,
        content_hash=normalized_hash,
        policy_version=normalized_policy_version,
        idempotency_key=idempotency_key,
        advisory_only=True,
        promoted=promoted,
        upstream_ids=normalized_upstream_ids,
        metadata=metadata,
    )


def wiki_artifact_to_evidence_asset_ref(
    artifact: AdvisoryWikiArtifactRef,
    *,
    asset_type: WikiBridgeAssetType = "knowledge_candidate",
    version: str = "v1",
    policy: WikiEvidenceBridgePolicy | None = None,
) -> EvidenceAssetRef:
    """Map an advisory wiki artifact into an advisory evidence asset."""

    if not isinstance(artifact, AdvisoryWikiArtifactRef):
        raise TypeError("artifact must be AdvisoryWikiArtifactRef")
    normalized_asset_type = cast(
        WikiBridgeAssetType, validate_non_empty_token("asset_type", asset_type)
    )
    allowed_asset_types = (
        policy.allowed_asset_types
        if policy is not None
        else ("knowledge_candidate", "context_bundle", "verification_bundle")
    )
    if normalized_asset_type not in allowed_asset_types:
        raise ValueError(f"unsupported advisory wiki asset_type: {normalized_asset_type}")
    _validate_policy(policy, artifact.policy_version, artifact.corpus, artifact.promoted)

    payload: dict[str, JsonValue] = {
        "advisory_only": True,
        "artifact_id": artifact.artifact_id,
        "bridge": "advisory_wiki",
        "content_hash": artifact.content_hash,
        "corpus": artifact.corpus,
        "promoted": artifact.promoted,
        "slug": artifact.slug,
    }
    return create_evidence_asset_ref(
        asset_type=normalized_asset_type,
        rail="advisory",
        version=version,
        policy_version=artifact.policy_version,
        payload=payload,
        upstream_ids=artifact.upstream_ids,
    )


def wiki_artifact_to_admission_input(
    artifact: AdvisoryWikiArtifactRef,
    *,
    produced_at: str,
    coverage_rate: float,
    verification_rate: float,
    fallback_rate: float,
    validation_status: ValidationStatus = "valid",
    degraded_reason: str | None = None,
    metadata: Mapping[str, JsonValue] | None = None,
    policy: WikiEvidenceBridgePolicy | None = None,
) -> AdmissionInput:
    """Adapt a wiki artifact to E4 admission input for advisory review only."""

    if not isinstance(artifact, AdvisoryWikiArtifactRef):
        raise TypeError("artifact must be AdvisoryWikiArtifactRef")
    _validate_policy(policy, artifact.policy_version, artifact.corpus, artifact.promoted)
    allowed_statuses = policy.allowed_admission_statuses if policy is not None else ("valid",)
    if validation_status not in allowed_statuses:
        raise ValueError(
            f"validation_status is not admitted by wiki bridge policy: {validation_status}"
        )
    _freeze_metadata(metadata or {})
    admission_metadata: dict[str, JsonValue] = {
        "advisory_only": True,
        "bridge": "advisory_wiki",
        "corpus": artifact.corpus,
        "promoted": artifact.promoted,
        "serve_scope": "advisory_review_only",
        "slug": artifact.slug,
    }
    if metadata:
        admission_metadata["bridge_metadata"] = _thaw_json(_freeze_metadata(metadata))

    return AdmissionInput(
        target_id=artifact.artifact_id,
        target_type="evidence_asset",
        fingerprint=artifact.content_hash,
        idempotency_key=artifact.idempotency_key,
        policy_version=artifact.policy_version,
        produced_at=produced_at,
        validation_status=validation_status,
        coverage_rate=coverage_rate,
        verification_rate=verification_rate,
        fallback_rate=fallback_rate,
        degraded_reason=degraded_reason,
        upstream_ids=artifact.upstream_ids,
        metadata=admission_metadata,
    )


def _validate_policy(
    policy: WikiEvidenceBridgePolicy | None,
    policy_version: str,
    corpus: str,
    promoted: bool,
) -> None:
    if policy is None:
        return
    if policy.policy_version != policy_version:
        raise ValueError("policy_version must match bridge policy")
    if corpus not in policy.allowed_corpora:
        raise ValueError(f"corpus is not admitted by wiki bridge policy: {corpus}")
    if policy.require_content_hash is not True:
        raise ValueError("wiki bridge policy must require content_hash")
    if policy.require_source_rel_path is not True:
        raise ValueError("wiki bridge policy must require source_rel_path")
    if policy.allow_promoted_only and not promoted:
        raise ValueError("wiki bridge policy requires promoted artifacts")


def _validate_sluglike_token(value: str, field_name: str) -> str:
    normalized = validate_non_empty_token(field_name, value)
    if not isinstance(normalized, str):
        raise TypeError(f"{field_name} must be a string")
    if normalized in _CURRENT_DIR_VALUES or "/" in normalized or "\\" in normalized:
        raise ValueError(f"{field_name} must be a slug-like token")
    if ".." in normalized:
        raise ValueError(f"{field_name} must not contain traversal")
    return normalized


def _normalize_content_hash(value: str) -> str:
    normalized = _validate_non_empty_identifier(value, "content_hash").lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError("content_hash must be sha256 hex")
    if not normalized.startswith("sha256:"):
        normalized = f"sha256:{normalized}"
    return normalized


def _validate_non_empty_identifier(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{field_name} must not contain whitespace")
    return normalized


def _validate_bridge_path(
    field_name: str,
    value: str,
    *,
    allow_docs_authority: bool,
) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError(f"{field_name} must not be blank")
    normalized = raw.replace("\\", "/")
    if normalized in _CURRENT_DIR_VALUES:
        raise ValueError(f"{field_name} must not reference current directory")
    first_segment = normalized.split("/", maxsplit=1)[0]
    if (
        normalized.startswith("/")
        or normalized.startswith("~")
        or _WINDOWS_DRIVE_RE.match(raw)
        or _URI_SCHEME_RE.match(raw)
        or ":" in first_segment
    ):
        raise ValueError(f"{field_name} must be repo-relative")
    path = PurePosixPath(normalized)
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{field_name} must not contain unsafe path segments")
    if parts[0] == "docs" and not allow_docs_authority:
        raise ValueError(f"{field_name} must not be under canonical docs authority")
    return path.as_posix()


def _freeze_metadata(value: Mapping[str, JsonValue]) -> FrozenJson:
    _validate_metadata(value)
    return _freeze_json(value)


def _validate_metadata(value: JsonValue, *, key_path: tuple[str, ...] = ()) -> None:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise ValueError("metadata must be JSON-compatible")
    if isinstance(value, str):
        _validate_metadata_string(value, key_path)
        return
    if isinstance(value, bool) or value is None or isinstance(value, int):
        if key_path and key_path[-1].lower() == "advisory_only" and value is not True:
            raise ValueError("advisory_only metadata must be true")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("metadata numbers must be finite")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("metadata keys must be strings")
            _validate_metadata_key(key, child)
            _validate_metadata(child, key_path=(*key_path, key))
        return
    if isinstance(value, Sequence):
        for index, child in enumerate(value):
            _validate_metadata(child, key_path=(*key_path, str(index)))
        return
    raise ValueError("metadata must be JSON-compatible")


def _validate_metadata_key(key: str, value: JsonValue) -> None:
    normalized_key = key.strip().lower().replace("-", "_")
    if not normalized_key:
        raise ValueError("metadata keys must not be blank")
    if any(fragment in normalized_key for fragment in _FORBIDDEN_METADATA_KEY_FRAGMENTS):
        raise ValueError(f"metadata contains forbidden field: {key}")
    if any(fragment in normalized_key for fragment in _AUTHORITY_KEY_FRAGMENTS):
        if _metadata_value_claims_authority(value):
            raise ValueError(f"metadata contains forbidden authority claim: {key}")
    if normalized_key == "advisory_only" and value is not True:
        raise ValueError("advisory_only metadata must be true")


def _validate_metadata_string(value: str, key_path: tuple[str, ...]) -> None:
    normalized = value.strip()
    lower = normalized.lower()
    if lower in _CURRENT_DIR_VALUES:
        raise ValueError("metadata contains unsafe path-like value")
    if any(fragment in lower for fragment in _FORBIDDEN_METADATA_STRING_FRAGMENTS):
        raise ValueError("metadata contains forbidden raw payload")
    if any(
        lower.startswith(prefix) or lower.endswith(suffix)
        for prefix in _PATH_VALUE_PREFIXES
        for suffix in _PATH_VALUE_SUFFIXES
    ):
        raise ValueError("metadata contains unsafe path-like value")
    if lower.startswith(_PATH_VALUE_PREFIXES) or lower.endswith(_PATH_VALUE_SUFFIXES):
        raise ValueError("metadata contains unsafe path-like value")
    if key_path and any(fragment in key_path[-1].lower() for fragment in _AUTHORITY_KEY_FRAGMENTS):
        if any(fragment in lower for fragment in _AUTHORITY_VALUE_FRAGMENTS):
            raise ValueError("metadata contains forbidden authority claim")


def _metadata_value_claims_authority(value: JsonValue) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        lower = value.strip().lower()
        return any(fragment in lower for fragment in _AUTHORITY_VALUE_FRAGMENTS)
    if isinstance(value, Mapping):
        return any(_metadata_value_claims_authority(child) for child in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview)):
        return any(_metadata_value_claims_authority(child) for child in value)
    return False


def _freeze_json(value: JsonValue) -> FrozenJson:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int, float)):
        return value
    if isinstance(value, Mapping):
        return tuple((key, _freeze_json(child)) for key, child in sorted(value.items()))
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview)):
        return tuple(_freeze_json(child) for child in value)
    raise ValueError("metadata must be JSON-compatible")


def _thaw_json(value: FrozenJson) -> JsonValue:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
            for item in value
        ):
            return {
                key: _thaw_json(child)
                for key, child in cast(tuple[tuple[str, FrozenJson], ...], value)
            }
        return [_thaw_json(child) for child in value]
    return value
