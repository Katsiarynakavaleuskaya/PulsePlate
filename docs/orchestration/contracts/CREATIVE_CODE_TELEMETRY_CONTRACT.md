# CreativeCodeTelemetry Contract

Status: PR-4 local telemetry and rejection taxonomy. No product runtime impact.

PR-4 measures the governed creative-code private-pilot funnel from sanitized
local PR-1, PR-2, and PR-3 artifacts:

```text
CreativeCodeSpecificationBundle
-> CreativeCodePatchResult
-> CreativeCodePRPromotion plan / validation / approval / receipt
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
- `creative_code_rejection_taxonomy.v1.schema.json`

Reference taxonomy:

- `creative_code_rejection_taxonomy.v1.json`

Validators and collector:

```bash
python -m scripts.orchestration.creative_code_telemetry_contract
python -m scripts.orchestration.creative_code_telemetry
```

Local outputs stay under:

```text
artifacts/orchestration/creative_code/telemetry/
```

That directory is local-only and gitignored. It must never be committed.

## Inputs

Allowed inputs are already-sanitized local artifacts under
`artifacts/orchestration/creative_code/**`:

- PR-1 specification bundles;
- PR-2 `result.json` patch-builder results;
- PR-3 promotion plan, validation, approval, and receipt artifacts.

The collector validates those inputs with the existing PR-1/PR-2/PR-3 contract
validators before it emits any event. Malformed artifacts are counted only as
safe read-error events with fingerprint-only identifiers; raw exception text,
paths, prompts, patches, provider payloads, and command output are not copied.

## Telemetry Event

`CreativeCodeTelemetryEvent` stores:

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

`CreativeCodeTelemetryRollup` aggregates:

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

## Boundary

PR-4 is a measurement layer for the private loop. PR-5 adds a separate local,
read-only review-disposition integration over sanitized review context or
explicit fixtures, but PR-4 telemetry output remains non-disposition evidence.
Public GitHub App backend, public Slack beta, review-thread resolution, and the
first governed applied candidate remain later PRs.

Rollback removes the PR-4 telemetry contracts, collector, tests, docs, and
ledger references. Because PR-4 adds no runtime behavior, provider integration,
workflow mutation, DB migration, OpenAPI/client change, Slack setting, or GitHub
App setting, rollback requires no runtime or release coordination.
