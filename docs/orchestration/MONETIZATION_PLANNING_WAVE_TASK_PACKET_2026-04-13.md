# Monetization Planning Wave Task Packet

**Date:** 2026-04-13 (`America/New_York`)
**Mode:** coordinator-owned monetization execution packet
**Worktree model:** one clean PR worktree per slice

## Decision Question

How should PulsePlate open the next monetization line on top of the existing
planning-first product flow without reopening billing/provider work that is already
closed on `origin/main`?

## Purpose

Freeze one explicit execution packet for the planning-flow monetization wave so
coordinator-owned role order, PR decomposition, and cleanup discipline stay
canonical across the PR train.

## Hard Boundaries

- No new receipt verification or entitlement-routing rewrite
- No web checkout success path beyond the current fail-closed contract
- No client-side pricing truth
- No dynamic pricing, QoS tiers, concurrency pricing, or gamification in the opening wave
- No PR-2 / PR-3 work before the bootstrap PR and PR-1 contracts are in place

## Canonical PR Order

1. `docs/monetization-planning-wave-bootstrap`
   - worktree: `worktrees/monetization_planning_bootstrap`
   - branch: `docs/monetization-planning-wave-bootstrap`
2. `feat(growth): add intervention trigger engine v1`
   - worktree: `worktrees/monetization_planning_pr1`
   - branch: `feat/monetization-trigger-engine-v1`
3. `feat(analytics): add planning paywall exposure ledger`
   - worktree: `worktrees/monetization_planning_pr2`
   - branch: `feat/planning-paywall-exposure-ledger`
4. `feat(frontend): consume next_best_action hints`
   - worktree: `worktrees/monetization_planning_pr3`
   - branch: `feat/planning-next-best-action-consumers`

Deferred until after PR-3:
- paywall copy alignment
- CBT premium packaging
- business-wave runtime follow-through

## Required Role-Agent Order

### Bootstrap PR

1. `agent-coordinator`
2. `business-strategist-agent`
3. `marketing-strategist`
4. `cursor-specialist-agent`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `agent-coordinator`

### PR-1 pre-open

1. `agent-coordinator`
2. `architecture-specialist`
3. `backend-engineer`
4. `security-auditor`

### PR-2 pre-open

1. `agent-coordinator`
2. `backend-engineer`
3. `frontend-engineer`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `agent-coordinator`

### Mandatory post-open review lane

- `qa-engineer-agent -> bug-hunter -> agent-coordinator`

## Agent-Use Contract

- Every coordinator-assigned role in this packet must be used in the declared order.
- No assigned role may be skipped without updating this packet or the runbook in the
  same lane.
- No ad-hoc internal role stack may replace the coordinator-owned order.
- Bootstrap remains docs/governance-only even if follow-up implementation ideas are known.

## Current Canon

- PR `#1296` merged `2026-04-02` (`America/New_York`)
- PR `#1312` merged `2026-04-03` (`America/New_York`)
- PR `#1381` merged `2026-04-09` (`America/New_York`)
- PR `#1416` merged `2026-04-15` (`America/New_York`) and closed the general paywall exposure ledger foundation (`docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md:58`)
- PR `#1434` merged `2026-04-17` (`America/New_York`) and closed intervention trigger engine v1 (`docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md:59`, `docs/review/PR_1434_FIXED_MAPPING.md:2`)
- execution-time `main` / `origin/main` baseline for PR-2: `7bf5d8819e33b40b35cef1aac7c7fcc76c32229f` (`docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md:60`)

## PR-1 Contract Snapshot

### New additive contract

- `app/schemas/intervention.py`
  - `NextBestAction`
  - fields:
    - `type`
    - `recommended_surface`
    - `recommended_tier`
    - `trigger_reason`
    - `why_now`

### New backend seam

- `app/services/intervention_trigger_engine.py`
  - deterministic rule-only logic
  - no billing/provider/client truth
  - fail-closed by default

### Response seams to extend

- `BMICalculateResponse`
- `WHOTargetsResponse`
- `WeeklyMealPlanResponse`

Each receives:
- `next_best_action: NextBestAction | None`

### Wiring boundaries

- `app/routers/bmi.py`
- `app/routers/pro_nutrition_contracts.py`
- `app/routers/pro.py`

Do not wire through billing or checkout paths.

### Fixed rule set for v1

- `post_bmi` -> `PRO` targets
- `targets_ready` -> `pro_daily_plate`
- `weekly_plan_ready` -> `VIP` export / recipe upsell

### Explicitly out of scope for PR-1

- `app/services/payments_activation.py`
- `app/security/llm_monthly_quota.py`
- web checkout
- iOS `SubscriptionManager`
- Apple Server API migration
- App Store offers / assets
- dynamic pricing / concurrency / QoS billing
- streaks / gamification

## Success Criteria

1. Bootstrap PR reconciles stale monetization wording before runtime work starts.
2. PR-1 introduces one backend-owned additive monetization seam without breaking
   current API payloads.
3. PR-2 adds planning paywall exposure measurement before client experiments.
   - This is a narrow planning-specific delta on top of PR `#1416`, not a second ledger-foundation PR (`docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md:58`, `docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md:92`).
4. PR-3 consumes backend hints while preserving fail-closed web checkout.
5. Each PR starts from a fresh worktree off synced `origin/main`.
6. After each merge, local `main` is fast-forward synced and old worktree artifacts
   are cleaned before the next PR starts.

## Canonical Files

- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/MONETIZATION_PLANNING_WAVE_TASK_PACKET_2026-04-13.md`
- `README.md`
- `docs/contracts/PRODUCT_TIER_MAP.md`
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
- `app/routers/bmi.py`
- `app/routers/pro.py`
- `frontend/src/lib/usePremium.ts`
- `frontend/src/lib/paywallPurchase.ts`

## Validation

- Before edits:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
- Before push:
  - `pre-commit run --all-files`
  - `make verify`
- Before merge-ready claim:
  - `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`

## Cleanup Contract

After each merged PR:
- fast-forward local `main`
- confirm current-head `main` health
- delete merged branch
- delete retired worktree
- remove only gitignored local artifacts from that worktree:
  - `artifacts/`
  - `.pytest_cache/`
  - `.mypy_cache/`
  - `.ruff_cache/`
  - `coverage.*`
  - `.venv`
  - `node_modules`

If `main` is red or unstable after merge, stop the train and stabilize `main`
before opening the next monetization PR.

## Security Notes

- This wave must remain thin-client-safe and wellness-safe.
- No browser-authoritative purchase state.
- No relaxed PRO/VIP gates.
- No medical-claim phrasing in monetization prompts.
- No provider modernization hidden inside growth work.

## Marketing & GTM

- The value proposition is reduced decision fatigue across planning flow, not
  “AI access” as a generic bundle.
- Canonical progression axis:
  - BMI -> targets
  - targets -> plate
  - weekly plan -> export / recipe / repair
- Copy/packaging follow-through is intentionally delayed until backend-owned
  hints and analytics truth exist.
