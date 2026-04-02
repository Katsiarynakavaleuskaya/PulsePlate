# PR 1298 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1298_FIXED_MAPPING.md`
Reason: Initial post-open pass found no actionable review comments on PR `#1298` at artifact creation time.

Disposition: FIXED
Commit: `ed3f121d`
Evidence: `docs/audit/PR4_ENTITLEMENT_ROUTING_CLOSEOUT_AUDIT_2026-04-02.md`
Reason: The post-open bug-hunter pass found one actionable docs defect on the opened PR: the audit packet used absolute local filesystem links that do not work in GitHub review context. Commit `ed3f121d` removed those links and kept repo-portable `file:line` evidence only.

Disposition: FIXED
Commit: `f0403c72`
Evidence: `docs/review/PR_1298_FIXED_MAPPING.md`
Reason: Codex connector and cubic identified the same closeout-artifact accounting problem: mixed mapping modes and an internally inconsistent disposition record inside `## Fixed in Commit Mapping`. Commit `f0403c72` normalized the section to structured disposition blocks only.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#discussion_r3026961772 -> f0403c72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#discussion_r3026995833 -> f0403c72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#discussion_r3026995837 -> f0403c72

Mandatory post-open review lane for this packet:
- `qa-engineer-agent -> bug-hunter`

Post-open review notes:
- QA review on the opened PR found no runtime/authz drift beyond the documentation packet itself.
- Bug-hunter pass on the opened PR found one actionable docs defect: the audit packet used absolute local filesystem links that do not work in GitHub review context. The current branch revision removes those links and keeps repo-portable `file:line` evidence only.

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
- Scope: PR4 entitlement-routing closeout packet only. Current-head runtime authz already satisfies the narrow fail-closed routing contract, so this lane is limited to canonical audit and roadmap/governance truth sync.
