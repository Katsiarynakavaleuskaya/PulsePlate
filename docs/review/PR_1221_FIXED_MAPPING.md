# PR 1221 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Stable Evidence Anchors
- Replacement provenance:
  - `286e13bc` — `feat(business): add collateral builders and specs`
  - `fb4d6cb3` — `fix(ci): install root node deps for backend tests`
  - `4dc941cd` — `fix(worker): mark edge proxy as esm`
- Replacement note:
  - this PR replaces stacked child `#1218`, which previously targeted `feat/business-wave-director-contract`

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 958dc2332ff57c23e3709098bbae5ca065c88118
Evidence: `scripts/business_collateral/content_loader.js:46-51`, `scripts/business_collateral/content_loader.js:78-83`, `scripts/business_collateral/content_loader.js:100-116`, `tests/test_business_collateral_builders.py:58-72`, `.github/workflows/ci.yml:370-395`, `.github/workflows/ci.yml:488-513`, `.github/workflows/ci.yml:607-632`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970182968 -> 958dc2332ff57c23e3709098bbae5ca065c88118
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970190909 -> 958dc2332ff57c23e3709098bbae5ca065c88118
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970190912 -> 958dc2332ff57c23e3709098bbae5ca065c88118
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970191913 -> 958dc2332ff57c23e3709098bbae5ca065c88118
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970202318 -> 958dc2332ff57c23e3709098bbae5ca065c88118
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970202319 -> 958dc2332ff57c23e3709098bbae5ca065c88118
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970202323 -> 958dc2332ff57c23e3709098bbae5ca065c88118

Disposition: FIXED
Commit: b9c5295b1a5e824e195e37f6300b8c3c64a28be2
Evidence: `.github/workflows/pr-tests.yml:138-162`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970191916 -> b9c5295b1a5e824e195e37f6300b8c3c64a28be2

Disposition: FIXED
Commit: cf668f97d143dceba413f03d0291a885b79e20f6
Evidence: `scripts/business_collateral/content_loader.js:24-52`, `scripts/business_collateral/content_loader.js:165-169`, `tests/test_business_collateral_builders.py:16-20`, `tests/test_business_collateral_builders.py:35-43`, `tests/test_business_collateral_builders.py:75-95`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970239236 -> cf668f97d143dceba413f03d0291a885b79e20f6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970243122 -> cf668f97d143dceba413f03d0291a885b79e20f6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970247806 -> cf668f97d143dceba413f03d0291a885b79e20f6

Disposition: FIXED
Commit: 9da57793121b40998319247fbf58f852dc0756b5
Evidence: `tests/test_business_collateral_builders.py:46-55`, `tests/test_business_collateral_builders.py:58-72`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970247808 -> 9da57793121b40998319247fbf58f852dc0756b5

Disposition: NOT-A-BUG
Evidence: `package.json:5-15`, `scripts/business_collateral/package.json:1-2`, `worker.js:1-15`
Reason: Root package ESM and collateral CommonJS are intentionally separated by the nearer `scripts/business_collateral/package.json` boundary; on current head the CommonJS usage flagged by review is confined to that subpackage, while the root worker surface remains ESM-compatible.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970182967
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970191919
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970191922
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970191929

Disposition: NOT-A-BUG
Evidence: `scripts/business_collateral/build_b2b_proposal.js:8-67`, `tests/test_business_collateral_builders.py:58-108`
Reason: This thread requests optional JSDoc ergonomics, not a correctness or contract defect; the builder entrypoint is intentionally small, already locally validated, and no JS doc-type gate is enforced for this lane.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#discussion_r2970191926

Disposition: NOT-A-BUG
Evidence: `scripts/business_collateral/content_loader.js:24-116`, `.github/workflows/ci.yml:370-632`, `.github/workflows/pr-tests.yml:138-162`, `tests/test_business_collateral_builders.py:46-95`
Reason: These review-level bot URLs are aggregate review summaries whose actionable findings are already dispositioned by the mapped inline thread URLs above, so no separate code change or additional backlog item exists beyond those underlying thread mappings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#pullrequestreview-3986758431
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#pullrequestreview-3986769148
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#pullrequestreview-3986779718
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#pullrequestreview-3986822271
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1221#pullrequestreview-3986827064

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] `pre-commit run --all-files`
- [x] `make verify`
- Replacement-lane note: `PR_1218_FIXED_MAPPING.md` was intentionally not carried into this lane; all new review dispositions start from `PR_1221_FIXED_MAPPING.md`
