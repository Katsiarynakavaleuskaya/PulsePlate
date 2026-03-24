"""GenAI tracing helpers with deterministic, minimized metadata only.

RU: Хелперы GenAI tracing с детерминированными и минимизированными полями.
EN: GenAI tracing helpers with deterministic, minimized fields only.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
import hashlib
import hmac
import logging
import os
from typing import Any, Iterator
from uuid import uuid4

from app.telemetry.setup import get_tracer, require_observability_hmac_key, tracing_is_enabled

logger = logging.getLogger(__name__)

TRACER_NAME = "pulseplate.genai"
HTTP_TRACER_NAME = "pulseplate.http"
OPENINFERENCE_SPAN_KIND = "openinference.span.kind"
REQUEST_ID_ATTR = "pulseplate.request.id"
USER_TIER_ATTR = "pulseplate.user.tier"
ROUTE_ATTR = "http.route"
PROMPT_FINGERPRINT_ATTR = "pulseplate.prompt.fingerprint"
PROMPT_LENGTH_ATTR = "pulseplate.prompt.length"
COMPLETION_FINGERPRINT_ATTR = "pulseplate.completion.fingerprint"
COMPLETION_LENGTH_ATTR = "pulseplate.completion.length"

OPENINFERENCE_KIND_AGENT = "AGENT"
OPENINFERENCE_KIND_CHAIN = "CHAIN"
OPENINFERENCE_KIND_LLM = "LLM"
OPENINFERENCE_KIND_RETRIEVER = "RETRIEVER"
OPENINFERENCE_KIND_TOOL = "TOOL"

_REQUEST_ID: ContextVar[str | None] = ContextVar("pulseplate_request_id", default=None)

_ALLOWED_ATTRS: frozenset[str] = frozenset(
    {
        "gen_ai.provider.name",
        "gen_ai.request.model",
        "gen_ai.request.temperature",
        "gen_ai.request.top_k",
        "gen_ai.response.model",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "http.request.method",
        OPENINFERENCE_SPAN_KIND,
        REQUEST_ID_ATTR,
        USER_TIER_ATTR,
        ROUTE_ATTR,
        PROMPT_FINGERPRINT_ATTR,
        PROMPT_LENGTH_ATTR,
        COMPLETION_FINGERPRINT_ATTR,
        COMPLETION_LENGTH_ATTR,
        "pulseplate.feature_flags.cbt_agent",
        "pulseplate.feature_flags.creative_research_pilot",
        "pulseplate.feature_flags.insight",
        "pulseplate.feature_flags.philosophy_linguistic",
        "pulseplate.feature_flags.philosophy_phase12",
        "pulseplate.feature_flags.philosophy_pragmatic",
        "pulseplate.feature_flags.philosophy_router",
        "pulseplate.feature_flags.philosophy_validation",
        "pulseplate.feature_flags.rag",
        "pulseplate.feature_flags.rag_recursive",
        "pulseplate.feature_flags.rag_vector",
        "pulseplate.rag.agent_id",
        "pulseplate.rag.hops",
        "pulseplate.retrieval.max_chunks",
        "pulseplate.route_type",
        "pulseplate.tool.kind",
        "pulseplate.tool.name",
    }
)

_ALLOWED_EVENT_ATTRS: frozenset[str] = frozenset(
    {
        "role",
        "pulseplate.prompt.fingerprint",
        "pulseplate.prompt.length",
        "pulseplate.completion.fingerprint",
        "pulseplate.completion.length",
    }
)

_ALLOWED_EVENT_NAMES: frozenset[str] = frozenset(
    {"pulseplate.gen_ai.prompt", "pulseplate.gen_ai.completion"}
)


class _NullSpan:
    """No-op span proxy used when tracing is disabled or backend fails."""

    def set_attribute(self, _key: str, _value: Any) -> None:
        return None

    def add_event(self, _name: str, _attributes: dict[str, Any] | None = None) -> None:
        return None

    def update_name(self, _name: str) -> None:
        return None

    def record_exception(self, _exception: BaseException) -> None:
        return None


NULL_SPAN = _NullSpan()


def _span_kind(kind: str) -> Any:
    from opentelemetry.trace import SpanKind

    return getattr(SpanKind, kind)


def _hmac_key_available() -> bool:
    return bool((os.getenv("PULSE_OBS_HMAC_KEY") or "").strip())


def _sanitize_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in attrs.items():
        if key not in _ALLOWED_ATTRS:
            continue
        if value is None:
            continue
        safe[key] = value
    return safe


def _sanitize_event_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in attrs.items():
        if key not in _ALLOWED_EVENT_ATTRS:
            continue
        if value is None:
            continue
        safe[key] = value
    return safe


def _estimate_token_count(text: str) -> int:
    """Use a deterministic, low-cost token estimate for current providers."""

    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _resolve_model_name(provider_name: str) -> str:
    normalized = provider_name.strip().lower()
    env_mapping = {
        "perplexity": ("PERPLEXITY_MODEL", "sonar"),
        "ollama": ("OLLAMA_MODEL", "llama3.1:8b"),
        "stub": ("LLM_STUB_MODEL", "stub"),
        "pico": ("PICO_MODEL", "pico"),
    }
    env_name, default = env_mapping.get(normalized, ("", provider_name))
    if env_name:
        return (os.getenv(env_name) or "").strip() or default
    return provider_name


def _fingerprint_text(text: str) -> str:
    key = require_observability_hmac_key().encode("utf-8")
    return hmac.new(key, text.encode("utf-8"), hashlib.sha256).hexdigest()


def new_request_id() -> str:
    """Generate a deterministic-format request id."""

    return uuid4().hex


def bind_request_id(request_id: str | None) -> Token[str | None]:
    """Bind request id to current context."""

    return _REQUEST_ID.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Reset request id context."""

    _REQUEST_ID.reset(token)


