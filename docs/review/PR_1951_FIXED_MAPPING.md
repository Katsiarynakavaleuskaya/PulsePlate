# PR 1951 Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: ff6bb347828e60e80ac67e49014607890f426cff
Evidence: `.github/workflows/build.yml` and `.github/workflows/cd.yml` now use `predicate-type: https://spdx.dev/Document/v2.3` for SBOM attestations, matching `scripts/ci/check_docker_provenance_attestation.py` `SBOM_PREDICATE_TYPE`.
Evidence: `tests/test_python_supply_chain_controls.py` imports `SBOM_PREDICATE_TYPE` and asserts every SBOM attestation step uses that verifier-owned value while keeping `sbom-path` absent.
Evidence: `python3 scripts/ci/guard_actions_pin.py` passed; focused pytest passed through the repo-approved root virtualenv for `tests/test_python_supply_chain_controls.py::test_push_to_registry_workflows_restore_signed_attestations_on_publish_lanes` and `tests/test_check_docker_provenance_attestation.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1951#pullrequestreview-4479411829 -> ff6bb347828e60e80ac67e49014607890f426cff
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1951#discussion_r3398166657 -> ff6bb347828e60e80ac67e49014607890f426cff

## External Review Availability Notes

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1951#issuecomment-4683611937 is a Codex review usage-limit notice and contains no repository code or documentation action.
Reason: External reviewer quota notice; no code change is requested by the bot comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1951#issuecomment-4683611937

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1951#issuecomment-4683612353 is a CodeRabbit review quota notice and contains no repository code or documentation action.
Reason: External reviewer quota notice; no code change is requested by the bot comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1951#issuecomment-4683612353

## Lane Start Provenance
- Packet: `artifacts/orchestration/task_packets/8afffb82abbf.json`
- Branch: `codex/fix-sbom-attestation-action-in-ci/cd`
- Worktree: sibling PR worktree `PulsePlate-pr-1951-sbom`
- Existing PR lane resumed: PR #1951 was already open before this post-open remediation pass.

## Role Dispatch Evidence
- Required role order from packet `8afffb82abbf`: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`.
- `agent-coordinator`: scope locked to privileged CI/SBOM attestation verifier alignment and PR governance; no backend runtime, OpenAPI, frontend, iOS, DB, product AI, or wellness behavior changes.
- `qa-engineer-agent`: required local gates are focused SBOM/provenance pytest, action pin guard, `make validate-changed`, and `pre-commit run --all-files`; full local `make verify` is operator-deferred under the machine-heavy exception.
- `bug-hunter`: Cubic P0 reproduced as valid because `SBOM_PREDICATE_TYPE` is `https://spdx.dev/Document/v2.3` and `_parse_verification_output` fails closed on predicate mismatch.
- `security-auditor`: fix preserves fail-closed verification, full action SHA pinning, registry-backed attestation publication, and does not weaken any secret, auth, suppression, or `continue-on-error` policy.

## Premortem Evidence
- Artifact: `artifacts/orchestration/premortem/pr-1951-sbom-premortem.md`
- Decision: `proceed with changes`.
- Primary risk closed: verifier/workflow predicate drift fixed in commit `ff6bb347828e60e80ac67e49014607890f426cff`.

## Experiment Runner Evidence
- Packet: `artifacts/orchestration/experiments/exp-ad2c2435d47f.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-ad2c2435d47f-root-venv.json`
- Mode: `oracle_only_governance_reviewer`.
- Status: `accepted`.
- Mutated paths: `[]`.
- Co-author required: `true`.
- Co-author reason: Experiment Runner oracle evidence shapes PR #1951 fixed-mapping and merge-readiness governance.

## Validation Evidence
- PASS: `python3 scripts/orchestration/check_preflight.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: `python3 scripts/ci/guard_actions_pin.py`.
- PASS: focused pytest through repo-approved root virtualenv for `tests/test_python_supply_chain_controls.py::test_push_to_registry_workflows_restore_signed_attestations_on_publish_lanes` and `tests/test_check_docker_provenance_attestation.py`.
- PASS: commit hook rerun with `VENV_PYTHON` pointing to the repo-approved root virtualenv; backend changed-file pytest passed.
- DEFERRED by operator instruction: full local `make verify` because the project has a very large test suite; this PR uses the machine-heavy narrow-gate path with `make validate-changed` as the heavy local diff gate.

## Merge Readiness
- [ ] `make validate-changed` passes.
- [ ] `pre-commit run --all-files` passes.
- [ ] Codex Security diff scan / finding discovery completes.
- [ ] `pulseplate-pr-review` completes.
- [ ] Current-head CI terminal success confirmed.
- [ ] Required checks complete with no pending jobs.
- [ ] Bot review/governance completed with no unmapped actionable comments.
- [ ] Strict review-thread disposition passes with auth.
- [ ] Strict merge-readiness guard passes with auth.
- [ ] Mandatory wait-window after latest bot/review activity completed.
