# PR 1304 — Fixed in Commit Mapping

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: f66c1679
Evidence: `legacy_app.py:1541`, `frontend/src/pages/Profile.tsx:5`, `frontend/src/pages/Profile.tsx:120`, `frontend/src/pages/__tests__/Profile.test.tsx:47`, `tests/test_app_endpoints_1383_1401.py:168`
Reason: Initial narrow legal-policy implementation aligns the legacy `/terms` publication path to the canonical typed helper, adds canonical web legal links to `/privacy` and `/terms`, and adds targeted backend/frontend regressions for those release-safety contracts.

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- [ ] Mandatory post-open bug-hunter pass completed
Notes: PR `#1304` must stay narrowly scoped to legal publication paths, web/iOS client-link alignment, and runtime source-of-truth normalization for `/terms`. It must not widen into broader compliance control-plane, App Store/provider modernization, or new public legal URL work.
