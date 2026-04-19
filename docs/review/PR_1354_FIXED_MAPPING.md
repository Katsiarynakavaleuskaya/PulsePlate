<!-- markdownlint-disable MD034 -->
# PR 1354 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 12f1f9872340a0e3ef8bd8f7e46967718f108bd0
Evidence: `scripts/orchestration/task_bootstrap.py:568` (`allowed_promotions`), `:575` (graph precedence over non-routable); `docs/orchestration/AGENT_NON_ROUTABLE_SPECIALISTS.md:10`; `docs/orchestration/AGENT_ROUTING_GRAPH.md:116`; `docs/roadmap/BACKLOG_LEDGER.md:149`; `tests/test_task_bootstrap.py:1856`
Reason: Codex P1 thread: keep non-routable promotions bounded by canonical graph slots (implementation + regression test). CodeRabbit threads: add explicit `file:line` evidence in orchestration docs and ledger status line; align backlog closure wording with mandatory docs-only follow-up policy.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1354#discussion_r3039135619 -> 12f1f9872340a0e3ef8bd8f7e46967718f108bd0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1354#discussion_r3039148998 -> 12f1f9872340a0e3ef8bd8f7e46967718f108bd0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1354#discussion_r3039149004 -> 12f1f9872340a0e3ef8bd8f7e46967718f108bd0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1354#discussion_r3039149006 -> 12f1f9872340a0e3ef8bd8f7e46967718f108bd0

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1354_FIXED_MAPPING.md:1`; Sourcery output is a reviewer guide / summary, not a single fix thread tied to a code defect.
Reason: No code change required for the Sourcery review body; inline review threads above carry the actionable items.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1354#pullrequestreview-4061634319

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1354_FIXED_MAPPING.md:1`; CodeRabbit summary review mirrors threaded findings already mapped with FIXED dispositions above.
Reason: Avoid duplicate FIXED mapping against the aggregate review URL; per-thread resolutions are recorded on the four `discussion_r` links.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1354#pullrequestreview-4061651926

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green locally

Notes: Resolve review threads after mapping; refresh checkboxes when CI is green.

<!-- markdownlint-enable MD034 -->
