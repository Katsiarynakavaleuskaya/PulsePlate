# PR 1751 Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Implementing Commits

- `584b5d00f93ebc5f799c4631509b4800f869c10a` - `feat(orchestration): add experiment email notification sink`
- `f4c2601df6cb55f409e62b332773b5512354b7bf` - `docs(review): add PR 1751 fixed mapping`
- `7ef7d0904c0d32337e84fd4400267d0eb0db7ce7` - `docs(review): fix PR 1751 phase2 mapping contract`
- `da8b2db70bbd11afe765b30da551b5aa629a43fa` - `fix(orchestration): harden experiment email notification sink`

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
  - promotion overclaim risk -> FIXED in `584b5d00f93ebc5f799c4631509b4800f869c10a`; real `experiment_promote` result compatibility fixed in `da8b2db70bbd11afe765b30da551b5aa629a43fa`
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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237898304 -> da8b2db70bbd11afe765b30da551b5aa629a43fa
Disposition: FIXED
Commit: da8b2db70bbd11afe765b30da551b5aa629a43fa
Evidence: `scripts/AGENTS.md` now says `local artifact output is the default`; `VENV_PYTHON=../../.venv/bin/python pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237905243 -> da8b2db70bbd11afe765b30da551b5aa629a43fa
Disposition: FIXED
Commit: da8b2db70bbd11afe765b30da551b5aa629a43fa
Evidence: Implementing commit list now includes current branch fix commits through `da8b2db70bbd11afe765b30da551b5aa629a43fa`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237905249 -> da8b2db70bbd11afe765b30da551b5aa629a43fa
Disposition: FIXED
Commit: da8b2db70bbd11afe765b30da551b5aa629a43fa
Evidence: `scripts/orchestration/experiment_notify.py` accepts promoted results from the real runner/promote flow without requiring runner-only `promotion_ready=true`; `tests/test_experiment_notify.py::test_notification_includes_promotion_decision_from_promote_output` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237905251 -> da8b2db70bbd11afe765b30da551b5aa629a43fa
Disposition: FIXED
Commit: da8b2db70bbd11afe765b30da551b5aa629a43fa
Evidence: Email audit writes `send_in_progress` before SMTP send and duplicate retry blocks on matching `send_in_progress`; `tests/test_experiment_notify.py::test_email_delivery_blocks_retry_when_sent_audit_write_fails` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1751#discussion_r3237905252 -> da8b2db70bbd11afe765b30da551b5aa629a43fa
Disposition: FIXED
Commit: da8b2db70bbd11afe765b30da551b5aa629a43fa
Evidence: Email audit path is canonical by experiment id, not caller-controlled `--output`; `tests/test_experiment_notify.py::test_email_delivery_is_idempotent_across_output_paths` covers it.

## Merge Readiness

- [ ] Coordinator-first preflight/bootstrap completed.
- [ ] Canonical artifact exists.
- [ ] Local narrow gates completed.
- [ ] Current-head CI pending.
- [ ] Bot/human review pass pending.
- [ ] Mandatory wait-window pending.
