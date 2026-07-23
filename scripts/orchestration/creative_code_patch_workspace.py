"""Workspace and artifact helpers for PR-2 creative-code patch building."""

from __future__ import annotations

from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404: fixed git subprocess wrappers only (remove-by: 2026-07-31, ref: PR-2)
import sys
import tempfile
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code" / "patch_runs"
CHECKOUT_DIRNAME = "generation_checkout"

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
SAFE_GIT_ENV_KEYS = frozenset(
    {
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOGNAME",
        "PATH",
        "TERM",
        "TMPDIR",
        "TZ",
        "USER",
    }
)
SECRET_ENV_SUBSTRINGS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASS",
    "SALT",
    "COOKIE",
    "CREDENTIAL",
    "DATABASE_URL",
    "DSN",
)
SAFE_GIT_CONFIG_PAIRS = (
    ("diff.external", ""),
    ("core.fsmonitor", "false"),
    ("core.hooksPath", os.devnull),
)


class CreativeCodePatchWorkspaceError(ValueError):
    """Raised when PR-2 workspace/artifact containment fails."""


@contextmanager
def exclusive_patch_run_lock(run_dir: Path, *, label: str) -> Iterator[None]:
    """Hold the shared non-blocking file lock for one patch run."""

    try:
        fcntl_module = importlib.import_module("fcntl")
    except ModuleNotFoundError as exc:
        raise CreativeCodePatchWorkspaceError(
            f"{label} locking is unavailable on this platform."
        ) from exc
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    lock_fd = -1
    try:
        try:
            lock_fd = os.open(run_dir, flags)
        except OSError as exc:
            raise CreativeCodePatchWorkspaceError(f"{label} lock could not be acquired.") from exc
        try:
            fcntl_module.flock(
                lock_fd,
                fcntl_module.LOCK_EX | fcntl_module.LOCK_NB,
            )
        except BlockingIOError as exc:
            raise CreativeCodePatchWorkspaceError(f"{label} is already in progress.") from exc
        except OSError as exc:
            raise CreativeCodePatchWorkspaceError(f"{label} lock could not be acquired.") from exc
        yield
    finally:
        active_error = sys.exc_info()[1]
        cleanup_error: OSError | None = None
        if lock_fd >= 0:
            try:
                os.close(lock_fd)
            except OSError as exc:
                cleanup_error = exc
        if active_error is None and cleanup_error is not None:
            raise CreativeCodePatchWorkspaceError(
                f"{label} lock cleanup failed."
            ) from cleanup_error


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


def resolve_existing_artifact_root() -> Path:
    """Return the existing resolved PR-2 artifact root without creating it."""

    _reject_symlink_components(ARTIFACT_ROOT, label="artifact root")
    try:
        root = ARTIFACT_ROOT.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodePatchWorkspaceError("artifact root must exist.") from exc
    if not root.is_dir():
        raise CreativeCodePatchWorkspaceError("artifact root must be a directory.")
    return root


def ensure_creative_code_root() -> Path:
    """Create and return the resolved creative-code artifact root."""

    root_path = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
    _reject_symlink_components(root_path, label="creative-code artifact root")
    try:
        root_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodePatchWorkspaceError(
            "creative-code artifact root could not be created."
        ) from exc
    _reject_symlink_components(root_path, label="creative-code artifact root")
    root = root_path.resolve(strict=True)
    if not root.is_dir():
        raise CreativeCodePatchWorkspaceError("creative-code artifact root must be a directory.")
    return root


