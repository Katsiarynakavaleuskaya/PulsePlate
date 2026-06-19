# PR 1994 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1994

Branch: `codex/consolidated-dependency-security-alerts`

## Summary

This PR consolidates current dependency-security remediation into one bounded
lane. It updates frontend dependency floors, disables the vulnerable tracked
RAGAS/DiskCache eval dependency profile while preserving runner ergonomics, and
splits Python dependency graph submission by profile so alert attribution cannot
cross-contaminate runtime, eval/data, and optional vector manifests.

## Scope

- Supersede Dependabot PR #1993 by carrying `undici==7.28.0` coverage in this
  branch.
- Update frontend override/lock floors for `dompurify`, `undici`, and `ws`.
- Keep RAGAS native execution disabled while `ragas` / `diskcache` advisories
  have no patched dependency path.
- Regenerate `requirements-evals.txt` through `pip-tools` with
  `--no-emit-index-url`.
- Split Python dependency submission into runtime, eval/data, and RAG/vector
  graph roots.
- Document torch `CVE-2025-3000` as upstream-blocked until advisory and private
  index evidence identify a patched version.

## Out Of Scope

Backend route changes, OpenAPI changes, runtime product behavior, iOS release
behavior, native RAGAS scoring restoration, and speculative torch upgrades.

## Operator Exceptions

- Full local `make verify` was not run under the operator-approved
  machine-heavy exception.
- Validation uses focused local gates, `make validate-changed`,
  `pre-commit run --all-files`, pre-push hooks, and current-head GitHub CI as
  the heavy signal.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- `python3 scripts/orchestration/task_bootstrap.py ...` -> PASS
- `. .venv/bin/activate && pytest -q tests/test_frontend_dependency_guards.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py tests/test_ci_workflow_pr_size_governance_contract.py` -> `114 passed`
- `npm --prefix frontend ls dompurify undici ws --package-lock-only --all` -> PASS
- `npm --prefix frontend audit --package-lock-only --audit-level=moderate` -> PASS, `found 0 vulnerabilities`
- `. .venv/bin/activate && python -m evals.ragas.run_ragas_eval --help` -> PASS
- `npm --prefix frontend run build` -> PASS with existing Vite warnings
- `npm --prefix frontend run test:ci` -> PASS
- `npm --prefix frontend run build-storybook` -> PASS with existing Storybook/Vite warnings; generated `frontend/storybook-static/` was removed
- `. .venv/bin/activate && pytest -q tests/evals/test_ragas_dataset_contract.py tests/evals/test_ragas_metrics_config.py tests/evals/test_ragas_runner_contract.py` -> `14 passed`
- `. .venv/bin/activate && pytest -q tests/test_remaining_modules.py -k ragas` -> `7 passed`
- `make validate-changed` -> PASS; branch mode selected no Python/cross-surface governance files
- `pre-commit run --all-files` -> PASS after `black` reformatted two test files and focused pytest was rerun
- `git diff --check` and `git diff --cached --check` -> PASS
- Credential-oriented scan over changed generated files found no auth URL, token marker, `file:`, or `/Users/` paths.
- Pre-push hooks -> PASS, including `pip-audit`, backend pytest pre-push, and full-repo Bandit.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/ad85012276cf.json`
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> frontend-engineer -> backend-engineer -> qa-engineer-agent -> bug-hunter`

## Premortem

Artifact: `docs/review/CONSOLIDATED_DEPENDENCY_SECURITY_PREMORTEM.md`

Disposition summary:

- Dependency graph cross-contamination risk: FIXED with profile-scoped
  submission roots and guard tests.
- Vulnerable RAGAS/DiskCache no-patch dependency risk: FIXED by disabling
  tracked native RAGAS deps and documenting restoration criteria.
- Frontend audit false-green risk: FIXED by including `ws==8.21.0` alongside
  `dompurify==3.4.11` and `undici==7.28.0`.
- Torch speculative-upgrade risk: DEFERRED with advisory evidence showing no
  patched version.

