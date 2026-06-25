"""Workspace and artifact helpers for PR-2 creative-code patch building."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404: fixed git subprocess wrappers only (remove-by: 2026-07-31, ref: PR-2)
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code" / "patch_runs"
CHECKOUT_DIRNAME = "generation_checkout"

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


class CreativeCodePatchWorkspaceError(ValueError):
    """Raised when PR-2 workspace/artifact containment fails."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    components: list[Path] = []
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeCodePatchWorkspaceError(f"{label} must not traverse symlinks.")


def ensure_artifact_root() -> Path:
    """Create and return the resolved PR-2 artifact root."""

    _reject_symlink_components(ARTIFACT_ROOT, label="artifact root")
    try:
        ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodePatchWorkspaceError("artifact root could not be created.") from exc
    _reject_symlink_components(ARTIFACT_ROOT, label="artifact root")
    root = ARTIFACT_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise CreativeCodePatchWorkspaceError("artifact root must be a directory.")
    return root


def resolve_run_dir(run_id: str, *, create: bool = False) -> Path:
    """Resolve a run directory below the creative-code patch artifact root."""

    normalized = run_id.strip()
    if not normalized or not RUN_ID_RE.fullmatch(normalized):
        raise CreativeCodePatchWorkspaceError("run id must be a safe identifier.")
    root = ensure_artifact_root()
    run_dir = ARTIFACT_ROOT / normalized
    _reject_symlink_components(run_dir, label="run directory")
    candidate = run_dir.resolve(strict=False)
    if not _is_relative_to(candidate, root):
        raise CreativeCodePatchWorkspaceError("run directory must stay under artifact root.")
    if create:
        run_dir.mkdir(parents=True, exist_ok=True)
    try:
        resolved = run_dir.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodePatchWorkspaceError("run directory must exist.") from exc
    if not _is_relative_to(resolved, root):
        raise CreativeCodePatchWorkspaceError("run directory must stay under artifact root.")
    if not resolved.is_dir():
        raise CreativeCodePatchWorkspaceError("run directory must be a directory.")
    return resolved


def resolve_run_file(run_dir: Path, filename: str, *, for_write: bool = False) -> Path:
    """Resolve a direct file below a contained run directory."""

    if "/" in filename or "\\" in filename or filename in {"", ".", ".."}:
        raise CreativeCodePatchWorkspaceError("artifact filename must be direct.")
    root = ensure_artifact_root()
    run_root = run_dir.resolve(strict=True)
    if not _is_relative_to(run_root, root):
        raise CreativeCodePatchWorkspaceError("run directory must stay under artifact root.")
    target = run_root / filename
    _reject_symlink_components(target.parent, label="artifact file parent")
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            raise CreativeCodePatchWorkspaceError("artifact file must not be a symlink.")
        if not target.is_file():
            raise CreativeCodePatchWorkspaceError("artifact path must be a file.")
    if for_write:
        target.parent.mkdir(parents=True, exist_ok=True)
    return target


def write_json_atomic(path: Path, payload: Any) -> None:
    """Write JSON atomically inside an already-contained run directory."""

    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(payload, temp_file, sort_keys=True, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodePatchWorkspaceError(f"Unable to read JSON artifact: {path.name}") from exc


def resolve_git_binary() -> str:
    git_binary = shutil.which("git")
    if not git_binary:
        raise CreativeCodePatchWorkspaceError("git binary is required.")
    return git_binary


def git_env_without_parent_state() -> dict[str, str]:
    """Return a stable env for git subprocesses."""

    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key not in {"PYTHONPATH"}
    }


