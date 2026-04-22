#!/usr/bin/env python3
"""Resolve a Docker image telemetry baseline for CI jobs.

The helper prefers the latest successful `main` artifact from the canonical
Docker build workflow and falls back to a checked-in seed baseline when GitHub
lookup or download is unavailable. Remote lookup remains advisory-only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404: bounded gh CLI calls are required to fetch workflow artifacts for CI telemetry (remove-by: 2026-09-30, ref: PR-docker-image-budget-telemetry)
import sys
import tempfile
import zipfile

DEFAULT_ARTIFACT_NAME = "docker-image-telemetry-build"
DEFAULT_ARTIFACT_PAYLOAD_NAME = "docker-image-telemetry.json"
DEFAULT_BRANCH = "main"
DEFAULT_WORKFLOW = "build.yml"
GH_TIMEOUT_SECONDS = 30
MAIN_ARTIFACT_SOURCE = "main-artifact"


def _gh_path() -> str:
    """Return the absolute gh binary path or fail closed."""

    gh_path = shutil.which("gh")
    if gh_path is None:
        raise RuntimeError("gh binary is not available on PATH")
    return gh_path


def _auth_env() -> dict[str, str]:
    """Return a subprocess env that exposes a GitHub token to gh."""

    token = os.getenv("GH_TOKEN", "").strip() or os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required for Docker baseline fetch.")
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    env.setdefault("GITHUB_TOKEN", token)
    return env


def _run_gh(args: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run gh with a resolved binary path and fixed argv."""

    try:
        return subprocess.run(  # nosec B603: argv uses a resolved gh path with fixed GitHub API/auth subcommands only (remove-by: 2026-09-30, ref: PR-docker-image-budget-telemetry)
            [_gh_path(), *args],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"gh command timed out after {GH_TIMEOUT_SECONDS}s: {' '.join(args)}"
        ) from exc


def _ensure_gh_auth(env: dict[str, str]) -> None:
    """Verify the provided token is usable before API calls."""

    _run_gh(["auth", "status"], env=env)


def _github_api_json(endpoint: str, *, env: dict[str, str]) -> object:
    """Fetch JSON from the GitHub REST API through gh."""

    completed = _run_gh(["api", endpoint], env=env)
    return json.loads(completed.stdout)


def _iter_run_artifact_candidates(
    *,
    repo: str,
    workflow: str,
    branch: str,
    artifact_name: str,
    env: dict[str, str],
    per_page: int,
) -> list[tuple[dict[str, object], dict[str, object]]]:
    """Return successful workflow runs that published the target artifact."""

    runs_payload = _github_api_json(
        (
            f"repos/{repo}/actions/workflows/{workflow}/runs"
            f"?branch={branch}&status=success&event=push&per_page={per_page}"
        ),
        env=env,
    )
    if not isinstance(runs_payload, dict):
        raise RuntimeError("GitHub workflow-runs response is not an object.")
    workflow_runs = runs_payload.get("workflow_runs")
    if not isinstance(workflow_runs, list):
        raise RuntimeError("GitHub workflow-runs response is missing workflow_runs.")

    candidates: list[tuple[dict[str, object], dict[str, object]]] = []
    for run in workflow_runs:
        if not isinstance(run, dict):
            continue
        run_id = run.get("id")
        if not isinstance(run_id, int):
            continue
        artifacts_payload = _github_api_json(
            f"repos/{repo}/actions/runs/{run_id}/artifacts",
            env=env,
        )
        if not isinstance(artifacts_payload, dict):
            continue
        artifacts = artifacts_payload.get("artifacts")
        if not isinstance(artifacts, list):
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("name") == artifact_name:
                candidates.append((run, artifact))

    return candidates


def _extract_image_size_bytes(payload: object) -> int:
    """Extract a canonical image_size_bytes value from telemetry payloads."""

    if not isinstance(payload, dict):
        raise RuntimeError("Docker telemetry payload must be a JSON object.")
    if isinstance(payload.get("image_size_bytes"), int):
        return int(payload["image_size_bytes"])
    image_payload = payload.get("image")
    if isinstance(image_payload, dict) and isinstance(image_payload.get("size_bytes"), int):
        return int(image_payload["size_bytes"])
    raise RuntimeError("Docker telemetry payload is missing image_size_bytes.")


