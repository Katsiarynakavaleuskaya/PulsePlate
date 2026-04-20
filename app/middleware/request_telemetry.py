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
from typing import Any, Mapping, cast
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
UNMATCHED_ROUTE_LABEL = "<unmatched_route>"
KNOWN_CLIENT_PLATFORMS = {"web", "ios", "android"}
KNOWN_TIERS = {"free", "pro", "vip"}
KNOWN_CONTENT_TYPES = {
    "application/json",
    "application/problem+json",
    "application/vnd.api+json",
    "application/octet-stream",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
    "text/plain",
}


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


def _normalized_route_label(route_template: str | None) -> str:
    """Return a safe low-cardinality route label."""

    normalized = (route_template or "").strip()
    return normalized or UNMATCHED_ROUTE_LABEL


def _normalized_content_type(raw_content_type: str | None) -> str:
    """Collapse client-controlled content-type values to a safe allowlist."""

    normalized = (raw_content_type or "").split(";", 1)[0].strip().lower()
    if normalized in KNOWN_CONTENT_TYPES:
        return normalized
    if normalized.endswith("+json"):
        return "application/*+json"
    if normalized.startswith("multipart/"):
        return "multipart/other"
    if normalized.startswith("text/"):
        return "text/other"
    return "other"


def _normalized_platform_label(raw_platform: str | None) -> str:
    """Whitelist client platform labels before persisting them in spans."""

    normalized = (raw_platform or "").strip().lower()
    if normalized in KNOWN_CLIENT_PLATFORMS:
        return normalized
    return "unknown"


def _normalized_tier_label(raw_tier: str | None) -> str:
    """Whitelist tier hints before persisting them in spans."""

    normalized = (raw_tier or "").strip().lower()
    if normalized in KNOWN_TIERS:
        return normalized
    return "unknown"


