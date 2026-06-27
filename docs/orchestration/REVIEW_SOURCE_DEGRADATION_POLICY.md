# Review Source Degradation Policy

Review-source status records whether advisory review inputs were available,
degraded, or unavailable while collecting PR review context.

Canonical helper/CLI: `scripts/orchestration/review_source_status.py`.
Schema: `docs/orchestration/contracts/review_source_status.v1.json`.

`source_degraded` is warning-only. It is not a pass and is not a blocker by
itself. Blocking comes only from explicit fallback findings, failed required
checks, unresolved review threads, or actionable bot comments.

This policy cannot replace GitHub review-thread truth, CodeRabbit/Sourcery/Cubic
dispositions, `docs/review/PR_<N>_FIXED_MAPPING.md`, PR body mirror governance,
current-head CI, or strict merge-readiness checks.
