# PR #1626 Fixed in Commit Mapping

## Summary

PR #1626 triages GitHub Code Scanning alert #589 for `libgnutls30` / `CVE-2026-33845`.

## Scope

- `docs/security/CVE-2026-33845-gnutls.md`
- `trivy/ignore-policy.rego`
- `docs/roadmap/BACKLOG_LEDGER.md`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1626#pullrequestreview-4215081881

Disposition: NOT-A-BUG (fallback branches) / FIXED (evidence anchors)

Evidence (fallback branches): The `not input.Image` / `not input.Distro` fallback pattern is intentionally consistent with existing CVE-2026-41989 (`trivy/ignore-policy.rego:147-157`) and CVE-2026-4878 (`trivy/ignore-policy.rego:299-311`) blocks. The fallback is justified because Trivy sometimes omits these fields in certain scan contexts; the suppression still requires exact CVE + package + version + pkgID prefix match, preventing unintended suppression. Inline justification comments have been added.

Evidence (evidence anchors): Hard-coded line numbers replaced with named anchor (`anchor:cve-2026-33845-gnutls-suppression`) and ledger anchor ID.

## Validation

- `python3 scripts/orchestration/check_preflight.py` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- `python3 scripts/ci/check_trivy_ignore_policy_expiry.py` -> PASS (exit 0)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-33845-gnutls.md` -> PASS
- `pre-commit run --all-files` -> PASS
- `git diff --check` -> clean

## Merge Readiness

- [ ] CI green
- [ ] Security policy tests green
- [ ] Review mapping artifact complete
- [ ] No actionable bot comments remain
- [ ] Mandatory wait-window elapsed
