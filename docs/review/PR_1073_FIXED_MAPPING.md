# PR 1073 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `fcc107db` rebuilt PR #1073 on top of `origin/main` and removed the unintended `AGENTS.md` / `docs/runbooks/ENGINEER_QUICKPATH.md` drift from the PR diff, while preserving the intended PR1 scope; `86b56fbf` added the required root `AGENTS.md` sync, completed the deferred ledger block fields, switched the canonical workflow preflight command to module form, and restored the missing CV ledger anchor; `40825f7f` adds the exact `docs(agents): update instructions` follow-up commit requested by CodeRabbit and extends the root instructions with the immutable-oracle guard and PR1→PR6 rollout sequence.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#pullrequestreview-3921934779 -> fcc107db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911295085 -> fcc107db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911295090 -> fcc107db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911295095 -> fcc107db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911321991 -> fcc107db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911321996 -> fcc107db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911321998 -> fcc107db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#pullrequestreview-3922136298 -> 86b56fbf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911509358 -> 86b56fbf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911509378 -> 86b56fbf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911509385 -> 86b56fbf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911509406 -> 86b56fbf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911509410 -> 86b56fbf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1073#discussion_r2911591286 -> 40825f7f
