#!/usr/bin/env python3
"""Opt-in local collection of final FitChef distortion answers with a hard send budget.

Run only with a frozen private synthetic manifest and configured environment.
This module has no import-time provider call. Partial runs remain private and
must not be restarted for better answers.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from collections import Counter
from contextlib import ExitStack
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import inspect
import json
import logging
import math
import os
from pathlib import Path
import re
import stat
import ssl
import sys
import time
from typing import Any, cast
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from openai import APIConnectionError, AsyncOpenAI, OpenAI
from sqlalchemy import select

from app.middleware.api_tiers import SubscriptionTier, get_subscription_tier
from app.routers import fitchef_structured
from app.schemas.fitchef import (
    FitChefDistortionSimulatorInput,
    FitChefDistortionSimulatorTaskEnvelope,
)
from app.security.agent_input_guard import require_safe_ai_agent_input, scan_ai_agent_input
from app.middleware.api_tiers import TEST_KEY_PRO
from app.security.llm_monthly_quota import (
    VipLlmMonthlyUsage,
    _legacy_llm_key_fingerprint,
    llm_key_fingerprint,
    month_start_date_utc,
    require_llm_monthly_limit,
)
from app.services import fitchef_runtime
from core.i18n import Language
from core.insight import fitchef_companion
from core.db import session_scope
from core.rag import vector_rag
from core.rag.contracts import RAGChunk, RAGContext
from providers.perplexity import PerplexityProvider
from scripts.evals.evidence_relation_audit import (
    MAX_LINE_BYTES,
    _check_depth,
    _parent_fd,
    read_jsonl,
    write_report,
)
from scripts.evals.fitchef_claim_assurance_eval import (
    CASE_SCHEMA,
    FAMILIES,
    LANGUAGES,
    SPLITS,
    _canonical,
    _rubric_hash,
    read_private_jsonl,
    case_fingerprint,
    validate_cases,
)
from scripts.orchestration.creative_code_patch_workspace import run_git
from scripts.evals import fitchef_claim_assurance_eval

_MANIFEST_KEYS = frozenset(
    (
        "case_id",
        "canonical_id",
        "split",
        "family",
        "language",
        "context",
        "sources",
    )
)
_INPUT_SOURCE_KEYS = frozenset(("chunk_id", "file", "content", "score"))
_ATTEMPT_LIMIT = 32
_RESERVE_USD = 0.15
_MAX_HTTP_BODY_BYTES = 32768
_EXPECTED_ENDPOINT = "https://api.perplexity.ai"
_MODEL = "sonar"
_OCW_MODE = "ocw-nutrition-comparison"
_OCW_CASES = tuple(f"OCW-N{index:02d}" for index in range(1, 9))
_OCW_MODELS = {"sonar": "sonar", "sol": "openai/gpt-6.1-sol"}
_OCW_ENDPOINTS = {
    "sonar": "https://api.perplexity.ai/chat/completions",
    "sol": "https://api.perplexity.ai/v1/responses",
}
_OCW_OUTPUT_TOKENS = 2048
_OCW_RESPONSE_BYTES = 256 * 1024
_OCW_PACE_SECONDS = 6.1
_OCW_INPUT_FRAMING_MARGIN = 2048
_OCW_BILLED_INPUT_CEILING = _MAX_HTTP_BODY_BYTES + _OCW_INPUT_FRAMING_MARGIN
_OCW_PRICING_MAX_AGE = timedelta(hours=24)


class BudgetExhausted(RuntimeError):
    """The next physical request is not allowed to reach transport."""


class _PreproviderHighDistressBoundary(HTTPException):
    """Identify only the collector's own preprovider distress admission failure."""

    def __init__(self) -> None:
        """Represent the preprovider distress boundary with the canonical HTTP detail."""

        super().__init__(status_code=400, detail="fitchef_high_distress_boundary")


def _validate_ocw_request(request: httpx.Request, *, arm: str, prompt: str) -> None:
    if (
        arm not in _OCW_MODELS
        or request.method != "POST"
        or str(request.url) != _OCW_ENDPOINTS[arm]
        or len(request.content) > _MAX_HTTP_BODY_BYTES
    ):
        raise ValueError("ocw_request")
    try:
        body = json.loads(request.content)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError("ocw_request") from exc
    expected: dict[str, Any]
    if arm == "sonar":
        expected = {
            "model": "sonar",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "disable_search": True,
        }
    else:
        expected = {
            "model": "openai/gpt-6.1-sol",
            "input": prompt,
            "reasoning": {"effort": "low"},
            "max_output_tokens": 2048,
            "tools": [],
            "store": False,
        }
    # Canonical native JSON comparison preserves bool/int and rejects nonfinite
    # values; ordinary dict equality would alias store=False with numeric0.
    try:
        if type(body) is not dict or _canonical(body) != _canonical(expected):
            raise ValueError("ocw_request")
    except (ValueError, TypeError) as exc:
        raise ValueError("ocw_request") from exc


def _ocw_usage(value: object) -> tuple[dict[str, Any] | None, int | float | None]:
    if value is None:
        return None, None
    if type(value) is not dict:
        raise ValueError("ocw_usage")
    raw = cast(dict[str, Any], value)
    usage: dict[str, Any] = {}
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "input_tokens",
        "output_tokens",
        "total_tokens",
    ):
        if key in raw:
            if type(raw[key]) is not int or raw[key] < 0:
                raise ValueError("ocw_usage")
            usage[key] = raw[key]
    for field, total_field in (
        ("input_tokens_details", "input_tokens"),
        ("prompt_tokens_details", "prompt_tokens"),
    ):
        if field not in raw:
            continue
        detail = raw[field]
        if type(detail) is not dict:
            raise ValueError("ocw_usage")
        if "cached_tokens" in detail:
            cached = detail["cached_tokens"]
            total = usage.get(total_field)
            if (
                type(cached) is not int
                or type(total) is not int
                or not 0 <= cached <= min(total, _OCW_BILLED_INPUT_CEILING)
            ):
                raise ValueError("ocw_usage")
    cost = raw.get("cost")
    if cost is None:
        _canonical(raw)
        return copy.deepcopy(raw), None
    if type(cost) is not dict:
        raise ValueError("ocw_usage")
    amount = cost.get("total_cost")
    if type(amount) not in (int, float):
        raise ValueError("ocw_usage")
    numeric = cast(int | float, amount)
    if (type(numeric) is float and not math.isfinite(numeric)) or numeric < 0:
        raise ValueError("ocw_usage")
    # Retain returned cache/reasoning/currency detail as provider data. It is not
    # invoice truth; the caller separately admits a documented USD basis.
    _canonical(raw)
    return copy.deepcopy(raw), numeric


def _validate_ocw_manifest_rows(rows: list[object]) -> list[dict[str, Any]]:
    """Validate the existing finite eight-row input grammar before copying."""
    from scripts.evals.eval_validity_contract import EvalVariantRecord, validate_eval_variant_record

    if type(rows) is not list or len(rows) != 8:
        raise ValueError("ocw_manifest")
    admitted: list[dict[str, Any]] = []
    variants: set[str] = set()
    for index, raw in enumerate(rows):
        if type(raw) is not dict or set(raw) != set(EvalVariantRecord.__annotations__):
            raise ValueError("ocw_manifest")
        row = cast(dict[str, Any], raw)
        if (
            any(
                type(row[k]) is not str
                for k in (
                    "canonical_id",
                    "variant_id",
                    "variant_family",
                    "transform_type",
                    "expected_relation",
                )
            )
            or row["variant_id"] != _OCW_CASES[index] + "-canonical"
            or type(row["slice_tags"]) is not list
            or row["slice_tags"] != ["synthetic", "development", "fitchef", "ocw", "language:ru"]
        ):
            raise ValueError("ocw_manifest")
        if (
            row["canonical_id"] != _OCW_CASES[index]
            or row["variant_id"] in variants
            or not row["variant_id"]
            or row["variant_family"] != "canonical"
            or row["transform_type"] != "identity"
            or row["expected_relation"] != "same_decision"
            or not {"synthetic", "development", "fitchef", "ocw", "language:ru"}.issubset(
                row["slice_tags"]
            )
        ):
            raise ValueError("ocw_manifest")
        variants.add(row["variant_id"])
        inner = row["input_payload"]
        if type(inner) is not dict or set(inner) != {"query", "language", "sources"}:
            raise ValueError("ocw_manifest")
        query, sources = inner["query"], inner["sources"]
        if (
            type(query) is not str
            or not query.strip()
            or len(query) > 2000
            or inner["language"] != "ru"
            or type(inner["language"]) is not str
            or type(sources) is not list
            or len(sources) > 5
            or not scan_ai_agent_input(query).is_safe
        ):
            raise ValueError("ocw_manifest")
        ids: set[str] = set()
        for source in sources:
            if type(source) is not dict or set(source) != _INPUT_SOURCE_KEYS:
                raise ValueError("ocw_manifest")
            if any(
                type(source[k]) is not str or not source[k].strip() or len(source[k]) > 4000
                for k in ("chunk_id", "file", "content")
            ):
                raise ValueError("ocw_manifest")
            if any(
                not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", source[k]) for k in ("chunk_id", "file")
            ):
                raise ValueError("ocw_manifest")
            if (
                source["chunk_id"] in ids
                or type(source["score"]) not in (int, float)
                or (type(source["score"]) is float and not math.isfinite(source["score"]))
                or not 0 <= source["score"] <= 1
                or not scan_ai_agent_input(source["content"]).is_safe
            ):
                raise ValueError("ocw_manifest")
            ids.add(source["chunk_id"])
        admitted.append(copy.deepcopy(cast(dict[str, Any], validate_eval_variant_record(row))))
    return admitted


def validate_ocw_manifest(rows: list[object]) -> list[dict[str, Any]]:
    """Bind the complete generation projection to the current tracked fixture."""
    admitted = _validate_ocw_manifest_rows(rows)
    fixture = (
        Path(__file__).resolve().parents[2] / "tests/fixtures/ocw/fitchef_nutrition_cases.v1.jsonl"
    )
    canonical = _validate_ocw_manifest_rows(read_jsonl(fixture))
    if any(
        _canonical(row["input_payload"]) != _canonical(expected["input_payload"])
        for row, expected in zip(admitted, canonical)
    ):
        raise ValueError("ocw_manifest")
    return admitted


def _ocw_prompt(inner: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    safe_query = require_safe_ai_agent_input(inner["query"])
    occurrences: list[dict[str, Any]] = []
    context: list[str] = []
    for source in inner["sources"]:
        content = (
            fitchef_runtime.redact_pii_from_text(
                fitchef_runtime.sanitize_rag_markdown(source["content"])
            )
            or ""
        )
        occurrences.append(
            {
                **source,
                "content": content,
                "preview": fitchef_runtime.sanitize_chunk_preview(content) or "",
            }
        )
        if content.strip():
            context.append(f"[{source['file']}]\n{content}")
    return fitchef_runtime.build_mascot_prompt(safe_query, "\n\n".join(context)), occurrences


async def _serialize_ocw_request(prompt: str, arm: str) -> bytes:
    """Exercise the real native SDK against a separate local mock only."""
    from providers.perplexity_agent import PerplexityAgentProvider, _AgentAsyncOpenAI

    captured: list[bytes] = []

    async def response(request: httpx.Request) -> httpx.Response:
        _validate_ocw_request(request, arm=arm, prompt=prompt)
        captured.append(request.content)
        if arm == "sonar":
            payload: dict[str, Any] = {
                "id": "serialization-only",
                "object": "chat.completion",
                "created": 0,
                "model": "sonar",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "serialization only"},
                    }
                ],
            }
        else:
            payload = {
                "id": "serialization-only",
                "object": "response",
                "created_at": 0,
                "model": _OCW_MODELS["sol"],
                "status": "completed",
                "error": None,
                "incomplete_details": None,
                "output": [
                    {
                        "type": "message",
                        "id": "serialization-message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": "serialization only", "annotations": []}
                        ],
                    }
                ],
            }
        return httpx.Response(200, json=payload)

    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        serialization_label = "ocw-serialization-only"
        sdk_identity_default = ""
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(response), follow_redirects=False, trust_env=False
        ) as transport:
            if arm == "sonar":
                async with _AgentAsyncOpenAI(
                    base_url=_EXPECTED_ENDPOINT,
                    api_key=serialization_label,
                    organization=sdk_identity_default,
                    project=sdk_identity_default,
                    webhook_secret=sdk_identity_default,
                    http_client=transport,
                    max_retries=0,
                ) as sdk:
                    await sdk.chat.completions.create(
                        model="sonar",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=2048,
                        extra_body={"disable_search": True},
                    )
            else:
                provider = PerplexityAgentProvider(
                    api_key=serialization_label,
                    model=_OCW_MODELS["sol"],
                    reasoning_effort="low",
                    http_client=transport,
                )
                await provider.generate(prompt)
    except APIConnectionError as error:
        # The separate local transport reports encoded-body rejection through
        # the native SDK's connection wrapper. Keep preflight's stable local
        # failure before any live provider/client or budget allocation.
        raise ValueError("ocw_preflight") from error
    finally:
        logging.disable(previous_logging)
    if len(captured) != 1:
        raise ValueError("ocw_preflight")
    return captured[0]