def current_request_id() -> str:
    """Return current request id or generate a local fallback."""

    return _REQUEST_ID.get() or new_request_id()


def _safe_set_attribute(span: Any, key: str, value: Any) -> None:
    """Best-effort wrapper for span attribute writes."""

    try:
        span.set_attribute(key, value)
    except Exception:
        logger.debug("Span attribute application failed for key=%s", key, exc_info=True)


def _safe_add_event(span: Any, name: str, attributes: dict[str, Any]) -> None:
    """Best-effort wrapper for span event writes."""

    try:
        span.add_event(name, attributes)
    except Exception:
        logger.debug("Span event emission failed for name=%s", name, exc_info=True)


def set_attributes(span: Any, **attrs: Any) -> None:
    """Apply only allowlisted attributes to a span."""

    for key, value in _sanitize_attrs(attrs).items():
        _safe_set_attribute(span, key, value)


def set_prompt_fingerprint(span: Any, prompt_text: str) -> None:
    """Attach prompt fingerprint and length to a span."""

    if not tracing_is_enabled() or not _hmac_key_available():
        return
    set_attributes(
        span,
        **{
            PROMPT_FINGERPRINT_ATTR: _fingerprint_text(prompt_text),
            PROMPT_LENGTH_ATTR: len(prompt_text),
        },
    )


def set_completion_fingerprint(span: Any, completion_text: str) -> None:
    """Attach completion fingerprint and length to a span."""

    if not tracing_is_enabled() or not _hmac_key_available():
        return
    set_attributes(
        span,
        **{
            COMPLETION_FINGERPRINT_ATTR: _fingerprint_text(completion_text),
            COMPLETION_LENGTH_ATTR: len(completion_text),
        },
    )


def add_prompt_event(span: Any, prompt_text: str, *, role: str) -> None:
    """Emit a fingerprint-only prompt event."""

    if not tracing_is_enabled() or not _hmac_key_available():
        return
    name = "pulseplate.gen_ai.prompt"
    if name not in _ALLOWED_EVENT_NAMES:
        return
    _safe_add_event(
        span,
        name,
        _sanitize_event_attrs(
            {
                "role": role,
                PROMPT_FINGERPRINT_ATTR: _fingerprint_text(prompt_text),
                PROMPT_LENGTH_ATTR: len(prompt_text),
            }
        ),
    )


