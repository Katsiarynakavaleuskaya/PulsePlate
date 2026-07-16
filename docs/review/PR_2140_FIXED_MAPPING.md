# PR #2140 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140

Branch: `codex/canonicalize-legacy-weekly-menu-builder-access`

## Summary

Canonicalize the hidden legacy weekly-plan route's builder access without
changing its route, API-key dependency, success payload, canonical VIP/FitChef
execution, OpenAPI visibility, or shared FastAPI instance identity. Replace
mutable `sys.modules` / facade resolution with one lazy typed core access path,
preserve only the two reviewed static downstream 422 envelopes, sanitize every
other unexpected failure, and remove dead legacy resolver shims.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/c15727fd5dc5.json`
- Packet note: exact-scope pre-open packet; local-only and gitignored.
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor`.
- Final production-material post-open order executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Pre-open packet role order completed
- [x] Actual-diff premortem completed
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed
- [x] One Codex Security production-material diff scan completed with 0 findings
- [x] One `pulseplate-pr-review` pass completed
- [x] Both resolved CodeRabbit threads have real post-comment commit evidence
- [x] All current bot comments/reviews have dispositions below
- [ ] Canonical current-head CI completed
- [ ] Strict authenticated merge readiness and mandatory wait-window completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 97a7ebd41a0effa86212d3e1b1a7b18783b3cde9
Evidence: `app/routers/legacy_premium_weekly_plan.py` uses `fastapi.status`, one typed fixed 500 boundary, and exact fail-closed exception handling; `tests/test_legacy_weekly_plan_alias_api.py` uses precise response and `NoReturn` annotations. The focused 95-test review-fix suite, targeted MyPy, legacy guard, review-pattern oracle, all-files pre-commit, and branch-selected validation passed.
Reason: Both inline CodeRabbit findings were valid and were fixed in the real post-comment runtime/test commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140#discussion_r3590852742 -> 97a7ebd41a0effa86212d3e1b1a7b18783b3cde9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140#discussion_r3590852745 -> 97a7ebd41a0effa86212d3e1b1a7b18783b3cde9

Disposition: FIXED
Commit: 97a7ebd41a0effa86212d3e1b1a7b18783b3cde9
Evidence: `tests/test_final_push_97_percent.py` now has complete annotations for the changed test and uses dict-shaped `daily_menus`, preventing MagicMock false positives; the same focused and branch-selected suites passed.
Reason: The outside-diff typing finding and dict-shape false-green finding in the CodeRabbit summary were bounded, valid, and fixed. The remaining marker nitpick is intentionally not adopted: the exact status/detail/headerless allowlist is the approved narrow compatibility contract, while a shared exception marker would widen this PR into canonical VIP exception ownership.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140#pullrequestreview-4708252380 -> 97a7ebd41a0effa86212d3e1b1a7b18783b3cde9

Disposition: NOT-A-BUG
Evidence: Every changed production callable in `app/routers/legacy_premium_weekly_plan.py` and `app/services/legacy_premium_weekly_plan.py` has a docstring; local Black, Ruff, MyPy, Bandit, and repository lint hooks pass.
Reason: CodeRabbit's remaining docstring-percentage warning is a repository-wide advisory, not a missing docstring in this diff or a canonical PulsePlate merge gate.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140#issuecomment-4985366104

Disposition: FIXED
Commit: 90e9500bde4511f475e096aeef74881bc2afb6c8
Evidence: Both canonical `route_contract_safety` suite blocks now select the weekly-menu access, route, and registration tests; commit `fce42504ecd50c8ba76a9791bd8b449a987ac27e` locks test-pr/test-feature parity. A fresh local coverage run over those selected suites reports 46/46 changed production lines covered (100%).
Reason: Codecov correctly exposed a CI selection gap. The existing deterministic tests covered the production diff at 100%, but the Tier 1 coverage job did not run them until this post-comment workflow fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140#issuecomment-4985554506 -> 90e9500bde4511f475e096aeef74881bc2afb6c8

Disposition: NOT-A-BUG
Evidence: Cursor explicitly reported that Bugbot was not enabled and produced no code finding.
Reason: A source-availability notice contains no actionable defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140#issuecomment-4985361724

