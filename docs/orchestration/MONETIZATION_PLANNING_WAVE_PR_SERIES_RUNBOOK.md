# Monetization Planning Wave PR Series Runbook

**Version:** 2026-04-13 (`America/New_York`)
**Scope:** Governance-first monetization wave for planning-flow value capture over the canonical FREE -> PRO -> VIP ladder.
**Execution surface:** isolated PR worktrees only; one clean worktree per PR.

## Purpose

This runbook is the canonical operating contract for the planning-flow monetization
wave launched from isolated worktrees.

It exists to keep:
- billing/provider modernization closed instead of accidentally reopened,
- coordinator-owned role order explicit for every PR in the wave,
- runtime monetization additive and thin-client-safe,
- PR train execution sequential: bootstrap -> PR-1 -> PR-2 -> PR-3.

## Contract Boundaries

- This runbook owns process, sync points, merge cadence, cleanup, and hard rules.
- `docs/orchestration/MONETIZATION_PLANNING_WAVE_TASK_PACKET_2026-04-13.md`
  owns the active wave packet: branch/worktree names, PR sequence, execution order,
  and acceptance scope.
- `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md` remains the source of
  truth for review-thread disposition, current-head CI truth, and merge governance.

## Source of Truth

- Coordinator workflow: `docs/orchestration/workflow.md`
- Merge-readiness procedure: `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md`
- Orchestration governance contract: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- Worktree promotion policy: `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
- Product tier map: `docs/contracts/PRODUCT_TIER_MAP.md`
- Payments baseline: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
- Backlog ledger: `docs/roadmap/BACKLOG_LEDGER.md`
- Repo runbook: `RUNBOOK_AGENT.md`
- Root policy: `AGENTS.md`

## Wave Objective

Deliver a narrow monetization wave that monetizes the existing planning-first
product chain without reopening billing backbone work:
- FREE BMI -> PRO targets
- PRO targets -> PRO daily plate
- PRO weekly plan -> VIP export / recipe follow-through

This wave is intentionally not:
- a new receipt verification rewrite,
- a new entitlement-routing PR,
- a web checkout rollout,
- a pricing/QoS/concurrency billing system.

## Current State

- PR `#1296` merged on `2026-04-02` (`America/New_York`) and closed the activation/subscription persistence baseline.
- PR `#1312` merged on `2026-04-03` (`America/New_York`) and landed App Store pricing-truth governance.
- PR `#1381` merged on `2026-04-09` (`America/New_York`) and moved web premium truth to canonical backend/store session state.
- PR `#1416` merged on `2026-04-15` (`America/New_York`) and landed the general paywall exposure ledger foundation (`app/schemas/paywall_analytics.py`, `app/routers/paywall_analytics.py`, `app/services/paywall_exposure_ledger.py`).
- PR `#1434` merged on `2026-04-17` (`America/New_York`) and landed intervention trigger engine v1 as the current execution baseline for PR-2.
- Execution-time `main` baseline for PR-2 is synced to `origin/main` at `7bf5d8819e33b40b35cef1aac7c7fcc76c32229f`.

## PR Series

### PR-0: Bootstrap Governance

- Worktree: `worktrees/monetization_planning_bootstrap`
- Branch: `docs/monetization-planning-wave-bootstrap`
- Scope:
  - reconcile stale `ledger-p0-web-entitlement-truth` wording to merged PR `#1381`,
  - add the planning-flow monetization epic entry to `docs/roadmap/BACKLOG_LEDGER.md`,
  - create this runbook,
  - create the dated task packet.
- Hard boundary:
  - docs/governance only; no runtime/app/frontend edits.

### PR-1: Intervention Trigger Engine V1

- Worktree: `worktrees/monetization_planning_pr1`
- Branch: `feat/monetization-trigger-engine-v1`
- Scope:
  - additive backend-owned `next_best_action` contract,
  - deterministic intervention trigger engine,
  - BMI / targets / weekly plan response wiring only.
- Hard boundary:
  - do not touch billing, entitlement routing, providers, quota core, or checkout.

### PR-2: Planning Paywall Exposure Ledger

- Worktree: `worktrees/monetization_planning_pr2`
- Branch: `feat/planning-paywall-exposure-ledger`
- Scope:
  - planning-specific wiring/taxonomy on top of the already-merged ledger foundation from PR `#1416`,
  - keep the hidden route `/api/v1/internal/paywall/events` (see `app/main.py:48`, `app/main.py:205`),
  - keep the canonical event set unchanged (see `app/schemas/paywall_analytics.py:36`, `app/schemas/paywall_analytics.py:41`):
    - `shown`
    - `dismissed`
    - `cta_clicked`
    - `upgrade_started`
    - `upgrade_completed`,
  - align concrete planning surfaces only:
    - BMI -> PRO targets: `source_surface=bmi_soft_paywall`, `trigger_reason=post_bmi` (see `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:9`, `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:10`, `app/schemas/intervention.py:12`)
    - targets -> daily plate: `source_surface=pro_daily_plate`, `trigger_reason=targets_ready` (see `app/services/intervention_trigger_engine.py:41`, `app/services/intervention_trigger_engine.py:43`, `app/schemas/intervention.py:11`, `app/schemas/intervention.py:12`)
