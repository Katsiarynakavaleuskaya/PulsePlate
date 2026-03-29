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

Disposition: FIXED
Commit: e3473f24
Evidence: `docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md:5` now records the explicit policy exception for this grouped npm remediation batch, `frontend/package.json:86` now adds matching frontend `overrides` for `brace-expansion=2.0.3` and `path-to-regexp=8.4.0`, and `frontend/package-lock.json:4979` plus `frontend/package-lock.json:8616` now resolve the frontend lockfile to the fixed versions. Validation was re-run with `cd frontend && npm install --package-lock-only` and `cd frontend && npm audit --package-lock-only --omit=dev --json`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1272#discussion_r3005804714 -> e3473f24
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1272#discussion_r3005804715 -> e3473f24
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1272#pullrequestreview-4026444931 -> e3473f24

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
Notes: PR `#1272` remains the narrow security/dependabot remediation lane for alerts `#76`, `#82`, and `#83`. Scope is limited to npm manifest policy plus canonical security evidence across the two repo-managed npm surfaces that install independently in CI: root and `frontend/`. The mandatory post-open bug-hunter pass confirmed the original root-only lockfile state was insufficient for full npm-surface remediation, so the lane was widened only to matching frontend overrides/lockfile regeneration while still keeping Pygments alerts `#80` and `#81` plus unrelated npm audit findings (`smol-toml`, `yaml`) out of scope.
