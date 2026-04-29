# Machine-local coordinator launcher rollout

<!-- markdownlint-disable MD013 -->

This document describes an **opt-in, operator-owned** machine-local wrapper that runs
`check_preflight.py` (analyze mode) and then `task_bootstrap.py` from a checked-out PulsePlate
repository.

**Scope boundary:** Launcher behavior is **launcher-enforced only on opted-in machine(s)** where
you install the wrapper and optional `PATH` hooks. It is **not** a global default for all
developers or CI. Repository markdown and templates do not auto-start sessions on any host.

**Canonical example (sanitized):** [`docs/templates/pulseplate-coordinator-launch.example.sh`](../templates/pulseplate-coordinator-launch.example.sh)

**Related SoT:** [`docs/orchestration/AUTOMATION_READINESS_MATRIX.md`](../orchestration/AUTOMATION_READINESS_MATRIX.md),
[`scripts/orchestration/local_session_bootstrap.sh`](../../scripts/orchestration/local_session_bootstrap.sh)
(repo bridge; runs analyze preflight and prints the selected bootstrap recipe only).

**Governance boundary:** This launcher can invoke canonical coordinator packets on an opted-in
machine. It does **not** bypass review-thread, required-check, or merge-readiness rules from root
`AGENTS.md` and `RUNBOOK_AGENT.md`.

**Coordinator-first boundary:** launcher installation makes coordinator-first startup easier on
an opted-in machine, but it does not replace the repo policy that manual `agent-coordinator`
invocation is mandatory when launcher/runtime auto-capture is unavailable.

**Governance lane note:** the coordinator-first/RAG-Karpathy governance prep lane may carry its
own packet, but this launcher runbook remains governed by the stable repo SoT listed above rather
than by an ephemeral PR packet path.

## Install (host)

1. Ensure `python3` is on `PATH` and you have a git clone of this repository.
2. Create `~/.local/bin` if needed: `mkdir -p ~/.local/bin`
3. Copy the canonical script body from [`docs/templates/pulseplate-coordinator-launch.example.sh`](../templates/pulseplate-coordinator-launch.example.sh)
   into `~/.local/bin/pulseplate-coordinator-launch.sh` (or merge edits carefully).
4. `chmod +x ~/.local/bin/pulseplate-coordinator-launch.sh`
5. Ensure `~/.local/bin` is on your shell `PATH` when you work (shell-specific).
6. Optional: set `CODEX_HOME` if your Codex install expects it; the wrapper exports
   `CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"` only as a convenience default.

**Do not commit** real host wrappers, `~/.codex/config.toml`, or machine-specific `PATH` snippets
into the repository.

## Use

Run from any directory inside the repo (so `git rev-parse --show-toplevel` resolves), or set
`PULSEPLATE_REPO_ROOT` to the clone root and run from elsewhere.

Required flags for the host wrapper: `--goal`, `--task-class`.

Optional: `--pr-phase`, repeatable `--path`, repeatable `--requested-agent`.

The wrapper passes the same `--path` values to **both** `check_preflight.py --mode analyze` and
`task_bootstrap.py` so scoped `AGENTS.md` resolution in analyze mode stays aligned with bootstrap.

Example:

```bash
pulseplate-coordinator-launch.sh \
  --goal "Close machine-local launcher gap for coordinator-first startup" \
  --task-class "pr_governance" \
  --path docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md \
  --pr-phase pre_open
```

## Smoke checks (host)

Run these **before** opening the docs companion PR (or re-run after template changes).

### Smoke 1

```bash
~/.local/bin/pulseplate-coordinator-launch.sh \
  --goal "Close machine-local launcher gap for coordinator-first startup" \
  --task-class "pr_governance" \
  --path docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md \
  --pr-phase pre_open
```

Expect: preflight exit 0, bootstrap writes task packet under gitignored `artifacts/orchestration/task_packets/`.

## Repo bridge smoke

The repo helper is intentionally weaker than the installed host wrapper: it does not execute
`task_bootstrap.py`, but it can validate the selected options and print the exact command to run
(`scripts/orchestration/local_session_bootstrap.sh:87-139`, `scripts/orchestration/local_session_bootstrap.sh:154-166`).

```bash
scripts/orchestration/local_session_bootstrap.sh \
  --goal "Close machine-local launcher gap for coordinator-first startup" \
  --task-class "pr_governance" \
  --path docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md \
  --pr-phase pre_open
```

