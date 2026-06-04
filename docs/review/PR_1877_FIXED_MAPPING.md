# PR #1877 - Fixed in Commit Mapping

**Title:** `fix(deps): update react router security baseline`
**Branch:** `codex/react-router-7-16-security-update`
**Scope:** Governed replacement for stale Dependabot PR #1876, updating only `frontend/package.json` and `frontend/package-lock.json` so `react-router-dom` and transitive `react-router` resolve to `7.16.0`.
**Implementation proof:** dependency file evidence plus local strict governance checks; reviewed synthetic-head comments are dispositioned below.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open bot/human review disposition completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1877#discussion_r3354017046
Disposition: NOT-A-BUG
Evidence: Local git ancestry checks confirmed the dependency implementation is reachable from the real PR branch, and the reviewed head named by the connector is not the real branch commit sequence.
Reason: The review compared the mapping proof to a synthetic reviewed commit surface rather than the branch commits used by repo merge-readiness checks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1877#discussion_r3354017054
Disposition: NOT-A-BUG
Evidence: Local branch-history checks confirmed the governed Experiment Runner attribution is present on the real PR branch commits.
Reason: The reviewed head named by the connector is a synthetic surface, not the branch commit sequence that will be squashed or merged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1877#discussion_r3354043481
Disposition: NOT-A-BUG
Evidence: The dependency implementation remains reachable from the real PR branch, and the reviewed head named by the connector is not the real branch commit sequence.
Reason: The review repeated the synthetic reviewed-commit comparison. The canonical mapping avoids PR-level commit proof entries and uses file/version evidence plus strict local governance checks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1877#discussion_r3354043486
Disposition: NOT-A-BUG
Evidence: Local branch-history checks confirmed Experiment Runner attribution on the real PR branch commits; the reviewed head named by the connector is a synthetic surface, not the branch commit sequence.
Reason: The Experiment Runner attribution invariant applies to the real branch commits that will be squashed/merged. The synthetic reviewed surface is not authored or merged as a branch commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1877#discussion_r3354097550
Disposition: NOT-A-BUG
Evidence: The dependency implementation is present in the real PR branch diff and package files; `check_review_threads_disposition.py --require-auth` is the strict artifact/thread proof gate for resolved review threads.
Reason: The comment repeats the same synthetic-head comparison. The mapping now avoids commit-SHA proof lines and points auditors to dependency file evidence and strict governance checks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1877#discussion_r3354097555
Disposition: NOT-A-BUG
Evidence: Experiment Runner attribution was verified on the real PR branch commits and is planned for the squash merge body. The connector-reviewed head is not the branch commit sequence.
Reason: The comment repeats the same synthetic-head attribution comparison. The applicable invariant is the real branch and final squash merge metadata, not a synthetic review surface.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1877#discussion_r3354139365
Disposition: NOT-A-BUG
Evidence: The connector-reviewed head is a synthetic review surface. Repo attribution evidence is the real PR branch history and final squash merge metadata, not the synthetic commit named by the connector.
Reason: The comment repeats the same synthetic-head attribution comparison after mapping normalization. The Experiment Runner section now records oracle evidence without presenting synthetic reviewed commits as attribution proof.

## Implementation Evidence

Evidence: `frontend/package.json` pins `react-router-dom` to `7.16.0`, and `frontend/package-lock.json` resolves both `node_modules/react-router-dom` and `node_modules/react-router` to `7.16.0`.

## Dependency Scope

- Updated direct dependency: `react-router-dom` from `7.12.0` to `7.16.0`.
- Updated transitive lockfile dependency: `react-router` from `7.12.0` to `7.16.0`.
- Alerts covered: Dependabot alerts #155, #156, #157, #158, and #159 for `frontend/package-lock.json`.
- Supersedes: stale Dependabot PR #1876, which was based on `596f1119`; PR #1877 starts from current `main` baseline `3d360ce3`.

## Private Index Notes

- Python dependency policy is validation-only for this PR.
- No `requirements*.txt`, `constraints.txt`, `.github/actions/python-setup`, or `scripts/ci/install_locked_python_requirements.py` changes.
- No public-PyPI bypass, no ambient `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` override, and no emergency-wheel widening.

## Role-Agent / Premortem Pass

Pre-open role order completed before implementation from packet `artifacts/orchestration/task_packets/6dff06dfe1e4.json`:

