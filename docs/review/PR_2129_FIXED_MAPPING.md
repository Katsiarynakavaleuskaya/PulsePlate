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
  merge commits `7c41597d10060a4c52ef559d7a163d9e1a6bf764` and
  `42c9853ccc4572b753f8cab94b82fde74484197a`.
- The pre-open role order completed as declared:
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer -> dev-operator`.
- Every role returned `PROCEED` with no unresolved finding after the bounded
  implementation and MyPy correction.
- After the dispatcher local-config clamp fix, the final post-open role tail
  reran on material head `af2aed04166b2f3e1c1adf5b90903675f30c2f2d`
  in the coordinator-approved required order:
  `qa-engineer-agent -> bug-hunter -> security-auditor`; QA and bug-hunter
  returned `PROCEED`, security-auditor returned `PASS`, and all three reported
  no finding.
- Native Codex Security scanning remained `operator_directed_stop`; no scan
  PASS is claimed and no scan was restarted.
- Local packets, role outputs, premortem notes, and Experiment Runner evidence
  are gitignored control-plane artifacts.

## Implementation Commit

- `b0f3f18078020dfe4e3c656ae3610288098c1122` - restore bounded Docker
  `tmpfs`; enforce explicit Apple Container for macOS Oracle-only review;
  inject one resolved, adjacent trust boundary into every Experiment Runner
  and dispatcher Git invocation; compare
  retained JSON by canonical fingerprint; and admit only exact non-symlink
  failed-review quarantine directories.
- `cdfc7d92d40ddf4ef001d5d6b176a500697e9601` - snapshot quarantine child
  metadata once and fail closed on metadata-read errors.
- `7e464ad929db9fd1a46f3529d5abab6b8271e79e` - replace newly added untyped
  macOS dispatch lambdas with fully annotated named stubs.
- `7767faf06e8ebfdb951d8e8e2a749c31af60bb3b` - apply the exact resolved
  `safe.directory` trust boundary and sanitized Git environment to the active
  dispatcher snapshot path.
- `bafa16bbb4d9fb6c48422027a2ef8d4eb8a3d1dd` - clamp checkout-local Git
  execution config in the dispatcher and disable external/textconv diff
  processing while retaining binary snapshot fidelity.
- `af2aed04166b2f3e1c1adf5b90903675f30c2f2d` - bind governed Git commands
  to the resolved work tree, clone without materializing a checkout, reject
  checkout-local `core.worktree` redirects, and replace configuration-sensitive
  casts with a fail-closed typed result boundary.

## Source PR Replacement Matrix

- PR #2122 (`d564b62530b313ce3ac229563200e582f6cd4a93`) is replaced by the exact
  `.spec_finalize_reviewed.<16-lowercase-hex>.failed` directory contract. The
  token length is derived from `FAILED_REVIEWED_RUN_TOKEN_BYTES`, children are
  captured once, and tests reject near matches, files, and symlinks.
- PR #2131 (`cde62eae3ae043af581b71b9500a30bad184410f`) is replaced by one exact
  `-c safe.directory=<resolved-cwd>` pair in every
  `experiment_runner._run_git` and `experiment_runner_dispatch._git`
  invocation. Tests prove adjacency, uniqueness, resolved-path equality,
  sanitized Git config, and absence of wildcard trust; missing or
  non-directory cwd fails before subprocess execution.
- PR #2132 (`1c1575ab2885b6db769ad86ca548c0d0cfea28f0`) is replaced by canonical
  fingerprint comparison for retained and exact prepare artifacts. Tests prove
  `int`/`float` drift and `NaN`/positive-infinity/negative-infinity rejection
  without leaking the rejected value.
- PR #2132 had no actionable source-review finding: Sourcery reported only a
  capacity/rate-limit notice, so no source-review URL requires FIXED mapping.
- The original PR #2129 durable-volume change is superseded. Docker volume
  creation is the bounded local `tmpfs` form with `size=2m,mode=0700`.

## Premortem Closure

- FIXED in `b0f3f18078020dfe4e3c656ae3610288098c1122`: macOS Oracle review could
  have silently reached `auto` or Docker. The dispatcher now rejects every
  non-Apple backend before probing or result creation and never falls back
  after Apple capability loss.
- FIXED in `b0f3f18078020dfe4e3c656ae3610288098c1122`: Docker handoff could have
  become an unbounded durable volume. Exact argv coverage requires bounded
  `tmpfs` creation and preserves multi-container named-volume handoff.
- FIXED in `cdfc7d92d40ddf4ef001d5d6b176a500697e9601`: quarantine inspection could
  observe multiple metadata states. One `stat(follow_symlinks=False)` snapshot
  per child now feeds symlink rejection and unexpected-entry validation, and
  metadata-read failure is terminal.
- FIXED in `b0f3f18078020dfe4e3c656ae3610288098c1122`: focused MyPy found an
  `Any` return on the new canonical comparison line. Explicit boolean
  normalization closes the changed-line error; the final intersection is zero.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/pr-2129-consolidation/pr-2129-final-oracle-packet.json`.
