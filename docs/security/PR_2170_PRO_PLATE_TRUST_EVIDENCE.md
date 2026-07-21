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

Exactly one Codex Security scan session was used:

- session: `2f00c998-c5a9-41d6-954d-e30c7f2fbb40`;
- scan: `880bb67f-2965-4858-b2f0-fa94ff2f6ffe`;
- frozen head: `197e3c3e1e7a39ef8662a02fd4e629c5364cbfa3`;
- scan progress: `5 of 5` completed;
- reportable findings: `0`.

After that frozen scan, correctness actionables were fixed. The exact runtime/test head
before this evidence-only commit is
`17071a32ac963b0a0d1485407bc6a97aaf7375dd`, so it is not the scanned head. No second
scan was started. Therefore this lane has no exact-current-head Codex Security scan and
this evidence makes no ready, green, or mergeable claim. The operator stop remains in
force pending the repository's authorized disposition of the changed material digest.

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
