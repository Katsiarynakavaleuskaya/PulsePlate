# PR 1751 Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Implementing Commits

- `584b5d00f93ebc5f799c4631509b4800f869c10a` - `feat(orchestration): add experiment email notification sink`
- `f4c2601df6cb55f409e62b332773b5512354b7bf` - `docs(review): add PR 1751 fixed mapping`
- `7ef7d0904c0d32337e84fd4400267d0eb0db7ce7` - `docs(review): fix PR 1751 phase2 mapping contract`
- `da8b2db703c4a9e8840524f7d5987e1da4d79463` - `fix(orchestration): harden experiment email notification sink`
- `fcef53e4e53eac11ff165084a8efb08c72b0cf73` - `docs(review): map PR 1751 review fixes`
- `716e94e09e5386ffeb4abb90ece0b8c1456456f9` - `fix(orchestration): type email audit path resolution`
- `51f0344106f92846e168685ce62f61145358037a` - `fix(orchestration): stabilize email audit path typing`
- `ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4` - `fix(orchestration): harden smtp email delivery claims`
- `f0d39d65e5554fa8b2798dc2d4494c04cbab0b4d` - `docs(review): map PR 1751 smtp claim fixes`
- `d5998b4899df9b07a6c295841f52dab27b08df51` - `docs(orchestration): align experiment notify lifecycle`
- `6acfee69f276900e47c844fceb8ceb048eade324` - `fix(orchestration): fail closed on duplicate experiment email sends`

## Coordinator / Agent Passes

- Coordinator bootstrap:
  - Pre-open packet: `artifacts/orchestration/task_packets/experiment_email_notification_sink_preopen.json` (local gitignored)
  - Post-open packet: `artifacts/orchestration/task_packets/experiment_email_notification_sink_pr1751_postopen.json` (local gitignored)
- Declared role coverage:
  - `agent-coordinator`
  - `security-auditor`
  - `backend-engineer`
  - `qa-engineer-agent`
  - `bug-hunter`
  - `data-scientist`
  - `pulseplate-premortem-risk-review`
  - `codex-security`
- Premortem/security/QA/bug/data-scientist findings before PR open:
  - duplicate send risk -> FIXED in `584b5d00f93ebc5f799c4631509b4800f869c10a`
  - SMTP send before durable audit evidence -> FIXED in `584b5d00f93ebc5f799c4631509b4800f869c10a`
  - malformed SMTP sender bypassing sanitized failure path -> FIXED in `584b5d00f93ebc5f799c4631509b4800f869c10a`
  - promotion overclaim risk -> FIXED in `584b5d00f93ebc5f799c4631509b4800f869c10a`; real `experiment_promote` result compatibility fixed in `da8b2db703c4a9e8840524f7d5987e1da4d79463`
  - email audit not bound to exact evidence body/source artifacts -> FIXED in `584b5d00f93ebc5f799c4631509b4800f869c10a`
  - missing SMTP validation negative tests -> FIXED in `584b5d00f93ebc5f799c4631509b4800f869c10a`
