# PR 1961 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1961>

## Goal

Complete post-open governance for the locked Bandit Security Scan fix without
widening beyond the existing CI workflow, supply-chain regression test, fixed
mapping artifact, and PR body mirror.

## Business Reason

The scheduled/manual Security Scan workflow must not downgrade Bandit after the
locked `ci-lite` installer has already installed the repository-approved Bandit
version. Keeping the fix narrow protects CI supply-chain integrity without
changing runtime product behavior.

## Scope

- `.github/workflows/security.yml`
- `tests/test_python_supply_chain_controls.py`
- `docs/review/PR_1961_FIXED_MAPPING.md`
- PR body Phase2 mirror

## Out Of Scope

- No backend, OpenAPI, web, iOS, database, runtime AI, product behavior, or
  migration changes.
- No dependency lock or constraints rewrite.
- No broad CI/security workflow cleanup beyond the existing Bandit downgrade
  fix.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## External Review Availability And Bot Evidence

- Codex review availability notice:
  <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1961#issuecomment-4685539681>
  - Disposition: NOT-A-BUG
  - Evidence: availability/quota notice only; it contains no code finding or
    requested repository change.
- CodeRabbit review availability notice:
  <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1961#issuecomment-4685540185>
  - Disposition: NOT-A-BUG
  - Evidence: rate-limit/usage-credit notice only; it contains no code finding.
- Sourcery review availability notice:
  <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1961#pullrequestreview-4480965649>
  - Disposition: NOT-A-BUG
  - Evidence: weekly diff-character rate-limit notice only; it contains no code
    finding.
- Cubic review:
  <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1961#pullrequestreview-4480985675>
  - Disposition: NOT-A-BUG
  - Evidence: Cubic reported "No issues found" across 2 files for head
    `4c445bd8ad0276b948899f1f51d7b3de259933f8`.
- Codecov:
  <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1961#issuecomment-4685675350>
  - Disposition: NOT-A-BUG
  - Evidence: Codecov reported that all modified and coverable lines are
    covered by tests.
- GitHub review threads:
  - Disposition: NOT-A-BUG
  - Evidence: GraphQL review-thread query returned `totalCount: 0` for PR
    #1961 before this artifact was created.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/29c79c572307.json`
- Branch: `codex/propose-fix-for-bandit-downgrade-issue`
- Head before governance artifact: `4c445bd8ad0276b948899f1f51d7b3de259933f8`
- Note: this is late post-open remediation evidence. PR #1961 was already open
  before this governance pass; packet creation is provenance only and did not
  execute role agents.

## Role Dispatch Evidence

- Declared packet order executed in sequence:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> dev-operator -> cursor-specialist-agent -> architecture-specialist`.
- `agent-coordinator`: PASS / scope locked to the existing Security Scan
  workflow/test diff plus this mapping artifact and PR body mirror. No widening
  into requirements, constraints, installer behavior, or runtime/product
  surfaces.
- `qa-engineer-agent`: PASS / no code or test change required before mapping.
  Evidence: confirmed the workflow no longer re-installs `bandit==1.8.6`,
  `requirements-ci-lite.txt` still pins Bandit, and the regression test covers
  the intended invariant. Governance blocker was missing mapping/body only.
- `bug-hunter`: PASS / no code regression found. Evidence: flagged a
  false-confidence risk that normal PR CI does not prove the scheduled/manual
  `Security Scan` workflow; this remains a required post-push validation item.
- `security-auditor`: PASS / no code or test security finding requiring a fix.
  Evidence: confirmed the fix removes the Bandit downgrade while preserving the
  locked `ci-lite` direct-proxy setup, Safety proxy install, constraints use,
  and pinned workflow actions. Required follow-up: dispatch `security.yml` on
  the PR branch before merge-readiness claim.
- `dev-operator`: PASS / local and GitHub gate sequence confirmed. Evidence:
  exact local validation sequence and post-push workflow-dispatch requirement
  recorded; no process blocker besides missing mapping/body and no PR-branch
  `Security Scan` run yet.
- `cursor-specialist-agent`: PASS / provenance flow adequate. Evidence:
  packet identity and role binding were valid; blocker was missing
  `docs/review/PR_1961_FIXED_MAPPING.md` and PR body Phase2 mirror.
- `architecture-specialist`: PASS / no architecture blocker. Evidence:
  backend/OpenAPI/client/runtime untouched; tool ownership remains in the
  shared locked supply-chain path.

## Premortem Findings

- PM-001: Missing fixed mapping blocks Phase2, disposition, and merge-readiness
  gates.
  - Disposition: FIXED
  - Evidence: this artifact adds parser-safe `Discussion Thread Pass` and
    `Fixed in Commit Mapping` sections.
- PM-002: External review quota/rate-limit notices could be mistaken for
  approvals or actionables.
  - Disposition: FIXED
  - Evidence: external availability notices are recorded separately from the
    parser-owned fixed-mapping section with NOT-A-BUG dispositions.
- PM-003: Normal PR CI could be mistaken for proof that the scheduled/manual
  `Security Scan` workflow ran.
  - Disposition: FIXED
  - Evidence: this artifact records workflow-dispatch proof as a required
    pre-merge validation item; no readiness claim is made from unrelated PR CI.
- PM-004: Fixing governance before implementation could hide a real Bandit or
  Safety workflow regression.
  - Disposition: NOT-A-BUG
  - Evidence: role passes reviewed the implementation first; no code/test
    blocker was found before this mapping artifact was created.
- PM-005: Local-only artifacts or absolute personal paths could leak into the
  committed diff.
  - Disposition: FIXED
  - Evidence: only this repo review artifact is intended for commit; local
    task, experiment, Codex Security, and PR review outputs remain untracked.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/artifacts/orchestration/experiments/pr1961-governance-oracle-packet.json`
