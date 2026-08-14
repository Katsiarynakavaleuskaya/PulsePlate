# PR Orchestration Contract Matrix

Canonical reference for PR governance. Single source of truth to reduce drift between scripts, AGENTS, PR body expectations, and CI checks.

## 1. Purpose

- Define canonical orchestration contract for PR governance
- Remove drift between scripts, AGENTS, PR body expectations, CI checks
- Document mergeability rules

## 2. Source-of-Truth Hierarchy

| Level | Artifact                                | Role                           |
| ----- | --------------------------------------- | ------------------------------ |
| 1     | Git commit SHA                          | canonical repo state           |
| 2     | Repository files                        | canonical governance artifacts |
| 2a    | `docs/review/PR_<N>_FIXED_MAPPING.md`    | Fixed in Commit Mapping SoT    |
| 3     | Latest CI run for current HEAD          | merge decision                 |
| 4     | PR body                                 | summary + artifact link        |

Evidence:
- Level 2: `AGENTS.md:39`, `AGENTS.md:102`, `AGENTS.md:103`, `AGENTS.md:434`, `AGENTS.md:435`
- Level 2a: `scripts/orchestration/review_mapping_artifact.py:24`, `scripts/orchestration/review_mapping_artifact.py:84`, `scripts/orchestration/review_mapping_artifact.py:110`
- Level 3: `scripts/ci/check_pr_merge_readiness.py:349`, `scripts/ci/check_pr_merge_readiness.py:369`, `scripts/ci/check_pr_merge_readiness.py:400`
- Level 4: `scripts/ci/check_pr_body_phase2_gates.py:162`, `scripts/ci/check_pr_body_phase2_gates.py:182`

## 3. Governance Phases

| Phase   | Gate                    | Artifact                                                         | Blocks Merge |
| ------- | ----------------------- | ---------------------------------------------------------------- | ------------ |
| Phase 1 | CI hygiene              | workflows/checks                                                 | yes          |
| Phase 2 | artifact-first contract | canonical artifact (authoritative) + PR body link                | yes          |
| Phase 2b | pre-closeout validation | uncommitted artifact + live bot inventory + true Markdown link | blocks closeout commit |
| Phase 3 | Merge readiness         | unresolved threads + actionable mapping                          | yes          |
| Phase 4 | Disposition proof       | script semantics                                                 | yes          |

Canonical operator entrypoint:

- `scripts/orchestration/check_merge_ready.py` runs Phase 2, merge-readiness, and disposition proof as one verdict.
- Before the sole mapping commit, its local-only `--pre-closeout --require-auth`
  mode reads the uncommitted canonical artifact, requires both `GH_TOKEN` and
  `GITHUB_TOKEN`, requires the mapping artifact to be the only dirty path,
  explicitly maps every live actionable bot issue comment, bot inline comment,
  and top-level bot review, and requires exactly one true
  same-repository `blob/<exact-live-head-ref>/docs/review/...` Markdown link to
  that artifact in the live PR body. The ref path must equal the authenticated
  PR `head.ref`; the standalone link's decoded URL may occur only once, and
  repo-relative or raw HTML/code examples do not count. It skips thread-resolution,
  current-head-CI, and wait-window gates and is never merge-readiness evidence.
- Underlying gate scripts remain authoritative for their own contract semantics.

## 4. Phase 2 Contract (Canonical Artifact)

Canonical source: `docs/review/PR_<N>_FIXED_MAPPING.md`.

The PR body keeps Goal, Scope, Tests/validation, Security notes,
Risks/Rollback, and one link to the canonical artifact. It does not mirror
review-thread URL→SHA entries. Required `## Experiment Runner Evidence` lives
in the canonical artifact:

- full URL→SHA mapping lines exist only in the canonical artifact
- required `## Experiment Runner Evidence` in the canonical artifact:
  non-trivial PRs must include an oracle-only artifact by default, and
  `Not applicable` requires an explicit coordinator/operator reason

Canonical runtime behavior is artifact-first when `pr_number` is available.
PR-body parsing is a temporary compatibility seam for legacy local/body-only
checks. It is not authority and must not cause agents to copy mapping blocks.

Before the single final-material closeout, an open PR may declare the exact
non-mergeable marker `<!-- phase2-pre-closeout: final-security-pending -->`
and the matching pending mapping-status line. This lets the Phase 2 body gate
validate the truthful pre-closeout state without fabricating an artifact. The
marker requires both Phase 2 boxes to remain unchecked and forbids mapping
entries; `check_merge_ready.py` still requires the canonical artifact and
therefore cannot treat this state as merge-ready. Once the canonical
mapping/seal is published, the marker must be removed; a stale marker is a
Phase 2 body-gate error even when the artifact exists.

The historical marker name is retained for wire compatibility only. It does
not request, invoke, retry, wait for, or claim a Connector/Codex Security
provider result; current closeout means exact-material self-review, applicable
current-head security/governance checks, dispositions, and the static
provider-neutral no-claim seal.

Temporary seam tracking:

