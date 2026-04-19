#!/usr/bin/env python3
"""Collect deterministic Docker image telemetry for CI evidence.

RU: Скрипт собирает advisory-only telemetry по размеру образа, крупнейшим слоям
и build-context входам для PR-visible отчётов.
EN: Collect advisory-only telemetry for image size, largest layers, and
build-context inputs so Docker lanes emit deterministic evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess  # nosec B404: bounded local Docker inspection is required for CI telemetry evidence (remove-by: 2026-09-30, ref: PR-docker-telemetry-baseline)
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKER_BINARY = shutil.which("docker")
DOCKER_TIMEOUT_SECONDS = 60
REDACTED_CREATED_BY = "<redacted: docker history command hidden>"
SIZE_UNITS = {
    "B": 1,
    "KB": 1_000,
    "MB": 1_000_000,
    "GB": 1_000_000_000,
    "TB": 1_000_000_000_000,
}


@dataclass(frozen=True)
class LayerTelemetry:
    """Single Docker history row rendered as deterministic telemetry."""

    created_by: str
    size_bytes: int
    size_human: str


@dataclass(frozen=True)
class BuildContextEvidence:
    """Deterministic build-context evidence from repo-truth files."""

    dockerfile_path: str
    dockerignore_path: str
    copy_inputs: tuple[str, ...]
    dockerignore_allowlist: tuple[str, ...]


@dataclass(frozen=True)
class BaselineComparison:
    """Advisory baseline comparison; never fails the lane in this wave."""

    baseline_path: str | None
    baseline_size_bytes: int | None
    size_delta_bytes: int | None
    regression_warning: bool


@dataclass(frozen=True)
class ImageTelemetryReport:
    """Top-level advisory telemetry payload."""

    advisory_only: bool
    image_ref: str
    image_size_bytes: int
    image_size_human: str
    largest_layers: tuple[LayerTelemetry, ...]
    build_context: BuildContextEvidence
    baseline: BaselineComparison
    warnings: tuple[str, ...]


def _run_docker(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run Docker with a resolved binary path and fixed argv."""

    if DOCKER_BINARY is None:
        raise RuntimeError("docker binary is not available on PATH")
    try:
        return subprocess.run(  # nosec B603: argv uses resolved docker path with fixed inspect/history subcommands only (remove-by: 2026-09-30, ref: PR-docker-telemetry-baseline)
            [DOCKER_BINARY, *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"docker command timed out after {DOCKER_TIMEOUT_SECONDS}s: {' '.join(args)}"
        ) from exc


def _human_size_to_bytes(size_text: str) -> int:
    """Parse Docker history size text into bytes."""

    value = size_text.strip()
    if value in {"", "0", "0B"}:
        return 0
    match = re.fullmatch(r"(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z]+)", value)
    if match is None:
        raise ValueError(f"Unsupported Docker size format: {size_text}")
    unit_aliases = {
        "B": "B",
        "K": "KB",
        "KB": "KB",
        "M": "MB",
        "MB": "MB",
        "G": "GB",
        "GB": "GB",
        "T": "TB",
        "TB": "TB",
    }
    normalized_unit = unit_aliases.get(match.group("unit").upper())
    if normalized_unit is None:
        raise ValueError(f"Unsupported Docker size format: {size_text}")
    return int(float(match.group("number")) * SIZE_UNITS[normalized_unit])


def _bytes_to_human(size_bytes: int) -> str:
    """Render bytes using decimal Docker-style units."""

    if size_bytes < SIZE_UNITS["KB"]:
        return f"{size_bytes} B"
    if size_bytes < SIZE_UNITS["MB"]:
        return f"{size_bytes / SIZE_UNITS['KB']:.2f} KB"
    if size_bytes < SIZE_UNITS["GB"]:
        return f"{size_bytes / SIZE_UNITS['MB']:.2f} MB"
    return f"{size_bytes / SIZE_UNITS['GB']:.2f} GB"


def _read_image_size_bytes(image_ref: str) -> int:
    """Read the total image size from docker image inspect."""

    result = _run_docker(["image", "inspect", image_ref])
    payload = json.loads(result.stdout)
    if not payload:
        raise RuntimeError(f"Docker inspect returned no payload for {image_ref}")
    size_value = payload[0].get("Size")
    if not isinstance(size_value, int):
        raise RuntimeError(f"Docker inspect returned invalid Size for {image_ref}")
    return size_value


def _read_history_rows(image_ref: str) -> list[LayerTelemetry]:
    """Read Docker history and normalize the largest layers."""

    result = _run_docker(["history", "--no-trunc", "--format", "{{json .}}", image_ref])
    rows: list[LayerTelemetry] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        rows.append(
            LayerTelemetry(
                created_by=REDACTED_CREATED_BY,
                size_bytes=_human_size_to_bytes(str(payload.get("Size", "0B"))),
                size_human=str(payload.get("Size", "0B")).strip() or "0B",
            )
        )
    return rows


def _logical_lines(text: str) -> list[str]:
    """Join Dockerfile continuation lines for simple COPY parsing."""

    logical_lines: list[str] = []
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not current:
            current = line
        else:
            current = f"{current} {line.lstrip()}"
        if line.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        logical_lines.append(current)
        current = ""
    if current:
        logical_lines.append(current)
    return logical_lines


def _parse_copy_inputs(dockerfile_path: Path) -> tuple[str, ...]:
    """Extract local COPY inputs from the Dockerfile as concise evidence."""

    inputs: list[str] = []
    for line in _logical_lines(dockerfile_path.read_text(encoding="utf-8")):
        stripped = line.strip()
        if not stripped.startswith("COPY "):
            continue
        copy_args = stripped[len("COPY ") :].lstrip()
        if copy_args.startswith("["):
            try:
                payload = json.loads(copy_args)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, list) or len(payload) < 2:
                continue
            for source in payload[:-1]:
                if isinstance(source, str):
                    inputs.append(source)
            continue
        # RU: shell-form COPY поддерживается ограниченной эвристикой; флаги
        # `--from` остаются non-local inputs и intentionally исключаются.
        # EN: shell-form COPY uses a bounded heuristic; `--from` inputs are
        # treated as non-local and intentionally excluded from build-context evidence.
        tokens = shlex.split(copy_args)
        if any(token.startswith("--from=") for token in tokens):
            continue
        filtered_tokens = [token for token in tokens if not token.startswith("--")]
        if len(filtered_tokens) < 2:
            continue
        for source in filtered_tokens[:-1]:
            inputs.append(source)
    return tuple(dict.fromkeys(inputs))


