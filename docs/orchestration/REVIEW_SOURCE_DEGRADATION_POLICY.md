# Review Source Degradation Policy

Review-source status records whether advisory review inputs were available,
degraded, or unavailable while collecting PR review context.

Canonical helper/CLI: `scripts/orchestration/review_source_status.py`.
Schema: `docs/orchestration/contracts/review_source_status.v1.json`.

`source_degraded` is warning-only. It is not a pass and is not a blocker by
itself. Blocking comes only from explicit fallback findings, failed required
checks, unresolved review threads, or actionable bot comments.

Exact `rate_limited` and `usage_limit_reached` statuses are terminal
review-source unavailability: `source_degraded=true`,
`fallback_required=false`, and `blocking=false`. No retry, substitute review,
prior review, operator override, or TTL is required. The trusted evidence has
`review_claim=none`; it proves only that the configured source was unavailable
at the recorded attempt.

This policy cannot replace GitHub review-thread truth, CodeRabbit/Sourcery/Cubic
dispositions, `docs/review/PR_<N>_FIXED_MAPPING.md`, PR body mirror governance,
current-head CI, or strict merge-readiness checks.

For a material seal, `--review-source-unavailable-ref` accepts only a canonical
same-repository, same-PR, unedited issue-comment URL from the trusted Codex
GitHub App. The verifier authenticates the bot and App identity, exact
`html_url`/`issue_url`, immutable timestamp, and exact known quota body, then
recomputes the UTF-8 body SHA-256 on every validation. Unknown or changed text
fails closed. The receipt binds the immutable evidence to the current material
head/digest as `seal_context_only`; a later material change requires resealing,
but the same immutable comment may be reverified and reused.

Historical compatibility: the PR `#2142`
`operator_review_credit_exhaustion_override` receipt remains parseable and
is live-authenticated only for PR `#2142`. Its multi-reference authoring flags
are no longer active CLI options for later PRs and do not define current quota
handling.
