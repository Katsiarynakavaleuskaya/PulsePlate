# PR #2170 PRO Plate Trust Evidence

## Purpose and scope

PR #2170 moves PRO Plate orchestration from the legacy application facade to the
canonical nutrition service while retaining the existing public route contracts and
compatibility aliases. The cutover is limited to Plate ownership, deterministic
dependency boundaries, error hygiene, and regression coverage. It does not add a new
nutrition product behavior or a new endpoint.

This document records evidence for the lane. It is not a policy, exception, gate
override, or merge-readiness claim.

## Access-control invariants

- `POST /api/v1/pro/nutrition/plate` retains its existing PRO-tier guard.
- `POST /api/v1/premium/plate` retains its existing API-key guard and deprecated alias
  semantics.
- Request and response schemas remain shared across the canonical and deprecated
  route families.
- The cutover does not change object ownership, tenant lookup, authorization context,
  or any BOLA boundary.

## Fail-closed runtime behavior

- BMR and TDEE dependency results must be non-empty numeric mappings with finite,
  positive values. The selected `mifflin` TDEE must be present and valid before
  `make_plate` runs.
- Malformed, non-finite, zero, or negative calculation output fails with the stable
  generic Plate `500` envelope; private dependency values are logged server-side and
  are not returned to clients.
- Enriched micronutrient values must be numeric, finite, and within the canonical
  range. Boolean measurements are rejected before numeric coercion.
- Missing or `None` provider micronutrient evidence is omitted rather than fabricated
  as `0.0`; an explicit numeric zero remains valid evidence.
- Canonical target safety failures remain fail-closed. Bounded fallback kcal and macro
  output use one coherent heuristic when an out-of-range target override is rejected.
- Canonical and deprecated routes have deterministic parity tests for success,
  fallback bounds, safety failures, malformed dependencies, and non-leaking errors.

## Focused and local validation

The implementation and review remediations were exercised with deterministic focused
Plate suites, exact review-affected tests, and the repository-resolved Python runtime.
Recorded successful evidence includes:

- focused Plate suite: `165 passed`;
- exact review-affected suite: `109 passed`;
- canonical Plate service suite after the final calculation guard: `74 passed`;
- zero, negative, malformed, and non-finite calculation regression matrix: `9 passed`;
- `make validate-changed`: passed on the final runtime/test head;
- `pre-commit run --all-files`: passed on the final runtime/test head;
- `git diff --check`: passed, with a clean worktree after each commit.

Primary runtime and regression anchors include
`app/services/pro_nutrition_plate.py:578` and
`tests/edges/test_pro_nutrition_plate_service.py:146`.

The machine-heavy local `make verify` target was not run, in accordance with repository
policy.

## Strict Apple Container oracle

The PulsePlate Experiment Runner executed the bounded oracle in a strict Apple
Container environment:

- oracle result: `2/2` passed;
- retries: `0`;
- `network_budget=0`;
- pinned image digest:
  `sha256:cefe9cfa20a89e2b24b4041c50d02f9bc202664d44e81470f962d5b72f063e13`.

The oracle contributed to implementation decisions and is attributed through the
required commit co-author trailer. It did not mutate governance contracts or grant
merge authority.

## Codex Security material identity and stop condition

The single explicitly authorized exceptional Codex Security scan completed for the
frozen material that included all findings known before the final review cycle:

- scan: `14e6e86f-18bc-4314-97b9-6683eb04d36f`;
- frozen head: `4aafde870f620640ec519a7803319e7706d84183`;
- snapshot digest:
  `codex-security-snapshot/v1:sha256:cc4b1abf959a098431c35554793a901985f3fc7a820b2e9348f84a35cc94bc43`;
- scan progress: `7 of 7` completed;
- reportable findings: `0`.

Earlier scans, including `605022ae-6aa8-47f2-ab14-54cae9622912` at
`cb7a0cd6614ca1ccd07b9ced13914c7e98b43d1b`, are historical evidence only and do not
authorize later material. The final review cycle subsequently identified a bounded
Plate safety-warning defect that requires a runtime and test fix after the frozen head.
That material change invalidates the exact-head binding above and restores the
fail-closed operator stop. No retry or additional scan is permitted under the approved
lane rules, so this document makes no ready, green, or mergeable claim for the changed
head.

## Rollback

Rollback is to revert the Plate ownership and its correctness-remediation commits as a
unit. The existing route paths, guards, request/response schemas, and compatibility
aliases provide a bounded rollback surface; no data migration or destructive state
transition is involved.

## Governance non-change

PR #2170 does not change orchestration contracts, bot contracts, review contracts,
security-scan contracts, CI workflows, merge gates, or operator-approval semantics.
This evidence file documents observed execution and the unresolved material-identity
stop; it does not modify or work around those controls.
