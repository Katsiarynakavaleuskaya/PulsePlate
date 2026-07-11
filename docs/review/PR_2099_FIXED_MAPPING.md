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
- `f16b7663b` - preserve optional scheduler imports, map Meili shutdown races to
  the existing fallback path, close remaining lifecycle-guard bypasses, and
  correct durable review documentation.
- `2b0f393d1` - require every guarded `FastAPI(...)` construction to retain the
  canonical lifespan and reject parameter-shadowed static security facts.
- `79e1a19f7` - cover transactional rollback/cancellation paths and route the
  canonical lifecycle bundle into Tier 1 CI diff coverage.
- `4751548dc` - narrow namespace mutation detection, close remaining import and
  lifecycle-event bypasses, and replace the forbidden global import mock.
- `6ff7e62e8` - reject direct and namespace-based deletion of lifecycle state.
- `6df7d472e` - remove redundant nested `TestClient` lifespans from the RAG
  contract suite while retaining its per-test client identity.
- `056a8aaf6` - resolve `vars()`/`__dict__` lifecycle references and inspect
  unpacked namespace updates, closing the late Cubic guard bypasses.
- `c800c13ee` - reject reflective lifecycle event lookups and freeze explicit
  module-namespace dynamic-import regressions.
- `bf4ee059e` - harden namespace mapping reads and in-place unions, including
  static `.get`, `.__getitem__`, `.__ior__`, and direct `__dict__ |=` forms.
- `1609d8ce9` - treat reflected `__dict__` access as an object namespace for
  mutation and lifecycle-event enforcement.
- `3663352d6` - inspect assigned namespace replacement values and fail closed
  when a composed mapping can install lifecycle state.
- `7f9d2cead` - remove a stale coverage test that required the retired private
  lifecycle resolver through the legacy app facade.
- `e2e040fa0` - generalize protected namespace mutation checks to lifecycle
  event lists and enforce the same event-registration guard in food search.
- `fbb5d3060` - recognize unbound built-in `dict` namespace mutators and their
  imported aliases while preserving safe unrelated mappings.

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
- [x] `pulseplate-pr-review` completed on published head `1067988aa`.
- [ ] Current-head CI completed.
- [ ] Strict merge-readiness checks completed after the final review cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562131781
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562249863
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562249867
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562256410
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562096556
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562118864
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562131786
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562249878
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562249883
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562256404
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562256412
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562399636
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562399643
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562425016
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562425022
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562425024
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563306164
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563315060
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4675099095
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4675277921
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4676789851
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563410379
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415182
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415186
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415190
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415192
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415196
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563496282
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4676962649
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563549257
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563549260
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563549609
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4677050714
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563625646
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563625647
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563633855
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563668971
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563731379
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563731382
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4677331316
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563818055
Disposition: FIXED
Commit: see mapping entries below
Evidence: `1e2d4918c`, `e28fb34c3`, `31bd2d457`, `ef4a03da0`, `f16b7663b`, `056a8aaf6`, `c800c13ee`, `bf4ee059e`, `1609d8ce9`, `3663352d6`, `e2e040fa0`, and `fbb5d3060` contain the post-comment production, guard, regression-test, architecture, and governance fixes; the focused suite, legacy guard, MyPy, OpenAPI zero-diff, validate-changed, pre-commit, and pre-push gates pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562131781 -> 1e2d4918c5b6f6cf67d11865d218bf0253728f16
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562249863 -> e28fb34c3a0d6c044194e9cc90e81504cbb2adbf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562249867 -> 31bd2d457f66aa4df7ed01b5cf8b179b2d27c3ea
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562256410 -> ef4a03da04a414498c159b4e792a7b9579e20531
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562096556 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562118864 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562131786 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562249878 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562249883 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562256404 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562256412 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562399636 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562399643 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562425016 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562425022 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3562425024 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563306164 -> 2b0f393d10d9eb4ccb0e3c598138d24d3c8d2f9f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563315060 -> 2b0f393d10d9eb4ccb0e3c598138d24d3c8d2f9f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4675099095 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4675277921 -> f16b7663bfd606d72d4e45f518b20e1e0c676365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4676789851 -> 4751548dcad7b60542bb04834170a7b6f8482883
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563410379 -> 4751548dcad7b60542bb04834170a7b6f8482883
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415182 -> 4751548dcad7b60542bb04834170a7b6f8482883
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415186 -> 4751548dcad7b60542bb04834170a7b6f8482883
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415190 -> 4751548dcad7b60542bb04834170a7b6f8482883
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415192 -> 4751548dcad7b60542bb04834170a7b6f8482883
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563415196 -> 4751548dcad7b60542bb04834170a7b6f8482883
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563496282 -> 6ff7e62e84ade37305bab9cc9a45302f979fb0ea
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4676962649 -> 056a8aaf622472644672f03ff5741b6c9d437bd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563549257 -> 056a8aaf622472644672f03ff5741b6c9d437bd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563549260 -> 056a8aaf622472644672f03ff5741b6c9d437bd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563549609 -> c800c13ee5e546e5bd47b0b4b03ff27db6254817
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4677050714 -> bf4ee059ee262fe4e2903989e22c8a51cf4b1499
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563625646 -> bf4ee059ee262fe4e2903989e22c8a51cf4b1499
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563625647 -> bf4ee059ee262fe4e2903989e22c8a51cf4b1499
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563633855 -> 1609d8ce921f1c08d9bbde1eabfb86226c2545e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563668971 -> 3663352d64c71f707160e74f8bd8a2c39a2952e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563731379 -> e2e040fa0972176fc39786db09e8d18811e346ff
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563731382 -> e2e040fa0972176fc39786db09e8d18811e346ff
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#pullrequestreview-4677331316 -> fbb5d3060232e9f587d3be1a3ee6a2341ee2dae9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563818055 -> fbb5d3060232e9f587d3be1a3ee6a2341ee2dae9

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2099#discussion_r3563609195
Disposition: NOT-A-BUG
Evidence: `scripts/ci/check_legacy_growth_guard.py` normalizes static module namespace references; explicit builtins/importlib cases in `tests/test_legacy_growth_guard.py` return the canonical dynamic-facade error, and the complete guard suite passes.
Reason: The comment was generated against the parent head after `056a8aaf6` had generalized namespace-mediated resolution; `c800c13ee` adds explicit importlib regression evidence without weakening the guard.

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

