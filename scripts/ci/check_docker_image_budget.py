#!/usr/bin/env python3
"""Enforce the production Docker image hard-budget policy.

RU: Скрипт проверяет telemetry report против фиксированного hard-budget policy
и пишет PR-visible evidence в JSON/Markdown.
EN: Validate the Docker telemetry report against the checked-in hard-budget
policy and emit PR-visible JSON/Markdown evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys


@dataclass(frozen=True)
class DockerImageBudgetPolicy:
    """Checked-in hard-budget policy for the production backend image."""

    budget_name: str
    budget_version: int
    budget_scope: str
    max_image_size_bytes: int
    max_positive_delta_bytes: int
    baseline_reference: dict[str, object]
    policy_note: str


@dataclass(frozen=True)
class BudgetCheckResult:
    """Deterministic budget-check result used by CI and PR summaries."""

    passed: bool
    image_ref: str
    image_size_bytes: int
    baseline_size_bytes: int | None
    baseline_source: str | None
    size_delta_bytes: int | None
    max_image_size_bytes: int
    max_positive_delta_bytes: int
    violations: tuple[str, ...]
    policy: DockerImageBudgetPolicy


def _load_json_object(path: Path, *, description: str) -> dict[str, object]:
    """Load a JSON object and fail closed on malformed payloads."""

    if not path.exists() or not path.is_file():
        raise RuntimeError(f"{description} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, PermissionError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to read {description}: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{description} must be a JSON object: {path}")
    return payload


def _read_non_negative_int(payload: dict[str, object], key: str, *, description: str) -> int:
    """Return a non-negative integer field from a payload."""

    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RuntimeError(f"{description} field {key!r} must be a non-negative integer.")
    return value


def load_budget_policy(path: Path) -> DockerImageBudgetPolicy:
    """Parse the checked-in Docker budget policy."""

    payload = _load_json_object(path, description="Docker image budget policy")
    budget_name = payload.get("budget_name")
    budget_scope = payload.get("budget_scope")
    policy_note = payload.get("policy_note")
    baseline_reference = payload.get("baseline_reference")
    budget_version = payload.get("budget_version")

    if not isinstance(budget_name, str) or not budget_name.strip():
        raise RuntimeError("Docker image budget policy requires a non-empty budget_name.")
    if not isinstance(budget_scope, str) or not budget_scope.strip():
        raise RuntimeError("Docker image budget policy requires a non-empty budget_scope.")
    if not isinstance(policy_note, str) or not policy_note.strip():
        raise RuntimeError("Docker image budget policy requires a non-empty policy_note.")
    if (
        not isinstance(budget_version, int)
        or isinstance(budget_version, bool)
        or budget_version <= 0
    ):
        raise RuntimeError("Docker image budget policy requires a positive integer budget_version.")
    if not isinstance(baseline_reference, dict) or not baseline_reference:
        raise RuntimeError("Docker image budget policy requires a baseline_reference object.")

    return DockerImageBudgetPolicy(
        budget_name=budget_name.strip(),
        budget_version=budget_version,
        budget_scope=budget_scope.strip(),
        max_image_size_bytes=_read_non_negative_int(
            payload,
            "max_image_size_bytes",
            description="Docker image budget policy",
        ),
        max_positive_delta_bytes=_read_non_negative_int(
            payload,
            "max_positive_delta_bytes",
            description="Docker image budget policy",
        ),
        baseline_reference=baseline_reference,
        policy_note=policy_note.strip(),
    )


def evaluate_budget(
    *,
    telemetry_path: Path,
    budget_path: Path,
) -> BudgetCheckResult:
    """Evaluate the Docker telemetry report against the hard-budget policy."""

    telemetry_payload = _load_json_object(telemetry_path, description="Docker image telemetry")
    image_ref = telemetry_payload.get("image_ref")
    if not isinstance(image_ref, str) or not image_ref.strip():
        raise RuntimeError("Docker image telemetry requires a non-empty image_ref.")

    baseline_payload = telemetry_payload.get("baseline")
    if not isinstance(baseline_payload, dict):
        raise RuntimeError("Docker image telemetry requires a baseline object.")

    policy = load_budget_policy(budget_path)
    image_size_bytes = _read_non_negative_int(
        telemetry_payload,
        "image_size_bytes",
        description="Docker image telemetry",
    )

    baseline_size_bytes_raw = baseline_payload.get("baseline_size_bytes")
    if baseline_size_bytes_raw is None:
        baseline_size_bytes = None
    elif (
        isinstance(baseline_size_bytes_raw, int)
        and not isinstance(baseline_size_bytes_raw, bool)
        and baseline_size_bytes_raw >= 0
    ):
        baseline_size_bytes = baseline_size_bytes_raw
    else:
        raise RuntimeError(
            "Docker image telemetry baseline_size_bytes must be null or a non-negative integer."
        )

    baseline_source = baseline_payload.get("baseline_source")
    if baseline_source is not None and not isinstance(baseline_source, str):
        raise RuntimeError("Docker image telemetry baseline_source must be null or a string.")

    size_delta_raw = baseline_payload.get("size_delta_bytes")
    if size_delta_raw is None:
        size_delta_bytes = None
    elif isinstance(size_delta_raw, int) and not isinstance(size_delta_raw, bool):
        size_delta_bytes = size_delta_raw
    else:
        raise RuntimeError("Docker image telemetry size_delta_bytes must be null or an integer.")

    violations: list[str] = []
    if image_size_bytes > policy.max_image_size_bytes:
        violations.append(
            "Image size exceeds the absolute hard-budget cap "
            f"({image_size_bytes} > {policy.max_image_size_bytes})."
        )
    if size_delta_bytes is not None and size_delta_bytes > policy.max_positive_delta_bytes:
        violations.append(
            "Image size delta exceeds the allowed positive regression budget "
            f"({size_delta_bytes} > {policy.max_positive_delta_bytes})."
        )

    return BudgetCheckResult(
        passed=not violations,
        image_ref=image_ref.strip(),
        image_size_bytes=image_size_bytes,
        baseline_size_bytes=baseline_size_bytes,
        baseline_source=baseline_source.strip() if isinstance(baseline_source, str) else None,
        size_delta_bytes=size_delta_bytes,
        max_image_size_bytes=policy.max_image_size_bytes,
        max_positive_delta_bytes=policy.max_positive_delta_bytes,
        violations=tuple(violations),
        policy=policy,
    )


def render_markdown(result: BudgetCheckResult) -> str:
    """Render a concise Markdown summary for the hard-budget result."""

    lines = [
        "# Docker Image Budget Check",
        "",
        f"- Passed: `{str(result.passed).lower()}`",
        f"- Image: `{result.image_ref}`",
        f"- Image size bytes: `{result.image_size_bytes}`",
        f"- Absolute cap bytes: `{result.max_image_size_bytes}`",
        f"- Positive delta cap bytes: `{result.max_positive_delta_bytes}`",
    ]
    if result.baseline_size_bytes is not None:
        lines.append(f"- Baseline size bytes: `{result.baseline_size_bytes}`")
    if result.baseline_source is not None:
        lines.append(f"- Baseline source: `{result.baseline_source}`")
    if result.size_delta_bytes is not None:
        lines.append(f"- Delta vs baseline bytes: `{result.size_delta_bytes}`")

    lines.extend(
        [
            f"- Policy: `{result.policy.budget_name}` v`{result.policy.budget_version}`",
            f"- Scope: `{result.policy.budget_scope}`",
            "",
        ]
    )
    if result.violations:
        lines.extend(["## Violations", ""])
        lines.extend(f"- {violation}" for violation in result.violations)
    else:
        lines.extend(["## Result", "", "- Budget check passed within policy."])
    return "\n".join(lines)


def render_failure_markdown(*, error: str, telemetry_path: Path, budget_path: Path) -> str:
    """Render fail-closed Markdown evidence for malformed inputs."""

    return "\n".join(
        [
            "# Docker Image Budget Check",
            "",
            "- Passed: `false`",
            f"- Telemetry input: `{telemetry_path}`",
            f"- Budget policy input: `{budget_path}`",
            "",
            "## Fail-Closed Error",
            "",
            f"- {error}",
        ]
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--telemetry-json", required=True, help="Path to docker-image-telemetry.json"
    )
    parser.add_argument(
        "--budget-json", required=True, help="Path to checked-in budget policy JSON"
    )
    parser.add_argument("--json-out", required=True, help="Path to JSON output artifact")
    parser.add_argument("--markdown-out", required=True, help="Path to Markdown output artifact")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    telemetry_path = Path(args.telemetry_json)
    budget_path = Path(args.budget_json)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    try:
        result = evaluate_budget(
            telemetry_path=telemetry_path,
            budget_path=budget_path,
        )
    except RuntimeError as exc:
        failure_payload = {
            "passed": False,
            "error": str(exc),
            "telemetry_json": str(telemetry_path),
            "budget_json": str(budget_path),
        }
        json_out.write_text(json.dumps(failure_payload, indent=2, sort_keys=True), encoding="utf-8")
        markdown_out.write_text(
            render_failure_markdown(
                error=str(exc),
                telemetry_path=telemetry_path,
                budget_path=budget_path,
            ),
            encoding="utf-8",
        )
        print(f"check_docker_image_budget failed: {exc}", file=sys.stderr)
        return 1

    json_out.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")
    markdown_out.write_text(render_markdown(result), encoding="utf-8")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
