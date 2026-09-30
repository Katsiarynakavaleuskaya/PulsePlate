#!/usr/bin/env python3
"""Opt-in local collection of final FitChef distortion answers with a hard send budget.

Run only with a frozen private synthetic manifest and configured environment.
This module has no import-time provider call. Partial runs remain private and
must not be restarted for better answers.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from contextlib import ExitStack
import copy
import hashlib
import logging
import math
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, cast
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from openai import AsyncOpenAI, OpenAI
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
from scripts.evals.evidence_relation_audit import _parent_fd, read_jsonl, write_report
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


class BudgetExhausted(RuntimeError):
    """The next physical request is not allowed to reach transport."""


class _PreproviderHighDistressBoundary(HTTPException):
    """Identify only the collector's own preprovider distress admission failure."""

    def __init__(self) -> None:
        super().__init__(status_code=400, detail="fitchef_high_distress_boundary")


class AttemptLedger:
    """Durable private reservation immediately before each HTTPX send."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._lock = asyncio.Lock()
        self.attempts = 0
        self.exhausted = False
        self.transport_rejection = False
        self.reported_overrun_usd: int | float | None = None
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


def _validate_output_directory(directory: Path) -> None:
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
        [f"attempt-{index:04d}.json" for index in range(1, _ATTEMPT_LIMIT + 1)]
        + [f"case-{index:02d}.jsonl" for index in range(1, 25)]
        + ["cases.jsonl", "collection-status.json"]
    )
    paths = [str(relative / name) for name in names]
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--pricing-evidence", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
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