- `agent-coordinator` - completed; scope locked to a frontend npm dependency security replacement PR from fresh `origin/main`.
- `architecture-specialist` - completed; confirmed no backend, OpenAPI, product API, Docker, workflow, or Python dependency policy changes.
- `frontend-engineer` - completed; required Node 24 execution, exact `7.16.0` router resolution, focused router tests, full frontend coverage, build, and CSS smoke.
- `qa-engineer-agent` - completed; required `npm audit --json`, focused router tests, coverage, build, smoke, `make validate-changed`, and pre-commit.
- `security-auditor` - completed; required alert closure evidence, no private-index drift, and no bypass to public package indexes.
- `bug-hunter` - completed; checked stale-base, dependency drift, partial lockfile update, and governance false-green risks.
- `creative-designer` - completed; no UI/source design changes were introduced, so no rendered design action was required.
- `pulseplate-premortem-risk-review` - completed on the actual diff; risks were stale Dependabot base, Node 24 lockfile drift, incomplete alert closure, and router behavior regression. Mitigations are fresh `origin/main`, exact `7.16.0` package/lock resolution, `npm audit --json` with zero vulnerabilities, focused router tests, full frontend coverage, build, and CSS smoke.

Post-open role order completed:

- [x] `qa-engineer-agent` - completed; found one governance/body drift issue: the PR size governance job requires an exact `## Tests` section, while the initial body used `## Test Plan`. The PR body was edited to the exact required heading.
- [x] `bug-hunter` - completed; no dependency or lockfile defect found. The only false-green risk was the same body-contract drift, fixed by PR body edit before readiness checks.
- [x] `security-auditor` - completed; PASS for scoped dependency security: `react-router-dom` and `react-router` resolve to `7.16.0`, `npm audit --json` reports zero vulnerabilities, and no Python private-index or workflow/deploy surface changed.
- [x] Codex Security diff scan / finding discovery - completed; diff-scoped worklist closed with no reportable findings. Local reports were generated under scan id `65260c65d399_20260604T063925Z`, and the final report validator passed.
- [x] `pulseplate-pr-review` - completed; dry-run report produced no deterministic findings, and `tests/test_pr_review_report.py tests/test_pr_review_context.py` passed with 13 tests.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-b2c2e7aeb5a1.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-b2c2e7aeb5a1.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted; 4/4 oracle commands passed; `mutated_paths=[]`; synthetic reviewed commits are not used as attribution proof.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/6dff06dfe1e4.json`

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze --path frontend/package.json --path frontend/package-lock.json --path docs/review/PR_TBD_FIXED_MAPPING.md` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json` - PASS.
- `node -v` - PASS, `v24.16.0`.
- `npm -v` - PASS, `11.13.0`.
- `cd frontend && npm ci` - PASS.
- `cd frontend && npm audit --json` - PASS, zero vulnerabilities.
- `cd frontend && npm test -- --run src/__tests__/App.test.tsx src/components/__tests__/TabBar.test.tsx src/auth/__tests__/RequireKey.test.tsx src/pages/__tests__/Home.test.tsx src/pages/__tests__/Plate.test.tsx src/pages/Pro/__tests__/ProPaywallPage.test.tsx` - PASS, 6 files and 55 tests.
- `cd frontend && npm run test -- --coverage` - PASS, 91 files, 765 passed, 1 skipped.
- `cd frontend && npm run build` - PASS.
- `cd frontend && npm run smoke:css` - PASS.
- `make validate-changed` - PASS, no Python files changed.
- `python3 scripts/ci/check_pr_body_phase2_gates.py --body "$(gh pr view 1877 --json body --jq .body)" --pr-number 1877 --commit-range origin/main..HEAD` - PASS.
- `python3 scripts/orchestration/pr_review_context.py --pr 1877 --repo Katsiarynakavaleuskaya/PulsePlate --base origin/main --head HEAD --repo-root . --output <local-pr-review-context.json>` - PASS.
- `python3 scripts/orchestration/pr_review_report.py --context <local-pr-review-context.json> --format markdown` - PASS, no deterministic findings.
- `python3 scripts/orchestration/pr_review_report.py --context <local-pr-review-context.json> --format json` - PASS.
- `<repo-root>/.venv/bin/python -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q` - PASS, 13 tests.
- `pre-commit run --all-files` - PASS.
- Pre-push hooks - PASS, including pre-commit, backend pytest, full-repo Bandit, and pip-audit; Docker build hook skipped because no Docker-surface files changed.

## Machine-Heavy Gate Deferral

Full local `make verify` is not claimed. This PR uses the operator-approved machine-heavy exception for the frontend dependency lane: scoped local gates above passed, and final merge readiness still requires current-head sharded CI, strict review-thread disposition, strict merge readiness, and no unresolved bot actionables.

## Current CI Status

Current-head PR checks are pending after the post-open body edit and mapping artifact update. Do not claim merge readiness until current-head CI, review-thread disposition, and strict merge readiness pass.

## Merge Readiness

- [ ] Current-head CI is green on latest commit with no pending required jobs.
- [ ] No unresolved review threads.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`.
- [ ] `check_review_threads_disposition.py --require-auth` passes.
- [ ] `check_merge_ready.py --require-auth` passes.
- [ ] Wait-window completed after latest bot/review activity.
