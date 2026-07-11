# PR #2099 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099
Branch: `codex/extract-canonical-application-lifespan`

## Summary

Move application startup/shutdown ownership from `legacy_app.py` and hidden
food-search lifespan wrapping into one canonical, deterministic lifecycle while
preserving FastAPI instance identity, OpenAPI, DB fallback, scheduler policy,
routes, auth, tiers, schemas, and FoodDB authority.

## Scope

- Add `app.bootstrap.lifespan` with explicit per-start hooks and reverse-order
  cleanup through `AsyncExitStack`.
- Acquire and dispose food-search resources transactionally during lifespan.
- Preserve the legacy-created FastAPI instance while reducing the legacy
  lifecycle implementation to a canonical re-export.
- Block lifecycle implementation, hidden wrapping, and legacy dependency lookup
  from regrowing in the compatibility seam.
- Replace brittle alias/global lifecycle tests with injected hooks and real
  `TestClient` lifespan coverage.

## Out Of Scope

FastAPI app-factory inversion, OpenAPI metadata/builder migration, deployment
entrypoint changes, route/auth/tier/schema changes, DB fallback or scheduler
policy changes, Creative-Code mutable-surface expansion, and `legacy_app.py`
deletion.

## Implementation Commits

- `444b9a80d340ecc89c79cd2f5c6c987b3bb03157` - refresh the detect-secrets
  baseline after lifecycle coverage moved.
- `6f629181cc1fca5a10d8e98e02811348a594ca03` - extract canonical lifecycle
  ownership, transactional food-search resources, architecture guards, focused
  tests, and scoped documentation.
- `1e2d4918c5b6f6cf67d11865d218bf0253728f16` - release food-search ownership
  after resolver failures, close lifecycle-guard alias/dynamic bypasses, and add
  explicit body-cancellation and scheduler-start-failure evidence.
- `e28fb34c3` - reject FastAPI keyword-expansion and qualified dynamic-facade
  bypasses reported by the sealed Codex Security diff scan.
- `31bd2d457` - require stable single bindings for canonical lifespan aliases and
  static strings, closing the targeted security-rescan findings.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/75988d98c2b6.json`
- Required pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`.
- Creative-Code remained `oracle_only_governance_reviewer`; no candidate patch,
  promotion, or app-layer mutation permission was used.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial discussion-thread pass completed for published head
  `6f629181cc1fca5a10d8e98e02811348a594ca03`; no review threads existed at
  this pass.
- [x] Initial fixed-in-commit mapping completed for published head
  `6f629181cc1fca5a10d8e98e02811348a594ca03`; this no-actionable state must be
  replaced if post-open review emits findings.
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter -> security-auditor`
  pass completed.
- [x] Codex Security diff scan / finding discovery completed; scan
  `fe7a0056-e0d1-4b90-b5ba-84adc40060dc` reviewed 8/8 bounded surfaces and
  reported two Medium/P2 lifecycle-guard findings fixed in `e28fb34c3`.
- [x] Targeted Codex Security rescan
  `98ca8e42-2586-4db9-812a-0301ed0a3289` reviewed 8/8 bounded surfaces and
  reported two additional Medium/P2 binding-stability findings fixed in
  `31bd2d457`.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI completed.
- [ ] Strict merge-readiness checks completed after the final review cycle.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099
Evidence: Initial published-head review inventory on `6f629181cc1fca5a10d8e98e02811348a594ca03` contained no review threads.
Reason: This is the parser-safe initial no-actionable marker; it must be replaced if post-open review emits findings.

## Pre-Open Implementation Evidence

Disposition: FIXED
Commit: `6f629181cc1fca5a10d8e98e02811348a594ca03`
Evidence: `app/bootstrap/lifespan.py`, `app/bootstrap/food_search.py`,
`tests/test_canonical_application_lifespan.py`,
`tests/test_food_search_foundation.py`
Reason: Canonical startup order, explicit failure policy, process-wide
food-search ownership, transactional publication/rollback, reverse cleanup,
sequential resource freshness, overlap rejection, cancellation, and
application-body failure are implemented and deterministically tested, with
post-open gaps closed by `1e2d4918c5b6f6cf67d11865d218bf0253728f16`.

Disposition: FIXED
Commit: `6f629181cc1fca5a10d8e98e02811348a594ca03`
Evidence: `legacy_app.py`, `app/main.py`, `app/__init__.py`,
`tests/test_app_public_surface.py`
Reason: `legacy_app.py` re-exports the canonical lifespan while the existing
FastAPI instance and package/main identity remain unchanged; additive bootstrap
no longer creates food-search resources.

Disposition: FIXED
Commit: `6f629181cc1fca5a10d8e98e02811348a594ca03`
Evidence: `scripts/ci/check_legacy_growth_guard.py`,
`tests/test_legacy_growth_guard.py`
Reason: Legacy lifecycle definitions, event decorators, lifespan-context
assignment/wrapping, and canonical legacy/sys.modules/alias dependency lookup
are rejected without forbidding the temporary `FastAPI(..., lifespan=lifespan)`
compatibility construction.

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-background-scheduler-multi-worker-ownership`
Reason: In-process scheduler startup remains per ASGI worker by design; a
dedicated worker, distributed lease, leader election, or external scheduler is
required before multi-worker deployment is enabled.

## Pre-Open Role Evidence

- `agent-coordinator`: locked lifespan-only scope and explicitly deferred
  compatibility-wrapper deletion to the dependency-cutover PR.
- `architecture-specialist`: required one lifecycle authority, per-start
  callable resolution, transactional resource ownership, and unchanged app
  identity.
