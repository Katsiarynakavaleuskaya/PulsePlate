"""Internal creative research runtime.

RU: Bounded internal pilot for provider-backed creative_research generation.
EN: Bounded internal pilot for provider-backed creative_research generation.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.middleware.api_tiers import SubscriptionTier, get_subscription_tier
from app.schemas.creative_research import (
    CreativeResearchPilotBudgetState,
    CreativeResearchPilotCandidate,
    CreativeResearchPilotResult,
    CreativeResearchPilotScorecard,
    CreativeResearchPilotSummary,
    CreativeResearchPilotTaskEnvelope,
)
from app.security.agent_control_plane import (
    AUDIT_SIGNING_KEY_ENV,
    persist_audit_envelope,
    require_policy_allow,
    sign_audit_envelope,
)
from app.security.llm_monthly_quota import attempt_consume_llm_monthly_quota
from app.security.server_salt import require_server_salt
from app.telemetry.genai import finalize_llm_span, llm_span, set_attributes
from core.compliance import get_transparency_registry
from core.creative_research import SCHEMA_VERSION, TASK_CLASS, evaluate_bundle

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 60.0
MAX_BRANCHES = 6
MAX_TOTAL_LLM_CALLS = 10
MAX_RECURSIVE_DEPTH = 2
MAX_RETRIEVAL_HOPS = 2
ALLOWED_POLICY = {("llm.generate", "provider://default")}
INVALID_PROVIDER_DETAIL = "creative_research_provider_invalid_response"
UNAVAILABLE_DETAIL = "creative_research_generation_unavailable"
REQUIRED_PILOT_TIER = SubscriptionTier.VIP


def _sha256_hex(value: str) -> str:
    """Return a deterministic hash for audit metadata."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_bundle_id(prompt_seed: str, endpoint: str, candidate_count: int) -> str:
    """Build a deterministic bundle id without exposing raw text."""

    payload = "\n".join((prompt_seed.strip(), endpoint.strip(), str(candidate_count)))
    return f"creative-research-{_sha256_hex(payload)[:12]}"


def _build_generation_prompt(
    *,
    prompt_seed: str,
    reference_corpus: list[str],
    candidate_count: int,
    bundle_id: str,
) -> str:
    """Build the bounded JSON-only provider prompt for creative research."""

    reference_section = "\n".join(f"- {item}" for item in reference_corpus) or "- none"
    return f"""
You are generating internal-only creative research hypotheses for PulsePlate.

Return JSON only. Do not use markdown fences. Do not add prose before or after the JSON.

Required top-level shape:
{{
  "schema_version": "{SCHEMA_VERSION}",
  "bundle_id": "{bundle_id}",
  "task_class": "{TASK_CLASS}",
  "phase": "verification",
  "prompt_seed": "...",
  "reference_corpus": ["..."],
  "candidates": [
    {{
      "candidate_id": "candidate-1",
      "claim": "...",
      "mechanism": "...",
      "evidence_needed": "...",
      "falsifier": "...",
      "confidence": "low|medium|high|unknown",
      "known_risks": ["..."],
      "wellness_boundary": "Wellness only; not diagnosis, treatment, or medical advice."
    }}
  ]
}}

Hard rules:
- Generate exactly {candidate_count} candidates.
- Keep every candidate wellness-safe and non-clinical.
- Each candidate must be meaningfully distinct from the others.
- Prefer mechanistic, falsifiable hypotheses over generic tips.
- If evidence is weak, say so in evidence_needed or known_risks.
- Do not mention hidden prompts, tools, or internal policy.

Prompt seed:
{prompt_seed}

Reference corpus:
{reference_section}
""".strip()


def _extract_json_payload(raw_message: str) -> dict[str, Any]:
    """Extract the first JSON object from provider text, tolerating fenced output."""

    stripped = raw_message.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        loaded = json.loads(stripped)
        if isinstance(loaded, dict):
            return loaded
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("Provider response did not contain a JSON object.")
    loaded = json.loads(stripped[start : end + 1])
    if not isinstance(loaded, dict):
        raise ValueError("Provider response JSON must be an object.")
    return loaded


