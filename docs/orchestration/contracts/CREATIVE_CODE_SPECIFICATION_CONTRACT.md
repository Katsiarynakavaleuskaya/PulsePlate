# CreativeCodeSpecificationBundle Contract

Status: PR-1 local control-plane contract. Specification-only. No runtime impact.

`CreativeCodeSpecificationBundle` is the first executable handoff after a valid
PR-0 `CreativeCodeCandidatePacket`. It converts promoted creative-research
provenance into deterministic implementation specifications, skeptic review
records, synthesis, telemetry summary, and a fingerprint-only rejection index.

It does not authorize candidate patches, repository writes, provider calls,
network calls, OpenAPI/client changes, product runtime behavior, Slack/GitHub
authority, review-thread disposition, merge readiness, release activity, public
multi-tenant use, semantic-cache use, or scientific/medical overclaims.

## Artifacts

- Schema: `docs/orchestration/contracts/creative_code_specification.v1.schema.json`
- Reference: `docs/orchestration/contracts/creative_code_specification.v1.json`
- Validator: `python -m scripts.orchestration.creative_code_specification --validate docs/orchestration/contracts/creative_code_specification.v1.json`
- Local CLI: `python -m scripts.orchestration.creative_code_spec_pipeline prepare --packet <candidate.json> --run-dir <run>`
- Rejection index: `scripts/orchestration/creative_code_rejection_index.py`

## Required Source

PR-1 admission starts only from a valid PR-0 `CreativeCodeCandidatePacket`.
The pipeline must call `validate_creative_code_candidate_packet(...)` before it
builds specifications.

The source packet must already prove:

- `promotion_decision=promote`
- `gate_status=closed`
- `authority_class=code-specification`
- `variant_count` between 3 and 5
- sandbox and human review required
- repo-relative target/oracle paths
- disjoint mutable target surfaces and immutable oracles
- all provider, repo-write, PR, review, merge, release, runtime, OpenAPI/client,
  semantic-cache, public multi-tenant, and Slack/GitHub authority flags false

## Bundle Shape

Every valid bundle includes:

- deterministic `bundle_id` and `idempotency_key`
- `source_packet_fingerprint` and source creative-research provenance
- exactly `variant_count` specification variants
- complete skeptic coverage for each variant from:
  `architecture-specialist`, `security-auditor`, and `qa-engineer-agent`
- deterministic synthesis with `next_authority=human_review_required`
- fingerprint-only rejection index
- PR-1 telemetry fields:
  `packet_id`, `source_candidate_id`, `variant_count`, `generation_status`,
  `oracle_status`, `failure_class`, `human_decision`, and
  `cost_metadata_available`

## Specification Variants

Each variant must define:

- unique `variant_id`
- unique `approach_family`
- `variant_fingerprint`
- problem statement
- implementation steps
- target paths contained by the source packet `target_surface`
- tests to add
- negative controls
- rollback plan
- falsifier
- risk notes
- wellness-only boundary
- estimated changed-file count

Allowed approach families:

- `minimal_surgical_change`
- `seam_extraction`
- `fail_closed_guard`
- `observable_metadata_only`
- `test_first_contract_lock`

The bundle rejects duplicate variant IDs, duplicate approach families, duplicate
fingerprints, bool-like integers, unsupported nested fields, unsafe paths, unsafe
authority text, patch/diff payloads, raw prompts/responses, secrets, local
absolute paths, provider/network/Slack/GitHub actions, review-thread actions,
merge-readiness claims, semantic-cache serving claims, and medical overclaims.

## Skeptic Review And Synthesis

Every variant must have one review from each required skeptic role. Missing,
duplicate, skipped, errored, or pending reviews block selection.

The JSON Schema mirrors the executable coverage floor with exact review counts:
9 reviews for 3 variants, 12 for 4 variants, and 15 for 5 variants. The Python
validator remains the authority for per-variant reviewer-role uniqueness.

`pass` reviews must be clean: no blockers, unsafe authority flags, duplicate
reason, or required revision. `reject` reviews require blockers. `revise`
reviews require revision notes and are not selectable.

Synthesis is deterministic:

- fully passed variants are ranked by the fixed policy
  `pass_count_then_fingerprint_then_ordinal`
- selected variants must not be rejected, duplicate, or unreviewed
- `all_rejected` is a valid terminal state with no selected variant, non-empty
  rejection records, fallback, human review required, and no patch/runtime effect

## Local Pipeline

`creative_code_spec_pipeline.py` is the only PR-1 file-I/O layer.

`prepare` validates the PR-0 packet, writes deterministic local artifacts under
`artifacts/orchestration/creative_code`, and emits metadata-only context-pack
compression data. `finalize` reads the local source packet, variants, and
skeptic reviews, then writes the validated bundle atomically.

The CLI must reject symlink escapes, paths outside the repository or artifact
root, non-JSON inputs, duplicate JSON keys, and partial-write states. The pure
validator module has no filesystem writes, subprocesses, provider imports,
network imports, GitHub/Slack calls, or product-runtime imports.

## Rejection Index

Rejected variants are recorded in
`CreativeCodeRejectionIndex` as fingerprints and reason codes only:

- `variant_id`
- `variant_fingerprint`
- `reason_codes`
- `reviewer_roles`

The index must not store raw prompts, raw source packets, raw candidate prose,
generated code, patches, provider payloads, oracle stdout/stderr, local absolute
paths, secrets, or token values.

## PR-2 Handoff

PR-2 may consume a valid `CreativeCodeSpecificationBundle` only through
`CreativeCodePatchBuildRequest`. The request must bind the full source bundle
fingerprint, selected variant ID/fingerprint, exact `origin/main` base SHA, and
explicit human admission. PR-1 does not infer patch authority by itself.

The PR-2 builder may generate local `candidate.patch` artifacts only inside an
isolated no-remote checkout and may evaluate them only through Experiment Runner
candidate-patch mode. It must not mutate the shared worktree, call promotion or
notification wrappers, open branches/PRs, resolve review threads, or store raw
patches/prompts/output in sanitized results.

Contract: `docs/orchestration/contracts/CREATIVE_CODE_PATCH_BUILDER_CONTRACT.md`.

## Boundary

This contract is not fixed-mapping evidence, bot-review disposition evidence,
merge-readiness evidence, public scientific proof, product runtime truth, or a
release signal. PR-2 opens only the local sandboxed candidate-patch builder
described above; repository-write and promotion authority remain closed until a
later operator-approved gate lands.
