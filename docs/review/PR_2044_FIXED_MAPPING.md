# PR #2044 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2044

Branch: `codex/creative-code-telemetry-rejection-taxonomy-pr4`

## Summary

This PR adds PR-4 local creative-code telemetry and rejection taxonomy over
sanitized PR-1/PR-2/PR-3 control-plane artifacts. It measures the private-pilot
funnel before any public GitHub App backend, Slack beta, live review ingestion,
or broader automation authority is considered.

## Scope

- Add strict telemetry event, rollup, and rejection-taxonomy contracts.
- Add a local collector for sanitized creative-code specification, patch, and
  promotion artifacts.
- Emit advisory local-only sidecars under the gitignored creative-code
  telemetry artifact root.
- Update orchestration docs, scripts scoped instructions, and the creative-code
  backlog PR train.
- Add deterministic tests for schema closure, duplicate-key rejection, leak
  guards, path containment, malformed-artifact handling, deterministic rollups,
  and repo-relative CLI paths.

## Out Of Scope

No product runtime behavior, OpenAPI/backend route/client changes, public
GitHub App backend, Slack beta, live GitHub/review-thread ingestion,
review-thread resolution, fixed-mapping automation, merge-readiness claim,
branch mutation, provider call, or semantic-cache activation is authorized by
this PR.

## Implementation Commits

- `a7bb7a5b8` - add PR-4 local creative-code telemetry contracts, collector,
  rejection taxonomy, docs, scoped instructions, backlog updates, tests, and
  pre-open governance evidence.

## Lane Start Provenance

- Base branch: `main`
- Branch: `codex/creative-code-telemetry-rejection-taxonomy-pr4`
- Initial packet: `artifacts/orchestration/task_packets/d1fee07492a7.json`
- Refreshed packet after fast-forward: `artifacts/orchestration/task_packets/24a9d90008fd.json`
- Packet: `artifacts/orchestration/task_packets/d1fee07492a7.json`
- Packet: `artifacts/orchestration/task_packets/24a9d90008fd.json`
- Pre-implementation role order executed:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> cursor-specialist-agent -> architecture-specialist`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2044`.
- [x] Initial PR open: no GitHub review threads existed and none were resolved.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [x] `pulseplate-pr-review` completed.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Role Findings

Role: `qa-engineer-agent`

Disposition: FIXED

Commit: `013642ce8`

Evidence: The QA pass found that collector file discovery could follow
symlinked JSON descendants inside otherwise valid artifact roots. Commit
`013642ce8` rejects symlink components for JSON artifacts in
`scripts/orchestration/creative_code_telemetry.py` and covers the case in
`tests/test_creative_code_telemetry.py::test_artifact_json_symlinks_are_rejected`.

Disposition: FIXED

Commit: `013642ce8`

Evidence: The QA pass found malformed PR-1 specification artifacts were
silently dropped by default. Commit `013642ce8` emits the same safe
`artifact_read_error` event for malformed specification artifacts as for
malformed PR-2/PR-3 artifacts, with coverage in
`tests/test_creative_code_telemetry.py::test_malformed_spec_artifact_becomes_safe_error_event_by_default`.

Disposition: FIXED

Commit: `013642ce8`

Evidence: The QA pass found schema-only false-green risk in the rejection
taxonomy and rollup count-map schemas. Commit `013642ce8` locks the taxonomy
schema to the exact reference class list and restricts rollup count maps to
taxonomy, stage, and status keys, with assertions in
`tests/test_creative_code_telemetry.py::test_reference_taxonomy_and_schemas_are_closed`.

Disposition: FIXED

Commit: `340f9f80c`

Evidence: The QA pass found the PR #2044 fixed-mapping artifact was missing
from the tracked branch at the reviewed head and did not match the Phase 2
parser shape in the local draft. Commit `414bad0b2` added the canonical
artifact, and commit `340f9f80c` aligned the artifact with exact
discussion-thread and fixed-mapping parser requirements. Validation:
`scripts/orchestration/review_mapping_artifact.py::validate_mapping_artifact_text`
returns no errors for `docs/review/PR_2044_FIXED_MAPPING.md`.

Disposition: NOT-A-BUG

Evidence: The QA pass reported current-head Private Python proxy health as a
pending external gate. That is not caused by the local creative-code telemetry
diff and remains a current-head CI monitoring item, not a PR-owned code defect.
This artifact still does not claim merge readiness while current-head CI is
pending or red.

Role: `bug-hunter`

Disposition: FIXED

Commit: `4b1ee2921`

