# PR #1866 - Fixed in Commit Mapping

**Title:** `chore(frontend): remediate Vitest 4 dependency bump`
**Branch:** `codex/frontend-vitest-4-dependency-remediation`
**Scope:** Supersede PR #1864 with a governed frontend Vitest 4.1.8 dependency
remediation. The PR updates only frontend test tooling, Vitest config, and
test compatibility surfaces; it does not alter backend, OpenAPI, product API,
Python dependency, private-index installer, or CI workflow surfaces.
**Primary commit:** `452629b03`

## Discussion Thread Pass

- [ ] Discussion-thread pass pending post-open bot/human comments.
- [x] Fixed in commit mapping created for PR #1866.
- [ ] Post-open bot/human review disposition pending.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1866 -> 452629b03
Disposition: FIXED
Commit: 452629b03
Evidence: `frontend/package.json` and `frontend/package-lock.json` update the
direct Vitest family to exact `4.1.8`; `frontend/src/api/__tests__/wsClient.test.ts`
and `frontend/src/features/plan/__tests__/WeeklyPlanViewer.test.tsx` use
constructor-compatible mocks; `frontend/src/lib/__tests__/useTelemetry.test.tsx`
resets mocked telemetry enablement; `frontend/vitest.config.ts` recalibrates
only Vitest 4 V8 functions/branches thresholds; `docs/review/PR_FRONTEND_VITEST_4_PREMORTEM.md`
records pre-open risk closure.

## Implementation Evidence

Disposition: FIXED
Commit: `452629b03`
Evidence:

- `frontend/package.json` pins `vitest`, `@vitest/coverage-v8`, and
  `@vitest/expect` to exact `4.1.8`.
- `frontend/package-lock.json` records the corresponding Vitest 4.1.8 lockfile
  graph.
- `frontend/src/api/__tests__/wsClient.test.ts` replaces arrow WebSocket
  constructor mocks with function-compatible mocks.
- `frontend/src/features/plan/__tests__/WeeklyPlanViewer.test.tsx` replaces
  arrow `Intl.DateTimeFormat` mocks with function-compatible mocks.
- `frontend/src/lib/__tests__/useTelemetry.test.tsx` resets
  `isTelemetryEnabled` to `true` in `beforeEach` while preserving disabled
  telemetry assertions.
- `frontend/vitest.config.ts` keeps `lines` and `statements` thresholds at
  `52` and recalibrates only Vitest 4 V8 `functions` to `68` and `branches` to
  `63`, below observed Vitest 4 coverage of `68.84` functions and `63.13`
  branches.

## Dependency Scope / Private-Index Notes

- No Python dependency lockfiles or requirement files changed.
- No `.github/actions/python-setup`, `scripts/ci/install_locked_python_requirements.py`,
  emergency wheel manifest, CI workflow, Docker, or env example files changed.
- Python setup validation used the explicit private index:
  `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`.
- No `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` fallback or public-PyPI bypass was
  added.

## Role-Agent / Premortem Pass

Initial pre-open role order completed before implementation from packet
`artifacts/orchestration/task_packets/7cfaf2c8ef6e.json`:

- `agent-coordinator` - completed; scoped the lane to frontend npm dependency
  governance and PR #1864 evidence-only context.
- `architecture-specialist` - completed; approved narrow frontend-only
  dependency/test remediation.
- `frontend-engineer` - completed; applied the focused dependency/test changes.
- `qa-engineer-agent` - completed; confirmed assertions were preserved and
  Vitest family lockstep held.
- `security-auditor` - completed; classified npm audit findings as pre-existing
  dev/tooling transitives and confirmed Python private-index boundary was
  preserved.
- `creative-designer` - completed; confirmed no design/UI/token/copy impact.

Supplemental pre-open role order completed after adding `frontend/vitest.config.ts`
from packet `artifacts/orchestration/task_packets/2a8cf3f4dc4e.json`:

- `agent-coordinator` - completed; accepted `frontend/vitest.config.ts` as
  in-scope for Vitest 4 coverage recalibration.
- `architecture-specialist` - completed; accepted threshold recalibration as a
  narrow Vitest 4 metric-accounting change, not a runtime architecture change.
