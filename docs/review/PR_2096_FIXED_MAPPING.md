# PR #2096 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096
Branch: `codex/canonicalize-http-middleware-stack`

## Summary

Move CSP, SlowAPI, metrics, request telemetry, and tracing registration into one
canonical fail-closed HTTP stack. Remove legacy middleware ownership and the
redundant pseudonymous request logger without changing routes, OpenAPI, clients,
DB state, auth, tiers, or CSP policy.

## Scope

- Add stateless pure-ASGI CSP nonce middleware.
- Add transactional canonical HTTP stack registration in `app/main.py`.
- Make SlowAPI wiring idempotent, live-state validated, and fail closed.
- Remove direct middleware/rate-limit ownership from `legacy_app.py`.
- Delete the dead request-specific fingerprint helper and its tests.
- Reduce legacy route/middleware ownership allowlist to empty and block
  aliased/functional/indirect reintroduction.

## Out Of Scope

CSP policy hardening, observability schema rewrites, auth/tier changes, route or
OpenAPI changes, lifespan/app-factory inversion, DB changes, and Creative-Code
mutable-surface expansion.

## Implementation Commits

- `8218a0c13` - canonicalize HTTP middleware ownership, harden SlowAPI wiring,
  remove duplicate logging/dead fingerprint code, tighten the legacy guard, and
  add production-focused tests.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/68c6dce1612c.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Required pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> backend-engineer -> qa-engineer-agent -> bug-hunter`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed for published head `b90e8dc36`; no
  review threads existed at this pass.
- [x] Fixed in commit mapping completed for published head `b90e8dc36`; the
  no-actionable marker will be replaced if post-open review emits findings.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI completed.
- [ ] Strict merge-readiness checks completed after the final review cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Pre-Open Implementation Evidence

Disposition: FIXED
Commit: `8218a0c13`
Evidence: `app/bootstrap/http_stack.py`, `app/middleware/csp.py`,
`app/security/rate_limit.py`, `tests/test_production_runtime_invariants.py`
Reason: Middleware ordering, CSP response behavior, SlowAPI exact wiring,
idempotency, partial/duplicate/foreign/late rejection, and transactional rollback
are enforced in production code and focused tests.

Disposition: FIXED
Commit: `8218a0c13`
Evidence: `legacy_app.py`, `scripts/ci/check_legacy_growth_guard.py`,
`tests/test_legacy_growth_guard.py`
Reason: `legacy_app.py` owns zero HTTP routes and zero middleware registration;
the guard rejects decorator, functional, bound-alias, direct, module-qualified,
`getattr`, and `import_module` reintroduction patterns.

Disposition: FIXED
Commit: `8218a0c13`
Evidence: `core/fingerprint_security.py`, deletion of
`tests/test_fingerprint_security_client_fingerprint.py`, repository call-site
search
Reason: The removed legacy request logger was the last production caller of the
private request fingerprint adapter; reusable fingerprint/secret helpers and
data-class constants with other callers remain.

## Pre-Open Role Evidence

- `agent-coordinator`: scope and 15-file privileged budget locked; middleware,
  lifespan, and app-factory work kept separate.
- `architecture-specialist`: exact owned-stack projection, third-party-layer
  tolerance, and pre-global-assignment bootstrap order required and implemented.
- `security-auditor`: CSP copy-before-mutation, no request-local instance state,
  exact SlowAPI handler/middleware/limiter validation, and rollback required and
  implemented.
- `backend-engineer`: existing registrars reused without internal rewrite; legacy
  logger and dead adapter removed rather than relocated.
- `qa-engineer-agent`: failure-state, streaming, non-HTTP, 404, rehydration,
  OpenAPI, and 429 proof matrix implemented.
- `bug-hunter`: foreign/partial/late, global app identity, alias bypass, and
  stale-marker false-positive paths covered.

## Premortem Evidence

- Artifact:
  `artifacts/orchestration/premortem/canonical_http_stack_20260710.md`
- Result: all actual-diff findings closed through code/tests or repository-backed
  `NOT-A-BUG` evidence before PR open.
- A Ruff finding in the new legacy guard was fixed before commit and the full
  pre-commit suite was rerun successfully.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/exp-http-stack-oracle-20260710.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`; `failure_class: null`; `mutated_paths: []`;
  `shared_tree_untouched: true`.
- Contribution: `none`; no co-author trailer required.
- This artifact has no candidate-patch, promotion, GitHub-write, thread, or
  readiness authority.

## Validation Evidence

- Preflight and agent consistency - PASS.
- Focused pytest bundle - PASS (554 tests).
- Legacy growth guard - PASS.
- Focused MyPy - PASS.
- Runtime diff coverage - 98%.
- OpenAPI generation/check and committed generated artifacts - zero diff.
- `make validate-changed` after commit - PASS.
- `pre-commit run --all-files` - PASS.
- Pre-push hooks - PASS, including MyPy, pip-audit, backend tests, full-repo
  Bandit, and Docker build.

## Deferred / Follow-ups

- Extract lifespan/startup ownership.
- Extract FastAPI metadata/OpenAPI factory inputs.
- Invert FastAPI app-factory ownership.
- Inventory remaining compatibility exports and delete `legacy_app.py`.
- Evaluate strict CSP separately, preferably in report-only mode first.

## Local Verification Exception

Local `make verify` was not run, in accordance with the repository local
full-verify budget rule. Heavy verification remains a current-head CI signal.

## Merge Readiness

- [x] Focused implementation and local required gates completed on `8218a0c13`.
- [x] Non-draft PR opened.
- [ ] Mandatory post-open role/security/review chain completed.
- [ ] Current-head required CI completed successfully.
- [ ] Review bots report no unresolved actionable findings.
- [ ] Strict authenticated merge-readiness wrapper passes after the wait-window.

Merge readiness is not claimed.
