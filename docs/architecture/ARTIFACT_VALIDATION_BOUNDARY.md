# Artifact Validation Boundary

Status: Accepted guardrail

<!-- ARTIFACT_BOUNDARY_STATUS: accepted_guardrail -->
<!-- ARTIFACT_BOUNDARY_RUNTIME_READS_ALLOWED: false -->
<!-- ARTIFACT_BOUNDARY_RAW_PUBLICATION_ALLOWED: false -->
<!-- ARTIFACT_BOUNDARY_MISSING_OR_MALFORMED: fail_closed -->
<!-- ARTIFACT_BOUNDARY_SEMANTIC_CACHE_SERVING: false -->

## Context

PulsePlate has many governance artifacts: task packets, review mappings,
Experiment Runner evidence, release-control-plane evidence, verification
reports, semantic-cache gate documents, and local audit traces. These artifacts
support review and control-plane decisions. They are not product runtime truth.

Recent PR waves exposed repeated failure classes:

- malformed JSON readers assuming an object shape;
- raw attestation or provider payloads being too close to publication surfaces;
- stale evidence accepted without git or source binding;
- local workspace artifact paths being treated as trusted input;
- legacy artifact formats drifting without explicit adapters.

## Decision

Artifact readers must use a fail-closed validation boundary before a parsed file
can influence governance output. Product runtime code must not read local
governance artifact roots directly.

Reader contract:

1. Parse bytes as UTF-8 text and JSON when applicable.
2. Reject malformed JSON with stable diagnostics.
3. Reject non-object top-level JSON unless the reader explicitly documents an
   array or scalar contract.
4. Validate schema, required keys, and value types before use.
5. Bind evidence to `git_sha`, `source_fingerprint`, `policy_version`, or an
   equivalent source-specific identity when the artifact can influence a
   release, admission, review, or merge decision.
6. Publish sanitized summary, digest, status, count, or reason-code fields only.
7. Keep raw provider payloads, raw prompts, raw responses, workflow logs, local
   absolute paths, tokens, and secrets out of public summaries.
8. Read legacy artifact formats only through exact legacy adapters with a sunset
   or migration policy.

## Runtime Boundary

The following roots are local/control-plane evidence and must not be product
runtime inputs:

- `artifacts/orchestration/`
- `artifacts/agent_runs/`
- `artifacts/security_lab/`

Allowed readers live in governance tooling, CI tooling, tests, or local operator
helpers. Product runtime roots such as `legacy_app.py`, `app/`, `core/`, and
`providers/` may mention artifact policy or write bounded audit traces, but they
must not read, enumerate, or existence-check these local artifact roots to drive
responses, feature flags, provider behavior, cache admission, knowledge
promotion, or release truth.

Write-only audit traces are allowed only when the code path cannot read the
existing artifact payload.

## Guard Contract

`scripts/ci/check_artifact_reader_contracts.py` statically scans product runtime
source for direct reads or enumeration of local governance artifact roots. It
also validates this document's machine-readable markers.

The guard is intentionally narrow:

- it does not scan `scripts/`, `tests/`, or `docs/`;
- it does not ban general food-data, catalog, template, or user-data file reads;
- it does not treat `core/verification` artifacts or evidence metadata terms as
  local artifact-file reads;
- it does not open semantic-cache serving or runtime artifact reuse.

## Exit Criteria

This boundary can be narrowed only when all are true:

1. A dedicated reviewed artifact safety gateway exists.
2. Every artifact reader has typed contract coverage and deterministic
   fail-closed tests.
3. Raw-to-sanitized evidence reduction is centralized for release, review, and
   admission artifacts.
4. Product runtime rails remain separate from advisory wiki, support-plane, and
   local orchestration artifacts.
5. Any semantic-cache or retrieval-serving admission is approved through its
   dedicated gate-open PR.

## Validation

Use:

```bash
python3 scripts/ci/check_artifact_reader_contracts.py
pytest -q tests/test_artifact_validation_boundary.py
```

This guard does not change runtime behavior, OpenAPI, database state,
semantic-cache serving, FoodDB cutover, or provider routing.
