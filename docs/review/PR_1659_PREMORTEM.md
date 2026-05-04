# PR 1659 Pre-mortem -- Canonical-Fail Invariance Fixtures

## Summary

This pre-mortem assumes the PR failed after merge and records the highest-risk
failure modes for canonical-fail negative-control fixture coverage.

Frame: It is 6 months from now. This PR failed. We are looking backward to
understand why.

## Failure Mode 1 -- Fixtures become ornamental coverage theater

Risk: One canonical-fail group per fixture set gives false confidence about
negative-control completeness while the actual failure surface grows.

Underlying assumption: One canonical-fail group is representative of the failure
surface.

Early warning signs:
- A new claim type is added but no canonical-fail fixture row is added.
- The team cites `invariance_score: 1.0` as evidence of negative-control
  robustness.

Mitigation: Docs already state this limitation. When expanding claim types, the
eval protocol should require proportional fixture expansion tracked in the
backlog.

## Failure Mode 2 -- Score/threshold drift between fixtures and live logic

Risk: Offline fixture `decision` values drift from live threshold logic. The
fixture says "fail" but the live system would say "pass" for the same scores.

Underlying assumption: Offline fixture `decision` values will remain aligned
with live threshold logic.

Early warning signs:
- A RAG threshold PR lands without updating fixture `score`/`decision` alignment.
- `PULSEPLATE_RAG_RELEASE_GATES.md` thresholds change but fixture rows keep
  old scores.

Mitigation: Sidecar threshold test already tests threshold logic separately.
A future "threshold-fixture alignment" test could verify score-to-decision
mapping. This is deferred work.

## Failure Mode 3 -- Canonical-fail score=0.0 masks mutation blind spot

Risk: Judgment canonical-fail group has `score: 0.0`. If mutation rows are added,
the existing mutation test (`m["score"] <= canonical_score`) passes trivially.

Underlying assumption: Mutation rows will only be added to passing groups where
score drop is meaningful.

Mitigation: No mutation rows in canonical-fail groups by design. If added in
the future, the PR should test meaningful behavior change, not just `score <= 0.0`.

## Failure Mode 4 -- Nondeterministic report output

Risk: unstable item ordering or slice breakdown differs across runs.

Mitigation: deterministic report tests remain active for both fixture sets.
Two-run diff confirmed identical output for both judgment and RAG reports.

## Failure Mode 5 -- Scope creep into advanced eval science

Risk: PR expands into hybrid adjudication, IRT, tool-use reliability,
semantic cache, or retriever rewrite.

Mitigation: allowed-files check confirms only data/evals, tests/evals, and docs
are touched. No runtime files modified.

## Failure Mode 6 -- Malformed fixture with decision=fail but passed=True

Risk: A fixture row could have `decision: "fail"` but `passed: true`, silently
invalidating negative-control semantics.

Mitigation: Fixed in `9e790f466` per Cubic/CodeRabbit review. Tests now assert
`passed is False` for both the canonical row and the `has_canonical_fail_group`
test.

## Synthesis

### Most likely failure

Fixture coverage stays at one canonical-fail group per dataset indefinitely,
creating a false sense of negative-control completeness.

### Most dangerous failure

Score/threshold drift between offline fixtures and live release-gate logic.

### Hidden assumption

That `invariance_score: 1.0` looks like strong negative-control evidence but
only reflects curated fixture agreement.

### Decision

`proceed` -- Plan is sound. The single actionable finding from bot reviews has
been fixed. Remaining risks are addressed by existing docs and deferred backlog
items.

## Required Evidence Before Merge

- `pytest -q tests/evals/` (137 passed)
- `pytest -q tests/test_judgment_eval.py` (passed)
- `pytest -q tests/evals/test_rag_release_gate_validity_sidecar.py` (passed)
- `pytest -q tests/test_rag_release_gates_runner.py` (passed)
- repeated validity reports are deterministic (diff clean)
- `make test-fast` (144 passed)
- `make lint` (clean)
- pre-push hooks all passed
- Bot review comments addressed: `9e790f466` (passed=False assertions)