def run_git(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git with a resolved binary, no shell, and bounded capture."""

    process = subprocess.run(  # nosec B603: absolute git binary with bounded argv for isolated PR-2 checkouts (remove-by: 2026-07-31, ref: PR-2)
        [resolve_git_binary(), *args],
        cwd=str(cwd),
        env=git_env_without_parent_state(),
        capture_output=True,
        text=True,
        check=False,
        input=input_text,
    )
    if check and process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "unknown git failure"
        raise CreativeCodePatchWorkspaceError(f"git {' '.join(args)} failed: {stderr}")
    return process


def shared_tree_status() -> str:
    """Return current shared worktree status including untracked files."""

    return run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
    ).stdout


def verify_origin_main_base(base_commit_sha: str) -> None:
    """Require the request base SHA to match the current local origin/main ref."""

    resolved = run_git(["rev-parse", "origin/main"], cwd=REPO_ROOT).stdout.strip()
    if resolved != base_commit_sha:
        raise CreativeCodePatchWorkspaceError(
            "base_commit_sha must match current origin/main " f"({base_commit_sha} != {resolved})."
        )


def prepare_generation_checkout(*, run_dir: Path, base_commit_sha: str) -> dict[str, Any]:
    """Create an isolated detached checkout at the exact base SHA."""

    verify_origin_main_base(base_commit_sha)
    status = shared_tree_status()
    if status.strip():
        raise CreativeCodePatchWorkspaceError("shared worktree must be clean before generation.")
    checkout = run_dir / CHECKOUT_DIRNAME
    if checkout.exists() or checkout.is_symlink():
        raise CreativeCodePatchWorkspaceError("generation checkout already exists.")
    run_git(["clone", "--no-hardlinks", str(REPO_ROOT), str(checkout)], cwd=REPO_ROOT)
    try:
        run_git(["checkout", "--detach", base_commit_sha], cwd=checkout)
        run_git(["remote", "remove", "origin"], cwd=checkout)
        head_sha = run_git(["rev-parse", "HEAD"], cwd=checkout).stdout.strip()
        if head_sha != base_commit_sha:
            raise CreativeCodePatchWorkspaceError("generation checkout HEAD mismatch.")
        remotes = run_git(["remote"], cwd=checkout).stdout.strip()
        if remotes:
            raise CreativeCodePatchWorkspaceError("generation checkout must not retain remotes.")
        checkout_status = run_git(
            ["status", "--porcelain=v1", "--untracked-files=all"],
            cwd=checkout,
        ).stdout
        if checkout_status.strip():
            raise CreativeCodePatchWorkspaceError("generation checkout must start clean.")
    except Exception:
        destroy_generation_checkout(run_dir)
        raise
    return {
        "detached_base_sha": base_commit_sha,
        "origin_removed": True,
        "checkout_relpath": CHECKOUT_DIRNAME,
    }


def generation_checkout(run_dir: Path) -> Path:
    checkout = run_dir / CHECKOUT_DIRNAME
    root = run_dir.resolve(strict=True)
    candidate = checkout.resolve(strict=True)
    if not _is_relative_to(candidate, root):
        raise CreativeCodePatchWorkspaceError("generation checkout must stay under run dir.")
    if not candidate.is_dir():
        raise CreativeCodePatchWorkspaceError("generation checkout must be a directory.")
    return candidate


def destroy_generation_checkout(run_dir: Path) -> bool:
    """Destroy the generation checkout and fail closed on containment problems."""

    checkout = run_dir / CHECKOUT_DIRNAME
    if not checkout.exists() and not checkout.is_symlink():
        return True
    root = run_dir.resolve(strict=True)
    if checkout.is_symlink():
        raise CreativeCodePatchWorkspaceError("generation checkout must not be a symlink.")
    candidate = checkout.resolve(strict=True)
    if not _is_relative_to(candidate, root):
        raise CreativeCodePatchWorkspaceError("generation checkout must stay under run dir.")
    shutil.rmtree(candidate)
    return not checkout.exists()


def cleanup_run_dir(run_id: str) -> None:
    """Remove a contained run directory for interrupted local runs."""

    run_dir = resolve_run_dir(run_id, create=False)
    root = ensure_artifact_root()
    if run_dir.is_symlink():
        raise CreativeCodePatchWorkspaceError("run directory must not be a symlink.")
    resolved = run_dir.resolve(strict=True)
    if not _is_relative_to(resolved, root):
        raise CreativeCodePatchWorkspaceError("run directory must stay under artifact root.")
    shutil.rmtree(resolved)
