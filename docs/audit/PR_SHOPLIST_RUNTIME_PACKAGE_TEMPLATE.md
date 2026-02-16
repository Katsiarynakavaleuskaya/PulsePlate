# Runtime PR Template — Shoplist Flow Stabilization

## Context Gathering Snapshot

- **Document type:** Runtime work-package PR description.
- **Primary audience:** Reviewers, maintainers, bots, and future contributors.
- **Desired impact:** Fast, deterministic review with zero ambiguity on scope and acceptance gates.
- **Source context:** `docs/audit/PR_SHOPLIST_FLOW_STABILIZATION_WORK_PACKAGE_PLAN.md`, `AGENTS.md`, `docs/roadmap/BACKLOG_LEDGER.md`.
- **Constraints:** One value package (`plan -> shoplist`), no scope creep, merge only with green CI and resolved review threads.

## Evidence anchors

- `core/shoplist.py:1`
- `tests/core/test_shoplist_contract.py:1`
- `AGENTS.md:1352`

## PR Title

`feat(shoplist): stabilize contract-only helpers into end-to-end user flow`

## Outcome

Deliver one deterministic backend flow outcome:

`plan -> shoplist`

This PR is a complete, testable, and reversible runtime package (not scaffolding-only).

## Flow Definition

- **plan:** canonical backend plan payload used as the source input for list generation.
- **shoplist:** canonical shopping-list payload derived from the plan input.
- **plan -> shoplist:** given the same valid input fixtures, the flow must produce identical outputs (deterministic contract).

## Scope Freeze

### IN

- Flow wiring for `plan -> shoplist` within canonical/compat boundaries.
- Contract assertions:
  - 200 response shape,
  - key failures (422/401/403/429 where applicable),
  - explicit content-type and error envelope checks.
- One deterministic integration happy path.
- One deterministic negative/edge matrix.
- No import hygiene or guard-order regressions.
- Minimal docs touch only when needed to describe flow call and error envelope.

### OUT

- AI/RAG endpoints.
- iOS/frontend expansion.
- Security suppression and CVE config changes.
- Unrelated refactor/cleanup.

Any OUT item discovered during execution is deferred to `docs/roadmap/BACKLOG_LEDGER.md`.

## Test Plan

### Contract tests

- Validate request/response shape.
- Assert `Content-Type`.
- Assert stable error envelope (no upstream internal leak).

### Integration test

- Deterministic full flow `plan -> shoplist`.
- Identical inputs produce identical outputs.

### Negative tests

- Invalid inputs -> 422.
- Auth/tier mismatch -> 401/403.
- Rate limit -> 429 for flow endpoints that use `@limit_if_available`.
- If no endpoint in this flow is rate-limited, state that explicitly in the PR test plan.

### Anti-flake rules

- No `--lf` dependence.
- Deterministic fixtures only.
- No mutable shared global state between tests.
- Explicit assertions; avoid implicit schema assumptions.

## Security Checks

- Guard order is preserved.
- No tier bypass through compat aliases.
- No token/secret exposure in payloads or logs.
- No upstream exception leakage in API responses.

## Rollback Plan

- Full package can be reverted with one PR revert.
- No irreversible migration in this package.
- Compat behavior remains stable.

## Metrics Block (8-12 week evaluation window)

- Median time-to-merge.
- Review iterations per PR.
- First-run CI pass rate.
- Revert/hotfix rate within 14 days.
- Package completion rate.

## Pre-push Checklist

- [ ] `pre-commit run --all-files`
- [ ] `make verify`
- [ ] targeted `pytest -q` for flow + relevant guards
- [ ] no unrelated diff in PR
- [ ] no unresolved TODO/FIXME in touched files (or explicitly justified)

## Ready-to-Merge Gates

- [ ] 0 unresolved review threads
- [ ] 0 actionable bot comments
- [ ] required checks PASS
- [ ] IN/OUT scope validation confirmed

**Note:** Green CI is necessary but not sufficient; merge is blocked until all gates above pass.

## Deferred / Follow-ups

- Link any deferred OUT items to `docs/roadmap/BACKLOG_LEDGER.md` with Owner/Priority/Target PR/DoD.

## Reader Testing Checklist (Doc-Coauthoring Stage 3)

Ask a fresh reader (or separate agent) these questions:

1. What exactly is the single user-visible outcome?
2. Which items are explicitly OUT of scope?
3. What tests prove determinism and contract stability?
4. What blocks merge even when CI is green?
5. How can this package be rolled back safely?

If any answer is ambiguous, update this template before reuse.
