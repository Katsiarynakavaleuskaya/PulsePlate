# PR 2015 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2015

Branch: `codex/creative-code-specification-pr1`

## Summary

PR-1 implements the governed creative-code specification pipeline as a local
control-plane layer. It converts a validated PR-0 `CreativeCodeCandidatePacket`
into deterministic implementation specifications, skeptic reviews, synthesis,
telemetry summary, and fingerprint-only rejection records.

The PR remains specification-only. It adds no candidate patches, provider/model
calls, network calls, product runtime, OpenAPI/client/frontend/iOS changes,
GitHub/Slack authority, semantic-cache use, review-thread authority,
merge-readiness authority, or repo-write authority in generated artifacts.

## Scope

- Add `CreativeCodeSpecificationBundle` contract docs, schema, reference JSON,
  and validator.
- Add pure PR-1 validation/admission/synthesis in
  `scripts/orchestration/creative_code_specification.py`.
- Add safe local `prepare` / `finalize` artifact I/O in
  `scripts/orchestration/creative_code_spec_pipeline.py`.
- Add fingerprint-only rejected-variant records in
  `scripts/orchestration/creative_code_rejection_index.py`.
- Add focused tests for schema parity, duplicate keys, unsafe paths/content,
  authority flags, deterministic replay, all-rejected state, selected-rejected
  bans, symlinked artifact rejection, and fingerprint-only rejection records.
- Update narrow orchestration/backlog handoff text.
- Add premortem artifact with all findings closed.

## Out Of Scope

No `app/**`, OpenAPI/client/frontend/iOS, DB migration, provider/model call,
network call, semantic-cache activation, GitHub/Slack operation, candidate patch,
branch/PR automation, review-thread resolution, merge automation, release
automation, or product-runtime behavior.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/6bb7ee0c5548.json`
- Worktree:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/creative-code-specification-pr1`
- Branch: `codex/creative-code-specification-pr1`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Runtime dispatch manifest:
  `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/6bb7ee0c5548.json --mode runtime --implementation-owner security-auditor --pretty`
- Pre-open role order executed:
  `agent-coordinator -> ai-innovation-specialist -> architecture-specialist -> security-auditor -> qa-engineer-agent -> logic-agent -> epistemology-discovery-agent -> bug-hunter -> cursor-specialist-agent`
- Packet creation was treated as provenance only, not role execution.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: role dispatch manifest command listed above.
- PASS: `python -m scripts.orchestration.creative_code_contract --validate docs/orchestration/contracts/creative_code_candidate.v1.json`
- PASS: `python -m scripts.orchestration.creative_code_specification --validate docs/orchestration/contracts/creative_code_specification.v1.json`
- PASS: `python -m pytest -q tests/test_creative_code_contract.py tests/test_creative_code_specification.py tests/test_context_pack_compression.py tests/core/evidence/test_fingerprints.py`
- PASS after commit: `make validate-changed` selected
  `tests/test_creative_code_specification.py`.
- PASS: `pre-commit run --all-files`
- PASS on push hook: changed-files mypy, backend pytest, full-repo Bandit, and
  Docker build test.

Full local `make verify` was not run. The operator explicitly requested narrow
validation for this PR-1 creative-code specification lane because the full local
suite is too large for this machine. Merge readiness requires the focused local
gates above, current-head GitHub CI parity, review-thread disposition,
post-open role passes, Codex Security when available, `pulseplate-pr-review`,
strict merge-readiness with auth, and the final wait-window.

## Premortem Findings

Artifact: `docs/review/PR_CREATIVE_CODE_SPECIFICATION_PR1_PREMORTEM.md`

Decision: `proceed`

Disposition: FIXED

Finding: specification output could be mistaken for patch/repo-write authority.

Commit: `977b48d2208453ae4c3a1eb6bb0c61ed50f717af`

Evidence: `scripts/orchestration/creative_code_specification.py`,
`docs/orchestration/contracts/CREATIVE_CODE_SPECIFICATION_CONTRACT.md`,
`tests/test_creative_code_specification.py::test_authority_flags_fail_closed`,
and
`tests/test_creative_code_specification.py::test_unsafe_variant_text_is_rejected`.

