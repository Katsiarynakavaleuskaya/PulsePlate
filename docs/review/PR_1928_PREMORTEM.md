# PR 1928 Premortem Risk Review

Target mode: `pr-premortem`

Plan: finish PR #1928 by hardening design bridge coverage evidence-anchor
validation against repo-local path traversal, absolute path bypasses, and
Sourcery review gaps, then complete PulsePlate post-open governance without
running full local `make verify`.

Failure frame: it is 48 hours from now, this security hotfix made the PR lane
worse, and we are looking backward to understand why.

## Summary

This PR narrows evidence-anchor validation to a single normalized repo-relative
path before allowed-root and file-existence checks. The highest-risk failure
would be a false-green validator that still accepted traversal or absolute
repo-local paths while review governance recorded the issue as fixed.

## Failure Modes

### PM-1928-001: Path normalization drift

Failure story: the validator rejects `docs/../app/main.py` in one check but
recomputes file existence from the raw anchor. A future path shape with line
suffixes or repeated `..` segments slips through because root checks and
existence checks are not using the same normalized relative path.

Underlying assumption: each helper normalizes paths in exactly the same way.

Early warning signs:

- Sourcery or focused tests find inconsistent behavior between root validation
  and file existence validation.
- A path with `..` or `:line` behaves differently depending on whether the file
  exists.

Containment action: keep `_validate_record(...)` responsible for computing one
normalized relative path and pass that value into both helper checks.

Disposition: FIXED

Evidence: `scripts/design/design_bridge_coverage_inventory.py` computes
`relative_path = _repo_evidence_relative_path(anchor, repo_root)` once per
evidence anchor and routes allowed-root and file-existence checks through that
value.

### PM-1928-002: Negative coverage misses valid and invalid edge pairs

Failure story: tests cover only one traversal shape, so a later refactor
appears green while accepting leading `..`, repeated traversal, line suffixes,
absolute repo-local paths, or same-root collapse cases.

Underlying assumption: the original traversal regression represents the full
attack surface.

Early warning signs:

- Review asks for the same traversal classes again.
- A valid docs anchor with harmless `foo/../bar.md` is rejected while invalid
  escape paths remain accepted.

Containment action: add deterministic parameterized tests for traversal classes
and a separate absolute-path regression.

Disposition: FIXED

Evidence: `tests/test_design_bridge_coverage_inventory.py` covers leading
traversal, repeated traversal, line suffix traversal, same-root normalization,
and absolute repo-local evidence anchors.

### PM-1928-003: Governance false readiness

Failure story: the code fix lands but the lane still fails because review
threads are resolved before fixed mapping, PR body Phase2 sections are missing,
or local validation claims exceed the operator-approved narrow gate.

Underlying assumption: a small security diff does not need the full post-open
governance path.

Early warning signs:

- `PR Body Phase2 gates` or `Merge readiness gate` fails on missing
  `docs/review/PR_1928_FIXED_MAPPING.md`.
- The PR body claims full local readiness despite the explicit operator
  instruction not to run `make verify`.

Containment action: update fixed mapping and PR-body mirror only after the
fixing commit exists, record the machine-heavy `make verify` deferral, and
keep readiness claims tied to focused gates plus current-head CI.

Disposition: FIXED

Evidence: this premortem, the Experiment Runner oracle-only result, Codex
Security scan, post-open role passes, `make validate-changed`, and
`pre-commit run --all-files` are recorded in the fixed mapping and PR body
mirror before merge-readiness checks.

## Most Likely Failure

The most likely failure was PM-1928-003: governance false readiness. The prior
PR head already had code intent but failed Phase2 body and merge-readiness
because the fixed-mapping artifact was absent.

## Most Dangerous Failure

The most dangerous failure was PM-1928-001: path normalization drift. It would
turn a security hardening PR into a false-green validator and leave design
evidence inventory consumers trusting anchors outside the intended root family.

## Hidden Assumption

The hidden assumption was that checking allowed roots and checking file
existence can safely parse the evidence anchor separately.

## Revised Plan

- Use one normalized relative path per evidence anchor for every downstream
  validation decision.
- Expand focused tests to cover invalid traversal, absolute repo-local bypass,
  and valid same-root normalization.
- Record narrow-gate validation explicitly and avoid full `make verify` claims.
- Map Sourcery actionables only to a post-comment fixing commit.

## Pre-Merge Checklist

- Focused inventory test file passes.
- Inventory validator accepts the canonical contract file.
- `make validate-changed` passes.
- `pre-commit run --all-files` passes.
- Codex Security diff scan reports no findings.
- Sourcery actionable review threads are mapped and resolved only after the
  fixing commit and fixed-mapping artifact exist.
- Strict merge-readiness checks pass against current-head PR state.

## Decision

`proceed with changes`

All premortem findings are closed by the current code/test/governance plan
before fixed mapping and merge-readiness checks.