def validate_ocw_pricing(
    rows: list[object], *, now: datetime | None = None
) -> dict[str, dict[str, Any]]:
    """Check the recorded applicable all-charge bound; metadata is not price authentication."""
    keys = {
        "schema_version",
        "arm",
        "requested_model",
        "max_request_bytes",
        "max_output_tokens",
        "max_input_usd_per_million",
        "max_output_usd_per_million",
        "extra_fees_usd_per_attempt",
        "max_billed_input_tokens",
        "input_rate_includes_cache_write",
        "billed_input_bound_verified",
        "returned_cost_currency_basis",
        "cost_currency_source_url",
        "output_includes_reasoning",
        "all_charges_included",
        "verified_at",
        "source_url",
    }
    if type(rows) is not list or len(rows) != 2:
        raise ValueError("ocw_pricing")
    result: dict[str, dict[str, Any]] = {}
    current = datetime.now(timezone.utc) if now is None else now
    if current.utcoffset() is None:
        raise ValueError("ocw_pricing")
    for raw in rows:
        if type(raw) is not dict or set(raw) != keys:
            raise ValueError("ocw_pricing")
        row = cast(dict[str, Any], raw)
        arm = row["arm"]
        if (
            type(arm) is not str
            or arm not in _OCW_MODELS
            or arm in result
            or row["schema_version"] != "ocw_pricing_evidence.v1"
            or row["requested_model"] != _OCW_MODELS[arm]
            or type(row["max_request_bytes"]) is not int
            or row["max_request_bytes"] != 32768
            or type(row["max_output_tokens"]) is not int
            or row["max_output_tokens"] != 2048
            or type(row["max_billed_input_tokens"]) is not int
            or row["max_billed_input_tokens"] != _OCW_BILLED_INPUT_CEILING
            or row["input_rate_includes_cache_write"] is not True
            or row["billed_input_bound_verified"] is not True
            or type(row["returned_cost_currency_basis"]) is not str
            or row["returned_cost_currency_basis"] not in {"documented_usd", "unknown"}
            or (
                row["returned_cost_currency_basis"] == "documented_usd"
                and (
                    type(row["cost_currency_source_url"]) is not str
                    or not row["cost_currency_source_url"].startswith("https://docs.perplexity.ai/")
                )
            )
            or (
                row["returned_cost_currency_basis"] == "unknown"
                and row["cost_currency_source_url"] is not None
            )
            or row["output_includes_reasoning"] is not True
            or row["all_charges_included"] is not True
            or type(row["source_url"]) is not str
            or not row["source_url"].startswith("https://docs.perplexity.ai/")
            or type(row["verified_at"]) is not str
        ):
            raise ValueError("ocw_pricing")
        try:
            verified = datetime.fromisoformat(row["verified_at"].replace("Z", "+00:00"))
            offset = verified.utcoffset()
            if (
                offset is None
                or offset.total_seconds() != 0
                or verified > current
                or current - verified > _OCW_PRICING_MAX_AGE
            ):
                raise ValueError("ocw_pricing")
        except ValueError as exc:
            raise ValueError("ocw_pricing") from exc
        for field in (
            "max_input_usd_per_million",
            "max_output_usd_per_million",
            "extra_fees_usd_per_attempt",
        ):
            if (
                type(row[field]) not in (int, float)
                or (type(row[field]) is float and not math.isfinite(row[field]))
                or row[field] < 0
            ):
                raise ValueError("ocw_pricing")
        upper = (
            Decimal(str(row["max_input_usd_per_million"])) * _OCW_BILLED_INPUT_CEILING / 1_000_000
            + Decimal(str(row["max_output_usd_per_million"])) * 2048 / 1_000_000
            + Decimal(str(row["extra_fees_usd_per_attempt"]))
        )
        if upper > Decimal("0.15"):
            raise ValueError("ocw_pricing")
        result[arm] = {**copy.deepcopy(row), "upper_usd_per_attempt": str(upper)}
    return result


def ocw_request_preflight(manifest: list[object], pricing: list[object]) -> list[dict[str, Any]]:
    """Return only mock-serialization bounds; no quota, reservation or measured answer."""
    rows, prices = validate_ocw_manifest(manifest), validate_ocw_pricing(pricing)
    result: list[dict[str, Any]] = []
    for row in rows:
        prompt, _sources = _ocw_prompt(row["input_payload"])
        for arm in _OCW_MODELS:
            body = asyncio.run(_serialize_ocw_request(prompt, arm))
            result.append(
                {
                    "case_id": row["canonical_id"],
                    "arm": arm,
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "request_bytes": len(body),
                    "upper_usd_per_attempt": prices[arm]["upper_usd_per_attempt"],
                    "observation_kind": "local_mock_serialization_only",
                    "reserved_cents": 0,
                }
            )
    return result


