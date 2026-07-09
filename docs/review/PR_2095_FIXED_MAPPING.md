# PR #2095 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2095
Branch: `hotfix/cve-2026-53615-fixedversion-omitempty`

## Summary

Fix the CVE-2026-53615 suppression fallout from PR #2094 by treating Trivy
v0.71.2's omitted `FixedVersion` field as unfixed while preserving fail-closed
behavior whenever a non-empty fixed version is reported.

## Scope

- Replace direct empty-string equality with an omission-safe Rego lookup.
- Guard the exact omission-safe predicate in the focused policy test.
- Record failed Docker publish run 29052278755 as remediation evidence.

## Out Of Scope

Package upgrades, base-image changes, unrelated suppressions, alert dismissal,
and weakening the fail-closed Docker publish scan.

## Implementation Commits

- `3d0b8356f` - handle omitted Trivy `FixedVersion`, update the focused guard,
  and record failed-run evidence.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/8f47dd181d21.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Required pre-open role order:
  `agent-coordinator -> security-auditor -> architecture-specialist`

## Discussion Thread Pass

- [x] Initial discussion-thread inventory completed; no review threads existed at artifact creation.
- [x] Fixed in commit mapping completed for the implementation fallout.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI completed.
- [ ] Strict merge-readiness checks completed after the final review cycle.

## Fixed in Commit Mapping

### PR #2094 Docker publish fallout

Disposition: FIXED
Commit: `3d0b8356f`
Evidence: `trivy/ignore-policy.rego:157-161` uses omission-safe `object.get` while
`tests/test_trivy_ignore_policy_expiry.py:450-468` guards the exact predicate,
and `docs/security/CVE-2026-53615-util-linux.md:48-72` records the failed run.
Reason: Trivy v0.71.2 omits empty `FixedVersion` values from Rego input, so the
prior direct equality could not match the eight otherwise-correct findings.

## Experiment Runner Evidence

- Infrastructure blocker: oracle-only packet bootstrap stalled locally before
  artifact creation; no result artifact or readiness authority is claimed.
- The operator explicitly requested the canonical co-author trailer on the
  implementation commit for this urgent hotfix.

## Validation Evidence

- `python scripts/ci/check_trivy_ignore_policy_expiry.py` - PASS.
- `pytest -q tests/test_trivy_ignore_policy_expiry.py` - PASS (18 tests).
- `python scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-53615-util-linux.md` - PASS.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS.
- Pre-push hook - PASS, including pip-audit, focused backend tests, and full-repo Bandit.

## Deferred / Follow-ups

- No new deferred work was introduced.
- Existing monitoring remains in force: remove the suppression after Debian
  publishes a fixed util-linux package and main Docker publish confirms it.
- Alerts #623-#630 remain open until this hotfix lands and replacement scan
  results are published from `main`.

## Local Verification Exception

Local `make verify` was not run, in accordance with the repository local
full-verify budget rule. Heavy verification remains a current-head CI signal.

## Merge Readiness

- [x] Focused implementation and local required gates completed.
- [x] Branch pushed and non-draft PR opened.
- [ ] Mandatory post-open role-agent pass completed.
- [ ] Codex Security and `pulseplate-pr-review` passes completed.
- [ ] Current-head required CI completed successfully.
- [ ] Review bots report no unresolved actionable findings.
- [ ] Strict authenticated merge-readiness wrapper passes after the wait-window.

Merge readiness is not claimed.