- `backend-engineer`: implemented canonical hooks, food-search lease/CAS
  behavior, and the public DB-fallback adapter.
- `security-auditor`: reviewed fail-closed ordering, cancellation, cleanup,
  overlap, diagnostics, and non-expansion of secrets/auth surfaces.
- `qa-engineer-agent`: required exact ordering/failure tests and real
  `TestClient` lifespan integration.
- `bug-hunter`: reviewed partial acquisition, sequential/overlapping starts,
  stale state, timeout drain, and exception-masking edges.

## Post-Open Role Evidence

Disposition: FIXED
Commit: `1e2d4918c5b6f6cf67d11865d218bf0253728f16`
Evidence: Mandatory `qa-engineer-agent -> bug-hunter -> security-auditor` review on published head `1bf8f19b770339575bca94ff980c9147f9021d2e`, followed by the focused 295-test lifecycle/food-search/guard bundle, legacy guard, and scoped MyPy.
Reason: All three roles confirmed the missing cancellation/start-failure evidence and lifecycle guard bypasses; QA and security independently reproduced the food-search reservation leak. All actionables were fixed before this mapping update. No additional secret, race, resource, fail-open, or app-identity defect was found.

## Codex Security Diff Scan Evidence

Disposition: FIXED
Commit: `e28fb34c3`
Evidence: Codex Security scan `fe7a0056-e0d1-4b90-b5ba-84adc40060dc`, finding
`FastAPI keyword expansion bypasses lifecycle ownership enforcement`, plus
`tests/test_legacy_growth_guard.py`.
Reason: `FastAPI(**kwargs)` now resolves bounded literal mappings, validates a
resolved `lifespan` against the canonical re-export, and fails closed when the
mapping cannot be proven static or has escaped/mutated.

Disposition: FIXED
Commit: `e28fb34c3`
Evidence: Codex Security scan `fe7a0056-e0d1-4b90-b5ba-84adc40060dc`, finding
`Qualified dynamic imports bypass lifecycle facade lookup enforcement`, plus
`tests/test_legacy_growth_guard.py`.
Reason: Dynamic imports now reject both exact facade names and their dotted
descendants while legitimate static imports of canonical `app.*` modules remain
allowed.

The sealed scan report remains a local plugin artifact, as required for local
security artifacts. Its validated summary is mirrored here; it is not used as
an unpublished merge-readiness substitute.

Disposition: FIXED
Commit: `31bd2d457`
Evidence: Targeted Codex Security rescan
`98ca8e42-2586-4db9-812a-0301ed0a3289`, finding
`Rebinding the canonical lifespan import name bypasses ownership enforcement`,
plus `tests/test_legacy_growth_guard.py`.
Reason: Canonical lifespan aliases are now accepted only when their import name
has exactly one stable binding; explicit and static-mapping reassignment forms
fail closed.

Disposition: FIXED
Commit: `31bd2d457`
Evidence: Targeted Codex Security rescan
`98ca8e42-2586-4db9-812a-0301ed0a3289`, finding
`Stale first-assignment string resolution bypasses lifecycle and facade checks`,
plus `tests/test_legacy_growth_guard.py`.
Reason: Static string facts now require a single stable binding, and unresolved
dynamic import names fail closed. Reassigned FastAPI keys and facade module names
are rejected while a known-safe single-assignment import remains allowed.

## Premortem Evidence

- Result: PROCEED after all actual-diff findings were closed.
- Real `TestClient` integration proves the legacy-created application acquires
  and disposes the Meili client on normal and body-error exits.
- The three committed OpenAPI/client artifacts have zero diff.
- Direct router lifespan callable identity is intentionally not asserted because
  FastAPI composes router lifespan contexts; observable lifecycle and canonical
  re-export identity are the stable contracts.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-2dba53ad6a27.json`

- Mode: `oracle_only_governance_reviewer`; status: `accepted`;
  `failure_class: null`; `mutated_paths: []`; `shared_tree_untouched: true`.
- Contribution: `commit_decision`; canonical Experiment Runner co-author trailer
  is present in `6f629181cc1fca5a10d8e98e02811348a594ca03`.
- Rejected infra-only predecessor `exp-71c19a6e2e14` is not evidence or
  attribution; it lacked local `unshare` for network-disabled sandboxing.

## Validation Evidence

- Preflight, agent consistency, and legacy growth guard - PASS.
- Focused lifecycle, food-search, DB fallback, production invariant, public
  surface, and guard tests - PASS (578 tests after the binding-stability fixes).
- `make validate-changed` after commit - PASS.
- Scoped MyPy through `.venv/bin/python` - PASS.
- `make openapi-check` and explicit three-artifact check - zero diff.
- `pre-commit run --all-files` - PASS.
- Codex Security diff scan - completed with 8/8 bounded surfaces; two Medium/P2
  findings were fixed in `e28fb34c3` before this evidence update.
- Targeted Codex Security rescan - completed with 8/8 bounded surfaces; two
  Medium/P2 binding-stability findings were fixed in `31bd2d457` before this
  evidence update.
- Pre-push hooks - PASS, including MyPy, pip-audit, backend tests, full-repo
  Bandit, and Docker build.
- Full local `make verify` was not run under repository machine-budget policy.

## Deferred / Follow-ups

- Canonical compatibility dependency cutover (`app/* -> legacy_app`).
- FastAPI metadata/OpenAPI and app-factory ownership inversion.
- Compatibility inventory and `legacy_app.py` deletion.
- Multi-worker-safe scheduler ownership tracked by the P1 backlog anchor above.