Disposition: NOT-A-BUG
Evidence: Sourcery's review body reports weekly quota exhaustion and contains no code finding; the local role chain, deterministic gates, and sealed Codex Security scan remain separate evidence.
Reason: A source-capacity notice is source-degraded review evidence, not an actionable code defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140#pullrequestreview-4708200755

Disposition: NOT-A-BUG
Evidence: The Codex GitHub connector posted a usage-limit notice and no code finding; the required local Codex Security diff scan completed separately with complete 3/3 coverage and zero findings.
Reason: The usage-limit notice does not claim that the code was reviewed and creates no actionable item.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2140#issuecomment-4985631725

## Current-PR CI Findings

Disposition: FIXED
Commit: f74bd1143b70e720c92bc3a2eaac735cd0d3e763
Evidence: CI job `87481244583` failed collection at `tests/test_legacy_weekly_plan_alias_api.py:14` because the ci-lite environment intentionally omits `httpx2`. The response type is now imported only under `TYPE_CHECKING`; the exact branch-selected hook passes 284 tests, the focused pair passes 50 tests, and targeted MyPy passes.
Reason: This was a real PR-scoped CI portability defect introduced by the review typing fix, not an inherited or optional failure.

Disposition: FIXED
Commit: 90e9500bde4511f475e096aeef74881bc2afb6c8
Evidence: `.github/workflows/ci.yml` adds the three existing weekly-menu contract suites to both bounded `route_contract_safety` lists. `tests/test_ci_workflow_pr_size_governance_contract.py` locks the membership and equality of the test-pr/test-feature lists; focused workflow and weekly suites, `make validate-changed`, all-files pre-commit, and pre-push hooks pass.
Reason: The Codecov failure was caused by omitted tests in the canonical coverage runtime, not missing deterministic behavior coverage. The fix changes test selection only and leaves the 97% threshold untouched.

## Premortem and Role Review

### Actual-diff Premortem

Disposition: FIXED
Commit: 8d9af8c0ba53152ba92047bc51ae1a8b30f40900
Evidence: The implementation separates getter failures from executor `ValueError`, maps only exact canonical-module absence to unavailable, rejects non-callable exports, patches only the consumer binding, deletes zero-call-site private shims, and proves auth/flag/getter/executor short-circuit order.
Reason: The bounded risks identified before opening the PR were closed in the material implementation rather than deferred or mapped to synthetic review revisions.

### QA Engineer Agent

Disposition: NOT-A-BUG
Evidence: QA reviewed the final production-material diff and passed 86 focused route/access/registration/public-surface tests, 9 security/auth contract tests, and 4 review-pattern oracles with no actionable finding.
Reason: Exact status/detail, auth-before-getter, consumer binding, callable identity, and OpenAPI/route contracts matched the approved scope.

### Bug Hunter

Disposition: NOT-A-BUG
Evidence: Bug-hunter passed 73 focused tests, 9 security/auth tests, 4 review-pattern oracles, and targeted MyPy; no false-green route, import-order, response-shape, or exception-boundary defect survived.
Reason: No reproducible current-PR defect remained on the production-material head.

### Security Auditor

Disposition: NOT-A-BUG
Evidence: Security-auditor confirmed the API-key dependency runs before handler probing, only exact canonical-module absence maps to 503, mutable facade/sys.modules authority is removed, approved 422 pass-through is exact and headerless, and all unknown failures return a generic 500 with fixed server logging.
Reason: No actionable security regression remained after the post-open role pass.

### Codex Security

Disposition: NOT-A-BUG
Evidence: Sealed scan `0d6914fe-b8dc-4ce2-9c9c-83576b83db25` covered exact production-material range `00968dc99d40764961b85d109e46623eb9d5c4b5...97a7ebd41a0effa86212d3e1b1a7b18783b3cde9` with snapshot digest `codex-security-snapshot/v1:sha256:1d74df0bc5da366ec7aad16a4841552de3d91d1cb5319d4e849096130ccb54eb`. All 3 production rows have completion receipts, coverage is complete, and findings are empty. Sealed report SHA-256: `90cdfc0d7e19a33b2d6ad2ae24977024e17c88336d846a0e7e26c6ca2102571b`.
Reason: No technically plausible candidate survived full-file diff discovery. Validation and attack-path phases were correctly not applicable with zero reportable candidates.

### Scan Reuse Boundary