## Current-Head CI Regression Evidence

Disposition: FIXED
Commit: `6df7d472ee4d8393283f7b5d267c128f5a24b00a`
Evidence: `tests/test_insight_rag_response_fields.py`; the four failing RAG
cases and the complete 17-test file pass locally, followed by the focused
lifecycle/food-search/guard bundle, `make validate-changed`, scoped MyPy,
OpenAPI zero-diff, `pre-commit run --all-files`, and pre-push tests.
Reason: CI exposed four tests that opened a second lifespan for the same
application while the fixture-owned lifespan was active. The production
food-search overlap rejection remains fail-closed; the tests now reuse the
already isolated fixture client instead of starting a redundant nested
application lifecycle.

Disposition: FIXED
Commit: `7f9d2cead90da9aa33633d58825ddb4dda9a5376`
Evidence: `tests/test_app_error_paths_97.py` and the canonical utility coverage in `tests/test_app_coverage_branches_extra.py`; both files, the lifecycle/guard bundle, `make validate-changed`, and `pre-commit run --all-files` pass.
Reason: Python 3.12 CI selected a stale duplicate test that required the removed private `app._resolve_app_callable` facade export. The canonical utility remains directly tested; restoring the legacy private export would contradict the lifecycle dependency-cutover contract.

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

## PulsePlate PR Review Evidence

Disposition: NOT-A-BUG
Evidence: `pulseplate-pr-review` dry-run on head `1067988aa`, explicit operator
scope/privileged/emergency approvals in the PR body, packet-declared ordered
role reviews, 578 focused lifecycle/food-search/guard tests, `make
validate-changed`, two completed Codex Security scans, and zero OpenAPI/client
artifact drift.
Reason: The deterministic reviewer emitted one note solely because the cohesive
lifecycle-ownership migration exceeds its generic 800-line review-risk
threshold. The PR cannot be split without temporarily retaining contradictory
lifecycle authorities or false legacy tests; the expanded review and validation
evidence addresses the note without changing runtime scope.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-2dba53ad6a27.json`
(Local and gitignored; not durable merge authority.)

Content identifier (SHA-256):
`93b1d313fde78e123a85c8c50026fc29f3f0f1e0946e650a00db68c88741c317`

The committed summary below is the durable review record. The local artifact
cannot be independently recovered from Git and is not promotion,
thread-disposition, or merge-readiness authority.

- Mode: `oracle_only_governance_reviewer`; status: `accepted`;
  `failure_class: null`; `mutated_paths: []`; `shared_tree_untouched: true`.
- Recorded oracle results: 289 lifecycle/food-search/guard/public-surface tests,
  the legacy compatibility guard, and 106 DB-fallback/health/production
  invariant tests all exited `0`; `promotion_ready: false`.
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