- `frontend-engineer` - completed; confirmed no production frontend code
  changed and direct Vitest-family pins remain exact.
- `qa-engineer-agent` - completed; confirmed tests are not hidden and thresholds
  remain enforced below observed Vitest 4 coverage.
- `security-auditor` - completed; confirmed coverage recalibration does not
  disable coverage or affect production security/private-index posture.
- `creative-designer` - completed; confirmed no design impact.

Premortem:

- Artifact: `docs/review/PR_FRONTEND_VITEST_4_PREMORTEM.md`
- Decision: proceed with changes.
- Findings were closed as FIXED or NOT-A-BUG for this lane before PR open.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-d13452c42344.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-d13452c42344.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted.
- Oracle commands: 5 configured, 5 executed, all passed.
- `source_diff_applied=true`
- `source_diff_paths`:
  - `docs/review/PR_FRONTEND_VITEST_4_PREMORTEM.md`
  - `frontend/package-lock.json`
  - `frontend/package.json`
  - `frontend/src/api/__tests__/wsClient.test.ts`
  - `frontend/src/features/plan/__tests__/WeeklyPlanViewer.test.tsx`
  - `frontend/src/lib/__tests__/useTelemetry.test.tsx`
  - `frontend/vitest.config.ts`
- `mutated_paths=[]`
- `coauthor_required=true`
- Commit trailer used on `452629b03`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Validation

- `git fetch --prune origin` - PASS.
- `git worktree add -b codex/frontend-vitest-4-dependency-remediation worktrees/frontend-vitest-4-dependency-remediation origin/main` - PASS.
- `python3 scripts/orchestration/check_preflight.py --mode analyze --path frontend/package.json --path frontend/package-lock.json --path frontend/src/api/__tests__/wsClient.test.ts --path frontend/src/lib/__tests__/useTelemetry.test.tsx --path frontend/src/features/plan/__tests__/WeeklyPlanViewer.test.tsx` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/orchestration/task_bootstrap.py --goal "Remediate PR #1864 Vitest 4 frontend dependency bump without Python private-index drift" --task-class frontend-dependency-governance --pr-phase pre_open ...` - PASS; packet `7cfaf2c8ef6e`.
- `python3 scripts/orchestration/task_bootstrap.py --goal "Remediate PR #1864 Vitest 4 frontend dependency bump and Vitest 4 coverage metric recalibration without Python private-index drift" --task-class frontend-dependency-governance --pr-phase pre_open ...` - PASS; packet `2a8cf3f4dc4e`.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json` - PASS.
- `cd frontend && npm ci` - PASS, with existing 2 moderate dev/tooling audit findings.
- `npm test -- --run src/api/__tests__/wsClient.test.ts src/lib/__tests__/useTelemetry.test.tsx src/features/plan/__tests__/WeeklyPlanViewer.test.tsx` - PASS; Vitest 4.1.8; 3 files, 26 tests.
- `npm run lint --if-present -- --max-warnings=0` - PASS/no-op; no frontend lint script exists.
- `npm run test -- --coverage` - PASS; Vitest 4.1.8; 91 files; 765 passed; 1 pre-existing skipped test; coverage summary: statements 66.68, branches 63.13, functions 68.84, lines 67.29.
- `npm run build` - PASS with non-blocking Vite chunk/dynamic-import warnings.
- `npm run smoke:css` - PASS.
- `npm ls vitest @vitest/coverage-v8 @vitest/expect --depth=0` - PASS; all direct packages at 4.1.8.
- `npm audit --omit=dev` - PASS; 0 vulnerabilities.
- `pre-commit run --all-files` - PASS.
- Commit hooks on `452629b03` - PASS.
- Pre-push hooks - PASS, including pip-audit, backend pre-push tests, and full-repo Bandit; Docker build hook skipped because no Docker-surface files changed.

## Current CI Status

Pending current-head CI for PR #1866. Merge readiness is not claimed.

## Codex Security Diff Scan

Pending post-open Codex Security diff scan / finding discovery.

## PulsePlate PR Review

Pending post-open `pulseplate-pr-review`.

## Merge Readiness

Not claimed. Full local `make verify` has not been run, current-head CI is
pending, post-open role passes are pending, and review-thread/bot dispositions
must be checked after the latest PR activity.
