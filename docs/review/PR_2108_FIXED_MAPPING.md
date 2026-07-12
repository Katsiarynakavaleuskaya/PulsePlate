# PR #2108 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2108

Branch: `codex/fix-excon-cve-2026-54171`

## Summary

This PR remediates Dependabot alert #231 by upgrading the compatible Fastlane
release-tool graph to `2.237.0` and Excon to patched `1.5.0`, with deterministic
guards, exact advisory evidence, fail-closed rollback, and no upload authority.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed
- [x] Codex Security exact-head diff scan completed with 0 findings
- [x] `pulseplate-pr-review` completed
- [ ] Current-head CI completed
- [ ] Mandatory review wait-window and strict merge-readiness completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 324670760
Evidence: `docs/security/CVE-2026-54171-excon-fastlane.md` now carries exact `file:line` anchors; `docs/security/CVE-2026-54297-faraday-fastlane.md` points to current Faraday/Fastlane lock lines; Phase1 docs gates pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/commit/324670760 -> 324670760

Disposition: FIXED
Commit: 734146124
Evidence: `docs/security/CVE-2026-54171-excon-fastlane.md` explains the Excon `RedirectFollower` cross-target sensitive-header disclosure and the `1.5.0` fix; Phase1 docs gates pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/commit/734146124 -> 734146124

Disposition: FIXED
Commit: a4886cd6d
Evidence: The Excon floor now reuses the repository's prerelease-aware version comparator and covers shortened and prerelease versions; the Faraday evidence separates the resolver command from resulting lock entries; focused tests and docs gates pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2108#pullrequestreview-4680869413 -> a4886cd6d

Disposition: NOT-A-BUG
Evidence: PR #2108 adds no production functions: its executable changes are deterministic test guards, while the remaining surfaces are dependency manifests and documentation. The CodeRabbit docstring warning is therefore not a missing production-docstring defect. Sourcery emitted no code finding because its external weekly quota was exhausted; the mandatory repo role chain, Codex Security, and PulsePlate PR review remain the reviewed evidence sources.
Reason: A zero-percent docstring metric over a manifest/docs/test-only diff is not an actionable product defect, and an external review-quota message contains no code finding to fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2108#issuecomment-4952946956
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2108#pullrequestreview-4680862825

## Post-open Role Findings

### QA Engineer Agent

Disposition: FIXED
Commit: 324670760
Evidence: QA reproduced the docs Phase1 failure for missing anchors and a stale Faraday line; the focused docs gate and 25 dependency/toolchain tests pass after the fix.

### Bug Hunter

Disposition: FIXED
Commit: 734146124
Evidence: Bug-hunter identified the missing advisory-specific impact; the CVE evidence now names `RedirectFollower`, cross-target header leakage, confidentiality impact, and patched version.

### Security Auditor

Disposition: NOT-A-BUG
Evidence: Exact-head review confirmed Fastlane `2.237.0`, Excon `1.5.0`, the compatible `>=0.71.0,<2.0.0` edge, no suppression, fail-closed rollback, and no workflow/Fastfile/upload/App Store mutation.
Reason: No security actionable remained after the QA and bug-hunter fixes.

### Codex Security

Disposition: NOT-A-BUG
Evidence: Exact-head scan `bad2b504-dc43-4c07-9e85-c854fc48ab2e` reviewed the dependency/security contract at `734146124`; the canonical executable production-code worklist contained zero rows and contextual review of all 9 paths produced 0 findings.
Reason: No candidate survived the dependency-focused discovery and threat-model gates.

### PulsePlate PR Review

Disposition: FIXED
Commit: this mapping commit
Evidence: Dry-run review emitted only the expected missing fixed-mapping artifact warnings. This canonical artifact closes that governance gap; no correctness, security, or release finding was emitted.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-70e5d3e92642.json

- Accepted `oracle_only_governance_reviewer` result with 2/2 oracle commands.
- `mutated_paths=[]`, `shared_tree_untouched=true`, and no promotion authority.
- Material-contribution commits use the canonical Experiment Runner co-author trailer.

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/af0c0437b06f.json

Starter: scripts/orchestration/start_pr_lane.sh

## Validation Evidence

- PASS: `bundle check` against the isolated resolved bundle.
- PASS: no-auth `bundle exec fastlane ios validate_metadata_package`.
- PASS: metadata and HealthKit-copy validators; no upload executed.
- PASS: 25 focused runtime-toolchain and Trivy-policy tests.
- PASS: Phase1 docs gates.
- PASS: `python3 scripts/orchestration/check_preflight.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS: pre-push dependency audit, backend tests, and full-repo Bandit.
- Not run: local `make verify`, per repository machine-budget policy.

## Merge Readiness

Not claimed. Current-head CI, external review-bot disposition, the mandatory
wait-window, zero unresolved/actionable threads, and strict authenticated
merge-readiness must pass first.

## Deferred / Follow-ups

- Ruby 3.3 Fastlane runtime migration is tracked at
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ruby-3-3-fastlane-runtime`.
- Confirm Dependabot alert #231 closes after merge and dependency-graph refresh.
