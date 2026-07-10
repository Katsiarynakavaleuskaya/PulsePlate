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
- `83bb059f9` - discard stale rate-limit receipts as cache-only state, close the
  functional `getattr` legacy-guard bypass, and make CSP policy preservation
  tests independent of the implementation constant.
- `a8a004acb` - type the static middleware alias state added by the QA guard fix.
- `d99f79aae` - require the exact `RateLimitExceeded` exception-class key and
  block package-module aliases for forbidden runtime registrars.
- `7d75b972d` - isolate mutable limiter state in the focused invariant test and
  close static-string and star-import legacy registrar guard bypasses.
- `4444eac4a` - resolve statically bound `import_module(...)` targets and close
  the remaining dynamic registrar guard bypass.

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
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed
  on implementation head `d99f79aae`.
- [x] Codex Security diff scan / finding discovery completed on
  `e7748291c..d99f79aae`: 6/6 source files reviewed, zero reportable findings.
- [x] `pulseplate-pr-review` completed against the merge-base-corrected 15-file
  diff; its size advisory was reviewed and dispositioned below.
- [ ] Current-head CI completed.
- [ ] Strict merge-readiness checks completed after the final review cycle.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558343216
Evidence: `8218a0c13495a5fb8b94420351115be4024f57f4` is an ancestor of current implementation head `d99f79aae5c52b86fd59e6035cc3779972700c2a`.
Reason: The comment described a transient published-head mismatch that no longer exists in the current branch history.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558343226 -> d99f79aae5c52b86fd59e6035cc3779972700c2a
Commit: d99f79aae5c52b86fd59e6035cc3779972700c2a
Evidence: Package-module registrar aliases are detected by `scripts/ci/check_legacy_growth_guard.py` and covered by `tests/test_legacy_growth_guard.py`.

Disposition: NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#pullrequestreview-4670658879
Evidence: Snapshot rollback, callable/state classification, and all partial/foreign/late failure paths are covered by `tests/test_production_runtime_invariants.py` within the approved 15-file budget.
Reason: The three Sourcery items are maintainability alternatives, while the current implementation is isolated, fail-closed, and deterministically tested.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558593404 -> 7d75b972dcbcccbb0c54c2f17453b9ac62e797fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558631549 -> 7d75b972dcbcccbb0c54c2f17453b9ac62e797fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558631554 -> 7d75b972dcbcccbb0c54c2f17453b9ac62e797fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558631559 -> 7d75b972dcbcccbb0c54c2f17453b9ac62e797fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#pullrequestreview-4671065704 -> 7d75b972dcbcccbb0c54c2f17453b9ac62e797fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#pullrequestreview-4671105883 -> 7d75b972dcbcccbb0c54c2f17453b9ac62e797fd
Commit: 7d75b972dcbcccbb0c54c2f17453b9ac62e797fd
Evidence: `tests/test_production_runtime_invariants.py`, `scripts/ci/check_legacy_growth_guard.py`, and `tests/test_legacy_growth_guard.py`; focused pytest, guard, MyPy, `make validate-changed`, pre-commit, and pre-push hooks pass.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558937879 -> 4444eac4aaf7b29abc59a44c2621a8d8c6cdf0fa
Commit: 4444eac4aaf7b29abc59a44c2621a8d8c6cdf0fa
Evidence: `_static_module_reference()` now resolves `import_module()` arguments through `_resolve_static_string()`; the exact static module/method binding bypass is covered by `tests/test_legacy_growth_guard.py`, with focused pytest, guard, MyPy, `make validate-changed`, pre-commit, and pre-push PASS.

## Post-Open Review Dispositions

Disposition: FIXED
Thread: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558937879
Commit: `4444eac4aaf7b29abc59a44c2621a8d8c6cdf0fa`
Evidence: `scripts/ci/check_legacy_growth_guard.py` passes `static_string_bindings` through `_static_module_reference()` and resolves the `import_module()` target with the existing static-string helper; `tests/test_legacy_growth_guard.py` covers the direct static module and registrar binding combination.
Reason: The finding was a valid fail-closed guard bypass and was fixed before this mapping update.

