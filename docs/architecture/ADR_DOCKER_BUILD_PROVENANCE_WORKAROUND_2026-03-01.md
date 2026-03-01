# ADR: Docker build provenance: false workaround (2026-03-01)

## Status
Accepted (temporary seam)

## Context
Docker image push to GHCR was failing with `failed to push ... cache entry no longer exists` when using `cache-from: type=gha` and default provenance. This is a known class of issues with buildx + GHA cache backend where cache blobs can become unavailable during export/push.

To unblock main and stabilize CI, we apply two workarounds in `.github/workflows/build.yml`:
1. **provenance: false** — disables SLSA build provenance attestations so buildx does not generate attestations that can interact badly with the cache export path.
2. **Single-arch (linux/amd64)** in publish step — reduces surface for cache/export issues; multi-arch can be restored when cache/provenance stack is stable.

## Decision
- Set `provenance: false` in the publish job's `docker/build-push-action` step.
- Keep single platform `linux/amd64` for the publish step; document intent to restore `linux/arm64` when GHA cache/provenance is stable.
- Inline comments in the workflow document the trade-off (SLSA attestations disabled; `cosign verify-attestation` will fail for consumers) and re-enable intent.
- This ADR documents the temporary seam and exit criteria.

## Rationale
- Restores green CI and reliable image pushes to GHCR.
- Trade-off is explicit: we lose attestations until upstream/buildx or GHA cache behavior is fixed.
- Single-arch reduces variables while cache/provenance tooling is unstable.

## Consequences
- Image consumers cannot verify SLSA provenance via cosign for images built by this workflow until the workaround is removed.
- Arm64 image builds are deferred until we re-enable multi-platform.

## Evidence Anchors (file:line)
- `provenance: false` and comment: `.github/workflows/build.yml` (publish step, ~179–183).
- Platforms comment and single-arch: `.github/workflows/build.yml` (publish step, ~175–176).
- Build job omits `cache-from` to avoid 404: `.github/workflows/build.yml` (build step, ~32–42).

## Exit Criteria / Definition of Done
- [ ] Upstream fix or documented stable approach: buildx and/or GHA cache backend no longer produces "cache entry no longer exists" (or equivalent) when using `cache-from: type=gha` and provenance enabled.
- [ ] Remove `provenance: false` and restore default or `provenance: mode=max` in `.github/workflows/build.yml` publish step.
- [ ] Optionally restore `platforms: linux/amd64,linux/arm64` when cache/provenance is stable.
- [ ] Update this ADR status to Superseded with a pointer to the removal PR when workaround is removed.

## Links
- Workflow: `.github/workflows/build.yml`.
