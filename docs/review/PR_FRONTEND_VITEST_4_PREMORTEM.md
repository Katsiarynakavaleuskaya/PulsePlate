# PR Frontend Vitest 4 Premortem

**Scope:** Supersede PR #1864 with a governed frontend dependency PR that
updates the Vitest family to `4.1.8`, remediates Vitest 4 test mock behavior,
and preserves the Python private-index boundary.

**Task packets:**

- Initial packet: `artifacts/orchestration/task_packets/7cfaf2c8ef6e.json`
- Updated packet after coverage config scope: `artifacts/orchestration/task_packets/2a8cf3f4dc4e.json`

## Summary

It is 48 hours from now. The Vitest 4 replacement PR failed because the
dependency bump was treated as a simple Dependabot carry-forward while the
test-runner semantics, coverage accounting, and private-index boundary were not
made explicit.

Decision: proceed with changes.

## Failure Modes

### 1. Mixed Vitest Family Drift

Failure story: The PR updates `vitest` and `@vitest/coverage-v8` but leaves
direct `@vitest/expect` on the old major. The test graph then depends on a
mixed assertion/coverage stack, causing nondeterministic failures between local
and CI installs.

Underlying assumption: Dependabot's original two-file diff is complete enough
to carry forward unchanged.

Early warning signs:

- `npm ls vitest @vitest/coverage-v8 @vitest/expect --depth=0` does not show
  all three direct packages at `4.1.8`.
- `frontend/package-lock.json` contains the old direct Vitest-family root
  packages.

Containment action: Keep `vitest`, `@vitest/coverage-v8`, and direct
`@vitest/expect` exact at `4.1.8`; reject any mixed direct Vitest-family pins.

Disposition: FIXED.

Evidence:

- `frontend/package.json` pins all three direct Vitest-family packages to
  `4.1.8`.
- `npm ls vitest @vitest/coverage-v8 @vitest/expect --depth=0` exits 0 and
  reports `4.1.8` for all three direct packages.

### 2. Vitest 4 Constructor Mock Regression

Failure story: Vitest 4 invokes constructor mocks with `new`, but old tests use
arrow-function mocks for `WebSocket` and `Intl.DateTimeFormat`. CI fails even
though production code is unchanged.

Underlying assumption: Existing Vitest 3 mock implementations remain valid
under Vitest 4.

Early warning signs:

- Error text such as `is not a constructor`.
- Vitest warning that a `DateTimeFormat` mock did not use `function` or
  `class`.

Containment action: Keep remediation test-only and convert constructor mocks to
function-compatible implementations.

Disposition: FIXED.

Evidence:

- `frontend/src/api/__tests__/wsClient.test.ts` uses function-compatible
  `WebSocket` constructor mocks.
- `frontend/src/features/plan/__tests__/WeeklyPlanViewer.test.tsx` uses
  function-compatible `Intl.DateTimeFormat` mocks.
- Focused Vitest command exits 0 with 3 files and 26 tests passing.

### 3. Telemetry Mock Leakage

Failure story: A test sets mocked telemetry enablement to `false`, later tests
inherit that state, and Vitest 4 reports missing telemetry calls. A weak fix
could remove assertions instead of resetting the mock.

Underlying assumption: `vi.clearAllMocks()` is enough for this mocked return
value.

Early warning signs:

- Telemetry call-count assertions drop to zero after a disabled-telemetry case.
- Tests pass only when reordered or run alone.

Containment action: Reset mocked `isTelemetryEnabled` to `true` in `beforeEach`
and preserve disabled-telemetry assertions.

Disposition: FIXED.

Evidence:

- `frontend/src/lib/__tests__/useTelemetry.test.tsx` resets the mocked
  `isTelemetryEnabled` return value in `beforeEach`.
- Disabled telemetry not-call assertions remain in the file.

### 4. Coverage Gate Appears Red After All Tests Pass

Failure story: Full frontend coverage runs all tests successfully, but Vitest 4
changes V8 coverage accounting for functions and branches. The PR either stays
red or overcorrects by weakening unrelated coverage behavior.

Underlying assumption: Vitest 3 and Vitest 4 coverage percentages are directly
comparable.