Disposition: NOT-A-BUG
Evidence: The only commits after scanned production head `97a7ebd41` are test-only import portability `f74bd1143`, CI test selection `90e9500bd`, and its contract assertion `fce42504e`; `git diff 97a7ebd41..fce42504e` contains only `.github/workflows/ci.yml` and two test files.
Reason: The operator-approved review contract permits one scan per stable material runtime/security diff and targeted verification for later test/docs/governance fixes. Repeating the scan would create synthetic review/mapping churn without adding production security coverage.

### PulsePlate PR Review

Disposition: NOT-A-BUG
Evidence: The one PR #2140 dry-run reviewed all changed files and produced only three advisory notes: the then-missing mapping artifact, its resulting source-degraded status, and large-diff review cost. This artifact now exists; the PR body contains an atomic split justification; production scope remains three files while most line volume is deterministic replacement/deletion of resolver-precedence test debt.
Reason: The review found no correctness, architecture, security, or wellness defect. Its mapping-state note is closed by this artifact, and its size note is review-planning evidence rather than a product defect.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/weekly-menu-access-666568316-apple-result.json`

The strict Apple Container oracle passed all 3 immutable commands, reported
`shared_tree_untouched=true` and `mutated_paths=[]`, and materially shaped
the commit decision. Commit `8d9af8c0b` carries the required
`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer.

## Validation Evidence

- PASS: orchestration preflight and agent consistency.
- PASS: focused weekly-menu access/route/registration/public-surface suites.
- PASS: security auth/tier and static authz contract suites.
- PASS: targeted MyPy for the production modules and changed response helper.
- PASS: inherited legacy-growth guard and its tests.
- PASS: `make openapi-check`; all three generated OpenAPI/TypeScript artifacts
  have zero diff.
- PASS: branch-selected backend pre-commit tests after the ci-lite import fix.
- PASS: fresh local diff-cover for the newly selected weekly-menu suites:
  46/46 changed production lines, 100%.
- PASS: focused CI workflow contract and test-pr/test-feature suite parity.
- PASS: `make validate-changed`, `pre-commit run --all-files`, pre-push
  MyPy/pip-audit/backend/Bandit hooks, and `git diff --check`.
- PASS: one sealed Codex Security material-diff scan with 3/3 receipts and zero
  findings.
- NOT RUN: local full `make verify`, per repository machine-budget policy.
- PENDING: canonical current-head CI after the test-selection and mapping commits.

## Security Review

- Missing/invalid API keys remain exact 403 and prevent handler/getter execution.
- VIP-disabled and exact canonical-module absence retain their distinct static
  503 envelopes.
- Broken imports, non-callable exports, getter failures, unknown downstream
  `HTTPException`, and response-shaping failures expose only the stable generic
  500 while retaining server-side traceback diagnostics.
- No payload, API key, profile, callable representation, or exception text is
  logged as an explicit message/field.
- Public compatibility exports remain available but are not production route
  authority.

## Risks / Rollback

Primary risks are auth/validation precedence drift, hiding a broken deployment
as feature unavailability, leaking downstream error details, restoring mutable
facade authority, and omitting the focused tests from CI coverage. Controls are
exact route tests, typed lazy-loader tests, AST ownership assertions,
registration/OpenAPI parity, current-head diff coverage, role review, and the
sealed production scan.

Rollback is a revert of the PR commits; there is no database, schema, route,
client, persisted-state, feature-flag, or deployment migration.

## Deferred / Follow-ups

- BMI visualization resolver is the next bounded legacy candidate recorded in
  `docs/roadmap/BACKLOG_LEDGER.md`.
- PRO nutrition, insight compatibility, and app-factory inversion remain
  separate later lanes.

## Merge Readiness

- PASS: implementation, review-fix, ci-lite import, and CI coverage-selection
  defects have deterministic local evidence.
- PASS: all two resolved GitHub review threads use real reachable post-comment
  commits; no synthetic or squash-preview SHA is mapped.
- PASS: one production-material security scan and one PR review pass are
  recorded without a synthetic rerun loop.
- PENDING: canonical current-head CI and diff coverage at least 97% after this
  mapping commit.
- PENDING: no actionable bot comments and zero unresolved review threads on the
  exact final head.
- PENDING: strict authenticated merge readiness and one quiet review cycle.