class AttemptLedger:
    """Durable private reservation immediately before each HTTPX send."""

    def __init__(self, directory: Path, *, comparison: bool = False) -> None:
        self.directory = directory
        self._lock = asyncio.Lock()
        self.attempts = 0
        self.exhausted = False
        self.transport_rejection = False
        self.reported_overrun_usd: int | float | None = None
        if type(comparison) is not bool:
            raise ValueError("ocw_budget")
        self.comparison = comparison
        self.arm_attempts = {"sonar": 0, "sol": 0}
        self.case_attempts: dict[tuple[str, str], int] = {}
        self.arm: str | None = None
        self.case_id: str | None = None
        self.prompt: str | None = None
        self.terminal_reason: str | None = None
        self.retryable = False
        self.http_observations: list[dict[str, Any]] = []
        self._comparison_secrets: tuple[str, ...] = ()
        self.pricing_valid_until: datetime | None = None
        self.cost_currency_basis = {"sonar": "unknown", "sol": "unknown"}
        self.reservation_publications = 0
        self.reservation_publication_uncertain = False
        self._published_attempts: set[int] = set()
        self._invocation_start_attempt = 0
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("unsafe_budget_directory")
        info = directory.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("unsafe_budget_directory")
        for path in directory.iterdir():
            if path.name.startswith("attempt-"):
                raise ValueError("nonempty_attempt_ledger")

    async def reserve(self, request: httpx.Request) -> None:
        """HTTPX request event hook, including OpenAI SDK and Tenacity retries."""
        if self.comparison:
            await self._reserve_ocw(request)
            return
        if (
            request.url.scheme != "https"
            or request.url.host != "api.perplexity.ai"
            or request.url.path != "/chat/completions"
        ):
            self.transport_rejection = True
            raise ValueError("unexpected_provider_destination")
        if len(request.content) > _MAX_HTTP_BODY_BYTES:
            self.transport_rejection = True
            raise ValueError("request_body_limit")
        async with self._lock:
            if self.reported_overrun_usd is not None:
                raise BudgetExhausted("reported_cost_overrun")
            if self.attempts >= _ATTEMPT_LIMIT:
                self.exhausted = True
                raise BudgetExhausted("physical_attempt_limit")
            next_attempt = self.attempts + 1
            record = {
                "schema_version": "fitchef_http_reservation.v1",
                "attempt": next_attempt,
                "reserved_usd": _RESERVE_USD,
                "cost_status": "unknown",
            }
            write_report(
                self.directory / f"attempt-{next_attempt:04d}.json",
                _canonical(record) + b"\n",
            )
            self.attempts = next_attempt

    def bind_case(self, arm: str, case_id: str, prompt: str) -> None:
        """Bind the one serial admitted comparison invocation to physical requests."""
        if (
            not self.comparison
            or arm not in _OCW_MODELS
            or case_id not in _OCW_CASES
            or type(prompt) is not str
            or not prompt.strip()
            or len(prompt) > _MAX_HTTP_BODY_BYTES
            or len(prompt.encode("utf-8")) > _MAX_HTTP_BODY_BYTES
        ):
            raise ValueError("ocw_budget")
        self.arm, self.case_id, self.prompt = arm, case_id, prompt
        self.retryable = False
        self._invocation_start_attempt = self.attempts

    def require_secret_free(self, data: bytes) -> None:
        """Never retain credentials, even if a provider reflects a header value."""
        for value in self._comparison_secrets:
            if value and (value.encode("utf-8") in data or _canonical(value)[1:-1] in data):
                self.terminal_reason = "credential_reflection"
                raise ValueError("ocw_private_material")

    def native_failure(self, error: BaseException) -> None:
        """Retain a published reservation's uncertain outcome without replacing its cause."""
        from openai import APIConnectionError, APIStatusError, APITimeoutError

        if self.terminal_reason is not None or self.arm != "sonar":
            self.retryable = False
        elif isinstance(error, APIStatusError):
            self.retryable = error.status_code in {408, 429, 500, 502, 503, 504}
        elif isinstance(error, (APIConnectionError, APITimeoutError)):
            self.retryable = isinstance(
                error.__cause__,
                (
                    httpx.ConnectError,
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.WriteTimeout,
                    httpx.ReadError,
                    httpx.WriteError,
                    httpx.RemoteProtocolError,
                ),
            )
            # Inspect only native exception objects, never their prose. TLS
            # certificate/configuration errors are terminal even when HTTPX
            # wraps them as a nominal connection failure.
            pending: list[BaseException] = [error]
            seen: set[int] = set()
            while pending and len(seen) < 16:
                cause = pending.pop()
                if id(cause) in seen:
                    continue
                seen.add(id(cause))
                if isinstance(cause, (ssl.SSLError, ssl.CertificateError, ValueError)):
                    self.retryable = False
                for child in (cause.__cause__, cause.__context__):
                    if child is not None:
                        pending.append(child)
            if pending:
                self.retryable = False
        else:
            self.retryable = False
        if not self.retryable:
            self.terminal_reason = self.terminal_reason or "provider_failure_terminal"
        # HTTP outcomes are already immutable. A transport-only failure still
        # retains its type and uncertain cost, without SDK text or request data.
        path = self.directory / f"attempt-result-{self.attempts:04d}.json"
        if (
            self.attempts in self._published_attempts
            and self.attempts > self._invocation_start_attempt
            and not any(item["attempt"] == self.attempts for item in self.http_observations)
        ):
            record = {
                "attempt": self.attempts,
                "arm": self.arm,
                "case_id": self.case_id,
                "requested_model": _OCW_MODELS[self.arm or ""],
                "endpoint": _OCW_ENDPOINTS[self.arm or ""],
                "failure_type": type(error).__name__,
                "retryable": self.retryable,
                "cost_usd": None,
                "cost_status": "unknown",
            }
            self.http_observations.append(record)
            try:
                write_report(path, _canonical(record) + b"\n")
            except BaseException as publication_error:
                self.terminal_reason = "outcome_publication_uncertain"
                self.retryable = False
                error.add_note("ocw_outcome_publication_failed:" + type(publication_error).__name__)

    async def _reserve_ocw(self, request: httpx.Request) -> None:
        if self.arm is None or self.case_id is None or self.prompt is None:
            raise ValueError("ocw_request")
        if (
            self.pricing_valid_until is not None
            and datetime.now(timezone.utc) > self.pricing_valid_until
        ):
            self.terminal_reason = "pricing_not_current"
            raise ValueError("ocw_pricing")
        try:
            _validate_ocw_request(request, arm=self.arm, prompt=self.prompt)
        except ValueError:
            self.terminal_reason = "request_admission"
            raise
        # Strip only the individual final request, after native SDK/client merge.
        for name in ("OpenAI-Organization", "OpenAI-Project", "Cookie"):
            request.headers.pop(name, None)
        async with self._lock:
            if self.terminal_reason is not None or self.reported_overrun_usd is not None:
                raise BudgetExhausted("ocw_terminal_failure")
            limit = 24 if self.arm == "sonar" else 8
            case_limit = 3 if self.arm == "sonar" else 1
            key = (self.arm, self.case_id)
            if (
                self.attempts >= 32
                or self.arm_attempts[self.arm] >= limit
                or self.case_attempts.get(key, 0) >= case_limit
            ):
                self.exhausted = True
                self.terminal_reason = "physical_attempt_limit"
                raise BudgetExhausted("physical_attempt_limit")
            # Count conservatively even if publication reports uncertain durability.
            self.attempts += 1
            self.arm_attempts[self.arm] += 1
            self.case_attempts[key] = self.case_attempts.get(key, 0) + 1
            self.retryable = False
            record = {
                "schema_version": "ocw_http_reservation.v1",
                "attempt": self.attempts,
                "arm": self.arm,
                "case_id": self.case_id,
                "reserved_cents": 15,
                "cost_status": "unknown",
                "endpoint": _OCW_ENDPOINTS[self.arm],
                "requested_model": _OCW_MODELS[self.arm],
                "request_sha256": hashlib.sha256(request.content).hexdigest(),
                "prompt_sha256": hashlib.sha256(self.prompt.encode("utf-8")).hexdigest(),
            }
            try:
                write_report(
                    self.directory / f"attempt-{self.attempts:04d}.json", _canonical(record) + b"\n"
                )
            except BaseException:
                self.reservation_publication_uncertain = True
                self.terminal_reason = "reservation_publication_uncertain"
                self.retryable = False
                raise
            self.reservation_publications += 1
            self._published_attempts.add(self.attempts)

    async def observe_http(self, response: httpx.Response) -> None:
        """Retain bounded native outcome facts without request headers or SDK errors."""
        native: dict[str, Any] = {
            "attempt": self.attempts,
            "arm": self.arm,
            "case_id": self.case_id,
            "requested_model": _OCW_MODELS[self.arm or ""],
            "endpoint": _OCW_ENDPOINTS[self.arm or ""],
            "status_code": response.status_code,
            "returned_model": None,
            "usage": None,
            "cost_usd": None,
            "cost_status": "unknown",
            "raw_assistant_text": None,
        }
        chunks: list[bytes] = []
        total = 0
        try:
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > _OCW_RESPONSE_BYTES:
                    self.terminal_reason = "response_limit"
                    raise ValueError("ocw_response_limit")
                chunks.append(chunk)
        except BaseException as error:
            self.terminal_reason = self.terminal_reason or "response_read_failed"
            self.retryable = False
            native["response_failure_type"] = type(error).__name__
            try:
                self._retain_ocw_http_outcome(native)
            except BaseException as publication_error:
                error.add_note("ocw_outcome_publication_failed:" + type(publication_error).__name__)
            try:
                await response.aclose()
            except BaseException as cleanup_error:
                error.add_note("ocw_response_cleanup_failed:" + type(cleanup_error).__name__)
            raise
        # The existing SDK will read this SAME response after the observational hook.
        response._content = b"".join(chunks)
        payload: dict[str, Any] | None = None
        try:
            decoded = response.json()
            if type(decoded) is not dict:
                raise ValueError("ocw_response_shape")
            payload = decoded
        except (ValueError, TypeError, RecursionError):
            # Only native transient Sonar status can admit a retry of an
            # undecodable error body. Accounting admission remains terminal.
            if not (self.arm == "sonar" and response.status_code in {408, 429, 500, 502, 503, 504}):
                self.terminal_reason = self.terminal_reason or "response_admission"
            native["raw_error_body_sha256"] = (
                "sha256:" + hashlib.sha256(response.content).hexdigest()
            )
            native["raw_error_body_bytes"] = len(response.content)
            try:
                self.require_secret_free(response.content)
            except ValueError:
                self.terminal_reason = self.terminal_reason or "credential_reflection"
                self.retryable = False
                native["raw_error_body_status"] = "omitted_credential_reflection"
            else:
                native["raw_error_body_base64"] = base64.b64encode(response.content).decode("ascii")
                native["raw_error_body_status"] = "retained_invalid_json"
                if len(_canonical(native)) > MAX_LINE_BYTES:
                    native.pop("raw_error_body_base64")
                    native["raw_error_body_status"] = "omitted_outcome_limit"
                    self.terminal_reason = self.terminal_reason or "response_limit"
        try:
            if payload is not None:
                try:
                    # JSON decoding accepts nonfinite extensions. Admit canonical
                    # metadata before copying it into the durable native envelope.
                    _canonical(payload)
                except (ValueError, TypeError, RecursionError):
                    native["raw_error_body_sha256"] = (
                        "sha256:" + hashlib.sha256(response.content).hexdigest()
                    )
                    native["raw_error_body_bytes"] = len(response.content)
                    native["raw_error_body_status"] = "omitted_noncanonical_metadata"
                    raise
                native["returned_model"] = (
                    payload.get("model") if type(payload.get("model")) is str else None
                )
                raw_usage = payload.get("usage")
                # Retain bounded observed bytes before semantic accounting admission.
                # Rejected cache/token/cost metadata remains native failure evidence.
                _check_depth(raw_usage)
                native["usage"] = copy.deepcopy(raw_usage)
                native["provider_declared_cost"] = (
                    copy.deepcopy(raw_usage.get("cost")) if type(raw_usage) is dict else None
                )
                native["usage"], declared_amount = _ocw_usage(raw_usage)
                usage = native["usage"]
                if usage is not None:
                    ceilings = {
                        "prompt_tokens": _OCW_BILLED_INPUT_CEILING,
                        "input_tokens": _OCW_BILLED_INPUT_CEILING,
                        "completion_tokens": _OCW_OUTPUT_TOKENS,
                        "output_tokens": _OCW_OUTPUT_TOKENS,
                        "total_tokens": _OCW_BILLED_INPUT_CEILING + _OCW_OUTPUT_TOKENS,
                    }
                    if any(usage.get(field, 0) > ceiling for field, ceiling in ceilings.items()):
                        self.terminal_reason = "reported_token_overrun"
                    for field, total_field in (
                        ("output_tokens_details", "output_tokens"),
                        ("completion_tokens_details", "completion_tokens"),
                    ):
                        detail = usage.get(field)
                        if type(detail) is dict and "reasoning_tokens" in detail:
                            count = detail["reasoning_tokens"]
                            if (
                                type(count) is not int
                                or count < 0
                                or count
                                > min(
                                    usage.get(total_field, _OCW_OUTPUT_TOKENS), _OCW_OUTPUT_TOKENS
                                )
                            ):
                                self.terminal_reason = "reported_token_overrun"
                declared = (
                    payload.get("usage", {}).get("cost")
                    if type(payload.get("usage")) is dict
                    else None
                )
                native["provider_declared_cost"] = declared
                currency = declared.get("currency") if type(declared) is dict else None
                known_usd = currency == "USD" or (
                    currency is None
                    and self.cost_currency_basis.get(self.arm or "") == "documented_usd"
                )
                native["cost_usd"] = declared_amount if known_usd else None
                native["cost_basis"] = (
                    "provider_declaration_usd" if known_usd else "unknown_currency"
                )
                native["invoice_verified"] = False
                if currency is not None and currency != "USD":
                    self.terminal_reason = "provider_cost_currency_changed"
                if native["cost_usd"] is not None:
                    native["cost_status"] = "known"
                if self.arm == "sonar":
                    choices = payload.get("choices")
                    if type(choices) is list and choices and type(choices[0]) is dict:
                        message = choices[0].get("message")
                        if type(message) is dict and type(message.get("content")) is str:
                            native["raw_assistant_text"] = message["content"]
                else:
                    output = payload.get("output")
                    if type(output) is list:
                        texts = [
                            part["text"]
                            for item in output
                            if type(item) is dict
                            and item.get("type") == "message"
                            and item.get("role") == "assistant"
                            for part in item.get("content", [])
                            if type(part) is dict
                            and part.get("type") == "output_text"
                            and type(part.get("text")) is str
                        ]
                        native["raw_assistant_text"] = "".join(texts) if texts else None
        except (ValueError, TypeError, KeyError, RecursionError):
            self.terminal_reason = self.terminal_reason or "response_admission"
        if native["cost_usd"] is not None and native["cost_usd"] > _RESERVE_USD:
            self.reported_overrun_usd = native["cost_usd"]
            self.terminal_reason = "reported_cost_overrun"
        if response.status_code not in (200, 201):
            self.retryable = response.status_code in {408, 429, 500, 502, 503, 504}
            if not self.retryable:
                self.terminal_reason = "provider_http_terminal"
        self._retain_ocw_http_outcome(native)
        if self.terminal_reason is not None:
            self.retryable = False
            raise ValueError("ocw_terminal_failure")

    def _retain_ocw_http_outcome(self, native: dict[str, Any]) -> None:
        """Keep observed header/body admission facts even when the body is rejected."""
        self.http_observations.append(native)
        content = _canonical(native)
        self.require_secret_free(content)
        if len(content) > MAX_LINE_BYTES:
            # The response bound does not bound duplicated usage/cost metadata
            # inside this envelope. Keep a readable terminal omission receipt.
            summary: dict[str, Any] = {
                key: native[key]
                for key in (
                    "attempt",
                    "arm",
                    "case_id",
                    "requested_model",
                    "endpoint",
                    "status_code",
                )
                if key in native
            }
            summary.update(
                returned_model=None,
                usage=None,
                cost_usd=None,
                cost_status="unknown",
                raw_assistant_text=None,
                outcome_material_status="omitted_native_line_limit",
                outcome_content_bytes=len(content),
                outcome_material_sha256="sha256:" + hashlib.sha256(content).hexdigest(),
            )
            native.clear()
            native.update(summary)
            self.terminal_reason = self.terminal_reason or "outcome_limit"
            self.retryable = False
            content = _canonical(native)
        encoded = content + b"\n"
        try:
            write_report(self.directory / f"attempt-result-{self.attempts:04d}.json", encoded)
        except BaseException:
            self.terminal_reason = "outcome_publication_uncertain"
            self.retryable = False
            raise


def validate_manifest(rows: list[object], *, require_full: bool = True) -> list[dict[str, Any]]:
    """Reject unbounded or ambiguous synthetic scenario sets before network."""
    if not rows or len(rows) > 24 or (require_full and len(rows) != 24):
        raise ValueError("manifest_count")
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    canonical_ids: set[str] = set()
    for raw in rows:
        if type(raw) is not dict or set(raw) != _MANIFEST_KEYS:
            raise ValueError("manifest_shape")
        case = cast(dict[str, Any], raw)
        for key in ("case_id", "canonical_id"):
            if type(case[key]) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", case[key]):
                raise ValueError("manifest_id")
        if case["case_id"] in ids or case["canonical_id"] in canonical_ids:
            raise ValueError("duplicate_manifest_id")
        ids.add(case["case_id"])
        canonical_ids.add(case["canonical_id"])
        for key, choices in (("split", SPLITS), ("family", FAMILIES), ("language", LANGUAGES)):
            if type(case[key]) is not str or case[key] not in choices:
                raise ValueError(f"manifest_{key}")
        context = case["context"]
        if type(context) is not dict or set(context) != {
            "situation",
            "automatic_thought",
            "emotion",
            "goal",
        }:
            raise ValueError("manifest_context")
        for key in ("situation", "automatic_thought", "emotion"):
            if (
                type(context[key]) is not str
                or not context[key].strip()
                or len(context[key]) > 2000
            ):
                raise ValueError("manifest_context")
        if context["goal"] is not None and (
            type(context["goal"]) is not str
            or not context["goal"].strip()
            or len(context["goal"]) > 2000
        ):
            raise ValueError("manifest_context")
        if any(
            value is not None and not scan_ai_agent_input(value).is_safe
            for value in context.values()
        ):
            raise ValueError("unsafe_context_instruction")
        sources = case["sources"]
        if type(sources) is not list or len(sources) > 5:
            raise ValueError("manifest_sources")
        for source in sources:
            if type(source) is not dict or set(source) != _INPUT_SOURCE_KEYS:
                raise ValueError("manifest_source")
            for key in ("chunk_id", "file", "content"):
                if type(source[key]) is not str or not source[key] or len(source[key]) > 4000:
                    raise ValueError("manifest_source")
            if (
                type(source["score"]) not in (int, float)
                or not 0 <= source["score"] <= 1
                or not math.isfinite(source["score"])
            ):
                raise ValueError("manifest_score")
            if not scan_ai_agent_input(source["content"]).is_safe:
                raise ValueError("unsafe_source_instruction")
        _preflight_request_size(case)
        result.append(copy.deepcopy(case))
    if require_full:
        split = Counter(case["split"] for case in result)
        family = Counter(case["family"] for case in result)
        language = Counter(case["language"] for case in result)
        holdout = Counter(case["family"] for case in result if case["split"] == "holdout")
        holdout_languages = {case["language"] for case in result if case["split"] == "holdout"}
        if (
            split != {"development": 16, "holdout": 8}
            or any(family[name] != 4 for name in FAMILIES)
            or any(language[name] != 8 for name in LANGUAGES)
            or holdout_languages != set(LANGUAGES)
            or holdout
            != {
                "causal_overclaim": 2,
                "absent_evidence": 2,
                "cautious_explanation": 1,
                "contradicting_source": 1,
                "irrelevant_citation": 1,
                "context_time_mismatch": 1,
            }
        ):
            raise ValueError("manifest_distribution")
    return result


