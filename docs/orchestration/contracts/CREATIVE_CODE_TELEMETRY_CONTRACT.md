# CreativeCodeTelemetry Contract

Status: PR-4 local telemetry plus terminal outcome envelope v1. No product
runtime impact.

PR-4 measures the governed creative-code private-pilot funnel from sanitized
local PR-1, PR-2, and PR-3 artifacts:

```text
CreativeCodeSpecificationBundle
-> CreativeCodePatchResult
-> CreativeCodePRPromotion plan / validation / approval / receipt
-> CreativeCodeTerminalOutcomeV1
-> CreativeCodeTelemetryEvent
-> CreativeCodeTelemetryRollup
```

It does not authorize repository writes, branch or PR creation, review-thread
resolution, fixed-mapping edits, merge-readiness claims, merge, release,
provider calls, product runtime AI, OpenAPI/client changes, frontend/iOS
changes, Slack delivery, GitHub App changes, semantic-cache activation, or
public multi-tenant use.

## Artifacts

Strict schemas:

- `creative_code_telemetry_event.v1.schema.json`
- `creative_code_telemetry_rollup.v1.schema.json`
- `creative_code_terminal_outcome.v1.schema.json`
- `creative_code_telemetry_event.v2.schema.json`
- `creative_code_telemetry_rollup.v2.schema.json`
- `creative_code_rejection_taxonomy.v1.schema.json`

Reference taxonomy:

- `creative_code_rejection_taxonomy.v1.json`

Validators and collector:

```bash
python -m scripts.orchestration.creative_code_telemetry_contract
python -m scripts.orchestration.creative_code_telemetry
python -m scripts.orchestration.creative_code_terminal_outcome build \
  --promotion-plan <promotion_plan.json> \
  --promotion-receipt <promotion_receipt.json> \
  --observation <sanitized_observation.json>
python -m scripts.orchestration.creative_code_terminal_outcome validate \
  --outcome <terminal_outcome.json>
```

Local outputs stay under:

```text
artifacts/orchestration/creative_code/telemetry/
artifacts/orchestration/creative_code/terminal_outcomes/<outcome-id>/terminal_outcome.json
```

That directory is local-only and gitignored. It must never be committed.

## Inputs

Allowed inputs are already-sanitized local artifacts under
`artifacts/orchestration/creative_code/**`:

- PR-1 specification bundles;
- PR-2 `result.json` patch-builder results;
- PR-3 promotion plan, validation, approval, and receipt artifacts.
- a caller-supplied, closed, sanitized terminal observation cross-bound to one
  validated open PR-3 promotion receipt.

The collector validates those inputs with the existing PR-1/PR-2/PR-3 contract
validators before it emits any event. Malformed artifacts are counted only as
safe read-error events with fingerprint-only identifiers; raw exception text,
paths, prompts, patches, provider payloads, and command output are not copied.

The terminal observation is an input object, not a second canonical artifact
type. It contains only promotion/PR/head binding, a positive closure epoch,
one observed terminal branch, bounded aggregate review/post-merge/process
evidence, the existing closed cost shape, and `sanitized=true`. It cannot
contain PR bodies, comments, prompts, patches, snippets, oracle output,
free-form notes, URLs, or paths. Terminal state collection failure emits no
outcome; `terminal_evidence_unavailable` is an input/collection error, not a
third terminal state.

## Terminal Outcome Envelope

`CreativeCodeTerminalOutcomeV1` is the sole semantic carrier after `pr_open`.
It validates and cross-binds the existing promotion plan and receipt, then
records exactly one immutable `merged` or `closed_unmerged` observation.
Identity is content-bound to repository, PR number, promotion id, and promoted
head SHA; terminal state and closure epoch do not change that identity.
Identical replay is byte-preserving and performs no target write. A different
payload for the same identity fails as `divergent_replay` and preserves the
first outcome.

Review and governance outputs use observation vocabulary only:

- `actionables_observed | no_actionables_observed | evidence_unavailable`;
- `blockers_observed | no_blockers_observed | evidence_unavailable`.

