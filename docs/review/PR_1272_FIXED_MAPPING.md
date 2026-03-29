# PR 1272 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 6adb803f
Evidence: `docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md:14` now uses the clearer term "affected transitive dependencies", and `docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md:26` now explicitly states that the safe versions are enforced via root-level `overrides` in `package.json`.
Reason: The remaining Sourcery suggestion about adding an inline comment above `package.json` `overrides` is not applicable because `package.json` is strict JSON and does not support comments; the rationale is preserved in the canonical security note instead.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1272#pullrequestreview-4026442420 -> 6adb803f

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
Notes: Draft PR `#1272` is the narrow security/dependabot remediation lane for alerts `#76`, `#82`, and `#83`. Scope is intentionally limited to root npm manifest policy plus canonical security evidence: explicit root overrides for `brace-expansion=2.0.3` and `path-to-regexp=8.4.0`, with rationale anchored in `docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md`. The mandatory post-open bug-hunter pass confirmed the lane is sufficiently narrow for a draft PR, identified the root cause as GitHub alerts staying open while fixed transitive versions existed only in the lockfile, and explicitly kept Pygments alerts `#80` and `#81` plus unrelated npm audit findings (`smol-toml`, `yaml`) out of scope.
