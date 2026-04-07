# ADR: Docker build provenance: false workaround (2026-03-01)

## Status
Accepted (temporary seam)

## Context
Docker image push to GHCR was failing with `failed to push ... cache entry no longer exists` when using `cache-from: type=gha` and default provenance. This is a known class of issues with buildx + GHA cache backend where cache blobs can become unavailable during export/push.

To unblock main and stabilize CI/CD, we keep the existing workaround profile in
`.github/workflows/build.yml` and align `.github/workflows/cd.yml` with the same
provenance/single-arch policy:

1. **provenance: false** — disables SLSA build provenance attestations so buildx does not generate attestations that can interact badly with the cache export path.
2. **Single-arch (linux/amd64)** in publish step — reduces surface for cache/export issues; multi-arch can be restored when cache/provenance stack is stable.
3. **Scoped `cache-from: type=gha` + `cache-to: type=gha,mode=min,ignore-error=true`** on CD image builds — an earlier iteration omitted `cache-from` on CD to avoid `BlobNotFound`; the current workflows reintroduced **ref-scoped** `cache-from` keys (`cd-staging-*`, `cd-production-*`) to improve hit rate while keeping `mode=min` and `ignore-error=true` on export as the fail-safe profile (same pattern as `build.yml` publish).

**Local `load: true` jobs (smoke / PR CI):** `docker/build-push-action` with `push: false` and `load: true` uses the docker exporter. Docker’s attestations model expects a registry push; **SLSA provenance attestations are not supported for `load: true`** (local image store). Those jobs therefore keep `provenance: false` for an explicit, stable contract until a **separate** push-based pilot (e.g. GHCR tag + scan-only) is designed — not by flipping `provenance` on the same step as `load: true`.

## Decision
- Keep `provenance: false` in the existing `build.yml` publish step and set it
  in the corresponding `cd.yml` image-build steps.
- Keep single platform `linux/amd64` for the affected publish/deploy/CD steps;
  document intent to restore `linux/arm64` when GHA cache/provenance is
  stable.
- Keep **scoped** `cache-from` / `cache-to` on CD image builds aligned with the
  bounded cache profile used on `build.yml` (`mode=min`, `ignore-error=true` on
  `cache-to`).
- Keep `provenance: false` on all jobs that use `load: true` until a dedicated
  registry-backed build path is introduced for attestations.
- Inline comments in the workflow document the trade-off (SLSA attestations disabled; `cosign verify-attestation` will fail for consumers) and re-enable intent.
- This ADR documents the temporary seam and exit criteria.

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