def _preflight_request_size(scenario: dict[str, Any]) -> None:
    """Serialize the admitted prompt through the actual SDK without a send."""
    context = scenario["context"]
    occurrences: list[fitchef_runtime.FitChefSourceOccurrenceV1] = []
    for source in scenario["sources"]:
        content = (
            fitchef_runtime.redact_pii_from_text(
                fitchef_runtime.sanitize_rag_markdown(source["content"])
            )
            or ""
        )
        if content.strip():
            occurrences.append(
                fitchef_runtime.FitChefSourceOccurrenceV1(
                    ordinal=len(occurrences),
                    chunk_id=source["chunk_id"],
                    file=source["file"],
                    content=content,
                    preview=fitchef_runtime.sanitize_chunk_preview(content) or "",
                    score=source["score"],
                )
            )
    snapshot = fitchef_runtime.freeze_fitchef_source_snapshot(tuple(occurrences))
    prompt = fitchef_companion.build_distortion_simulator_prompt(
        context["situation"],
        context["automatic_thought"],
        context["emotion"],
        context["goal"],
        fitchef_runtime.build_fitchef_source_prompt_context(snapshot),
        lang=scenario["language"],
    )

    def transport(request: httpx.Request) -> httpx.Response:
        if len(request.content) > _MAX_HTTP_BODY_BYTES:
            raise ValueError("request_body_limit")
        return httpx.Response(
            200,
            json={
                "id": "preflight",
                "object": "chat.completion",
                "created": 0,
                "model": _MODEL,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": ""},
                    }
                ],
            },
        )

    previous_logging_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with httpx.Client(transport=httpx.MockTransport(transport)) as client:
            with OpenAI(
                base_url=_EXPECTED_ENDPOINT,
                api_key=TEST_KEY_PRO,
                http_client=client,
                max_retries=0,
            ) as sdk:
                sdk.chat.completions.create(
                    model=_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    extra_body={"web_search_options": {"disable_search": True}},
                )
    finally:
        logging.disable(previous_logging_disable)


def validate_pricing_evidence(rows: list[object]) -> None:
    """Require a recorded primary-source upper bound for this exact request cap."""
    if len(rows) != 1 or type(rows[0]) is not dict:
        raise ValueError("pricing_shape")
    row = cast(dict[str, object], rows[0])
    if set(row) != {
        "schema_version",
        "model",
        "max_request_bytes",
        "max_tokens",
        "max_usd_per_attempt",
        "source_url",
        "verified_at",
    }:
        raise ValueError("pricing_shape")
    max_cost = row["max_usd_per_attempt"]
    if not isinstance(max_cost, (int, float)) or isinstance(max_cost, bool):
        raise ValueError("pricing_unverified")
    if (
        row["schema_version"] != "fitchef_pricing_evidence.v1"
        or row["model"] != _MODEL
        or type(row["max_request_bytes"]) is not int
        or row["max_request_bytes"] != _MAX_HTTP_BODY_BYTES
        or type(row["max_tokens"]) is not int
        or row["max_tokens"] != 1024
        or not 0 <= max_cost <= _RESERVE_USD
        or not math.isfinite(max_cost)
        or type(row["source_url"]) is not str
        or not row["source_url"].startswith("https://docs.perplexity.ai/")
        or type(row["verified_at"]) is not str
        or not row["verified_at"]
    ):
        raise ValueError("pricing_unverified")


def _code_sha() -> str:
    observed = run_git(
        ["status", "--porcelain", "--untracked-files=all"], cwd=Path.cwd(), check=False
    )
    if observed.returncode != 0:
        raise ValueError("git_status_unavailable")
    if observed.stdout.strip():
        raise ValueError("uncommitted_code_state")
    observed = run_git(["rev-parse", "HEAD"], cwd=Path.cwd(), check=False)
    if observed.returncode != 0:
        raise ValueError("git_head_unavailable")
    sha = observed.stdout.strip()
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("code_sha")
    return sha


def _code_hashes() -> dict[str, str]:
    adapter_file = sys.modules[PerplexityProvider.__module__].__file__
    if not isinstance(adapter_file, str):
        raise ValueError("perplexity_adapter_file_unavailable")
    modules = {
        "collector": Path(__file__),
        "evaluator": Path(fitchef_claim_assurance_eval.__file__),
        "fitchef_runtime": Path(fitchef_runtime.__file__),
        "fitchef_companion": Path(fitchef_companion.__file__),
        "perplexity_adapter": Path(adapter_file),
    }
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in modules.items()}


def _private_parent(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError("unsafe_private_path")
    parent, name = _parent_fd(path)
    try:
        parent_info = os.fstat(parent)
        if parent_info.st_uid != os.getuid() or parent_info.st_mode & 0o077:
            raise ValueError("unsafe_private_path")
        try:
            target = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        if (
            not stat.S_ISREG(target.st_mode)
            or target.st_nlink != 1
            or target.st_uid != os.getuid()
            or target.st_mode & 0o077
        ):
            raise ValueError("unsafe_private_path")
    except OSError as exc:
        raise ValueError("unsafe_private_path") from exc
    finally:
        os.close(parent)


def validate_live_environment(fitchef_key: str) -> None:
    """Admit only isolated synthetic PRO state through the normal local gates."""
    if os.getenv("APP_ENV") != "development" or os.getenv(
        "SUBSCRIPTION_DB_ENABLED", "false"
    ).lower() not in {"false", "0", "off", "no"}:
        raise ValueError("nonisolated_runtime_environment")
    if not fitchef_key.startswith("noos-eval-") or fitchef_key not in {
        part.strip() for part in os.getenv("PRO_API_KEYS", "").split(",")
    }:
        raise ValueError("synthetic_pro_key_required")
    if get_subscription_tier(fitchef_key) is not SubscriptionTier.PRO:
        raise ValueError("pro_tier_unavailable")
    if require_llm_monthly_limit("PRO") < 24:
        raise ValueError("insufficient_synthetic_quota")
    if not os.getenv("SERVER_SALT") or not os.getenv("AGENT_CONTROL_AUDIT_SIGNING_KEY"):
        raise ValueError("missing_local_audit_secret")
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith("sqlite:////"):
        raise ValueError("private_sqlite_required")
    _private_parent(Path(db_url.removeprefix("sqlite:///")))
    audit_log = os.getenv("AGENT_CONTROL_AUDIT_LOG_PATH", "")
    if not audit_log:
        raise ValueError("private_audit_path_required")
    _private_parent(Path(audit_log))
    with session_scope() as session:
        used = session.scalar(
            select(VipLlmMonthlyUsage.used_requests).where(
                VipLlmMonthlyUsage.key_fingerprint == llm_key_fingerprint(fitchef_key, tier="PRO"),
                VipLlmMonthlyUsage.month_start_date == month_start_date_utc(),
            )
        )
    if used is not None and (type(used) is not int or used < 0):
        raise ValueError("invalid_synthetic_quota_usage")
    if require_llm_monthly_limit("PRO") - (used if used is not None else 0) < 24:
        raise ValueError("insufficient_synthetic_quota")
    if not fitchef_structured._is_fitchef_structured_enabled():
        raise ValueError("fitchef_feature_disabled")
    if fitchef_structured._require_fitchef_structured_mode() != "auto-safe":
        raise ValueError("fitchef_mode_not_auto_safe")


def _validate_output_directory(
    directory: Path, *, generated_names: list[str] | None = None
) -> None:
    """Private output must be outside Git or fully ignored before any send."""
    parent, _ = _parent_fd(directory / "collection-status.json")
    try:
        info = os.fstat(parent)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("unsafe_output_directory")
    finally:
        os.close(parent)
    observed = run_git(["rev-parse", "--show-toplevel"], cwd=Path.cwd(), check=False)
    if observed.returncode != 0:
        raise ValueError("git_root_unavailable")
    root = observed.stdout.strip()
    try:
        relative = directory.absolute().relative_to(Path(root))
    except ValueError:
        return
    names = (
        generated_names
        if generated_names is not None
        else (
            [f"attempt-{index:04d}.json" for index in range(1, _ATTEMPT_LIMIT + 1)]
            + [f"case-{index:02d}.jsonl" for index in range(1, 25)]
            + ["cases.jsonl", "collection-status.json"]
        )
    )
    # The immutable publisher also creates random staging names. Prove this
    # directory's current Git ignore state alongside every finite final name;
    # final-name patterns alone do not cover the publisher's staging paths.
    paths = [str(relative)] + [str(relative / name) for name in names]
    observed = run_git(
        [
            "check-ignore",
            "--no-index",
            "-z",
            "--stdin",
        ],
        cwd=Path(root),
        check=False,
        input_text="".join(path + "\0" for path in paths),
    )
    if observed.returncode == 1 or (
        observed.returncode == 0 and set(observed.stdout.rstrip("\0").split("\0")) != set(paths)
    ):
        raise ValueError("nonignored_output_directory")
    if observed.returncode != 0:
        raise ValueError("output_ignore_unavailable")


def _admitted_task(
    context: dict[str, Any], key: str, lang: Language
) -> FitChefDistortionSimulatorTaskEnvelope:
    """Validate collector admission and preserve the scenario locale before execution."""

    if not fitchef_structured._is_fitchef_structured_enabled():
        raise ValueError("fitchef_feature_disabled")
    mode = fitchef_structured._require_fitchef_structured_mode()
    if mode != "auto-safe":
        raise ValueError("fitchef_mode_not_auto_safe")
    if fitchef_companion.has_high_distress_boundary(
        context["situation"], context["automatic_thought"], context["emotion"], context["goal"]
    ):
        raise _PreproviderHighDistressBoundary()
    return FitChefDistortionSimulatorTaskEnvelope(
        agent_id="fitchef-agent",
        mode=mode,
        task_type="distortion_simulator",
        input=FitChefDistortionSimulatorInput(
            safe_situation=require_safe_ai_agent_input(context["situation"]),
            safe_automatic_thought=require_safe_ai_agent_input(context["automatic_thought"]),
            safe_emotion=require_safe_ai_agent_input(context["emotion"]),
            safe_goal=(
                require_safe_ai_agent_input(context["goal"])
                if context["goal"] is not None and context["goal"].strip()
                else None
            ),
            lang=lang,
            api_key=key,
            endpoint="/api/v1/pro/fitchef/explain",
            method="POST",
        ),
    )


async def _collect_one(
    scenario: dict[str, Any],
    *,
    key: str,
    provider: PerplexityProvider,
    ledger: AttemptLedger,
    code_sha: str,
    code_hashes: dict[str, str],
    rubric_sha256: str,
) -> dict[str, Any]:
    """Run the real task with controlled retrieval and observational wrappers."""
    context = scenario["context"]
    rag_chunks = [RAGChunk(**source) for source in scenario["sources"]]
    raw_response: str | None = None
    frozen_snapshot: Any = None
    fallback_called = False
    retrieval_completed = False
    usage: dict[str, Any] | None = None
    provider_content: str | None = None
    actual_cost: int | float | None = None
    starting_attempts = ledger.attempts
    real_create = provider.client.chat.completions.create
    real_generate = provider.generate
    real_freeze = fitchef_runtime.freeze_fitchef_source_snapshot
    real_fallback = fitchef_companion._fallback_balanced_reframe

    async def bounded_create(*args: Any, **kwargs: Any) -> Any:
        nonlocal usage, provider_content, actual_cost
        if "max_tokens" in kwargs or "extra_body" in kwargs:
            raise ValueError("provider_parameter_collision")
        kwargs["max_tokens"] = 1024
        kwargs["extra_body"] = {"web_search_options": {"disable_search": True}}
        response = await real_create(*args, **kwargs)
        content = response.choices[0].message.content
        if type(content) is str:
            provider_content = content
        raw_usage = getattr(response, "usage", None)
        if raw_usage is not None:
            dumped = raw_usage.model_dump(mode="json")
            if type(dumped) is dict:
                usage = {
                    key: dumped[key]
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                    if type(dumped.get(key)) is int and dumped[key] >= 0
                }
                extra = dumped.get("cost")
                if extra is not None:
                    if type(extra) is not dict:
                        raise ValueError("invalid_provider_cost")
                    amount = extra.get("total_cost")
                    if (
                        not isinstance(amount, (int, float))
                        or isinstance(amount, bool)
                        or amount < 0
                        or (type(amount) is float and not math.isfinite(amount))
                    ):
                        raise ValueError("invalid_provider_cost")
                    actual_cost = amount
                    if actual_cost > _RESERVE_USD:
                        ledger.reported_overrun_usd = actual_cost
                        raise ValueError("reported_cost_overrun")
        return response

    async def observed_generate(prompt: str) -> str:
        nonlocal raw_response
        result = await real_generate(prompt)
        if not isinstance(result, str):
            raise ValueError("provider_response_type")
        raw_response = result
        return result

    def observed_freeze(occurrences: Any) -> Any:
        nonlocal frozen_snapshot
        frozen_snapshot = real_freeze(occurrences)
        return frozen_snapshot

    def observed_fallback(
        *, automatic_thought: str, goal: str | None, lang: Language = "en"
    ) -> str:
        """Record fallback use while preserving its locale and text result contract."""

        nonlocal fallback_called
        fallback_called = True
        result = real_fallback(automatic_thought=automatic_thought, goal=goal, lang=lang)
        if not isinstance(result, str):
            raise ValueError("fallback_response_type")
        return result

    def controlled_retrieval(query: str, **kwargs: Any) -> RAGContext:
        nonlocal retrieval_completed
        if kwargs.get("agent_id") != "cbt-agent" or kwargs.get("user_tier") not in ("PRO", "VIP"):
            raise ValueError("unexpected_retrieval_context")
        retrieval_completed = True
        return RAGContext(
            query=query,
            refined_queries=[],
            chunks=rag_chunks,
            confidence=0.5 if rag_chunks else 0.0,
            hops=1,
            latency_ms=0,
            agent_id="cbt-agent",
            user_tier=kwargs["user_tier"],
        )

    task = _admitted_task(context, key, scenario["language"])
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(provider.client.chat.completions, "create", bounded_create)
        )
        stack.enter_context(patch.object(provider, "generate", observed_generate))
        stack.enter_context(
            patch.object(fitchef_runtime, "_require_llm_provider", lambda: provider)
        )
        stack.enter_context(
            patch.object(fitchef_runtime, "freeze_fitchef_source_snapshot", observed_freeze)
        )
        stack.enter_context(
            patch.object(fitchef_companion, "_fallback_balanced_reframe", observed_fallback)
        )
        stack.enter_context(
            patch.object(vector_rag, "retrieve_context_structured", controlled_retrieval)
        )
        previous_logging_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        try:
            result = await fitchef_runtime.run_distortion_simulator_task(task)
        finally:
            logging.disable(previous_logging_disable)
    if frozen_snapshot is None or raw_response is None or not retrieval_completed:
        raise ValueError("capture_incomplete")
    if "rag_retrieval_failed" in result.warnings:
        raise ValueError("controlled_retrieval_degraded")
    if frozen_snapshot.source_snapshot_fingerprint is None:
        raise ValueError("source_fingerprint_unavailable")
    expected_sources: list[tuple[str, str, str, float]] = []
    for chunk in rag_chunks[:5]:
        sanitized = fitchef_runtime.sanitize_rag_markdown(chunk.content)
        content = fitchef_runtime.redact_pii_from_text(sanitized) or ""
        if content.strip():
            expected_sources.append((chunk.chunk_id, chunk.file, content, chunk.score))
    observed_sources = [
        (item.chunk_id, item.file, item.content, item.score) for item in frozen_snapshot.occurrences
    ]
    if observed_sources != expected_sources:
        raise ValueError("controlled_source_mismatch")
    public_result = result.model_dump(mode="json")
    public_result.pop("claim_evidence_assessment", None)
    answer = result.balanced_reframe
    provider_reframe = ""
    if provider_content is not None:
        try:
            payload = fitchef_companion._extract_json_payload(provider_content)
            provider_reframe = fitchef_companion._normalize_structured_string(
                payload.get("balanced_reframe")
            )
        except ValueError:
            pass
    if fallback_called:
        origin = "fallback"
    elif provider_content is not None and provider_reframe == answer:
        origin = "provider"
    else:
        origin = "unknown"
    occurrences = [
        {
            "ordinal": item.ordinal,
            "chunk_id": item.chunk_id,
            "file": item.file,
            "content": item.content,
            "preview": item.preview,
            "score": item.score,
        }
        for item in frozen_snapshot.occurrences
    ]
    attempts = ledger.attempts - starting_attempts
    case: dict[str, Any] = {
        "schema_version": CASE_SCHEMA,
        "case_id": scenario["case_id"],
        "canonical_id": scenario["canonical_id"],
        "split": scenario["split"],
        "family": scenario["family"],
        "language": scenario["language"],
        "input_provenance": "provider_run",
        "field_origin": origin,
        "answer": answer,
        "context": context,
        "sources": occurrences,
        "source_snapshot_fingerprint": frozen_snapshot.source_snapshot_fingerprint,
        "raw_response": provider_content if provider_content is not None else raw_response,
        "result": public_result,
        "run": {
            "id": f"noos-1b-{code_sha[:12]}",
            "code_sha": code_sha,
            "code_hashes": code_hashes,
            "model": _MODEL,
            "parameters": {"max_tokens": 1024, "web_search_options": {"disable_search": True}},
            "attempts": attempts,
            "reserved_usd": round(attempts * _RESERVE_USD, 2),
            "cost_usd": actual_cost if attempts == 1 else None,
            "cost_status": "known" if actual_cost is not None and attempts == 1 else "unknown",
            "usage": usage,
        },
        "material_fingerprint": "",
    }
    case["material_fingerprint"] = case_fingerprint(case, rubric_sha256)
    return case