def _extract_artifact_payload(archive_path: Path) -> dict[str, object]:
    """Read docker-image-telemetry.json from an artifact archive."""

    with zipfile.ZipFile(archive_path) as archive:
        members = [
            name for name in archive.namelist() if Path(name).name == DEFAULT_ARTIFACT_PAYLOAD_NAME
        ]
        if len(members) != 1:
            raise RuntimeError(
                f"Expected exactly one {DEFAULT_ARTIFACT_PAYLOAD_NAME} in artifact archive; "
                f"found {len(members)}."
            )
        payload = json.loads(archive.read(members[0]).decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Extracted Docker telemetry payload is not an object.")
    return payload


def _download_artifact_payload(
    *,
    repo: str,
    artifact_id: int,
    env: dict[str, str],
) -> dict[str, object]:
    """Download and parse the telemetry artifact payload."""

    with tempfile.TemporaryDirectory(prefix="docker-image-baseline-") as temp_dir:
        archive_path = Path(temp_dir) / "artifact.zip"
        try:
            completed = subprocess.run(  # nosec B603: argv uses resolved gh path with fixed artifact-download subcommand only (remove-by: 2026-09-30, ref: PR-docker-image-budget-telemetry)
                [
                    _gh_path(),
                    "api",
                    f"repos/{repo}/actions/artifacts/{artifact_id}/zip",
                ],
                check=True,
                capture_output=True,
                env=env,
                timeout=GH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "gh artifact download timed out after "
                f"{GH_TIMEOUT_SECONDS}s for artifact {artifact_id}"
            ) from exc
        archive_path.write_bytes(completed.stdout)
        return _extract_artifact_payload(archive_path)


def _normalize_main_artifact_baseline(
    *,
    repo: str,
    workflow: str,
    branch: str,
    run: dict[str, object],
    artifact: dict[str, object],
    raw_payload: dict[str, object],
) -> dict[str, object]:
    """Normalize the remote artifact into the repo baseline schema."""

    image_size_bytes = _extract_image_size_bytes(raw_payload)
    image_size_human = raw_payload.get("image_size_human")
    normalized: dict[str, object] = {
        "baseline_source": MAIN_ARTIFACT_SOURCE,
        "baseline_reference": {
            "artifact_id": artifact["id"],
            "artifact_name": artifact["name"],
            "branch": branch,
            "repo": repo,
            "run_attempt": run.get("run_attempt"),
            "run_id": run["id"],
            "run_number": run.get("run_number"),
            "run_url": run.get("html_url"),
            "workflow": workflow,
        },
        "image_size_bytes": image_size_bytes,
    }
    if isinstance(image_size_human, str) and image_size_human.strip():
        normalized["image_size_human"] = image_size_human.strip()
    return normalized


def fetch_main_artifact_baseline(
    *,
    repo: str,
    workflow: str,
    branch: str,
    artifact_name: str,
    per_page: int,
) -> dict[str, object]:
    """Fetch and normalize the latest successful main-artifact baseline."""

    env = _auth_env()
    _ensure_gh_auth(env)
    candidates = _iter_run_artifact_candidates(
        repo=repo,
        workflow=workflow,
        branch=branch,
        artifact_name=artifact_name,
        env=env,
        per_page=per_page,
    )
    if not candidates:
        raise RuntimeError(
            f"No successful {workflow} run on {branch} published artifact {artifact_name}."
        )

    last_error: RuntimeError | None = None
    for run, artifact in candidates:
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, int):
            last_error = RuntimeError("Artifact payload is missing an integer id.")
            continue
        try:
            raw_payload = _download_artifact_payload(repo=repo, artifact_id=artifact_id, env=env)
            return _normalize_main_artifact_baseline(
                repo=repo,
                workflow=workflow,
                branch=branch,
                run=run,
                artifact=artifact,
                raw_payload=raw_payload,
            )
        except (
            RuntimeError,
            subprocess.CalledProcessError,
            json.JSONDecodeError,
            zipfile.BadZipFile,
        ) as exc:
            last_error = RuntimeError(
                f"Artifact {artifact_id} from run {run.get('id')} is unusable: {exc}"
            )

    if last_error is not None:
        raise RuntimeError(
            "No valid Docker telemetry payload was found in the latest successful "
            f"{workflow} runs on {branch}: {last_error}"
        ) from last_error
    raise AssertionError("Unreachable: candidate loop invariant violated.")


def _write_payload(output_path: Path, payload: dict[str, object]) -> None:
    """Write a normalized JSON payload to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo GitHub identifier")
    parser.add_argument("--output", required=True, help="Resolved baseline JSON output path")
    parser.add_argument(
        "--fallback-json",
        required=True,
        help="Checked-in repo fallback baseline JSON path",
    )
    parser.add_argument(
        "--workflow",
        default=DEFAULT_WORKFLOW,
        help="Workflow file used for the canonical main baseline",
    )
    parser.add_argument(
        "--branch",
        default=DEFAULT_BRANCH,
        help="Branch used for the canonical main baseline",
    )
    parser.add_argument(
        "--artifact-name",
        default=DEFAULT_ARTIFACT_NAME,
        help="Artifact name expected from the canonical workflow run",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=20,
        help="Number of successful runs to search before falling back",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_path = Path(args.output)
    fallback_path = Path(args.fallback_json)

    try:
        payload = fetch_main_artifact_baseline(
            repo=args.repo,
            workflow=args.workflow,
            branch=args.branch,
            artifact_name=args.artifact_name,
            per_page=args.per_page,
        )
    except (
        RuntimeError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as exc:
        if not fallback_path.exists():
            print(
                "docker baseline fetch failed and fallback baseline is missing: "
                f"{fallback_path} ({exc})",
                file=sys.stderr,
            )
            return 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fallback_path, output_path)
        print(
            "Advisory: using repo-seed-fallback baseline because latest successful "
            f"main artifact fetch failed: {exc}",
            file=sys.stderr,
        )
        return 0

    _write_payload(output_path, payload)
    print(
        "Resolved Docker image baseline from latest successful main artifact: " f"{output_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
