# PR-P1: Home/Plate/Progress CTA Runtime Remediation Execution Plan

<!-- markdownlint-disable MD013 -->

**Status:** Skeleton ready (coordinator-first, runtime implementation not started)
**Branch:** `feat/hpp-cta-runtime-remediation`
**Date:** 2026-02-18

---

## Scope

### IN

- Home/Plate/Progress CTA runtime parity remediation.
- iOS placeholder CTA destination replacement.
- Web paywall CTA production wiring with explicit result handling.
- Deterministic CTA-level test additions (web+iOS).
- Matrix status sync after runtime evidence.

### OUT

- New product flows beyond Home/Plate/Progress.
- Backend feature expansion unrelated to CTA contracts.
- Design-system-wide restyling.
- Broad navigation architecture rewrite.

---

## Coordinator-First Execution Skeleton

### Phase 1 - CTA map freeze

- Extract exact CTA inventory from matrix SoT.
- Build mapping: CTA label -> current destination -> expected destination.
- Mark blockers and policy-sensitive seams (paywall, adapter boundaries).

### Phase 2 - Runtime remediation slices

- iOS: replace placeholder CTA destinations with canonical targets.
- Web: wire paywall CTA to production purchase path with deterministic success/failure handling.
- Keep thin-adapter policy and avoid client-side domain logic.

### Phase 3 - Deterministic validation

- Add/update CTA-level tests for critical Home/Plate/Progress paths.
- Validate error-envelope handling on paywall failure path.
- Re-run policy guards for thin adapter compliance.

### Phase 4 - Matrix and audit sync

- Update matrix statuses (`Exists Now / Missing / Implement Needed`) with evidence.
- Fill audit with command output and file anchors.
- Prepare PR body mapping for reviewer/bot discussion closure.

---

## Brainstorming-to-Execution Track

1. **Navigation parity option:** one canonical CTA mapping table shared across web+iOS docs.
2. **Paywall wiring option:** keep callback path as fallback only, with production purchase path as primary.
3. **Testing option:** CTA contract tests first, then visual-level smoke tests (Playwright/Xcode).
4. **Risk option:** feature-flag rollout for paywall path to reduce blast radius.
5. **Watch option:** keep a live check table in audit for CI/bot thread status until merge.

---

## Negative Scenario Matrix

| # | Failure scenario | Hole risk | Required guard |
| --- | --- | --- | --- |
| 1 | iOS CTA still routes to placeholders | user-flow dead end | deterministic destination assertions |
| 2 | Web paywall CTA handles success only | purchase failure regression | success+failure test pair required |
| 3 | Client adds domain logic during fix | thin-adapter violation | guard tests + code review grep |
| 4 | Matrix updated without runtime evidence | docs/runtime drift | evidence anchor required per CTA |
| 5 | Runtime+docs mixed with unrelated scope | review noise | PR scope lock and file-list guard |

---

## Deterministic Validation Commands (Skeleton)

```bash
make test-fast
pytest -q tests/test_repo_policy_guards.py
cd frontend && npm test
cd frontend && npm run build
python scripts/ci/check_pr_body_phase2_gates.py --body "<PR_BODY>"
make verify
```

---

## DoD

- [ ] iOS Home/Plate/Progress CTAs are no longer placeholders.
- [ ] Web paywall CTA wiring is production-ready with deterministic result handling.
- [ ] CTA-level deterministic tests are added for critical paths.
- [ ] Matrix status is updated with file/evidence anchors.
- [ ] Required local/CI gates are green with no unresolved review threads.
