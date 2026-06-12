# PR 1935 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1935>

## Summary

This PR closes the Trivy publish-gate review findings by moving GHCR publish
behind the fail-closed Trivy image scan and SARIF evidence gates. The publish
job now builds the production image locally for scanning, delays GHCR login and
push until after Trivy/SARIF success, pushes the same scanned tags, derives the
pushed registry digest fail-closed, and uses that digest for GitHub-signed
provenance/SBOM attestations.

## Lane Start Provenance

- Branch: `codex/propose-fix-for-docker-image-scanning-vulnerability`
- PR phase: `post_open_review`
- Worktree: `/Users/katsiaryna_kavaleuskaya/Developer/PulsePlate-pr-1935`
- Current implementation fix commit: `256f2584c7b6fad7141ececdb12dcb02b5807c8b`
- Packet: `artifacts/orchestration/task_packets/1020d9be96b8.json`
- Bootstrap packets: `artifacts/orchestration/task_packets/fc4793de310d.json`,
  `artifacts/orchestration/task_packets/cd3a609da9dd.json`,
  `artifacts/orchestration/task_packets/1020d9be96b8.json`
- Final packet used for role dispatch:
  `artifacts/orchestration/task_packets/1020d9be96b8.json`
- Machine-heavy exception: operator approved excluding full local `make verify`
  for this CI/tooling PR. Focused PR-scoped local gates plus current-head CI
  parity are the required proof path.

## Scope

IN:

- `.github/workflows/build.yml`
- `.github/workflows/trivy.yml`
- `tests/test_docker_workflow_build_path_contract.py`
- `tests/test_ci_workflow_pr_size_governance_contract.py`
- `tests/test_python_supply_chain_controls.py`
- Docker/provenance/security/governance documentation that names this workflow
  contract.
- `docs/review/PR_1935_FIXED_MAPPING.md`

OUT:

- Backend API or OpenAPI behavior.
- Web or iOS runtime behavior.
- Docker base-image changes, dependency-profile changes, Dagger changes, or
  multi-arch restoration.
- Full local `make verify`; deferred under the operator-approved machine-heavy
  exception and replaced by narrow local gates plus current-head CI.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [ ] Review threads resolved after this artifact and PR body mirror pass.
- [ ] Current-head CI and strict merge-readiness wrapper pass after push.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1935#discussion_r3386545107 -> 256f2584c7b6fad7141ececdb12dcb02b5807c8b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1935#discussion_r3386545114 -> 256f2584c7b6fad7141ececdb12dcb02b5807c8b
Disposition: FIXED
Commit: 256f2584c7b6fad7141ececdb12dcb02b5807c8b
Evidence: `.github/workflows/build.yml`; `tests/test_docker_workflow_build_path_contract.py::test_publish_image_scan_fails_closed`; `tests/test_ci_workflow_pr_size_governance_contract.py::test_node24_checkout_and_docker_action_pins_use_verified_commit_shas`.
Reason: Sourcery's severity/fail-closed findings are fixed by setting the publish image scan to `exit-code: '1'`, keeping `severity: CRITICAL,HIGH`, preserving SARIF output and the missing-SARIF gate, and removing `continue-on-error` from the publish scan contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1935#discussion_r3386555609 -> 256f2584c7b6fad7141ececdb12dcb02b5807c8b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1935#discussion_r3386599926 -> 256f2584c7b6fad7141ececdb12dcb02b5807c8b
Disposition: FIXED
Commit: 256f2584c7b6fad7141ececdb12dcb02b5807c8b
Evidence: `.github/workflows/build.yml`; `tests/test_docker_workflow_build_path_contract.py::test_publish_image_scan_fails_closed`; `tests/test_python_supply_chain_controls.py::test_push_to_registry_workflows_restore_signed_attestations_on_publish_lanes`.
Reason: Codex and Cubic both identified the previous publish-after-push gap; the publish job now builds a local production image for Trivy, runs the fail-closed scan and SARIF upload gate before GHCR login, pushes the same scanned tags only after those gates pass, extracts the pushed registry digest fail-closed, and binds provenance/SBOM attestation plus verification to that digest.

## Bot Review Summary

- Sourcery: FIXED in commit `256f2584c7b6fad7141ececdb12dcb02b5807c8b`.
- Codex review: FIXED in commit `256f2584c7b6fad7141ececdb12dcb02b5807c8b`.
- Cubic: FIXED in commit `256f2584c7b6fad7141ececdb12dcb02b5807c8b`.
- CodeRabbit and Codecov: no separate actionable finding has been used as
  readiness evidence; current-head CI and bot disposition gates remain required
  after push.

