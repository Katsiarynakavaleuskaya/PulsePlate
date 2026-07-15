# PR #2143 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2143

Branch: `codex/fix-accepted-result-inventory-contract-test`

## Summary

Restore current-main CI after PR #2119 made incomplete accepted Experiment
Runner proof correctly unconstructable through the production patch-result
builder. The regression now models that state as an untrusted stale on-disk
sidecar, then proves artifact inventory rejects it and promotion remains
blocked. Production contracts and schemas are unchanged.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/49e2ee88c936.json`

- Pre-open role order completed as declared:
  `agent-coordinator -> bug-hunter -> qa-engineer-agent`.
- Every role returned `PROCEED` with no unresolved finding after the fixture
  correction.
- Codex Security scan was not invoked by operator direction; no scan PASS is
  claimed.

## Implementation Commit

- `4ee8b4f00d5b58f474cbcc3a925981a8806869f9` - replace impossible
  builder-based construction with a forged retained result, preserve
  `invalid_patch_result`, and retain artifact and promotion blockers.

## Premortem Closure

- FIXED in `4ee8b4f00d5b58f474cbcc3a925981a8806869f9`: the hotfix could have
  stopped testing inventory behavior and merely repeated production builder
  validation. The fixture now mutates a valid result only after construction,
  writes it as untrusted retained data, and asserts inventory rejection plus
  promotion blocking.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/main-hotfix-2119-inventory-result.json`
- Experiment: `exp-259bf4a1f7fc`.
- Backend: `apple-container`; immutable image digest and strict isolation
  preflight passed.
- Result: accepted, `mutated_paths=[]`, shared tree untouched, promotion not
  ready.
- The evidence materially shaped commit
  `4ee8b4f00d5b58f474cbcc3a925981a8806869f9`, which carries the canonical
  Experiment Runner co-author trailer.

## Validation

- Focused inventory and incomplete-proof regressions: PASS, 44 tests.
- `make validate-changed`: PASS, 41 tests.
- Exact diff-selected backend-test hook: PASS, 41 tests.
- `pre-commit run --all-files`: PASS.
- `git diff --check`: PASS.
- MyPy errors on changed lines: 0. Existing findings on unchanged lines 70 and
  110 remain outside this test-only hotfix.

## Discussion Thread Pass

- [ ] Discussion-thread pass completed.
- [ ] Fixed in commit mapping completed.
- Post-open review and current-head CI are pending.

## Fixed in Commit Mapping

- No actionable review comments at initial publication.

## Merge Readiness

- [ ] Mandatory post-open role tail completed on current head.
- [ ] Current-head CI and diff coverage are terminal and passing.
- [ ] CodeRabbit, Sourcery, and Cubic have no actionable findings.
- [ ] Strict authenticated merge wrapper passes after the review wait window.
