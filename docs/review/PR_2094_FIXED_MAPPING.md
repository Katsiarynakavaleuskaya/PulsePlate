# PR #2094 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2094
Branch: `security/cve-2026-53615-util-linux`

## Summary

Temporarily suppress CVE-2026-53615 for the exact Debian bookworm util-linux
binary package, installed-version, and PkgID tuples currently reported by the
fail-closed Docker publish scan. Record upstream monitoring, removal criteria,
and deterministic policy guards without weakening the scanner.

## Scope

- Add the exact CVE-2026-53615 package/version/PkgID Rego suppression.
- Add the canonical security note and backlog monitoring entry.
- Add deterministic expiry and exact-match guard coverage.
- Preserve shorter residual review windows for existing suppressions.

## Out Of Scope

util-linux package removal, base-image upgrades, `.trivyignore`, scanner
weakening, and unrelated CVE suppression changes.

## Implementation Commits

- `e50a871748298f5e669a92c6d3a7c1c58be3b46d` - add the scoped CVE-2026-53615 suppression, security note, guard, and monitoring.
- `041cbb6287d146650529988b0b8dc0b22b2bc0d1` - close premortem findings and record the CVE-2026-3184 exact-match follow-up.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/13d631bf0738.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Required pre-open role order:
  `agent-coordinator -> security-auditor -> architecture-specialist -> qa-engineer-agent -> bug-hunter`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial post-open discussion inventory completed; no actionable review comments existed when this artifact was created.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass complete.
- [ ] Codex Security diff scan / finding discovery complete.
- [ ] `pulseplate-pr-review` complete.
- [ ] Current-head CI complete.
- [ ] Strict merge-readiness checks complete after the final review cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Premortem Dispositions

### F1 — residual suppression review horizon

Disposition: FIXED
Commit: `041cbb6287d146650529988b0b8dc0b22b2bc0d1`
Evidence: `trivy/ignore-policy.rego` keeps zlib, CVE-2026-3184, and ncurses at the shorter `2026-08-08` Review-by date.
Reason: The shared file expiry does not silently extend older exceptions to the new CVE's 90-day horizon.

### F2 — PkgID wording and exact equality

Disposition: FIXED
Commit: `041cbb6287d146650529988b0b8dc0b22b2bc0d1`
Evidence: `docs/security/CVE-2026-53615-util-linux.md` and `tests/test_trivy_ignore_policy_expiry.py` state and enforce exact PkgID equality.
Reason: Documentation and deterministic guards now match the fail-closed Rego implementation.

### F3 — inherited CVE-2026-3184 prefix matching

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cve-2026-3184-exact-pkgid-match`
Evidence: Commit `041cbb6287d146650529988b0b8dc0b22b2bc0d1` records owner, priority, rationale, target PR placeholder, links, and DoD.
Reason: Tightening a different CVE belongs to its own CVE-scoped security PR.

### F4/F6/F7 — scoped suppression and release behavior

Disposition: NOT-A-BUG
Evidence: `trivy/ignore-policy.rego`, `docs/security/CVE-2026-53615-util-linux.md`, and `.github/workflows/build.yml` retain fail-closed scanning and exact observed package scope.
Reason: The change neither disables Trivy nor broadens package/version matching, and rollback restores fail-closed failure on this CVE.

### Main suppression implementation

Disposition: FIXED
Commit: `e50a871748298f5e669a92c6d3a7c1c58be3b46d`
Evidence: `trivy/ignore-policy.rego`, `docs/security/CVE-2026-53615-util-linux.md`, `tests/test_trivy_ignore_policy_expiry.py`, and `docs/roadmap/BACKLOG_LEDGER.md`.
Reason: The implementation suppresses only the observed CVE/package/version/PkgID tuples and records expiry, monitoring, and removal conditions.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-2b097776673e.json`
- Mode: oracle-only governance review.
- Oracles: expiry checker and focused pytest passed.
- The artifact does not authorize GitHub writes, review-thread resolution, or merge-readiness claims.

## Validation Evidence

- `python scripts/ci/check_trivy_ignore_policy_expiry.py` - PASS.
- `pytest -q tests/test_trivy_ignore_policy_expiry.py` - PASS.
- `python scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-53615-util-linux.md` - PASS.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS.
- Pre-push hook - PASS, including pip-audit, changed backend tests, full-repo Bandit, and applicable Docker checks.

## Local Verification Exception

Local `make verify` was not run, in accordance with the repository local
full-verify budget rule. Heavy verification remains a current-head CI signal.

## Merge Readiness

- [x] Pre-open role order completed.
- [x] Premortem findings fixed, dispositioned, or backlog-tracked.
- [x] Experiment Runner oracle-only evidence recorded.
- [x] Branch pushed and non-draft PR opened.
- [ ] Mandatory post-open role and review chain completed.
- [ ] Current-head required CI completed successfully.
- [ ] Review bots report no unresolved actionable findings.
- [ ] Strict authenticated merge-readiness wrapper passes after the wait-window.

Merge readiness is not claimed.