- ADR: `docs/architecture/ADR_FIXED_MAPPING_PR_BODY_FALLBACK_SEAM_2026-03-07.md`
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md:186`

Exit criteria for removing PR-body fallback:

1. CI/event paths always provide `pr_number` for Phase 2 and merge-readiness flows.
2. Local tooling supports deterministic artifact lookup without PR-body parsing.
3. The fallback branch in `scripts/ci/check_pr_body_phase2_gates.py` can be removed without losing local validation ergonomics.

Phase 2 sections and required orchestration evidence:

- `## Discussion Thread Pass`
- Checkbox contract (completed / mapping completed)
- `## Fixed in Commit Mapping` in the canonical artifact
- Required `## Experiment Runner Evidence` with `Artifact: artifacts/orchestration/experiments/results/<id>.json` or `Not applicable: <reason>` in the canonical artifact. Non-trivial PRs must create oracle-only evidence by default; local artifact load/write failures are infrastructure blockers and are not valid `Not applicable` reasons. Malformed evidence is rejected.
- Required premortem evidence for non-trivial PRs: `pulseplate-premortem-risk-review`
  must run against the actual diff before PR open, and every finding must be
  `FIXED`, `NOT-A-BUG`, or `DEFERRED` with evidence/backlog proof.
  Premortem evidence is a creative future-state risk view and must be
  diff-specific: each finding names the concrete failure mode, affected surface,
  plausible user/business/project/security/governance impact, closure surface,
  and proof. For code, runtime, schema, security, workflow, orchestration, CI,
  or governance risks, `FIXED` proof must cite an enforceable mitigation in the
  PR, such as code, schema, validator, workflow guard, deterministic test,
  policy guard, or fail-closed behavior. A docs-only note is valid `FIXED`
  proof only when the underlying risk is documentation-only. Otherwise use
  `DEFERRED` with backlog proof or `NOT-A-BUG` with contract evidence.
- Required learning-loop evidence when triggered: `pulseplate-agent-learning-loop`
  is conditionally required when the operator asks for it or when the PR exposes
  a repeated role-agent, premortem, review, workflow, architecture, or
  successful-iteration pattern. Records must use
  `agent_learning_record.v1`, distinguish `pattern_kind`, include bounded
  `learning_metrics`, stay redacted and proposal-only, and require reviewed
  repo-diff promotion before becoming canonical instructions. If the pattern
  affects the current PR scope, close it with code/schema/test/guard/policy
  changes, not a learning note alone.
- Required bootstrap role-agent evidence: `task_bootstrap.py` packet creation
  does not execute roles. The packet/runbook-declared role order must be run in
  order before implementation or before the phase it governs; missing role
  execution blocks readiness unless `agent-coordinator` records an explicit
  disposition with evidence.
- Required custom-role dispatch evidence:
  run the packet-provided
  `role_agent_dispatch_contract.dispatch_manifest_command` with the actual
  packet path, preserving any `--mode runtime --implementation-owner <role>`
  flags the coordinator packet emits. Historical `qoder_dispatch_bridge.py`
  invocations are compatibility-only. Role bindings in the packet's legacy
  `advisory` collection with `required_role_pass: true` are mandatory
  custom-role passes; that collection name is metadata only, not permission to
  skip.

Valid mapping forms in the canonical artifact:

- `- <url> -> <sha>`
- `- <url>`
- `- No actionable review comments`

Legacy body mirrors and 7–40-character SHAs remain readable for pre-activation
PRs. V1 artifacts require full 40-character FIXED SHAs and the embedded closed
JSON block `PULSEPLATE_PR_REVIEW_SEAL_V1`. The activation boundary is the
governance PR number + 1; the governance PR may opt in with
`Review-Seal-Version: v1`.

Root `AGENTS.md` owns the global final-material provider/no-claim
invariant. The current v1 field projection is one exact static pair:
- review: `review_claim=none`, `output_required=false`, `blocking=false`,
  exact material head and digest;
- security: `scan_claim=none`, `no_findings_claim=false`,
  `output_required=false`, `blocking=false`, exact base/head/digest.

When both provider inputs are absent, `seal` authors that pair without
invoking, starting, restarting, retrying, polling, waiting for, substituting, or
requiring an operator override for either provider. One-sided, mixed, partial,
arbitrary, and escalating forms fail closed. Absence is not review, scan,
approval, PASS, or no findings.
Provider absence requires no retry.

Provider no-claim changes only provider-output availability. Current-head
required CI and the trusted security-check bundle, actual provider findings,
review dispositions, canonical mapping, unresolved threads, bot actionables,
commit ancestry, the mapping-only descendant rule, and the mandatory wait
window remain hard.

Legacy provider-backed v1 receipts remain parseable/revalidatable only for
historical artifacts and grant no current authoring authority. Historical
metadata such as `scope=per_pr`, `automatic_budget=1`,
`automatic_retries=0`, `requires_frozen_material=true`,
`additional_invocation=trusted_operator_approval`, and
`repository_invokes_plugin=false` is compatibility data only. The historical
terminal projection remains `source_degraded=true`,
`fallback_required=false`, `blocking=false`, `review_claim=none`,
`retry_required=false`, `substitute_review_required=false`,
`prior_review_required=false`, `operator_override_required=false`, and
`ttl_required=false`; it is a no-retry record, not provider success.

Legacy compatibility only: GitHub Codex Connector review and Codex Security
were separate providers. Their embedded receipts remain readable only as
historical data; provider preparation/outcome authoring commands are not
registered and no legacy receipt authorizes a current provider request or
retry.

### Material review seal v1

- The gate snapshots live base/head, fully paginates the PR commit connection,
  reads the artifact from that exact checked-out head, and rechecks refs before
  PASS. A change returns `SNAPSHOT_CHANGED`.
- The material base is the unique real merge-base. The digest is canonical JSON
  over merge-base, file status/path, old/new modes, full blob OIDs, and the
  classification-policy version.
- Every path is material except the exact current-PR mapping artifact. PR-body
  edits are outside Git. Other docs, AGENTS/runbook, workflows, tests,
  dependencies, schemas, and policies remain material.
