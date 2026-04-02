# PR 1298 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1298_FIXED_MAPPING.md`
Reason: Initial post-open pass found no actionable review comments on PR `#1298` at artifact creation time.

Disposition: FIXED
Commit: ed3f121d
Evidence: `docs/audit/PR4_ENTITLEMENT_ROUTING_CLOSEOUT_AUDIT_2026-04-02.md`
Reason: The post-open bug-hunter pass found one actionable docs defect on the opened PR: the audit packet used absolute local filesystem links that do not work in GitHub review context. Commit `ed3f121d` removed those links and kept repo-portable `file:line` evidence only.

Disposition: FIXED
Commit: f0403c72
Evidence: `docs/review/PR_1298_FIXED_MAPPING.md`
Reason: Codex connector and cubic identified the same closeout-artifact accounting problem: mixed mapping modes and an internally inconsistent disposition record inside `## Fixed in Commit Mapping`. Commit `f0403c72` normalized the section to structured disposition blocks only.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#pullrequestreview-4049529020 -> f0403c72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#discussion_r3026961772 -> f0403c72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#discussion_r3026995833 -> f0403c72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#discussion_r3026995837 -> f0403c72

Disposition: NOT-A-BUG
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:53`
Reason: CodeRabbit's review-level nitpick referenced an earlier diff snapshot. On the current head the ledger already reads `PR #1296 (activation/persistence closeout) -> PR-TBD-BILLING-ENTITLEMENT-ROUTING`, so no further text change is required for this PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#pullrequestreview-4049505034

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1298-doc-governance-followup`
Reason: Sourcery suggested deduplicating repeated evidence anchors in the audit packet and introducing a single clearly labeled PR1-PR4 sequencing SoT across the audit and roadmap docs. Those are valid governance refinements, but they are outside the narrow PR4 entitlement-routing closeout scope and are deferred to a docs/governance follow-up.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1298#pullrequestreview-4049488678

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
- Scope: PR4 entitlement-routing closeout packet only. Current-head runtime authz already satisfies the narrow fail-closed routing contract, so this lane is limited to canonical audit and roadmap/governance truth sync.
