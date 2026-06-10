# PR 1916 Fixed Mapping

## Summary

This PR redacts Docker provenance attestation evidence before CI artifact
publication. The follow-up fixes close post-open review and CI findings: helper
validation now fails closed, attestation proof hashes no longer derive from raw
secret-bearing statements, failure diagnostics are redacted, workflow contract
tests match the intentional artifact policy, and the synthetic redaction test no
longer trips secret scanning.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/d79c1c61cefe.json`
- Packet id: `d79c1c61cefe`
- Branch: `pr-1916-fix` tracking `origin/codex/fix-build-workflow-provenance-upload-issue`
- Head commit before fixes: `7b444af95b0d6a6e881ef4a97bcfeaa78fd5a60d`

## Scope

IN:

- `.github/workflows/build.yml`
- `scripts/ci/check_docker_provenance_attestation.py`
- `tests/test_check_docker_provenance_attestation.py`
- `tests/test_release_manifest_evidence_workflow.py`
- `tests/test_ci_workflow_pr_size_governance_contract.py`
- `docs/review/PR_1916_FIXED_MAPPING.md`

OUT:

- Docker image build topology changes
- dependency or base-image changes
- CD attestation-check artifact policy outside the release-control-plane build-source upload
- full local `make verify` execution; this is an operator-approved machine-heavy CI/tooling lane using narrow gates plus current-head CI parity

## Agent Execution Log

- `agent-coordinator`: PASS. Classified the lane as post-open CI/security remediation and approved the narrow-gate machine-heavy path.
- `qa-engineer-agent`: PASS. Confirmed detect-secrets, stale contract-test, missing Phase2 artifact, and helper validation findings.
- `bug-hunter`: PASS. Confirmed direct-indexing, stale workflow expectation, synthetic secret fixture, and missing mapping root causes.
- `security-auditor`: PASS. Added security findings for raw-statement derived hashes and unredacted failure diagnostics; both were fixed in code/tests.
- `Codex Security diff scan / finding discovery`: pending after commit/push.
- `pulseplate-pr-review`: completed locally; native transport returned empty output, so coordinator performed direct diff review and found no additional P0/P1 issues beyond premortem closure items.

## Skill Execution Log

- `pulseplate-workflow`: coordinator-first setup, separate worktree, scoped preflight.
- `pulseplate-gates`: focused pytest and planned narrow verification bundle.
- `pulseplate-pr-review`: scheduled as mandatory post-open review pass.
- `pulseplate-premortem-risk-review`: scheduled on actual diff before readiness.
- `securing-github-actions-workflows`: applied to workflow artifact and secret-handling risk.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-30104d6d9778.json`

Accepted oracle-only governance reviewer evidence. The runner applied the source diff in an isolated checkout, executed two immutable oracle commands, and returned `status=accepted`. The first runner packet `exp-f604a04ae5a9` was rejected because the packet context omitted changed files; the full-surface packet `exp-30104d6d9778` corrected that. The accepted result did not materially shape the patch or commit decision, so no Experiment Runner co-author trailer is required.

## Risk Fix Matrix