- Current authoring uses no provider flags and emits the exact symmetric
  provider-neutral no-claim pair plus one repo-native `self_review` advisory
  artifact reserved for that pair. Both provider receipts bind the frozen
  material digest; review additionally binds the material head, security binds
  the exact merge-base/head range, and `self_review` binds the exact
  base/merge-base/material-head/digest and canonical report hash without
  claiming provider review or scan. Exact-key validation rejects unknown
  authority, escalation, stale identity, partial receipts, mixed
  legacy/no-claim forms, and `self_review` on any other seal shape.
- Authenticated validation rebuilds the pair from the live material identity and
  compares it byte-for-byte. It does not call either provider. The merge gate
  waits at most 300 seconds for missing or pending trusted exact-head security
  checks to settle. Failed, stale, skipped-when-applicable, or untrusted checks
  are terminal immediately; the wait never invokes or retries a provider.
- The no-claim pair itself grants no authority, bypass, or self-authorization
  for protected authority, verifier, workflow, dependency, or security-policy
  changes.
- Actual provider output, when independently present, remains normal review
  evidence: every actionable finding still needs FIXED / NOT-A-BUG / DEFERRED
  disposition and mapping. Provider absence grants no thread-resolution,
  approval, PASS, scan, or no-findings authority.
- Historical completed-review, source-unavailability, positive-response,
  content receipt, operator-outage, and PR #2142 review-credit receipt variants
  remain parseable for legacy artifacts only. Their existing identity, scope,
  and material checks remain read-compatible; no legacy variant becomes a
  current fallback, activation mechanism, or self-authorization path.
- `pr_review_closeout.py` keeps `init`, `freeze`, and `add-disposition` state
  gitignored. `seal` is the only tracked authoring step; mapping and seal publish
  in one batched governance-closeout commit. Resealing after a base sync is
  accepted only when Git proves both the base and the previously sealed material
  head advanced by ancestry and the replacement preserves every disposition
  proof block.
- Before publishing the one closeout commit, the pre-closeout gate must require
  the mapping artifact to be the only dirty path and validate the local sealed
  artifact against the complete live actionable bot inventory.
  In this pre-commit mode an actionable top-level review requires its own
  mapping even when all actionable child comments are mapped. The PR body must
  contain exactly one rendered same-repository blob Markdown link whose ref is
  the authenticated PR `head.ref` and whose destination is
  `docs/review/PR_<N>_FIXED_MAPPING.md`; its decoded canonical URL may occur
  only once, and plain text, repo-relative links, inline/fenced/raw-HTML
  examples do not count.
  Before PASS, the gate re-reads the live body, content-bound actionable
  inventory, and local dirty-path set and fails closed on new, removed, or
  edited concurrent bot activity or local worktree drift.

Evidence:
- `scripts/orchestration/check_merge_ready.py:383`
- `scripts/orchestration/check_merge_ready.py:409`
- `scripts/ci/check_pr_merge_readiness.py:1157`
- `scripts/ci/check_pr_merge_readiness.py:1239`
- `scripts/ci/check_pr_merge_readiness.py:1291`
- `scripts/ci/check_pr_merge_readiness.py:1342`
- `scripts/orchestration/review_mapping_artifact.py:44`
- `scripts/orchestration/review_mapping_artifact.py:84`
- `scripts/orchestration/review_mapping_artifact.py:110`
- `scripts/ci/check_pr_body_phase2_gates.py:162`
- `scripts/ci/check_pr_body_phase2_gates.py:169`
- `scripts/ci/check_pr_body_phase2_gates.py:182`
- `docs/architecture/ADR_FIXED_MAPPING_PR_BODY_FALLBACK_SEAM_2026-03-07.md:1`
- `docs/roadmap/BACKLOG_LEDGER.md:186`

Artifact-only governance findings are fixed in the canonical artifact itself, but the proof block must still cite the validator/runtime enforcement that makes the artifact contract merge-blocking.

## 5. Merge Readiness Contract

- Unresolved review threads must be zero
- Actionable bot comments must be mapped
- Activated PRs must have a current material review seal and real mapped FIX
  commits in the complete live PR graph
- Cancelled/stale runs do not define mergeability
- PR lifecycle packets may distinguish `post_open_review` from `merge_ready`,
  but both phases still use current-head truth and the canonical artifact
  `docs/review/PR_<N>_FIXED_MAPPING.md`
- `post_open_review` is the packet-level phase where the canonical role-only
  `qa-engineer-agent -> bug-hunter -> security-auditor` lane is synthesized.
  Final-material gates remain outside role dispatch: exact-head
  `pulseplate-pr-review` self-review and finding disposition precede a
  provider-neutral `seal` invocation without provider flags. The no-claim pair
  changes no current-head merge-wrapper requirement and does not widen either
  lane.

Evidence:
- `scripts/ci/check_pr_merge_readiness.py:1`
- `scripts/ci/check_pr_merge_readiness.py:135`
- `scripts/ci/check_pr_merge_readiness.py:219`
- `scripts/ci/check_pr_merge_readiness.py:349`
- `scripts/ci/check_pr_merge_readiness.py:369`
- `scripts/ci/check_pr_merge_readiness.py:383`

## 6. FIXED / NOT-A-BUG / DEFERRED Semantics

### FIXED

- Requires commit proof
- V1 SHA must be full length, GitHub-addressable, in the live PR commit set, and
  reachable from live head
- Commit must not be trigger-only
- Commit-after-comment applies
- An off-live-PR original comment commit/ref is reviewer-execution context only
  when the root comment author is exactly
  `chatgpt-codex-connector` (the authenticated GraphQL login). It never supplies
  FIX proof: the mapped FIX
  must still be a real live-PR commit reachable from the live head.
  `API_UNKNOWN` remains terminal, and off-graph refs from any other bot or
  human remain untrusted.

