"""Deterministic `docker compose config -q` checks for METATRON lab profiles."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404: operator-only docker compose config -q; argv from fixed tokens + docker via shutil.which (remove-by: 2026-07-01, ref: PR-1366)
import sys
from pathlib import Path

LAB_PROFILES: tuple[str, ...] = ("metatron-lab-isolation", "metatron-lab-runner")

# Single place for checklist strings (operator-facing; rename docs in one place if paths change).
METATRON_LAB_ADR_STEM = "ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06"
METATRON_LAB_ROE_STEM = "METATRON_LAB_RULES_OF_ENGAGEMENT"
METATRON_LAB_ARTIFACTS_HINT = "artifacts/security_lab/"
_STDERR_SNIPPET_MAX = 500


def repo_root() -> Path:
    """Resolve repo root by locating `deploy/metatron-lab/docker-compose.yaml` (not `parents[N]`)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        marker = parent / "deploy" / "metatron-lab" / "docker-compose.yaml"
        if marker.is_file():
            return parent
    return here.parents[2]


def compose_file_for_repo(root: Path) -> Path:
    return root / "deploy" / "metatron-lab" / "docker-compose.yaml"


def run_compose_config_q(root: Path, profile: str, docker_bin: str) -> int:
    """Run `docker compose … config -q` for one profile; return process exit code."""
    compose = compose_file_for_repo(root)
    cmd = [
        docker_bin,
        "compose",
        "-f",
        str(compose),
        "--profile",
        profile,
        "config",
        "-q",
    ]
    completed = subprocess.run(  # nosec B603: no shell; argv is docker + fixed compose flags + repo compose path (remove-by: 2026-07-01, ref: PR-1366)
        cmd,
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr_snippet = (completed.stderr or "").strip()
        if len(stderr_snippet) > _STDERR_SNIPPET_MAX:
            stderr_snippet = f"{stderr_snippet[: _STDERR_SNIPPET_MAX - 3]}..."
        print(
            f"[metatron-lab] docker compose config -q failed for profile {profile!r} "
            f"(rc={completed.returncode})",
            file=sys.stderr,
        )
        if stderr_snippet:
            print(f"[metatron-lab] stderr: {stderr_snippet}", file=sys.stderr)
    return int(completed.returncode)


def validate_all_profiles() -> int:
    """Validate all lab profiles; return 0 on success, 2 if docker is missing, else first non-zero rc."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return 2
    root = repo_root()
    for profile in LAB_PROFILES:
        rc = run_compose_config_q(root, profile, docker_bin)
        if rc != 0:
            return rc
    return 0


def operator_checklist_lines() -> list[str]:
    """Short operator reminders (stdout only; no secrets)."""
    return [
        f"1. Read {METATRON_LAB_ADR_STEM} and {METATRON_LAB_ROE_STEM}.",
        f"2. Store lab outputs only under {METATRON_LAB_ARTIFACTS_HINT} (gitignored).",
        "3. Use docker compose with --profile metatron-lab-isolation or metatron-lab-runner; "
        "default compose has no lab services.",
    ]
