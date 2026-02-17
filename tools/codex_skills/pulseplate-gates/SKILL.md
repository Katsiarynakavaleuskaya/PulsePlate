---
name: pulseplate-gates
description: Run PulsePlate hard quality gates and report failures in the required deterministic format.
---

# PulsePlate Gates

## When to use

- Before push or PR creation.
- After code edits that may affect quality gates.
- When CI reports failures and local reproduction is needed.

## Inputs required

- Changed files list.
- Base branch (default `origin/main`).
- Whether this is full validation or quick sanity check.

## Procedure (commands)

1. Mandatory pre-commit gate:

   ```bash
   pre-commit run --all-files
   ```

2. Full project gate:

   ```bash
   make verify
   ```

3. If `make verify` fails, run split triage:

   ```bash
   make lint
   make typecheck
   make test-fast
   make diff-cov
   ```

4. For policy sanity in docs/scripts-only changes:

   ```bash
   pytest -q tests/test_repo_policy_guards.py
   ```

## Output format

- `Gate status`: pass/fail per command.
- `Failure excerpt`: raw failing lines copied verbatim.
- `Pointers`: `file:line:error`.
- `Fix plan`: smallest actionable sequence.
- `Rerun commands`: exact commands to verify fix.

## Guardrails

- Never mark task ready without command evidence.
- Never hide failures with `|| true` or skip tricks.
- Never state "all checks pass" if any gate was not run.
- If hooks modify files, report affected files explicitly.

## SoT links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `tests/AGENTS.md`
- `scripts/AGENTS.md`
- `Makefile`
- `.pre-commit-config.yaml`
