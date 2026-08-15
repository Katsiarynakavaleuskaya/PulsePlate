# CreativeCodeTelemetry Contract

Status: PR-4 local telemetry, terminal outcome envelope v1, and deterministic
local lifecycle transition analytics v1. No product runtime impact.

PR-4 measures the governed creative-code private-pilot funnel from sanitized
local PR-1, PR-2, and PR-3 artifacts:

```text
CreativeCodeSpecificationBundle
-> CreativeCodePatchResult
-> CreativeCodePRPromotion plan / validation / approval / receipt
-> CreativeCodeTerminalOutcomeV1
-> CreativeCodeTelemetryEvent
-> CreativeCodeTelemetryRollup
-> CreativeCodeLifecycleTransitionAnalyticsV1
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
- `creative_code_lifecycle_transition_analytics.v1.schema.json`

Reference taxonomy:

- `creative_code_rejection_taxonomy.v1.json`

The JSON Schemas are closed-shape, finite-vocabulary, and finite-implication
contracts. The Python validators are the normative semantic validators. Draft
2020-12 cannot express general equality, ordering, or sum relationships between
sibling numeric properties, so schema-only acceptance does not prove terminal
semantic validity. In particular, the Python terminal validator remains the
single owner of source-count equality, disposition-sum equality,
`commands_passed <= commands_executed <= commands_configured`, derived
observation tokens, content-bound identities, and idempotency hashes. The v2
Python validator/rollup builder likewise remains normative for content-bound
event identity, rollup arithmetic, rates, and single-counted outcome cost.

Validators and collector:

```bash
VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
"$VENV_PYTHON" -m scripts.orchestration.creative_code_telemetry_contract
"$VENV_PYTHON" -m scripts.orchestration.creative_code_telemetry
"$VENV_PYTHON" -m scripts.orchestration.creative_code_terminal_outcome build \
  --promotion-plan <promotion_plan.json> \
  --promotion-receipt <promotion_receipt.json> \
  --observation <sanitized_observation.json>
"$VENV_PYTHON" -m scripts.orchestration.creative_code_terminal_outcome validate \
  --outcome <terminal_outcome.json>
"$VENV_PYTHON" -m scripts.orchestration.creative_code_lifecycle_transition_analytics build \
  --telemetry-dir artifacts/orchestration/creative_code/telemetry
"$VENV_PYTHON" -m scripts.orchestration.creative_code_lifecycle_transition_analytics validate \
  --telemetry-dir artifacts/orchestration/creative_code/telemetry
```

Local outputs stay under:

```text
artifacts/orchestration/creative_code/telemetry/
artifacts/orchestration/creative_code/terminal_outcomes/<outcome-id>/terminal_outcome.json
artifacts/orchestration/creative_code/lifecycle_transition_analytics/<analytics-id>/analytics.json
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
type. It contains only promotion/PR/head binding, a bounded logical
`closure_epoch` sequence in `[1, 1_000_000]`, one observed terminal branch,
bounded aggregate review/post-merge/process evidence, the existing closed cost
shape, and `sanitized=true`. `closure_epoch` distinguishes terminal collection
attempts for replay detection; it is not a wall-clock or Unix timestamp. The
observation cannot contain PR bodies, comments, prompts, patches, snippets,
oracle output, free-form notes, URLs, or paths. Terminal state collection
failure emits no outcome; `terminal_evidence_unavailable` is an input/collection
error, not a third terminal state.

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

Completion requires a frozen validation inventory, no configured-command
execution/pass gaps, and at least one observed evidence source: either all
configured commands were executed and passed or current-main CI succeeded.
CI failure or any configured/executed/passed gap derives
`incomplete_observed`; successful CI never overrides a command gap. The outcome
does not claim that a validation provider passed.

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

## Lifecycle Transition Analytics

`CreativeCodeLifecycleTransitionAnalyticsV1` is a deterministic, read-only
consumer of one exact mixed v2 event/rollup snapshot. It rebuilds the v2 rollup
from the validated events and requires semantic equality before deriving any
aggregate. The closed adjacent graph is:

```text
specification -> patch_evaluation -> promotion_plan
-> promotion_validation -> promotion_approval -> pr_open -> pr_terminal
```

The first join uses exact `(source_bundle_id, selected_variant_id)`, the second
uses exact `(source_bundle_id, selected_variant_id, request_id, result_id)`,
and all later joins use exact `promotion_id`. Multiple patch attempts from one
accepted specification and multiple distinct promotion attempts from one
accepted patch are counted as separate destination transitions. Duplicate
promotion-stage carriers, multiple possible predecessors, incompatible status
transitions, non-canonical event profiles, source drift, or stale rollup input
fail closed. A missing adjacent event creates an explicit unobserved-neighbor
count; it never creates a skip edge. Rejected patches and blocked PR openings
are observed stop branches and do not create missing-successor claims.

The artifact contains only aggregate transition rows, complete/incomplete
terminal-lineage counts, fixed `0 | 1 | 2 | 3_or_more` terminal process
histograms, corpus fingerprints, and non-authority flags. It contains no event,
source, candidate, promotion, PR, SHA, path, timestamp, review, prompt, patch,
command, provider, or oracle payload. Existing rollup marginal distributions
remain owned by the rollup. The sibling three-row Evidence Eval projection
remains one indivisible normalization bundle and is never counted as three
lifecycle transitions.

Publication is fixed under the local creative-code analytics root, mode `0600`,
and atomic no-replace. Inputs and existing winners must be bounded, regular,
single-link, and symlink-free within the cooperative-local threat boundary.
Identical replay is byte-preserving and mutation-free. Changed source identity,
malformed or divergent winner bytes, ambiguous namespace contents, or any
validation mismatch fails without overwrite, deletion, or repair. The
read-only validator recreates the expected artifact from the same snapshot and
performs no filesystem mutation.

## Boundary

PR-4 is a measurement layer for the private loop. PR-5 adds a separate local,
read-only review-disposition integration over sanitized review context or
explicit fixtures, but PR-4 telemetry output remains non-disposition evidence.
This terminal envelope and its aggregate lifecycle consumer are intermediate
control-plane continuations of the existing creative-code trajectory. They are
not Pilot 3, OCW, a new product hypothesis, or a new telemetry stack. They add
no GitHub/network reader or writer, raw Markdown/comment parser, provider call,
Evidence Graph adapter, probability/cognitive state, workflow, DB, API/OpenAPI,
product runtime, semantic cache, routing/learning authority, merge authority,
or public GitHub App/Slack surface.

Rollback of transition analytics is an ordinary revert of its consumer
contract/CLI, schema, tests, docs, and ledger references. Existing v1/v2
telemetry and terminal/evidence artifacts remain readable and byte-stable. No
runtime, DB, API, workflow, or release migration is required.