### NOT-A-BUG

- Requires written reasoning/evidence
- Thread URL must still be listed in Fixed in Commit Mapping
- No commit proof required

### DEFERRED

- Requires ledger reference
- Thread URL must still be listed in Fixed in Commit Mapping
- No commit proof required

### Reply-only disposition exceptions

The closed reply-only validator has five mutually exclusive paths. Existing
canonical fingerprint records retain their current later-duplicate semantics.
The recordless path covers only the first currently visible trusted Codex/App
`unavailable_review_ref_ancestry` seed on the exact live direct single
mapping-only successor. Its resolved thread root must have `originalCommit`
equal to that live head and the same frozen material digest. One later
`OWNER|MEMBER|COLLABORATOR` reply must use the exact closed structured fields;
its fingerprint must bind the unique real reachable FIX already present in the
canonical FIXED mappings and cited by the finding. That FIX must be mapped from
a live resolved thread root, have a snapshot `pushed_at` strictly after the root
comment, and be a non-empty, non-trigger-only repository commit. Issue or
top-level-only mappings remain valid ordinary dispositions but cannot qualify
this recordless exception. The recordless path groups by fingerprint only after
full eligibility and covers a fingerprint only when exactly one eligible seed
is currently visible; ineligible comments do not affect cardinality, while two
eligible seeds leave both blocking. This is a current-snapshot cardinality rule,
not a historical once-ever claim.

The third path is a separate repository-owner authority class and activates
only when that same thread root has no canonical fingerprint record or FIXED
mapping; unrelated canonical records may coexist. Its resolved thread root must
be the first comment, have authenticated author login
exactly `chatgpt-codex-connector`, target
`docs/review/PR_<N>_FIXED_MAPPING.md`, and have `originalCommit` equal to the
live head. That head must be the sole direct mapping-only successor whose direct
parent is the sealed material head; recomputing both material projections must
equal the sealed digest. The root body is not sent through the generic SHA
lexer and its natural-language clause structure is not interpreted. It must name
an ancestry/commit-graph cause and contain exact, hex-boundary-delimited
occurrences of the sealed material SHA and the lowercase reply-selected ref.
Before posting, the human OWNER must inspect the whole root and confirm that no
independent actionable finding exists beyond the unavailable-ref ancestry claim;
otherwise this class is forbidden and ordinary disposition remains required.
After that explicit human decision, exactly
one later comment with GraphQL `authorAssociation=OWNER` must equal this one
line byte-for-byte:

`OWNER NOT-A-BUG: ignore unavailable reviewer ref <full-40-sha>; authenticated live PR graph is authoritative.`

The placeholder is replaced by exactly one full lowercase 40-character SHA;
leading/trailing whitespace, newline, Markdown, capitalization changes, or any
extra text are invalid. The selected ref is classified independently of the
generic finding parser. Only a definitive `REVIEW_REF_UNAVAILABLE` result is
eligible. `API_UNKNOWN` is terminal, a repository-addressable or live-PR commit
is ineligible, and the unavailable ref is never passed to ancestry. Coverage is
granted only when exactly one root is globally eligible; two leave all roots
blocking. That census examines every live thread root before caller-side URL
filtering, so a URL-only NOT-A-BUG or DEFERRED disposition cannot hide a second
eligible root. The authenticated repository argument must parse to the same
case-insensitive owner/name identity as the live PR snapshot; mixed-repository
evidence fails closed. The exact reply is the human selection and disposition of
that root; automation does not infer it from bot wording. The validator is
read-only and never posts the reply. This record is
only a bounded NOT-A-BUG disposition; it is not review, provider output,
approval, merge authority, or a bypass of actual findings, current-head CI,
trusted security checks, unresolved threads, ancestry, mapping-only closeout,
or the wait window. A canonical fingerprint record or FIXED mapping for the
same root keeps this owner-only branch inactive and preserves the existing paths
unchanged.

The fourth path is the recommended owner-only class for unavailable or
synthetic provider-only evidence on the canonical mapping. It has one exact
reply and no provider identifier:

`OWNER NOT-A-BUG: provider-only evidence in this root is unavailable; authenticated live PR state is authoritative.`

The thread must contain exactly one later GraphQL-authenticated `OWNER`
comment; that sole OWNER comment must be byte-equal to that line. Other
non-OWNER discussion does not silently acquire disposition authority. The human
OWNER must first read the complete root and confirm that it contains no
independent actionable finding beyond provider-only evidence that is unavailable
or synthetic. *Unavailable* means that evidence is
not repository-addressable evidence usable by the authenticated live PR
validator; it never labels a material, security, code, workflow, dependency, or
runtime defect as unavailable. Automation neither parses the root prose nor
extracts, lexes, or classifies a SHA, ref, URL, token, or fingerprint for this
class.

Eligibility is structural and fail-closed: the resolved root is the first
comment, is authored by `chatgpt-codex-connector`, targets the canonical
current-PR mapping path, and has `originalCommit` equal to the exact live head.
REST and GraphQL cross-bind the same authenticated repository, PR, numeric
comment ID, URL, canonical path, byte-identical body, timestamp with
`updated_at == created_at`, trusted connector REST user id/login/type, and
`originalCommit`. The live head is the sole direct non-empty non-trigger
mapping-only successor of the sealed material head; both projections preserve
the caller-bound digest; and the embedded provider-neutral current seal passes
the ordinary strict base, merge-base, material-head, digest, and self-review
checks. A same-root canonical fingerprint or ordinary mapping disposition makes
the root ineligible. Comments on any material path are ineligible. Unlike the
legacy full-ref class, each eligible root is evaluated independently, so two or
more roots may each be covered by their own exact OWNER reply. Any repository,
API, Git, identity, path, seal, digest, timestamp, or topology uncertainty leaves
that root blocking.