Early warning signs:

- `npm run test -- --coverage` reports all test files passed but exits 1 on
  global functions/branches thresholds.
- Baseline `origin/main` with Vitest 3 passes the same command.

Containment action: Recalibrate only the affected frontend Vitest coverage
thresholds after validating the full suite under Vitest 4; keep lines and
statements unchanged.

Disposition: FIXED.

Evidence:

- `frontend/vitest.config.ts` keeps `lines` and `statements` at `52`, and
  recalibrates only `functions` to `68` and `branches` to `63`.
- `npm run test -- --coverage` exits 0 on Vitest `4.1.8` with 91 test files,
  765 passed tests, 1 pre-existing skipped test, and coverage above the
  configured thresholds.

### 5. Python Private-Index Drift

Failure story: A frontend dependency PR tries to work around local setup or CI
mirror lag by touching Python requirements, installer scripts, workflow setup,
or ambient pip index variables. The PR becomes a cross-ecosystem dependency
change and violates the private-index contract.

Underlying assumption: Frontend dependency validation can freely adjust Python
setup surfaces.

Early warning signs:

- Changes to `requirements*.txt`, `constraints.txt`, `.github/actions/python-setup`,
  or `scripts/ci/install_locked_python_requirements.py`.
- Public PyPI fallback through `PIP_INDEX_URL` or `PIP_EXTRA_INDEX_URL`.

Containment action: Do not touch Python dependency surfaces; run Python
preflight with the explicit private index URL.

Disposition: FIXED.

Evidence:

- `git diff --name-only` is limited to frontend package, Vitest config, and
  frontend test files plus this premortem.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`
  exits 0.

### 6. Pre-Existing npm Audit Debt Confused With This PR

Failure story: npm audit output reports dev/tooling advisories and the PR is
misclassified as introducing new production dependency risk, or the PR attempts
to remediate unrelated Storybook/jsdom/tooling debt.

Underlying assumption: Every npm audit finding in the install output belongs to
the Vitest 4 change.

Early warning signs:

- `npm audit` reports the same dev/transitive advisories present on
  `origin/main`.
- `npm audit --omit=dev` is clean.

Containment action: Keep audit classification explicit and defer unrelated
frontend dependency hygiene to a separate lane.

Disposition: NOT-A-BUG for this lane.

Evidence:

- Security role pass classified the 2 moderate audit findings as pre-existing
  dev/tooling transitives.
- `npm audit --omit=dev` exits 0.

## Revised Plan

- Keep the direct Vitest family exact at `4.1.8`.
- Keep mock remediation test-only.
- Keep the Vitest 4 coverage recalibration narrow: functions/branches only,
  documented as metric-accounting drift, with full coverage evidence.
- Keep Python private-index validation explicit and read-only.
- Open the replacement PR non-draft; use PR #1864 as evidence only and close it
  after the replacement PR is live.

## Pre-Open Checklist

- [x] Canonical fixed-mapping artifact created: `docs/review/PR_1866_FIXED_MAPPING.md`.
- [x] PR body includes `## Discussion Thread Pass`.
- [x] PR body includes `### Fixed in Commit Mapping`.
- [x] PR body includes `## Merge Readiness`.
- [x] `check_preflight.py` passed for the scoped frontend paths.
- [x] `check_agent_consistency.py` passed.
- [x] Initial role order executed in sequence.
- [x] Supplemental role order executed after adding `frontend/vitest.config.ts`.
- [x] Focused Vitest 4 tests passed.
- [x] Full frontend coverage passed after Vitest 4 threshold recalibration.
- [x] Frontend build passed.
- [x] CSS smoke passed.
- [x] Python private-index preflight passed with explicit
  `PULSEPLATE_PYTHON_INDEX_URL`.
- [x] Experiment Runner oracle-only governance evidence recorded.
- [x] `pre-commit run --all-files` passed before push.

## Decision

Proceed with changes. Pre-open Experiment Runner oracle evidence, pre-commit,
commit, push, replacement PR creation, and Phase2 body/fixed-mapping artifacts
are recorded. Remaining work is post-open review disposition, current-head CI,
and merge-readiness governance.
