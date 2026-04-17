# ADR: Docker build provenance: false workaround (2026-03-01)

## Status
Superseded (workaround removed)

## Context
Docker image push to GHCR was failing with `failed to push ... cache entry no longer exists` when using `cache-from: type=gha` and default provenance. This is a known class of issues with buildx + GHA cache backend where cache blobs can become unavailable during export/push.

To unblock main and stabilize CI, we apply two workarounds in `.github/workflows/build.yml`:
1. **provenance: mode=max** — re-enables SLSA build provenance attestations for published images.
2. **Single-arch (linux/amd64)** in publish step remains to reduce surface for cache/export issues; multi-arch can be restored when cache/provenance stack is stable.

## Decision
- Re-enable provenance in the publish job with `provenance: mode=max` in `docker/build-push-action`.
- Keep single platform `linux/amd64` for the publish step; document intent to restore `linux/arm64` when GHA cache/provenance is stable.
- Inline comments in the workflow document that published images keep provenance attestations enabled.
- This ADR documents the temporary seam and exit criteria.

## Rationale
- Restores supply-chain provenance attestations for GHCR-published images.
- Keeps cache settings (`mode=min`, `ignore-error=true`) and single-arch publish for stability.
- Single-arch still reduces variables while cache/provenance tooling evolves.

## Consequences
- Image consumers can verify SLSA provenance via cosign for images built by this workflow.
- Arm64 image builds are deferred until we re-enable multi-platform.

## Evidence Anchors (file:line)
- `provenance: mode=max` in publish step: `.github/workflows/build.yml` (publish step, ~187–189).
- Platforms comment and single-arch: `.github/workflows/build.yml` (publish step, ~175–176).
- Build job omits `cache-from` to avoid 404: `.github/workflows/build.yml` (build step, ~32–42).

## Exit Criteria / Definition of Done
- [ ] Upstream fix or documented stable approach: buildx and/or GHA cache backend no longer produces "cache entry no longer exists" (or equivalent) when using `cache-from: type=gha` and provenance enabled.
- [x] Remove `provenance: false` and restore default or `provenance: mode=max` in `.github/workflows/build.yml` publish step.
- [ ] Optionally restore `platforms: linux/amd64,linux/arm64` when cache/provenance is stable.
- [x] Update this ADR status to Superseded with a pointer to the removal PR when workaround is removed.

## Links
- Workflow: `.github/workflows/build.yml`.