Expect: analyze preflight exit 0, no task packet creation from the helper itself, and a printed
`python3 .../scripts/orchestration/task_bootstrap.py` command that includes the same `--path` and
`--pr-phase` values. Evidence: `scripts/orchestration/local_session_bootstrap.sh:145-147`
for analyze preflight and `scripts/orchestration/local_session_bootstrap.sh:154-166` for
command rendering. Use `--help` to inspect the local bridge contract without running preflight
(`scripts/orchestration/local_session_bootstrap.sh:63-68`).

### Smoke 2

```bash
~/.local/bin/pulseplate-coordinator-launch.sh \
  --goal "Run post-open review packet for launcher PR" \
  --task-class "review" \
  --path docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md \
  --pr-phase post_open_review \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter
```

Expect: packet includes requested agents per `task_bootstrap.py` normalization rules.

### Smoke 3 (normalization, not fail-closed)

Repeated `--requested-agent` **must not** fail the wrapper or bootstrap.

- The wrapper forwards every `--requested-agent` flag to `task_bootstrap.py`.
- `task_bootstrap.py` normalizes via `scripts/orchestration/requested_agents.py` (`normalize_requested_agents`):
  deduplication with **order preserved** (first occurrence wins).
- Pass criteria: command succeeds; inspect the emitted packet JSON and confirm **unique** slugs in
  stable first-seen order (e.g. duplicate `qa-engineer-agent` appears once).

This smoke validates normalization, not crash-on-duplicate.

### Fail-closed smokes (expect non-zero / errors)

- **Bad repo root:** run outside a clone without `PULSEPLATE_REPO_ROOT` → wrapper exit 2.
- **Bad `python3`:** temporarily break `PATH` so `python3` is missing → preflight/bootstrap fails.
- **Unknown arg:** e.g. `--nope` → wrapper exit 2.
- **Missing `--goal` or `--task-class`:** wrapper exit 2.

### Smoke 4 (rollback)

- Remove or rename the wrapper; remove `~/.local/bin` from `PATH` for a test shell.
- Confirm normal repo workflows still work (`make validate-min`, or your usual commands).
- If you are running Smoke 4 from a clean worktree without a local `.venv`, either run `make venv`
  first or point `VENV_PYTHON` at a valid repo venv before `make validate-min`.
- Baseline repository state must remain valid (wrapper is host-only).

## Post-merge git flow (operator)

After the docs PR merges, sync `main` using a **fetch-based** flow (aligned with root `AGENTS.md`
git guidance; avoid bare `git pull`):

```bash
git checkout main
git fetch origin
git merge --ff-only origin/main
git branch -d docs/local-launcher-rollout-closeout
```

Before opening the next PR in the train:
- inspect current-head `main` health;
- if `main` is red, pending on merge fallout, or otherwise unstable, stop and stabilize
  `main` first;
- only then create the next branch from synced `origin/main`;
- re-run wrapper smokes on the same machine;
- refresh the installed script if the repo template changed.

Delete the remote PR branch only if that matches your post-merge policy (`AGENTS.md`, `RUNBOOK_AGENT.md`).

Clean only local gitignored artifacts relevant to the finished lane. Do **not** commit or promote:
- `artifacts/`
- `worktrees/`
- host-local wrappers
- `~/.codex/config.toml`
- shell `PATH` snippets

Avoid vague "clear caches" cleanup. Remove only lane-local gitignored artifacts that are safe to
recreate; do not touch tracked repo files except through intentional PR changes.

## Rollback

- Delete `~/.local/bin/pulseplate-coordinator-launch.sh` (or unlink).
- Remove `~/.local/bin` from shell startup `PATH` if you added it only for this launcher.
- No repository revert is required; the repo companion is documentation + sanitized example only.

## Known limits

- **Bash 3.2 / `set -u`:** the canonical template uses `${ARRAY[@]+"${ARRAY[@]}"}` so empty `--path` / `--requested-agent` lists do not trip unbound-variable errors.
- **Bash-only** in the canonical template; zsh/fish parity is a follow-up if needed.
- **No Windows launcher** in this slice; parity is deferred unless documented separately.
- **No CI enforcement:** hosts opt in individually.
- **Secrets:** never pass tokens via wrapper flags; keep host config out of git.
- Task packets land under `artifacts/` (gitignored); do not commit them.
- This launcher/runbook line does **not** authorize a new PR if post-merge `main` is unhealthy.

## Evidence and backlog

Closing the backlog ledger item for this lane requires **recorded host smoke evidence** (commands
run, pass/fail, date). This runbook is the intended place to cite that evidence when updating
[`docs/roadmap/BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md).

Do **not** mark coordinator-first auto-start as a **global** default in the automation matrix;
only document the **local opt-in** boundary.

<!-- markdownlint-enable MD013 -->
