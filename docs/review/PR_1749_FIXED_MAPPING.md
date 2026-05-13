<!-- markdownlint-disable MD013 MD034 -->
# PR 1749 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749>
- Branch: `codex/experiment-runner-notification-sink`
- Title: `feat(orchestration): add experiment notification artifact sink`
- Implementing commits:
  - `0d45edbe4df594cd22213107cd9aaf56c5bc87e6` - initial artifact-only sink.
  - `585607b04c0476fbb3f5f7cd8f35a42545c16858` - initial fixed-mapping artifact.
  - `e3f1232abc9a54743bc3485930c81f4de7c734ed` - post-open hardening and role-agent fixes.
  - `77bec5c2ca36167cee1077a3dcb0639487eb10d2` - review-thread mapping update.
  - `52c84f793b5338b14fc5953d9bab0672257acb9d` - stale-commit review-thread mapping.
  - `f9fb7ef437644b1782ca9906ad8131aa6a50ea50` - aggregate bot review mapping.
  - `b281fa42bf17d9a565f536e7b64acabc21e7202b` - redaction and symlink-containment follow-up fixes.
  - `67dea3563288468c70d45895885c8d0b90712c15` - post-fix review-thread mapping.
  - `155b25f088f1f0fc5d36daf7d33243e7f11d1f50` - role review pass mapping.
  - `6b837c9207ccddb00f2663a8d73762f458b154d9` - result evidence validation fixes.
  - `389e5c3d5d62ad6721842e8fc686db8a0b91107d` - valid ancestor proof mapping.
  - `791caa567ff0f3f4bed2051e93141f16bf667554` - latest review-fix mapping.
  - `c15f2ac344b92be833567d7c64745fd3c11d0013` - notification diagnostic hardening.
  - `a8d7432917674a63bd844e36d95748ab1e03d3e7` - diagnostic fix mapping update.
  - `d2e15ebb1c51584d5d97da639bd04868185708d2` - stale proof mapping update.
  - `9e42c202155683886b49ee381c3f1b15b67a0955` - promotion evidence and diagnostic validation.
  - `527ea55bce9345189a09403f13dc310c45d74a63` - promotion evidence mapping update.
  - `cc7a28debe49cc228abacb8196c8c33c63e27dbe` - command diagnostic and mutable-surface containment hardening.
  - `98740bebd04302f0cd552558d09df60af8eeb48b` - fail-closed evidence drift validation.
  - `b5bf50f9f60204feb476ce2ca810fdb773d225df` - typed surface containment follow-up.
  - `261085d5e2fc8d760dcc743fc0adeffadcaa07c5` - runner-aligned notification evidence validation.
  - `0b7790f853562deb0a58ddd934085636d990d7be` - sanitized validation diagnostics and accepted/rejected state checks.
  - `367504ae685a97c0cd410b2acde0bfc115a13b5a` - forged evidence rejection hardening.
  - `a705625f9d39f652cee75463e07fd26d5a9ebab9` - rejected-result shape alignment.
