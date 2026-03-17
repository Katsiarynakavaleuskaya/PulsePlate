# PR 1184 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 68c79280
Evidence: docs/roadmap/BACKLOG_LEDGER.md:35 Target PR set to PR #1184 (CodeRabbit r2946264280).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946264280 -> 68c79280

Disposition: FIXED
Commit: 16d902a7
Evidence: scripts/ops/postgres_restore.sh (usage), docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md (DB fallback verbs).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946208015 -> 16d902a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946208021 -> 16d902a7

Disposition: FIXED
Commit: d392a601
Evidence: scripts/ops/postgres_restore.sh — path normalization before cd (Cubic r2946901107).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946901107 -> d392a601

Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-postgres-backup-restore-hardening
Reason: Valid operational hardening; out of narrow infra-wave scope. One follow-up PR: infra/p1-postgres-backup-restore-hardening.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946225587
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946233285
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946233291
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946264287
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946264299

Disposition: NOT-A-BUG
Evidence: /health/db per PR DoD; file:line required for docs/audit and docs/security only.
Reason: .env.example and FIXED_MAPPING pre-commit are style/optional; no code changes required.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#pullrequestreview-3960158912
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#pullrequestreview-3960184617
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946264260
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946264277
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#pullrequestreview-3960216980
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946536336
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946536348
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#pullrequestreview-3960503190
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#discussion_r2946616865
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#pullrequestreview-3960589867
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1184#pullrequestreview-3960622779

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] Pre-commit green
