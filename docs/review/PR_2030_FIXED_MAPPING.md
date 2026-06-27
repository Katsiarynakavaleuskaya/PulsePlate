# PR #2030 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2030

Branch: `codex/creative-code-human-approved-pr-promotion-pr3`

## Summary

This PR adds PR-3 human-approved creative-code PR promotion tooling. It turns
one accepted PR-2 local patch result into a later normal non-draft
`experiment/*` pull request only after isolated validation and explicit TTY
human approval.

## Scope

- Add strict PR promotion plan, validation, approval, and receipt contracts.
- Add local `plan`, `validate`, `approve`, and `promote` CLI commands.
- Bind PR-2 lineage, patch fingerprints, changed paths, validation, approval,
  receipt replay, human Git identity, branch creation, and PR readback.
- Keep the tool same-repo, local-only, non-draft-only, and fakeable in tests.

## Out Of Scope

No real promoted candidate PR is opened by PR-3. No draft PRs, branch updates,
force push, review requests, review submissions, review-thread resolution,
fixed-mapping automation, merge-readiness claims, merge, release, Slack,
GitHub App, workflow, product runtime, OpenAPI/client, frontend, iOS, DB, or
dependency changes are authorized.

## Implementation Commits

- `1a93ca062` - add PR-3 contracts, schemas, CLI, docs, and fake-transport
  tests for human-approved non-draft creative-code PR promotion.
- `a4e06d845` - fix post-open QA findings by binding promote-time patch
  fingerprints, validation/approval artifacts, and patch-derived changed
  paths.
- `01dbc95c7` - fix post-open bug-hunter findings by enforcing human Git
  identity, stale receipt replay binding, and pre-push branch-race checks.
- `59a2e5daf` - fix post-open security-auditor findings by removing
  force-style push flags and suppressing partial receipts until commit identity
  verification succeeds.

## Lane Start Provenance

- Base branch: `main`
- Branch: `codex/creative-code-human-approved-pr-promotion-pr3`
- Packet: `artifacts/orchestration/task_packets/698e1c76bbed.json`
- Role order executed pre-implementation:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> cursor-specialist-agent -> architecture-specialist`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed for local role-agent findings.
- [x] Fixed in commit mapping completed
- [x] Fixed in commit mapping created after GitHub assigned PR number `#2030`.
- [x] Initial PR open: no GitHub review threads were resolved by this PR.
- [x] Post-open `qa-engineer-agent` pass completed; actionable findings fixed
  in `a4e06d845`.
- [x] Post-open `bug-hunter` pass completed; actionable findings fixed in
  `01dbc95c7` and `59a2e5daf`.
- [x] Post-open `security-auditor` pass completed; actionable findings fixed
  in `59a2e5daf`.
- [x] CodeRabbit review completed with no actionable code-thread mapping
  required at artifact creation.
- [x] `pulseplate-pr-review` completed; advisory fixed-mapping and large-diff
  notes are dispositioned below.
- [ ] Codex Security plugin finalization completed. Current attempt reported
  zero findings in scan context but could not finalize because the workbench did
  not produce `scan-manifest.json`.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Role Findings

Role: `qa-engineer-agent`

Disposition: FIXED

Commit: `a4e06d845`

Evidence: The QA pass found that `promote` could read a modified
`candidate.patch` after validation/approval and still apply it if the changed
path list matched. Commit `a4e06d845` adds promote-time patch fingerprint and
changed-path rechecks in `scripts/orchestration/creative_code_pr_promotion.py`
and regression coverage in
`tests/test_creative_code_pr_promotion.py::test_promote_rejects_stale_patch_file_before_mutation`.

Disposition: FIXED

Commit: `a4e06d845`

Evidence: The QA pass found validation and approval artifacts were not fully
cross-bound to the current plan. Commit `a4e06d845` adds
`_require_validation_matches_plan()` and
`_require_approval_matches_plan_and_validation()` and covers mismatched
artifacts in
`tests/test_creative_code_pr_promotion.py::test_approval_rejects_validation_artifact_cross_mismatch`
and
`tests/test_creative_code_pr_promotion.py::test_promote_rejects_approval_artifact_cross_mismatch`.

Disposition: FIXED

Commit: `a4e06d845`

Evidence: The QA pass found `plan` did not derive changed paths from the patch
itself. Commit `a4e06d845` adds `_patch_changed_paths()` and rejects mismatch
in
`tests/test_creative_code_pr_promotion.py::test_plan_rejects_patch_changed_paths_mismatch`.

Role: `bug-hunter`

Disposition: FIXED

Commit: `01dbc95c7`

Evidence: The bug-hunter pass found promotion commits were not reliably
human-authored while receipts always claimed `human_commit_author=true`.
Commit `01dbc95c7` resolves and verifies a human Git identity before push and
adds
`tests/test_creative_code_pr_promotion.py::test_promote_rejects_non_human_git_identity_before_mutation`.

Disposition: FIXED

Commit: `01dbc95c7`

Evidence: The bug-hunter pass found existing receipt replay returned before
binding to the current plan, validation, and approval chain. Commit
`01dbc95c7` validates existing receipts against current artifact fingerprints,
approval id, source result, patch, branch, and approver, with coverage in
`tests/test_creative_code_pr_promotion.py::test_promote_rejects_stale_receipt_replay`.

