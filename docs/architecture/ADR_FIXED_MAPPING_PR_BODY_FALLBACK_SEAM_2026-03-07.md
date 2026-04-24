# ADR: Fixed Mapping PR-Body Fallback Seam (2026-03-07)

- Status: Accepted (temporary seam)
- Date: 2026-03-07
- Owner: @katsiaryna_kavaleuskaya

## Context

`docs/review/PR_<N>_FIXED_MAPPING.md` is now the canonical source of truth for
review-thread disposition and merge-readiness mapping.

However, one compatibility seam still exists:

- PR pages need a human-readable mirror of the same governance sections.
- Local/body-only runs of `scripts/ci/check_pr_body_phase2_gates.py` may execute
  without a `pr_number`, so they still fall back to parsing the PR body.

This seam is temporary and must not remain the long-term architecture.

Implementation anchors:

- `scripts/ci/check_pr_body_phase2_gates.py:162`
- `scripts/ci/check_pr_body_phase2_gates.py:182`
- `scripts/orchestration/review_mapping_artifact.py:44`
- `AGENTS.md:39`

## Decision

Keep PR-body mirroring only as:

1. A human-readable mirror of the canonical artifact.
2. A fallback path for local validation when no `pr_number` is available.

All authoritative CI / governance decisions must continue to prefer the repo
artifact over the PR body whenever `pr_number` is known.

## Exit Criteria

Remove the PR-body fallback only when ALL are true:

1. CI/event flows always provide `pr_number` to Phase 2 and merge-readiness jobs.
2. Local tooling has a deterministic artifact-first invocation path (`--pr-number`
   or equivalent) that does not depend on PR-body parsing.
3. PR body remains a mirror/documentation surface only, with no enforcement logic
   depending on it.

## Follow-up Tracking

Canonical backlog item:

- `docs/roadmap/BACKLOG_LEDGER.md` -> `P1: Move Fixed in Commit Mapping source-of-truth from PR body to repo file`

## Consequences

Positive:
- Governance becomes deterministic on git-tracked artifacts.
- PR body remains readable for reviewers without being authoritative.

Trade-offs:
- Until the seam is removed, Phase 2 logic must preserve both artifact-first and
  body-fallback behavior.
