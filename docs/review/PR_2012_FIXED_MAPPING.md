# PR #2012 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2012
Title: `fix(deps): bump Ruff quality toolchain`
Branch: `codex/deps-ruff-quality-refresh`

## Summary

This PR started as the human-owned Ruff replacement for Dependabot PR #2002:

- `constraints.txt`: `ruff>=0.15.17` -> `ruff>=0.15.18`
- `requirements-all.txt`: `ruff>=0.15.17` -> `ruff>=0.15.18`
- `requirements-dev.in`: `ruff~=0.15.17` -> `ruff~=0.15.18`
- `requirements-dev.txt`: `ruff==0.15.17` -> `ruff==0.15.18`
- `requirements-lock.txt`: `ruff==0.15.17` -> `ruff==0.15.18`

After PR open, current-head CI exposed a Docker Build `security-scan` failure
from Trivy Code Scanning alert #613: `CVE-2026-54297` in
`ios/Gemfile.lock` for Fastlane's `faraday 1.10.5` graph. The user explicitly
asked to fix Docker in this lane, so the PR also includes a narrow Trivy policy
compatibility fix for current Trivy v0.71.2 output. It does not update the
Fastlane/Faraday dependency graph; that removal/remediation lane remains
tracked separately.

Out of scope: `requirements.txt`, testing stack PR #2001, runtime, RAG/vector,
Torch alerts #160/#161/#162, and full Faraday/Fastlane dependency remediation.

## Implementation Commit

- `d30906288a8168d97192243203609be4f47a2397` - `fix(deps): bump Ruff quality toolchain`
- `9657435215a11e1f203bcefb71ff5d3f6531dd63` - `fix(security): align Faraday Trivy suppression with current scan output`

The implementation commit includes the governed Experiment Runner attribution
trailer:

`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Lane Start Provenance

- Worktree: `worktrees/deps-ruff-quality-refresh`
- Branch: `codex/deps-ruff-quality-refresh`
- Packet: `artifacts/orchestration/task_packets/7f05a69c890f.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Role dispatch:
  `python scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/7f05a69c890f.json --pretty`
- Pre-open role order completed:
  `agent-coordinator -> cursor-specialist-agent -> architecture-specialist`

## Premortem Risk Review

