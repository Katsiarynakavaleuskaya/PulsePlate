"""Deterministic `docker compose config -q` checks for METATRON lab profiles."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404: operator-only docker compose config -q; argv from fixed tokens + docker via shutil.which (remove-by: 2026-07-01, ref: PR-1366)
from pathlib import Path

LAB_PROFILES: tuple[str, ...] = ("metatron-lab-isolation", "metatron-lab-runner")


def repo_root() -> Path:
    """Repository root (parent of `deploy/` and `scripts/`)."""
    return Path(__file__).resolve().parents[2]


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
        "1. Read ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06 and "
        "METATRON_LAB_RULES_OF_ENGAGEMENT.",
        "2. Store lab outputs only under artifacts/security_lab/ (gitignored).",
        "3. Use docker compose with --profile metatron-lab-isolation or metatron-lab-runner; "
        "default compose has no lab services.",
    ]