This reply is a human NOT-A-BUG disposition for provider-only evidence. It is
not review, approval, provider output, a scan, PASS, a no-findings claim, merge
authority, or a bypass of current seal, CI, security, diff coverage, mapping,
unresolved threads, bot actionables, ancestry, or the review wait window. The
legacy full-40 ref reply remains readable and valid only for compatibility with
already-open historical threads, uses the same strict REST connector and
unedited-root binding, and is not the recommended authoring format.

The fifth path is an owner-only historical stale-seal `FIXED` class. It is
available only when the candidate thread is resolved; its root is the first
comment, has authenticated login exactly `chatgpt-codex-connector`, targets the
canonical current-PR mapping artifact, has `originalCommit=S`, and has neither a
same-root canonical fingerprint nor a FIXED mapping. Unrelated records may
coexist. The thread must contain exactly one later comment whose GraphQL
`authorAssociation` is `OWNER`; that sole OWNER comment must fullmatch this
single line byte-for-byte:

`OWNER FIXED: stale seal at <full-stale-head-sha> is corrected by mapping-only reseal <full-reseal-sha>; authenticated live PR graph is authoritative.`

Both placeholders are distinct lowercase 40-character SHAs selected only by
the OWNER reply. GraphQL and REST evidence must cross-bind the same repository,
PR, comment URL and numeric ID, canonical path, byte-identical unedited root
body and timestamps, trusted connector identity, and `originalCommit=S`.
Authenticated GitHub and local Git evidence must prove that `S` and `R` are
real current-PR commits reachable from the live head, `S` matches exactly one
member of the closed disjoint union `LINEAR_MATERIAL ∪ BASE_SYNC`, and `R` is
the sole direct one-parent child of
`S` in the complete live PR commit graph, pushed after the root and no later
than the OWNER reply, non-empty, non-trigger-only, and changing exactly the
regular canonical mapping blob. In `LINEAR_MATERIAL`, `S` has exactly one
parent `P`; its mapping equals `P` byte-for-byte; `P→S` is a non-empty real
material diff that neither changes nor exclusively changes the canonical
mapping; the valid seal at `P` binds its exact historical base and merge-base;
that base is unchanged for `S` and `R` and is an ancestor of the authenticated
current base; `P` is a reachable live PR commit; and the inherited seal is
demonstrably stale at `S`. This form is retrospective only and does not permit
manufacturing material after closeout. In `BASE_SYNC`, the second parent `B`
must be repository-addressable, an ancestor of the authenticated current base,
an advancement of the prior sealed base, and not already an ancestor of the
first parent `P`. A two-parent candidate is classified only as `BASE_SYNC` and
never falls through to linear after a failed invariant; zero, three, or more
parents are rejected. In both forms, the mapping inherited at `S` must equal
the `P` mapping and contain a seal that recomputes for its prior
material/base identity. That historical seal may use any valid parseable v1
provider shape; its repository-addressable material head must reach `P` through
the unique ordinary direct mapping-only closeout invariant, yet the inherited
seal must not be valid for `S`. The seal at `R` must use the exact
provider-neutral no-claim plus self-review shape, bind material head `S`, use
the form-selected unchanged or synchronized base and exact merge-base,
and match the exact recomputed material digest; the `S` and `R` material
projections must be identical after excluding the mapping. If later
base syncs exist, `R` may be an ancestor of the live head, but the current live
seal must separately use that exact provider-neutral plus self-review shape and
pass the ordinary exact current-base, material-head, digest, and sole
mapping-only successor checks.

Eligibility is counted across all live roots before caller filtering and is
granted only for one globally eligible stale-seal root; two cover neither. The
human OWNER must inspect the entire root and confirm that no independent
actionable finding exists beyond the historical stale-seal defect that `R`
corrected. The validator deliberately does not interpret bot
prose, never authors the reply, and fails closed on any repository, REST,
GraphQL, repository-bound pagination, commit-object identity,
shallow-boundary, replacement-object, commit-graph, regular-path, seal, digest, timestamp, or
cardinality uncertainty.
This class is not review, provider output, approval, scan, PASS, merge
authority, or a bypass of actual findings, current-head CI, trusted security,
mapping, unresolved threads, ancestry, closeout, or wait-window requirements.
Every pagination link must remain on `api.github.com` at the same repository
endpoint and path with immutable non-pagination query fields; a repeated,
cross-repository, or cross-endpoint page is terminal uncertainty. Local Git
evidence is evaluated with replacement objects disabled; a shallow boundary that
hides a selected parent or lies in selected ancestry is terminal, while an
unrelated legacy shallow boundary supplies no evidence. This path
records `FIXED`, not `NOT-A-BUG`: the defect was real at
`S` and `R` corrected it. It grants no review, provider output, approval, scan,
PASS, merge authority, or bypass of current CI, security, other findings,
unresolved threads, bot actionables, ancestry, or the wait window.

A root actually covered by a canonical reply-only validator is the narrow
exception to ordinary artifact mapping: its exact reply plus resolved thread is
the disposition evidence, and no second mapping entry or docs commit is created.
Every non-covered resolved actionable retains the ordinary mapping requirement.

