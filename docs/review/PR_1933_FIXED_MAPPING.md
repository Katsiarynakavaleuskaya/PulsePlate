# PR #1933 Fixed in Commit Mapping

## Summary

PR #1933 binds release-manifest ML/RAG evidence to the build commit by requiring
`ml_identity.git_sha`, copying it from RAG gate evidence, and fail-closing on
missing or mismatched SHA values. This closeout commit fixes the post-open review
gaps without widening release workflow, iOS, Fastlane, App Store metadata,
OpenAPI, semantic-cache, or runtime RAG scope.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/pr_1933_post_open_review.json`
- Role order preserved: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> app-store-release-agent -> cursor-specialist-agent -> web-research-agent`
- PR head before closeout: `85c16be1da4d9ff8fa4c93eb03282cf6724867ec`
- Fix commit: `f04d471110be400b7d9087cbec4ef1508a72b776`

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/pr_1933_release_manifest_git_sha_oracle_result.json`
- Status: accepted
- Mode: `oracle_only_governance_reviewer`
- Oracles: `python3 -m py_compile ...` and focused release/build-equivalence pytest returned `0`.
- Contribution: `commit_decision`, `coauthor_required=true`; commit `f04d471110be400b7d9087cbec4ef1508a72b776` includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Role And Security Passes

- `agent-coordinator`: scope locked to release-manifest RAG `git_sha` closeout and required mapping after the fix commit.
- `qa-engineer-agent`: confirmed the stale build-equivalence fixture was the real failing thread and that focused release/build-equivalence tests cover the closure.
- `bug-hunter`: confirmed `85c16be1` must not be used as FIXED proof because it predates the Codex thread and does not touch the stale fixture.
- `security-auditor`: confirmed fail-closed `rag_git_sha_mismatch` semantics remain acceptable for missing or mismatched SHA values.
- `app-store-release-agent`: confirmed no iOS, Fastlane, App Store metadata, privacy, screenshots, or StoreKit release surfaces are touched.
- `cursor-specialist-agent`: confirmed the minimal patch shape and that `str | None` is the correct typed signature for validator missing-identity paths.
- `web-research-agent`: confirmed no external web evidence is needed; GitHub current-head review URLs are the relevant evidence.
- Codex Security diff scan / finding discovery: no candidates for `f04d471110be400b7d9087cbec4ef1508a72b776` versus parent.
- `pulseplate-pr-review`: findings from Codex, CodeRabbit, Sourcery, Cubic, premortem, role passes, and Codex Security are dispositioned below.

## Premortem Closure

- Finding: Hidden caller break from required SHA kwargs.
  - Disposition: NOT-A-BUG
  - Evidence: `scripts/release/release_manifest.py:219` and `scripts/release/release_manifest.py:379` are the only repo call sites and both pass `build_git_sha` plus `ml_git_sha`.
  - Reason: The new required signature prevents silent future omissions while preserving validator missing-identity behavior through explicit `None` values.
- Finding: Fixture could become false evidence if `ml_identity.git_sha` and hash/validation were not updated together.
  - Disposition: FIXED
  - Commit: f04d471110be400b7d9087cbec4ef1508a72b776
  - Evidence: `tests/test_build_equivalence_evidence_workflow.py:70` adds the matching `ml_identity.git_sha`, `tests/test_build_equivalence_evidence_workflow.py:88` recomputes the fixture hash, and `tests/test_build_equivalence_evidence_workflow.py:91` validates the payload.
- Finding: Direct CLI/helper can accept matching noncanonical SHA strings.
  - Disposition: NOT-A-BUG
  - Evidence: `scripts/release/evidence_source.py:66` validates governed workflow SHAs as full 40-character hex, `.github/workflows/release-manifest-evidence.yml:121` applies that validation before release-manifest evidence publication, and this PR does not change direct CLI SHA-shape policy.
  - Reason: PR #1933 owns stale RAG/build binding, not a wider SHA-shape contract migration.
- Finding: Premortem evidence could drift from PR current head.
  - Disposition: FIXED
  - Commit: f04d471110be400b7d9087cbec4ef1508a72b776
  - Evidence: This artifact records the pre-closeout head, fix commit, role passes, Experiment Runner evidence, Codex Security no-findings result, and local focused gates.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Known Codex, CodeRabbit, Sourcery, Cubic, Codecov, role-agent, premortem, Experiment Runner, and Codex Security findings are fixed or dispositioned below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1933#discussion_r3386406604 -> f04d471110be400b7d9087cbec4ef1508a72b776
Disposition: FIXED
Commit: f04d471110be400b7d9087cbec4ef1508a72b776
Evidence: `tests/test_build_equivalence_evidence_workflow.py:70` now includes `ml_identity.git_sha` matching `build_identity.git_sha`; `tests/test_build_equivalence_evidence_workflow.py:88` rehashes the payload and `tests/test_build_equivalence_evidence_workflow.py:91` validates it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1933#pullrequestreview-4465631175 -> f04d471110be400b7d9087cbec4ef1508a72b776
Disposition: FIXED
Commit: f04d471110be400b7d9087cbec4ef1508a72b776
Evidence: `scripts/release/release_manifest.py:256` and `scripts/release/release_manifest.py:257` use required `str | None` keyword arguments for `build_git_sha` and `ml_git_sha`, replacing the prior `Any = None` hints.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1933#pullrequestreview-4465603203 -> f04d471110be400b7d9087cbec4ef1508a72b776
Disposition: FIXED
Commit: f04d471110be400b7d9087cbec4ef1508a72b776
Evidence: The required-SHA-kwargs Sourcery action is fixed at `scripts/release/release_manifest.py:256` and `scripts/release/release_manifest.py:257`. The missing-versus-mismatch semantics suggestion is dispositioned separately as NOT-A-BUG in this artifact.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1933#pullrequestreview-4465603203
Disposition: NOT-A-BUG
Evidence: `docs/release/RELEASE_MANIFEST_CONTRACT.md:128` documents that any missing or invalid required evidence results in `BLOCK` with deterministic reasons including `rag_git_sha_mismatch`; `scripts/release/release_manifest.py:264` preserves that fail-closed umbrella reason for missing, invalid, empty, or mismatched SHA values.
Reason: Splitting missing identity from mismatch would widen the release-manifest decision contract and is not required to close the stale RAG reuse vulnerability.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1933#pullrequestreview-4465689567
Disposition: NOT-A-BUG
Evidence: Cubic reported "No issues found" for reviewed commit `85c16be1da4d9ff8fa4c93eb03282cf6724867ec`; no actionable Cubic item requires code or docs changes.
Reason: The review contains no actionable finding to fix or defer.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1933#issuecomment-4667774398
Disposition: NOT-A-BUG
Evidence: CodeRabbit's walkthrough/comment is summary context only; the actionable CodeRabbit review item is mapped to `#pullrequestreview-4465631175` above.
Reason: No separate actionable item is present in the summary issue comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1933#issuecomment-4667774679
Disposition: NOT-A-BUG
Evidence: Sourcery's reviewer guide is summary context only; the actionable Sourcery review items are mapped to `#pullrequestreview-4465603203` above.
Reason: No separate actionable item is present in the reviewer-guide issue comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1933#issuecomment-4667828019
Disposition: NOT-A-BUG
Evidence: Codecov reported all modified and coverable lines are covered by tests.
Reason: The coverage report has no actionable remediation request.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path ...` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review` - PASS, packet `artifacts/orchestration/task_packets/pr_1933_post_open_review.json`.
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/pr_1933_post_open_review.json --mode review --pretty` - PASS; role order recorded above.
- `python3 -m py_compile scripts/release/release_manifest.py tests/test_release_manifest.py tests/test_build_equivalence_evidence_workflow.py` - PASS.
- `. .venv/bin/activate && PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_build_equivalence_evidence_workflow.py::test_build_identity_helper_derives_existing_contract_without_new_manifest_format tests/test_build_equivalence_evidence_workflow.py::test_build_identity_helper_rejects_invalid_manifest_and_placeholder_digest tests/test_release_manifest.py -p no:cacheprovider` - PASS (`25 passed`).
- `. .venv/bin/activate && PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_release_manifest.py tests/test_build_equivalence_evidence_workflow.py tests/test_release_manifest_evidence_workflow.py tests/test_build_equivalence.py tests/test_release_control_plane_ci_gate.py tests/test_production_release_evidence_wiring.py -p no:cacheprovider` - PASS (`105 passed`).
- `git diff --check` - PASS.
- Commit hook for `f04d471110be400b7d9087cbec4ef1508a72b776` - PASS, including black, ruff, Bandit changed-files, and backend changed-files pytest.

## Merge Readiness

- [ ] Current-head CI terminal success confirmed after this artifact commit is pushed.
- [ ] `pre-commit run --all-files` passes after mapping/body updates.
- [ ] Full local `make verify` is not used as local pass evidence for this lane; operator stopped the machine-heavy full run during coverage pytest and current-head CI parity remains required.
- [ ] PR body Phase2 mirror synchronized with this artifact.
- [ ] Strict review-thread disposition passes with auth.
- [ ] Strict merge-readiness wrapper passes with auth.
- [ ] No unresolved review threads or actionable bot comments remain.
- [ ] Mandatory wait-window after latest bot/review activity completed.

## Full Verify Deferral

- Operator instruction on 2026-06-11: "полный мейк верифай не делаем".
- Local `make verify` was stopped during the full coverage pytest phase and is not cited as PASS evidence.
- Completed before stop: `verify-env`, `flake8`, `mypy`, and smoke tests passed.
- The interrupted coverage pytest stream had failure markers before the stop, but no pytest failure summary was produced; no green or merge-ready claim is made from that run.
- Required remaining path: narrow local gates, `pre-commit run --all-files`, current-head CI parity, strict review-thread disposition, strict merge-readiness wrapper with auth, and the mandatory wait-window.
