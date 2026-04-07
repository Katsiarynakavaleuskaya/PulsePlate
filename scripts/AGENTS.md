# Agent instructions (scope: scripts/ and subdirectories)

## Scope and layout

- This AGENTS.md applies to: `scripts/` and below.
- Scripts are repo automation utilities; run from repo root.

## Conventions

- Treat scripts as production automation: avoid breaking flags or outputs.
- Prefer small, focused edits; update any dependent docs or Make targets if needed.
- Avoid adding network calls to scripts used in CI unless explicitly required.

## Governed Experimentation Runner

- Canonical entrypoints for the experimentation lane are `scripts/orchestration/experiment_bootstrap.py` and `scripts/orchestration/experiment_runner.py`.
- Run both scripts from repo root so path validation and artifact resolution stay deterministic.
- `experiment_runner.py` accepts only a validated packet plus a prebuilt unified diff via `--packet <packet.json> --candidate-patch <candidate.patch> [--output ...]`.
- The runner must apply patches only inside an isolated temporary checkout and must leave the shared working tree untouched.
- Mutable surfaces, immutable oracles, budgets, and promotion boundaries are defined by `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`; do not duplicate or relax them here.
- Result artifacts stay local under `artifacts/orchestration/experiments/results/` and are evidence only, not merge-ready or promotion-ready output.

## Pre-push backend tests (smart diff runner)

The `run-backend-tests-pre-commit.sh` script is used by pre-commit framework to run backend pytest only when Python files changed.

First-class repo wrappers:

- `make validate-changed` is the supported repo-root command for this diff-based path and runs the script with the repo `.venv` on `PATH`.
- `scripts/quick_check.sh` is a separate convenience helper: it runs `make validate-min` first, then staged-file format/import/syntax checks.
- `scripts/orchestration/local_session_bootstrap.sh` is an **opt-in** raw-session helper: runs `check_preflight.py --mode analyze` from repo root and prints how to invoke `task_bootstrap.py`. It does not replace a machine-local launcher and does not auto-start Codex/Cursor sessions.

**Coordinator cold-start precedence (host):**

1. Opt-in **machine-local launcher** (operator-installed; see `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md` + `docs/templates/pulseplate-coordinator-launch.example.sh`)
2. Repo helper `scripts/orchestration/local_session_bootstrap.sh` (preflight + printed recipe)
3. Direct `python3 scripts/orchestration/task_bootstrap.py ...` after `check_preflight.py`
- `scripts/orchestration/local_support_plane.py` is an **experimental non-canonical** operator KV store under gitignored `artifacts/orchestration/local_support_plane/` (override via `LOCAL_SUPPORT_PLANE_ROOT`). Mutations require `AGENT_CONTROL_ALLOWLIST` to include `local_support_plane:artifacts_kv` and a compatible `AGENT_CONTROL_EXECUTION_MODE` (see `app/security/agent_control_plane.py`). It is not orchestration SoT.

**Change detection order:**

1. If upstream exists: diff `upstream..HEAD`
2. Else: diff from merge-base against (origin/main|origin/master|main|master)
3. If base cannot be resolved: fallback to last N commits (diagnostic mode)

**Debug mode:**

- Set `PREPUSH_DEBUG=1` to print resolved upstream/base and file list
- Example: `PREPUSH_DEBUG=1 git push` will show detailed change detection info

**Skip tests:**

- Set `SKIP_TESTS=1` to bypass backend tests (useful for documentation-only commits)