For the canonical-fingerprint and mapped-FIX recordless paths, the cited review
ref must resolve as unavailable (not
API-unknown). Finding-local commit
candidates are capped at four unique values and admit only a full lowercase
40-character SHA or a lowercase 7–39-character hexadecimal ref carried by
exactly `...` or `…`. One finding-local maximal-token lexer examines each
standalone maximal ASCII-hex run. A run enters the SHA-like inventory when it
has at least seven characters or when a non-empty shorter run is immediately
followed by `...` or `…`. The whole atom must match one of the two accepted
forms; an adjacent
Unicode letter, number, mark, underscore, non-whitespace `C*` control, dot, or
ellipsis tail is part of the same atom, so malformed prefixes cannot be
admitted while their suffix is ignored. The same `L|N|M|_|C*-nonspace`
boundary-blocking class prevents substring extraction inside ordinary or
invisibly joined words. Whitespace controls remain separators. Only other
punctuation and Markdown delimiters bound atoms; underscore remains an
identifier character rather than a CommonMark emphasis instruction. Any
malformed SHA-like atom makes the whole finding ambiguous before API,
classification, or ancestry work. This conservative rule intentionally treats
all-hex prose followed by an ellipsis as ambiguous in this privileged
mapping-less path; ordinary disposition and mapping remain available. A
shortened ref must resolve
through the authenticated GitHub Commit API to one matching full SHA, and that
same successful response is passed to the existing commit classifier without
a second network lookup. Only authenticated Commit API `404` proves
finding-local repository unavailability, and only when the prefix matches none of the
snapshot-proven base, head, or PR commits. A successful binding must agree with
every snapshot-known prefix match; contradictions remain `API_UNKNOWN`. Every
shortened-ref `422` remains `API_UNKNOWN`
because prefix uniqueness is unproven. Ambiguity, malformed or non-prefix
responses, authorization, rate-limit, server, HTTP protocol, and transport
failures remain `API_UNKNOWN`. The canonical-record repository identity set
remains exactly `{verified FIX}` or `{verified FIX, base, live head}`. The
recordless identity set is exactly `{verified FIX}` or
`{verified FIX, sealed material head}`. Each path requires exactly one
unavailable ref; unavailable refs never enter ancestry. Any `API_UNKNOWN` is
terminal. The exception creates no docs commit and does not restart
review/security scans.

Evidence:
- `scripts/orchestration/pr_review_evidence.py:577` — exact `OWNER FIXED` parser
- `scripts/orchestration/pr_review_evidence.py:783` — shared reply-only producer
- `scripts/orchestration/pr_review_evidence.py:1966` — raw-Git linear-material edge invariant
- `scripts/orchestration/pr_review_evidence.py:2632` — closed historical topology classifier
- `tests/test_pr_review_material_seal.py:6662` — real-Git base-sync acceptance with later sync/current reseal
- `tests/test_pr_review_material_seal.py:6673` — real-Git linear-material acceptance
- `tests/test_pr_review_material_seal.py:6701` — exact parser rejection matrix
- `tests/test_pr_review_material_seal.py:6959` — linear topology negative matrix
- `tests/test_pr_review_material_seal.py:6974` — linear historical base-binding negatives
- `tests/test_pr_review_material_seal.py:6989` — invalid base-sync no-fallthrough proof
- `tests/test_pr_review_material_seal.py:7262` — batched complete parent enumeration
- `tests/test_pr_merge_readiness_gate.py:48` — strict merge-readiness consumer uses the shared producer
- `tests/test_pr_merge_readiness_gate.py:81` — strict merge-readiness input wiring
- `tests/test_review_threads_disposition_strict.py:44` — disposition consumer uses the shared producer
- `tests/test_review_threads_disposition_strict.py:1528` — disposition input wiring and snapshot stability
- `scripts/orchestration/check_review_threads_disposition.py:38`
- `scripts/orchestration/check_review_threads_disposition.py:298`
- `scripts/orchestration/check_review_threads_disposition.py:467`
- `AGENTS.md:47`
- `AGENTS.md:64`
- `AGENTS.md:81`

## 7. Trigger-only Commit Ban

- Empty commit = invalid FIXED proof
- Rerun/trigger subject = invalid FIXED proof

Evidence:
- `scripts/orchestration/check_review_threads_disposition.py:181`
- `scripts/orchestration/check_review_threads_disposition.py:197`
- `scripts/orchestration/check_review_threads_disposition.py:528`
- `AGENTS.md:103`

## 8. Required-check Truth

- Mergeability is decided by the **latest required checks for current HEAD only**
- Ignore cancelled runs
- Ignore stale runs
- External review tools do not block unless explicitly required
- `gh pr checks <PR_NUMBER>` is diagnostic only; a non-zero exit can mean live
  `pending`/`in_progress` required jobs, not failed current-head checks
- When only one current-head job remains live, inspect the exact run/job with
  `gh run view <RUN_ID>` or `gh run view --job=<JOB_ID>` before calling the PR
  red or green

## 9. CI Check Classification

| Class     | Meaning                   | Blocks Merge                |
| --------- | ------------------------- | --------------------------- |
| Hard gate | canonical merge blocker   | yes                         |
| Soft gate | advisory quality signal   | no                          |
| External  | third-party review signal | only if explicitly required |

Canonical lane matrix:

