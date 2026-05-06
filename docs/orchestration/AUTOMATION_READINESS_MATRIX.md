# Automation Readiness Matrix

**Version:** 2026-03-26 (`America/New_York`)
**Status:** Canonical source of truth for coordinator-first automation claims.

## Purpose

This document defines what PulsePlate automation is allowed to claim today,
what is still policy-only, and what requires a local launcher or host-runtime
support to become truly automatic.

It exists because orchestration docs, runbooks, and skills already describe a
coordinator-first system with post-open reviewer paths, skill routing, and
design/research lanes, but repo policy alone is not the same thing as enforced
runtime behavior.

Use this matrix whenever a doc, task packet, or implementation says something
is:

- automatic,
- automatically invoked,
- default,
- mandatory by policy,
- launcher-enforced,
- host-runtime constrained.

## Enforcement Layers

### Repo policy layer

Owned by repo-tracked source of truth:

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/orchestration/workflow.md`
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- packet/runbook docs under `docs/orchestration/`

This layer can require behavior by policy, but it cannot by itself force a raw
new Codex session to start with bootstrap logic before the first response.

### Deterministic repo engine layer

Owned by repo-tracked scripts:

- `scripts/orchestration/start_pr_lane.sh`
- `scripts/orchestration/task_bootstrap.py`
- `scripts/orchestration/skill_router.py`
- `scripts/orchestration/native_subagent_bridge.py`
- related deterministic tests

This layer can create an operator-invoked PR lane worktree and provide
canonical task packets plus explainable routing once it is invoked, but it
still depends on an execution surface calling it.

### Local launcher / wrapper layer

Owned outside repo source of truth:

- local launcher/wrapper scripts
- compatible `~/.codex/config.toml` settings
- machine-local entrypoint wiring

Optional **repo companion** (operator-invoked only; not host auto-start):

- `scripts/orchestration/start_pr_lane.sh` creates an isolated PR worktree, runs
  analyze preflight, invokes `task_bootstrap.py`, and prints a non-blocking
  plugin/runtime checklist when the operator explicitly runs it.
- `scripts/orchestration/local_session_bootstrap.sh` runs `check_preflight.py --mode analyze` and prints the next step to invoke `task_bootstrap.py` (see script output and `--help`).

This is the layer that can actually make coordinator-first bootstrap happen at
session start on one machine.

### Host-runtime constraint layer

Owned by the Codex/OpenAI runtime and surrounding safety/integration rules.

This layer may:

- allow or block automatic sub-agent spawning,
- limit startup hooks,
- constrain browser/Figma/network behaviors,
- require explicit user action for some execution modes.

Repo docs must not describe host-runtime-dependent behavior as if it were
unconditionally guaranteed by Markdown alone.

## Capability Matrix

| Capability | Repo policy | Repo engine | Local launcher needed | Host/runtime dependency | Current truth |
|------------|-------------|-------------|------------------------|-------------------------|---------------|
| Coordinator-first task handling | Yes | Partial | Usually yes | Yes | Policy-required, not guaranteed raw-session auto-start |
| PR lane worktree + bootstrap start | Yes | Yes | No for manual invocation; yes for raw-session auto-start | Low | Repo wrapper-enforced once `start_pr_lane.sh` is invoked |
| Bootstrap task packet generation | Yes | Yes | No for manual invocation; yes for auto-start | Low | Deterministic once invoked |
| Skill auto-selection | Yes | Yes | Yes for raw-session auto-start | Medium | Automatic after bootstrap, not at raw chat start |
| Mandatory post-open bug-hunter pass | Yes | Yes | No | Medium | Deterministic once invoked via PR phase packet; not globally event-triggered |
| Creative research lane | Yes | Yes | Likely yes for raw-session auto-start | Medium | Deterministic once invoked via explicit report/research triggers; not generic wellness wording |
| Figma execution lane | Partial | Yes (packet gating only) | Likely yes for raw-session auto-start | High | Packet-gated and blocker-aware; `read_only` by default until valid metadata or explicit creation mode exists |
| Post-merge local sync / cleanup gating next PR | Yes | N/A | No | Low | Required by process, enforced by canon/runbook discipline |

## Claim Rules

Use these exact semantics:

- **Policy-required**: repo docs require it, but runtime may still need manual invocation.
- **Deterministic once invoked**: repo scripts enforce it after the right entrypoint is called.
- **Launcher-enforced**: machine-local tooling actually makes it happen automatically.
- **Host-runtime constrained**: even with repo + launcher support, the platform may still block or narrow it.

Never collapse these into one vague word like "automatic."

Current approved wording:

- Canonical policy wording lives in `AGENTS.md`; workflow and readiness docs
  must stay aligned to that source instead of restating divergent variants.

- Coordinator-first is **policy-required**.
- Manual `agent-coordinator` invocation remains mandatory when launcher/runtime
  auto-capture is unavailable.
- PR lane worktree startup is **repo wrapper-enforced once invoked** through
  `scripts/orchestration/start_pr_lane.sh`; it is not raw-session auto-start.
- Bootstrap packet generation is **deterministic once invoked**.
- Skill routing is **automatic after bootstrap**, not automatic at raw chat start.
- Bug-hunter post-open pass is **deterministic once invoked** via
  `pr_phase=post_open_review`, not yet globally event-triggered.
- Creative research is **deterministic once invoked** only for explicit
  report/research deliverables or governed research surfaces.
- Figma execution is **conditionally automatic**, packet-gated, blocker-aware,
  and never unconditional.
- Launcher convenience can invoke canonical packets, but it does **not** bypass
  review-thread, required-check, or merge-readiness governance.

## Approved PR Series For This Wave

Series invariant:

- Do not start `PR<N+1>` until `PR<N>` has:
  - been opened under canonical PR governance,
  - executed any declared role-agent order for that lane packet/runbook,
  - completed its mandatory post-open review loop for that lane,
  - reached current-head green + resolved-comment merge readiness,
  - been merged,
  - been synced back into the local main clone,
  - passed post-merge sanity,
  - had temporary artifacts, branches, and worktrees cleaned up.

This wording is canonical for the PR-series gate. Other runbooks may summarize
the rule for operators, but they should reference this section instead of
creating competing definitions.

Explicit operator rule:
- after `PR<N>` merges, sync local `main`, verify current-head `main` health, and do not
  start `PR<N+1>` while `main` is red, pending on merge fallout, or otherwise unstable.
- treat this as a hard process gate for the next PR in the train, not a heuristic.

### Composer bootstrap kit wave (PR-A / PR-B)

Closure status for this wave is recorded in the backlog ledger (not duplicated
here): `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-a-bootstrap-seam`
and `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-b-reflection-protocol`.
Baseline merge for the PR-A envelope slice is PR #1329 (merged). PR #1339 is
squash-merged to `main` as `3b243a003daf9101b00639cada199a27e19c7e83` (router
parity: `docs_only` suppression + `envelope_mode_hint`, `bootstrap_sync_policy`
docs-only path contract, tests, SoT docs). PR-B reflection protocol extensions
landed in the same merge; ledger rows for PR-A/PR-B are **closed** with that
SHA (see backlog ledger anchors above).

### PR1: Governance and SoT alignment

In:

- this matrix,
- wording corrections where repo policy was described as unconditional runtime automation,
- backlog decomposition for follow-up slices.

Out:

- `task_bootstrap.py`,
- `skill_router.py`,
- local launcher/runtime hooks.

### PR2: Bootstrap engine hardening

In:

- packet schema for automation flags and sync flags,
- bootstrap invariants and tests.

Out:

- PR event automation,
- design/Figma triggers,
- local launcher.

### PR3: Skill routing and intent classifier

In:

- minimal-optimal skill stack selection,
- deterministic task-class classifier,
- nested `inputs.skill_routing.task_classification`,
- backward-compatible `recommended_skills = required + recommended`,
- required/recommended/conditional/blocked routing outputs.

Out:

- PR lifecycle hooks,
- Figma mutation flow,
- local launcher wiring.

### PR4: PR lifecycle automation

In:

- PR phase detection,
- mandatory post-open review path synthesis,
- current-head review-preparation contract.

Out:

- creative brainstorming and design-lane execution.

### PR5: Creative research and design/Figma activation

In:

- `creative_research` trigger rules,
- code-native design brief path,
- `design_lane_contract` packet semantics,
- Figma lane activation rules with explicit trigger, blocker states, and valid
  packet metadata or explicit creation mode.

Out:

- broad PR governance refactors,
- new merge-readiness semantics.

### Local rollout (outside repo PR chain)

Operator path today (repo companion, **not** a guarantee of raw-session auto-start):

1. `scripts/orchestration/start_pr_lane.sh --goal "<goal>" --task-class "<class>" --branch "codex/<slug>" --worktree "worktrees/<slug>" --path "<scope>"` from a clean checkout synced with `origin/main` — creates the isolated PR worktree, runs analyze preflight, invokes `task_bootstrap.py`, and prints the plugin/runtime checklist plus packet summary.
2. (Optional) `scripts/orchestration/local_session_bootstrap.sh` from repo root — preflight analyze + printed `task_bootstrap` recipe. Evidence: `scripts/orchestration/local_session_bootstrap.sh:145-147` runs analyze preflight and `scripts/orchestration/local_session_bootstrap.sh:154-166` renders the follow-up command without executing it. For flag-specific option handling, use the script's `--help` output.
3. `python3 scripts/orchestration/task_bootstrap.py ...` — deterministic packet + routing metadata once invoked.

In:

- machine-local launcher/wrapper,
- compatible `~/.codex/config.toml` updates,
- entrypoint wiring.

Out:

- host plugin installation or raw-session auto-start guarantees from repo
  scripts alone.
- repo source-of-truth mutation used as a substitute for launcher/runtime
  support.

## Acceptance Rules For This Document

This matrix is correct only if:

- repo docs stop overstating policy as runtime certainty,
- each follow-up capability has a named PR slice or explicit local rollout,
- PR-series docs state that the next PR is blocked until the previous PR
  completes its full post-merge closure cycle,
- host/runtime blockers are recorded instead of hand-waved away,
- future docs refer to this matrix when claiming something is automatic.
