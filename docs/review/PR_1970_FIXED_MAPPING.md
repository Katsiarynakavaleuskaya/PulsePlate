# PR 1970 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1970>

## Summary

This emergency lane fixes the stale post-health-extraction main/nightly test
failure and refreshes frontend dev tooling to a high-severity-audit-clean Vite
8 / Storybook 10 graph without `npm audit fix --force`, Trivy ignores, npm
audit suppressions, or fake torch remediation.

## Lane Start Provenance

- Branch: `codex/fix-main-nightly-frontend-security-deps`
- Base: `origin/main` at `3a881ea0362137e131619be52666ab54692091e1`
- Task class: `Security / Frontend / CI`
- PR phase: `pre_open`
- Packet: `artifacts/orchestration/task_packets/41917ee6517b.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Pre-edit role order completed:
  `agent-coordinator -> architecture-specialist -> frontend-engineer -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter -> creative-designer`.
- Initial implementation commit:
  `d928cec353dde88ed429c1c3cda20e50ee38d421`
- Scope correction commit:
  `5352596631a9653943b995f2887bf6d19371eb50`
- Sourcery follow-up commit:
  `d6451320b1a6c142b58d6d41fb521b639afe1742`
- Full local `make verify`: intentionally not run under the operator-approved
  emergency narrow-lane scope; this artifact does not claim full local verify.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Inline review comments at first inspection: none.
- Sourcery review `4491179836`: reviewed and dispositioned below.
- CodeRabbit/Cubic/Sourcery generated summaries: reviewed as advisory
  summaries. Their early references to `.github/workflows/frontend-ci.yml`
  became stale after commit `5352596631a9653943b995f2887bf6d19371eb50`, which
  removed the workflow file from the PR diff.
- Final current-head review-thread, bot actionable, and strict disposition
  checks remain required before any merge-readiness claim.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1970#pullrequestreview-4491179836 -> d6451320b1a6c142b58d6d41fb521b639afe1742
Disposition: FIXED
Commit: d6451320b1a6c142b58d6d41fb521b639afe1742
Evidence: `frontend/package.json` and `frontend/package-lock.json` no longer list direct `esbuild` in root `devDependencies`; `frontend/package.json` keeps `overrides.esbuild`, `npm ls esbuild vite storybook @storybook/react-vite @vitejs/plugin-react` reports `esbuild@0.28.1 overridden`, and `frontend/package.json` records `msw.workerDirectory: ["public"]` for the generated `frontend/public/mockServiceWorker.js` asset.
Reason: Sourcery flagged duplicate `esbuild` pinning and noted the generated MSW worker header; the duplicate direct pin is removed while the audit-fixed version is still enforced, and generated-worker provenance stays in MSW package config plus mapping evidence rather than a manual generated-file comment.

## Post-Open Role Review Evidence

- `qa-engineer-agent`: no code/test blocker on the implementation; identified
  governance blockers for missing mapping, PR body Phase2, stale scope guard,
  and pending bot/current-head checks.
- `bug-hunter`: found two P1 governance blockers: missing mapping artifact and
  workflow+frontend scope guard due `.github/workflows/frontend-ci.yml` being in
  the initial diff.
  - Disposition: FIXED for workflow scope by commit
    `5352596631a9653943b995f2887bf6d19371eb50`, which restores the workflow to
    `origin/main` and keeps Codecov executable removal in frontend config and
    package dependencies only.
  - Disposition: FIXED for mapping by this artifact.
- `security-auditor`: confirmed the npm graph/security direction and raised the
  same workflow-scope and mapping blockers.
  - Disposition: FIXED by commit
    `5352596631a9653943b995f2887bf6d19371eb50` plus this mapping artifact.
  - Torch Dependabot alerts remain out of scope because GitHub reports
    `patched: null` for the current `torch <= 2.12.0` advisory.

## Premortem Finding Closure

- Artifact:
  `artifacts/orchestration/premortem/main-nightly-frontend-security-deps-premortem.md`
- Decision: proceed with changes.
- Storybook 10 compatibility risk: FIXED by Storybook config/import updates and
  `npm run build-storybook`.
- Codecov removal completeness risk: FIXED by removing `@codecov/vite-plugin`
  from `frontend/package.json` and `frontend/vite.config.ts`, while commit
  `5352596631a9653943b995f2887bf6d19371eb50` keeps
  `.github/workflows/frontend-ci.yml` out of this PR.
- Lockfile drift risk: NOT-A-BUG; clean npm 11 lock regeneration was required
  because the old lock could not resolve the Storybook 8/10 graph without
  force/legacy peer flags.
- Torch alert risk: DEFERRED/NOT-A-BUG for this PR; current GitHub Dependabot
  data reports three open `torch` alerts with `patched: null`.
- Nightly over-claim risk: NOT-A-BUG; this PR only claims the stale health test
  and frontend audit fixes, not generic runner shutdown remediation.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/main-nightly-frontend-security-deps-oracle-packet.json`
- Artifact:
  `artifacts/orchestration/experiments/results/main-nightly-frontend-security-deps-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted.
- Oracles:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 -m pytest -q tests/test_legacy_runtime_env_canonicalization.py tests/test_health_db.py tests/test_app_endpoints_combined.py tests/test_python_supply_chain_controls.py`
- Co-author required: true.
- Co-author trailer present on implementation commit
  `d928cec353dde88ed429c1c3cda20e50ee38d421`.

## Codex Security Diff Scan / Finding Discovery

