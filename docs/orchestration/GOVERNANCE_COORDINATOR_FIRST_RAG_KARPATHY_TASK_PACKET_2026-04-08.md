# Governance Task Packet — Coordinator-First + RAG/LLM/Karpathy Epic Spine

**Date:** 2026-04-08
**Scope:** docs/governance only
**Mode:** pre-open governance packet

## Purpose

Freeze one docs-only governance lane that:
- makes coordinator-first startup a hard start gate;
- keeps the machine-local launcher explicitly opt-in and host-local;
- normalizes the separate RAG/LLM/Karpathy epic rails without mixing them into release-fix work.

## Hard boundaries

- No runtime/product code changes
- No OpenAPI or contract-surface mutation
- No absorption of `docs/review/PR_1372_FIXED_MAPPING.md` into this lane
- No claim that markdown alone guarantees raw-session auto-start
- No next-PR start while synced local `main` is red or unstable

## Required role-agent order

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`

## Agent-use contract

- Every coordinator-assigned role agent in this packet must be used in the declared order.
- No assigned role agent may be skipped without an explicit packet update in the same lane.
- No ad-hoc internal role stack may replace this order.
- The canonical post-open `qa-engineer-agent -> bug-hunter` lane remains mandatory.

## Canonical files

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/orchestration/workflow.md`
- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
- `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

## Deliverables

- repo-global coordinator-first wording updated to hard start-gate language
- launcher/runbook line merged into the same canonical governance lane
- explicit `main`-stability-before-next-PR rule
- explicit branch/artifact cleanup protocol
- canonical two-rail RAG/LLM/Karpathy packet committed
- backlog umbrella normalization for the AI runtime rail and advisory wiki rail

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- grep verification for coordinator-first wording consistency
- grep verification for `main`-green-before-next-PR wording
- grep verification for cleanup/sync protocol
- grep verification for the five new backlog anchors

## Next-PR rule

After this governance PR merges:
- sync local `main`;
- verify current-head `main` health;
- if `main` is not green/stable, stop and stabilize `main`;
- only then open the next narrow epic slice.