- Scope: artifact-only experiment result notification sink, governance docs, and focused tests.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open bot review threads were classified, fixed, mapped, and resolved on 2026-05-13.
The PR was marked ready for review after the draft-only CodeRabbit skip, and the latest
current-head bot/CI cycle is being monitored before any merge-readiness claim.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235757434 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235757454 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235757467 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4283401283 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235761786 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235761791 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235761797 -> 52c84f793b5338b14fc5953d9bab0672257acb9d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235799044 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235799048 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4283452129 -> e3f1232abc9a54743bc3485930c81f4de7c734ed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235961723 -> b281fa42bf17d9a565f536e7b64acabc21e7202b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235961729 -> b281fa42bf17d9a565f536e7b64acabc21e7202b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235961734 -> b281fa42bf17d9a565f536e7b64acabc21e7202b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236005091 -> b281fa42bf17d9a565f536e7b64acabc21e7202b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4283699021 -> b281fa42bf17d9a565f536e7b64acabc21e7202b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236168813 -> 389e5c3d5d62ad6721842e8fc686db8a0b91107d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236168816 -> 6b837c9207ccddb00f2663a8d73762f458b154d9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236168825 -> 6b837c9207ccddb00f2663a8d73762f458b154d9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284047218 -> c15f2ac344b92be833567d7c64745fd3c11d0013
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236302268 -> a8d7432917674a63bd844e36d95748ab1e03d3e7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236302273 -> c15f2ac344b92be833567d7c64745fd3c11d0013
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236302278 -> c15f2ac344b92be833567d7c64745fd3c11d0013
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284068594 -> c15f2ac344b92be833567d7c64745fd3c11d0013
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236321888 -> c15f2ac344b92be833567d7c64745fd3c11d0013
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236445973 -> 527ea55bce9345189a09403f13dc310c45d74a63
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284209741 -> 9e42c202155683886b49ee381c3f1b15b67a0955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236445976 -> 9e42c202155683886b49ee381c3f1b15b67a0955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236445980 -> 9e42c202155683886b49ee381c3f1b15b67a0955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236445984 -> 9e42c202155683886b49ee381c3f1b15b67a0955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284232269 -> 9e42c202155683886b49ee381c3f1b15b67a0955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236465759 -> 9e42c202155683886b49ee381c3f1b15b67a0955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236465778 -> 9e42c202155683886b49ee381c3f1b15b67a0955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236650609 -> cc7a28debe49cc228abacb8196c8c33c63e27dbe
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236650615 -> cc7a28debe49cc228abacb8196c8c33c63e27dbe
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236650623 -> cc7a28debe49cc228abacb8196c8c33c63e27dbe
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236650625 -> cc7a28debe49cc228abacb8196c8c33c63e27dbe
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284441229 -> cc7a28debe49cc228abacb8196c8c33c63e27dbe
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236651151 -> cc7a28debe49cc228abacb8196c8c33c63e27dbe
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284603279 -> 98740bebd04302f0cd552558d09df60af8eeb48b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236793354 -> 98740bebd04302f0cd552558d09df60af8eeb48b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284603849 -> 98740bebd04302f0cd552558d09df60af8eeb48b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236793887 -> 98740bebd04302f0cd552558d09df60af8eeb48b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236793892 -> 98740bebd04302f0cd552558d09df60af8eeb48b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236793897 -> 98740bebd04302f0cd552558d09df60af8eeb48b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284687950 -> 261085d5e2fc8d760dcc743fc0adeffadcaa07c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236869446 -> 261085d5e2fc8d760dcc743fc0adeffadcaa07c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236869450 -> 261085d5e2fc8d760dcc743fc0adeffadcaa07c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236869455 -> 261085d5e2fc8d760dcc743fc0adeffadcaa07c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284762777 -> 0b7790f853562deb0a58ddd934085636d990d7be
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236937872 -> 0b7790f853562deb0a58ddd934085636d990d7be
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236937877 -> 0b7790f853562deb0a58ddd934085636d990d7be
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236937880 -> 0b7790f853562deb0a58ddd934085636d990d7be
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236937894 -> 0b7790f853562deb0a58ddd934085636d990d7be
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#pullrequestreview-4284815927 -> 367504ae685a97c0cd410b2acde0bfc115a13b5a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236984651 -> 367504ae685a97c0cd410b2acde0bfc115a13b5a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236984659 -> 367504ae685a97c0cd410b2acde0bfc115a13b5a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236984667 -> 367504ae685a97c0cd410b2acde0bfc115a13b5a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3236984673 -> 367504ae685a97c0cd410b2acde0bfc115a13b5a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3237147911 -> a705625f9d39f652cee75463e07fd26d5a9ebab9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3237147913 -> a705625f9d39f652cee75463e07fd26d5a9ebab9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3237147920 -> a705625f9d39f652cee75463e07fd26d5a9ebab9

Disposition: FIXED
Commit: e3f1232abc9a54743bc3485930c81f4de7c734ed
Evidence: `scripts/orchestration/experiment_notify.py` removes dynamic `sys.path.insert`, rejects symlinked artifact ancestors/components, redacts Windows/backslash local path shapes, and exposes explicit module-entrypoint failure for unsupported direct invocation contexts. `tests/test_experiment_notify.py` adds the regression coverage.

Disposition: FIXED
Commit: 52c84f793b5338b14fc5953d9bab0672257acb9d
Evidence: This artifact now lists all implementing commits instead of only the initial sink commit and maps the stale-commit review thread to the review-mapping update.

Disposition: FIXED
Commit: b281fa42bf17d9a565f536e7b64acabc21e7202b
Evidence: `scripts/orchestration/experiment_notify.py` now checks `is_symlink()` without `exists()` gating, redacts home-relative credential paths and control-character paths, and `tests/test_experiment_notify.py` covers those regressions.