- Artifact: `artifacts/orchestration/premortem/20260623_ruff_quality_refresh.md`
- Disposition: proceed with Ruff-only manual alignment.
- Fixed/controlled risks:
  - Resolver churn rejected after dry-run evidence showed unrelated dependency
    movement outside the lane.
  - Stale Dependabot `requirements.txt` surface rejected because current `main`
    does not expose Ruff through that file for this lane.
  - Approved proxy availability for `ruff==0.15.18` proved before editing.
  - Current `main` red state recorded as a merge-readiness blocker.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-1efee9eb482c.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-1efee9eb482c.json`
- Status: `accepted`
- Source diff paths:
  `constraints.txt`, `requirements-all.txt`, `requirements-dev.in`,
  `requirements-dev.txt`, `requirements-lock.txt`
- Oracle commands:
  - `python -m pytest -q tests/test_install_locked_python_requirements.py -k ruff` - PASS
  - `python -m pytest -q tests/test_dependency_security_guard.py` - PASS
- Co-author required: yes, included on implementation commit `d30906288a8168d97192243203609be4f47a2397`.

## Local Validation

Focused local gates:

- `python scripts/orchestration/check_preflight.py --path constraints.txt --path requirements-all.txt --path requirements-dev.in --path requirements-dev.txt --path requirements-lock.txt` - PASS
- `python scripts/orchestration/check_agent_consistency.py` - PASS
- `git diff --check` - PASS
- `python -m pip index versions ruff --index-url "$PULSEPLATE_PYTHON_INDEX_URL"` - PASS; approved proxy served `ruff (0.15.18)` as latest.
- `python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py` - PASS
- `python scripts/ci/install_locked_python_requirements.py --requirements-file requirements-dev.txt --constraints-file constraints.txt --install-dev --preflight-only` - PASS
- `python verify_requirements.py` - PASS
- `python -m pip_audit -r requirements-dev.txt` - PASS; no known vulnerabilities found.
- `python -m pip_audit -r requirements-lock.txt` - PASS; no known vulnerabilities found.
- `make validate-changed` - PASS; selected no Python or cross-surface governance files, so the focused dependency/security pytest bundle remains the scoped test signal.
- `pre-commit run --all-files` - PASS
- Pre-push hooks - PASS, including `pip-audit`, backend pre-push pytest, and full-repo Bandit.
- `python scripts/ci/check_pr_body_phase2_gates.py --pr-number 2012 --body "$(cat artifacts/orchestration/pr_bodies/pr2012_live_body.md)" --commit-range origin/main..HEAD --experiment-runner-evidence-mode required` - PASS after the Phase2 parser-shape correction.
- `python scripts/ci/check_docs_phase1_gates.py --files docs/review/PR_2012_FIXED_MAPPING.md` - PASS.
- `bash scripts/ci/pr_scope_guard.sh` - PASS.
- `python3 scripts/orchestration/task_bootstrap.py --goal "Fix PR #2012 Docker Build security-scan Faraday Trivy policy regression after Ruff dependency PR open" --task-class security --pr-phase post_open_review --path trivy/ignore-policy.rego --path tests/test_trivy_ignore_policy_expiry.py --path docs/security/CVE-2026-54297-faraday-fastlane.md --path docs/review/PR_2012_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent qa-engineer-agent` - PASS; packet `artifacts/orchestration/task_packets/f80fa94eccc9.json`.
- `python scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/f80fa94eccc9.json --pretty` - PASS; expanded Docker/Faraday security scope role order recorded.
- `python3 scripts/ci/check_trivy_ignore_policy_expiry.py` - PASS.
- `$VENV_PYTHON -m pytest -q tests/test_trivy_ignore_policy_expiry.py tests/test_ci_workflow_pr_size_governance_contract.py::test_build_workflow_trivy_fs_sarif_is_temp_isolated_before_upload` - PASS; 14 passed, existing Starlette deprecation warning only.
- `TRIVY_DB_REPOSITORY=ghcr.io/aquasecurity/trivy-db <trivy-v0.71.2>/trivy fs . --skip-dirs trivy --ignore-policy trivy/ignore-policy.rego --ignorefile .trivyignore --scanners vuln --severity CRITICAL,HIGH --format json --exit-code 1 --output <scan-output>.json` - PASS; local Trivy v0.71.2 exited 0 and the JSON output had zero HIGH/CRITICAL vulnerabilities.

Full local `make verify` was not run under the operator-approved machine-heavy
exception for this dependency lane. Current-head CI is the required heavy parity
signal before any merge-readiness claim.

## Post-Open Role Passes

- `qa-engineer-agent` - initial BLOCKED on older head/body because the PR body
  and mapping artifact used parser-rejected Phase2 shape. Disposition: FIXED by
  commit `8eab3370564a71fbdd88ccfcde26a0887f13e2bd` and live PR body update.
  Evidence: local required-mode Phase2 validation passed after correction.
- `bug-hunter` - PASS on head
  `8eab3370564a71fbdd88ccfcde26a0887f13e2bd`; no PR-diff bugs found.
  Evidence: scoped dependency checks, `pip-audit`, `verify_requirements.py`,
  `pr_scope_guard.sh`, and review-thread inspection passed or found no
  unresolved threads.
- `security-auditor` - PASS on head
  `8eab3370564a71fbdd88ccfcde26a0887f13e2bd`; no Ruff supply-chain/security
  finding found. Evidence: diff is Ruff dev/tooling only, approved proxy served
  `ruff==0.15.18`, `pip-audit` passed for dev and lock files, and no runtime,
  Docker, auth, secrets, API, or app-code surface changed.
- `Codex Security diff scan` - PASS on scan
  `3e2c0ae4-3db4-4944-b6b5-9bcaf4ebba40`; 0 findings. Artifact outputs:
  `report.md`, `scan-manifest.json`, `coverage.json`, and `findings.json` in
  the durable Codex Security scan directory. The canonical target remained
  `git_diff` over base `df9ede804b22a956933c7981072a8b5a327cc01a` and head
  `ccdf81b474a8d68b14077871ecdc178969129dca`.
- `pulseplate-pr-review` - PASS in dry-run report mode; no deterministic
  findings for the dependency/governance diff.
- Expanded Docker/Faraday security scope - FIXED by commit
  `9657435215a11e1f203bcefb71ff5d3f6531dd63`. Evidence: GitHub Code Scanning
  alert #613 reports `CVE-2026-54297` for `faraday 1.10.5` with fixed version
  `>= 2.14.3`; `trivy/ignore-policy.rego` now accepts both Trivy JSON
  `2.14.3` and SARIF/GitHub `>= 2.14.3` fixed-version shapes while preserving
  exact `CVE + faraday + 1.10.5 + PURL/PkgID + PrimaryURL + severity/status`
  matching.

## Current-Head CI Notes

- Latest `pr_scope_guard` and `PR Body Phase2 gates` runs pass on head
  `8eab3370564a71fbdd88ccfcde26a0887f13e2bd`; earlier failures were from the
  superseded parser-shape revision.
- Docker Build and Push `security-scan` failure was traced to Trivy Code
  Scanning alert #613 (`CVE-2026-54297`, `faraday 1.10.5`,
  `ios/Gemfile.lock`). The PR now includes the scoped Rego compatibility fix in
  commit `9657435215a11e1f203bcefb71ff5d3f6531dd63`; local Trivy v0.71.2
  filesystem scan exits 0 with zero HIGH/CRITICAL findings after the patch.
- Current-head CI must rerun on the latest pushed head before any readiness
  claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No actionable review threads existed at PR open.

No actionable QA, bug-hunter, security-auditor, Codex Security, CodeRabbit, or
pulseplate-pr-review findings are currently known after the Phase2
parser-shape and Docker/Faraday Trivy policy fixes. Any later bot/review
findings still require disposition before merge-readiness governance can pass.

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

- Ruff-only dependency update -> `d30906288a8168d97192243203609be4f47a2397`
- Faraday Trivy policy compatibility fix ->
  `9657435215a11e1f203bcefb71ff5d3f6531dd63`

## Deferred / Follow-ups

- Dependabot PR #2001 remains the separate testing stack lane for `pytest`,
  `hypothesis`, and `coverage`.
- Dependabot alerts #160/#161/#162 for `torch` remain deferred because the GHSA
  lane currently has no patched version.
- Dependabot alert #224 for `faraday` remains a dedicated Fastlane/Ruby security
  lane for dependency graph remediation/removal. This PR only fixes the current
  Trivy policy mismatch that made Docker `security-scan` fail despite the
  documented temporary suppression.
- Dependabot PR #2002 should remain open until this replacement PR is merged or
  otherwise confirmed as superseding.

## Merge Readiness

Not merge-ready at this point.

- Current `main` is known red on current-head CI.
- Current-head CI for PR #2012 must rerun on the latest pushed head after the
  Docker/Faraday Trivy policy fix.
- Post-open role passes completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Codex Security diff scan/finding discovery completed with 0 findings.
- CodeRabbit and other bot actionables must be reviewed and dispositioned.
- Strict merge-readiness governance must be rerun after the latest head commit,
  current-head CI, bot comments, and review-thread state settle.
