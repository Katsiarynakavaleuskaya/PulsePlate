# PR #2137 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2137

Branch: `codex/fix-cd-trivy-policy-parity`

## Summary

Restore the push-only `main` CD security gate by aligning the staged backend
digest scan with the canonical repository Trivy policy while keeping the
Alpine Caddy digest scan explicitly suppression-free. Preserve immutable image
digests, fail-closed deployment ordering, the pinned scanner/action versions,
and all public/runtime contracts.

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/a4230146f0ae.json

- The preflight and infrastructure task bootstrap packet is local-only and
  gitignored.
- The startup role order executed as
  `agent-coordinator -> dev-operator -> architecture-specialist -> security-auditor`.
- The actual-diff premortem ran before PR open and its bounded failure scenarios
  were either closed in the implementation or dispositioned below.
- Experiment Runner oracle-only result
  `artifacts/orchestration/experiments/results/cd-trivy-policy-parity-oracle-final-result.json`
  is local-only and gitignored. It was accepted with 2/2 immutable oracles,
  zero retries, no candidate mutation, and an untouched shared tree. Its
  contribution kind is `none`, so no co-author trailer applies.

## Implementation Commits

- `46fccc221c73d1c0c6f2958a270c8d8107382e2f` - add fail-closed Trivy policy
  preparation and exact staged-digest scan contracts.
- `fe7ff2017029ee9ede21264f2fbe19dca1ce23a2` - keep the Caddy/Alpine scan
  suppression-free while retaining canonical policy only for backend/Debian.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Startup packet and declared role order completed.
