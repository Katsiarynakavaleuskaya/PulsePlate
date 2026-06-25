# PR #2022 - Fixed in Commit Mapping SoT

## Scope

PR #2022 implements PR-2 of the governed creative-code execution train: a
sandboxed local candidate-patch builder that can generate and evaluate isolated
patches without shared repository writes, branch/PR automation, review-thread
resolution, merge, promotion, product runtime AI, OpenAPI/client, frontend, iOS,
DB, dependency, Slack, or GitHub authority.

## Implementation Commits

- `34fa5e73c` - initial generated detect-secrets baseline update for reference
  JSON examples; superseded by the scope-cap fix so no final `.secrets.baseline`
  delta remains.
- `7837abd5f` - add PR-2 patch-builder contracts, local workspace/executor/
  builder CLIs, strict patch validation, sanitized Experiment Runner candidate
  evaluation, docs, ledger, premortem, and focused tests.
- `9fc5499fa` - remove tracked request/result example JSON and the generated
  detect-secrets baseline delta so the final privileged orchestration PR
  surface stays within the CI hard cap.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial PR open: no GitHub review threads existed at artifact creation.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` review
  lane is still required.
- [ ] Codex Security diff scan / finding discovery is still required.
- [ ] CodeRabbit, Sourcery, Cubic, and human review comments must be fixed or
  dispositioned before merge readiness.
- [ ] Current-head CI and strict merge-readiness wrapper evidence are still
  required before any merge-readiness claim.

## Fixed in Commit Mapping

- No actionable review comments

## Premortem Closure

Premortem artifact:
`docs/review/PR_CREATIVE_CODE_PATCH_BUILDER_PR2_PREMORTEM.md`.

Disposition: FIXED

Evidence:

- Authority expansion risks are closed by
  `scripts/orchestration/creative_code_patch_contract.py`,
  `docs/orchestration/contracts/CREATIVE_CODE_PATCH_BUILDER_CONTRACT.md`,
  `scripts/AGENTS.md`, and
  `tests/test_creative_code_patch_builder.py::test_reference_patch_contracts_validate_and_schema_is_closed`.
- Codex prompt/output/secret leakage risks are closed by
  `scripts/orchestration/creative_code_patch_executor.py`,
  `scripts/orchestration/creative_code_patch_contract.py`,
  `tests/test_creative_code_patch_builder.py::test_executor_builds_fixed_argv_and_strips_secret_env`,
  and
  `tests/test_creative_code_patch_builder.py::test_evaluate_writes_sanitized_result_without_runner_leaks`.
- Workspace isolation and cleanup risks are closed by
  `scripts/orchestration/creative_code_patch_workspace.py`,
  `scripts/orchestration/creative_code_patch_builder.py`,
  `tests/test_creative_code_patch_builder.py::test_workspace_creates_detached_no_remote_checkout_and_cleanup`,
  and
  `tests/test_creative_code_patch_builder.py::test_cli_prepare_generate_evaluate_cleanup`.
- Patch false-negative risks are closed by
  `scripts/orchestration/creative_code_patch_builder.py`,
  `scripts/orchestration/creative_code_patch_contract.py`,
  `tests/test_creative_code_patch_builder.py::test_patch_metadata_accepts_allowed_modified_file`,
  `tests/test_creative_code_patch_builder.py::test_patch_metadata_rejects_unapproved_untracked_file`,
  and
  `tests/test_creative_code_patch_builder.py::test_patch_metadata_rejects_symlink_mode_change`.
- Runner-evidence confusion is closed by `scripts/AGENTS.md`,
  `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`, and
  `docs/orchestration/contracts/CREATIVE_CODE_PATCH_BUILDER_CONTRACT.md`.
- The `make validate-changed` false-green risk is closed by rerunning
  `make validate-changed` after commit; it selected
  `tests/test_creative_code_patch_builder.py` and ran 11 tests.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/pr2-creative-code-patch-builder-oracle-result.json`

Mode: `oracle_only_governance_reviewer`

Result: accepted, `exp-4561b190580c`, `source_diff_paths_count=15`,
`shared_tree_untouched=true`, `coauthor_required=true`.

The accepted oracle-only result shaped the PR-2 validation and commit decision;
commit `7837abd5f` includes the canonical co-author trailer. The refreshed
final-diff oracle result also shaped the post-scope-cap mapping/PR-body sync.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/904282be7567.json`

Starter: `scripts/orchestration/start_pr_lane.sh`

## Local Validation

- PASS: `python scripts/orchestration/check_preflight.py`
- PASS: `python scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_pr_size_governance.py --base-sha "$(git
  merge-base origin/main HEAD)" --head-sha "$(git rev-parse HEAD)" --body
  "$(gh pr view 2022 --json body -q .body)"` (`Counted files: 15`;
  `PR scope governance: OK (privileged CI/security/workflow policy).`)
- PASS:
  `python -m pytest -q tests/test_creative_code_patch_builder.py tests/test_creative_code_specification.py tests/test_experiment_bootstrap.py tests/test_experiment_runner.py tests/test_codex_ollama_operator_doctor.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py tests/test_repo_policy_guards.py`
- PASS: PR-2 request/result contract validation and `additionalProperties:
  false` schema guards are covered by
  `tests/test_creative_code_patch_builder.py::test_reference_patch_contracts_validate_and_schema_is_closed`.
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during push: changed-file mypy, pip-audit, backend tests, bandit full,
  and docker build test.

## Machine-Heavy Deferral

Full local `make verify` is intentionally deferred per operator request and the
repo machine-heavy exception. This PR must rely on focused local gates plus
current-head CI parity before any merge-readiness claim.

## Merge Readiness

Not claimed. PR #2022 still requires current-head CI, post-open role review,
Codex Security diff scan/finding discovery, `pulseplate-pr-review`, bot review
disposition, fixed mapping sync for any later comments, and strict
`check_merge_ready.py --require-auth` evidence before any merge-readiness claim.