def build_request_fingerprint(request: Request, route_template: str | None) -> str:
    """Build stable request fingerprint from low-cardinality request attributes."""

    fingerprint_payload = {
        "method": request.method.upper(),
        "route": _normalized_route_label(route_template),
        "query_keys": sorted(request.query_params.keys()),
        "content_type": _normalized_content_type(request.headers.get("content-type")),
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
        return _normalized_tier_label(tier)
    header_tier = request.headers.get("X-Api-Tier")
    if isinstance(header_tier, str) and header_tier.strip():
        return _normalized_tier_label(header_tier)
    return "unknown"


def _clone_request_with_body(request: Request, body: bytes) -> Request:
    """Rebuild request so downstream handlers can read the cached body."""

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(request.scope, receive)


def _clone_request_with_preview_buffer(
    request: Request,
    *,
    preview_limit: int = MAX_CAPTURED_BODY_BYTES,
) -> tuple[Request, bytearray]:
    """Stream the request body downstream while caching a bounded preview.

    RU: Телеметрия хранит только ограниченный preview и не буферизует весь body.
    EN: Telemetry stores only a bounded preview and does not buffer the full body.
    """

    preview = bytearray()
    upstream_receive = request.receive

    async def receive() -> dict[str, Any]:
        message = await upstream_receive()
        if message.get("type") == "http.request":
            chunk = message.get("body", b"")
            if isinstance(chunk, bytes) and chunk and len(preview) < preview_limit:
                remaining = preview_limit - len(preview)
                preview.extend(chunk[:remaining])
        return cast(dict[str, Any], message)

    return Request(request.scope, receive), preview


def _body_preview(value: bytes | None) -> str | None:
    """Return bounded text preview for encrypted artifact storage."""

    if not value:
        return None
    preview = value[:MAX_CAPTURED_BODY_BYTES]
    return preview.decode("utf-8", errors="replace")


def _resolve_vault_capture_config() -> tuple[str | None, str | None]:
    """Load vault capture config without dropping the lightweight span on failure."""

    try:
        vault_dir = telemetry_vault_dir()
        vault_key = telemetry_vault_key()
    except Exception:
        logger.debug("Request telemetry vault configuration failed", exc_info=True)
        return None, None
    if not vault_dir or not vault_key:
        return None, None
    return str(vault_dir), str(vault_key)


async def request_telemetry_middleware(request: Request, call_next: Any) -> Response:
    """Record lightweight request spans and rare encrypted capture pointers."""

    start = time.perf_counter()
    cloned_request, request_preview = _clone_request_with_preview_buffer(request)
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
            route_label = _normalized_route_label(route_template)
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
            capture_requested = False
            if detector_hits:
                capture_requested = True
                capture_reasons.extend(f"detector:{hit}" for hit in detector_hits)

            if (
                not capture_requested
                and is_non_prod_environment()
                and telemetry_client_debug_full_enabled()
                and request.headers.get("X-Debug-Full") == "1"
            ):
                capture_requested = True
                capture_reasons.append("debug_header")

            if not capture_requested and sample_decision.capture_full:
                capture_requested = True
                capture_reasons.append("sampled")

            attributes: dict[str, Any] = {
                "http.method": request.method.upper(),
                "http.route": route_label,
                "http.status_code": status_code,
                "duration.ms": round((time.perf_counter() - start) * 1000, 3),
                "pp.req.fingerprint": fingerprint,
                "pp.req.query_key_count": len(request.query_params),
                "pp.sample.rate": sample_decision.rate,
                "pp.sample.digest_prefix": sample_decision.digest_prefix,
                "pp.tier": _extract_tier(request),
                "pp.flags": _feature_flags_from_request(request),
                "pp.detectors": list(detector_hits),
                "pp.full_capture_requested": capture_requested,
                "pp.client.platform": _normalized_platform_label(
                    request.headers.get("X-Client-Platform")
                ),
            }

            vault_dir, vault_key = (None, None)
            should_capture_full = False
            if capture_requested:
                vault_dir, vault_key = _resolve_vault_capture_config()
                if vault_dir and vault_key:
                    should_capture_full = reservoir.take()

            if should_capture_full and vault_dir and vault_key:
                response_body = getattr(response, "body", None)
                captured_request_body = bytes(request_preview)
                capture_payload = {
                    "request": {
                        "method": request.method.upper(),
                        "route": route_label,
                        "query_params": dict(request.query_params),
                        "headers": {
                            "content-type": _normalized_content_type(
                                request.headers.get("content-type")
                            ),
                            "x-client-platform": _normalized_platform_label(
                                request.headers.get("X-Client-Platform")
                            ),
                            "x-api-tier": _extract_tier(request),
                        },
                        "request_body": _body_preview(captured_request_body),
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
                try:
                    pointer = store_capture_artifact(
                        payload=capture_payload,
                        vault_dir=vault_dir,
                        encoded_key=vault_key,
                    )
                except Exception:
                    logger.debug("Request telemetry vault storage failed", exc_info=True)
                    attributes["pp.full_capture"] = False
                    attributes["pp.full_capture_reasons"] = [
                        *capture_reasons,
                        "vault_store_failed",
                    ]
                else:
                    attributes["pp.full_capture"] = True
                    attributes["pp.full_pointer_sha256"] = pointer.sha256
                    attributes["pp.full_capture_reasons"] = capture_reasons
            else:
                attributes["pp.full_capture"] = False
                if capture_reasons:
                    failure_reason = None
                    if capture_requested and (not vault_dir or not vault_key):
                        failure_reason = "vault_config_failed"
                    attributes["pp.full_capture_reasons"] = [
                        *capture_reasons,
                        *([failure_reason] if failure_reason else []),
                    ]

            recorder.record(
                RequestTelemetrySpan(
                    trace_id=uuid4().hex,
                    name=route_label,
                    attributes=attributes,
                )
            )
        except Exception:
            logger.debug("Request telemetry capture failed", exc_info=True)
        finally:
            if error is not None:
                logger.debug("Request failed after telemetry processing", exc_info=error)
