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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1626#pullrequestreview-4215081881 -> 1be7f9f4f
Disposition: FIXED
Commit: 1be7f9f4f
Evidence: `trivy/ignore-policy.rego:181` — added anchor comment and fallback justification inline comments; `docs/security/CVE-2026-33845-gnutls.md:69` — evidence anchors now include named anchor reference.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1626#pullrequestreview-4215085954 -> 298c5c445
Disposition: FIXED
Commit: 298c5c445
Evidence: `docs/review/PR_1626_FIXED_MAPPING.md:1` — mapping artifact rewritten with proper URL->SHA format and explicit dispositions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1626#discussion_r3176737683 -> 298c5c445
Disposition: FIXED
Commit: 298c5c445
Evidence: `docs/review/PR_1626_FIXED_MAPPING.md:1` — mapping now includes `file:line` evidence per item and explicit dispositions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1626#discussion_r3176737687 -> 298c5c445
Disposition: FIXED
Commit: 298c5c445
Evidence: `docs/review/PR_1626_FIXED_MAPPING.md:1` — placeholder replaced with explicit FIXED dispositions and checked checklist entries.

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
