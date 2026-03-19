# PulsePlate — Unified Execution Tracker
Batches A–E in one operational view: what is archived, what executes next, what stays queued and what must wait.

**Date:** 19 March 2026
**Last sync:** B3 operational setup truth consolidated after the StoreKit contract baseline in PR #1172 and B2 activation normalization in PR #1185.

## Current truth

| Current truth | What is next | What stays out of scope for now |
|---------------|--------------|----------------------------------|
| Batch A is archived after PR-6. Batch B monetization foundations are already merged on `main`: B1 baseline runtime in PR #1182, StoreKit contract baseline in PR #1172, thin SubscriptionManager groundwork in PR #1171, Apple verify → activation normalization in PR #1185, and B3 operational/setup truth is now consolidated into the canonical StoreKit contract. | The next Batch B work is follow-through, not first-pass baseline creation: backend-driven SubscriptionManager hardening and the remaining runtime cleanup around the merged billing truth. | Do not reopen baseline contract work, and do not mix unrelated AI/GTM or dependency-remediation scope into this lane. |

## Batch B — Item-level execution tracker

| ID | Deliverable | Priority | Current state | Trigger to start | Next concrete action |
|----|-------------|----------|---------------|------------------|----------------------|
| B1 | Payments RU/BY + iOS Baseline Runtime W1 | P0/P1 | **✅ Completed** | — | PR #1182 merged. |
| B2 | Apple Receipt Verification Backend (full activation) | P0/P1 | **✅ Completed** | — | PR #1185 merged. |
| B3 | StoreKit Product Contract and Operational Setup | P0/P1 | **✅ Completed** | — | Future TestFlight / App Store setup work must use the canonical checklist in `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`. |
| B4 | iOS SubscriptionManager Thin-Client Integration | P0/P1 | **Runtime client follow-through still pending** | After backend activation and StoreKit contract baseline are merged | Complete the thin-client activation handoff so iOS forwards backend activation contract data without rebuilding billing truth on-device. |

**Batch rule:** PR-6 and Batch A governance work closed; do not mix with AI/GTM.

## Source basis

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ios-storekit-products`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ios-subscription-manager`
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
- `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`
- `docs/IOS_API_INTEGRATION.md`
- `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md`
