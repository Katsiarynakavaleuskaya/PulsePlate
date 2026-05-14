<!-- markdownlint-disable MD013 MD034 -->
# PR 1752 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752>
- Branch: `codex/experiment-runner-gnhi-crypto-policy`
- Title: `feat(orchestration): govern experiment runner identity`
- Implementing commits:
  - `f53cb69db` - governed Experiment Runner identity boundary, offline guard, tests, and nested git environment hardening.
  - `e33e29c2d` - initial PR 1752 fixed-mapping artifact.
  - `229777a55` - CodeRabbit CLI governance fixes for backlog priority ordering and Phase 2 fixed-mapping formatting.
  - `916b51d57` - mapping entry for CodeRabbit CLI governance fixes.
  - `6f1e29fb8` - canonical no-actionable review-thread mapping format for Phase 2 parser compatibility.
  - `7b8c78a35` - mapping entry for canonical Phase 2 parser format fix.
  - `5790abc7f` - PR body Phase 2 mirror validation evidence.
  - `19d2c92ee` - fail-closed malformed policy validation and token-prefix guard hardening.
  - `2853fca3e` - repo-standard `make validate-changed` validation command wording.
  - `4f431c553` - additional fail-closed identity policy bypass hardening for repeated separators, token-shaped keys, Slack app/config tokens, and authority drift.
- Scope: Experiment Runner cryptographic attribution boundary, policy validation, Slack identity deferral, and focused runner test hardening.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806276 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806284 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806290 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806297 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806302 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242812229 -> 229777a55
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242812243 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4291639395 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242847407 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242847414 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242847423 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242847432 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4291682243 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242894051 -> 2853fca3e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4291735416 -> 2853fca3e

Disposition: FIXED
Commit: `229777a55`, `19d2c92ee`, `2853fca3e`, `4f431c553`
Evidence: CodeRabbit/Cubic/Codex bot findings were fixed by checking the fixed-mapping artifact checkboxes, hardening malformed policy validation to fail closed without raw `TypeError`, expanding current token-prefix detection for `github_pat_`, `xapp-`, and `xoxc-`, detecting token-shaped JSON keys, rejecting repeated separators in sensitive key names, rejecting authority drift outside `authority_boundary`, and replacing the brittle validation command text with `make validate-changed`.

## Role-Agent Findings

Disposition: FIXED
Commit: `f53cb69db`
Evidence: `scripts/orchestration/check_experiment_runner_identity.py` rejects placeholder attribution, non-governed attribution, private-key/token-shaped values, sensitive key names with separators/spaces, merge/readiness/thread authority drift, notification delivery drift, and Slack crypto-identity drift. `tests/test_experiment_runner_identity_policy.py` covers the regressions raised by `qa-engineer-agent` and `bug-hunter`.

Disposition: FIXED
Commit: `f53cb69db`
Evidence: `scripts/orchestration/experiment_runner.py` strips inherited `GIT_*` environment variables from nested git subprocesses so isolated experiment checkouts are not affected by parent commit/pre-commit hook context. `tests/test_experiment_runner.py` covers hook-style `GIT_INDEX_FILE` leakage.

Disposition: NOT-A-BUG
Evidence: Coordinator scope was refreshed after review to include actual touched files, including `scripts/orchestration/experiment_runner.py`, `scripts/AGENTS.md`, `tests/test_experiment_runner.py`, and `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.json`.

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-experiment-runner-slack-identity-boundary`
Evidence: Slack identity is explicitly deferred as notification/display identity only. It is not a cryptographic Git identity and requires a separate security-governed PR.

Disposition: FIXED
Commit: `229777a55`
Evidence: CodeRabbit CLI governance findings were addressed by moving the Slack follow-up from the Open Items insertion point into the `### P2` section, changing the fixed-mapping heading to `### Fixed in Commit Mapping`, completing the discussion-thread/fixed-mapping checklist for the local review pass, and removing the stale draft-only note.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path ...` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `scripts/orchestration/check_experiment_runner_identity.py --json` PASS.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS.
- `black --check` on changed Python files PASS.
- `flake8` on identity guard/tests PASS.
- `mypy --explicit-package-bases` on identity guard/tests PASS.
- `bandit -q scripts/orchestration/check_experiment_runner_identity.py` PASS.
- `pre-commit run --all-files` PASS.
- `make validate-changed` PASS.
- Pre-push hooks PASS: mypy, pip-audit, backend tests, full bandit, docker-build-test hook.
- `python3 scripts/ci/check_pr_body_phase2_gates.py --body "$(gh pr view 1752 --json body -q .body)" --pr-number 1752` PASS after live PR body mirror update.

## Merge Readiness

- [ ] Current-head CI terminal and required checks passing.
- [ ] CodeRabbit no actionables.
- [ ] Cubic no actionables.
- [ ] Sourcery no actionables.
- [ ] Discussion-thread pass complete.
- [ ] Fixed mapping artifact/body mirror updated after review activity.
- [ ] Required wait-window complete.