- Skill: `codex-security:security-diff-scan`.
- Scan directory:
  `/tmp/codex-security-scans/fix-main-nightly-frontend-security-deps/d928cec35_20260613T084517Z`
- Report:
  `/tmp/codex-security-scans/fix-main-nightly-frontend-security-deps/d928cec35_20260613T084517Z/report.md`
- HTML report:
  `/tmp/codex-security-scans/fix-main-nightly-frontend-security-deps/d928cec35_20260613T084517Z/report.html`
- Work ledger:
  `/tmp/codex-security-scans/fix-main-nightly-frontend-security-deps/d928cec35_20260613T084517Z/artifacts/02_discovery/work_ledger.jsonl`
- Result: PASS, no reportable diff-scoped security findings. The five
  source-like changed files reviewed by the scanner each have not-applicable
  receipts; no validation or attack-path candidate remained.
- Goal accounting from `update_goal`: 23,472 tokens, 126 seconds.

## PulsePlate PR Review

- Skill: `pulseplate-pr-review`.
- Context: `/tmp/pulseplate_pr_1970_review_context.json`.
- Markdown report: `/tmp/pulseplate_pr_1970_review_report.md`.
- JSON report: `/tmp/pulseplate_pr_1970_review_report.json`.
- Result: one advisory `note` for large-diff review planning because the
  regenerated frontend lockfile makes the diff exceed the 800 changed-line
  threshold.
- Disposition: NOT-A-BUG.
- Evidence: the PR contains the intended emergency dependency graph update,
  generated `frontend/package-lock.json`, Storybook compatibility edits, and two
  narrow backend/supply-chain tests. The workflow file is no longer in
  `origin/main...HEAD`; focused backend, frontend audit/build/test/storybook,
  Codex Security, post-open role reviews, and `make validate-changed` are the
  scoped validation path.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `scripts/orchestration/start_pr_lane.sh ...`
- PASS: role dispatch via
  `scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/41917ee6517b.json --mode runtime ...`
- PASS:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_legacy_runtime_env_canonicalization.py tests/test_health_db.py tests/test_app_endpoints_combined.py tests/test_python_supply_chain_controls.py`
  (`90 passed`)
- PASS: `cd frontend && npm ci` (`found 0 vulnerabilities`)
- PASS: `cd frontend && npm audit --audit-level=high` (`found 0 vulnerabilities`)
- PASS: `cd frontend && npm audit --omit=dev --audit-level=high`
  (`found 0 vulnerabilities`)
- PASS:
  `cd frontend && npm ls vite @vitejs/plugin-react vitest esbuild storybook @storybook/react-vite @storybook/addon-docs jsdom`
- PASS: `cd frontend && npm run test:ci`
- PASS: `cd frontend && npm run build`
- PASS: `cd frontend && npm run smoke:css`
- PASS: `cd frontend && npm run build-storybook`
- PASS: `npm ci && npm audit --audit-level=high` at repo root
- PASS:
  `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python`
  after implementation commit
- PASS:
  `PRE_COMMIT_HOME=/tmp/pre-commit-main-nightly-security-deps pre-commit run --all-files`
  after implementation commit
- PASS: initial commit hooks and pre-push hooks, including frontend tests,
  backend changed tests, pip-audit, and full-repo Bandit pre-push.
- PASS after Sourcery follow-up:
  `cd frontend && npm install --package-lock-only` (`found 0 vulnerabilities`)
- PASS after Sourcery follow-up:
  `cd frontend && npm ls esbuild vite storybook @storybook/react-vite @vitejs/plugin-react`
- Final post-mapping `make validate-changed`, `pre-commit run --all-files`,
  PR body gates, and current-head CI are still required before merge discussion.

## Security Alerts

- Dependabot open alerts rechecked before edits: three open `torch` alerts
  across `requirements-ci-lite.txt`, `requirements-rag-vector-cpu.txt`, and
  `requirements-rag-vector.txt`.
- Advisory: CVE-2025-3000 / GHSA-rrmf-rvhw-rf47.
- Vulnerable range: `<= 2.12.0`.
- Patched version: `null`.
- Code scanning open alerts: `0`.
- Secret scanning open alerts: `0`.
- No new suppressions, ignores, or waiver extensions were added.

## Machine-Heavy Verify Deferral

- Full local `make verify` was not run by explicit operator instruction for
  this emergency lane.
- Accepted local validation before merge discussion is focused backend pytest,
  frontend npm audit/build/test/storybook gates, `make validate-changed`,
  `pre-commit run --all-files`, current-head CI, review disposition, and strict
  merge-readiness wrappers.

## Deferred / Follow-ups

- Torch CVE-2025-3000 remains tracked by the existing security advisory and
  backlog until upstream publishes a patched version outside the vulnerable
  range.
- Nightly runner shutdown/concurrency remains separate unless a fresh
  current-head run exposes the same health test failure.

## Merge Readiness

- [x] Post-open required role pass:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan / finding discovery.
- [x] `pulseplate-pr-review` after mapping artifact.
- [ ] PR body Phase2 gate against the live PR body.
- [ ] Scope guard against the final PR body and current branch diff.
- [ ] Final focused local gates after mapping/body updates.
- [ ] Current-head CI terminal success.
- [ ] Strict review-thread disposition with auth.
- [ ] Strict merge-readiness wrapper with auth.
- [ ] CodeRabbit / Sourcery / Cubic actionables checked on current head.
- [ ] Mandatory wait-window after latest bot/review activity.
