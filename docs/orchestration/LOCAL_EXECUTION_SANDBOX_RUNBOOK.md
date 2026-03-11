# Local Execution Sandbox Runbook

## Goal

This runbook describes the cheapest practical way to run the PulsePlate agent
execution sandbox on a developer machine before any remote runner platform is
introduced.

Related integration spec:

- `docs/orchestration/FITCHEF_SANDBOX_INTEGRATION_PLAN.md`
- `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`

## Current Scope

The local sandbox is intentionally narrow:

- allowlisted binaries only
- bounded working directory
- timeout and output-size limits
- sanitized environment
- control-plane policy gate before execution
- execution-mode gate before execution

This is a **developer-machine sandbox**, not a strong VM/container isolation
boundary yet.

## Machine Profile

Validated local baseline for this repository:

- Apple Silicon laptop is acceptable for sandbox orchestration work
- 16 GB RAM is enough for control-plane + tests + a lightweight local LLM
- low free disk is the main practical constraint; keep model downloads small

Recommended local budget profile:

- sandbox + repo tooling: yes
- sandbox + Ollama with a small or medium instruct model: yes
- large local multi-model stack: no

## Required Environment

Add the following to local env only:

```env
AGENT_EXECUTION_SANDBOX_ENABLED=true
AGENT_EXECUTION_SANDBOX_ROOT=.
AGENT_EXECUTION_SANDBOX_TIMEOUT_SECONDS=30
AGENT_EXECUTION_SANDBOX_MAX_OUTPUT_BYTES=32768
AGENT_EXECUTION_SANDBOX_ALLOWED_BINARIES=pytest,mypy,coverage,diff-cover,ruff,flake8,git
```

`python` / `python3` are not part of the runtime default allowlist. Add them
only when a local workflow explicitly needs interpreter execution.

Optional interpreter add-on:

```env
AGENT_EXECUTION_SANDBOX_ALLOWED_BINARIES=python3,pytest,mypy,coverage,diff-cover,ruff,flake8,git
```

Optional runtime gate:

```env
AGENT_CONTROL_EXECUTION_MODE=auto-safe
```

## Recommended Local Profile

Use the sandbox first without any local model.

If a local model is needed, keep it cheap:

- prefer one small instruct model only
- stay in the 3B to 8B class on a 16 GB laptop
- avoid parallel local model workers
- do not preload multiple models while running the full test suite

## Example Flow

1. Enable sandbox env vars locally.
2. Keep `AGENT_EXECUTION_SANDBOX_ROOT` at repo root or a narrower worktree.
3. Allowlist only the binaries needed for the task.
4. Run deterministic tests before enabling wider local use.

Example Python snippet:

```python
from app.security.execution_sandbox import SandboxRequest
from app.security.execution_sandbox import run_local_sandbox

result = run_local_sandbox(
    SandboxRequest(
        binary="python3",
        args=("-c", "print('sandbox-ok')"),
        cwd=".",
    )
)
print(result.stdout)
```

## Verification

Run from repo root with the project venv:

```bash
. .venv/bin/activate
python3 scripts/orchestration/check_preflight.py
pytest -q tests/test_execution_sandbox.py tests/test_agent_control_plane_mvp.py
pytest -q tests/edges tests/test_remaining_modules.py --maxfail=3
```

## Stop Conditions

Do not widen sandbox usage if any of the following is true:

- free disk drops below a safe working margin for repo + local model cache
- local test latency becomes unstable
- a task requires non-allowlisted binaries or network-heavy automation
- a task needs stronger isolation than a developer-machine bounded subprocess

## Next Step After Local Validation

After the local sandbox is stable, the next upgrade path is:

1. keep inference local or provider-based
2. move only the orchestrator/audit/webhook plane to a cheap VM
3. add a stronger isolated runner boundary later

This keeps costs minimal while preserving a clean path to production hardening.

Phase 2 capabilities such as exports, realtime progress, and broader autonomy
remain planned only. See:

- `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`