Artifact: `artifacts/orchestration/experiments/results/pr-2129-final-oracle-result.json`
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
- Final dispatcher trust bundle: focused dispatcher/patch-builder tests,
  external-diff and redirected-worktree non-execution, snapshot regressions,
  invalid-cwd fail-before-subprocess coverage, Ruff, and both normal and
  pre-push `--follow-imports=skip` MyPy with zero diagnostics: PASS.
- `make validate-changed`: PASS.
- Exact diff-selected backend-test hook: PASS.
- `pre-commit run --all-files`: PASS.
- Pre-push MyPy, pip-audit, backend tests, full-repo Bandit, and Docker build:
  PASS.
- `git diff --check`: PASS.
- MyPy errors on changed lines: 0; the final bounded direct run reports no
  diagnostics in either changed source file.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Source PR replacement evidence published on owner head.
- [x] Source review findings mapped below after their timestamps.
- [x] Mandatory post-open role tail completed on current material head.
- [x] Native Codex Security `operator_directed_stop` recorded without a PASS
  claim or restart.
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

Disposition: FIXED
Commit: d2443a22cf10c0f59ec344e8ec9e077490037009
Evidence: The `Discussion Thread Pass` section contains both exact parser-required checkboxes; the local Phase2 validator passes.
Reason: The canonical artifact now records completed discussion and mapping work without marking the still-pending CI and merge gates complete.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592636352 -> d2443a22cf10c0f59ec344e8ec9e077490037009
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592848184 -> d2443a22cf10c0f59ec344e8ec9e077490037009
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592870391 -> d2443a22cf10c0f59ec344e8ec9e077490037009

Disposition: FIXED
Commit: d2443a22cf10c0f59ec344e8ec9e077490037009
Evidence: The `Experiment Runner Evidence` section uses the canonical one-line `Artifact:` result reference accepted by the Experiment Runner evidence parser.
Reason: The prior multiline `Result:` label was valid prose but not parser-valid Phase2 evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592636357 -> d2443a22cf10c0f59ec344e8ec9e077490037009
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592870393 -> d2443a22cf10c0f59ec344e8ec9e077490037009

Disposition: FIXED
Commit: d2443a22cf10c0f59ec344e8ec9e077490037009
Evidence: The `Source PR Replacement Matrix` section records the #2132 replacement behavior and explicitly states that its source review produced no actionable finding requiring a source-review mapping URL.
Reason: Replacement evidence and the absence of an actionable source review are now explicit and auditable.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592848181 -> d2443a22cf10c0f59ec344e8ec9e077490037009

Disposition: FIXED
Commit: d2443a22cf10c0f59ec344e8ec9e077490037009
Evidence: The `Source PR Replacement Matrix` section records the implemented bounded Docker tmpfs contract as `size=2m,mode=0700`.
Reason: The canonical evidence now matches `RESULT_VOLUME_SIZE = "2M"` and the exact Docker argv.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592870388 -> d2443a22cf10c0f59ec344e8ec9e077490037009

