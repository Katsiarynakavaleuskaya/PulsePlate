"""Best-effort request telemetry foundation middleware.

RU: Middleware должен быть fail-closed для данных, но fail-open для запросов.
EN: Middleware must fail closed for data capture, but fail open for requests.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
import logging
import time
from typing import Any, Mapping
from uuid import uuid4

from fastapi import Request, Response

from app.telemetry import (
    FEATURED_RUNTIME_FLAGS,
    is_non_prod_environment,
    telemetry_client_debug_full_enabled,
    telemetry_detectors_enabled,
    telemetry_full_capture_rate,
    telemetry_recorder_maxlen,
    telemetry_reservoir_per_hour,
    telemetry_sampler_salt,
    telemetry_vault_dir,
    telemetry_vault_key,
)
from app.telemetry.detectors import DetectorContext, evaluate_capture_detectors
from app.telemetry.reservoir import HourlyReservoir
from app.telemetry.sampler import DeterministicHashSampler
from app.telemetry.vault import store_capture_artifact

logger = logging.getLogger(__name__)
MAX_CAPTURED_BODY_BYTES = 16_384


@dataclass(frozen=True)
class RequestTelemetrySpan:
    """Recorded request span payload."""

    trace_id: str
    name: str
    attributes: Mapping[str, Any]


class InMemorySpanRecorder:
    """Small bounded recorder used for diagnostics and deterministic tests."""

    def __init__(self, maxlen: int) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def record(self, span: RequestTelemetrySpan) -> None:
        """Append span payload to the recorder."""

        self._items.append(
            {
                "trace_id": span.trace_id,
                "name": span.name,
                "attributes": dict(span.attributes),
            }
        )

    def snapshot(self) -> list[dict[str, Any]]:
        """Return current recorder snapshot."""

        return list(self._items)


def _get_sampler(request: Request) -> DeterministicHashSampler:
    sampler = getattr(request.app.state, "request_telemetry_sampler", None)
    if sampler is None:
        sampler = DeterministicHashSampler(
            rate=telemetry_full_capture_rate(),
            salt=telemetry_sampler_salt(),
        )
        request.app.state.request_telemetry_sampler = sampler
    return sampler


def _get_reservoir(request: Request) -> HourlyReservoir:
    reservoir = getattr(request.app.state, "request_telemetry_reservoir", None)
    if reservoir is None:
        reservoir = HourlyReservoir(n=telemetry_reservoir_per_hour())
        request.app.state.request_telemetry_reservoir = reservoir
    return reservoir


def _get_recorder(request: Request) -> InMemorySpanRecorder:
    recorder = getattr(request.app.state, "request_telemetry_recorder", None)
    if recorder is None:
        recorder = InMemorySpanRecorder(maxlen=telemetry_recorder_maxlen())
        request.app.state.request_telemetry_recorder = recorder
    return recorder


def build_request_fingerprint(request: Request, route_template: str | None) -> str:
    """Build stable request fingerprint from low-cardinality request attributes."""

    fingerprint_payload = {
        "method": request.method.upper(),
        "route": route_template or request.url.path,
        "query_keys": sorted(request.query_params.keys()),
        "content_type": request.headers.get("content-type", "").split(";")[0].strip().lower(),
    }
    encoded = json.dumps(
        fingerprint_payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.blake2s(encoded, digest_size=16).hexdigest()


def _feature_flags_from_request(request: Request) -> list[str]:
    """Collect known runtime feature flags into a low-cardinality list."""

    enabled_flags = []
    for flag_name in FEATURED_RUNTIME_FLAGS:
        value = (request.headers.get(flag_name) or "").strip().lower()
        if value in {"1", "true", "yes", "on"}:
            enabled_flags.append(flag_name)
    return enabled_flags


def _extract_tier(request: Request) -> str:
    """Return best-effort tier hint without changing auth behavior."""

    current_user = getattr(request.state, "current_user", None)
    tier = getattr(current_user, "tier", None)
    if isinstance(tier, str) and tier.strip():
        return tier.strip().lower()
    header_tier = request.headers.get("X-Api-Tier")
    if header_tier:
        return header_tier.strip().lower()
    return "unknown"


def _clone_request_with_body(request: Request, body: bytes) -> Request:
    """Rebuild request so downstream handlers can read the cached body."""

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(request.scope, receive)


def _body_preview(value: bytes | None) -> str | None:
    """Return bounded text preview for encrypted artifact storage."""

    if not value:
        return None
    preview = value[:MAX_CAPTURED_BODY_BYTES]
    return preview.decode("utf-8", errors="replace")


async def request_telemetry_middleware(request: Request, call_next: Any) -> Response:
    """Record lightweight request spans and rare encrypted capture pointers."""

    start = time.perf_counter()
    body = await request.body()
    cloned_request = _clone_request_with_body(request, body)
    response: Response | None = None
    error: Exception | None = None

    try:
        response = await call_next(cloned_request)
        return response
    except Exception as exc:  # pragma: no cover - exercised through status fallback path
        error = exc
        raise
    finally:
        try:
            route_template = getattr(request.scope.get("route"), "path", None)
            fingerprint = build_request_fingerprint(request, route_template=route_template)
            sampler = _get_sampler(request)
            reservoir = _get_reservoir(request)
            recorder = _get_recorder(request)
            sample_decision = sampler.decide(fingerprint=fingerprint)

            status_code = response.status_code if response is not None else 500
            response_content_type = ""
            if response is not None:
                response_content_type = response.headers.get("content-type", "")
            detector_hits: tuple[str, ...] = ()
            if telemetry_detectors_enabled():
                detector_hits = evaluate_capture_detectors(
                    DetectorContext(
                        status_code=status_code,
                        response_content_type=response_content_type,
                        expected_response_kind=getattr(
                            request.state,
                            "expected_response_kind",
                            None,
                        ),
                        llm_confidence=getattr(request.state, "llm_confidence", None),
                        explicit_hits=tuple(
                            getattr(request.state, "telemetry_detector_hits", ()) or ()
                        ),
                    )
                )

            capture_reasons: list[str] = []
            should_capture_full = False
            if detector_hits:
                should_capture_full = True
                capture_reasons.extend(f"detector:{hit}" for hit in detector_hits)

            if (
                not should_capture_full
                and is_non_prod_environment()
                and telemetry_client_debug_full_enabled()
                and request.headers.get("X-Debug-Full") == "1"
            ):
                should_capture_full = True
                capture_reasons.append("debug_header")

            if not should_capture_full and sample_decision.capture_full:
                should_capture_full = True
                capture_reasons.append("sampled")

            if not should_capture_full and reservoir.take():
                should_capture_full = True
                capture_reasons.append("reservoir")

            attributes: dict[str, Any] = {
                "http.method": request.method.upper(),
                "http.route": route_template or request.url.path,
                "http.status_code": status_code,
                "duration.ms": round((time.perf_counter() - start) * 1000, 3),
                "pp.req.fingerprint": fingerprint,
                "pp.req.query_key_count": len(request.query_params),
                "pp.sample.rate": sample_decision.rate,
                "pp.sample.digest_prefix": sample_decision.digest_prefix,
                "pp.tier": _extract_tier(request),
                "pp.flags": _feature_flags_from_request(request),
                "pp.detectors": list(detector_hits),
                "pp.full_capture_requested": should_capture_full,
                "pp.client.platform": request.headers.get("X-Client-Platform", "unknown"),
            }

            if should_capture_full and telemetry_vault_dir() and telemetry_vault_key():
                response_body = getattr(response, "body", None)
                capture_payload = {
                    "request": {
                        "method": request.method.upper(),
                        "route": route_template or request.url.path,
                        "query_params": dict(request.query_params),
                        "headers": {
                            "content-type": request.headers.get("content-type"),
                            "x-client-platform": request.headers.get("X-Client-Platform"),
                            "x-api-tier": request.headers.get("X-Api-Tier"),
                        },
                        "request_body": _body_preview(body),
                    },
                    "response": {
                        "status_code": status_code,
                        "content_type": response_content_type,
                        "response_body": _body_preview(response_body),
                    },
                    "telemetry": {
                        "fingerprint": fingerprint,
                        "capture_reasons": capture_reasons,
                        "detector_hits": list(detector_hits),
                    },
                }
                pointer = store_capture_artifact(
                    payload=capture_payload,
                    vault_dir=str(telemetry_vault_dir()),
                    encoded_key=str(telemetry_vault_key()),
                )
                attributes["pp.full_capture"] = True
                attributes["pp.full_pointer_sha256"] = pointer.sha256
                attributes["pp.full_capture_reasons"] = capture_reasons
            else:
                attributes["pp.full_capture"] = False
                if capture_reasons:
                    attributes["pp.full_capture_reasons"] = capture_reasons

            recorder.record(
                RequestTelemetrySpan(
                    trace_id=uuid4().hex,
                    name=route_template or request.url.path,
                    attributes=attributes,
                )
            )
        except Exception:
            logger.debug("Request telemetry capture failed", exc_info=True)
        finally:
            if error is not None:
                logger.debug("Request failed after telemetry processing", exc_info=error)
