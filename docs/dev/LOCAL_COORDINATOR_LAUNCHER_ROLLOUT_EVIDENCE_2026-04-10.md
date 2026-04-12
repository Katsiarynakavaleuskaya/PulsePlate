# Local Coordinator Launcher Rollout Evidence — 10 April 2026

## Context

- Machine: opted-in local operator machine
- Wrapper path: `~/.local/bin/pulseplate-coordinator-launch.sh`
- Repo worktree: `worktrees/fix-coordinator-role-agent-rollout`
- Template source: `docs/templates/pulseplate-coordinator-launch.example.sh`

## Host-local sync

- Compared the installed wrapper to the canonical template.
- Found drift in flag parsing: the installed wrapper was missing explicit value checks for
  `--goal`, `--task-class`, `--pr-phase`, `--requested-agent`, and `--path`.
- Synced the installed wrapper to the canonical template.
- Post-sync verification: `cmp -s ~/.local/bin/pulseplate-coordinator-launch.sh docs/templates/pulseplate-coordinator-launch.example.sh` → `TEMPLATE_SYNCED`.

## Smoke Results

### Smoke 1

Command:

```bash
~/.local/bin/pulseplate-coordinator-launch.sh \
  --goal "Close machine-local launcher gap for coordinator-first startup" \
  --task-class "pr_governance" \
  --path docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md \
  --pr-phase pre_open
```

Result:

- `check_preflight.py --mode analyze` passed.
- Scoped `AGENTS.md` resolution passed.
- Task packet emitted: `artifacts/orchestration/task_packets/3e9e83d8e2c5.json`.
- Primary agent: `cursor-specialist-agent`.
- Reviewer: `qa-engineer-agent`.

### Smoke 2

Command:

```bash
~/.local/bin/pulseplate-coordinator-launch.sh \
  --goal "Run post-open review packet for launcher PR" \
  --task-class "review" \
  --path docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md \
  --pr-phase post_open_review \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter
```

Result:

- Command passed.
- Task packet emitted: `artifacts/orchestration/task_packets/39b5396fd243.json`.
- Requested agents preserved in packet order: `["qa-engineer-agent", "bug-hunter"]`.
- Primary agent resolved to `qa-engineer-agent`.

### Smoke 3

Command:

```bash
~/.local/bin/pulseplate-coordinator-launch.sh \
  --goal "Check duplicate requested-agent normalization" \
  --task-class "review" \
  --path docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md \
  --pr-phase post_open_review \
  --requested-agent qa-engineer-agent \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter
```

Result:

- Command passed.
- Task packet emitted: `artifacts/orchestration/task_packets/f1fccd7106b8.json`.
- Packet shows normalized requested agents: `["qa-engineer-agent", "bug-hunter"]`.
- Duplicate `qa-engineer-agent` did not crash the wrapper and was deduplicated with first-seen order preserved.

### Smoke 4

Command:

```bash
env PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
  VENV_PYTHON="../../.venv/bin/python" \
  bash -lc 'command -v pulseplate-coordinator-launch.sh >/dev/null 2>&1 && echo LAUNCHER_VISIBLE || echo LAUNCHER_HIDDEN; make validate-min'
```

Result:

- `pulseplate-coordinator-launch.sh` was hidden from `PATH`: `LAUNCHER_HIDDEN`.
- `make validate-min` passed.
- Normal repo workflow remained usable without the launcher in `PATH`.

## Conclusion

- The coordinator-first launcher path is working on at least one opted-in machine.
- The remaining gap was host-local wrapper drift, not a missing repo-side coordinator / role-agent implementation.
- The backlog rollout item can be closed using this evidence.
