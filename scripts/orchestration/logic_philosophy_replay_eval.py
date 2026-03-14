#!/usr/bin/env python3
"""Deterministic offline replay evaluator for logic + philosophy reliability.

RU: Оценивает offline replay + ablation без live provider/network calls.
EN: Scores offline replay + ablation without live provider/network calls.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.insight.analytical import extract_claims
from core.insight.aristotelian import NonContradictionChecker
from scripts.orchestration.logic_philosophy_replay_contract import (
    PRIMARY_METRICS,
    REPLAY_ARMS,
    REPLAY_MODE,
    REPLAY_SCHEMA_VERSION,
    load_json_document,
    validate_negative_controls_document,
    validate_replay_cases_document,
)

RESULTS_DIR = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "results"
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text(value: str) -> str:
    compact = re.sub(r"[^\w\s.%/-]", " ", value.casefold())
    return _WHITESPACE_RE.sub(" ", compact).strip()


def _contains_supported_snippet(text: str, snippets: list[str]) -> bool:
    normalized_text = _normalize_text(text)
    return any(_normalize_text(snippet) in normalized_text for snippet in snippets)


def _claim_list(answer: str) -> list[str]:
    claims = extract_claims(answer)
    if claims:
        return claims
    normalized_answer = answer.strip()
    return [normalized_answer] if normalized_answer else []


def evaluate_answer(
    *,
    answer: str,
    required_facts: list[str],
    supported_claims: list[str],
    usefulness_markers: list[str],
    contradiction_checker: NonContradictionChecker,
) -> dict[str, Any]:
    """Evaluate one deterministic answer against the immutable replay oracle."""

    claims = _claim_list(answer)
    unsupported_claims = [
        claim for claim in claims if not _contains_supported_snippet(claim, supported_claims)
    ]
    contradiction_count = contradiction_checker.count(answer)
    correctness_pass = all(_contains_supported_snippet(answer, [fact]) for fact in required_facts)
    usefulness_pass = _contains_supported_snippet(answer, usefulness_markers)
    claim_count = max(1, len(claims))
    unsupported_claim_rate = len(unsupported_claims) / claim_count
    first_pass_ready = (
        correctness_pass and usefulness_pass and contradiction_count == 0 and not unsupported_claims
    )
    return {
        "answer": answer,
        "claims": claims,
        "claim_count": claim_count,
        "unsupported_claims": unsupported_claims,
        "unsupported_claim_rate": round(unsupported_claim_rate, 4),
        "contradiction_count": contradiction_count,
        "correctness_pass": correctness_pass,
        "usefulness_pass": usefulness_pass,
        "first_pass_ready": first_pass_ready,
    }


def _round_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _summarize_arm(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    total_cases = len(case_results)
    total_claims = sum(int(item["claim_count"]) for item in case_results)
    unsupported_claims = sum(len(item["unsupported_claims"]) for item in case_results)
    contradiction_cases = sum(int(item["contradiction_count"]) > 0 for item in case_results)
    correctness_passes = sum(bool(item["correctness_pass"]) for item in case_results)
    readiness_passes = sum(bool(item["first_pass_ready"]) for item in case_results)
    usefulness_passes = sum(bool(item["usefulness_pass"]) for item in case_results)
    return {
        "case_count": total_cases,
        "correctness_pass_rate": _round_rate(correctness_passes, total_cases),
        "unsupported_claim_rate": _round_rate(unsupported_claims, total_claims),
        "contradiction_rate": _round_rate(contradiction_cases, total_cases),
        "first_pass_readiness_proxy": _round_rate(readiness_passes, total_cases),
        "usefulness_floor_rate": _round_rate(usefulness_passes, total_cases),
        "cases": case_results,
    }


def _arm_rank(summary: dict[str, Any]) -> tuple[float, float, float, float, float]:
    return (
        float(summary["first_pass_readiness_proxy"]),
        float(summary["correctness_pass_rate"]),
        -float(summary["unsupported_claim_rate"]),
        -float(summary["contradiction_rate"]),
        float(summary["usefulness_floor_rate"]),
    )


def evaluate_replay_documents(
    *,
    replay_cases: dict[str, Any],
    negative_controls: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate all replay arms and negative controls against the immutable corpus."""

    validated_cases = validate_replay_cases_document(replay_cases)
    validated_controls = validate_negative_controls_document(negative_controls)
    checker = NonContradictionChecker()

    arm_results: dict[str, list[dict[str, Any]]] = {arm: [] for arm in REPLAY_ARMS}
    for case in validated_cases["cases"]:
        for arm in REPLAY_ARMS:
            evaluation = evaluate_answer(
                answer=case["arm_outputs"][arm],
                required_facts=case["required_facts"],
                supported_claims=case["supported_claims"],
                usefulness_markers=case["usefulness_markers"],
                contradiction_checker=checker,
            )
            arm_results[arm].append({"case_id": case["case_id"], **evaluation})

    known_good_controls: list[dict[str, Any]] = []
    flagged_controls = 0
    for control in validated_controls["known_good_controls"]:
        evaluation = evaluate_answer(
            answer=control["answer"],
            required_facts=control["supported_claims"],
            supported_claims=control["supported_claims"],
            usefulness_markers=control["usefulness_markers"],
            contradiction_checker=checker,
        )
        false_positive = (
            bool(evaluation["unsupported_claims"])
            or int(evaluation["contradiction_count"]) > 0
            or not bool(evaluation["usefulness_pass"])
        )
        if false_positive:
            flagged_controls += 1
        known_good_controls.append(
            {
                "control_id": control["control_id"],
                **evaluation,
                "false_positive": false_positive,
            }
        )

    arm_summaries = {arm: _summarize_arm(results) for arm, results in arm_results.items()}
    sorted_arms = sorted(REPLAY_ARMS, key=lambda arm: _arm_rank(arm_summaries[arm]), reverse=True)
    winner_arm = sorted_arms[0]
    baseline = arm_summaries["A0_control"]
    combined = arm_summaries["A3_combined"]
    known_good_false_positive_rate = _round_rate(flagged_controls, len(known_good_controls))
    promotion_ready = (
        winner_arm == "A3_combined"
        and known_good_false_positive_rate == 0.0
        and combined["first_pass_readiness_proxy"] > baseline["first_pass_readiness_proxy"]
        and combined["correctness_pass_rate"] > baseline["correctness_pass_rate"]
        and combined["unsupported_claim_rate"] <= baseline["unsupported_claim_rate"]
        and combined["contradiction_rate"] <= baseline["contradiction_rate"]
    )
    return {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "mode": REPLAY_MODE,
        "network_budget": validated_cases["network_budget"],
        "primary_metrics": list(PRIMARY_METRICS),
        "winner_arm": winner_arm,
        "promotion_ready": promotion_ready,
        "arm_order": sorted_arms,
        "arms": arm_summaries,
        "guardrails": {
            "known_good_false_positive_rate": known_good_false_positive_rate,
            "flagged_known_good_controls": flagged_controls,
            "known_good_control_count": len(known_good_controls),
            "usefulness_floor_rate": {
                arm: arm_summaries[arm]["usefulness_floor_rate"] for arm in REPLAY_ARMS
            },
        },
        "known_good_controls": known_good_controls,
    }


