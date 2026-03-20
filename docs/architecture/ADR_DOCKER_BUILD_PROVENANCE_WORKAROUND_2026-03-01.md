# ADR: Docker build provenance: false workaround (2026-03-01)

## Status
Accepted (temporary seam)

## Context
Docker image push to GHCR was failing with `failed to push ... cache entry no longer exists` when using `cache-from: type=gha` and default provenance. This is a known class of issues with buildx + GHA cache backend where cache blobs can become unavailable during export/push.

To unblock main and stabilize CI/CD, we keep the existing workaround profile in
`.github/workflows/build.yml` and extend the same provenance/single-arch policy
to `.github/workflows/cd.yml`:
1. **provenance: false** — disables SLSA build provenance attestations so buildx does not generate attestations that can interact badly with the cache export path.
2. **Single-arch (linux/amd64)** in publish step — reduces surface for cache/export issues; multi-arch can be restored when cache/provenance stack is stable.
3. **No `cache-from: type=gha` on CD image builds** — avoids `BlobNotFound` /
   missing cache entry failures when the GitHub Actions cache backend evicts or
   cannot resolve a referenced blob during multi-stage COPY.

## Decision
- Keep `provenance: false` in the existing `build.yml` publish step and set it
  in the corresponding `cd.yml` image-build steps.
- Keep single platform `linux/amd64` for the affected publish/deploy/CD steps;
  document intent to restore `linux/arm64` when GHA cache/provenance is
  stable.
- Keep `build.yml` publish on its current bounded cache profile, and omit
  `cache-from: type=gha` for the affected `cd.yml` image-build steps while
  using `cache-to: type=gha,mode=min,ignore-error=true` as the fail-safe export
  profile.
- Inline comments in the workflow document the trade-off (SLSA attestations disabled; `cosign verify-attestation` will fail for consumers) and re-enable intent.
- This ADR documents the temporary seam and exit criteria.

## Rationale
- Restores green CI/CD and reliable image pushes to GHCR.
- Trade-off is explicit: we lose attestations until upstream/buildx or GHA cache behavior is fixed.
- Single-arch reduces variables while cache/provenance tooling is unstable.
- Removing `cache-from` on CD image builds favors reliability over cache hit
  rate for the release path.

## Consequences
- Image consumers cannot verify SLSA provenance via cosign for images built by this workflow until the workaround is removed.
- Arm64 image builds are deferred until we re-enable multi-platform.

## Evidence Anchors (file:line)
- `.github/workflows/build.yml:42` omits `cache-from` in the local build job to
  avoid `BlobNotFound`.
- `.github/workflows/build.yml:181`-`.github/workflows/build.yml:193` pins
  `linux/amd64`, uses `cache-to: ...mode=min,ignore-error=true`, and sets
  `provenance: false` for publish.
- `.github/workflows/cd.yml:73`, `.github/workflows/cd.yml:80`,
  `.github/workflows/cd.yml:84` align the staging CD image build with the same
  cache/provenance workaround profile.
- `.github/workflows/cd.yml:260`, `.github/workflows/cd.yml:268`,
  `.github/workflows/cd.yml:272` align the production CD image build with the
  same cache/provenance workaround profile.

## Exit Criteria / Definition of Done
- [ ] Upstream fix or documented stable approach: buildx and/or GHA cache backend no longer produces "cache entry no longer exists" (or equivalent) when using `cache-from: type=gha` and provenance enabled.
- [ ] Remove `provenance: false` and restore default or `provenance: mode=max`
  in the affected publish/deploy workflow steps.
- [ ] Re-evaluate whether `cache-from: type=gha` can be safely restored on the
  affected `cd.yml` image-build steps.
- [ ] Optionally restore `platforms: linux/amd64,linux/arm64` when
  cache/provenance is stable.
- [ ] Update this ADR status to Superseded with a pointer to the removal PR when workaround is removed.

## Links
- Workflow: `.github/workflows/build.yml`.
- Workflow: `.github/workflows/cd.yml`.
