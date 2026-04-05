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

- `scripts/orchestration/task_bootstrap.py`
- `scripts/orchestration/skill_router.py`
- `scripts/orchestration/native_subagent_bridge.py`
- related deterministic tests

This layer can provide canonical task packets and explainable routing once it is
invoked, but it still depends on an execution surface calling it.

### Local launcher / wrapper layer

Owned outside repo source of truth:

- local launcher/wrapper scripts
- compatible `~/.codex/config.toml` settings
- machine-local entrypoint wiring

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

- Coordinator-first is **policy-required**.
- Bootstrap packet generation is **deterministic once invoked**.
- Skill routing is **automatic after bootstrap**, not automatic at raw chat start.
- Bug-hunter post-open pass is **deterministic once invoked** via
  `pr_phase=post_open_review`, not yet globally event-triggered.
- Creative research is **deterministic once invoked** only for explicit
  report/research deliverables or governed research surfaces.
- Figma execution is **conditionally automatic**, packet-gated, blocker-aware,
  and never unconditional.

## Approved PR Series For This Wave

Series invariant:

- Do not start `PR<N+1>` until `PR<N>` has:
  - been opened under canonical PR governance,
  - completed its mandatory post-open review loop for that lane,
  - reached current-head green + resolved-comment merge readiness,
  - been merged,
  - been synced back into the local main clone,
  - passed post-merge sanity,
  - had temporary artifacts, branches, and worktrees cleaned up.

This wording is canonical for the PR-series gate. Other runbooks may summarize
the rule for operators, but they should reference this section instead of
creating competing definitions.

### Composer bootstrap kit wave (PR-A / PR-B)

Closure status for this wave is recorded in the backlog ledger (not duplicated
here): `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-a-bootstrap-seam`
and `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-b-reflection-protocol`.
Baseline merge for the PR-A envelope slice is PR #1329; router parity
(`docs_only` suppression + `envelope_mode_hint`) and PR-B reflection protocol
extensions ship in the follow-on merge that contains those artifacts.

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

In:

- machine-local launcher/wrapper,
- compatible `~/.codex/config.toml` updates,
- entrypoint wiring.

Out:

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
