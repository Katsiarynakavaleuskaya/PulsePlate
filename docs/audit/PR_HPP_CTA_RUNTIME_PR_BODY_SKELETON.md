# PR Body Skeleton: Home/Plate/Progress CTA Runtime Remediation

## Summary

- Execute runtime remediation for Home/Plate/Progress CTA gaps from matrix SoT.
- Remove iOS placeholder CTA destinations in critical user paths.
- Add production-ready web paywall purchase CTA wiring with deterministic result handling.
- Add deterministic CTA-level tests and synchronize matrix status after runtime evidence.
- Evidence anchors: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:1`,
  `docs/roadmap/BACKLOG_LEDGER.md:479`.

## Scope

### IN

- iOS CTA destination remediation for Home/Plate/Progress.
- Web paywall CTA wiring and failure/success handling.
- Deterministic CTA-level test coverage.
- Matrix and audit synchronization.

### OUT

- New feature surface outside Home/Plate/Progress.
- Broad navigation redesign or non-CTA refactors.
- Backend product changes unrelated to CTA contract.

## Risks / Mitigations

- Placeholder paths remain in iOS -> enforce destination assertions per CTA.
- Paywall flow handles success only -> require deterministic failure-path tests.
- Client logic drift -> enforce thin-adapter guards and policy checks.
- Docs/runtime divergence -> matrix updates only after evidence-backed runtime pass.

## Test Plan

- `make test-fast`
- `pytest -q tests/test_repo_policy_guards.py`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- `python scripts/ci/check_pr_body_phase2_gates.py --body "<PR_BODY>"`
- `make verify`

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping

- [ ] iOS Home/Plate/Progress CTA destination remediation
- [ ] Web paywall CTA production purchase wiring
- [ ] Deterministic CTA tests for critical paths
- [ ] Matrix + audit status synchronization

## Deferred / Follow-ups

- [ ] Additional CTA polish outside Home/Plate/Progress in a separate package
- [ ] Extended end-to-end CTA telemetry/reporting in follow-up PR