Disposition: FIXED
Commit: 7e464ad929db9fd1a46f3529d5abab6b8271e79e
Evidence: `tests/test_experiment_runner_dispatch.py` replaces every newly added lambda in the three macOS Oracle dispatch tests with fully annotated named local stubs; focused tests, Ruff, and changed-line MyPy pass with zero in-diff errors.
Reason: The valid CodeRabbit typing finding was fixed in a real post-comment material commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592848186 -> 7e464ad929db9fd1a46f3529d5abab6b8271e79e

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor b0f3f18078020dfe4e3c656ae3610288098c1122 7e464ad929db9fd1a46f3529d5abab6b8271e79e` exits 0, and GitHub lists `b0f3f18078020dfe4e3c656ae3610288098c1122` in the complete live PR commit graph.
Reason: All three reviews compared the real FIXED proof against unavailable synthetic reviewer-execution refs (`7a4b9d5d...`, `de0c399f...`, and `2f7f724b...`) rather than the real GitHub PR head. The mapped implementation commit is reachable from the live owner head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592636349
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3592870385
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3593163624

Disposition: NOT-A-BUG
Evidence: Every actionable inline finding from these summary reviews is individually dispositioned above with post-comment commit proof; Sourcery reported no actionable finding.
Reason: The review objects aggregate their inline threads or an explicit no-finding result and introduce no additional independent defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#pullrequestreview-4694139891
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#pullrequestreview-4710447514
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#pullrequestreview-4710682775
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#pullrequestreview-4710715767
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#pullrequestreview-4711111608

Disposition: FIXED
Commit: 7767faf06e8ebfdb951d8e8e2a749c31af60bb3b
Evidence: `scripts/orchestration/experiment_runner_dispatch.py` resolves and validates each dispatcher Git cwd before subprocess execution, adds one adjacent exact `-c safe.directory=<resolved-cwd>` entry, and disables global/system Git config. `tests/test_experiment_runner_dispatch.py::test_dispatch_git_uses_one_resolved_per_invocation_safe_directory` and `::test_dispatch_git_rejects_invalid_cwd_before_subprocess` pass together with both snapshot regressions, Ruff, and MyPy with zero diagnostics.
Reason: The pre-existing dispatcher Git wrapper is in the active Oracle snapshot execution path, so the valid finding was fixed in this PR rather than narrowed out of the replacement claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3593311728 -> 7767faf06e8ebfdb951d8e8e2a749c31af60bb3b

Disposition: NOT-A-BUG
Evidence: GitHub lists `b0f3f18078020dfe4e3c656ae3610288098c1122`, `7e464ad929db9fd1a46f3529d5abab6b8271e79e`, and `d2443a22cf10c0f59ec344e8ec9e077490037009` in the live PR commit graph; each is an ancestor of the owner head. The cited `6afe4b4b...` reviewer-execution ref is not a repository commit.
Reason: The finding again compared real FIXED proofs against an unavailable synthetic ref instead of the real GitHub PR head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3593311721

Disposition: NOT-A-BUG
Evidence: `git show -s --format=%B b0f3f18078020dfe4e3c656ae3610288098c1122` contains the exact `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer, and the artifact correctly attributes the accepted Oracle evidence to that material commit.
Reason: The synthetic `6afe4b4b...` reviewer-execution ref is not the attributed implementation commit and cannot replace its real Git identity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3593311724

Disposition: NOT-A-BUG
Evidence: The three inline findings from this Codex review are individually dispositioned above: one valid dispatcher trust defect is fixed in `7767faf06e8ebfdb951d8e8e2a749c31af60bb3b`, and both synthetic-ref findings have live Git evidence.
Reason: The review object introduces no independent finding beyond its three inline threads.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#pullrequestreview-4711276017

Disposition: FIXED
Commit: bafa16bbb4d9fb6c48422027a2ef8d4eb8a3d1dd
Evidence: `scripts/orchestration/experiment_runner_dispatch.py` reuses the governed checkout-local Git clamps and invokes snapshot diff with `--no-ext-diff --no-textconv --binary`; `tests/test_experiment_runner_dispatch.py::test_snapshot_ignores_checkout_local_external_diff` proves a configured helper is not executed while the tracked change is retained. Focused tests, Ruff, MyPy, `make validate-changed`, the exact backend hook, pre-commit, and pre-push gates pass.
Reason: The active host snapshot path now fails closed against checkout-local external diff execution without weakening binary patch capture.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3593666963 -> bafa16bbb4d9fb6c48422027a2ef8d4eb8a3d1dd

Disposition: NOT-A-BUG
Evidence: GitHub identifies the reviewed commit as real owner head `d849907345b59ae2ed96119b9a52c6ca6d2a0502`, where `b0f3f18078020dfe4e3c656ae3610288098c1122`, `d2443a22cf10c0f59ec344e8ec9e077490037009`, `7e464ad929db9fd1a46f3529d5abab6b8271e79e`, and `7767faf06e8ebfdb951d8e8e2a749c31af60bb3b` are reachable. The cited `5d426da1...` execution ref is not the review object's `commit_id` or the live PR head.
Reason: The finding applies ancestry checks to an unavailable synthetic execution ref instead of the trusted GitHub review commit and complete live PR graph.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3593666950