A complete, frozen source inventory plus exact aggregate counters is required
before any negative review observation can be derived. A seal fingerprint is
only a bound evidence reference; it is not provider verification, review
completion, PASS, no-findings, or merge-readiness evidence.

Post-merge output is likewise observational:

- merged: `complete_observed | incomplete_observed | evidence_unavailable`;
- closed-unmerged: exactly `not_applicable`.

Completion requires a frozen validation inventory and either all configured
commands executed/passed or an observed successful current-main CI SHA.
Failure or execution gaps derive `incomplete_observed`. The outcome does not
claim that a validation provider passed.

## Telemetry Event

The existing v1 `CreativeCodeTelemetryEvent` and its content-bound identities
remain unchanged. Without a terminal input the collector emits the same v1
events and v1 rollup.

With terminal inputs, each validated outcome projects into exactly one durable
v2 event:

```text
lane_stage=pr_terminal
status=merged|closed_unmerged
```

The one event binds the outcome id and fingerprint and carries only the
terminal lineage projection, closure epoch, derived observation tokens,
process counters, and the closed cost shape. It does not copy merge SHA,
closed reason, inventories, review counters, validation counters, or raw
evidence. Persisting separate review/terminal/post-merge events is forbidden:
those independently countable projections would become a second semantic
carrier.

The v1 event stores:

- stable event identity and idempotency key;
- source artifact type, id, and fingerprint;
- lane stage and status;
- candidate lineage IDs when available;
- closed rejection taxonomy codes;
- bounded counts and sizes;
- cost metadata placeholders only when sanitized counts exist;
- explicit non-authority flags.

It must not store raw patch text, raw prompts, raw model responses, reasoning,
provider payloads, oracle stdout/stderr, local absolute paths, secrets, token
values, Slack payloads, GitHub API payloads, review thread bodies, PR bodies, or
merge-readiness claims.

## Rejection Taxonomy

The taxonomy is closed. Events may reference only stable codes from
`creative_code_rejection_taxonomy.v1.json`.

Unknown is allowed as a counted class so drift is visible, but free-form
rejection explanations are not allowed in telemetry events. Detailed source
messages stay in the source local artifacts only if those artifacts are already
sanitized by their own contracts.

## Rollup

The v1 `CreativeCodeTelemetryRollup` aggregates:

- funnel counts;
- integer basis-point rates;
- counts by stage, status, failure class, and rejection class;
- source artifact fingerprints;
- local-only caveats.

Rates use basis points for deterministic integer math:

```text
10000 = 100%
5000 = 50%
```

The rollup is advisory only. It is not routing truth, fixed-mapping evidence,
bot-review disposition evidence, merge-readiness evidence, product runtime
truth, or release evidence.

When terminal inputs are explicitly supplied, the collector emits a mixed v2
rollup. V1 events continue to contribute only to the legacy funnel. Unique v2
terminal events contribute merged/closed counts, review/governance/post-merge
observation counts, and process/cost totals exactly once. `merge_rate_bps` uses
all terminal outcomes; `post_merge_complete_rate_bps` uses only
`complete_observed + incomplete_observed`. Duplicate event ids, duplicate
terminal lineages, and source-fingerprint drift fail closed.

## Boundary

PR-4 is a measurement layer for the private loop. PR-5 adds a separate local,
read-only review-disposition integration over sanitized review context or
explicit fixtures, but PR-4 telemetry output remains non-disposition evidence.
This terminal envelope is an intermediate control-plane continuation of the
existing creative-code trajectory. It is not Pilot 3, OCW, a new product
hypothesis, or a new telemetry stack. It adds no GitHub/network reader or
writer, raw Markdown/comment parser, provider call, Evidence Graph adapter,
probability/cognitive state, workflow, DB, API/OpenAPI, product runtime,
semantic cache, merge authority, or public GitHub App/Slack surface.

Rollback is an ordinary revert of the terminal contract/CLI, v2 projection and
rollup support, schemas, tests, docs, and ledger references. Existing v1
artifacts remain readable and byte-stable. No runtime, DB, API, workflow, or
release migration is required.
