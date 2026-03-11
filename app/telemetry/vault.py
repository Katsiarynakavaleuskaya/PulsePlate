"""Encrypted vault helpers for minimized full-capture artifacts."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.compliance.minimization import (
    get_sensitive_field_taxonomy,
    minimize_free_text,
    sanitize_audit_string,
)
from core.pii_redaction import redact_pii_from_text


@dataclass(frozen=True)
class VaultPointer:
    """Reference to an encrypted full-capture artifact."""

    path: str
    sha256: str
    bytes_written: int


def _resolve_field_name(field_path: str) -> str:
    """Map nested field names to minimization taxonomy families."""

    lowered = field_path.lower()
    if "provider_trace" in lowered:
        return "provider_trace"
    if "prompt" in lowered:
        return "prompt"
    if (
        "health" in lowered
        or "medical" in lowered
        or "diagnosis" in lowered
        or "allergy" in lowered
    ):
        return "health_profile"
    if "response" in lowered:
        return "llm_response"
    if "query" in lowered or "request" in lowered or "body" in lowered:
        return "query"
    if "content" in lowered or "preview" in lowered:
        return "source_content"
    return "preview"


def _minimize_scalar(value: Any, *, field_path: str) -> Any:
    """Return audit-safe scalar representation."""

    if isinstance(value, str):
        field_name = _resolve_field_name(field_path)
        policy = get_sensitive_field_taxonomy().get(field_name)
        if policy is not None and policy.persistence_rule == "hash_only":
            audit_value = sanitize_audit_string(field_name, value)
            if isinstance(audit_value, dict):
                return audit_value
        redacted = redact_pii_from_text(value) or ""
        return minimize_free_text(redacted, field_name=field_name)
    return value


def minimize_capture_payload(payload: Any, *, field_path: str = "root") -> Any:
    """Recursively minimize payload before encryption."""

    if isinstance(payload, Mapping):
        result: dict[str, Any] = {}
        for key, value in payload.items():
            nested_path = f"{field_path}.{key}"
            minimized = minimize_capture_payload(value, field_path=nested_path)
            if minimized is not None:
                result[str(key)] = minimized
        return result
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return [minimize_capture_payload(item, field_path=f"{field_path}[]") for item in payload]
    return _minimize_scalar(payload, field_path=field_path)


def _load_vault_key(encoded_key: str) -> bytes:
    """Decode base64 vault key and validate AES-GCM key size."""

    key = base64.b64decode(encoded_key.encode("utf-8"))
    if len(key) not in {16, 24, 32}:
        raise ValueError("TELEMETRY_VAULT_KEY must decode to 16, 24, or 32 bytes")
    return key


def store_capture_artifact(
    *,
    payload: Mapping[str, Any],
    vault_dir: str,
    encoded_key: str,
) -> VaultPointer:
    """Encrypt and store a minimized capture artifact."""

    key = _load_vault_key(encoded_key)
    sanitized_payload = minimize_capture_payload(payload)
    plaintext = json.dumps(
        sanitized_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = nonce + aesgcm.encrypt(nonce, plaintext, None)

    date_partition = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    artifact_dir = Path(vault_dir) / date_partition
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{uuid4().hex}.bin"
    artifact_path.write_bytes(ciphertext)

    return VaultPointer(
        path=str(artifact_path),
        sha256=hashlib.sha256(ciphertext).hexdigest(),
        bytes_written=len(ciphertext),
    )


def decrypt_capture_artifact(*, artifact_path: str, encoded_key: str) -> dict[str, Any]:
    """Decrypt an artifact for tests and audited workflows."""

    key = _load_vault_key(encoded_key)
    ciphertext = Path(artifact_path).read_bytes()
    nonce, encrypted = ciphertext[:12], ciphertext[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, encrypted, None)
    payload: dict[str, Any]
    payload = json.loads(plaintext.decode("utf-8"))
    return payload
