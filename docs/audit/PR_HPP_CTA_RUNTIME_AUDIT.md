# PR-P1: Home/Plate/Progress CTA Runtime Remediation Audit

<!-- markdownlint-disable MD013 -->

**Status:** Skeleton audit ready (pre-implementation)
**Branch:** `feat/hpp-cta-runtime-remediation`
**Date:** 2026-02-18

---

## Scope Validation

### In scope

- Home/Plate/Progress CTA runtime remediation.
- iOS CTA destination de-placeholdering.
- Web paywall CTA production wiring and deterministic handling.
- Deterministic CTA-level test coverage and matrix status synchronization.

### Out of scope

- New product surfaces beyond Home/Plate/Progress.
- Backend feature expansion unrelated to CTA flow.
- Global visual redesign outside execution matrix.

---

## Evidence Anchors (Current Baseline)

- CTA matrix source of truth: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:1`
- Ledger item to remediate: `docs/roadmap/BACKLOG_LEDGER.md:479`
- Frontend policy baseline: `frontend/AGENTS.md:1`
- iOS policy baseline: `ios/AGENTS.md:1`

---

## Recommended Execution Shape

1. Freeze CTA inventory and expected destination map before code edits.
2. Implement iOS and web changes in separate deterministic slices.
3. Prove success and failure paths for paywall CTA.
4. Update matrix statuses only after tests and evidence are green.

---

## Live Watch Checklist (CI + bot dialogue)

- [ ] Required checks are PASS on PR head (ignore cancelled stale runs).
- [ ] No unresolved review threads.
- [ ] CodeRabbit status is pass/no actionables.
- [ ] Sourcery and Cubic statuses are pass/no actionables.
- [ ] PR Body Phase2 gates pass with fixed-in-commit mapping.

---

## Command Evidence Skeleton (to fill during implementation)

```bash
make test-fast
pytest -q tests/test_repo_policy_guards.py
cd frontend && npm test
cd frontend && npm run build
python scripts/ci/check_pr_body_phase2_gates.py --body "<PR_BODY>"
make verify
```

Expected completion format per command:

- exact command
- 1-3 raw output lines
- exit code

---

## Go/No-Go Criteria

- [ ] CTA runtime gaps are remediated within defined scope.
- [ ] Deterministic CTA tests cover critical Home/Plate/Progress paths.
- [ ] Thin-adapter policy is preserved (no client domain logic drift).
- [ ] Matrix status is synchronized to runtime evidence.
- [ ] All required local/CI gates pass with zero unresolved threads.
