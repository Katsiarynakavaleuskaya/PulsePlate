# PR #2063 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2063

Branch: `codex/experiment-runner-pr-creative-context`

## Summary

This PR adds a local, read-only Experiment Runner PR creative-context layer for
eligible orchestration surfaces. It emits sanitized context, hypothesis,
routing, oracle attachment, consumption summary, and approval-reservation
artifacts without granting patch, branch, PR, workflow, provider, product
runtime, thread-resolution, fixed-mapping, merge, or readiness authority.

## Scope Boundary

- In scope: local artifact contract, CLI, schemas, premortem, task-bootstrap
  metadata, rendered start prompt text, scripts-scoped AGENTS guidance, backlog
  tracking, and focused tests.
- Out of scope: `.github/workflows/**`, automatic PR attachment, provider calls,
  product runtime calls, GitHub App mutation, Slack mutation, comments, thread
  resolution, branch writes by the runner, PR-2 patch generation, and merge
  readiness claims.

## Privileged Scope Exception

- operator approval: approved for the combined Experiment Runner creative-context
  contract slice requested by the operator.
- privileged scope exception: approved for the local orchestration/security
  governance scope over the privileged target file cap.
- Scope note: splitting runtime contract, matching schemas, docs, task-bootstrap
  guard metadata, and tests would leave the new authority boundary partially
  machine-visible and weaken the QA/security proof for this PR.
- Trusted labels required on PR #2063: `scope/operator-approved`,
  `scope/privileged-approved`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [x] `pulseplate-pr-review` completed.
- [ ] CodeRabbit actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Sourcery actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Cubic actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Role-Agent Finding Dispositions

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Commit: 437a01405eb7e8205d8d704290e8bdccc3ae8179
Evidence: `docs/orchestration/contracts/*creative*.v1.schema.json` and
`docs/orchestration/contracts/experiment_runner_pr_oracle_attachment.v1.schema.json`
now require the exact runtime authority key set with `additionalProperties:
false`. Regression coverage is in
`tests/test_experiment_runner_pr_creative_context.py::test_schema_authority_definitions_match_runtime_authority`.

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Commit: 437a01405eb7e8205d8d704290e8bdccc3ae8179
Evidence:
`docs/orchestration/contracts/creative_hypothesis_packet.v1.schema.json`
now encodes generated/no-action status coupling: generated packets require
3-5 hypotheses and a concrete non-doc target, while `no_creative_action`
requires zero hypotheses. Regression coverage is in
`tests/test_experiment_runner_pr_creative_context.py::test_hypothesis_packet_schema_encodes_generated_and_no_action_guards`.

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Evidence: This artifact fixes the missing canonical mapping artifact that made
`PR Body Phase2 gates` and `Merge readiness gate` fail after PR open. The PR
body mirror is updated separately and does not claim merge readiness.

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Evidence: The PR body now records `operator approval: approved` and
`privileged scope exception: approved`, and PR #2063 carries trusted labels
`scope/operator-approved` and `scope/privileged-approved`, so the coherent
20-file privileged orchestration/security-governance slice is explicitly
approved instead of bypassing the scope guard.

Disposition: FIXED
Source: post-open `bug-hunter`
Commit: 1f60046148b06d4cddf8cc438509b935cfbd9c8e
Evidence:
`scripts/orchestration/experiment_runner_pr_creative_context_contract.py` now
rejects rejected/deferred approval artifacts that try to create PR-1
specifications, requires approved PR-1 handoffs to stay on creative-context
orchestration surfaces, and rejects product-runtime targets such as
`app/main.py`. Regression coverage is in
`tests/test_experiment_runner_pr_creative_context.py::test_approval_rejects_rejected_or_deferred_pr1_handoff`
and
`tests/test_experiment_runner_pr_creative_context.py::test_approval_rejects_product_runtime_pr1_targets`.

Disposition: FIXED
Source: post-open `bug-hunter`
Commit: 1f60046148b06d4cddf8cc438509b935cfbd9c8e
Evidence:
`scripts/orchestration/experiment_runner_pr_creative_context_contract.py` now
checks that agent consumption summaries use a routing artifact whose source
packet id, packet fingerprint, and routed hypothesis ids match the supplied
hypothesis packet. Regression coverage is in
`tests/test_experiment_runner_pr_creative_context.py::test_consumption_summary_rejects_unrelated_routing_packet`
and
`tests/test_experiment_runner_pr_creative_context.py::test_consumption_summary_rejects_missing_routing_rows_for_generated_packet`.

Disposition: FIXED
Source: post-open `bug-hunter`
Commit: 1f60046148b06d4cddf8cc438509b935cfbd9c8e
Evidence:
`docs/orchestration/contracts/creative_protocol_context_map.v1.schema.json` and
`docs/orchestration/contracts/creative_hypothesis_packet.v1.schema.json` now
pin `reason_code` to the runtime enum and reject `artifacts/` values through
their repo-path definitions; approval schema now encodes the decision state
machine. Regression coverage is in
`tests/test_experiment_runner_pr_creative_context.py::test_context_and_packet_schemas_pin_reason_codes_and_artifact_path_ban`
and
`tests/test_experiment_runner_pr_creative_context.py::test_approval_schema_encodes_decision_state_machine`.