- Codex Security scan:
  - diff-scoped scan completed before PR open
  - result: no reportable findings

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path scripts/orchestration/experiment_notify.py --path tests/test_experiment_notify.py --path docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md --path scripts/AGENTS.md` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- `source .venv/bin/activate && python -m pytest -q tests/test_experiment_notify.py tests/test_experiment_runner.py tests/test_experiment_promote.py` -> PASS
- `source .venv/bin/activate && ruff check scripts/orchestration/experiment_notify.py tests/test_experiment_notify.py` -> PASS
- `source .venv/bin/activate && python -m mypy scripts/orchestration/experiment_notify.py --no-incremental --cache-dir=/dev/null` -> PASS
- `source .venv/bin/activate && bandit -q scripts/orchestration/experiment_notify.py` -> PASS
- `make VENV_PYTHON=.venv/bin/python validate-changed` -> PASS
- `VENV_PYTHON=.venv/bin/python pre-commit run --all-files` -> PASS
- `git push -u origin codex/experiment-email-notification-sink` pre-push hooks -> PASS

## Main CI Note

At lane start, local `main` was synced with `origin/main` (`0 0`), but GitHub still reported current-head main `CI` run `25827093414` as `in_progress` on merge commit `17db1118d215d0ffecd5e09a8d254db03db336e4`.

Operator explicitly held main on control and approved opening this PR lane. This PR must remain draft and must not claim merge readiness while required current-head checks, bot review, or main fallout are unresolved.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237898304 -> da8b2db703c4a9e8840524f7d5987e1da4d79463
Disposition: FIXED
Commit: da8b2db703c4a9e8840524f7d5987e1da4d79463
Evidence: `scripts/AGENTS.md` now says `local artifact output is the default`; `VENV_PYTHON=../../.venv/bin/python pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#pullrequestreview-4285886523 -> da8b2db703c4a9e8840524f7d5987e1da4d79463
Disposition: FIXED
Commit: da8b2db703c4a9e8840524f7d5987e1da4d79463
Evidence: Sourcery review-level actionable typo is fixed by the same `scripts/AGENTS.md` wording change as `discussion_r3237898304`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237901619 -> fcef53e4e53eac11ff165084a8efb08c72b0cf73
Disposition: FIXED
Commit: fcef53e4e53eac11ff165084a8efb08c72b0cf73
Evidence: Merge-readiness checklist boxes in this artifact are unchecked until the final merge cycle.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#pullrequestreview-4285890872 -> fcef53e4e53eac11ff165084a8efb08c72b0cf73
Disposition: FIXED
Commit: fcef53e4e53eac11ff165084a8efb08c72b0cf73
Evidence: CodeRabbit review-level actionables are mapped through their inline findings; the checklist/mapping artifact correction is fixed in this commit, and CLI help/command replay concerns are covered by the associated inline mappings.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237905243 -> da8b2db703c4a9e8840524f7d5987e1da4d79463
Disposition: FIXED
Commit: da8b2db703c4a9e8840524f7d5987e1da4d79463
Evidence: Implementing commit list now uses reachable commits from this branch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237905249 -> da8b2db703c4a9e8840524f7d5987e1da4d79463
Disposition: FIXED
Commit: da8b2db703c4a9e8840524f7d5987e1da4d79463
Evidence: `scripts/orchestration/experiment_notify.py` accepts promoted results from the real runner/promote flow without requiring runner-only `promotion_ready=true`; `tests/test_experiment_notify.py::test_notification_includes_promotion_decision_from_promote_output` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237905251 -> ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Disposition: FIXED
Commit: ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Evidence: Email audit is claimed before SMTP send and retry blocks on matching non-stale `send_in_progress`; `tests/test_experiment_notify.py::test_email_delivery_blocks_retry_when_sent_audit_write_fails` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237905252 -> da8b2db703c4a9e8840524f7d5987e1da4d79463
Disposition: FIXED
Commit: da8b2db703c4a9e8840524f7d5987e1da4d79463
Evidence: Email audit path is canonical by experiment id, not caller-controlled `--output`; `tests/test_experiment_notify.py::test_email_delivery_is_idempotent_across_output_paths` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239524561 -> ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Disposition: FIXED
Commit: ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Evidence: Email send claim now uses exclusive create, duplicate-blocking `send_in_progress`, and stale-claim reclaim; `tests/test_experiment_notify.py::test_stale_email_send_claim_can_be_reclaimed` covers reclaim.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#pullrequestreview-4287802089 -> ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Disposition: FIXED
Commit: ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Evidence: CodeRabbit review-level actionables are fixed by the atomic send claim and implicit TLS changes mapped below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239524565 -> ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Disposition: FIXED
Commit: ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Evidence: SMTP port `465` uses `SMTP_SSL`; `tests/test_experiment_notify.py::test_smtp_implicit_tls_uses_smtp_ssl` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#pullrequestreview-4287893382 -> d5998b4899df9b07a6c295841f52dab27b08df51
Disposition: FIXED
Commit: d5998b4899df9b07a6c295841f52dab27b08df51
Evidence: Experiment lifecycle flow now appends `-> notify` after `-> promote or discard`, matching `Step 6: Notify`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239603946 -> d5998b4899df9b07a6c295841f52dab27b08df51
Disposition: FIXED
Commit: d5998b4899df9b07a6c295841f52dab27b08df51
Evidence: `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md` lifecycle flow now includes the notify stage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239534960 -> f0d39d65e5554fa8b2798dc2d4494c04cbab0b4d
Disposition: FIXED
Commit: f0d39d65e5554fa8b2798dc2d4494c04cbab0b4d
Evidence: Fixed-mapping artifact now uses reachable full branch commit SHAs; `python3 scripts/ci/check_pr_body_phase2_gates.py --body "$BODY" --pr-number 1751` passed before this mapping follow-up.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239534963 -> ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Disposition: FIXED
Commit: ebe44d4e5ead92dd7e2b0a0ba6cbe087d6a2e9c4
Evidence: SMTP `quit()` failures after accepted `send_message()` are ignored so the final `sent` audit remains durable; `tests/test_experiment_notify.py::test_smtp_quit_failure_after_send_keeps_delivery_successful` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239605792 -> 6acfee69f276900e47c844fceb8ceb048eade324
Disposition: FIXED
Commit: 6acfee69f276900e47c844fceb8ceb048eade324
Evidence: Existing `send_in_progress` audit records now fail closed without stale reclaim, preventing ambiguous post-SMTP retries; `tests/test_experiment_notify.py::test_stale_email_send_claim_blocks_retry` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239605794 -> 6acfee69f276900e47c844fceb8ceb048eade324
Disposition: FIXED
Commit: 6acfee69f276900e47c844fceb8ceb048eade324
Evidence: Existing `sent` audit records now block by canonical experiment id regardless of changed markdown; `tests/test_experiment_notify.py::test_email_delivery_is_idempotent_for_experiment_id_when_markdown_changes` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239605801 -> 6acfee69f276900e47c844fceb8ceb048eade324
Disposition: FIXED
Commit: 6acfee69f276900e47c844fceb8ceb048eade324
Evidence: Stale `send_in_progress` reclaim was removed in favor of fail-closed duplicate protection, eliminating the non-atomic stale-reclaim path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#pullrequestreview-4287900129 -> 6acfee69f276900e47c844fceb8ceb048eade324
Disposition: FIXED
Commit: 6acfee69f276900e47c844fceb8ceb048eade324
Evidence: Cubic review-level duplicate-send finding is fixed by experiment-id fail-closed duplicate protection.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3239609603 -> 6acfee69f276900e47c844fceb8ceb048eade324
Disposition: FIXED
Commit: 6acfee69f276900e47c844fceb8ceb048eade324
Evidence: Duplicate-send guard no longer keys only on notification content; existing `sent`/`send_in_progress` audit for the experiment blocks delivery.

## Merge Readiness

- [ ] Coordinator-first preflight/bootstrap completed.
- [ ] Canonical artifact exists.
- [ ] Local narrow gates completed.
- [ ] Current-head CI pending.
- [ ] Bot/human review pass pending.
- [ ] Mandatory wait-window pending.