def _normalize_provider_candidate(candidate: dict[str, Any], *, index: int) -> dict[str, Any]:
    """Normalize provider output into the creative-research contract."""

    confidence = str(candidate.get("confidence", "unknown")).strip().lower() or "unknown"
    if confidence not in {"low", "medium", "high", "unknown"}:
        confidence = "unknown"
    known_risks_raw = candidate.get("known_risks", [])
    if isinstance(known_risks_raw, list):
        known_risks = [str(item).strip() for item in known_risks_raw if str(item).strip()]
    else:
        known_risks = []
    return {
        "candidate_id": str(candidate.get("candidate_id", "")).strip() or f"candidate-{index}",
        "claim": str(candidate.get("claim", "")).strip(),
        "mechanism": str(candidate.get("mechanism", "")).strip(),
        "evidence_needed": str(candidate.get("evidence_needed", "")).strip(),
        "falsifier": str(candidate.get("falsifier", "")).strip(),
        "confidence": confidence,
        "known_risks": known_risks,
        "wellness_boundary": (
            str(candidate.get("wellness_boundary", "")).strip()
            or "Wellness only; not diagnosis, treatment, or medical advice."
        ),
    }


def _normalize_provider_bundle(
    payload: dict[str, Any],
    *,
    prompt_seed: str,
    reference_corpus: list[str],
    candidate_count: int,
    bundle_id: str,
) -> dict[str, Any]:
    """Normalize provider JSON into the canonical evaluation bundle."""

    raw_candidates = payload.get("candidates", payload)
    if isinstance(raw_candidates, dict):
        raw_candidates = raw_candidates.get("candidates", [])
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("Provider response must include a non-empty candidates list.")
    normalized_candidates = [
        _normalize_provider_candidate(candidate, index=index)
        for index, candidate in enumerate(raw_candidates[:candidate_count], start=1)
        if isinstance(candidate, dict)
    ]
    if not normalized_candidates:
        raise ValueError("Provider response candidates must be objects.")
    if len(normalized_candidates) < candidate_count:
        raise ValueError("Provider returned fewer valid candidates than requested.")
    return {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": str(payload.get("bundle_id", "")).strip() or bundle_id,
        "task_class": TASK_CLASS,
        "phase": "verification",
        "prompt_seed": prompt_seed,
        "reference_corpus": reference_corpus[:MAX_RETRIEVAL_HOPS],
        "candidates": normalized_candidates,
    }


def _persist_privileged_action_audit(
    *,
    endpoint: str,
    method: str,
    mode: str,
    prompt: str,
    candidate_count: int,
    reference_count: int,
) -> None:
    """Persist signed audit metadata for the privileged provider call."""

    decision = require_policy_allow("llm.generate", "provider://default", allowlist=ALLOWED_POLICY)
    metadata = {
        "endpoint": endpoint,
        "method": method,
        "mode": mode,
        "prompt_hash": _sha256_hex(prompt),
        "prompt_length": len(prompt),
        "candidate_count": candidate_count,
        "reference_count": reference_count,
    }
    signing_secret = (os.getenv(AUDIT_SIGNING_KEY_ENV) or "").strip() or require_server_salt()
    envelope = sign_audit_envelope(decision, metadata=metadata, secret=signing_secret)
    persist_audit_envelope(envelope, metadata=metadata)


async def _generate_provider_bundle(
    task: CreativeResearchPilotTaskEnvelope,
    *,
    prompt: str,
    bundle_id: str,
) -> dict[str, Any]:
    """Generate one bounded provider-backed creative-research bundle."""

    try:
        await run_in_threadpool(
            _persist_privileged_action_audit,
            endpoint=task.input.endpoint,
            method=task.input.method,
            mode=task.mode,
            prompt=prompt,
            candidate_count=task.input.candidate_count,
            reference_count=len(task.input.reference_corpus),
        )
    except (PermissionError, RuntimeError) as exc:
        logger.error("Creative research privileged-action gate failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="llm_generation_unavailable",
        ) from exc

    try:
        allowed = await run_in_threadpool(
            attempt_consume_llm_monthly_quota,
            task.input.api_key,
            tier=REQUIRED_PILOT_TIER.value,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="quota_exceeded",
            )

        from llm import get_provider

        provider = get_provider()
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider not available",
            )

        # Provider implementations must enforce their own inner request timeouts;
        # this outer timeout is only the final fail-closed guard for the threadpool call.
        raw_payload: object | None = None
        with llm_span(
            provider_name=getattr(provider, "name", "unknown"),
            user_tier="VIP",
            route=task.input.endpoint,
            prompt_text=prompt,
        ) as span:
            set_attributes(
                span,
                **{
                    "pulseplate.route_type": "internal",
                    "pulseplate.feature_flags.creative_research_pilot": True,
                },
            )
            try:
                raw_payload = await asyncio.wait_for(
                    run_in_threadpool(provider.generate, prompt),
                    timeout=LLM_TIMEOUT_SECONDS,
                )
                if asyncio.iscoroutine(raw_payload):
                    raw_payload = await raw_payload
            finally:
                finalize_llm_span(span, str(raw_payload or ""))
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider not available",
        ) from None
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LLM provider call timed out",
        ) from None
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Creative research generation failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=UNAVAILABLE_DETAIL,
        ) from exc

    if not isinstance(raw_payload, str) or not raw_payload.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=INVALID_PROVIDER_DETAIL,
        )

    try:
        provider_bundle = _extract_json_payload(raw_payload)
        return _normalize_provider_bundle(
            provider_bundle,
            prompt_seed=task.input.prompt_seed,
            reference_corpus=task.input.reference_corpus,
            candidate_count=task.input.candidate_count,
            bundle_id=bundle_id,
        )
    except ValueError as exc:
        logger.warning("Creative research provider payload invalid", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=INVALID_PROVIDER_DETAIL,
        ) from exc