async def collect(
    manifest: list[dict[str, Any]],
    *,
    output_dir: Path,
    rubric_sha256: str,
    fitchef_key: str,
    perplexity_key: str,
) -> None:
    """Collect bounded cases and preserve completion or failure evidence under the attempt ledger."""

    manifest = validate_manifest(cast(list[object], manifest))
    if not fitchef_key or not perplexity_key:
        raise ValueError("missing_provider_or_fitchef_key")
    validate_live_environment(fitchef_key)
    if os.getenv("LLM_PROVIDER") not in (None, "perplexity"):
        raise ValueError("provider_selection_conflict")
    _validate_output_directory(output_dir)
    ledger = AttemptLedger(output_dir)
    if any(output_dir.iterdir()):
        raise ValueError("output_directory_not_empty")
    code_sha = _code_sha()
    code_hashes = _code_hashes()
    manifest_fingerprint = hashlib.sha256(_canonical(manifest)).hexdigest()
    transport = httpx.AsyncClient(event_hooks={"request": [ledger.reserve]}, follow_redirects=False)
    provider = PerplexityProvider(
        endpoint=_EXPECTED_ENDPOINT,
        model=_MODEL,
        api_key=perplexity_key,
    )
    await provider.client.close()
    # Evaluation-only SDK configuration; PerplexityProvider.generate remains the caller.
    provider.client = AsyncOpenAI(
        base_url=_EXPECTED_ENDPOINT,
        api_key=perplexity_key,
        http_client=transport,
        max_retries=2,
    )
    cases: list[dict[str, Any]] = []
    try:
        for index, scenario in enumerate(manifest, start=1):
            if _code_sha() != code_sha or _code_hashes() != code_hashes:
                raise ValueError("code_changed_during_collection")
            case = await _collect_one(
                scenario,
                key=fitchef_key,
                provider=provider,
                ledger=ledger,
                code_sha=code_sha,
                code_hashes=code_hashes,
                rubric_sha256=rubric_sha256,
            )
            write_report(output_dir / f"case-{index:02d}.jsonl", _canonical(case) + b"\n")
            cases.append(case)
        validate_cases(cast(list[object], cases), rubric_sha256)
        write_report(
            output_dir / "cases.jsonl", b"".join(_canonical(case) + b"\n" for case in cases)
        )
        complete = {
            "schema_version": "fitchef_collection_status.v1",
            "status": "complete",
            "failure_category": None,
            "manifest_fingerprint": manifest_fingerprint,
            "completed_ids": [case["case_id"] for case in cases],
            "missing_ids": [],
            "physical_attempts": ledger.attempts,
            "reserved_usd": round(ledger.attempts * _RESERVE_USD, 2),
            "reported_overrun_usd": None,
        }
        write_report(output_dir / "collection-status.json", _canonical(complete) + b"\n")
    except BaseException as exc:
        if ledger.reported_overrun_usd is not None:
            reason = "reported_cost_overrun"
        elif ledger.exhausted or isinstance(exc, BudgetExhausted):
            reason = "budget_exhausted"
        elif isinstance(exc, _PreproviderHighDistressBoundary):
            reason = "validation_failure"
        elif ledger.transport_rejection or isinstance(exc, ValueError):
            reason = "validation_failure"
        elif not isinstance(exc, Exception):
            reason = "interrupted"
        else:
            reason = "provider_or_runtime_failure"
        completed = [case["case_id"] for case in cases]
        receipt = {
            "schema_version": "fitchef_collection_status.v1",
            "status": "incomplete",
            "failure_category": reason,
            "manifest_fingerprint": manifest_fingerprint,
            "completed_ids": completed,
            "missing_ids": [
                case["case_id"] for case in manifest if case["case_id"] not in completed
            ],
            "physical_attempts": ledger.attempts,
            "reserved_usd": round(ledger.attempts * _RESERVE_USD, 2),
            "reported_overrun_usd": ledger.reported_overrun_usd,
        }
        write_report(output_dir / "collection-status.json", _canonical(receipt) + b"\n")
        raise
    finally:
        await provider.client.close()


def validate_ocw_environment(fitchef_key: str) -> None:
    """Require private synthetic VIP state; do not bypass native route admission."""
    if (
        os.getenv("APP_ENV") != "development"
        or os.getenv("SUBSCRIPTION_DB_ENABLED", "false").lower() not in {"false", "0", "off", "no"}
        or os.getenv("LLM_PROVIDER") != "perplexity"
        or os.getenv("PERPLEXITY_MODEL", "sonar") != "sonar"
        or os.getenv("PERPLEXITY_ENDPOINT", _EXPECTED_ENDPOINT) != _EXPECTED_ENDPOINT
    ):
        raise ValueError("ocw_environment")
    if (
        type(fitchef_key) is not str
        or not fitchef_key.startswith("ocw-eval-")
        or fitchef_key not in {item.strip() for item in os.getenv("VIP_API_KEYS", "").split(",")}
        or get_subscription_tier(fitchef_key) is not SubscriptionTier.VIP
    ):
        raise ValueError("ocw_synthetic_vip")
    if not os.getenv("SERVER_SALT") or not os.getenv("AGENT_CONTROL_AUDIT_SIGNING_KEY"):
        raise ValueError("ocw_audit_configuration")
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith("sqlite:////"):
        raise ValueError("ocw_private_sqlite")
    _private_parent(Path(db_url.removeprefix("sqlite:///")))
    audit = os.getenv("AGENT_CONTROL_AUDIT_LOG_PATH", "")
    if not audit:
        raise ValueError("ocw_audit_configuration")
    _private_parent(Path(audit))
    with session_scope() as session:
        counts = session.scalars(
            select(VipLlmMonthlyUsage.used_requests).where(
                VipLlmMonthlyUsage.key_fingerprint.in_(
                    (
                        llm_key_fingerprint(fitchef_key, tier="VIP"),
                        _legacy_llm_key_fingerprint(fitchef_key),
                    )
                ),
                VipLlmMonthlyUsage.month_start_date == month_start_date_utc(),
            )
        ).all()
    if any(type(used) is not int or used < 0 for used in counts):
        raise ValueError("ocw_quota")
    if require_llm_monthly_limit("VIP") - sum(counts) < 16:
        raise ValueError("ocw_quota")
    from app.routers import fitchef_insight
    from app.security.agent_control_plane import require_execution_mode
    from app.security import rate_limit

    if (
        not fitchef_insight._is_fitchef_mascot_enabled()
        or os.getenv("FITCHEF_MASCOT_EXECUTION_MODE") != "auto-safe"
    ):
        raise ValueError("ocw_feature_or_mode")
    require_execution_mode("auto-safe")
    if (
        os.getenv("RATE_LIMITING_IN_TESTS") != "true"
        or rate_limit.RATE_LIMIT_INSIGHT != "10/minute"
        or rate_limit.rate_limit_insight_value() != "10/minute"
        or rate_limit.limiter is None
        or rate_limit.limiter.enabled is not True
        or inspect.getclosurevars(fitchef_insight.fitchef_mascot_insight).nonlocals.get("self")
        is not rate_limit.limiter
    ):
        raise ValueError("ocw_active_limiter_required")


def _ocw_http_client(ledger: AttemptLedger) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        event_hooks={"request": [ledger.reserve], "response": [ledger.observe_http]},
        follow_redirects=False,
        trust_env=False,
        timeout=45.0,
    )


def _ocw_code_hashes() -> dict[str, str]:
    from providers import perplexity_agent
    from app.routers import fitchef_insight

    result = _code_hashes()
    for name, module in (
        ("perplexity_agent", perplexity_agent),
        ("mascot_router", fitchef_insight),
    ):
        source_file = module.__file__
        if type(source_file) is not str:
            raise ValueError("ocw_code_source")
        result[name] = hashlib.sha256(Path(source_file).read_bytes()).hexdigest()
    return result


