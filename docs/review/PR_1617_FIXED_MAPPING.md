# PR #1617 Fixed Mapping

## PR

- URL: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1617
- Branch: `security/code-scanning-588-libcap2-cve-2026-4878`
- Title: `security: triage libcap2 CVE-2026-4878 Trivy alert 588`

## Scope

- Narrow temporary Trivy suppression for libcap2 CVE-2026-4878 (code-scanning alert #588)
- Security advisory doc with evidence and removal condition
- Backlog ledger P1 follow-up entry for suppression removal
- No runtime, OpenAPI, billing, frontend, iOS, or AI changes

## Local Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `python3 scripts/ci/check_trivy_ignore_policy_expiry.py` PASS (no output = success).
- `pre-commit run --all-files` PASS.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Status: No prior review threads (new PR).

## Fixed in Commit Mapping

No review threads to map (initial PR open).

## Merge Readiness

- [x] Local gates green
- [x] Trivy expiry check green
- [ ] CI current-head checks green
- [ ] No actionable bot comments (pending first review cycle)
- [x] Canonical review artifact created
- [ ] Wait-window elapsed after last review activity