Disposition: FIXED

Finding: local CLI could leak or write outside the artifact boundary.

Commit: `977b48d2208453ae4c3a1eb6bb0c61ed50f717af`

Evidence: `scripts/orchestration/creative_code_spec_pipeline.py`,
`tests/test_creative_code_specification.py::test_pipeline_rejects_symlinked_artifact_directory`,
and
`tests/test_creative_code_specification.py::test_pipeline_prepare_and_finalize_write_valid_bundle`.

Disposition: FIXED

Finding: rejected variants could store raw prompts, secrets, candidate text, or
local paths.

Commit: `977b48d2208453ae4c3a1eb6bb0c61ed50f717af`

Evidence: `scripts/orchestration/creative_code_rejection_index.py`,
`tests/test_creative_code_specification.py::test_rejection_index_is_fingerprint_only`,
and
`tests/test_creative_code_specification.py::test_rejection_index_duplicate_keys_fail_closed`.

Disposition: FIXED

Finding: synthesis could select a rejected, duplicate, or unreviewed variant.

Commit: `977b48d2208453ae4c3a1eb6bb0c61ed50f717af`

Evidence: `scripts/orchestration/creative_code_specification.py`,
`tests/test_creative_code_specification.py::test_all_rejected_is_valid_terminal_state`,
`tests/test_creative_code_specification.py::test_selected_rejected_variant_is_banned`,
and
`tests/test_creative_code_specification.py::test_duplicate_approach_families_fail_closed`.

Disposition: FIXED

Finding: local `make validate-changed` could false-green before new files were
committed.

Commit: `977b48d2208453ae4c3a1eb6bb0c61ed50f717af`