def _parse_dockerignore_allowlist(dockerignore_path: Path) -> tuple[str, ...]:
    """Collect explicit allowlist lines from .dockerignore."""

    allowlist: list[str] = []
    for raw_line in dockerignore_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("!"):
            continue
        allowlist.append(line)
    return tuple(allowlist)


def _load_baseline_size_bytes(baseline_path: Path | None) -> int | None:
    """Load a prior telemetry baseline if one is supplied."""

    if baseline_path is None or not baseline_path.exists():
        return None
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unsupported baseline payload shape: {baseline_path}")
    if isinstance(payload.get("image_size_bytes"), int):
        return int(payload["image_size_bytes"])
    image_payload = payload.get("image")
    if isinstance(image_payload, dict) and isinstance(image_payload.get("size_bytes"), int):
        return int(image_payload["size_bytes"])
    raise RuntimeError(f"Unsupported baseline payload shape: {baseline_path}")


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer for CLI arguments."""

    parsed_value = int(value)
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed_value


def collect_telemetry(
    *,
    image_ref: str,
    dockerfile_path: Path,
    dockerignore_path: Path,
    top_layers: int,
    baseline_path: Path | None,
) -> ImageTelemetryReport:
    """Collect advisory-only telemetry for the given local image reference."""

    image_size_bytes = _read_image_size_bytes(image_ref)
    history_rows = sorted(
        _read_history_rows(image_ref),
        key=lambda row: row.size_bytes,
        reverse=True,
    )[:top_layers]
    copy_inputs = _parse_copy_inputs(dockerfile_path)
    dockerignore_allowlist = _parse_dockerignore_allowlist(dockerignore_path)

    warnings: list[str] = []
    baseline_size_bytes = _load_baseline_size_bytes(baseline_path)
    size_delta_bytes: int | None = None
    regression_warning = False
    if baseline_path is None:
        warnings.append("No baseline JSON was provided; telemetry remains advisory-only.")
    elif baseline_size_bytes is None:
        warnings.append(
            f"Baseline JSON is missing or absent at {baseline_path}; telemetry remains advisory-only."
        )
    else:
        size_delta_bytes = image_size_bytes - baseline_size_bytes
        if size_delta_bytes > 0:
            regression_warning = True
            warnings.append(
                "Image size increased relative to the supplied baseline; "
                "warning-only mode keeps the lane non-blocking."
            )

    return ImageTelemetryReport(
        advisory_only=True,
        image_ref=image_ref,
        image_size_bytes=image_size_bytes,
        image_size_human=_bytes_to_human(image_size_bytes),
        largest_layers=tuple(history_rows),
        build_context=BuildContextEvidence(
            dockerfile_path=str(dockerfile_path),
            dockerignore_path=str(dockerignore_path),
            copy_inputs=copy_inputs,
            dockerignore_allowlist=dockerignore_allowlist,
        ),
        baseline=BaselineComparison(
            baseline_path=str(baseline_path) if baseline_path is not None else None,
            baseline_size_bytes=baseline_size_bytes,
            size_delta_bytes=size_delta_bytes,
            regression_warning=regression_warning,
        ),
        warnings=tuple(warnings),
    )


def render_markdown(report: ImageTelemetryReport) -> str:
    """Render a concise Markdown summary for PR-visible workflow evidence."""

    lines = [
        "# Docker Image Telemetry",
        "",
        f"- Image: `{report.image_ref}`",
        f"- Advisory only: `{str(report.advisory_only).lower()}`",
        f"- Size: `{report.image_size_human}` (`{report.image_size_bytes}` bytes)",
    ]
    if report.baseline.baseline_size_bytes is None:
        lines.append("- Baseline: `not provided`")
    else:
        baseline_human = _bytes_to_human(report.baseline.baseline_size_bytes)
        lines.append(
            f"- Baseline: `{baseline_human}` (`{report.baseline.baseline_size_bytes}` bytes)"
        )
    if report.baseline.size_delta_bytes is not None:
        delta = report.baseline.size_delta_bytes
        sign = "+" if delta >= 0 else "-"
        lines.append(
            f"- Delta vs baseline: `{sign}{_bytes_to_human(abs(delta))}` (`{delta}` bytes)"
        )
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report.warnings)

    lines.extend(
        ["", "## Largest Layers", "", "| Size | Command (redacted) |", "| --- | --- |"]
    )
    for layer in report.largest_layers:
        command = layer.created_by.replace("|", "\\|")
        lines.append(f"| `{layer.size_human}` | `{command}` |")

    lines.extend(
        [
            "",
            "## Build Context Evidence",
            "",
            f"- Dockerfile: `{report.build_context.dockerfile_path}`",
            f"- Dockerignore: `{report.build_context.dockerignore_path}`",
            "- Local COPY inputs: "
            + ", ".join(f"`{item}`" for item in report.build_context.copy_inputs),
            "- Dockerignore allowlist: "
            + ", ".join(f"`{item}`" for item in report.build_context.dockerignore_allowlist),
            "",
        ]
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-ref", required=True, help="Local Docker image reference")
    parser.add_argument(
        "--dockerfile",
        default="Dockerfile",
        help="Dockerfile path relative to repo root",
    )
    parser.add_argument(
        "--dockerignore",
        default=".dockerignore",
        help=".dockerignore path relative to repo root",
    )
    parser.add_argument(
        "--baseline-json",
        default=None,
        help="Optional prior telemetry JSON for advisory regression comparison",
    )
    parser.add_argument(
        "--top-layers",
        type=_positive_int,
        default=5,
        help="Number of largest layers to report",
    )
    parser.add_argument("--json-out", required=True, help="Output JSON report path")
    parser.add_argument("--markdown-out", required=True, help="Output Markdown report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = collect_telemetry(
            image_ref=args.image_ref,
            dockerfile_path=REPO_ROOT / args.dockerfile,
            dockerignore_path=REPO_ROOT / args.dockerignore,
            top_layers=args.top_layers,
            baseline_path=REPO_ROOT / args.baseline_json if args.baseline_json else None,
        )
    except (RuntimeError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"docker_image_telemetry failed: {exc}", file=sys.stderr)
        return 1

    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    json_out.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    markdown_out.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
