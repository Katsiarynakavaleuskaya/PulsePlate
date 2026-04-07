# ADR: Docker build provenance: false workaround (2026-03-01)

## Status
Accepted (temporary seam)

## Context
Docker image push to GHCR was failing with `failed to push ... cache entry no longer exists` when using `cache-from: type=gha` and default provenance. This is a known class of issues with buildx + GHA cache backend where cache blobs can become unavailable during export/push.

To unblock main and stabilize CI/CD, we keep one workaround profile across
workflows. The **steps below follow the same order as** [Evidence Anchors](#evidence-anchors-fileline) (top → bottom) so operators can walk the YAML and the ADR in lockstep.

1. **`build.yml` — local test image (`load: true`)** — `push: false`, scoped `cache-from` / `cache-to` (`build-production-${{ github.ref_name }}`, `mode=min`, `ignore-error=true`), **`provenance: false`**. Uses the docker exporter; **SLSA attestations are not supported for `load: true`** (registry push is required for attestations). Do not enable `provenance` on this step without a separate push-based job.
2. **`build.yml` — publish to GHCR (`push: true`)** — **`platforms: linux/amd64`** only (reduces cache/export surface; restore `linux/arm64` when stable), same scoped cache pattern as (1), **`provenance: false`** to avoid buildx/GHA `"cache entry no longer exists"` / BlobNotFound on export.
3. **`cd.yml` — staging image** — **`cache-from` / `cache-to`** with scope `cd-staging-${{ github.ref_name }}` (`mode=min`, `ignore-error=true`), **`provenance: false`**, `target: staging`, **`linux/amd64`**.
4. **`cd.yml` — production image** — same cache policy with scope **`cd-production-${{ github.ref_name }}`**, **`provenance: false`**, **`linux/amd64`**.
5. **`docker-openapi-smoke.yml` — smoke build** — same pattern as (1): `load: true`, scoped cache (`docker-openapi-smoke-v2-${{ github.ref_name }}`), **`provenance: false`** (attestations incompatible with `load`; see (1)).

Cross-cutting themes: **scoped GHA cache keys** (per ref / job family) replace an older “omit `cache-from` on CD” iteration that avoided `BlobNotFound` but hurt hit rate; **`ignore-error=true` on `cache-to`** remains the export fail-safe everywhere.

## Decision
Aligned with **Context steps (1)–(5)** above (same order as [Evidence Anchors](#evidence-anchors-fileline)):

- Keep **`provenance: false`** on every `docker/build-push-action` step listed in those anchors (`load: true` and `push: true` paths) until a **separate** registry-backed pilot exists for attestations.
- Keep **`linux/amd64` only** on all publish/CD image builds; restore multi-arch when cache/provenance is stable.
- Keep **scoped** `cache-from: type=gha` + `cache-to: type=gha,mode=min,ignore-error=true` on each of those steps (scopes differ per job; see anchors).
- Keep **inline comments** in workflows stating the trade-off (SLSA off; `cosign verify-attestation` fails for these images) and intent to re-enable.
- Treat this ADR as the temporary seam SoT until **Exit Criteria** are met.

## Rationale
- Restores green CI/CD and reliable image pushes to GHCR.
- Trade-off is explicit: we lose attestations until upstream/buildx or GHA cache behavior is fixed.
- Single-arch reduces variables while cache/provenance tooling is unstable.
- Scoped `cache-from` on CD improves cache reuse while `ignore-error=true` on `cache-to` limits export-time flakes.

## Consequences
- Image consumers cannot verify SLSA provenance via cosign for images built by this workflow until the workaround is removed.
- Arm64 image builds are deferred until we re-enable multi-platform.
- Smoke and other `load: true` CI jobs cannot serve as a provenance pilot without changing architecture (e.g. build+push to a scratch tag, then pull/run).

## Evidence Anchors (file:line)
- `.github/workflows/build.yml:42`-`.github/workflows/build.yml:56` local build job: `load: true`, scoped `cache-from` / `cache-to`, `provenance: false`.
- `.github/workflows/build.yml:217`-`.github/workflows/build.yml:236` publish: `linux/amd64`, `push: true`, scoped `cache-from` / `cache-to`, `provenance: false`.
- `.github/workflows/cd.yml:87`-`.github/workflows/cd.yml:108` staging image: `cache-from` / `cache-to`, `provenance: false`, `target: staging`.
- `.github/workflows/cd.yml:284`-`.github/workflows/cd.yml:305` production image: `cache-from` / `cache-to`, `provenance: false`.
- `.github/workflows/docker-openapi-smoke.yml:61`-`.github/workflows/docker-openapi-smoke.yml:79` smoke build: `load: true`, `provenance: false` (attestations incompatible with `load`; see Context).

## Exit Criteria / Definition of Done
- [ ] Upstream fix or documented stable approach: buildx and/or GHA cache backend no longer produces "cache entry no longer exists" (or equivalent) when using `cache-from: type=gha` and provenance enabled.
- [ ] Remove `provenance: false` and restore default or `provenance: mode=max`
  in the affected publish/deploy workflow steps (registry push paths only).
- [ ] Re-evaluate cache scopes and `mode=min` vs `mode=max` once provenance is re-enabled on GHCR pushes.
- [ ] Optionally restore `platforms: linux/amd64,linux/arm64` when
  cache/provenance is stable.
- [ ] Update this ADR status to Superseded with a pointer to the removal PR when workaround is removed.

## Links
- Workflow: `.github/workflows/build.yml`.
- Workflow: `.github/workflows/cd.yml`.
- Docker CI attestations overview: https://docs.docker.com/build/ci/github-actions/attestations/