def _resolve_output_path(raw_output: str | None) -> Path | None:
    if not raw_output:
        return None
    candidate = Path(raw_output)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (RESULTS_DIR / candidate).resolve()
    try:
        resolved.relative_to(RESULTS_DIR.resolve())
    except ValueError as exc:
        raise ValueError(
            "--output must stay within artifacts/orchestration/experiments/results"
        ) from exc
    return resolved


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="logic_philosophy_replay_eval",
        description="Run deterministic offline replay scoring for logic/philosophy ablation arms.",
    )
    parser.add_argument("--cases", required=True, help="Path to replay_cases.json")
    parser.add_argument(
        "--negative-controls",
        required=True,
        help="Path to replay_negative_controls.json",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional JSON output path under artifacts/orchestration/experiments/results/. "
            "If omitted, the summary is printed to stdout only."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        replay_cases = load_json_document(Path(args.cases), label="Replay cases")
        negative_controls = load_json_document(
            Path(args.negative_controls),
            label="Replay negative controls",
        )
        summary = evaluate_replay_documents(
            replay_cases=replay_cases,
            negative_controls=negative_controls,
        )
        output_path = _resolve_output_path(args.output)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1

    if output_path is not None:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"FAIL: unable to write replay result: {exc}")
            return 1

    try:
        output_ref = str(output_path.relative_to(REPO_ROOT)) if output_path is not None else None
    except ValueError:
        output_ref = str(output_path)
    print(
        json.dumps(
            {
                "mode": summary["mode"],
                "winner_arm": summary["winner_arm"],
                "promotion_ready": summary["promotion_ready"],
                "network_budget": summary["network_budget"],
                "known_good_false_positive_rate": summary["guardrails"][
                    "known_good_false_positive_rate"
                ],
                "output": output_ref,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