## Role Dispatch Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review`
- Declared final role order executed against packet `1020d9be96b8`:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`.
- Mandatory post-open review stack executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`, followed by Codex
  Security diff scan / finding discovery.
- `agent-coordinator`: kept scope on the existing PR branch, current
  `origin/main` merge, Trivy publish-gate closeout, and narrow docs/tests.
- `qa-engineer-agent`: accepted the local scan-before-push contract and kept
  mapping artifact, unresolved threads, current-head CI, and full `make verify`
  deferral documentation as remaining governance gates.
- `bug-hunter`: no code blocker; recommended fixed-string digest lookup and
  current-head publish CI proof for the real registry path.
- `security-auditor`: no security blocker; confirmed private package index
  stays in BuildKit `secret-envs`, GHCR login occurs after Trivy/SARIF gates,
  and digest extraction fails closed before attestations.
- `cursor-specialist-agent`: identified stale docs wording around build publish
  provenance and trivy lane classification; fixed in the implementation commit.
- `web-research-agent`: no external source required; identified stale local
  evidence anchors, fixed in the implementation commit.

## Premortem Finding Closure

- `PM-1935-001` Publish still writes to GHCR before scan.
  Disposition: FIXED.
  Evidence: commit `256f2584c7b6fad7141ececdb12dcb02b5807c8b` moves GHCR login
  and push after Trivy, missing-SARIF, and SARIF upload steps; workflow tests
  assert this ordering.
- `PM-1935-002` Scan-before-push loses provenance/SBOM digest binding.
  Disposition: FIXED.
  Evidence: commit `256f2584c7b6fad7141ececdb12dcb02b5807c8b` adds
  `Push scanned Docker image`, extracts the pushed digest, and keeps
  provenance/SBOM attestation plus verification bound to
  `steps.docker-build-push.outputs.digest`.
- `PM-1935-003` Private package-index values leak through provenance/build args.
  Disposition: FIXED.
  Evidence: commit `256f2584c7b6fad7141ececdb12dcb02b5807c8b` keeps publish
  scan inputs in `secret-envs`, uses `provenance: false` for the load-only scan
  build, and preserves CD pushed-image BuildKit lanes at `provenance: mode=min`.
- `PM-1935-004` The full local `make verify` deferral is later misreported as
  green.
  Disposition: FIXED.
  Evidence: this artifact and the PR body mirror document that full local
  `make verify` was not run under the operator-approved machine-heavy exception.
- `PM-1935-005` Local static checks cannot prove the real GHCR push/digest path.
  Disposition: NOT-A-BUG.
  Evidence: local gates validate workflow structure; current-head GitHub CI is
  explicitly required before merge readiness.
  Reason: the real publish path needs GitHub-hosted registry credentials and is
  intentionally proven remotely, not by local `make verify`.