Disposition: FIXED
Threads: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558593404, https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558631549, https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558631554, https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558631559
Reviews: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#pullrequestreview-4671065704, https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#pullrequestreview-4671105883
Commit: `7d75b972dcbcccbb0c54c2f17453b9ac62e797fd`
Evidence: The production-invariant test restores the limiter singleton through `monkeypatch`; the legacy guard reuses `_resolve_static_string()` for `getattr()` and rejects star imports from the two forbidden registrar modules, with direct synthetic regression coverage.
Reason: These were actionable current-PR defects and were fixed before this mapping was updated.

Disposition: NOT-A-BUG
Thread: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558343216
Evidence: `git merge-base --is-ancestor 8218a0c13495a5fb8b94420351115be4024f57f4 d99f79aae5c52b86fd59e6035cc3779972700c2a`
Reason: The comment correctly identified a transient published-head mismatch,
but the current implementation head contains `8218a0c13` in its ancestry. The
canonical mapping now lists every post-open implementation fix explicitly.

Disposition: FIXED
Thread: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#discussion_r3558343226
Commit: `d99f79aae5c52b86fd59e6035cc3779972700c2a`
Evidence: `scripts/ci/check_legacy_growth_guard.py`,
`tests/test_legacy_growth_guard.py`; the guard now tracks package-module imports
such as `from app.security import rate_limit` and rejects calls through those
aliases.

Disposition: NOT-A-BUG
Review: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2096#pullrequestreview-4670658879
Evidence: `tests/test_production_runtime_invariants.py` exercises exact snapshot
restore, partial/foreign/late failure, and callable/state classification; the
15-file cap remains satisfied.
Reason: Sourcery's three items are maintainability alternatives rather than
runtime defects. The private FastAPI/Starlette fields are isolated in one
transactional registrar and guarded by focused compatibility tests; callable
identity stays local to its two ownership boundaries to avoid a new cross-layer
utility; exhaustive literal states are closed by fail-closed branches and tests.

Disposition: NOT-A-BUG
Evidence: `git diff --stat e7748291ced0f9a79f93fda9757506ecc722a50e..d99f79aae5c52b86fd59e6035cc3779972700c2a`,
98% runtime diff coverage, 554-test focused bundle, and the operator-approved
15-file privileged-change budget.
Reason: `pulseplate-pr-review` emitted only the calibrated `large-diff-risk`
advisory. The diff is cohesive around one security-critical middleware ownership
boundary; most added lines are deterministic failure-state and guard tests, so
splitting production code from its rollback/security evidence would weaken
reviewability.

### Post-Open Role Findings

Disposition: FIXED
Commit: `83bb059f9`
Evidence: `app/security/rate_limit.py`,
`scripts/ci/check_legacy_growth_guard.py`,
`tests/test_production_runtime_invariants.py`, `tests/test_legacy_growth_guard.py`
Reason: QA found stale-receipt false partial state, a functional `getattr`
middleware-guard bypass, and a self-referential CSP policy assertion; all three
were fixed in runtime/guard code and independent tests before mapping.

Disposition: FIXED
Commit: `a8a004acb`
Evidence: focused MyPy pass for the typed static middleware alias map.
Reason: The QA guard fix exposed a precise type annotation gap; it was corrected
without suppression.

Disposition: FIXED
Commit: `d99f79aae`
Evidence: `app/security/rate_limit.py`,
`scripts/ci/check_legacy_growth_guard.py`,
`tests/test_production_runtime_invariants.py`, `tests/test_legacy_growth_guard.py`
Reason: Bug-hunter found reload-equivalent exception keys could be accepted and
package-module aliases could bypass the legacy registrar guard; both controls now
require the intended exact/fail-closed behavior.

Disposition: NOT-A-BUG
Evidence: Codex Security scan
`8e4e293d-cebe-4f8b-ad3d-553f9be39159`, 6/6 changed source files with full-file
receipts and zero reportable findings.
Reason: Post-fix security review closed the CSP, SlowAPI, canonical stack,
legacy ownership, and deleted fingerprint-adapter paths without candidates.

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