Evidence: initial empty selection was treated as non-sufficient; focused pytest
ran, then post-commit `make validate-changed` selected
`tests/test_creative_code_specification.py` and passed.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/creative-code-specification-pr1-oracle.json`

Status: accepted

Runner mode: `oracle_only_governance_reviewer`

Oracles passed:

- `python -m pytest -q tests/test_creative_code_contract.py tests/test_creative_code_specification.py`
- `python -m scripts.orchestration.creative_code_specification --validate docs/orchestration/contracts/creative_code_specification.v1.json`

Result: 2/2 oracle commands passed; `mutated_paths=[]`;
`shared_tree_untouched=true`; `candidate_patch=oracle_only_governance_reviewer`.

Attribution: co-author trailer required and present on governance premortem
commit `2c6fd83f1915a709471ee1403f6e59845218eed9`.

## Discussion Thread Pass

Pre-open: no GitHub review threads existed before PR creation.

Post-open QA pass found three actionable PR-surface findings. They are fixed in
commit `c043263f6cb23e0f9718d8a21e988663d6967c5b` and recorded below. Remaining post-open pass sequence:
`bug-hunter -> security-auditor -> Codex Security diff scan / finding discovery -> pulseplate-pr-review`.

Disposition: FIXED

Finding: artifact path validation could create outside directories before
rejecting them.

Commit: `c043263f6cb23e0f9718d8a21e988663d6967c5b`

Evidence: `scripts/orchestration/creative_code_spec_pipeline.py`,
`tests/test_creative_code_specification.py::test_pipeline_rejects_absolute_artifact_paths_without_creating_them`,
and
`tests/test_creative_code_specification.py::test_pipeline_rejects_traversal_artifact_paths_without_creating_them`.

Disposition: FIXED

Finding: unsafe-authority text filtering missed `open PR`, `create PR`,
`push branch`, and `write repository`.

Commit: `c043263f6cb23e0f9718d8a21e988663d6967c5b`

Evidence: `scripts/orchestration/creative_code_specification.py` and
`tests/test_creative_code_specification.py::test_unsafe_variant_text_is_rejected`.

Disposition: FIXED

Finding: schema path definition was weaker than the Python validator and the
schema parity test did not lock path policy shape.

Commit: `c043263f6cb23e0f9718d8a21e988663d6967c5b`

Evidence:
`docs/orchestration/contracts/creative_code_specification.v1.schema.json` and
`tests/test_creative_code_specification.py::test_reference_bundle_schema_and_validator_are_aligned`.

Post-open bug-hunter pass found two additional actionable PR-surface findings.
They are fixed in commit `dae4e3a98d53632cf7f070f1214bbe4a210e9981` and recorded below. Remaining
post-open pass sequence:
`security-auditor -> Codex Security diff scan / finding discovery -> pulseplate-pr-review`.

Disposition: FIXED

Finding: unsafe-authority filtering still accepted common variants such as
`Open a PR`, `Create a pull request`, `Push the branch`, and
`Write to the repository`.

Commit: `dae4e3a98d53632cf7f070f1214bbe4a210e9981`

Evidence: `scripts/orchestration/creative_code_specification.py` and
`tests/test_creative_code_specification.py::test_unsafe_variant_text_is_rejected`.

Disposition: FIXED

Finding: source file targets accepted impossible child paths such as
`core/rag/orchestration.py/child.py`.

Commit: `dae4e3a98d53632cf7f070f1214bbe4a210e9981`

Evidence: `scripts/orchestration/creative_code_specification.py` and
`tests/test_creative_code_specification.py::test_variant_target_paths_cannot_create_children_under_file_surface`.

Post-open security-auditor pass found three additional actionable PR-surface
findings. They are fixed in commit
`c7740821d7dfd963f5b1b3c511e075a7666b6af0` and recorded below. Remaining
post-open pass sequence:
`Codex Security diff scan / finding discovery -> pulseplate-pr-review`.

Disposition: FIXED

Finding: unsafe-authority filtering still accepted authority variants such as
`open a draft PR`, `create branch`, and `write shared worktree files`.

Commit: `c7740821d7dfd963f5b1b3c511e075a7666b6af0`

Evidence: `scripts/orchestration/creative_code_specification.py` and
`tests/test_creative_code_specification.py::test_unsafe_variant_text_is_rejected`.

Disposition: FIXED

Finding: secret filtering missed modern hyphenated OpenAI-style key prefixes
such as `sk-proj-...` and `sk-svcacct-...`.

Commit: `c7740821d7dfd963f5b1b3c511e075a7666b6af0`

Evidence: `scripts/orchestration/creative_code_specification.py` and
`tests/test_creative_code_specification.py::test_unsafe_variant_text_is_rejected`.

Disposition: FIXED

Finding: schema-only consumers could accept unsafe prose in free-text fields
that the Python validator rejects.

Commit: `c7740821d7dfd963f5b1b3c511e075a7666b6af0`

Evidence:
`docs/orchestration/contracts/creative_code_specification.v1.schema.json`,
`tests/test_creative_code_specification.py::test_reference_bundle_schema_and_validator_are_aligned`,
and
`tests/test_creative_code_specification.py::test_schema_safe_text_rejects_unsafe_authority_prose`.

Security-fix validation:

- PASS: `python -m scripts.orchestration.creative_code_specification --validate docs/orchestration/contracts/creative_code_specification.v1.json`
- PASS: `python -m pytest -q tests/test_creative_code_contract.py tests/test_creative_code_specification.py tests/test_context_pack_compression.py tests/core/evidence/test_fingerprints.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`

Codex Security diff scan / finding discovery found four additional actionable
PR-surface findings.

Scan: `d8cd3e1b-48ee-4c54-b15f-b1627954bfe7`

They are fixed in commit `5f58d3e8dbeb3a9076fa83055b5d6978849bccfa` and
recorded below. Remaining post-open pass sequence: `pulseplate-pr-review`.

Disposition: FIXED

Finding: fingerprint-only rejection-index validation accepted semantic
authority/secret-shaped IDs and tokens such as `github:write`,
`provider_payload`, `openai:gpt-5`, and `slack:admin`.

Commit: `5f58d3e8dbeb3a9076fa83055b5d6978849bccfa`

Evidence: `scripts/orchestration/creative_code_rejection_index.py`,
`docs/orchestration/contracts/creative_code_specification.v1.schema.json`,
`tests/test_creative_code_specification.py::test_rejection_index_rejects_unsafe_ids_and_tokens`,
and
`tests/test_creative_code_specification.py::test_schema_rejection_labels_reject_unsafe_authority_tokens`.

Disposition: FIXED

Finding: `ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)` could follow a
pre-existing symlinked artifact-root ancestor before the pipeline rejected
symlinks.

Commit: `5f58d3e8dbeb3a9076fa83055b5d6978849bccfa`

Evidence: `scripts/orchestration/creative_code_spec_pipeline.py` and
`tests/test_creative_code_specification.py::test_pipeline_rejects_symlinked_artifact_root_before_creating_children`.

Disposition: FIXED

Finding: `variants[].tests_to_add` accepted out-of-scope product/client/iOS or
OpenAPI paths even though PR-1 artifacts must stay specification-only and narrow.

Commit: `5f58d3e8dbeb3a9076fa83055b5d6978849bccfa`

Evidence: `scripts/orchestration/creative_code_specification.py`,
`docs/orchestration/contracts/creative_code_specification.v1.schema.json`, and
`tests/test_creative_code_specification.py::test_variant_tests_to_add_must_stay_under_tests`.

Disposition: FIXED

Finding: free-text unsafe-authority filtering still accepted provider/runtime
and patch-authority prose such as OpenAI API calls, HTTP requests, repository
patches, and commit changes.

Commit: `5f58d3e8dbeb3a9076fa83055b5d6978849bccfa`

Evidence: `scripts/orchestration/creative_code_specification.py`,
`docs/orchestration/contracts/creative_code_specification.v1.schema.json`,
`tests/test_creative_code_specification.py::test_unsafe_variant_text_is_rejected`,
and
`tests/test_creative_code_specification.py::test_schema_safe_text_rejects_unsafe_authority_prose`.

Codex Security fix validation:

- PASS: `python -m scripts.orchestration.creative_code_specification --validate docs/orchestration/contracts/creative_code_specification.v1.json`
- PASS: `python -m pytest -q tests/test_creative_code_contract.py tests/test_creative_code_specification.py tests/test_context_pack_compression.py tests/core/evidence/test_fingerprints.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`

## Fixed in Commit Mapping

No pre-open GitHub review-thread URLs existed at PR creation time.

Implementation commits:

- `977b48d2208453ae4c3a1eb6bb0c61ed50f717af` implements the PR-1 specification
  bundle contract, validator, CLI, rejection index, docs, and tests.
- `2c6fd83f1915a709471ee1403f6e59845218eed9` records the premortem closure
  artifact with Experiment Runner attribution.
- `245a55d8533915f8cd1a309c679f2524b112b948` fixes PR-1 changed-file mypy
  typing for source packet fingerprints.
- `c043263f6cb23e0f9718d8a21e988663d6967c5b` closes post-open QA findings for
  artifact path rejection, authority filtering, and schema path parity.
- `dae4e3a98d53632cf7f070f1214bbe4a210e9981` closes post-open bug-hunter
  findings for authority phrase variants and file-target containment.
- `c7740821d7dfd963f5b1b3c511e075a7666b6af0` closes post-open security-auditor
  findings for authority variants, hyphenated secret prefixes, and schema
  free-text safety parity.
- `5f58d3e8dbeb3a9076fa83055b5d6978849bccfa` closes Codex Security findings for
  rejection-index semantic tokens, artifact-root symlink creation, test-path
  containment, and provider/runtime/patch prose filtering.

## Merge Readiness

Not claimed by this artifact. Merge readiness still requires current-head CI,
post-open role passes, CodeRabbit/Sourcery/Cubic/Codex Security no-actionable
state, fixed-mapping updates for any review threads, strict merge-readiness/auth
wrappers, and the required wait-window.