- [x] Actual-diff premortem completed with no open blocker.
- [x] Experiment Runner oracle-only evidence accepted.
- [x] Remediation role order completed as
  `agent-coordinator -> dev-operator -> architecture-specialist -> qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] A renewed Codex Security diff scan completed for the final material diff.
- [x] `pulseplate-pr-review` completed on the remediated material head.
- [x] All current review threads have an evidence-backed disposition.
- [ ] The mapped review thread is resolved after this artifact and its PR-body
  mirror are published and the authenticated disposition guard passes.
- [ ] Current-head CI, strict authenticated merge readiness, and the mandatory
  quiet review cycle are complete.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: fe7ff2017029ee9ede21264f2fbe19dca1ce23a2
Evidence: `.github/workflows/cd.yml:303-307` creates and verifies a fresh empty regular ignore file; `.github/workflows/cd.yml:322-344` keeps canonical ignore and Rego inputs backend-only while Caddy uses that empty file and no Rego; `tests/test_caddy_deploy_provenance.py:154-216` locks the preparation order and distinct exact scan contracts; a direct Trivy `0.71.2` scan of the published Caddy digest with the explicit empty ignore and no Rego returned zero HIGH/CRITICAL findings.
Reason: The original implementation applied backend/Debian suppressions to the Caddy/Alpine scan; the remediation overrides Trivy's implicit repository-root `.trivyignore` for Caddy without adding any waiver or weakening the HIGH/CRITICAL fail-closed gate, and pinned-action inspection confirms that each invocation resets Trivy environment state and truncates its generated plain ignore file so backend policy cannot leak into Caddy.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2137#discussion_r3586535889 -> fe7ff2017029ee9ede21264f2fbe19dca1ce23a2

## Premortem Closure

- Missing or stale policy input: closed by file, non-empty-copy, and byte-parity
  checks before either scan.
- Mutable image reference or deploy-before-scan drift: closed by existing
  digest-output validation and the deterministic
  `prepare -> backend scan -> Caddy scan -> deploy` contract.
- Cross-distribution suppression: surfaced by review and fixed in `fe7ff201`;
  backend owns the canonical Debian policy and Caddy is suppression-free.
- Scanner/action drift or cache collision: closed by the exact action SHA,
  Trivy `v0.71.2`, fixed database repository, and distinct cache directories.
- Secret-scan regression: not part of the image-vulnerability contract;
  `scanners: vuln` aligns CD with the canonical vulnerability lane while secret
  coverage remains with separate repository and CI guards.
- Rollback masking the outage: closed by documenting that reverting the
  eventual PR/squash commit deliberately returns CD to a fail-closed red state
  until a replacement fix is available.

## Validation Evidence

- PASS: orchestration preflight and agent consistency on material head
  `fe7ff2017029ee9ede21264f2fbe19dca1ce23a2`.
- PASS: 74 focused Caddy/CD contract, workflow-governance, and Trivy-policy
  expiry tests.
- PASS: `make validate-changed` selected and passed 21 tests.
- PASS: `pre-commit run --all-files`.
- PASS: full pre-push hooks, including MyPy, `pip-audit`, backend tests,
  Bandit, and the Docker build test.
- PASS: direct remote-digest backend scan with canonical policy and Caddy scan
  with the explicit empty regular ignore and no Rego, both on Trivy `0.71.2`,
  with zero HIGH/CRITICAL findings.
- PASS: fail-closed negative smokes for missing `.trivyignore` and missing
  `trivy/ignore-policy.rego`; Caddy ignore preparation also rejects a retained
  symlink/non-empty file state.
- PASS: Experiment Runner oracle-only `git diff --check` and the 74-test focused
  suite in Apple Container `1.1.0`; artifact SHA-256
  `af017507e9db854935ba605298d6ff70a673e52b933a519183fbb319a9f5d410`.
- NOT RUN: local full `make verify`; prohibited by the repository local budget
  rule.
- CURRENT-HEAD CI: must run again on the mapping/body publication head; no
  predecessor or canceled run is final merge evidence.

## Security Review

- PASS: the ordered post-open/remediation security-auditor found no remaining
  actionable issue after the cross-distribution suppression fix.
- PASS: authoritative Codex Security scan
  `a6fc1013-279e-4bef-ab3a-d93af5722f91` sealed the complete exact material
  range
  `7c149a84c44406f698d73fbd0dee0bd34b64d085...fe7ff2017029ee9ede21264f2fbe19dca1ce23a2`
  with zero findings and 2/2 completed coverage rows. Snapshot digest:
  `codex-security-snapshot/v1:sha256:10b73623cb5865aafe386e40f539fe50df5d69a643434c89fdfe797072f37f86`;
  sealed report SHA-256:
  `7142ea9cc58ebe1cc5f120ee548786ebc80da5948929b62a948e1a8fd415f5c7`.
- The earlier scan of `46fccc221` was invalidated by the material P1
  remediation and is not merge-readiness evidence for the final material diff.
- PASS: remediated `pulseplate-pr-review` found no code, security,
  architecture, or QA defect. Its only findings are the expected governance
  notes that this artifact was not yet present; local report SHA-256:
  `65581cec06529039949c2cd5d8f51d6db6d7f2b71b8b7286ed2885e2fb8bb0c6`.

## External Review Sources

- CodeRabbit: current material-head check completed successfully with no new
  actionable inline feedback.
- Sourcery: current material-head status check completed successfully and
  reports no blocking security issue; its substantive review body remained
  source-degraded by the weekly quota and is not represented as a completed
  code review.
- Cubic: source-degraded/neutral because its monthly line quota was reached; it
  produced no review comments or actionable finding and is not represented as
  a PASS.
- Codex GitHub review: one P1 thread, fixed and mapped above; no other review
  thread exists at this publication point.

## Risks / Rollback

The workflow remains fail closed: absent policy inputs, a scan finding, or a
scanner failure stops deployment. Caddy does not inherit a Debian-specific
waiver. Rollback is a revert of the whole eventual PR/squash commit; that
intentionally restores the prior fail-closed red CD until a replacement fix is
approved. Do not weaken the security gate as rollback mitigation.

## Deferred / Follow-ups

None in this hotfix. A Trivy `0.72.0` upgrade remains a separate lane and is not
required to restore canonical-policy parity at the repository pin.

## Merge Readiness

- PASS: functional diff remains limited to `.github/workflows/cd.yml` and
  `tests/test_caddy_deploy_provenance.py`; this canonical mapping is the only
  tracked governance addition.
- PASS: local narrow bundle and exact material-diff security/review passes are
  recorded above.
- PENDING final merge cycle: publish this fixed mapping and the exact PR-body
  mirror, then resolve only the mapped FIXED thread after authenticated
  disposition validation.
- PENDING final merge cycle: require terminal canonical CI and diff coverage
  at least 97% on the exact final head, with no required pending or failed job.
- PENDING final merge cycle: require no actionable bot feedback and zero
  unresolved review threads.
- PENDING final merge cycle: require strict authenticated
  `check_merge_ready.py --require-auth` and one quiet review cycle after the
  latest bot/review activity.
- PENDING post-merge: require successful push-only CD on the exact squash merge
  SHA, including both staged digest scans and the full workflow, before any
  local worktree/cache cleanup.
