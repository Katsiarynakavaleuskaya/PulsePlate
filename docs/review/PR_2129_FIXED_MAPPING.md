# PR #2129 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129

Branch: `codex/propose-fix-for-docker-tmpfs-vulnerability`

## Summary

Harden the existing owner PR without preserving its unsafe durable Docker
volume change. Docker result handoff remains a bounded `tmpfs` volume, while
macOS Oracle-only governance review now requires explicit Apple Container and
fails closed before runtime probing for `auto`, Docker, or native Linux. The
same replacement commit absorbs the bounded source work from PRs #2122, #2131,
and #2132: exact failed-review quarantine admission, exact per-invocation Git
`safe.directory`, and canonical retained-artifact fingerprint comparison.

Public APIs and OpenAPI are unchanged. General candidate, probe, and negative-
control Docker surfaces remain supported.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/1418f71dc1a5.json`

- The owner head was synchronized with fresh `origin/main` by non-rewriting
  merge commit `7c41597d10060a4c52ef559d7a163d9e1a6bf764`.
- The pre-open role order completed as declared:
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer -> dev-operator`.
- Every role returned `PROCEED` with no unresolved finding after the bounded
  implementation and MyPy correction.
- Native Codex Security scanning remained `operator_directed_stop`; no scan
  PASS is claimed and no scan was restarted.
- Local packets, role outputs, premortem notes, and Experiment Runner evidence
  are gitignored control-plane artifacts.

## Implementation Commit

- `b0f3f18078020dfe4e3c656ae3610288098c1122` - restore bounded Docker
  `tmpfs`; enforce explicit Apple Container for macOS Oracle-only review;
  inject one resolved, adjacent per-invocation Git trust boundary; compare
  retained JSON by canonical fingerprint; and admit only exact non-symlink
  failed-review quarantine directories.

## Source PR Replacement Matrix

- PR #2122 (`d564b62530b313ce3ac229563200e582f6cd4a93`) is replaced by the exact
  `.spec_finalize_reviewed.<16-lowercase-hex>.failed` directory contract. The
  token length is derived from `FAILED_REVIEWED_RUN_TOKEN_BYTES`, children are
  captured once, and tests reject near matches, files, and symlinks.
- PR #2131 (`cde62eae3ae043af581b71b9500a30bad184410f`) is replaced by one exact
  `-c safe.directory=<resolved-cwd>` pair per Git invocation. The test proves
  adjacency, uniqueness, resolved-path equality, and absence of wildcard
  trust; missing or non-directory cwd fails before subprocess execution.
- PR #2132 (`1c1575ab2885b6db769ad86ca548c0d0cfea28f0`) is replaced by canonical
  fingerprint comparison for retained and exact prepare artifacts. Tests prove
  `int`/`float` drift and `NaN`/positive-infinity/negative-infinity rejection
  without leaking the rejected value.
- The original PR #2129 durable-volume change is superseded. Docker volume
  creation is the bounded local `tmpfs` form with `size=16m,mode=0700`.

## Premortem Closure

- FIXED in `b0f3f18078020dfe4e3c656ae3610288098c1122`: macOS Oracle review could
  have silently reached `auto` or Docker. The dispatcher now rejects every
  non-Apple backend before probing or result creation and never falls back
  after Apple capability loss.
- FIXED in `b0f3f18078020dfe4e3c656ae3610288098c1122`: Docker handoff could have
  become an unbounded durable volume. Exact argv coverage requires bounded
  `tmpfs` creation and preserves multi-container named-volume handoff.
- FIXED in `b0f3f18078020dfe4e3c656ae3610288098c1122`: quarantine inspection could
  observe two directory snapshots. One captured child tuple now feeds both
  symlink rejection and unexpected-entry validation.
- FIXED in `b0f3f18078020dfe4e3c656ae3610288098c1122`: focused MyPy found an
  `Any` return on the new canonical comparison line. Explicit boolean
  normalization closes the changed-line error; the final intersection is zero.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/pr-2129-consolidation/pr-2129-final-oracle-packet.json`.
- Result:
  `artifacts/orchestration/experiments/results/pr-2129-final-oracle-result.json`.
- Experiment: `exp-2e324e6d35dd`.
- Backend: explicit `apple-container` 1.1.0 with immutable image digest
  `sha256:8b95aa8a94d989ff18af7449fbb0feae6783623a7bf49434f0e16341bd61c483`.
- Result: accepted after one attempt, no retry or fallback; all focused oracles
  passed, `network_budget=0`, `mutated_paths=[]`, shared tree untouched, and
  `promotion_ready=false`.
- The evidence materially shaped commit
  `b0f3f18078020dfe4e3c656ae3610288098c1122`, which carries the canonical
  Experiment Runner co-author trailer.

## Validation

- Scoped preflight and agent consistency: PASS.
- Focused runner/dispatch, patch-builder, specification/fingerprint,
  skeptic-review, subprocess, nosec-policy, and review-pattern suites: PASS.
- `make validate-changed`: PASS.
- Exact diff-selected backend-test hook: PASS.
- `pre-commit run --all-files`: PASS.
- Pre-push MyPy, pip-audit, backend tests, full-repo Bandit, and Docker build:
  PASS.
- `git diff --check`: PASS.
- MyPy errors on changed lines: 0. The narrow direct run reports 47 existing
  errors only on unchanged test lines.

## Discussion Thread Pass

- [x] Source PR replacement evidence published on owner head
  `b0f3f18078020dfe4e3c656ae3610288098c1122`.
- [x] Source review findings mapped below after their timestamps.
- [ ] Mandatory post-open role tail completed on current material head.
- [x] Native Codex Security operator stop recorded without a PASS claim or
  restart.
- Current-head CI, bot dispositions, strict authenticated merge readiness, and
  the mandatory wait window remain live PR-state gates and are not frozen as
  completed here.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b0f3f18078020dfe4e3c656ae3610288098c1122
Evidence: scripts/orchestration/creative_specification_skeptic_review.py ties quarantine length to generation and uses one child snapshot; focused quarantine tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2122#pullrequestreview-4694124577 -> b0f3f18078020dfe4e3c656ae3610288098c1122

Disposition: FIXED
Commit: b0f3f18078020dfe4e3c656ae3610288098c1122
Evidence: tests/test_creative_code_patch_builder.py proves the resolved safe.directory value is unique and directly adjacent to -c.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2131#pullrequestreview-4694153073 -> b0f3f18078020dfe4e3c656ae3610288098c1122
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2131#discussion_r3578866396 -> b0f3f18078020dfe4e3c656ae3610288098c1122

## Merge Readiness

- [ ] Mandatory post-open role tail completed on current head.
- [ ] Current-head CI and diff coverage are terminal and passing.
- [ ] CodeRabbit, Sourcery, and Cubic have no actionable findings.
- [ ] Strict authenticated merge wrapper passes after the review wait window.