Disposition: NOT-A-BUG
Evidence: `git show -s --format=%B b0f3f18078020dfe4e3c656ae3610288098c1122` contains the exact `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer, and that reachable material commit is the one to which the accepted Oracle evidence is attributed. GitHub reports the review object's commit as `d849907345b59ae2ed96119b9a52c6ca6d2a0502`, not `5d426da1...`.
Reason: A synthetic reviewer-execution ref cannot replace the attributed material commit's real Git identity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3593666957

Disposition: NOT-A-BUG
Evidence: GitHub reports the review object's trusted commit as real owner head `d849907345b59ae2ed96119b9a52c6ca6d2a0502`; at that head the recorded material identity was reachable. After the later real material fix, the coordinator-approved mandatory tail reran sequentially on current material head `bafa16bbb4d9fb6c48422027a2ef8d4eb8a3d1dd`: QA and bug-hunter returned `PROCEED`, security-auditor returned `PASS`, and all reported no findings with native scanning `operator_directed_stop`.
Reason: The cited `5d426da1...` is not the trusted review commit or a live PR head, and current-head role evidence is now explicitly bound to the real material commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3593666969

Disposition: NOT-A-BUG
Evidence: All four inline findings from this review are individually dispositioned above: the valid local-config defect is fixed in `bafa16bbb4d9fb6c48422027a2ef8d4eb8a3d1dd`; the three synthetic-ref claims are contradicted by the review object's real `commit_id`, live ancestry, canonical attribution, and current-head role evidence.
Reason: The aggregate review object introduces no independent defect beyond its inline threads.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#pullrequestreview-4711673591

Disposition: FIXED
Commit: af2aed04166b2f3e1c1adf5b90903675f30c2f2d
Evidence: Both governed Git wrappers bind normal commands with exact `--work-tree=<resolved-cwd>`, command-line `core.worktree=<resolved-cwd>`, and adjacent exact `safe.directory`; clone uses `--no-checkout` without the incompatible work-tree bind and is followed by an explicitly bound detached checkout. `tests/test_experiment_runner_dispatch.py::test_snapshot_ignores_checkout_local_worktree_redirect` proves attacker-selected content is not snapshotted. Full runner/dispatcher/patch-builder tests, Ruff, both MyPy modes, `make validate-changed`, exact backend hook, pre-commit, and pre-push gates pass.
Reason: Work-tree discovery and materialization are now bound to the trusted resolved paths before any host snapshot diff/apply operation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3595183214 -> af2aed04166b2f3e1c1adf5b90903675f30c2f2d

Disposition: NOT-A-BUG
Evidence: GitHub records this review object's trusted `commit_id` as real owner head `6a0e54b6a8802939d8ff14d9baa5cb20acfc2e1d`, where the mapped FIXED commits are reachable. The cited `86ce7261...` execution ref is neither that `commit_id` nor a live PR head.
Reason: The finding again runs ancestry checks against an unavailable synthetic execution ref instead of the trusted GitHub review commit and complete live PR graph.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3595183202

Disposition: NOT-A-BUG
Evidence: GitHub records this review on real owner head `6a0e54b6a8802939d8ff14d9baa5cb20acfc2e1d`, not `86ce7261...`; the previously recorded material head was reachable there. After the later real work-tree fix, the mandatory QA, bug-hunter, and security-auditor tail reran sequentially on current material head `af2aed04166b2f3e1c1adf5b90903675f30c2f2d` and returned `PROCEED`, `PROCEED`, and `PASS` with no findings.
Reason: Current role evidence is bound to the real material head, while the finding's replacement head is not the trusted review identity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3595183208

Disposition: NOT-A-BUG
Evidence: The accepted Oracle evidence remains attributed to reachable material commit `b0f3f18078020dfe4e3c656ae3610288098c1122`, whose message contains the exact `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer. GitHub identifies this review commit as `6a0e54b6a8802939d8ff14d9baa5cb20acfc2e1d`, not `86ce7261...`.
Reason: The synthetic execution ref cannot replace the real attributed implementation commit or its Git identity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#discussion_r3595183212

Disposition: NOT-A-BUG
Evidence: All four inline findings from this review are individually dispositioned above: the valid work-tree redirect is fixed in `af2aed04166b2f3e1c1adf5b90903675f30c2f2d`; the three synthetic-ref claims are contradicted by the review object's real `commit_id`, live ancestry, canonical attribution, and current-head role evidence.
Reason: The aggregate review object introduces no independent defect beyond its inline threads.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2129#pullrequestreview-4713398951

## Merge Readiness

- [x] Mandatory post-open role tail completed on current material head.
- [ ] Current-head CI and diff coverage are terminal and passing.
- [ ] CodeRabbit, Sourcery, and Cubic have no actionable findings.
- [ ] Strict authenticated merge wrapper passes after the review wait window.