def _ocw_observe_post(
    client: Any,
    scenario: dict[str, Any],
    *,
    arm: str,
    key: str,
    transport: httpx.AsyncClient,
    ledger: AttemptLedger,
    run: dict[str, Any],
) -> dict[str, Any]:
    """Observe one genuine canonical HTTP call; every wrapper delegates unchanged."""
    import llm
    from providers import perplexity_agent
    from tenacity import retry_if_exception, stop_after_attempt

    inner = scenario["input_payload"]
    expected_prompt, expected_sources = _ocw_prompt(inner)
    safe_query = require_safe_ai_agent_input(inner["query"])
    state: dict[str, Any] = {
        "sanitization": [],
        "redaction": [],
        "fallbacks": [],
        "extractions": [],
    }
    unused_clients: list[Any] = []
    provider_objects: list[Any] = []
    starting_attempts = ledger.attempts
    real_selector = fitchef_runtime._require_fitchef_llm_provider
    real_prompt = fitchef_runtime.build_mascot_prompt
    real_draft = fitchef_runtime.prepare_mascot_draft
    real_runtime = fitchef_runtime.run_mascot_insight_task
    real_sanitize = fitchef_runtime.sanitize_rag_markdown
    real_redact = fitchef_runtime.redact_pii_from_text
    real_fallback = fitchef_companion._fallback_draft
    real_extract = fitchef_companion._extract_action_items
    real_sonar_constructor = llm.PerplexityProvider
    real_agent_constructor = perplexity_agent.PerplexityAgentProvider

    def sonar_constructor(*args: Any, **kwargs: Any) -> Any:
        if args or kwargs.get("model") != "sonar" or kwargs.get("endpoint") != _EXPECTED_ENDPOINT:
            raise ValueError("ocw_provider_configuration")
        if not callable(real_sonar_constructor):
            raise ValueError("ocw_provider_configuration")
        provider: Any = real_sonar_constructor(**kwargs)
        unused_clients.append(provider.client)
        sdk_identity_default = ""
        provider.client = perplexity_agent._AgentAsyncOpenAI(
            api_key=kwargs["api_key"],
            base_url=_EXPECTED_ENDPOINT,
            organization=sdk_identity_default,
            project=sdk_identity_default,
            webhook_secret=sdk_identity_default,
            http_client=transport,
            max_retries=0,
            timeout=30.0,
        )
        original_create = provider.client.chat.completions.create

        async def bounded_create(*call_args: Any, **call_kwargs: Any) -> Any:
            if call_args or "max_tokens" in call_kwargs or "extra_body" in call_kwargs:
                ledger.terminal_reason = "provider_parameter_collision"
                raise ValueError("ocw_provider_configuration")
            try:
                return await original_create(
                    **call_kwargs, max_tokens=2048, extra_body={"disable_search": True}
                )
            except BaseException as error:
                ledger.native_failure(error)
                raise

        provider.client.chat.completions.create = bounded_create
        provider_objects.append(provider)
        return provider

    def agent_constructor(**kwargs: Any) -> Any:
        if (
            kwargs.get("model") != _OCW_MODELS["sol"]
            or kwargs.get("reasoning_effort") != "low"
            or "http_client" in kwargs
        ):
            raise ValueError("ocw_provider_configuration")
        provider = real_agent_constructor(**kwargs, http_client=transport)
        provider_objects.append(provider)
        return provider

    def selector(prompt: str) -> Any:
        if prompt != expected_prompt:
            raise ValueError("ocw_prompt_mismatch")
        provider: Any = real_selector(prompt)
        expected_type = PerplexityProvider if arm == "sonar" else real_agent_constructor
        if type(provider) is not expected_type or provider not in provider_objects:
            raise ValueError("ocw_provider_configuration")
        # This exact admitted instance exposes native decorator metadata and
        # instance-level observational replacement beyond ProviderBase typing.
        instrumented: Any = provider
        original_generate: Any = instrumented.generate
        bounded_generate = (
            original_generate.retry_with(
                retry=retry_if_exception(
                    lambda _error: ledger.retryable and ledger.terminal_reason is None
                ),
                stop=stop_after_attempt(3),
            )
            if arm == "sonar"
            else None
        )

        async def observed_generate(text: str) -> str:
            if text != state.get("prompt") or text != expected_prompt:
                raise ValueError("ocw_prompt_mismatch")
            ledger.bind_case(arm, scenario["canonical_id"], text)
            state["generation_prompt"] = text
            try:
                result = (
                    await bounded_generate(instrumented, text)
                    if bounded_generate is not None
                    else await original_generate(text)
                )
            except BaseException as error:
                ledger.native_failure(error)
                if ledger.terminal_reason is None:
                    ledger.terminal_reason = "provider_generation_failed"
                ledger.retryable = False
                raise
            if type(result) is not str or len(result.encode("utf-8")) > 32768:
                raise ValueError("ocw_generation_admission")
            state["generation_text"] = result
            return result

        instrumented.generate = observed_generate
        state["selector"] = {"requested_model": provider.model, "provider": provider.name}
        return provider

    def retrieval(query: str, **kwargs: Any) -> RAGContext:
        if (
            query != safe_query
            or kwargs.get("agent_id") != "fitchef-agent"
            or kwargs.get("user_tier") != "VIP"
            or kwargs.get("max_chunks") != 5
        ):
            raise ValueError("ocw_retrieval")
        state["retrieval_query"] = query
        return RAGContext(
            query=query,
            refined_queries=[],
            chunks=[RAGChunk(**source) for source in inner["sources"]],
            confidence=0.5 if inner["sources"] else 0.0,
            hops=1,
            latency_ms=0,
            agent_id="fitchef-agent",
            user_tier="VIP",
        )

    def sanitize(text: str) -> str:
        result: str = real_sanitize(text)
        state["sanitization"].append({"input": text, "output": result})
        return result

    def redact(text: str) -> Any:
        result = real_redact(text)
        state["redaction"].append({"input": text, "output": result})
        return result

    def prompt_builder(query: str, rag_context: str) -> str:
        result: str = real_prompt(query, rag_context)
        if query != safe_query or result != expected_prompt:
            raise ValueError("ocw_prompt_mismatch")
        state.update(prompt=result, builder_query=query, builder_context=rag_context)
        return result

    def fallback(**kwargs: Any) -> Any:
        result = real_fallback(**kwargs)
        state["fallbacks"].append(result)
        return result

    def extraction(*args: Any, **kwargs: Any) -> list[str]:
        result: list[str] = real_extract(*args, **kwargs)
        if type(result) is not list or any(type(item) is not str for item in result):
            raise ValueError("ocw_draft_mismatch")
        state["extractions"].append(result)
        return result

    def draft_builder(raw_text: str, *, query: str) -> Any:
        if raw_text != state.get("generation_text") or query != safe_query:
            raise ValueError("ocw_draft_mismatch")
        result = real_draft(raw_text, query=query)
        state["draft_object"] = result
        return result

    async def runtime(task: Any) -> Any:
        if (
            task.input.safe_query != safe_query
            or task.input.endpoint != "/api/v1/insight/fitchef"
            or task.input.method != "POST"
            or task.mode != "auto-safe"
        ):
            raise ValueError("ocw_runtime_input")
        result = await real_runtime(task)
        state["internal_result"] = result.model_dump(mode="json")
        return result

    with ExitStack() as stack:
        stack.enter_context(
            patch.dict(
                os.environ,
                {
                    "FITCHEF_AGENT_API_ENABLED": "false" if arm == "sonar" else "true",
                    "FITCHEF_AGENT_API_MODEL": _OCW_MODELS["sol"],
                    "FITCHEF_AGENT_API_REASONING_EFFORT": "low",
                },
            )
        )
        for owner, name, replacement in (
            (llm, "PerplexityProvider", sonar_constructor),
            (perplexity_agent, "PerplexityAgentProvider", agent_constructor),
            (fitchef_runtime, "_require_fitchef_llm_provider", selector),
            (vector_rag, "retrieve_context_structured", retrieval),
            (fitchef_runtime, "sanitize_rag_markdown", sanitize),
            (fitchef_runtime, "redact_pii_from_text", redact),
            (fitchef_runtime, "build_mascot_prompt", prompt_builder),
            (fitchef_runtime, "prepare_mascot_draft", draft_builder),
            (fitchef_runtime, "run_mascot_insight_task", runtime),
            (fitchef_companion, "_fallback_draft", fallback),
            (fitchef_companion, "_extract_action_items", extraction),
        ):
            stack.enter_context(patch.object(owner, name, replacement))
        previous_logging = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        try:
            response = client.post(
                "/api/v1/insight/fitchef",
                json={"query": inner["query"]},
                headers={"X-API-Key": key},
            )
            if not response.headers.get("content-type", "").startswith("application/json"):
                raise ValueError("ocw_http_envelope")
            body = response.json()
            if response.status_code != 200:
                raise ValueError("ocw_http_denied")
        finally:
            original_error = sys.exc_info()[1]
            logging.disable(previous_logging)
            for unused in unused_clients:
                try:
                    client.portal.call(unused.close)
                except BaseException as cleanup_error:
                    ledger.terminal_reason = ledger.terminal_reason or "provider_cleanup_failed"
                    ledger.retryable = False
                    if original_error is None:
                        raise
                    original_error.add_note(
                        "ocw_unused_client_cleanup_failed:" + type(cleanup_error).__name__
                    )
    required = {
        "prompt",
        "builder_query",
        "builder_context",
        "retrieval_query",
        "generation_prompt",
        "generation_text",
        "draft_object",
        "internal_result",
        "selector",
    }
    if not required.issubset(state) or state["prompt"] != state["generation_prompt"]:
        raise ValueError("ocw_capture_incomplete")
    if len(state["sanitization"]) != len(expected_sources) or len(state["redaction"]) != len(
        expected_sources
    ):
        raise ValueError("ocw_source_observation")
    for index, source in enumerate(expected_sources):
        if (
            state["sanitization"][index]["input"] != inner["sources"][index]["content"]
            or (state["redaction"][index]["output"] or "") != source["content"]
        ):
            raise ValueError("ocw_source_observation")
    draft = state["draft_object"]
    full_fallback = any(draft is item for item in state["fallbacks"])
    action_fallback = any(draft.action_items is item.action_items for item in state["fallbacks"])
    extracted = any(draft.action_items is item for item in state["extractions"])
    attempts = copy.deepcopy(
        [
            item
            for item in ledger.http_observations
            if starting_attempts < item["attempt"] <= ledger.attempts
        ]
    )
    if not attempts or attempts[-1].get("raw_assistant_text") is None:
        raise ValueError("ocw_capture_incomplete")
    internal = state["internal_result"]
    if (
        type(body) is not dict
        or body.get("scenario") != "mascot_insight"
        or body.get("message") != draft.message
        or body.get("action_items") != draft.action_items
        or internal.get("message") != draft.message
        or internal.get("action_items") != draft.action_items
        or body.get("quota_state") != "consumed"
    ):
        raise ValueError("ocw_result_mismatch")
    record = {
        "schema_version": "ocw_mascot_observation.v1",
        "asset_type": "eval_run",
        "rail": "advisory",
        "version": "v1",
        "policy_version": "ocw1a-comparison-v1",
        "run": copy.deepcopy(run),
        "case_id": scenario["canonical_id"],
        "arm": arm,
        "input_payload": copy.deepcopy(inner),
        "requested_language": "ru",
        "retrieval_origin": "controlled_synthetic",
        "admitted_sources": expected_sources,
        "sanitization": state["sanitization"],
        "redaction": state["redaction"],
        "source_snapshot_fingerprint": "sha256:"
        + hashlib.sha256(_canonical(expected_sources)).hexdigest(),
        "source_snapshot_origin": "derived_from_observed_prompt_material",
        "runtime_canonical_freeze_observed": False,
        "prompt": state["prompt"],
        "prompt_sha256": hashlib.sha256(state["prompt"].encode()).hexdigest(),
        "builder_query": state["builder_query"],
        "builder_context": state["builder_context"],
        "raw_assistant_text": attempts[-1]["raw_assistant_text"],
        "generation_text": state["generation_text"],
        "draft": {
            "message": draft.message,
            "action_items": draft.action_items,
            "warnings": draft.warnings,
        },
        "internal_result": internal,
        "http": {
            "method": "POST",
            "path": "/api/v1/insight/fitchef",
            "status_code": 200,
            "content_type": response.headers["content-type"],
            "body": body,
        },
        "field_origin": {
            "message": "fallback" if full_fallback else "provider_normalized",
            "action_items": (
                "fallback_default"
                if action_fallback
                else "provider_extracted" if extracted else "unknown"
            ),
        },
        "provider": {
            "requested_model": _OCW_MODELS[arm],
            "returned_model": attempts[-1].get("returned_model"),
            "endpoint": _OCW_ENDPOINTS[arm],
            "backend_identity": "unknown",
            "attempts": attempts,
            "reserved_cents": 15 * (ledger.attempts - starting_attempts),
            "cost_usd": attempts[0].get("cost_usd") if len(attempts) == 1 else None,
            "cost_status": (
                attempts[0].get("cost_status", "unknown") if len(attempts) == 1 else "unknown"
            ),
        },
        "upstream_assets": [
            run["manifest_fingerprint"],
            run["rubric_sha256"],
            run["pricing_fingerprint"],
        ],
        "upstream_binding": "informational_fingerprints_only",
        "replay_behavior": "frozen_read_only_observation",
        "admission_behavior": "native_route_and_capture_binding",
        "authority_granted": False,
        "answer_change_allowed": False,
    }
    record["material_fingerprint"] = "sha256:" + hashlib.sha256(_canonical(record)).hexdigest()
    record["idempotency_key"] = (
        "sha256:"
        + hashlib.sha256(
            _canonical(
                {
                    "run_id": run["id"],
                    "case_id": record["case_id"],
                    "arm": arm,
                    "material_fingerprint": record["material_fingerprint"],
                }
            )
        ).hexdigest()
    )
    encoded = _canonical(record)
    if len(encoded) > MAX_LINE_BYTES:
        raise ValueError("ocw_record_limit")
    ledger.require_secret_free(encoded)
    return record


