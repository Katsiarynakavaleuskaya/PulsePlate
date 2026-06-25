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
- `3e703c0d8` - fix post-open QA findings: reject executable new candidate
  files, align request/result schema forbidden path policy with the Python
  validator, and add deterministic regression coverage.
- `35936558a` - fix post-open bug-hunter findings: verify `candidate.patch`
  against stored metadata before evaluation, reject stale prepare run
  directories, align result schema failure/authority constraints with the
  Python validator, and resolve executor/git binaries to absolute executable
  paths.
- `b656cf801` - fix post-open security-auditor finding by replacing broad Git
  subprocess environment inheritance with an allowlisted, secret-stripped,
  normalized environment and focused regression coverage.

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

## Post-open Role Findings

- No actionable GitHub review-thread comments existed when this artifact was
  updated.
- Post-open `qa-engineer-agent`: executable new allowlisted files could bypass
  the PR-2 patch policy. Disposition: FIXED. Commit: `3e703c0d8`. Evidence:
  `scripts/orchestration/creative_code_patch_builder.py`,
  `tests/test_creative_code_patch_builder.py::test_patch_metadata_rejects_new_executable_file`.
- Post-open `qa-engineer-agent`: request/result schemas could drift from the
  Python validator forbidden-path policy and request schema contradicted the
  allowed-new-only validator path. Disposition: FIXED. Commit: `3e703c0d8`.
  Evidence:
  `docs/orchestration/contracts/creative_code_patch_request.v1.schema.json`,
  `docs/orchestration/contracts/creative_code_patch_result.v1.schema.json`,
  `tests/test_creative_code_patch_builder.py::test_patch_path_schemas_match_validator_for_forbidden_surfaces`,
  and
  `tests/test_creative_code_patch_builder.py::test_patch_request_allows_allowed_new_only_requests`.
- Post-open `bug-hunter`: stale or tampered `candidate.patch` could be
  evaluated with old patch metadata. Disposition: FIXED. Commit:
  `35936558a`. Evidence:
  `scripts/orchestration/creative_code_patch_builder.py`,
  `tests/test_creative_code_patch_builder.py::test_evaluate_rejects_tampered_candidate_patch`,
  and
  `tests/test_creative_code_patch_builder.py::test_prepare_rejects_non_empty_run_directory`.
- Post-open `bug-hunter`: result schema allowed failure classes and authority
  flags the Python validator rejects. Disposition: FIXED. Commit:
  `35936558a`. Evidence:
  `docs/orchestration/contracts/creative_code_patch_result.v1.schema.json` and
  `tests/test_creative_code_patch_builder.py::test_reference_patch_contracts_validate_and_schema_is_closed`.
- Post-open `bug-hunter`: `codex` and `git` resolvers could return relative
  paths when `PATH` contained relative entries. Disposition: FIXED. Commit:
  `35936558a`. Evidence:
  `scripts/orchestration/creative_code_patch_executor.py`,
  `scripts/orchestration/creative_code_patch_workspace.py`, and
  `tests/test_creative_code_patch_builder.py::test_binary_resolvers_return_absolute_executables_for_relative_path`.
- Post-open `security-auditor`: Git subprocesses inherited almost the entire
  parent environment and could receive local secrets or credential-shaped
  values. Disposition: FIXED. Commit: `b656cf801`. Evidence:
  `scripts/orchestration/creative_code_patch_workspace.py`,
  `scripts/orchestration/experiment_runner.py`,
  `tests/test_creative_code_patch_builder.py::test_git_env_strips_secret_and_parent_state`,
  and
  `tests/test_creative_code_patch_builder.py::test_experiment_runner_uses_sanitized_git_env`.

## Premortem Closure

Premortem closure is recorded in this artifact. The standalone premortem draft
was folded into this parser-safe mapping artifact to keep the final privileged
PR surface within the 15-file hard cap while preserving the finding/fix
evidence below.

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
  `tests/test_creative_code_patch_builder.py::test_patch_metadata_rejects_new_executable_file`,
  and
  `tests/test_creative_code_patch_builder.py::test_patch_metadata_rejects_symlink_mode_change`.
- Runner-evidence confusion is closed by `scripts/AGENTS.md`,
  `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`, and
  `docs/orchestration/contracts/CREATIVE_CODE_PATCH_BUILDER_CONTRACT.md`.
- The `make validate-changed` false-green risk is closed by rerunning
  `make validate-changed` after commit; it selected
  `tests/test_creative_code_patch_builder.py` and ran 18 tests.

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