| Lane        | Command / Surface | Class | Blocking Rule |
| ----------- | ----------------- | ----- | ------------- |
| Local       | `pre-commit run --all-files` | Hard gate | Must pass before push; hook modifications must be committed |
| Local       | Narrow validation bundle | Hard gate | Agents must run `check_preflight`, `check_agent_consistency`, focused tests for the touched surface, and `make validate-changed`; full local `make verify` is not a default agent command |
| Local / PR process | `task_bootstrap.py` + `role_dispatch_bridge.py` role-agent dispatch | Hard gate | Packet creation is not execution; every bootstrap/runbook assigned role and every required readonly/custom-role pass must run in declared order or carry an explicit coordinator disposition with evidence |
| Local / PR process | `pulseplate-premortem-risk-review` | Hard gate | Every non-trivial PR must run premortem on the actual diff before PR open; findings are creative future-state risk forecasts for user/business/project/security/governance impact, but require FIXED / NOT-A-BUG / DEFERRED evidence; FIXED for code/runtime/schema/security/workflow/orchestration/CI/governance risks requires enforceable closure in the PR, not docs-only risk recording |
| Local / PR process | `pulseplate-agent-learning-loop` | Conditional hard gate | Required when operator-triggered or when repeated failure/successful-iteration patterns appear; use redacted `agent_learning_record.v1` with `pattern_kind`, bounded `learning_metrics`, proposal-only authority, and reviewed repo-diff promotion before canonical instruction changes |
| Local / PR process | Experiment Runner oracle evidence | Hard gate | Every non-trivial PR must create oracle-only evidence by default; artifact load/write failures are infrastructure blockers, and material contribution requires governed attribution |
| Post-open role review | `qa-engineer-agent -> bug-hunter -> security-auditor` | Hard gate | Run once after PR open; every actionable must be fixed or dispositioned before final material freeze |
| Final-material review | repo-native exact-head `pulseplate-pr-review` self-review, disposition actual findings, then run provider-neutral `seal` without provider flags | Hard gate | The embedded self-review report is a content-integrity-checked procedural advisory artifact, not cryptographic proof of agent execution or review/scan/approval authority. The exact static pair claims neither review nor scan and requires no provider invocation/retry/wait/substitute/override; current-head CI/security, actual findings, mapping, threads, bot actionables, ancestry, mapping-only closeout, and wait window remain blocking |
| GitHub PR CI | Full/heavy verification signal | Hard gate | Current-head CI must be green for `lint`, required/current-head checks for the touched PR surface, relevant `test-main` matrix, `diff-coverage` ≥97%, applicable security/governance checks, and merge-readiness; this replaces default local full `make verify` on agent machines |
| GitHub PR CI | Operator-approved machine-heavy deferral | Hard gate | PR body and fixed mapping document the deferral, the narrow local bundle passes, canonical current-head CI parity is green, relevant `test-main` matrix passes when selected, `diff-coverage` ≥97% is preserved when selected, and security/governance checks remain strict |
| Local / CI  | `python scripts/orchestration/check_merge_ready.py ...` | Hard gate | Wrapper must pass Phase 2 + review governance + current-head required checks + disposition proof |
| PR CI       | GitHub branch-protection required checks on current HEAD | Hard gate | Pending/failed current-head required jobs block merge |
| PR CI       | Non-required jobs / informational workflows | Soft gate | Visible signal only; fix or ledger if risk is real |
| Release ops | App Store / Fastlane validation lanes | Hard gate for release, not PR merge by default | Must pass before upload/publish claims; may be out-of-scope for code-only PR merge |
| External    | CodeRabbit / Sourcery / Cubic / similar bots | External | Advisory unless GitHub explicitly marks them required |

Current repo workflow inventory (Tier 1 post-PR2 state):

| Workflow / Surface | Lane | Class | Default Merge Effect | Tier 1 status |
| ------------------ | ---- | ----- | -------------------- | ------------- |
| `.github/workflows/ci.yml` (`CI`) | Backend / shared PR lane | Hard gate | Sole canonical backend/shared PR workflow for merge claims; current-head required jobs from this lane block merge when branch protection requires them | Canonical backend/shared PR lane |
| `.github/workflows/ci.yml` (`lint`, `security`, `diff-coverage`) | Backend / shared PR lane | Hard gate | Canonical lint, PR-time security, and diff coverage live inside `CI`; failures block merge when attached to current HEAD | Canonical enforcement surface |
| `.github/workflows/ci.yml` (`OpenAPI sync`, docs gates, merge-readiness, review governance) | Backend / shared PR lane | Hard gate | Blocks merge when the corresponding job is required on current HEAD | Canonical governance surface |
| `.github/workflows/pr-tests.yml` (`PR Tests (Fast)`) | Archived / non-canonical | No current PR lane | Retired as an active PR lane after PR2; keep only as historical reference if the file still exists in branch history | Removed as active PR lane |
| `.github/workflows/pr-coverage.yml` (`PR Coverage Guard`) | Archived / non-canonical | No current PR lane | Retired as an active PR lane after PR2; keep only as historical reference if the file still exists in branch history | Removed as active PR lane |
| `.github/workflows/security.yml` (`Security Scan`) | Scheduled / manual security audit lane | Soft gate | Advisory deep-audit lane outside ordinary PR merge truth; findings still require fix-first engineering response when the surface is in scope | Demoted out of PR-time blocking path |
| `.github/workflows/trivy.yml` (`trivy`) | Main / scheduled / manual image-security lane | Soft gate | Internal image-security reporting lane that stays outside ordinary PR merge truth unless branch protection explicitly promotes it elsewhere | Demoted out of PR-time blocking path |
| `.github/workflows/frontend-ci.yml` (`Frontend CI`) | Frontend specialized lane | Hard gate when attached | Blocks merge only for frontend/design-token/OpenAPI-sync surfaces when attached by path or required checks | Specialized add-on lane |
| `.github/workflows/accessibility.yml` (`Accessibility Tests`) | Frontend specialized lane | Soft gate by default | Advisory frontend quality signal unless branch protection requires it | Specialized add-on lane |
| `.github/workflows/ci.yml` (`iOS unit tests`, `iOS UI smoke`) | iOS specialized lane | Hard gate when attached | Blocks merge for iOS / workflow-change surfaces when attached; note current path router also attaches on `.github/workflows/**` and `.github/actions/**` changes | Specialized add-on lane with current workflow-change coupling |
| `.github/workflows/greenlight-ios.yml` (`Greenlight iOS Preflight`) | iOS specialized lane | Soft gate | Report-only preflight (`GREENLIGHT_BLOCKING=false`) | Advisory iOS lane |
| `.github/workflows/build.yml` (`Docker Build and Push`) | Release / image lifecycle lane | Hard gate for release / image claims, not ordinary PR merge by default | Required before publish/image assertions; ordinary code-only PRs treat it as release-ops | Specialized release lane retained in PR2+ |