def validate_ocw_records(
    records: list[object], *, expected_run: dict[str, Any]
) -> list[dict[str, Any]]:
    """Recheck frozen paired material; consistency does not authenticate execution."""
    try:
        return _validate_ocw_records(records, expected_run=expected_run)
    except (KeyError, TypeError, IndexError, AttributeError, UnicodeError, RecursionError) as exc:
        raise ValueError("ocw_record") from exc


def _validate_ocw_records(
    records: list[object], *, expected_run: dict[str, Any]
) -> list[dict[str, Any]]:
    """Use the existing native JSON depth/wire owners before any defensive copy."""
    from app.schemas.fitchef import FitChefMascotInsightResult
    from app.schemas.fitchef_coaching import FitChefMascotInsightResponse

    if type(records) is not list or len(records) != 16:
        raise ValueError("ocw_capture_incomplete")
    if type(expected_run) is not dict or type(expected_run.get("id")) is not str:
        raise ValueError("ocw_record_binding")
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    physical_attempts: set[int] = set()
    pairs: dict[str, dict[str, dict[str, Any]]] = {}
    for raw in records:
        if type(raw) is not dict:
            raise ValueError("ocw_record")
        _check_depth(raw)
        encoded = _canonical(raw)
        if len(encoded) > MAX_LINE_BYTES:
            raise ValueError("ocw_record_limit")
        # Native decoding makes the returned material independent without
        # invoking a caller-supplied nested __deepcopy__ implementation.
        row = json.loads(encoded)
        keys = {
            "schema_version",
            "asset_type",
            "rail",
            "version",
            "policy_version",
            "run",
            "case_id",
            "arm",
            "input_payload",
            "requested_language",
            "retrieval_origin",
            "admitted_sources",
            "sanitization",
            "redaction",
            "source_snapshot_fingerprint",
            "source_snapshot_origin",
            "runtime_canonical_freeze_observed",
            "prompt",
            "prompt_sha256",
            "builder_query",
            "builder_context",
            "raw_assistant_text",
            "generation_text",
            "draft",
            "internal_result",
            "http",
            "field_origin",
            "provider",
            "upstream_assets",
            "upstream_binding",
            "replay_behavior",
            "admission_behavior",
            "authority_granted",
            "answer_change_allowed",
            "material_fingerprint",
            "idempotency_key",
        }
        if set(row) != keys:
            raise ValueError("ocw_record")
        if (
            row.get("schema_version") != "ocw_mascot_observation.v1"
            or _canonical(row.get("run")) != _canonical(expected_run)
            or row.get("case_id") not in _OCW_CASES
            or row.get("arm") not in _OCW_MODELS
            or row.get("authority_granted") is not False
            or row.get("answer_change_allowed") is not False
            or row.get("runtime_canonical_freeze_observed") is not False
            or row.get("retrieval_origin") != "controlled_synthetic"
            or row["asset_type"] != "eval_run"
            or row["rail"] != "advisory"
            or row["version"] != "v1"
            or row["policy_version"] != "ocw1a-comparison-v1"
            or row["requested_language"] != "ru"
            or row["upstream_binding"] != "informational_fingerprints_only"
            or row["replay_behavior"] != "frozen_read_only_observation"
            or row["admission_behavior"] != "native_route_and_capture_binding"
            or row["upstream_assets"]
            != [
                expected_run["manifest_fingerprint"],
                expected_run["rubric_sha256"],
                expected_run["pricing_fingerprint"],
            ]
        ):
            raise ValueError("ocw_record")
        key = (row["case_id"], row["arm"])
        if key in seen:
            raise ValueError("ocw_record")
        seen.add(key)
        material = {
            k: v for k, v in row.items() if k not in ("material_fingerprint", "idempotency_key")
        }
        if (
            row.get("material_fingerprint")
            != "sha256:" + hashlib.sha256(_canonical(material)).hexdigest()
        ):
            raise ValueError("ocw_record_binding")
        idem = {
            "run_id": expected_run["id"],
            "case_id": key[0],
            "arm": key[1],
            "material_fingerprint": row["material_fingerprint"],
        }
        if row.get("idempotency_key") != "sha256:" + hashlib.sha256(_canonical(idem)).hexdigest():
            raise ValueError("ocw_record_binding")
        inner = row["input_payload"]
        if "input_fingerprints" not in expected_run or "sha256:" + hashlib.sha256(
            _canonical(inner)
        ).hexdigest() != expected_run["input_fingerprints"].get(row["case_id"]):
            raise ValueError("ocw_record_binding")
        prompt, sources = _ocw_prompt(inner)
        if (
            row.get("prompt") != prompt
            or _canonical(row.get("admitted_sources")) != _canonical(sources)
            or row.get("prompt_sha256") != hashlib.sha256(prompt.encode()).hexdigest()
            or row.get("source_snapshot_fingerprint")
            != "sha256:" + hashlib.sha256(_canonical(sources)).hexdigest()
            or row.get("source_snapshot_origin") != "derived_from_observed_prompt_material"
        ):
            raise ValueError("ocw_record_binding")
        context = "\n\n".join(
            f"[{source['file']}]\n{source['content']}"
            for source in sources
            if source["content"].strip()
        )
        if (
            row["builder_query"] != require_safe_ai_agent_input(inner["query"])
            or row["builder_context"] != context
        ):
            raise ValueError("ocw_record_binding")
        for field in ("sanitization", "redaction"):
            if type(row[field]) is not list or len(row[field]) != len(sources):
                raise ValueError("ocw_record_binding")
        for index, source in enumerate(inner["sources"]):
            sanitized = fitchef_runtime.sanitize_rag_markdown(source["content"])
            redacted = fitchef_runtime.redact_pii_from_text(sanitized)
            if _canonical(row["sanitization"][index]) != _canonical(
                {"input": source["content"], "output": sanitized}
            ) or _canonical(row["redaction"][index]) != _canonical(
                {"input": sanitized, "output": redacted}
            ):
                raise ValueError("ocw_record_binding")
        provider = row["provider"]
        if (
            type(provider) is not dict
            or set(provider)
            != {
                "requested_model",
                "returned_model",
                "endpoint",
                "backend_identity",
                "attempts",
                "reserved_cents",
                "cost_usd",
                "cost_status",
            }
            or provider["requested_model"] != _OCW_MODELS[key[1]]
            or provider["endpoint"] != _OCW_ENDPOINTS[key[1]]
            or provider["backend_identity"] != "unknown"
            or type(provider["attempts"]) is not list
            or not 1 <= len(provider["attempts"]) <= (3 if key[1] == "sonar" else 1)
            or type(provider["reserved_cents"]) is not int
            or provider["reserved_cents"] != 15 * len(provider["attempts"])
        ):
            raise ValueError("ocw_record_binding")
        previous = 0
        for index, attempt in enumerate(provider["attempts"]):
            if (
                type(attempt) is not dict
                or type(attempt.get("attempt")) is not int
                or not previous < attempt["attempt"] <= 32
                or attempt["attempt"] in physical_attempts
                or attempt.get("case_id") != key[0]
                or attempt.get("arm") != key[1]
                or attempt.get("requested_model") != _OCW_MODELS[key[1]]
                or attempt.get("endpoint") != _OCW_ENDPOINTS[key[1]]
                or attempt.get("cost_status") not in {"known", "unknown"}
            ):
                raise ValueError("ocw_record_binding")
            previous = attempt["attempt"]
            physical_attempts.add(previous)
            _ocw_usage(attempt.get("usage"))
            if attempt["cost_status"] == "unknown":
                if attempt.get("cost_usd") is not None:
                    raise ValueError("ocw_record_binding")
            elif (
                type(attempt.get("cost_usd")) not in (int, float)
                or (type(attempt["cost_usd"]) is float and not math.isfinite(attempt["cost_usd"]))
                or not 0 <= attempt["cost_usd"] <= 0.15
                or attempt.get("invoice_verified") is not False
            ):
                raise ValueError("ocw_record_binding")
            if index == len(provider["attempts"]) - 1:
                if (
                    type(attempt.get("status_code")) is not int
                    or attempt["status_code"] not in (200, 201)
                    or attempt.get("raw_assistant_text") != row["raw_assistant_text"]
                    or type(row["raw_assistant_text"]) is not str
                    or attempt.get("returned_model") != provider["returned_model"]
                ):
                    raise ValueError("ocw_record_binding")
            elif attempt.get("status_code") not in {408, 429, 500, 502, 503, 504} and not (
                attempt.get("failure_type") in {"APIConnectionError", "APITimeoutError"}
                and attempt.get("retryable") is True
            ):
                raise ValueError("ocw_record_binding")
        known = len(provider["attempts"]) == 1
        if provider["cost_usd"] != (
            provider["attempts"][0].get("cost_usd") if known else None
        ) or provider["cost_status"] != (
            provider["attempts"][0]["cost_status"] if known else "unknown"
        ):
            raise ValueError("ocw_record_binding")
        draft = row["draft"]
        if (
            type(draft) is not dict
            or set(draft) != {"message", "action_items", "warnings"}
            or type(draft["message"]) is not str
            or not draft["message"].strip()
            or any(
                type(draft[field]) is not list
                or any(type(item) is not str for item in draft[field])
                for field in ("action_items", "warnings")
            )
        ):
            raise ValueError("ocw_record_binding")
        internal = FitChefMascotInsightResult.model_validate(
            row["internal_result"], strict=True
        ).model_dump(mode="json")
        expected_source_items = [
            {field: source[field] for field in ("chunk_id", "file", "preview", "score")}
            for source in sources
            if source["content"].strip()
        ]
        if (
            _canonical(internal) != _canonical(row["internal_result"])
            or internal["scenario"] != "mascot_insight"
            or internal["mode"] != "auto-safe"
            or internal["quota_state"] != "consumed"
            or _canonical(internal["sources"]) != _canonical(expected_source_items)
            or (
                draft["warnings"]
                and internal["warnings"][-len(draft["warnings"]) :] != draft["warnings"]
            )
        ):
            raise ValueError("ocw_record_binding")
        expected_http = {
            field: value for field, value in internal.items() if field not in {"mode", "sources"}
        }
        expected_http["sources"] = [
            {field: value[field] for field in ("file", "preview", "score")}
            for value in internal["sources"]
        ]
        response = row["http"]
        public = FitChefMascotInsightResponse.model_validate(
            response["body"], strict=True
        ).model_dump(mode="json")
        if (
            set(response) != {"method", "path", "status_code", "content_type", "body"}
            or _canonical(public) != _canonical(response["body"])
            or _canonical(public) != _canonical(expected_http)
            or response["method"] != "POST"
            or response["path"] != "/api/v1/insight/fitchef"
            or type(response["status_code"]) is not int
            or response["status_code"] != 200
            or not response["content_type"].startswith("application/json")
            or response["body"]["message"] != row["draft"]["message"]
            or response["body"]["action_items"] != row["draft"]["action_items"]
            or row["internal_result"]["message"] != row["draft"]["message"]
            or row["internal_result"]["action_items"] != row["draft"]["action_items"]
            or row["generation_text"] != row["raw_assistant_text"].strip()
        ):
            raise ValueError("ocw_record_binding")
        origin = row["field_origin"]
        if (
            type(origin) is not dict
            or set(origin) != {"message", "action_items"}
            or origin["message"] not in {"fallback", "provider_normalized"}
            or origin["action_items"] not in {"fallback_default", "provider_extracted", "unknown"}
        ):
            raise ValueError("ocw_record_binding")
        pairs.setdefault(key[0], {})[key[1]] = row
        result.append(row)
    if seen != {(case, arm) for case in _OCW_CASES for arm in _OCW_MODELS}:
        raise ValueError("ocw_capture_incomplete")
    if physical_attempts != set(range(1, len(physical_attempts) + 1)):
        raise ValueError("ocw_record_binding")
    for pair in pairs.values():
        for field in ("input_payload", "prompt", "admitted_sources", "source_snapshot_fingerprint"):
            if _canonical(pair["sonar"][field]) != _canonical(pair["sol"][field]):
                raise ValueError("ocw_pair_mismatch")
    return result


