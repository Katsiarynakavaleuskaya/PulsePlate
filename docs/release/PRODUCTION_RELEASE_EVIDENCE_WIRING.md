# Production Release Evidence Wiring

Release-control-plane PR-6 wires real production release evidence into the CD
production tag path. It consumes evidence that was produced by a separate
governed release ceremony and validates it before any production deploy job can
run.

This contract is validation-only. It does not generate fake production
evidence, contact App Store Connect, run Fastlane, mutate protected upload
automation, read App Store credentials, change runtime behavior, or change
backend, iOS, OpenAPI, RAG, billing, semantic-cache, GraphRAG, or product-facing
behavior.

## Required Artifact Source

Production tag workflows are not manually parameterized, so the CD workflow
resolves two GitHub Actions variables before deploy:

- `RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID`
- `RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME`

The variables may be defined on the `production` environment or at repository
Actions scope. Environment variables take precedence when readable through the
same protected configuration lookup used by production deploy mode resolution.

When `WEB_IOS_RELEASE_READY=true`, `PRODUCTION_ENV_READY=true`, and
`PROD_DEPLOY_MODE` requests production deploy, both variables are required.
Missing or malformed values fail closed before deploy.

## Required Artifact Layout

The downloaded artifact must contain this exact directory:

```text
release-control-plane/
  release_manifest.json
  rag_gate_result.json
  build_equivalence_result.json
```

The production tag job validates those files with:

```bash
python3 scripts/ci/check_release_control_plane.py \
  --release-manifest "${evidence_dir}/release_manifest.json" \
  --rag-gate-result "${evidence_dir}/rag_gate_result.json" \
  --build-equivalence "${evidence_dir}/build_equivalence_result.json" \
  --json-out "${output_dir}/release_control_plane_ci_gate.json" \
  --markdown-out "${output_dir}/release_control_plane_ci_gate.md"
```

The checker must return `ALLOW`. Any `BLOCK` decision exits nonzero and blocks
production deploy.

## Published Evidence

The production evidence job uploads:

```text
release_control_plane_ci_gate.json
release_control_plane_ci_gate.md
```

as workflow artifact:

```text
release-control-plane-ci-gate-cd-production
```

The Markdown summary is also appended to the GitHub Actions step summary when
the checker produced it.

## Fail-Closed Rules

Production deploy must not proceed when:

- `RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID` is missing or not numeric;
- `RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME` is missing or names a fixture;
- the configured artifact cannot be downloaded;
- any required file is absent from `release-control-plane/`;
- any evidence JSON is malformed;
- the release manifest decision is `BLOCK`;
- the RAG gate result decision is not `PASS`;
- the build-equivalence decision is not `EQUIVALENT`;
- SBOM/provenance digests are missing or malformed;
- attestation status is not `VERIFIED`;
- evidence hashes, release manifest hash, git SHA, or build identity mismatch;
- the checker cannot produce deterministic JSON output.

The workflow must not use `continue-on-error` for this gate.

## Fixture Boundary

Fixtures are allowed only in tests and in the non-secret `main` fixture
validation job that exercises the checker contract.

Fixtures must never be downloaded or substituted in the production tag path.
The production evidence artifact name rejects `fixture` in any casing, and the
production workflow job must not reference test fixture paths.

## Deferred Work

This PR does not automate App Store Connect upload or Fastlane protected upload
mutation. Those remain later explicitly scoped protected-environment slices.
