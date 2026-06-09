"""Deterministic prompt-module metadata contracts.

This scaffold stores prompt-module identifiers, fingerprints, and counts only.
It does not store raw prompt text, call providers, or enable semantic-cache
serving.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import TypeAlias

from core.evidence.fingerprints import fingerprint_payload

JsonScalar: TypeAlias = str | int | bool | None
JsonValue: TypeAlias = (
    JsonScalar | list["JsonValue"] | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
)

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PATH_RE = re.compile(r"(?:^|[\s=(;,])(?:/|~[/\\]|[A-Za-z]:[\\/]|\\\\|file://)")
_UNSAFE_METADATA_RE = re.compile(
    r"raw[_ -]?(?:query|prompt|response|answer|context)"
    r"|normalized[_ -]?query"
    r"|provider[_ -]?payload"
    r"|prompt"
    r"|response"
    r"|answer"
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
    r"|user[_ -]?health",
    re.IGNORECASE,
)
_UNSAFE_TOKEN_RE = re.compile(
    r"raw[_ -]?(?:query|prompt|response|answer|context)"
    r"|normalized[_ -]?query"
    r"|provider[_ -]?payload"
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
    r"|user[_ -]?health",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PromptModuleRecord:
    """Safe prompt-module metadata for future prefix/context reuse analysis."""

    module_id: str
    module_version: str
    surface: str
    text_fingerprint: str
    char_count: int
    token_estimate: int
    token_estimate_version: str
    policy_version: str
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _validate_token("module_id", self.module_id))
        object.__setattr__(
            self,
            "module_version",
            _validate_token("module_version", self.module_version),
        )
        object.__setattr__(self, "surface", _validate_token("surface", self.surface))
        object.__setattr__(
            self,
            "text_fingerprint",
            _validate_fingerprint("text_fingerprint", self.text_fingerprint),
        )
        object.__setattr__(
            self,
            "char_count",
            _validate_non_negative_int("char_count", self.char_count),
        )
        object.__setattr__(
            self,
            "token_estimate",
            _validate_non_negative_int("token_estimate", self.token_estimate),
        )
        object.__setattr__(
            self,
            "token_estimate_version",
            _validate_token("token_estimate_version", self.token_estimate_version),
        )
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class PromptModuleRegistry:
    """Deterministic prompt-module registry snapshot."""

    registry_id: str
    policy_version: str
    records: tuple[PromptModuleRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )
        raw_records = tuple(self.records)
        if not raw_records:
            raise ValueError("records must be non-empty")
        seen: set[tuple[str, str]] = set()
        for record in raw_records:
            if not isinstance(record, PromptModuleRecord):
                raise ValueError("records must contain PromptModuleRecord")
            key = (record.surface, record.module_id)
            if key in seen:
                raise ValueError("records contains duplicate prompt module")
            seen.add(key)
        records = tuple(sorted(raw_records, key=lambda item: (item.surface, item.module_id)))
        payload: JsonValue = {
            "policy_version": self.policy_version,
            "records": [dict(to_stable_mapping(record)) for record in records],
        }
        registry_id = f"pm-registry:{fingerprint_payload(payload)[7:31]}"
        object.__setattr__(self, "registry_id", _validate_token("registry_id", registry_id))
        object.__setattr__(self, "records", records)


def build_prompt_module_record(
    *,
    module_id: str,
    module_version: str,
    surface: str,
    text_fingerprint: str,
    char_count: int,
    token_estimate: int,
    token_estimate_version: str,
    policy_version: str,
    metadata: Mapping[str, JsonValue] | None = None,
) -> PromptModuleRecord:
    """Build one prompt-module metadata record without accepting raw text."""

    return PromptModuleRecord(
        module_id=module_id,
        module_version=module_version,
        surface=surface,
        text_fingerprint=text_fingerprint,
        char_count=char_count,
        token_estimate=token_estimate,
        token_estimate_version=token_estimate_version,
        policy_version=policy_version,
        metadata=metadata or {},
    )


def build_prompt_module_registry(
    *,
    policy_version: str,
    records: Iterable[PromptModuleRecord],
) -> PromptModuleRegistry:
    """Build a stable registry identity from prompt-module metadata."""

    normalized_policy_version = _validate_token("policy_version", policy_version)
    raw_records = tuple(records)
    for record in raw_records:
        if not isinstance(record, PromptModuleRecord):
            raise ValueError("records must contain PromptModuleRecord")
    ordered = tuple(sorted(raw_records, key=lambda item: (item.surface, item.module_id)))
    payload: JsonValue = {
        "policy_version": normalized_policy_version,
        "records": [dict(to_stable_mapping(record)) for record in ordered],
    }
    return PromptModuleRegistry(
        registry_id=f"pm-registry:{fingerprint_payload(payload)[7:31]}",
        policy_version=normalized_policy_version,
        records=ordered,
    )


def prompt_module_fingerprints(records: Iterable[PromptModuleRecord]) -> tuple[str, ...]:
    """Return stable text fingerprints for provenance envelopes."""

    return tuple(sorted({record.text_fingerprint for record in records}))


def to_stable_mapping(value: object) -> Mapping[str, JsonValue]:
    """Return deterministic safe JSON-ready mappings."""

    if isinstance(value, PromptModuleRecord):
        return _freeze_mapping(
            {
                "char_count": value.char_count,
                "metadata": _json_safe_copy(value.metadata),
                "module_id": value.module_id,
                "module_version": value.module_version,
                "policy_version": value.policy_version,
                "surface": value.surface,
                "text_fingerprint": value.text_fingerprint,
                "token_estimate": value.token_estimate,
                "token_estimate_version": value.token_estimate_version,
            }
        )
    if isinstance(value, PromptModuleRegistry):
        return _freeze_mapping(
            {
                "policy_version": value.policy_version,
                "records": [dict(to_stable_mapping(record)) for record in value.records],
                "registry_id": value.registry_id,
            }
        )
    raise ValueError(f"unsupported stable mapping value: {type(value).__name__}")


def _freeze_metadata(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    copied = _json_safe_copy(value)
    if not isinstance(copied, dict):
        raise ValueError("metadata must be a mapping")
    _validate_metadata_is_safe(copied)
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


def _validate_metadata_is_safe(value: JsonValue, *, path: str = "metadata") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_safe_metadata_string(f"{path}.key", key)
            _validate_metadata_is_safe(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_metadata_is_safe(item, path=f"{path}[{index}]")
    elif isinstance(value, str):
        _validate_safe_metadata_string(path, value)


def _validate_safe_metadata_string(name: str, value: str) -> None:
    if _UNSAFE_METADATA_RE.search(value) or _PATH_RE.search(value):
        raise ValueError(f"{name} contains unsafe metadata")


def _validate_token(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    if _UNSAFE_TOKEN_RE.search(normalized) or _PATH_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe metadata")
    return normalized


def _validate_fingerprint(name: str, value: str) -> str:
    normalized = value.strip()
    if not _FINGERPRINT_RE.match(normalized):
        raise ValueError(f"{name} must be sha256 fingerprint")
    return normalized


def _validate_non_negative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value