def _resolve_creative_code_json_file(path: Path, *, for_write: bool) -> Path:
    root = ensure_creative_code_root()
    target = path if path.is_absolute() else root / path
    if target.suffix != ".json":
        raise CreativeCodePatchWorkspaceError("artifact path must be a JSON file.")
    _reject_symlink_components(target.parent, label="artifact file parent")
    parent_candidate = target.parent.resolve(strict=False)
    if not _is_relative_to(parent_candidate, root):
        raise CreativeCodePatchWorkspaceError(
            "artifact file must stay under creative-code artifacts."
        )
    if for_write:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CreativeCodePatchWorkspaceError(
                "artifact file parent could not be created."
            ) from exc
        _reject_symlink_components(target.parent, label="artifact file parent")
    try:
        parent = target.parent.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodePatchWorkspaceError("artifact file parent must exist.") from exc
    if not _is_relative_to(parent, root):
        raise CreativeCodePatchWorkspaceError(
            "artifact file must stay under creative-code artifacts."
        )
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            raise CreativeCodePatchWorkspaceError("artifact file must not be a symlink.")
        if not target.is_file():
            raise CreativeCodePatchWorkspaceError("artifact path must be a file.")
    return parent / target.name


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


def resolve_existing_run_dir(run_id: str) -> Path:
    """Resolve an existing run directory below the PR-2 artifact root without writes."""

    normalized = run_id.strip()
    if not normalized or not RUN_ID_RE.fullmatch(normalized):
        raise CreativeCodePatchWorkspaceError("run id must be a safe identifier.")
    root = resolve_existing_artifact_root()
    run_dir = ARTIFACT_ROOT / normalized
    _reject_symlink_components(run_dir, label="run directory")
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

    output = _resolve_creative_code_json_file(path, for_write=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(output.parent),
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(payload, temp_file, sort_keys=True, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, output)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodePatchWorkspaceError("creative-code artifact JSON has duplicate key.")
        seen.add(key)
        payload[key] = value
    return payload


def read_json(path: Path) -> Any:
    artifact = _resolve_creative_code_json_file(path, for_write=False)
    try:
        return json.loads(
            artifact.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodePatchWorkspaceError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodePatchWorkspaceError(
            f"Unable to read JSON artifact: {artifact.name}"
        ) from exc


def resolve_git_binary() -> str:
    git_binary = shutil.which("git")
    if not git_binary:
        raise CreativeCodePatchWorkspaceError("git binary is required.")
    resolved = Path(git_binary).expanduser().resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise CreativeCodePatchWorkspaceError("git binary must resolve to an executable file.")
    return str(resolved)


def _absolute_path_env(raw_path: str | None) -> str:
    if not raw_path:
        return ""
    entries: list[str] = []
    for entry in raw_path.split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry).expanduser()
        if not candidate.is_absolute():
            candidate = candidate.resolve()
        entries.append(str(candidate))
    return os.pathsep.join(entries)


def git_env_without_parent_state() -> dict[str, str]:
    """Return a stable env for git subprocesses."""

    sanitized: dict[str, str] = {}
    for key, value in os.environ.items():
        upper_key = key.upper()
        if key not in SAFE_GIT_ENV_KEYS:
            continue
        if upper_key.startswith("GIT_") or upper_key in {"PYTHONPATH", "CODEX_HOME"}:
            continue
        if any(fragment in upper_key for fragment in SECRET_ENV_SUBSTRINGS):
            continue
        sanitized[key] = value
    sanitized["PATH"] = _absolute_path_env(os.environ.get("PATH"))
    sanitized["GIT_CONFIG_GLOBAL"] = os.devnull
    sanitized["GIT_CONFIG_NOSYSTEM"] = "1"
    sanitized["GIT_TERMINAL_PROMPT"] = "0"
    return sanitized


def safe_git_config_args() -> list[str]:
    """Return command-line config clamps that override checkout-local Git config."""

    args: list[str] = []
    for key, value in SAFE_GIT_CONFIG_PAIRS:
        args.extend(["-c", f"{key}={value}"])
    return args


def run_git(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git with a resolved binary, no shell, and bounded capture."""

    process = subprocess.run(  # nosec B603: absolute git binary with bounded argv for isolated PR-2 checkouts (remove-by: 2026-07-31, ref: PR-2)
        [resolve_git_binary(), *safe_git_config_args(), *args],
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
