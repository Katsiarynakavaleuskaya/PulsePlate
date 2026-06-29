# CreativeCodeReviewDisposition Contract

Status: PR-5 local review-disposition integration. No product runtime impact.

PR-5 connects ordinary PR review feedback to the governed creative-code lane
without granting mutation authority:

```text
sanitized PR review context / read-only fixture
-> CreativeCodeReviewFeedbackRecord
-> CreativeCodeReviewDispositionPacket
-> CreativeCodeRepairLaunchPacket
-> later human/coordinator PR-1 specification start
```

It does not authorize repository writes, branch or PR creation, GitHub review
submission, review-thread resolution, fixed-mapping edits, merge-readiness
claims, merge, release, provider calls, product runtime AI, OpenAPI/client
changes, frontend/iOS changes, Slack delivery, GitHub App changes,
semantic-cache activation, or public multi-tenant use.

## Artifacts

Strict schemas:

- `creative_code_review_feedback_record.v1.schema.json`
- `creative_code_review_disposition_packet.v1.schema.json`
- `creative_code_repair_launch_packet.v1.schema.json`

Validator and CLI:

```bash
python -m scripts.orchestration.creative_code_review_disposition_contract <artifact.json>
python -m scripts.orchestration.creative_code_review_disposition collect --review-context <context.json>
python -m scripts.orchestration.creative_code_review_disposition classify --input <records.json>
python -m scripts.orchestration.creative_code_review_disposition prepare-launch --disposition-packet <packet.json>
```

Local outputs stay under:

```text
artifacts/orchestration/creative_code/review_disposition/
```

That directory is local-only and gitignored. It must never be committed.

## Feedback Record

`CreativeCodeReviewFeedbackRecord` stores:

- safe source metadata and fingerprints;
- optional repo-relative review surface;
- bounded sanitized excerpt plus body fingerprint;
- advisory disposition candidate;
- explicit false authority flags.

Allowed disposition candidates are:

- `simple_fix`
- `creative_repair_candidate`
- `not_a_bug_candidate`
- `defer_candidate`
- `out_of_scope`
- `security_blocker`

Every candidate remains a human decision. A record must not store raw review
thread bodies, PR bodies, bot payloads, patches, prompts, provider payloads,
oracle stdout/stderr, local absolute paths, secrets, token values, or merge
readiness proof.

## Disposition Packet

`CreativeCodeReviewDispositionPacket` aggregates feedback records against a
single source context and optional expected/actual head SHA pair. If the head
SHA differs, all records become advisory head-drift blocks and no repair launch
may be prepared.

The packet is advisory only. It is not fixed-mapping evidence, review-thread
disposition proof, merge-readiness evidence, product runtime truth, or release
evidence.

## Repair Launch Packet

`CreativeCodeRepairLaunchPacket` is the only PR-5 handoff into the creative-code
repair lane. It may set only:

```text
create_pr1_specification = true
```

All patch generation, branch writes, pushes, PR creation, review-thread
resolution, fixed-mapping edits, merge, and release authority remain false.

The launch packet prepares a human/coordinator decision to start the existing
PR-1 specification lane. It does not itself run PR-1, PR-2, PR-3, or PR-6.

## Boundary

PR-5 makes the review-to-creative handoff explicit while preserving the split
from PR-6. The first governed applied candidate remains PR-6 and must pass
normal PR governance as a separate lane.

Rollback removes the PR-5 contract docs, schemas, validator, CLI, tests, and
ledger references. Because PR-5 adds no runtime behavior, provider integration,
workflow mutation, DB migration, OpenAPI/client change, Slack setting, or
GitHub App setting, rollback requires no runtime or release coordination.
