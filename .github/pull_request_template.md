<!-- markdownlint-disable MD013 -->

# Pull Request

## Goal

<!-- Concrete outcome this PR must produce. -->

## Business reason

<!-- Revenue, retention, trust, automation, operations, or risk reduction. -->

## Scope

<!-- Narrow in-scope behavior and contracts. -->

## Out of scope

<!-- Explicit boundaries that keep the lane auditable. -->

## Files changed

<!-- Important production, test, workflow, and contract surfaces. -->

## Key decisions

<!-- Decisions whose trade-offs a reviewer must understand. -->

## Tests

<!-- Exact local commands and current-head CI evidence; distinguish pending from passed. Review relevant guidance in docs/ENGINEERING_LESSONS.md. -->

## Security notes

<!-- Privileged surfaces, trust boundaries, threat model, or Not applicable with reason. -->

## Risks / rollback

<!-- Failure modes, observability, and the exact safe rollback. -->

## Discussion Thread Pass

<!-- Change both boxes to [x] only after the canonical artifact is complete. -->

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

<!-- phase2-pre-closeout: final-security-pending -->

### Fixed in Commit Mapping

<!--
Closeout automation must replace the entire Phase2 block from
`## Discussion Thread Pass` through the line before `## Split justification`
with the complete block produced by
scripts.orchestration.review_mapping_artifact.render_phase2_body_mirror(...)
for the live PR number, repository, and exact head ref.
-->

- Pending final clean scan and the single mapping/closeout commit.
- URL→SHA and disposition details belong only in the canonical artifact.

## Split justification

<!-- Required only above the Tier 1 800 changed-LoC threshold. -->

- Why this PR cannot be split safely:
- Invariant or rollout constraint requiring one PR:
- Follow-up PRs:

## Deferred / Follow-ups

<!-- Ledger links or None. -->

## Next best step

<!-- One bounded action after this PR. -->

<!-- markdownlint-enable MD013 -->
