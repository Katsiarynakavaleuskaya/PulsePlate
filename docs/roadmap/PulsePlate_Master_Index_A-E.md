# PulsePlate — Unified Execution Tracker
Batches A–E in one operational view: what is archived, what executes next, what stays queued and what must wait.

**Date:** 16 March 2026
**Last sync:** B1 completed (PR #1182); B2 next active layer.

## Current truth

| Current truth | What is next | What stays out of scope for now |
|---------------|--------------|----------------------------------|
| Batch A is archived after PR-6. Batch B is the next executable layer. Batches C–E stay prepared, but must not overtake the critical path. | **B1 completed.** Start **B2** → B3 → B4: Apple verify full activation, StoreKit contract, thin SubscriptionManager. | Do not pull AI differentiation, CI cleanup or GTM/brand work ahead of unresolved monetization/runtime and iOS paid-core work. |

## Batch B — Item-level execution tracker

| ID | Deliverable | Priority | Current state | Trigger to start | Next concrete action |
|----|-------------|----------|---------------|------------------|----------------------|
| B1 | Payments RU/BY + iOS Baseline Runtime W1 | P0/P1 | **✅ Completed** | — | PR #1182 merged. |
| B2 | Apple Receipt Verification Backend (full activation) | P0/P1 | **Next active** | After B1 merged | Prepare backend verify contract and failure paths |
| B3 | StoreKit Product Contract and Operational Setup | P0/P1 | Queued | After Apple verify direction is locked | Pin product IDs and operating contract |
| B4 | iOS SubscriptionManager Thin-Client Integration | P0/P1 | Queued | After StoreKit contract is fixed | Wire thin orchestration over backend billing truth |

**Batch rule:** PR-6 and Batch A governance work closed; do not mix with AI/GTM.

## Source basis

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
- `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md`