Evidence: The bug-hunter pass found that malformed local artifacts with the
same basename under different run directories could collide because
`artifact_read_error` identity used only the basename. Commit `4b1ee2921`
derives read-error identity from a containment-checked creative-code-root
relative locator fingerprint without emitting the raw locator, with coverage in
`tests/test_creative_code_telemetry.py::test_malformed_artifacts_with_same_basename_keep_distinct_identities`.

Role: `security-auditor`

Disposition: FIXED

Commit: `36f63bdc9`

Evidence: The security-auditor pass found the Python leak guard and JSON schemas
admitted tokenized oracle-output labels such as `oracle_stdout` and
`oracle-stderr`, plus other tokenized unsafe labels. Commit `36f63bdc9` aligns
the Python denylist and event/rollup schema safe-id denylist, with coverage in
`tests/test_creative_code_telemetry.py::test_reference_taxonomy_and_schemas_are_closed`
and
`tests/test_creative_code_telemetry.py::test_event_rejects_raw_patch_leaks_and_mutating_authority`.

Role: `pulseplate-pr-review`

Disposition: NOT-A-BUG

Evidence: The pushed-head dry-run report
`/tmp/pulseplate_pr2044_review_report.json` produced one advisory
large-diff review-planning note and no deterministic architecture, security, QA,
or governance findings. The diff is a single local orchestration slice
containing telemetry contracts, schemas, collector, docs, mapping, and focused
tests; splitting the schemas from the builder/tests would weaken the reviewed
contract/test pairing. Narrow gates passed, including focused telemetry/guard
tests, `make validate-changed`, `pre-commit run --all-files`, and pre-push
hooks. No merge-readiness claim is made while Codex Security and current-head CI
remain pending.

## Pre-Open Premortem Closure

Disposition: FIXED

Commit: `a7bb7a5b8`

Evidence: Repo-relative telemetry CLI paths could have nested under the output
root instead of resolving from repo root. The path resolver in
`scripts/orchestration/creative_code_telemetry.py` keeps repo-relative paths
under the creative-code artifact root, with coverage in
`tests/test_creative_code_telemetry.py::test_cli_accepts_repo_relative_artifact_paths`.

Disposition: FIXED

Commit: `a7bb7a5b8`

Evidence: The first schema pattern introduced a literal local `/Users/...`
guard string into changed docs. The schema now uses an escaped pattern that
still rejects real local path values without adding the forbidden docs literal,
with coverage in
`tests/test_creative_code_telemetry.py::test_reference_taxonomy_and_schemas_are_closed`
and
`tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths`.

Disposition: NOT-A-BUG

Evidence: The telemetry sidecar remains advisory and local-only. The authority
contract requires `read_only_telemetry=true` and all mutation/network/runtime
authority flags false in
`scripts/orchestration/creative_code_telemetry_contract.py`, with fail-closed
coverage in
`tests/test_creative_code_telemetry.py::test_event_rejects_raw_patch_leaks_and_mutating_authority`.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/creative-code-telemetry-pr4-oracle-result.json`

Disposition: FIXED

Commit: `a7bb7a5b8`

Evidence: Oracle-only governance reviewer result was accepted with two oracle
commands executed, no failure class, and shared tree untouched. The material
oracle review is recorded by the canonical co-author trailer on commit
`a7bb7a5b8`.

## Local Validation Evidence

- `.venv/bin/python -m pytest -q tests/test_creative_code_telemetry.py tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths` - pass.
- `python -m pytest -q tests/test_creative_code_specification.py tests/test_creative_code_patch_builder.py tests/test_creative_code_pr_promotion.py tests/test_creative_code_telemetry.py` - pass.
- `python -m scripts.orchestration.creative_code_telemetry_contract --validate-taxonomy docs/orchestration/contracts/creative_code_rejection_taxonomy.v1.json` - pass.
- `python -m scripts.orchestration.creative_code_telemetry --spec-runs-dir artifacts/orchestration/creative_code/spec_runs --patch-runs-dir artifacts/orchestration/creative_code/patch_runs --promotions-dir artifacts/orchestration/creative_code/promotions --output-dir artifacts/orchestration/creative_code/telemetry` - pass; generated gitignored sidecars were cleaned.
- `make validate-changed` - pass.
- `pre-commit run --all-files` - pass.
- Pre-push hooks during `git push` - pass: changed-file mypy, pip-audit,
  backend tests pre-push, bandit full, and docker build test.

Full `make verify` is not used as readiness evidence. It was started
accidentally, then operator-cancelled per the narrow-lane machine-budget rule;
the PR-owned guard finding surfaced before cancellation was fixed and rerun
with the exact guard above.

## Merge Readiness

Not claimed. Post-open role passes, external bot disposition, current-head CI,
Codex Security / security scan disposition, and strict merge-readiness checks
remain pending.