- Artifact: `artifacts/orchestration/experiments/results/pr1961-governance-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution: `fixed_mapping_review`
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `coauthor_required=true`
- Co-author reason: Experiment Runner oracle evidence shaped PR #1961
  fixed-mapping and merge-readiness governance.
- Oracle commands:
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `python3 scripts/ci/guard_actions_pin.py`
  - `python3 -m pytest -q tests/test_python_supply_chain_controls.py::test_security_scan_workflow_uses_ci_lite_direct_proxy_setup`

## Codex Security Diff Scan

- Status: PASS / no reportable findings.
- Scan bundle: `/tmp/codex-security-scans/BMI-App_2025_clean/4c445bd8ad02_20260612T054804Z`
- Report: `/tmp/codex-security-scans/BMI-App_2025_clean/4c445bd8ad02_20260612T054804Z/report.md`
- HTML report: `/tmp/codex-security-scans/BMI-App_2025_clean/4c445bd8ad02_20260612T054804Z/report.html`
- Coverage: `deep_review_input.csv` contains 2/2 PR-scoped rows, and
  `work_ledger.jsonl` has completion receipts for both
  `.github/workflows/security.yml` and
  `tests/test_python_supply_chain_controls.py`.
- Finding discovery: no technically plausible security candidates emitted;
  `raw_candidates.jsonl` is empty. Validation and attack-path phases were
  skipped per the diff-scan contract because discovery produced no candidates.
- Limitation: no PR-branch `workflow_dispatch` run of `.github/workflows/security.yml`
  existed when the local scan completed; dispatch proof remains required before
  any merge-readiness claim.

## PulsePlate PR Review

- Initial report: `/tmp/pulseplate_pr_review_1961.md`
- Initial JSON: `/tmp/pulseplate_pr_review_1961.json`
- Initial finding: governance-only missing fixed-mapping artifact/body mirror.
- Disposition: FIXED by this artifact.
- Post-mapping report: `/tmp/pulseplate_pr_review_1961_after_mapping.md`
- Post-mapping JSON: `/tmp/pulseplate_pr_review_1961_after_mapping.json`
- Post-mapping result: no deterministic findings and no warnings; JSON
  `findings=[]`.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --path .github/workflows/security.yml --path tests/test_python_supply_chain_controls.py --path docs/review/PR_1961_FIXED_MAPPING.md`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `. .venv/bin/activate && pytest -q tests/test_python_supply_chain_controls.py::test_security_scan_workflow_uses_ci_lite_direct_proxy_setup`
- PASS: `python3 scripts/ci/guard_actions_pin.py`
- PASS: `git diff --check origin/main...HEAD`
- PASS: `python3 scripts/ci/check_docs_phase1_gates.py --files docs/review/PR_1961_FIXED_MAPPING.md`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1961 --body "$(cat /tmp/pr1961_body_prepared.md)"`
- OPERATOR-DEFERRED: full local `make verify`
- PENDING: PR-branch `workflow_dispatch` run of `.github/workflows/security.yml`
- PENDING: strict live merge-readiness wrapper with exported GitHub token after
  push and current-head CI completion.

## Machine-Heavy Verify Exception

Full local `make verify` is operator-deferred for this coordinator-owned
CI/tooling governance lane under the root `AGENTS.md` machine-heavy PR exception.
The operator explicitly confirmed that this repository has roughly 10k tests and
that full local `make verify` is outside the acceptable machine budget for this
lane. A full `make verify` run was started before that clarification and stopped
at operator direction during the `diff-cov` coverage pytest phase with
`KeyboardInterrupt` / `make: *** [diff-cov] Error 2`; this interrupted run is
not used as success or failure evidence.

Required substitute evidence before any merge-readiness claim:

- PR-scoped local gates listed above remain PASS.
- Current-head GitHub CI parity must be green for required/touched surfaces,
  including lint, diff coverage at the required threshold, relevant test matrix,
  and governance/security checks.
- PR-branch `workflow_dispatch` for `.github/workflows/security.yml` must pass
  on the current PR head.
- `check_merge_ready.py --require-auth` must pass after current-head CI and bot
  review state settle.

## Security Notes

- The PR removes the ad-hoc `bandit==1.8.6` reinstall from the Security Scan
  job-local install step.
- Bandit remains installed through the locked `ci-lite` profile, where
  `requirements-ci-lite.txt` pins `bandit==1.9.4`.
- Safety remains installed through the approved private package proxy path with
  `-c constraints.txt`.
- No action-pin drift was introduced; local action-pin guard passed.
- No secrets, auth, deploy, OpenAPI, runtime product, database, web, or iOS
  behavior changed.

## Risks And Rollback

- Risk: the scheduled/manual Security Scan workflow could still fail at runtime
  if required repository secrets/vars for the private package proxy or Safety
  audit are unavailable.
- Validation control: dispatch `security.yml` on the PR branch and verify the
  current-head run before any readiness claim.
- Rollback: revert the workflow/test commit if the dispatched Security Scan
  proves this install path breaks. Prefer preserving the locked Bandit source
  and fixing any Safety/proxy installer issue in the locked path rather than
  restoring the Bandit downgrade.

## Deferred / Follow-ups

- None. Workflow-dispatch proof is a required validation item for this PR, not
  a deferred follow-up.

## Merge Readiness

- [ ] Required/current-head checks PASS with no pending required jobs
- [ ] PR-branch `Security Scan` workflow_dispatch run PASS on current head
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped
- [ ] Strict merge-readiness wrapper PASS with `--require-auth`
- [ ] Final post-bot/review wait cycle completed
