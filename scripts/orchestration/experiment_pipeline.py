#!/usr/bin/env python3
"""Run the governed experiment completion flow.

RU: Последовательно запускает runner, promotion и notification, не расширяя их
полномочия.
EN: Sequences runner, promotion, and notification without widening their
authority boundaries.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
from typing import Any, Callable

try:
    from scripts.orchestration.context_pack import normalize_repo_path
    from scripts.orchestration.experiment_contract import (
        ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
        validate_experiment_packet,
    )
    from scripts.orchestration import experiment_notify
    from scripts.orchestration import experiment_promote
    from scripts.orchestration import experiment_runner
except ModuleNotFoundError as exc:  # pragma: no cover - direct script invocation guard.
    if exc.name != "scripts":
        raise
    print(
        "FAIL: run as `python -m scripts.orchestration.experiment_pipeline` from repo root.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


EMAIL_REPORT_RECIPIENT = experiment_notify.V1_EMAIL_RECIPIENT


class ExperimentPipelineError(RuntimeError):
    """Pipeline orchestration failed without exposing child process details."""


def _read_packet(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExperimentPipelineError("Experiment pipeline packet is invalid.") from exc
    if not isinstance(payload, dict):
        raise ExperimentPipelineError("Experiment pipeline packet is invalid.")
    try:
        validated_packet: dict[str, Any] = validate_experiment_packet(payload)
        return validated_packet
    except ValueError as exc:
        raise ExperimentPipelineError("Experiment pipeline packet is invalid.") from exc


def _repo_ref(path: Path) -> str:
    try:
        repo_ref: str = normalize_repo_path(path)
        return repo_ref
    except ValueError:
        return "[artifact-path]"


def _default_result_path(experiment_id: str) -> Path:
    artifact_dir: Path = experiment_runner.RESULT_ARTIFACT_DIR
    return artifact_dir / f"{experiment_id}.json"


def _default_promotion_path(experiment_id: str) -> Path:
    artifact_dir: Path = experiment_promote.PROMOTION_ARTIFACT_DIR
    return artifact_dir / f"{experiment_id}.json"


def _promotion_output_path(raw_output: str | None, experiment_id: str) -> Path:
    """Mirror promotion output path selection without widening write permissions."""

    artifact_dir: Path = experiment_promote.PROMOTION_ARTIFACT_DIR.resolve()
    if raw_output:
        candidate = Path(raw_output).expanduser()
        if not candidate.is_absolute():
            candidate = artifact_dir / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(artifact_dir)
        except ValueError as exc:
            raise ExperimentPipelineError(
                "Experiment promotion output must stay within governed artifact directory."
            ) from exc
        return candidate
    return _default_promotion_path(experiment_id)


def _run_stage(
    stage: str,
    stage_main: Callable[[list[str]], int],
    argv: list[str],
) -> dict[str, Any]:
    """Run a child stage while preventing child stdout leakage."""

    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = stage_main(argv)
    except Exception as exc:
        raise ExperimentPipelineError(f"Experiment pipeline {stage} stage failed.") from exc
    if exit_code != 0:
        raise ExperimentPipelineError(f"Experiment pipeline {stage} stage failed.")
    raw_output = stdout.getvalue().strip()
    if not raw_output:
        return {}
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ExperimentPipelineError(
            f"Experiment pipeline {stage} stage output is invalid."
        ) from exc
    if not isinstance(payload, dict):
        raise ExperimentPipelineError(f"Experiment pipeline {stage} stage output is invalid.")
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="experiment_pipeline",
        description=(
            "Run governed experiment runner, promotion, and notification stages. "
            "Email reports are explicit opt-in and fixed to the governed v1 recipient."
        ),
    )
    parser.add_argument("--packet", required=True, help="Experiment packet JSON path.")
    parser.add_argument("--candidate-patch", required=True, help="Unified diff patch path.")
    parser.add_argument(
        "--promotion-output",
        default=None,
        help=(
            "Optional promotion decision JSON path under "
            "artifacts/orchestration/experiments/promotions/. "
            "Defaults to artifacts/orchestration/experiments/promotions/<id>.json"
        ),
    )
    parser.add_argument(
        "--email-reports",
        action="store_true",
        help="After local notification rendering, send the redacted report to the governed v1 recipient.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        packet_path = Path(args.packet).expanduser().resolve()
        candidate_patch_path = Path(args.candidate_patch).expanduser().resolve()
        packet = _read_packet(packet_path)
        if packet.get("runner_mode") == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
            raise ExperimentPipelineError(
                "Oracle-only governance reviewer packets are runner-only review evidence "
                "and must not enter promotion pipeline."
            )
        experiment_id = packet["experiment_id"]
        result_path = _default_result_path(experiment_id)
        promotion_path = _promotion_output_path(args.promotion_output, experiment_id)
        promotion_output_arg = (
            str(Path(args.promotion_output).expanduser())
            if args.promotion_output
            else str(promotion_path)
        )

        _run_stage(
            "runner",
            experiment_runner.main,
            [
                "--packet",
                str(packet_path),
                "--candidate-patch",
                str(candidate_patch_path),
                "--output",
                str(result_path),
            ],
        )
        _run_stage(
            "promotion",
            experiment_promote.main,
            [
                "--packet",
                str(packet_path),
                "--result",
                str(result_path),
                "--output",
                promotion_output_arg,
            ],
        )
        notify_args = [
            "--packet",
            str(packet_path),
            "--result",
            str(result_path),
            "--promotion",
            str(promotion_path),
        ]
        if args.email_reports:
            notify_args.extend(["--email", "--email-to", EMAIL_REPORT_RECIPIENT])
        notify_payload = _run_stage("notification", experiment_notify.main, notify_args)
    except ExperimentPipelineError as exc:
        print(f"FAIL: {exc}")
        return 1
    except OSError:
        print("FAIL: experiment pipeline artifact path is invalid.")
        return 1

    print(
        json.dumps(
            {
                "email_reports": bool(args.email_reports),
                "email_recipient": "governed-v1-recipient" if args.email_reports else None,
                "experiment_id": experiment_id,
                "notification": notify_payload.get("output"),
                "email_audit": notify_payload.get("email_audit"),
                "promotion": _repo_ref(promotion_path),
                "result": _repo_ref(result_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