Disposition: FIXED
Commit: 6b837c9207ccddb00f2663a8d73762f458b154d9
Evidence: `scripts/orchestration/experiment_notify.py` now rejects promoted accepted results when `shared_tree_untouched` is false and cross-checks result `mutated_paths` / `oracle_results` against the validated packet before rendering notification evidence. `tests/test_experiment_notify.py` covers dirty shared-tree promotion, missing accepted oracle results, out-of-surface mutated paths, and extra oracle commands.

Disposition: FIXED
Commit: 389e5c3d5d62ad6721842e8fc686db8a0b91107d
Evidence: This artifact now uses full valid commit SHAs reachable from the current branch head for every mapped FIXED proof.

Disposition: FIXED
Commit: a8d7432917674a63bd844e36d95748ab1e03d3e7
Evidence: This artifact maps the latest stale-SHA review thread to a current-head ancestor commit made after the review comment.

Disposition: FIXED
Commit: 527ea55bce9345189a09403f13dc310c45d74a63
Evidence: This artifact maps the latest current-head stale-proof review thread to a current-head ancestor commit made after the review comment.

Disposition: FIXED
Commit: c15f2ac344b92be833567d7c64745fd3c11d0013
Evidence: `scripts/orchestration/experiment_notify.py` now treats directory mutable surfaces as containing nested result paths, skips leading shell `KEY=value` assignments before rendering oracle command names, and redacts unexpected-oracle diagnostics to command names. `tests/test_experiment_notify.py` covers directory surface containment, env-assignment command redaction, and secret-free fail-closed diagnostics.

Disposition: FIXED
Commit: 9e42c202155683886b49ee381c3f1b15b67a0955
Evidence: `scripts/orchestration/experiment_notify.py` now redacts outside-surface mutated-path diagnostics, accepts nested directory mutable surfaces without suffix heuristics, validates promotion evidence oracle commands/mutated paths/oracle count against packet/result metadata, and rejects accepted results with failed or timed-out oracles. `tests/test_experiment_notify.py` covers each regression.

Disposition: FIXED
Commit: cc7a28debe49cc228abacb8196c8c33c63e27dbe
Evidence: `scripts/orchestration/experiment_notify.py` now redacts JSON load failures without echoing unsafe paths, skips multiline shell environment assignments before rendering oracle names, redacts credential-path command executables, and prevents file-like mutable surfaces from matching nested paths. `tests/test_experiment_notify.py` covers each regression.

Disposition: FIXED
Commit: 98740bebd04302f0cd552558d09df60af8eeb48b
Evidence: `scripts/orchestration/experiment_notify.py` now allows nested mutable paths only for explicit or existing directory surfaces, rejects accepted results with non-null `failure_class`, requires rejected result oracle evidence to preserve packet prefix order, and redacts `GITHUB_STEP_SUMMARY` write failures. `tests/test_experiment_notify.py` covers each regression.

Disposition: FIXED
Commit: 261085d5e2fc8d760dcc743fc0adeffadcaa07c5
Evidence: `scripts/orchestration/experiment_notify.py` now aligns directory-surface matching with runner prefix behavior for new directories while still rejecting existing file surfaces, rejects rejected results whose terminal oracle passed, and redacts notification output write failures. `tests/test_experiment_notify.py` covers each regression.

Disposition: FIXED
Commit: 0b7790f853562deb0a58ddd934085636d990d7be
Evidence: `scripts/orchestration/experiment_notify.py` now sanitizes shared-validator `ValueError` diagnostics, allows `infra_flake` rejected results after passing oracle prefixes, and rejects accepted results with dirty shared-tree evidence before notification rendering. `tests/test_experiment_notify.py` covers each regression.

Disposition: FIXED
Commit: 367504ae685a97c0cd410b2acde0bfc115a13b5a
Evidence: `scripts/orchestration/experiment_notify.py` now rejects traversal components before mutable-surface matching, requires terminal oracle evidence for oracle-failure rejected statuses, and redacts sensitive bare oracle command names. `tests/test_experiment_notify.py` covers each regression.

