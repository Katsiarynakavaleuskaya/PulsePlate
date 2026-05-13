<!-- markdownlint-disable MD013 MD034 -->
# PR 1749 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749>
- Branch: `codex/experiment-runner-notification-sink`
- Title: `feat(orchestration): add experiment notification artifact sink`
- Implementing commits:
  - `0d45edbe4df594cd22213107cd9aaf56c5bc87e6` - initial artifact-only sink.
  - `585607b04c0476fbb3f5f7cd8f35a42545c16858` - initial fixed-mapping artifact.
  - `e3f1232abc326ff805ae66737fddf5f34fd035d0` - post-open hardening and role-agent fixes.
- Scope: artifact-only experiment result notification sink, governance docs, and focused tests.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No review threads have been resolved. CodeRabbit initially skipped review while the PR
was draft; the PR was marked ready for review on 2026-05-13 and bot review is being
re-triggered through the normal ready-for-review cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235757434 -> e3f1232abc326ff805ae66737fddf5f34fd035d0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235757454 -> e3f1232abc326ff805ae66737fddf5f34fd035d0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235757467 -> e3f1232abc326ff805ae66737fddf5f34fd035d0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235761786 -> e3f1232abc326ff805ae66737fddf5f34fd035d0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235761791 -> e3f1232abc326ff805ae66737fddf5f34fd035d0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235799044 -> e3f1232abc326ff805ae66737fddf5f34fd035d0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1749#discussion_r3235799048 -> e3f1232abc326ff805ae66737fddf5f34fd035d0

Disposition: FIXED
Commit: e3f1232abc326ff805ae66737fddf5f34fd035d0
Evidence: `scripts/orchestration/experiment_notify.py` removes dynamic `sys.path.insert`, rejects symlinked artifact ancestors/components, redacts Windows/backslash local path shapes, and exposes explicit module-entrypoint failure for unsupported direct invocation contexts. `tests/test_experiment_notify.py` adds the regression coverage.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path scripts/orchestration --path docs/orchestration --path tests` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `. ../../.venv/bin/activate && python -m pytest -q tests/test_experiment_notify.py tests/test_experiment_runner.py tests/test_experiment_promote.py` - PASS, 63 tests after post-open review fixes.
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

- Security-auditor / Codex Security finding: durable artifact paths could be misleading if promotion metadata named an unrelated repo path. Disposition: FIXED in `0d45edbe4df594cd22213107cd9aaf56c5bc87e6` by target-specific durable artifact path validation and negative tests.
- QA / bug-hunter finding: false-green risk if tests only checked substring output. Disposition: FIXED in `0d45edbe4df594cd22213107cd9aaf56c5bc87e6` by deterministic full-body markdown checks, CLI JSON checks, and negative promotion/path tests.
- Premortem finding: reviewers may confuse artifact notification with external delivery. Disposition: FIXED in `0d45edbe4df594cd22213107cd9aaf56c5bc87e6` by explicit docs and rendered delivery boundary.

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
