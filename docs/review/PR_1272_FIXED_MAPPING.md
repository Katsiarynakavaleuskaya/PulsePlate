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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1272#discussion_r3005802120 -> 6adb803f

Disposition: FIXED
Commit: ef976140
Evidence: `docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md:5` still records the explicit policy exception for this grouped npm remediation batch, but the latest latest-head CI failure showed the blanket frontend `brace-expansion=2.0.3` pin was too broad for the Node 22 design-token tool chain. `frontend/package.json:86` now keeps only the frontend-safe `path-to-regexp=8.4.0` override, `frontend/package-lock.json:467` and `frontend/package-lock.json:10333` now restore compatible patched `brace-expansion=5.0.5` for dev-only `minimatch` consumers, and `frontend/package-lock.json:8640` still pins `path-to-regexp=8.4.0`. Validation was re-run with `make tokens-check`, `cd frontend && npm audit --package-lock-only --json`, `pre-commit run --all-files`, and `make verify`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1272#discussion_r3005804714 -> ef976140
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1272#discussion_r3005804715 -> ef976140
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1272#pullrequestreview-4026444931 -> ef976140

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
Notes: PR `#1272` remains the narrow security/dependabot remediation lane for alerts `#76`, `#82`, and `#83`. Scope is limited to npm manifest policy plus canonical security evidence across the two repo-managed npm surfaces that install independently in CI: root and `frontend/`. The mandatory post-open bug-hunter pass confirmed the original root-only lockfile state was insufficient for full npm-surface remediation, but the follow-up latest-head CI investigation also showed that a blanket frontend `brace-expansion` override was invalid for the design-token tool chain. The final lane therefore keeps the root `brace-expansion=2.0.3` pin, keeps the frontend `path-to-regexp=8.4.0` pin, and narrows the frontend lockfile to a patched/tool-compatible `brace-expansion` resolution while still keeping Pygments alerts `#80` and `#81` plus unrelated npm audit findings (`smol-toml`, `yaml`) out of scope.
