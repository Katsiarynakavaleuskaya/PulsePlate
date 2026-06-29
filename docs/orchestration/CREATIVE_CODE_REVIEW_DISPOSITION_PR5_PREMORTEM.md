# PR-5 Creative-Code Review Disposition Premortem

Status: pre-open premortem closure for PR-5. This is governance evidence only;
it is not fixed-mapping evidence, review-thread disposition proof, merge
readiness, or release evidence.

## Frame

It is after PR-5 opened for review and the lane failed. The failure did not come
from product runtime behavior, because PR-5 has no runtime surface. It came from
a local review-ingestion helper being misread or misused as higher authority, or
from sanitized review data being less sanitized than the contract claimed.

Success for PR-5 means the repo has a local, read-only lane that converts
sanitized PR review context into typed advisory packets and specification-only
repair launch packets while keeping PR-6 as the first applied candidate lane.

## Closure Matrix

| ID | Scenario | Premortem decision | Closure |
|---|---|---|---|
| PM-PR5-001 | Raw GitHub review text leaks into sanitized feedback records. | block until fixed | [x] FIXED |
| PM-PR5-002 | Advisory disposition output is treated as review-thread, fixed-mapping, or merge-readiness authority. | block until fixed | [x] FIXED |
| PM-PR5-003 | Stale head SHA review feedback launches a repair packet against the wrong commit. | block until fixed | [x] FIXED |
| PM-PR5-004 | Local artifact output escapes the gitignored review-disposition directory. | block until fixed | [x] FIXED |
| PM-PR5-005 | Repair launch packet identity is unstable when multiple repair candidates are present. | block until fixed | [x] FIXED |
| PM-PR5-006 | PR-5 silently widens into PR-6 by generating patches or opening candidate PRs. | block until fixed | [x] FIXED |
| PM-PR5-007 | Review ingestion fails on normal sanitized issue-comment URLs and drops bot comments. | proceed with changes | [x] FIXED |
| PM-PR5-008 | PR-5 starts from stale main after adjacent creative-code PRs merge. | proceed with changes | [x] CONTROLLED |

## Scenarios

### PM-PR5-001 Raw Review Text Leakage

Failure story: PR-5 accepts a copied GitHub API fixture where `body` contains the
raw review markdown. The CLI treats that field as a safe excerpt, writes it into
`CreativeCodeReviewFeedbackRecord`, and the local artifact now preserves review
body text that might contain secrets, local paths, or unreviewed bot payloads.
Later agents see the packet as sanitized and route it into repair planning.

Underlying assumption: a fixture field named `body` is safe if it came from a
test fixture. That assumption is false because GitHub review comments, reviews,
and issue comments use `body` for raw markdown.

Early warning signs: fixtures copied from GitHub API responses contain `body`,
`body_text`, `body_html`, or `raw_body`; sanitized excerpts are not explicitly
named.

Containment action: reject raw body fields fail-closed and require
`body_excerpt_sanitized` or `summary_sanitized`.

Closure:

- [x] FIXED. Raw GitHub body fields are rejected before record construction:
  `scripts/orchestration/creative_code_review_disposition.py:266` and
  `scripts/orchestration/creative_code_review_disposition.py:280`.
- [x] FIXED. The CLI requires explicit sanitized text:
  `scripts/orchestration/creative_code_review_disposition.py:313`.
- [x] TESTED. Raw body variants and missing sanitized text are covered:
  `tests/test_creative_code_review_disposition.py:404`,
  `tests/test_creative_code_review_disposition.py:437`, and
  `tests/test_creative_code_review_disposition.py:523`.

### PM-PR5-002 Advisory Output Becomes Authority

Failure story: reviewers or future automation see a disposition packet with
`creative_repair_candidate` and treat it as a decision to resolve a review
thread, update fixed mapping, or claim merge readiness. PR-5 then becomes a
hidden authority bridge from local classification to GitHub mutation.

Underlying assumption: a typed packet implies operational authority. That is
wrong for PR-5; all classification is advisory and every candidate still needs a
human decision.

Early warning signs: packets or docs mention resolving threads, editing mapping,
opening PRs, merging, or readiness as allowed behavior.

Containment action: keep review authority flags false, allow only
`create_pr1_specification=true` in repair launch packets, and test the exact
authority shape.

Closure:

- [x] FIXED. The contract forbids repository writes, review-thread resolution,
  fixed-mapping edits, readiness claims, provider calls, runtime changes, and
  GitHub App authority: `docs/orchestration/contracts/CREATIVE_CODE_REVIEW_DISPOSITION_CONTRACT.md:16`.
- [x] FIXED. Review packet authority is all false:
  `scripts/orchestration/creative_code_review_disposition_contract.py:469`.
- [x] FIXED. Repair launch authority only allows PR-1 specification creation:
  `scripts/orchestration/creative_code_review_disposition_contract.py:473`.
- [x] TESTED. The launch authority shape is asserted:
  `tests/test_creative_code_review_disposition.py:142`.

### PM-PR5-003 Head SHA Drift Launches Stale Repair Work

Failure story: PR feedback is collected against one head SHA, then another
commit lands. The disposition packet still creates repair candidates, and a
future PR-1 specification starts from stale feedback. The next lane repairs a
comment that no longer applies or misses a new blocker.

