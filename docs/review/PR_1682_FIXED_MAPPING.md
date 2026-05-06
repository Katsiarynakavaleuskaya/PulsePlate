# PR 1682 Fixed Mapping

**PR:** <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682>
**Branch:** `release/release-control-plane-pr5-ci-gates`
**Release-control-plane slice:** PR-5 CI release decision integration
**Canonical commit:** `eb798b4d9`
**Latest review-fix commit:** `62b0a2bc2`

## Scope

PR-5 adds a deterministic release-control-plane CI checker for release manifest,
RAG gate result, build-equivalence result, and supply-chain evidence. It also
wires a non-secret fixture validation job into CD without changing production
deploy dependencies, App Store upload behavior, Fastlane, runtime/API/OpenAPI,
iOS runtime, RAG behavior, semantic cache, GraphRAG, or product-facing behavior.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open discussion pass completed for comments visible through 2026-05-06
12:25 UTC. No human or bot review thread has been resolved without disposition
evidence. New comments after this timestamp require a new pass before merge.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682 -> eb798b4d9
Disposition: FIXED
Commit: eb798b4d9
Evidence: Pre-push MyPy found `_sha256_file(...)` returning an `Any`-typed value in `scripts/ci/check_release_control_plane.py`; commit `eb798b4d9` fixed the type boundary without suppression. Evidence commands after the fix: `. .venv/bin/activate && mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_release_control_plane.py` PASS, `. .venv/bin/activate && pytest -q tests/test_release_control_plane_ci_gate.py` PASS (`22 passed`), `make validate-changed` PASS (`44 passed`), `pre-commit run --all-files` PASS, and pre-push hooks PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#issuecomment-4387819794
Disposition: NOT-A-BUG
Evidence: CodeRabbit initially skipped because PR #1682 was draft. The PR was marked ready for review and CodeRabbit was explicitly requested with `@coderabbitai review` at https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#issuecomment-4387880259.
Reason: Draft-skip status is review orchestration state, not a code defect.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#issuecomment-4387881022
Disposition: NOT-A-BUG
Evidence: CodeRabbit acknowledged the explicit review trigger and reported review in progress.
Reason: This is a bot status acknowledgement, not an actionable code or docs finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#pullrequestreview-4235933131
Disposition: NOT-A-BUG
Evidence: Sourcery reported a weekly rate limit and did not provide code findings.
Reason: External review quota state is not an actionable repo defect.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#pullrequestreview-4235967433
Disposition: NOT-A-BUG
Evidence: Sourcery repeated the weekly rate-limit comment after the PR was marked ready.
Reason: External review quota state is not an actionable repo defect.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682
Disposition: NOT-A-BUG
Evidence: Cubic current-head status is PASS for PR #1682.
Reason: No Cubic actionable finding is present to fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#discussion_r3195366317 -> 62b0a2bc2
Disposition: FIXED
Commit: 62b0a2bc2
Evidence: `scripts/ci/check_release_control_plane.py` now validates empty `{}` evidence objects because payload checks use `is not None` instead of truthiness; `tests/test_release_control_plane_ci_gate.py::test_empty_evidence_objects_are_invalid_not_allowed` proves empty manifest, RAG, and build-equivalence files return `BLOCK` with invalid evidence reason codes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#discussion_r3195410123 -> 62b0a2bc2
Disposition: FIXED
Commit: 62b0a2bc2
Evidence: `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json` now allows raw string-or-null summary values for `build_equivalence_decision`, `rag_gate_decision`, and `attestation_status`, while the checker still fails closed on malformed upstream values; `tests/test_release_control_plane_ci_gate.py::test_schema_allows_raw_malformed_summary_values_for_block_outputs` covers the blocked malformed-output path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#pullrequestreview-4236025179 -> 62b0a2bc2
Disposition: FIXED
Commit: 62b0a2bc2
Evidence: The CodeRabbit actionable P1 is fixed by the empty-evidence object handling above. The low-value workflow/docs test brittleness note was addressed with an inline test comment documenting that those assertions intentionally guard PR-5 textual integration and should migrate to YAML/schema parsing if the workflow contract grows.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682#pullrequestreview-4236030844 -> 62b0a2bc2
Disposition: FIXED
Commit: 62b0a2bc2
Evidence: The Cubic P2 schema finding is fixed by relaxing the malformed summary fields in `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json` and covering the behavior in `tests/test_release_control_plane_ci_gate.py`.

## Split Justification

This PR is intentionally one release-control-plane slice because the fail-closed
CI checker, schema contract, workflow fixture integration, focused tests, ledger
reconciliation, premortem artifact, and fixed-mapping artifact must land
together for PR-5 governance to be reviewable and deterministic. Splitting the
checker from the contract or tests would create a temporary release-governance
state where CI evidence semantics are either undocumented or untested. Protected
production artifact wiring remains deferred as a separate follow-up.

## Premortem

- [x] Premortem pass completed against actual changed files
- [x] All P0/P1 premortem findings fixed or dispositioned as NOT-A-BUG with evidence
- [x] P2 findings, if any, are linked in BACKLOG_LEDGER.md

Artifact: [`docs/review/PR_1682_PREMORTEM.md`](PR_1682_PREMORTEM.md)

## Validation

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "Release control plane PR-5: CI release decision integration" --task-class Orchestration --pr-phase pre_open --path docs/roadmap/BACKLOG_LEDGER.md --path docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md --path scripts/ci/check_release_control_plane.py --path tests/test_release_control_plane_ci_gate.py --path docs/release/RELEASE_CONTROL_PLANE_EPIC.md --path docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md --path .github/workflows/cd.yml --requested-agent ...` PASS, packet `0ddd1b459d6d`
- `python3 scripts/orchestration/task_bootstrap.py --goal "Release control plane PR-5 post-open review: CI decision integration" --task-class Orchestration --pr-phase post_open_review --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent premortem-facilitator --requested-agent security-auditor` PASS, packet `f6116f0353a4`
- `. .venv/bin/activate && pytest -q tests/test_release_control_plane_ci_gate.py` PASS (`22 passed`)
- `. .venv/bin/activate && pytest -q tests/test_release_manifest.py` PASS (`20 passed`)
- `. .venv/bin/activate && pytest -q tests/test_build_equivalence.py` PASS (`22 passed`)
- `. .venv/bin/activate && pytest -q tests/test_rag_release_gates_runner.py` PASS (`48 passed`)
- `. .venv/bin/activate && pytest -q tests/test_check_docker_provenance_attestation.py` PASS (`12 passed`)
- `. .venv/bin/activate && pytest -q tests/test_repo_policy_guards.py` PASS (`14 passed`)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/roadmap/BACKLOG_LEDGER.md` PASS
- `make validate-changed` PASS (`44 passed`)
- `pre-commit run --all-files` PASS
- Pre-push hooks PASS, including changed-file MyPy, pip-audit, backend pre-push tests, full-repo Bandit, and docker build test

## Machine-Heavy Deferral

Full local `make verify` was intentionally not run per operator instruction.
This PR follows the bounded local gate path with focused tests,
`make validate-changed`, pre-commit, and current-head PR CI before any
merge-readiness claim.

## Merge Readiness

- [ ] PR is ready for review and no longer draft.
- [ ] Current-head required CI is green with no pending required checks.
- [ ] CodeRabbit/Sourcery/Cubic actionable comments are dispositioned.
- [ ] Discussion-thread pass is complete.
- [ ] Strict merge readiness gate passes with auth.