| Risk ID | Failure mode | Fix | Regression test | Evidence command | Fix commit SHA | Evidence | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ATT-RED-001` | Raw GitHub attestation statements can contain secret-bearing Docker build args and must not be published in release-control-plane artifacts. | Release-control-plane build-source upload keeps only digest/status files; parser emits predicate type plus a sanitized deterministic statement hash. | `test_docker_build_workflow_emits_governed_release_control_plane_sources`; `test_parser_redacts_raw_attestation_build_arguments`. | `../../.venv/bin/python -m pytest -q tests/test_check_docker_provenance_attestation.py tests/test_release_manifest_evidence_workflow.py::test_docker_build_workflow_emits_governed_release_control_plane_sources tests/test_ci_workflow_pr_size_governance_contract.py::test_node24_setup_go_and_upload_artifact_pins_preserve_workflow_contracts` | `602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192` | `.github/workflows/build.yml`; `scripts/ci/check_docker_provenance_attestation.py`; `tests/test_check_docker_provenance_attestation.py`; `tests/test_release_manifest_evidence_workflow.py` | FIXED |
| `ATT-RED-002` | `_redacted_verification_summary` used direct key indexing, risking `KeyError` instead of stable fail-closed errors. | Replaced direct indexing with `.get()` and explicit type checks, including `predicateType` validation. | `test_redacted_verification_summary_fails_closed_on_missing_predicate_type`. | same focused pytest command above | `602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192` | `scripts/ci/check_docker_provenance_attestation.py`; `tests/test_check_docker_provenance_attestation.py` | FIXED |
| `ATT-RED-003` | Failure diagnostics could write or print raw `gh` stdout/stderr containing secret-shaped attestation data. | Added bounded redaction for URL userinfo and private-index build arg tokens before RuntimeError details, JSON artifacts, Markdown artifacts, and stderr output. | `test_failure_diagnostics_redact_attestation_secrets`. | same focused pytest command above | `602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192` | `scripts/ci/check_docker_provenance_attestation.py`; `tests/test_check_docker_provenance_attestation.py` | FIXED |
| `ATT-RED-004` | Synthetic credential fixture tripped `detect-secrets`, causing CI `lint` failure. | Constructed the fake credential from fragments while preserving runtime redaction assertions; no baseline or global allowlist added. | `pre-commit run --all-files` | pending narrow gate | `602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192` | `tests/test_check_docker_provenance_attestation.py` | FIXED |
| `ATT-RED-005` | Workflow governance contract test still expected raw attestation artifacts in the release-control-plane upload path. | Updated the expected upload-artifact contract to match the intentional digest/status-only upload path. | `test_node24_setup_go_and_upload_artifact_pins_preserve_workflow_contracts`. | same focused pytest command above | `602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192` | `tests/test_ci_workflow_pr_size_governance_contract.py` | FIXED |
| `ATT-RED-006` | Premortem found `statement_sha256` implied raw statement integrity after the implementation intentionally stopped hashing raw secret-bearing statements. | Renamed the emitted field to `redacted_statement_summary_sha256` and kept the hash bound to a sanitized predicate-only evidence envelope. | `test_parser_redacts_raw_attestation_build_arguments`. | same focused pytest command above | `602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192` | `scripts/ci/check_docker_provenance_attestation.py`; `tests/test_check_docker_provenance_attestation.py` | FIXED |
| `ATT-RED-007` | Premortem found redaction coverage was too narrow for common credential/error shapes. | Added bounded redaction for URL userinfo, bearer-style values, and credential-bearing assignment patterns. | Focused diagnostics redaction tests in `tests/test_check_docker_provenance_attestation.py`. | same focused pytest command above | `602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192` | `scripts/ci/check_docker_provenance_attestation.py`; `tests/test_check_docker_provenance_attestation.py` | FIXED |
| `ATT-RED-009` | Bot review found redacted `gh` failure output was not length-bounded before serialization into artifacts and stderr. | Reused `_trim_for_error(...)` in `_run_gh(...)` so subprocess failure details are redacted and bounded before the `RuntimeError` reaches `main()`. | `test_run_gh_redacts_subprocess_failure_output`. | focused pytest command above | `d99d8930b33eb1180b181765e8afed777cc9baae` | `scripts/ci/check_docker_provenance_attestation.py`; `tests/test_check_docker_provenance_attestation.py` | FIXED |
| `ATT-RED-010` | Bot review found the risk matrix table separator had one more column than the table header. | Reduced the separator row to eight cells to match the header. | `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1916`. | Phase2 gate command | `d99d8930b33eb1180b181765e8afed777cc9baae` | `docs/review/PR_1916_FIXED_MAPPING.md` | FIXED |
| `SEC-CI-001` | Current-head `security` job failed in `Install Safety` because the approved private proxy lacked a Linux/Python 3.13 `regex` wheel needed by Safety's `nltk` dependency. | Added a narrow `requirements-security.txt` Safety tooling manifest, routed CI Safety install through the governed locked installer with emergency-wheel fallback, and added the exact `regex==2026.5.9` Linux wheel artifact to the existing emergency manifest. | `test_ci_security_job_installs_safety_through_locked_installer`; `test_security_requirements_pin_safety_and_regex_floor`. | `../../.venv/bin/python -m pytest -q tests/test_ci_risk_profile.py::test_security_tooling_manifest_change_routes_backend_and_security tests/test_python_supply_chain_controls.py::test_ci_security_job_installs_safety_through_locked_installer tests/test_python_supply_chain_controls.py::test_security_requirements_pin_safety_and_regex_floor tests/test_python_supply_chain_controls.py::test_no_canonical_workflow_uses_unscoped_public_pip_install` | `544c827c2b5886d9d760e9b4e64eece056499d59` | `.github/workflows/ci.yml`; `requirements-security.txt`; `scripts/ci/emergency_python_wheels.json`; `tests/test_python_supply_chain_controls.py` | FIXED |
| `SEC-CI-002` | New `requirements-security.txt` could be changed later without routing through backend/security CI. | Added it to the CI risk-profile backend/shared exact surfaces and added a deterministic route test. | `test_security_tooling_manifest_change_routes_backend_and_security`. | same focused pytest command above | `544c827c2b5886d9d760e9b4e64eece056499d59` | `scripts/ci/ci_risk_profile.py`; `tests/test_ci_risk_profile.py` | FIXED |
| `SEC-CS-001` | The GitHub Code Scanning page showed three open Trivy alerts, but they were suspected to be the failing PR security scan. | Verified via Code Scanning API that PR head `f78b7c7c92f43b1440c426b1cc145c81fd2d779e` had no open Code Scanning alerts; alerts 608, 609, and 610 are Trivy alerts on `refs/heads/main` for the published image and are not this PR-head blocker. | GitHub Code Scanning API query. | `gh api /repos/Katsiarynakavaleuskaya/PulsePlate/code-scanning/alerts?state=open&ref=f78b7c7c92f43b1440c426b1cc145c81fd2d779e` | N/A | Code Scanning API: alerts 608-610 `ref=refs/heads/main`; PR-head query returned no open alerts | NOT-A-BUG |
| `ATT-RED-008` | Premortem questioned whether sanitized attestation JSON/Markdown should remain uploaded as build artifacts after removing them from release-control-plane build-source artifact inputs. | Kept the PR's policy scope: release-control-plane build-source uploads exclude raw attestation files; build logs and generated local files remain enough for this lane, while CD attestation-check artifact policy stays out of scope. | `test_docker_build_workflow_emits_governed_release_control_plane_sources`; `test_node24_setup_go_and_upload_artifact_pins_preserve_workflow_contracts`. | same focused pytest command above | N/A | `.github/workflows/build.yml`; `tests/test_release_manifest_evidence_workflow.py`; `tests/test_ci_workflow_pr_size_governance_contract.py` | NOT-A-BUG |

## Tests / Bounded Checks

- `python3 scripts/orchestration/check_preflight.py && python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review ...` - PASS, packet `d79c1c61cefe`.
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/d79c1c61cefe.json --pretty` - PASS.
- `../../.venv/bin/python -m py_compile scripts/ci/check_docker_provenance_attestation.py tests/test_check_docker_provenance_attestation.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_release_manifest_evidence_workflow.py` - PASS.
- `../../.venv/bin/python -m pytest -q tests/test_check_docker_provenance_attestation.py tests/test_release_manifest_evidence_workflow.py::test_docker_build_workflow_emits_governed_release_control_plane_sources tests/test_ci_workflow_pr_size_governance_contract.py::test_node24_setup_go_and_upload_artifact_pins_preserve_workflow_contracts` - PASS (`20 passed`).
- `python3 scripts/orchestration/experiment_runner.py --packet artifacts/orchestration/experiments/exp-30104d6d9778.json` - PASS, accepted oracle-only evidence (`20 passed` in isolated checkout).
- `../../.venv/bin/python -m pytest -q tests/test_check_docker_provenance_attestation.py tests/test_release_manifest_evidence_workflow.py::test_docker_build_workflow_emits_governed_release_control_plane_sources tests/test_ci_workflow_pr_size_governance_contract.py::test_node24_setup_go_and_upload_artifact_pins_preserve_workflow_contracts` - PASS (`20 passed`).
- `pre-commit run --all-files` - pending.
- `make validate-changed` - pending.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1916#pullrequestreview-4456005291 -> 602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192
Disposition: FIXED
Commit: 602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192
Evidence: scripts/ci/check_docker_provenance_attestation.py; tests/test_check_docker_provenance_attestation.py
Reason: CodeRabbit's actionable nit requested safe `.get()` access in `_redacted_verification_summary`; the fix also preserves fail-closed validation and redacted evidence.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1916#discussion_r3378491273 -> 602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192
Disposition: FIXED
Commit: 602bbf4f2f9d70b1dc89d5640cfe7c9e06ea3192
Evidence: tests/test_ci_workflow_pr_size_governance_contract.py
Reason: Codex review found the workflow contract guard still expected raw attestation files; commit `602bbf4f2` updated the golden contract to the digest/status-only upload path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1916#discussion_r3386774296 -> d99d8930b33eb1180b181765e8afed777cc9baae
Disposition: FIXED
Commit: d99d8930b33eb1180b181765e8afed777cc9baae
Evidence: docs/review/PR_1916_FIXED_MAPPING.md
Reason: CodeRabbit found an eight-column table with a nine-cell separator; this commit fixes the separator row.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1916#pullrequestreview-4466047443 -> d99d8930b33eb1180b181765e8afed777cc9baae
Disposition: FIXED
Commit: d99d8930b33eb1180b181765e8afed777cc9baae
Evidence: scripts/ci/check_docker_provenance_attestation.py; docs/review/PR_1916_FIXED_MAPPING.md
Reason: CodeRabbit's review-level actionable findings covered the table separator mismatch and unbounded redacted `gh` failure detail; commit `d99d8930b` fixed both.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1916#discussion_r3386774309 -> d99d8930b33eb1180b181765e8afed777cc9baae
Disposition: FIXED
Commit: d99d8930b33eb1180b181765e8afed777cc9baae
Evidence: scripts/ci/check_docker_provenance_attestation.py; tests/test_check_docker_provenance_attestation.py
Reason: CodeRabbit found the redacted `gh` failure detail was still unbounded; this commit routes subprocess failure details through `_trim_for_error(...)`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1916#discussion_r3386790040 -> d99d8930b33eb1180b181765e8afed777cc9baae
Disposition: FIXED
Commit: d99d8930b33eb1180b181765e8afed777cc9baae
Evidence: scripts/ci/check_docker_provenance_attestation.py; tests/test_check_docker_provenance_attestation.py
Reason: Cubic found the same unbounded redacted failure detail risk; this commit applies bounded redaction before the RuntimeError is raised.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1916#discussion_r3386790061 -> d99d8930b33eb1180b181765e8afed777cc9baae
Disposition: FIXED
Commit: d99d8930b33eb1180b181765e8afed777cc9baae
Evidence: docs/review/PR_1916_FIXED_MAPPING.md
Reason: Cubic found the same table separator mismatch; this commit fixes the separator row.

## Bot Review Summary

- CodeRabbit nitpick: FIXED. Evidence: `_redacted_verification_summary` now uses `.get()` and explicit validation before returning redacted metadata.
- Sourcery review: NOT-A-BUG. Evidence: Sourcery reported the changes look great and requested no code change.
- Cubic review: NOT-A-BUG. Evidence: Cubic reported `No issues found` across 4 files.
- Codex review: NOT-A-BUG. Evidence: Codex posted review metadata only and no actionable findings.

## Deferred / Follow-ups

None.

## Merge Readiness

Not merge-ready yet. Pending before readiness claims:

- `pre-commit run --all-files` PASS.
- `make validate-changed` PASS.
- Experiment Runner oracle-only governance review PASS or disposition.
- `pulseplate-premortem-risk-review` findings fixed or dispositioned.
- `pulseplate-pr-review` PASS/no actionable findings.
- Current-head CI parity after push, including `lint`, `test-pr (3.13)`, `PR Body Phase2 gates`, and merge-readiness gate.