- Hard boundary:
  - no vendor SDK rollout, no checkout semantics change, no pricing-truth change.
  - no widening of client/server event authority split.

### PR-3: Consume `next_best_action` Hints

- Worktree: `worktrees/monetization_planning_pr3`
- Branch: `feat/planning-next-best-action-consumers`
- Scope:
  - web/iOS display backend-driven prompts after PR-2 exists.
- Hard boundary:
  - web checkout remains fail-closed through existing `purchasePremium`.

### Deferred Follow-Up Waves

Do not start these until PR-3 is merged and `main` is stable:
- paywall copy alignment
- CBT premium packaging
- business-wave runtime follow-through

## Role Order Contract

### Bootstrap PR role order

1. `agent-coordinator`
2. `business-strategist-agent`
3. `marketing-strategist`
4. `cursor-specialist-agent`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `agent-coordinator`

### PR-1 pre-open role order

1. `agent-coordinator`
2. `architecture-specialist`
3. `backend-engineer`
4. `security-auditor`

### PR-2 pre-open role order

1. `agent-coordinator`
2. `backend-engineer`
3. `frontend-engineer`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `agent-coordinator`

### PR-3 pre-open role order

1. `agent-coordinator`
2. `frontend-engineer`
3. `creative-designer`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `agent-coordinator`

### Mandatory post-open review lane

- `qa-engineer-agent -> bug-hunter -> agent-coordinator`

### Agent-use contract

- The declared role order is mandatory for this wave.
- No assigned role agent may be skipped without updating the packet/runbook in the
  same lane.
- No ad-hoc internal role stack may replace the coordinator-declared order.

## Sync Points

1. **Bootstrap locked**
   - stale web-entitlement wording reconciled,
   - monetization planning wave epic exists in the ledger,
   - runbook + task packet committed,
   - bootstrap PR branch/worktree isolated and clean.
2. **PR-1 runtime seam**
   - `NextBestAction` contract exists,
   - intervention trigger engine is deterministic and fail-closed,
   - BMI / targets / weekly plan responses remain additive only.
3. **PR-2 analytics seam**
   - planning-surface ledger wiring reuses the merged PR `#1416` foundation,
   - exposure ledger event naming matches analytics canon,
   - no fake checkout or pricing truth enters the runtime.
4. **PR-3 client consumption**
   - web/iOS consume backend hints,
   - web purchase remains fail-closed,
   - merge readiness is current-head based.

## Execution Model

Before each PR:
- `git checkout main`
- `git fetch --prune origin`
- `git merge --ff-only origin/main`
- verify `main` current-head health
- create a fresh `worktree` + branch from synced `origin/main`

Inside each worktree before edits:
- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py --pr-phase pre_open ...`

Before each push:
- `pre-commit run --all-files`
- `make verify`

After PR open:
- rerun task bootstrap with `--pr-phase post_open_review`
- execute the mandatory post-open lane:
  - `qa-engineer-agent`
  - `bug-hunter`
  - `agent-coordinator`

Before any merge-ready claim:
- `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`
- confirm no unresolved actionable review/bot items remain
- wait at least one full review cycle after the latest human/bot activity

After merge:
- verify GitHub state is `MERGED`
- fast-forward local `main`
- re-check current-head health on `main`
- delete merged branch
- remove retired worktree
- clean only gitignored local artifacts from that retired worktree:
  - `artifacts/`
  - `.pytest_cache/`
  - `.mypy_cache/`
  - `.ruff_cache/`
  - `coverage.*`
  - per-worktree `.venv`
  - per-worktree `node_modules`
- only then create the next PR worktree

## Hard Rules

- Do not reopen billing / receipt / entitlement backbone work in this wave.
- Do not introduce client-side pricing truth or optimistic web checkout success.
- Do not weaken PRO / VIP guards or route ownership boundaries.
- Do not base monetization triggers on the current daily-progress placeholder path
  that still returns `0.0` progress semantics.
- Do not merge a PR in this wave while `main` is red, unstable, or pending fallout
  from the previous merge.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`

## Security Notes

- Keep the wave thin-client-safe: backend/session truth stays canonical.
- Do not add fake or browser-authoritative purchase state.
- Do not turn prompts or upsells into medical claims; PulsePlate remains a wellness
  and planning product, not diagnosis/treatment software.
- Do not mix monetization prompts with provider modernization or App Store secret handling.

## Marketing & GTM

- The commercial axis of this wave is reduced decision fatigue, not generic “AI”.
- The copy spine must stay:
  - BMI -> targets
  - targets -> plate
  - weekly plan -> export / recipe / repair
- Packaging/copy work is deferred until backend-owned prompts and analytics truth
  exist; PR-3 is the earliest safe point for that UI expression.