Evidence: GitHub Actions workflow at
`.github/workflows/python-dependency-submission.yml`,
`frontend/package.json`, `frontend/package-lock.json`,
`requirements-evals.in`, `requirements-evals.txt`,
`tests/test_frontend_dependency_guards.py`,
`tests/test_python_supply_chain_controls.py`, and
`tests/guards/test_security_devtooling_regression_guards.py`.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-eac20f5aaa87.json`
- Artifact:
  `artifacts/orchestration/experiments/results/exp-eac20f5aaa87.json`
- Status: accepted.
- Oracle evidence: dependency-security boundaries preserved, private-index
  leakage not introduced, and local oracle command passed.
- Attribution: commit `fbb936af1` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because the
  accepted oracle-only result materially shaped governance and commit decision.

## Post-Open Review Evidence

Completed for current-head PR #1994:

- `agent-coordinator`: FIXED Phase2/body artifact and bot finding blockers in
  `5b593652f`.
- `qa-engineer-agent`: PASS for acceptance/regression risk on head
  `192b99d93`.
  Evidence: focused dependency/security pytest passed with `114 passed`;
  `npm --prefix frontend ls dompurify undici ws --package-lock-only --all`
  showed `dompurify@3.4.11`, `undici@7.28.0`, and `ws@8.21.0`; npm audit
  reported `found 0 vulnerabilities`.
- `bug-hunter`: PASS for false-green/regression risk on head `192b99d93`.
  Evidence: `pip-audit -r requirements-evals.txt` reported no known
  vulnerabilities, `python -m evals.ragas.run_ragas_eval --help` remained
  importable, PR body Phase2 and review-thread disposition passed, and
  `git diff --check origin/main...HEAD` passed.
- `security-auditor`: PASS with merge caveat on head `192b99d93`.
  Evidence: generated eval files contain no private index URL, credential marker,
  `file://`, or `/Users/` material; npm lock entries resolve the remediated
  floors from the npm registry with integrity; `security-scan` is passing.
- `architecture-specialist`: PASS on head `192b99d93`.
  Evidence: `origin/main...HEAD` has no backend runtime, OpenAPI, iOS,
  migration, or Docker runtime files; dependency ownership stays in frontend
  overrides, profile-scoped workflow roots, eval/manual docs, and advisory docs.
- Codex Security diff scan / finding discovery: completed via the installed
  local diff-scan skill because no callable Codex Security MCP endpoint was
  exposed in this session. No reportable findings. Report:
  `/tmp/codex-security-scans/BMI-App_2025_clean/192b99d93_pr1994_20260619T060921Z/report.md`;
  HTML:
  `/tmp/codex-security-scans/BMI-App_2025_clean/192b99d93_pr1994_20260619T060921Z/report.html`;
  worklist coverage: 1/1 generated source-like rows closed plus supporting
  dependency/security manifests reviewed.
- CodeRabbit: PASS on the latest current-head review status after bot findings
  were fixed in `5b593652f` and mapped in `ae1b1d464`.
- Sourcery: PASS after the weak disabled-state assertion finding was fixed in
  `5b593652f`.
- `pulseplate-pr-review`: dry-run report completed. The only advisory note was
  large-diff review risk, covered by the operator-approved consolidated scope,
  trusted scope labels, PR body scope approvals, `pr_scope_guard`, and focused
  local gates. Report: `/tmp/pulseplate_pr1994_review_report.md`; JSON:
  `/tmp/pulseplate_pr1994_review_report.json`. Calibration tests passed:
  `. .venv/bin/activate && python -m pytest -q tests/test_pr_review_report.py tests/test_pr_review_context.py`
  -> `13 passed`.
- Review thread disposition guard:
  `GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1994 --require-auth`
  -> PASS.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Current human and bot review threads have been checked and the actionable items
known at this pass are dispositioned below before resolution.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: fbb936af1
Evidence: `frontend/package.json`
Evidence: `frontend/package-lock.json`
Evidence: `requirements-evals.in`
Evidence: `requirements-evals.txt`
Evidence: GitHub Actions workflow at `.github/workflows/python-dependency-submission.yml`
Evidence: `tests/test_frontend_dependency_guards.py`
Evidence: `tests/test_python_supply_chain_controls.py`
Evidence: `tests/guards/test_security_devtooling_regression_guards.py`

Disposition: FIXED
Commit: 5b593652f
Evidence: `tests/test_python_supply_chain_controls.py`
Evidence: `docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md`
Evidence: `docs/review/PR_1994_FIXED_MAPPING.md`
Reason: Addressed Sourcery's weak disabled-state assertion finding, CodeRabbit's unchecked fixed-mapping checklist finding, CodeRabbit's torch advisory anchor finding, and CodeRabbit's single-disposition / GitHub capitalization notes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1994#pullrequestreview-4527742903 -> 5b593652f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1994#discussion_r3438230320 -> 5b593652f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1994#pullrequestreview-4527768907 -> 5b593652f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1994#pullrequestreview-4527790634 -> 5b593652f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1994#discussion_r3438270668 -> 5b593652f

## Deferred / Follow-Ups

- Native RAGAS companion scoring restoration is tracked by
  [`ledger-p1-restore-ragas-companion-safe-deps`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-restore-ragas-companion-safe-deps).
- Torch `CVE-2025-3000` remains upstream-blocked until advisory/private-index
  evidence identifies a patched version.
- Dependabot PR #1993 was closed as superseded after this replacement PR was
  opened with `undici==7.28.0` coverage.

## Merge Readiness

Status: NOT READY while current-head PR CI and strict merge-readiness are
pending.

Required before merge:

- Current-head PR CI parity.
- No unresolved actionable human or bot review comments.
- Strict merge-readiness with auth.
- Mandatory wait-window after latest review/bot activity.
