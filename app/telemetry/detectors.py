"""Detector rules for escalating request captures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class DetectorContext:
    """Inputs used to decide whether a full capture is justified."""

    status_code: int
    response_content_type: str
    expected_response_kind: str | None = None
    llm_confidence: float | None = None
    explicit_hits: Sequence[str] = ()


def evaluate_capture_detectors(context: DetectorContext) -> tuple[str, ...]:
    """Return ordered detector hits for a request/response pair."""

    hits: list[str] = []
    for hit in context.explicit_hits:
        normalized = str(hit).strip().lower()
        if normalized and normalized not in hits:
            hits.append(normalized)

    if context.status_code >= 500 and "server_error" not in hits:
        hits.append("server_error")

    if context.llm_confidence is not None and context.llm_confidence < 0.35:
        if "low_confidence" not in hits:
            hits.append("low_confidence")

    expected_kind = (context.expected_response_kind or "").strip().lower()
    content_type = (context.response_content_type or "").strip().lower()
    if expected_kind == "json" and content_type and "application/json" not in content_type:
        if "schema_mismatch" not in hits:
            hits.append("schema_mismatch")

    return tuple(hits)