def add_completion_event(span: Any, completion_text: str) -> None:
    """Emit a fingerprint-only completion event."""

    if not tracing_is_enabled() or not _hmac_key_available():
        return
    name = "pulseplate.gen_ai.completion"
    if name not in _ALLOWED_EVENT_NAMES:
        return
    _safe_add_event(
        span,
        name,
        _sanitize_event_attrs(
            {
                COMPLETION_FINGERPRINT_ATTR: _fingerprint_text(completion_text),
                COMPLETION_LENGTH_ATTR: len(completion_text),
            }
        ),
    )


@contextmanager
def safe_span(
    name: str,
    *,
    tracer_name: str,
    kind: str,
    attrs: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Open a tracing span or yield a no-op span on backend failure."""

    try:
        tracer = get_tracer(tracer_name)
        span_cm = tracer.start_as_current_span(name, kind=_span_kind(kind))
    except Exception:
        logger.debug("Tracing backend failed for span=%s", name, exc_info=True)
        yield NULL_SPAN
        return

    try:
        span = span_cm.__enter__()
    except Exception:
        logger.debug("Tracing backend failed while entering span=%s", name, exc_info=True)
        yield NULL_SPAN
        return

    try:
        try:
            set_attributes(span, **(attrs or {}))
        except Exception:
            logger.debug("Span attribute application failed for span=%s", name, exc_info=True)
        yield span
    except BaseException as exc:
        try:
            suppress = bool(span_cm.__exit__(type(exc), exc, exc.__traceback__))
        except Exception:
            logger.debug("Tracing backend failed while closing span=%s", name, exc_info=True)
            suppress = False
        if not suppress:
            raise
    else:
        try:
            span_cm.__exit__(None, None, None)
        except Exception:
            logger.debug("Tracing backend failed while closing span=%s", name, exc_info=True)


@contextmanager
def request_span(method: str, request_id: str) -> Iterator[Any]:
    """Create a best-effort request/root span."""

    token = bind_request_id(request_id)
    try:
        with safe_span(
            "http request",
            tracer_name=HTTP_TRACER_NAME,
            kind="SERVER",
            attrs={REQUEST_ID_ATTR: request_id, "http.request.method": method},
        ) as span:
            yield span
    finally:
        reset_request_id(token)


@contextmanager
def chain_span(
    name: str,
    *,
    user_tier: str,
    route: str,
    feature_flags: dict[str, bool],
    route_type: str | None = None,
) -> Iterator[Any]:
    """Create a CHAIN span for the main insight path."""

    attrs: dict[str, Any] = {
        OPENINFERENCE_SPAN_KIND: OPENINFERENCE_KIND_CHAIN,
        REQUEST_ID_ATTR: current_request_id(),
        USER_TIER_ATTR: user_tier,
        ROUTE_ATTR: route,
    }
    if route_type:
        attrs["pulseplate.route_type"] = route_type
    for key, value in feature_flags.items():
        attrs[f"pulseplate.feature_flags.{key}"] = value
    with safe_span(name, tracer_name=TRACER_NAME, kind="INTERNAL", attrs=attrs) as span:
        yield span


@contextmanager
def agent_span(
    name: str,
    *,
    user_tier: str,
    route: str,
    feature_flags: dict[str, bool],
) -> Iterator[Any]:
    """Create an AGENT span for CBT-like orchestrated requests."""

    attrs: dict[str, Any] = {
        OPENINFERENCE_SPAN_KIND: OPENINFERENCE_KIND_AGENT,
        REQUEST_ID_ATTR: current_request_id(),
        USER_TIER_ATTR: user_tier,
        ROUTE_ATTR: route,
    }
    for key, value in feature_flags.items():
        attrs[f"pulseplate.feature_flags.{key}"] = value
    with safe_span(name, tracer_name=TRACER_NAME, kind="INTERNAL", attrs=attrs) as span:
        yield span


@contextmanager
def retrieval_span(
    *,
    user_tier: str,
    route: str,
    max_chunks: int,
    agent_id: str | None = None,
) -> Iterator[Any]:
    """Create a retrieval span with deterministic metadata only."""

    attrs: dict[str, Any] = {
        OPENINFERENCE_SPAN_KIND: OPENINFERENCE_KIND_RETRIEVER,
        REQUEST_ID_ATTR: current_request_id(),
        USER_TIER_ATTR: user_tier,
        ROUTE_ATTR: route,
        "pulseplate.retrieval.max_chunks": max_chunks,
    }
    if agent_id:
        attrs["pulseplate.rag.agent_id"] = agent_id
    with safe_span("retrieval query", tracer_name=TRACER_NAME, kind="CLIENT", attrs=attrs) as span:
        yield span


@contextmanager
def llm_span(
    *,
    provider_name: str,
    user_tier: str,
    route: str,
    prompt_text: str,
) -> Iterator[Any]:
    """Create an LLM span with estimated usage and fingerprint-only payload metadata."""

    model_name = _resolve_model_name(provider_name)
    attrs = {
        OPENINFERENCE_SPAN_KIND: OPENINFERENCE_KIND_LLM,
        REQUEST_ID_ATTR: current_request_id(),
        USER_TIER_ATTR: user_tier,
        ROUTE_ATTR: route,
        "gen_ai.provider.name": provider_name,
        "gen_ai.request.model": model_name,
        "gen_ai.response.model": model_name,
        "gen_ai.usage.input_tokens": _estimate_token_count(prompt_text),
    }
    with safe_span(
        f"inference {model_name}",
        tracer_name=TRACER_NAME,
        kind="CLIENT",
        attrs=attrs,
    ) as span:
        set_prompt_fingerprint(span, prompt_text)
        add_prompt_event(span, prompt_text, role="user")
        yield span


def finalize_llm_span(span: Any, completion_text: str) -> None:
    """Attach completion metadata to an existing LLM span."""

    set_attributes(
        span,
        **{"gen_ai.usage.output_tokens": _estimate_token_count(completion_text)},
    )
    set_completion_fingerprint(span, completion_text)
    add_completion_event(span, completion_text)


@contextmanager
def tool_span(
    *,
    name: str,
    tool_kind: str,
    user_tier: str,
    route: str,
) -> Iterator[Any]:
    """Create a TOOL span for future instrumented tool calls."""

    with safe_span(
        f"tool {name}",
        tracer_name=TRACER_NAME,
        kind="INTERNAL",
        attrs={
            OPENINFERENCE_SPAN_KIND: OPENINFERENCE_KIND_TOOL,
            REQUEST_ID_ATTR: current_request_id(),
            USER_TIER_ATTR: user_tier,
            ROUTE_ATTR: route,
            "pulseplate.tool.name": name,
            "pulseplate.tool.kind": tool_kind,
        },
    ) as span:
        yield span


__all__ = [
    "COMPLETION_FINGERPRINT_ATTR",
    "COMPLETION_LENGTH_ATTR",
    "NULL_SPAN",
    "OPENINFERENCE_KIND_AGENT",
    "OPENINFERENCE_KIND_CHAIN",
    "OPENINFERENCE_KIND_LLM",
    "OPENINFERENCE_KIND_RETRIEVER",
    "OPENINFERENCE_KIND_TOOL",
    "OPENINFERENCE_SPAN_KIND",
    "PROMPT_FINGERPRINT_ATTR",
    "PROMPT_LENGTH_ATTR",
    "REQUEST_ID_ATTR",
    "ROUTE_ATTR",
    "USER_TIER_ATTR",
    "add_completion_event",
    "add_prompt_event",
    "agent_span",
    "bind_request_id",
    "chain_span",
    "current_request_id",
    "finalize_llm_span",
    "llm_span",
    "new_request_id",
    "request_span",
    "reset_request_id",
    "retrieval_span",
    "safe_span",
    "set_attributes",
    "tool_span",
]
