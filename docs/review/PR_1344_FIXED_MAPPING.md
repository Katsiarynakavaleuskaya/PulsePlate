<!-- markdownlint-disable MD034 -->
# PR 1344 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1344#pullrequestreview-4059602669
Disposition: NOT-A-BUG
Evidence: `scripts/ci/check_pr_body_phase2_gates.py:24` hard-codes the canonical Phase2 checkbox label as `Discussion-thread pass completed`, and `scripts/ci/check_pr_body_phase2_gates.py:138`-`scripts/ci/check_pr_body_phase2_gates.py:142` fail CI unless that exact checked label is present in the artifact.
Reason: The Sourcery wording suggestion is stylistically reasonable, but this PR must preserve the contract-frozen checkbox text required by the repo's Phase2 validator.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1344#discussion_r3037031377
Disposition: NOT-A-BUG
Evidence: `scripts/ci/check_pr_body_phase2_gates.py:24` and `scripts/ci/check_pr_body_phase2_gates.py:138`-`scripts/ci/check_pr_body_phase2_gates.py:142` require the exact checked label `Discussion-thread pass completed`, so keeping the hyphen is contract-correct for this artifact.
Reason: This inline Sourcery thread requests the same wording change as the parent review and is intentionally closed with the same contract-based rationale.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1344#pullrequestreview-4059620641
Disposition: FIXED
Evidence: `2eadb894`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1344#discussion_r3037055700 -> 2eadb894
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1344#discussion_r3037055702 -> 2eadb894

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
Notes: This continuation PR supersedes stale Dependabot PR #1336 because the original PR head is pinned to a detached hidden source ref that no longer tracks live branch updates. The branch already includes the Linux/x86_64 marker restoration for torch transitive CUDA/Triton packages, and local validation passes on April 5, 2026.
<!-- markdownlint-enable MD034 -->