- Decision: `proceed with changes`, subject to current-head CI, review-thread
  disposition, strict merge-readiness wrapper, and mandatory wait-window.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/artifacts/orchestration/experiments/pr-1935-trivy-publish-gate-oracle-packet.json`
- Artifact: `artifacts/orchestration/experiments/results/pr-1935-trivy-publish-gate-oracle-result.json`
- Experiment ID: `exp-ee3ce453b162`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Source diff applied in isolated checkout: `true`
- Shared tree untouched: `true`
- Oracles:
  - `python -m pytest -q tests/test_docker_workflow_build_path_contract.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_python_supply_chain_controls.py::test_production_target_docker_workflows_use_runtime_requirements_profile tests/test_python_supply_chain_controls.py::test_provenance_enabled_docker_builds_keep_private_index_out_of_build_args tests/test_python_supply_chain_controls.py::test_pushed_docker_builds_do_not_use_max_provenance_with_secret_index_args tests/test_python_supply_chain_controls.py::test_push_to_registry_workflows_restore_signed_attestations_on_publish_lanes`: return code `0`.
  - `git diff --check`: return code `0`.
- Contribution: `fixed_mapping_review`.
- Co-author required: `true`; implementation and mapping commits use
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Codex Security Diff Scan / Finding Discovery

- Skill: `codex-security:security-diff-scan`.
- Scan directory:
  `/tmp/codex-security-scans/PulsePlate-pr-1935/b715b350_20260612T1418Z`
- Markdown report:
  `/tmp/codex-security-scans/PulsePlate-pr-1935/b715b350_20260612T1418Z/report.md`
- HTML report:
  `/tmp/codex-security-scans/PulsePlate-pr-1935/b715b350_20260612T1418Z/report.html`
- Worklist:
  `/tmp/codex-security-scans/PulsePlate-pr-1935/b715b350_20260612T1418Z/artifacts/02_discovery/deep_review_input.csv`
- Work ledger:
  `/tmp/codex-security-scans/PulsePlate-pr-1935/b715b350_20260612T1418Z/artifacts/02_discovery/work_ledger.jsonl`
- Result: NOT-A-BUG / no reportable findings.
- Evidence: report format validation passed; HTML report rendered; 10
  diff-scoped workflow/doc/test surfaces were reviewed with 0 raw candidates and
  0 deduped candidates.

## PulsePlate PR Review

- Context: `/tmp/pr1935_pr_review_context.json`
- Markdown report: `/tmp/pr1935_pr_review_report.md`
- JSON report: `/tmp/pr1935_pr_review_report.json`
- Result: NOT-A-BUG / one advisory `large-diff-risk` planning note.
- Evidence: the report reviewed 11 files and emitted one `note` finding because
  the diff contains 641 changed lines, above its advisory threshold.
- Reason: this is the existing PR closeout slice, not a new broad feature PR;
  most added lines are the required `docs/review/PR_1935_FIXED_MAPPING.md`
  governance artifact, and targeted deterministic gates already passed.
- Gate: `make validate-changed` passed; focused workflow/supply-chain tests and
  full pre-commit also passed before this mapping update.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `git diff --check`
- PASS: focused pytest:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_docker_workflow_build_path_contract.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_python_supply_chain_controls.py::test_production_target_docker_workflows_use_runtime_requirements_profile tests/test_python_supply_chain_controls.py::test_provenance_enabled_docker_builds_keep_private_index_out_of_build_args tests/test_python_supply_chain_controls.py::test_pushed_docker_builds_do_not_use_max_provenance_with_secret_index_args tests/test_python_supply_chain_controls.py::test_push_to_registry_workflows_restore_signed_attestations_on_publish_lanes tests/test_build_equivalence_evidence_workflow.py::test_docker_build_workflow_publishes_governed_artifact_digest_source tests/test_release_manifest_evidence_workflow.py` (`50 passed`).
- PASS: `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` (`7 passed` in the changed Python test selection).
- PASS: `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python PRE_COMMIT_HOME=/tmp/pre-commit-pr1935 pre-commit run --all-files`.
- PASS: `python3 scripts/orchestration/pr_review_context.py --pr 1935 --repo Katsiarynakavaleuskaya/PulsePlate --repo-root . --base origin/main --head HEAD --output /tmp/pr1935_pr_review_context.json`.
- PASS: `python3 scripts/orchestration/pr_review_report.py --context /tmp/pr1935_pr_review_context.json --format markdown --packet-id 1020d9be96b8 --packet-path artifacts/orchestration/task_packets/1020d9be96b8.json --output /tmp/pr1935_pr_review_report.md`.
- PASS: `python3 scripts/orchestration/pr_review_report.py --context /tmp/pr1935_pr_review_context.json --format json --packet-id 1020d9be96b8 --packet-path artifacts/orchestration/task_packets/1020d9be96b8.json --output /tmp/pr1935_pr_review_report.json`.
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_pr_review_report.py tests/test_pr_review_context.py` (`13 passed`).
- PASS: `git diff --cached --check` before implementation commit.
- PASS: commit hooks before implementation commit, including workflow checks,
  Black, Ruff, changed-file backend tests, and commitizen.
- NOT RUN: full local `make verify`; intentionally deferred under the
  operator-approved machine-heavy exception.

## Deferred / Follow-ups

None for this PR. Current-head CI still must prove the real GHCR
push/digest/attestation path before merge readiness.

## Merge Readiness

- [x] Real implementation fix commit landed after the review comments.
- [x] Canonical fixed-mapping artifact exists.
- [x] Focused local gates passed before the implementation commit.
- [x] Full local `make verify` deferral is documented.
- [ ] Rerun `pulseplate-pr-review` after this artifact commit.
- [ ] Refresh PR body mirror from this artifact.
- [ ] Push the current PR branch.
- [ ] Resolve the four mapped review threads only after body/mapping evidence
  passes.
- [ ] `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1935 --body "$(gh pr view 1935 --repo Katsiarynakavaleuskaya/PulsePlate --json body --jq .body)"` passes.
- [ ] `GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1935 --require-auth` passes.
- [ ] `GH_TOKEN="$(gh auth token)" GITHUB_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_merge_ready.py --pr-number 1935 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth` passes on current head.
- [ ] Current-head required CI parity is green with no pending required jobs.
- [ ] No unresolved review threads remain.
- [ ] No actionable bot comments remain unmapped or undispositioned.
- [ ] Mandatory wait-window after latest bot/review activity has elapsed.