Disposition: FIXED
Source: post-open `security-auditor`
Commit: b38ed557e8252a5f9b43404983c3555d66bf1b1d
Evidence:
`docs/orchestration/contracts/creative_protocol_context_map.v1.schema.json` and
`docs/orchestration/contracts/experiment_runner_pr_oracle_attachment.v1.schema.json`
now add segment-level traversal bans to `artifact_ref`, preventing
`artifacts/orchestration/experiments/../...` references from passing
schema-only validation. Regression coverage is in
`tests/test_experiment_runner_pr_creative_context.py::test_artifact_ref_schemas_reject_traversal_segments`.

Disposition: FIXED
Source: post-open `security-auditor`
Commit: b38ed557e8252a5f9b43404983c3555d66bf1b1d
Evidence: This mapping artifact no longer stores machine-local absolute
interpreter paths; command evidence now uses the repo-relative
`scripts/hooks/repo_python.sh` resolver form required by
`docs/ENGINEERING_LESSONS.md`.

Disposition: FIXED
Source: post-open `security-auditor`
Commit: b38ed557e8252a5f9b43404983c3555d66bf1b1d
Evidence:
`scripts/orchestration/experiment_runner_pr_creative_context_contract.py` now
requires accepted oracle attachments to include `result_fingerprint`, and
`docs/orchestration/contracts/experiment_runner_pr_oracle_attachment.v1.schema.json`
adds an accepted-status schema guard requiring both `result_ref` and
`result_fingerprint`. Regression coverage is in
`tests/test_experiment_runner_pr_creative_context.py::test_accepted_oracle_attachment_requires_fingerprint`
and
`tests/test_experiment_runner_pr_creative_context.py::test_oracle_attachment_schema_requires_fingerprint_for_accepted_status`.

Disposition: NOT-A-BUG
Source: Codex Security diff scan / finding discovery
Evidence: Codex Security scan `85f14aea-d5d0-494d-9e78-218a37eb5325`
completed for head `3956e6d09c1a481b091e130cf727ca80bc65191d` with
0 reportable findings and 4/4 diff review rows closed. Reviewed surfaces
included CLI output confinement, contract sanitization and artifact refs,
oracle/approval/routing/summary binding, task-bootstrap single-pass governance,
and supporting schema/doc/test surfaces.

Disposition: NOT-A-BUG
Source: `pulseplate-pr-review`
Evidence: The dry-run report on PR head
`5675d24cdbeedff55953cc395438c3ba60b44f04c` reported no deterministic
architecture, security, QA, or source-degradation findings. Its only advisory
finding was the large-diff review-risk note. The broader coherent slice is
operator-approved and explicitly covered by trusted labels
`scope/operator-approved` and `scope/privileged-approved`, the split rationale
in this mapping artifact, focused tests, `make validate-changed`,
`pre-commit run --all-files`, and push-time pre-push hooks.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-faf9d17cb8f9.json`
- Experiment ID: `exp-faf9d17cb8f9`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Source diff applied: true
- Shared tree untouched: true
- Oracles: 3/3 passed
- Co-author required: true

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/353d0c92de04.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_experiment_runner_pr_creative_context.py tests/test_task_bootstrap.py tests/test_render_codex_start_prompt.py`
- PASS before PR open:
  `pytest -q tests/test_experiment_runner_pr_creative_context.py tests/test_task_bootstrap.py tests/test_render_codex_start_prompt.py tests/test_creative_code_review_disposition.py tests/test_creative_code_private_pilot_loop.py`
- PASS before PR open: `make validate-changed`
- PASS before PR open: `pre-commit run --all-files`
- PASS before PR open: push pre-push hooks, including changed-file mypy,
  `pip-audit`, backend pre-push pytest, full-repo Bandit, and Docker build test.
- PASS: Experiment Runner oracle-only evidence
  `artifacts/orchestration/experiments/results/exp-faf9d17cb8f9.json`.
- PASS after bug-hunter fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_experiment_runner_pr_creative_context.py tests/test_task_bootstrap.py tests/test_render_codex_start_prompt.py tests/test_creative_code_review_disposition.py tests/test_creative_code_private_pilot_loop.py`.
- PASS after bug-hunter fixes: JSON parse check for the touched creative-context
  schema files.
- PASS after security-auditor fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_experiment_runner_pr_creative_context.py tests/test_task_bootstrap.py tests/test_render_codex_start_prompt.py tests/test_creative_code_review_disposition.py tests/test_creative_code_private_pilot_loop.py`.
- PASS: Codex Security scan
  `85f14aea-d5d0-494d-9e78-218a37eb5325` completed with 0 findings and 4/4
  diff review rows closed.
- PASS: `pulseplate-pr-review` dry-run report on PR head
  `5675d24cdbeedff55953cc395438c3ba60b44f04c` had no source-degradation
  warnings and no deterministic architecture, security, or QA findings.

## Merge Readiness

Not claimed. This artifact records current dispositions and local evidence only.
Bot review disposition, current-head CI, and strict merge-readiness checks
remain required before any readiness language.