Disposition: FIXED
Commit: a705625f9d39f652cee75463e07fd26d5a9ebab9
Evidence: `scripts/orchestration/experiment_notify.py` now rejects pre-oracle rejected-result classes when oracle evidence is present, rejects `policy_violation` evidence with mutated paths, and scopes terminal-oracle failure requirements to oracle-derived failure classes so `metric_regression` can summarize passing oracle prefixes. `tests/test_experiment_notify.py` covers each regression.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path scripts/orchestration --path docs/orchestration --path tests` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `. ../../.venv/bin/activate && python -m pytest -q tests/test_experiment_notify.py tests/test_experiment_runner.py tests/test_experiment_promote.py` - PASS, 93 tests after post-open review fixes.
- `. ../../.venv/bin/activate && ruff check scripts/orchestration/experiment_notify.py tests/test_experiment_notify.py` - PASS.
- `. ../../.venv/bin/activate && python -m mypy scripts/orchestration/experiment_notify.py --no-incremental --cache-dir=/dev/null` - PASS.
- `pre-commit run --all-files` - PASS after black formatted `scripts/orchestration/experiment_notify.py`.
- `make VENV_PYTHON=../../.venv/bin/python validate-changed` - PASS.
- Push hook - PASS: changed-file mypy, pip-audit, backend pre-push tests, full-repo Bandit, Docker build test.

Plain `make validate-changed` in this isolated worktree failed before test execution because the worktree has no local `.venv` and the target selected system `python3`, which lacked `fastapi`. The same target passed with explicit `VENV_PYTHON=../../.venv/bin/python`.

## Security Notes

- Artifact-only delivery: no email, Slack, GitHub PR comment, SMTP, or external network notification is introduced.
- Rendered notification omits raw patch text, oracle stdout/stderr, cwd, local absolute paths, and sensitive path parts.
- `GITHUB_STEP_SUMMARY` writes require explicit `--github-step-summary`.
- Promotion decisions are checked against packet/result status and target-specific durable artifact paths.
- `PulsePlate Experiment Runner <pulseplate@pm.me>` is public git metadata for this PR lane only; it is not a result delivery channel.

## Premortem / Role Review Findings

- Coordinator bootstrap: `artifacts/orchestration/task_packets/pr1749_post_open_review_2026-05-13.json` produced task packet `8384fad99c80`; declared executable order was `agent-coordinator -> architecture-specialist -> cursor-specialist-agent -> security-auditor -> qa-engineer-agent -> bug-hunter`.
- Security-auditor / Codex Security finding: durable artifact paths could be misleading if promotion metadata named an unrelated repo path. Disposition: FIXED in `0d45edbe4df594cd22213107cd9aaf56c5bc87e6` by target-specific durable artifact path validation and negative tests.
- QA / bug-hunter finding: false-green risk if tests only checked substring output. Disposition: FIXED in `0d45edbe4df594cd22213107cd9aaf56c5bc87e6` by deterministic full-body markdown checks, CLI JSON checks, and negative promotion/path tests.
- Premortem finding: reviewers may confuse artifact notification with external delivery. Disposition: FIXED in `0d45edbe4df594cd22213107cd9aaf56c5bc87e6` by explicit docs and rendered delivery boundary.
- Premortem finding: notification artifacts could leak local runner details through path edge cases. Disposition: FIXED in `e3f1232abc9a54743bc3485930c81f4de7c734ed` and `b281fa42bf17d9a565f536e7b64acabc21e7202b` by Windows/backslash, home-credential, control-character, symlinked-directory, symlinked-ancestor, symlinked-child, and broken-symlink output tests.
- Premortem finding: stale or hand-edited result/promotion evidence could be summarized as accepted/promoted. Disposition: FIXED in `6b837c9207ccddb00f2663a8d73762f458b154d9` by packet/result evidence cross-checking and dirty shared-tree promotion rejection.
- Premortem decision: proceed with changes; required changes have been applied, and readiness remains blocked only on current-head CI/bot review terminal state and the mandatory wait-window.

## Risks / Rollback

- Risk: future callers may assume artifact notification sends email or Slack. Mitigation: script, docs, PR body, and artifact text state artifact-only delivery.
- Risk: environment-specific worktree validation can false-red when `.venv` is root-local. Mitigation: recorded explicit `VENV_PYTHON` command and pre-push hook evidence.
- Rollback: revert this PR; `experiment_runner.py` and `experiment_promote.py` behavior is unchanged.

## Merge Readiness

- [ ] Coordinator final synthesis completed.
- [ ] Canonical artifact updated after bot/human review cycle.
- [ ] Local narrow gates rerun after final review fixes.
- [ ] Current-head CI pending after ready-for-review governance update.
- [ ] Bot/human review pass pending.
- [ ] Mandatory wait-window pending.

PR is not merge-ready.

## Deferred / Follow-ups

- Real email, Slack, or GitHub-comment result delivery remains a later security-governed PR with explicit sink, auth, audit, opt-in behavior, and secret handling.