Disposition: FIXED

Commit: `59a2e5daf`

Evidence: The bug-hunter pass found branch absence was only a precheck. Commit
`01dbc95c7` added the final branch absence recheck and new-branch push result
validation; commit `59a2e5daf` removed the temporary force-style lease and kept
the invariant as a non-force push plus readback guard. Coverage:
`tests/test_creative_code_pr_promotion.py::test_promote_rejects_branch_that_appears_before_push`
and `tests/test_creative_code_pr_promotion.py::test_git_transport_contains_no_force_push_flag`.

Role: `security-auditor`

Disposition: FIXED

Commit: `59a2e5daf`

Evidence: The security-auditor pass found the promotion path still used
`--force-with-lease`, conflicting with the no-force-push policy. Commit
`59a2e5daf` removes the flag from `GitTransport.push_new_branch()`, updates the
contract wording, and adds
`tests/test_creative_code_pr_promotion.py::test_git_transport_contains_no_force_push_flag`.

Disposition: FIXED

Commit: `59a2e5daf`

Evidence: The security-auditor pass found partial receipts could still claim
human authorship when commit identity verification failed after `commit_sha`
was populated. Commit `59a2e5daf` tracks `commit_identity_verified` and writes
partial receipts only after identity verification succeeds, with coverage in
`tests/test_creative_code_pr_promotion.py::test_promote_identity_verification_failure_writes_no_receipt_or_remote_mutation`.

## Codex Security Evidence

Codex Security scan attempt: `4b426d60-396b-4688-8433-f11260cb088a`

Disposition: DEFERRED

Backlog: Current-head merge readiness remains unchecked in this artifact.

Evidence: The Codex Security workspace opened in diff mode for
`8625cc178bfc757bf603d51b88c3930a83db00d3..59a2e5daf40ddaa9df985860c73e5b72059c6e1d`
and reported zero findings in scan context. Finalization via
`complete_codex_security_scan` could not complete because the workbench did not
produce `scan-manifest.json`. Local security sweep found no active forbidden
authority paths; matches were limited to denylist documentation, tests, and
explicit token-env removal.

Reason: This is tooling evidence, not merge-readiness evidence. A finalized
Codex Security scan or explicit human disposition is still required before any
readiness claim.

## PulsePlate PR Review

Review: `pulseplate-pr-review`

Disposition: FIXED

Evidence: The dry-run report flagged missing fixed-mapping artifact for PR
`#2030`. This file is the canonical fixed-mapping artifact for PR `#2030` and
records role findings, dispositions, validation evidence, and readiness
deferrals.

Disposition: NOT-A-BUG

Evidence: The dry-run report flagged a large-diff advisory note for 4300
changed lines above the 800-line review-risk threshold. The split rationale is
intentional: PR-3 is a single authority-opening tooling slice where contracts,
schemas, implementation, docs, and tests must stay atomic to avoid policy/code
drift. The PR remains within the declared file scope and uses focused local
gates plus current-head CI before any readiness claim.

## Premortem Closure

Disposition: FIXED

Evidence:

- `make validate-changed` false-green risk was closed by running focused tests
  before staging and then rerunning `make validate-changed` after commits; it
  selected `tests/test_creative_code_pr_promotion.py`.
- Authority-creep risks were closed by strict schemas, GitHub command
  denylists, non-draft-only plan authority, no review/thread/merge paths, and
  tests covering forbidden GitHub command shapes.
- PR body and receipt leakage risks were closed by bounded body rendering,
  public-text leak rejection, and tests excluding raw patch, prompt, reasoning,
  secret-shaped strings, and local absolute paths.
- PR-2 lineage risks were closed by validating request/result/bundle/variant
  lineage, patch metadata, patch fingerprint, patch-derived paths, and
  cleanup/admission proofs.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/results/creative_code_pr3_oracle_result.json`

Mode: `oracle_only_governance_reviewer`

Result: accepted, `failure_class=null`, `mutated_paths=[]`,
`shared_tree_untouched=true`, `coauthor_required=true`.

The accepted oracle-only result shaped the PR-3 validation and commit decision.
Commit `1a93ca062` includes the canonical co-author trailer.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_experiment_runner_identity.py`
- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python -m pytest -q tests/test_creative_code_pr_promotion.py tests/test_creative_code_patch_builder.py tests/test_experiment_runner.py tests/test_experiment_runner_identity_policy.py tests/test_repo_policy_guards.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: push hooks, including changed-file mypy, pip-audit, backend pre-push
  pytest, full-repo Bandit, and docker build test.
- PASS: `python3 scripts/orchestration/pr_review_context.py --pr 2030 --output /tmp/pulseplate_pr_2030_review_context.json`
- PASS: `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_2030_review_context.json --format json`
- PASS: `python3 scripts/ci/check_pr_body_phase2_gates.py --event-path /tmp/pr2030_event.json` after refreshing the live PR body mirror.

## Machine-Heavy Deferral

Full local `make verify` was not run per operator request. This PR uses the
machine-heavy exception path: local focused gates passed, and current-head CI
must provide the heavy parity signal before any merge-readiness claim.

## Readiness Status

Merge readiness is not claimed. Current-head CI, finalized security/review
evidence, any external bot findings, review-thread disposition, and the strict
merge-readiness wrapper are still required before readiness language.
