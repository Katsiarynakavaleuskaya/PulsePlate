# PR 1394 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#pullrequestreview-4094056622 -> 9d875acd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068389834 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068389837 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#pullrequestreview-4094059624 -> 4bca99e5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068392173 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068392175 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068392178 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068392180 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068392181 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068392183 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#pullrequestreview-4094061749 -> 4bca99e5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068395085 -> 4bca99e5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#pullrequestreview-4094062879 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068396673 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068396675 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068396676 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068396677 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068396680 -> 404eb1c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068396685 -> 404eb1c0
Disposition: FIXED
Commit: 9d875acd, 404eb1c0, 4bca99e5
Evidence: `.github/workflows/npm-dependency-submission.yml:14` now runs the root npm dependency-submission lane for `pull_request` targets on `main`; `docs/orchestration/DEPENDABOT_ALERTS_105_106_RECONCILIATION_TASK_PACKET_2026-04-11.md:17` and `docs/security/CVE-2025-62718-axios.md:20` were corrected to match clean-`main` lockfile/runtime truth; `docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md:25` now includes concrete `file:line` evidence for the live `@goplus/agentguard -> axios` path.

Disposition: FIXED
Commit: 289da25a
Evidence: `docs/orchestration/DEPENDABOT_ALERTS_105_106_RECONCILIATION_TASK_PACKET_2026-04-11.md:98` now records the required `docs(agents)` instruction sync, including the exact mandatory lane order, the scoped `npm-dependency-submission.yml` workflow addition, and the explicit separation of the follow-up remediation lane.
Reason: Added the required `docs(agents): update instructions` commit requested by the latest CodeRabbit review cycle for workflow/agent-behavior changes in this reconciliation lane.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#discussion_r3068442511 -> 289da25a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1394#pullrequestreview-4094098027 -> 289da25a

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
- Scope: docs/workflow reconciliation for Dependabot `axios` alerts `#105` and `#106`, limited to current-truth correction, repo-managed npm dependency submission, and review-governance closure before a separate remediation PR.