Underlying assumption: review feedback remains valid until a human notices a
new commit. That is not acceptable for an automated handoff packet.

Early warning signs: expected and actual head SHAs differ, but packet summary
still reports repair candidates.

Containment action: when expected and actual SHA differ, classify every record
as `head_sha_drift`, set repair to false, and block repair launch.

Closure:

- [x] FIXED. Drift rewrites classifications to `head_sha_drift` and disables
  repair: `scripts/orchestration/creative_code_review_disposition_contract.py:1003`.
- [x] FIXED. Repair launch raises on drift:
  `scripts/orchestration/creative_code_review_disposition_contract.py:1160`.
- [x] TESTED. Drift blocks launch:
  `tests/test_creative_code_review_disposition.py:209`.

### PM-PR5-004 Artifact Output Escapes Local Artifact Root

Failure story: a local summary output path points at a symlink inside the
gitignored review-disposition directory. The CLI writes through the symlink and
modifies a tracked file or a private local file outside the artifact root.

Underlying assumption: checking only the output parent directory is enough.
That misses final-path symlinks.

Early warning signs: markdown or text output uses direct `write_text` while JSON
output uses atomic temp-and-replace.

Containment action: route text output through the same artifact-root resolver,
reject final-path symlinks, and use atomic replace.

Closure:

- [x] FIXED. Text output rejects final symlinks and uses temp-and-replace:
  `scripts/orchestration/creative_code_review_disposition.py:129`.
- [x] TESTED. Existing symlink output is rejected and the outside target remains
  unchanged: `tests/test_creative_code_review_disposition.py:327`.

### PM-PR5-005 Multi-Candidate Launch Identity Drift

Failure story: the builder emits multiple repair candidates in one order, but
the validator sorts them before validating identity. The packet generated by
the builder then fails its own validator, producing a false red after local
review ingestion already succeeded.

Underlying assumption: list order is irrelevant to identity. That is false when
fingerprints are computed over the packet content.

Early warning signs: builder identity is computed before validator-side
normalization.

Containment action: sort repair candidates before computing launch identity.

Closure:

- [x] FIXED. Repair candidates are sorted before identity:
  `scripts/orchestration/creative_code_review_disposition_contract.py:1177`.
- [x] TESTED. Multi-candidate launch validates and preserves priority order:
  `tests/test_creative_code_review_disposition.py:157`.

### PM-PR5-006 PR-5 Widens Into PR-6

Failure story: because PR-5 sees review feedback and prepares repair launch
packets, a future agent treats it as permission to generate patches, write a
branch, or open a candidate PR. That collapses the planned separation between
PR-5 classification and PR-6 applied candidate work.

Underlying assumption: "prepare launch" means "launch now." For PR-5 it means
only "prepare a local packet for a later human/coordinator PR-1 decision."

Early warning signs: CLI source imports subprocess/GitHub mutation paths or
contains `gh pr create`, `resolveReviewThread`, or GraphQL mutation strings.

Containment action: keep the CLI local-only and add static forbidden-command
tests.

Closure:

- [x] FIXED. The CLI module states it never calls GitHub, edits mapping,
  resolves threads, creates branches, opens PRs, or claims readiness:
  `scripts/orchestration/creative_code_review_disposition.py:3`.
- [x] TESTED. Forbidden mutation command/API fragments are scanned:
  `tests/test_creative_code_review_disposition.py:545`.

### PM-PR5-007 Normal Issue-Comment URLs Are Dropped

Failure story: issue comments from review bots use normal GitHub issue-comment
anchors. If the URL validator rejects those, the collector silently becomes less
useful for bot-comment review and downstream summaries undercount advisory
feedback.

Underlying assumption: pull-request discussion anchors are enough. PR review
work also includes issue comments.

Early warning signs: fixture ingestion works for `#discussion_r...` but not
`#issuecomment-...`.

Containment action: cover sanitized issue-comment URLs in fixture ingestion.

Closure:

- [x] FIXED. Sanitized issue-comment fixtures are accepted:
  `tests/test_creative_code_review_disposition.py:458`.
- [x] TESTED. The stored source URL remains the GitHub issue-comment URL:
  `tests/test_creative_code_review_disposition.py:497`.

### PM-PR5-008 Stale Main After Adjacent Creative-Code Merge

Failure story: PR-5 starts after PR-4, but another adjacent creative-code PR
merges before PR-5 is pushed. The branch still opens from the older base,
reviewers see obsolete context, and GitHub CI evaluates a stack that no longer
matches current `origin/main`.

Underlying assumption: the base checked at lane start remains current until PR
open. That is false in this active PR train.

Early warning signs: `origin/main` contains commits after the lane base and
changed creative-code governance files overlap the same train.

Containment action: fetch current main before push, inspect intervening files,
rebase when there is no destructive overlap, then rerun local narrow gates.

Closure:

- [x] CONTROLLED. PR-5 was rebased onto current `origin/main` after PR `#2045`
  merged. This is workflow evidence, not a tracked code invariant.
- [x] CONTROLLED. Local gates are rerun after rebase before push/open.

## Decision

Decision: proceed with changes.

All premortem scenarios that would block PR open are closed in this PR as
FIXED or CONTROLLED. PR-5 still does not claim merge readiness; post-open
review, Codex Security, current-head CI, review-thread governance, and fixed
mapping remain separate gates.