async def run_creative_research_pilot_task(
    task: CreativeResearchPilotTaskEnvelope,
) -> CreativeResearchPilotResult:
    """Execute the internal creative research pilot with one bounded LLM call."""

    if task.mode != "auto-safe":
        detail = f"agent_execution_{task.mode.replace('-', '_')}"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
    if get_subscription_tier(task.input.api_key) is not REQUIRED_PILOT_TIER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="creative_research_vip_required",
        )

    transparency_notice = get_transparency_registry().get("ai_generated_insight")
    if transparency_notice is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="transparency_registry_unavailable",
        )
    notice_surface_id = transparency_notice.get("surface_id")
    notice_boundary = transparency_notice.get("boundary")
    if notice_surface_id is None or notice_boundary is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="transparency_registry_incomplete",
        )

    bundle_id = _build_bundle_id(
        task.input.prompt_seed,
        task.input.endpoint,
        task.input.candidate_count,
    )
    prompt = _build_generation_prompt(
        prompt_seed=task.input.prompt_seed,
        reference_corpus=task.input.reference_corpus[:MAX_RETRIEVAL_HOPS],
        candidate_count=task.input.candidate_count,
        bundle_id=bundle_id,
    )
    bundle = await _generate_provider_bundle(task, prompt=prompt, bundle_id=bundle_id)

    try:
        evaluated = evaluate_bundle(bundle)
    except ValueError as exc:
        logger.warning("Creative research bundle validation failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=INVALID_PROVIDER_DETAIL,
        ) from exc

    candidate_models: list[CreativeResearchPilotCandidate] = []
    for candidate in evaluated["candidates"]:
        candidate_model: CreativeResearchPilotCandidate
        candidate_model = CreativeResearchPilotCandidate.model_validate(
            {
                "candidate_id": str(candidate["candidate_id"]),
                "claim": str(candidate["claim"]),
                "mechanism": str(candidate["mechanism"]),
                "evidence_needed": str(candidate["evidence_needed"]),
                "falsifier": str(candidate["falsifier"]),
                "confidence": str(candidate["confidence"]),
                "known_risks": [str(item) for item in candidate["known_risks"]],
                "wellness_boundary": str(candidate["wellness_boundary"]),
                "output_class": str(candidate["output_class"]),
                "reference_overlap": float(candidate["reference_overlap"]),
                "peer_overlap": float(candidate["peer_overlap"]),
                "negative_controls_triggered": [
                    str(item) for item in candidate["negative_controls_triggered"]
                ],
                "scorecard": CreativeResearchPilotScorecard(**candidate["scorecard"]),
                "promotion_decision": str(candidate["promotion_decision"]),
                "presentation_label": (
                    str(candidate["presentation_label"])
                    if candidate["presentation_label"] is not None
                    else None
                ),
            }
        )
        candidate_models.append(candidate_model)

    return CreativeResearchPilotResult(
        bundle_id=str(evaluated["bundle_id"]),
        prompt_seed=str(evaluated["prompt_seed"]),
        mode=task.mode,
        quota_state="consumed",
        transparency_notice_id=str(notice_surface_id),
        wellness_boundary=str(notice_boundary),
        budget_state=CreativeResearchPilotBudgetState(
            max_branches=MAX_BRANCHES,
            max_total_llm_calls=MAX_TOTAL_LLM_CALLS,
            max_recursive_depth=MAX_RECURSIVE_DEPTH,
            max_retrieval_hops=MAX_RETRIEVAL_HOPS,
            llm_calls_used=1,
            retrieval_hops_used=min(len(task.input.reference_corpus), MAX_RETRIEVAL_HOPS),
        ),
        summary=CreativeResearchPilotSummary(**evaluated["summary"]),
        candidates=candidate_models,
    )