def build_ocw_blind_view(
    records: list[object], *, expected_run: dict[str, Any], expected_capture_sha256: str
) -> list[dict[str, Any]]:
    """Allowlisted view of frozen final answers; no provider/cost/order/reference data."""
    frozen = validate_ocw_records(records, expected_run=expected_run)
    if (
        type(expected_capture_sha256) is not str
        or re.fullmatch(r"sha256:[0-9a-f]{64}", expected_capture_sha256) is None
        or "sha256:"
        + hashlib.sha256(b"".join(_canonical(row) + b"\n" for row in frozen)).hexdigest()
        != expected_capture_sha256
    ):
        raise ValueError("ocw_capture_binding")
    views: list[dict[str, Any]] = []
    for row in frozen:
        opaque = hashlib.sha256(
            _canonical(
                {"material": row["material_fingerprint"], "rubric": expected_run["rubric_sha256"]}
            )
        ).hexdigest()
        content = {
            "schema_version": "ocw_blind_view.v1",
            "opaque_id": opaque,
            "material_fingerprint": row["material_fingerprint"],
            "rubric_sha256": expected_run["rubric_sha256"],
            "requested_language": "ru",
            "query": row["input_payload"]["query"],
            "final_answer": {
                "message": row["http"]["body"]["message"],
                "action_items": row["http"]["body"]["action_items"],
            },
            "sources": [
                {"source_ref": f"source-{index}", "content": source["content"]}
                for index, source in enumerate(row["admitted_sources"])
            ],
        }
        views.append(content)
    # Stable opaque order removes run ordering; intrinsic answer text is retained.
    return sorted(views, key=lambda item: item["opaque_id"])


def collect_ocw_comparison(
    manifest: list[object],
    *,
    output_dir: Path,
    rubric: Path,
    pricing: list[object],
    fitchef_key: str,
    perplexity_key: str,
    run_id: str,
) -> None:
    """One guarded paced sixteen-POST capture, with private immutable partial evidence."""
    rows = validate_ocw_manifest(manifest)
    if type(run_id) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", run_id):
        raise ValueError("ocw_run_id")
    if not perplexity_key or perplexity_key != os.getenv("PERPLEXITY_API_KEY"):
        raise ValueError("ocw_provider_configuration")
    prices = validate_ocw_pricing(pricing)
    pricing = copy.deepcopy(pricing)
    preflight = ocw_request_preflight(cast(list[object], rows), pricing)
    validate_ocw_environment(fitchef_key)
    names = (
        [f"attempt-{i:04d}.json" for i in range(1, 33)]
        + [f"attempt-result-{i:04d}.json" for i in range(1, 33)]
        + [f"case-{arm}-{case}.jsonl" for case in _OCW_CASES for arm in _OCW_MODELS]
        + [
            "inputs.jsonl",
            "run.jsonl",
            "rubric.jsonl",
            "comparison.jsonl",
            "comparison-status.json",
        ]
    )
    _validate_output_directory(output_dir, generated_names=names)
    if any(output_dir.iterdir()):
        raise ValueError("output_directory_not_empty")
    ledger = AttemptLedger(output_dir, comparison=True)
    ledger._comparison_secrets = (fitchef_key, perplexity_key)
    ledger.pricing_valid_until = min(
        datetime.fromisoformat(row["verified_at"].replace("Z", "+00:00")) + _OCW_PRICING_MAX_AGE
        for row in prices.values()
    )
    ledger.cost_currency_basis = {
        arm: row["returned_cost_currency_basis"] for arm, row in prices.items()
    }
    code_sha, code_hashes = _code_sha(), _ocw_code_hashes()
    from scripts.evals.evidence_relation_audit import _read_input

    rubric_bytes = _read_input(rubric)
    canonical_rubric = (
        Path(__file__).resolve().parents[2] / "docs/evals/FITCHEF_CLAIM_EVIDENCE_EVAL_V1.md"
    )
    if rubric_bytes != _read_input(canonical_rubric):
        raise ValueError("ocw_rubric_binding")
    run: dict[str, Any] = {
        "id": run_id,
        "code_sha": code_sha,
        "code_hashes": code_hashes,
        "manifest_fingerprint": "sha256:" + hashlib.sha256(_canonical(rows)).hexdigest(),
        "input_fingerprints": {
            row["canonical_id"]: "sha256:"
            + hashlib.sha256(_canonical(row["input_payload"])).hexdigest()
            for row in rows
        },
        "rubric_sha256": "sha256:" + hashlib.sha256(rubric_bytes).hexdigest(),
        "pricing_fingerprint": "sha256:" + hashlib.sha256(_canonical(pricing)).hexdigest(),
        "request_preflight": preflight,
        "route_limit": "10/minute",
        "pacing_seconds": 6.1,
        "capture_kind": "native_guarded_http_observation",
    }
    records: list[dict[str, Any]] = []
    transport: httpx.AsyncClient | None = None
    capture_sha256: str | None = None
    previous_started: float | None = None
    expected_cases: dict[tuple[str, str], bytes] = {}
    run_bytes = _canonical(run) + b"\n"
    case_publication_uncertain = False
    case_readback_uncertain = False
    aggregate_publication_uncertain = False

    def publish(name: str, data: bytes) -> None:
        nonlocal case_publication_uncertain, aggregate_publication_uncertain
        try:
            ledger.require_secret_free(data)
            write_report(output_dir / name, data)
        except BaseException:
            ledger.retryable = False
            if name.startswith("case-"):
                case_publication_uncertain = True
            elif name == "comparison.jsonl":
                aggregate_publication_uncertain = True
            raise

    def retained_cases() -> set[tuple[str, str]]:
        """Compare only our finite destinations with independently captured exact bytes."""
        nonlocal case_readback_uncertain
        complete: set[tuple[str, str]] = set()
        try:
            if _read_input(output_dir / "run.jsonl") != run_bytes:
                raise ValueError("ocw_run_readback")
        except ValueError:
            case_readback_uncertain = True
            return complete
        for key, expected_bytes in expected_cases.items():
            case, arm = key
            try:
                if _read_input(output_dir / f"case-{arm}-{case}.jsonl") != expected_bytes:
                    raise ValueError("ocw_case_readback")
            except ValueError as error:
                if not isinstance(error.__cause__, FileNotFoundError):
                    case_readback_uncertain = True
            else:
                complete.add(key)
        return complete

    def status_bytes(failure: str | None) -> bytes:
        complete = retained_cases()
        if failure is None and (
            len(complete) != 16 or case_readback_uncertain or capture_sha256 is None
        ):
            raise ValueError("ocw_case_readback")
        encoded: bytes = (
            _canonical(
                {
                    "schema_version": "ocw_collection_status.v1",
                    "status": "complete" if failure is None else "incomplete",
                    "failure_category": failure,
                    "capture_sha256": capture_sha256,
                    "run_id": run_id,
                    "completed": sorted([list(key) for key in complete]),
                    "missing": [
                        [case, arm]
                        for case in _OCW_CASES
                        for arm in _OCW_MODELS
                        if (case, arm) not in complete
                    ],
                    "reserved_attempts": ledger.attempts,
                    "reserved_cents": ledger.attempts * 15,
                    "published_reservations": ledger.reservation_publications,
                    "reservation_publication_uncertain": ledger.reservation_publication_uncertain,
                    "case_publication_uncertain": case_publication_uncertain,
                    "case_readback_uncertain": case_readback_uncertain,
                    "aggregate_publication_uncertain": aggregate_publication_uncertain,
                    "observed_http_outcomes": sum(
                        "status_code" in item for item in ledger.http_observations
                    ),
                    "uncertain_transport_outcomes": sum(
                        "failure_type" in item for item in ledger.http_observations
                    ),
                    "arm_attempts": ledger.arm_attempts,
                    "reported_overrun_usd": ledger.reported_overrun_usd,
                    "authority_granted": False,
                    "answer_change_allowed": False,
                }
            )
            + b"\n"
        )
        return encoded

    # Successful no-replace publication claims this exact output cooperatively.
    # A loser (including unacknowledged claim publication) owns no status writes.
    publish("run.jsonl", run_bytes)
    try:
        for name, data in (
            ("inputs.jsonl", b"".join(_canonical(row) + b"\n" for row in rows)),
            (
                "rubric.jsonl",
                _canonical(
                    {"content": rubric_bytes.decode("utf-8"), "sha256": run["rubric_sha256"]}
                )
                + b"\n",
            ),
        ):
            publish(name, data)
        transport = _ocw_http_client(ledger)
        from app.main import app
        from app.security import rate_limit
        from tests._client import open_test_client

        if app.dependency_overrides:
            raise ValueError("ocw_dependency_override")
        with open_test_client(app, raise_server_exceptions=False) as client:
            portal = client.portal
            if portal is None:
                raise ValueError("ocw_client_portal")
            try:
                if (
                    app.state.limiter is not rate_limit.limiter
                    or app.state.limiter.enabled is not True
                ):
                    raise ValueError("ocw_active_limiter_required")
                for scenario in rows:
                    for arm in _OCW_MODELS:
                        if (
                            _code_sha() != code_sha
                            or _ocw_code_hashes() != code_hashes
                            or _read_input(rubric) != rubric_bytes
                        ):
                            raise ValueError("code_changed_during_collection")
                        if previous_started is not None:
                            remaining = _OCW_PACE_SECONDS - (time.monotonic() - previous_started)
                            if remaining > 0:
                                time.sleep(remaining)
                        previous_started = time.monotonic()
                        record = _ocw_observe_post(
                            client,
                            scenario,
                            arm=arm,
                            key=fitchef_key,
                            transport=transport,
                            ledger=ledger,
                            run=run,
                        )
                        record_bytes = _canonical(record) + b"\n"
                        expected_cases[(scenario["canonical_id"], arm)] = record_bytes
                        publish(f"case-{arm}-{scenario['canonical_id']}.jsonl", record_bytes)
                        records.append(record)
                if len(retained_cases()) != 16 or case_readback_uncertain:
                    raise ValueError("ocw_case_readback")
                validate_ocw_records(cast(list[object], records), expected_run=run)
                encoded = b"".join(_canonical(record) + b"\n" for record in records)
                publish("comparison.jsonl", encoded)
                capture_sha256 = "sha256:" + hashlib.sha256(encoded).hexdigest()
            finally:
                original_error = sys.exc_info()[1]
                try:
                    portal.call(transport.aclose)
                except BaseException as cleanup_error:
                    if original_error is None:
                        raise
                    original_error.add_note(
                        "ocw_transport_cleanup_failed:" + type(cleanup_error).__name__
                    )
        publish("comparison-status.json", status_bytes(None))
    except BaseException as error:
        if transport is not None and not transport.is_closed:
            try:
                asyncio.run(transport.aclose())
            except BaseException as cleanup_error:
                error.add_note("ocw_transport_cleanup_failed:" + type(cleanup_error).__name__)
        failure = (
            ledger.terminal_reason or "interrupted"
            if not isinstance(error, Exception)
            else ledger.terminal_reason or "capture_or_runtime_failure"
        )
        try:
            publish("comparison-status.json", status_bytes(failure))
        except BaseException as publication_error:
            # Keep the first actual failure and every existing immutable file.
            # A status publication failure is uncertainty, never permission to
            # replace a destination or start the capture again.
            error.add_note("ocw_status_publication_failed:" + type(publication_error).__name__)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--pricing-evidence", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("distortion", _OCW_MODE), default="distortion")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.mode == _OCW_MODE:
            manifest = validate_ocw_manifest(read_jsonl(args.manifest))
            pricing = read_private_jsonl(args.pricing_evidence)
            if args.preflight_only:
                print(
                    json.dumps(
                        ocw_request_preflight(cast(list[object], manifest), pricing), sort_keys=True
                    )
                )
                return 0
            collect_ocw_comparison(
                cast(list[object], manifest),
                output_dir=args.output_dir,
                rubric=args.rubric,
                pricing=pricing,
                fitchef_key=os.getenv("OCW_FITCHEF_API_KEY", ""),
                perplexity_key=os.getenv("PERPLEXITY_API_KEY", ""),
                run_id=args.run_id,
            )
            return 0
        if args.run_id is not None or args.preflight_only:
            raise ValueError("comparison_flag_requires_mode")
        manifest = validate_manifest(read_private_jsonl(args.manifest))
        rubric_sha256 = _rubric_hash(args.rubric)
        validate_pricing_evidence(read_jsonl(args.pricing_evidence))
        fitchef_key = os.getenv("NOOS_EVAL_FITCHEF_API_KEY", "")
        perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
        if not fitchef_key or not perplexity_key:
            raise ValueError("missing_provider_or_fitchef_key")
        validate_live_environment(fitchef_key)
        if os.getenv("LLM_PROVIDER") not in (None, "perplexity"):
            raise ValueError("provider_selection_conflict")
        output_info = args.output_dir.stat()
        if not stat.S_ISDIR(output_info.st_mode) or output_info.st_mode & 0o077:
            raise ValueError("unsafe_output_directory")
        asyncio.run(
            collect(
                manifest,
                output_dir=args.output_dir,
                rubric_sha256=rubric_sha256,
                fitchef_key=fitchef_key,
                perplexity_key=perplexity_key,
            )
        )
    except Exception as exc:
        # Provider exceptions can carry request text. Only the type is safe to print.
        print(f"collect_fitchef_answers: {type(exc).__name__}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
