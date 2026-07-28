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
at the recorded attempt. The exact negative projection is
`retry_required=false`, `substitute_review_required=false`,
`prior_review_required=false`, `operator_override_required=false`, and
`ttl_required=false`.

This policy cannot replace GitHub review-thread truth, CodeRabbit/Sourcery/Cubic
dispositions, `docs/review/PR_<N>_FIXED_MAPPING.md`, PR body mirror governance,
current-head CI, or strict merge-readiness checks.

Current material-seal authoring does not accept provider evidence and does not
invoke, retry, poll, wait for, or substitute either Connector or Codex Security.
`seal --self-review-report <report.json>` authors the exact symmetric
provider-neutral no-claim pair. Provider absence is not review, scan, approval,
PASS, or no-findings evidence, and all current-head CI/security, disposition,
mapping, thread, ancestry, and wait-window gates remain mandatory.

Historical material seals may contain `--review-source-unavailable-ref`
receipts. Their verifier remains available only to read and revalidate legacy
artifacts: it authenticates the canonical same-repository, same-PR, unedited
issue-comment URL, bot/App identity, immutable timestamp, exact known quota
body, and UTF-8 body SHA-256. That compatibility path grants no current
authoring authority and must not cause a provider request, retry, wait, or
fallback.

Historical compatibility: the PR `#2142`
`operator_review_credit_exhaustion_override` receipt remains parseable and
is live-authenticated only for PR `#2142`. Its multi-reference authoring flags
are no longer active CLI options for later PRs and do not define current quota
handling.
