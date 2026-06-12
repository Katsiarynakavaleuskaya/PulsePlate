# ADR: Docker build provenance: false workaround (2026-03-01)

## Status
Superseded in part by the 2026-04-23 pushed-image provenance restore lane

## Context
Docker image push to GHCR was failing with `failed to push ... cache entry no longer exists` when using `cache-from: type=gha` and default provenance. This is a known class of issues with buildx + GHA cache backend where cache blobs can become unavailable during export/push.

To unblock main and stabilize CI/CD, we keep one workaround profile across
workflows. The **steps below follow the same order as** [Evidence Anchors](#evidence-anchors) (top → bottom) so operators can walk the YAML and the ADR in lockstep.

1. **`build.yml` — local test image (`load: true`)** — `push: false`, scoped `cache-from` / `cache-to` (`build-production-${{ github.ref_name }}`, `mode=min`, `ignore-error=true`), **`provenance: false`**. Uses the docker exporter; **SLSA attestations are not supported for `load: true`** (registry push is required for attestations). Do not enable `provenance` on this step without a separate push-based job.
2. **`build.yml` — publish to GHCR (`push: true`)** — **`platforms: linux/amd64`** only (reduces cache/export surface; restore `linux/arm64` when stable), same scoped cache pattern as (1), **`provenance: mode=min`** for private package-index secret-env inputs while keeping GitHub-signed attestations and `cache-to: ... mode=min,ignore-error=true` to reduce export flakes.
3. **`cd.yml` — staging image** — keep **`cache-from` / `cache-to`** with scope `cd-staging-${{ github.ref_name }}` (`mode=min`, `ignore-error=true`), use **`provenance: mode=min`** and **`sbom: true`**, then verify both attestations by exact digest before any deploy step.
4. **`cd.yml` — production image** — same cache policy with scope **`cd-production-${{ github.ref_name }}`**, use **`provenance: mode=min`** and **`sbom: true`**, then verify both attestations by exact digest before any deploy step.
5. **`docker-openapi-smoke.yml` — smoke build** — same pattern as (1): `load: true`, scoped cache (`docker-openapi-smoke-v2-${{ github.ref_name }}`), **`provenance: false`** (attestations incompatible with `load`; see (1)).

Cross-cutting themes: **scoped GHA cache keys** (per ref / job family) replace an older “omit `cache-from` on CD” iteration that avoided `BlobNotFound` but hurt hit rate; **`ignore-error=true` on `cache-to`** remains the export fail-safe everywhere.

## Decision
Aligned with **Context steps (1)–(5)** above (same order as [Evidence Anchors](#evidence-anchors)):

- Keep **`provenance: false`** on `load: true` paths listed in those anchors; for pushed-image lanes in `build.yml` and `cd.yml`, use **`provenance: mode=min`** plus **`sbom: true`** while private package-index inputs flow through BuildKit secret envs.
- Keep **`linux/amd64` only** on all publish/CD image builds; restore multi-arch when cache/provenance is stable.
- Keep **scoped** `cache-from: type=gha` + `cache-to: type=gha,mode=min,ignore-error=true` on each of those steps (scopes differ per job; see anchors).
- Keep **inline comments** in workflows stating the narrowed workaround boundary: `load: true` jobs remain excluded, pushed-image lanes verify OCI-backed provenance/SBOM before deploy.
- Treat this ADR as the temporary seam SoT until **Exit Criteria** are met.

## Rationale
- Restores green CI/CD and reliable image pushes to GHCR.
- Trade-off remains scoped: pushed-image attestations are restored, but `load: true` paths keep temporary constraints.
- Single-arch reduces variables while cache/provenance tooling is unstable.
- Scoped `cache-from` on CD improves cache reuse while `ignore-error=true` on `cache-to` limits export-time flakes.

## Consequences
- Image consumers can verify SLSA provenance for GHCR images produced by pushed-image lanes in `build.yml` and `cd.yml`.
- Arm64 image builds are deferred until we re-enable multi-platform.
- Smoke and other `load: true` CI jobs cannot serve as a provenance pilot without changing architecture (e.g. build+push to a scratch tag, then pull/run).

## Evidence Anchors
- `.github/workflows/build.yml:49-64` local build job: `load: true`,
  scoped `cache-from` / `cache-to`, `provenance: false`.
- `.github/workflows/build.yml:327-345` publish job: `linux/amd64`,
  `push: true`, scoped `cache-from` / `cache-to`,
  `provenance: mode=min`, `sbom: true`.
- `.github/workflows/cd.yml:88-148` staging image: scoped
  `cache-from` / `cache-to`, `provenance: mode=min`, `sbom: true`,
  exact-digest attestation verification before deploy.
- `.github/workflows/cd.yml:343-402` production image: scoped
  `cache-from` / `cache-to`, `provenance: mode=min`, `sbom: true`,
  exact-digest attestation verification before deploy.
- `.github/workflows/docker-openapi-smoke.yml:61-80` smoke build:
  `load: true`, `provenance: false` (attestations incompatible with
  `load`; see Context).

## Exit Criteria / Definition of Done
- [ ] Upstream fix or documented stable approach: buildx and/or GHA cache backend no longer produces "cache entry no longer exists" (or equivalent) when using `cache-from: type=gha` and provenance enabled.
- [x] Remove `provenance: false` and restore pushed-image provenance
  for `build.yml` publish (`push: true`) path (PR #1448).
- [x] Remove `provenance: false` and restore pushed-image provenance
  for `cd.yml` pushed-image paths while keeping scoped cache, `mode=min`,
  and `ignore-error=true`.
- [x] Verify pushed-image provenance and SPDX SBOM attestations by exact digest before deploy.
- [ ] Re-evaluate cache scopes and `mode=min` vs `mode=max` once provenance is re-enabled on GHCR pushes.
- [ ] Optionally restore `platforms: linux/amd64,linux/arm64` when
  cache/provenance is stable.
- [ ] Update this ADR status again when the remaining `load: true` exceptions are fully removed.

## Links
- Workflow: `.github/workflows/build.yml`.
- Workflow: `.github/workflows/cd.yml`.
- PR `#1448` (publish provenance re-enable):
  [GitHub PR `#1448`](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1448)
- Docker CI attestations overview:
  [Docker CI attestations docs](https://docs.docker.com/build/ci/github-actions/attestations/)
- Backlog Ledger: `docs/roadmap/BACKLOG_LEDGER.md` (`#backlog-restore-signed-build-provenance` — restore signed build provenance; DoD and blockers tracked in the ledger).