Bot governance distinction (Tier 1 baseline):

- Third-party bot **status checks** remain `External` and advisory unless GitHub marks them required.
- Third-party or first-party bot **review comments** remain merge-blocking when they contain actionable items, because review governance/disposition policy is separate from status-check classification.
- Contributors must use `CI` as the canonical backend/shared PR lane for operator decisions; `pr-tests.yml` and `pr-coverage.yml` are no longer active PR lanes, `security.yml` is a scheduled/manual audit lane, and `trivy.yml` is a `main`/schedule/manual non-PR image-security lane.
- Canonical backend/shared PR merge truth does not imply that all other PR-triggered workflows disappear. Specialized repo-level workflows such as `Frontend CI`, `CodeQL Advanced`, and Docker/image lanes may still appear on workflow/governance PRs, but they remain non-canonical unless GitHub branch protection explicitly requires them.
Evidence:
- `scripts/ci/check_pr_merge_readiness.py:349`
- `scripts/ci/check_pr_merge_readiness.py:400`
- `scripts/ci/check_current_head_pr_checks.py:406`
- `scripts/orchestration/check_merge_ready.py:1`
- `scripts/ci/check_pr_body_phase2_gates.py:162`
- `scripts/ci/check_pr_body_phase2_gates.py:182`
- `.github/workflows/ci.yml:1`
- `.github/workflows/ci.yml:31`
- `.github/workflows/ci.yml:292`
- `.github/workflows/ci.yml:311`
- `.github/workflows/ci.yml:333`
- `.github/workflows/ci.yml:841`
- `.github/workflows/security.yml:2`
- `.github/workflows/security.yml:47`
- `.github/workflows/trivy.yml:12`
- `.github/workflows/trivy.yml:177`
- `.github/workflows/frontend-ci.yml:1`
- `.github/workflows/accessibility.yml:1`
- `.github/workflows/build.yml:1`
- `.github/workflows/build.yml:221`
- `.github/workflows/greenlight-ios.yml:2`
- `.github/workflows/greenlight-ios.yml:24`

## 10. Review Thread Lifecycle

```text
OPEN
→ FIXED / NOT-A-BUG / DEFERRED
→ RESOLVED
→ MERGE READINESS PASS
```

## 11. Security Invariants for Orchestration Scripts

- `GH_TOKEN` preflight
- Absolute binaries via `shutil.which()`
- Repo-approved Python interpreters for direct Python subprocesses
- Subprocess guard
- No blind `# nosec`
- Allowlist discipline

Evidence:
- `scripts/orchestration/check_review_threads_disposition.py:8`
- `scripts/orchestration/check_review_threads_disposition.py:60`
- `scripts/orchestration/check_review_threads_disposition.py:117`
- `scripts/orchestration/check_review_threads_disposition.py:394`
- `AGENTS.md:120`

## 12. Auth Mode Semantics

- **Local default / advisory:** disposition guard may skip when no usable `gh` auth is available.
- **Local strict parity:** `--require-auth` upgrades the disposition guard to CI-like behavior and requires `GH_TOKEN`.
- **CI strict:** `CI=true` requires `GH_TOKEN` and `gh auth status` before any GraphQL.
- `GITHUB_TOKEN` remains the merge-readiness sub-gate token; `GH_TOKEN` is the canonical disposition/GraphQL token.
- Advisory `SKIP` is not merge evidence; operators must use enforced mode before claiming strict local parity.
- Local `--pre-closeout` is valid only with `--require-auth` and both
  `GH_TOKEN` and `GITHUB_TOKEN`; it fails before network validation when either
  is absent.

Evidence:
- `AGENTS.md:120`
- `RUNBOOK_AGENT.md:246`
- `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md:45`
- `scripts/orchestration/check_review_threads_disposition.py:9`
- `scripts/orchestration/check_review_threads_disposition.py:623`
- `scripts/ci/check_pr_merge_readiness.py:308`

## 13. Roadmap / Future Hardening

- ~~Move Fixed Mapping SoT from PR body to repo file~~ ✅ Merged via PR #998 on 2026-03-07
- Stabilize allowlist keys
- AST subprocess guard
- Path-aware trigger proof

## 14. Stacked PR Replacement Rule

- If a stacked child PR auto-closes because its parent base branch was merged
  and deleted, the child review lane is no longer active
- Operators must create a new branch from `origin/main`, cherry-pick the child
  commits, rerun local gates, and open a replacement PR on `main`
- Replacement PR must get a new canonical artifact path:
  `docs/review/PR_<NEW_NUMBER>_FIXED_MAPPING.md`
- Do not continue mapping/reviewing against the auto-closed PR number
