<!-- markdownlint-disable MD013 MD034 -->
# PR 1765 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1765>
- Branch: `codex/experiment-runner-attribution-auto-email-reports`
- Title: `feat(orchestration): add experiment runner email pipeline`
- Implementing commits:
  - `d0daee249` - added canonical Experiment Runner co-author guidance, governed pipeline wrapper, identity guidance guard coverage, email-report regression tests, and mypy-compatible promotion typing cleanup.
  - `cd05b9a2d` - fixed Cubic and CodeRabbit review findings for relative promotion output handling, placeholder-email whitespace variants, and sanitized stage stderr/exception handling.
  - `fcb539efa` - fixed CodeRabbit promotion-output containment finding by rejecting wrapper output paths that escape the governed promotions artifact root.
- Scope: Experiment Runner attribution instructions and governed automatic email report wrapper only. No Slack delivery, no git-attribution delivery trigger, no signing key storage, no merge authority change, and no review-thread authority change.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: cd05b9a2d
Evidence: Cubic found that pre-resolving `--promotion-output` broke relative output paths. `scripts/orchestration/experiment_pipeline.py` now preserves the raw relative output argument for `experiment_promote.py` while resolving the expected artifact path for notification/summary use, and `tests/test_experiment_pipeline.py` covers `--promotion-output nested/decision.json`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1765#pullrequestreview-4306228421 -> cd05b9a2d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1765#discussion_r3255402933 -> cd05b9a2d

Disposition: FIXED
Commit: cd05b9a2d
Evidence: CodeRabbit found that placeholder co-author guidance with whitespace inside angle brackets could bypass the regex. `scripts/orchestration/check_experiment_runner_identity.py` now rejects `< runner@example.com >`, and `tests/test_experiment_runner_identity_policy.py` covers that variant.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1765#discussion_r3255410259 -> cd05b9a2d

Disposition: FIXED
Commit: cd05b9a2d
Evidence: CodeRabbit found that child stage stderr and unexpected exceptions could leak outside the pipeline's sanitized failure path. `scripts/orchestration/experiment_pipeline.py` now redirects both stdout and stderr and normalizes unexpected stage exceptions to the generic stage failure message; `tests/test_experiment_pipeline.py` covers stderr and exception redaction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1765#discussion_r3255410262 -> cd05b9a2d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1765#pullrequestreview-4306234841 -> cd05b9a2d

Disposition: FIXED
Commit: fcb539efa
Evidence: CodeRabbit found that `experiment_pipeline.py --promotion-output` could widen the wrapper write boundary with absolute paths or `..` escapes. `scripts/orchestration/experiment_pipeline.py` now resolves the candidate output and fails closed unless it remains under `artifacts/orchestration/experiments/promotions/`; `tests/test_experiment_pipeline.py` covers parent-directory and absolute-path escapes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1765#discussion_r3255475576 -> fcb539efa

## Role-Agent Findings

Disposition: FIXED
Commit: d0daee249
Evidence: `bug-hunter` found that exact-string placeholder rejection would miss `Co-authored-by: PulsePlate Experiment Runner <runner@example.com>`. `scripts/orchestration/check_experiment_runner_identity.py` now rejects any `Co-authored-by: ... <runner@example.com>` guidance, and `tests/test_experiment_runner_identity_policy.py` covers the governed-name placeholder variant.

Disposition: NOT-A-BUG
Evidence: `security-auditor` required automatic email to remain explicit and fixed-recipient. `scripts/orchestration/experiment_pipeline.py` exposes only `--email-reports`, passes `--email --email-to pulseplate@pm.me` to `experiment_notify.py`, and exposes no arbitrary recipient flag.
Reason: This preserves the existing allowlist, SMTP secret, redaction, and audit boundaries owned by `experiment_notify.py`.

Disposition: NOT-A-BUG
Evidence: `architecture-specialist` required the wrapper not to become a second policy engine. `scripts/orchestration/experiment_pipeline.py` sequences `experiment_runner.main`, `experiment_promote.main`, and `experiment_notify.main` without reimplementing runner sandboxing, promotion policy, notification redaction, or identity policy.
Reason: The wrapper is orchestration-only and delegates stage-specific authority to existing governed modules.

Disposition: NOT-A-BUG
Evidence: `backend-engineer` and `qa-engineer-agent` found no blocking backend/test gaps after focused coverage for default no-email behavior, explicit email report behavior, sanitized SMTP failure, audit artifact hygiene, and identity guidance validation.
Reason: The changed behavior is covered by deterministic unit tests and does not add runtime app endpoints.

Disposition: FIXED
Commit: d0daee249
Evidence: `pulseplate-premortem-risk-review` identified placeholder guidance drift and hidden automatic email behavior as the two main failure modes. Placeholder drift is guarded by `check_experiment_runner_identity.py`; hidden email behavior is blocked by requiring explicit `experiment_pipeline.py --email-reports` and documenting that git attribution email is never a delivery trigger.

Disposition: NOT-A-BUG
Evidence: Codex Security diff-focused scan found no surviving reportable finding: the wrapper uses no shell/subprocess execution, delegates SMTP/redaction/audit to `experiment_notify.py`, suppresses child stdout leakage, does not accept arbitrary recipients, and returns sanitized stage failures.
Reason: The remaining sensitive behaviors are handled by existing tested notification and experiment modules.

## Bot Review Notes

Disposition: NOT-A-BUG
Evidence: CodeRabbit CLI agent review completed on the initial committed diff with `findings: 0`; GitHub CodeRabbit later reported two actionable comments, both fixed in `cd05b9a2d` and mapped above.
Reason: The CLI result is historical evidence only; GitHub CodeRabbit actionables are treated as fixed.

Disposition: NOT-A-BUG
Evidence: `chatgpt-codex-connector` PR comment reported Codex code-review usage limits only and did not identify code changes or review-thread actionables.
Reason: Usage-limit notification is operational, not a code finding.

Disposition: NOT-A-BUG
Evidence: Sourcery review comment reported weekly diff-character rate-limit exhaustion only and did not identify code changes or review-thread actionables.
Reason: Rate-limit notification is operational, not a code finding.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path ...` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `python3 scripts/orchestration/check_experiment_runner_identity.py --json` PASS.
- `pytest -q tests/test_experiment_pipeline.py tests/test_experiment_runner_identity_policy.py tests/test_experiment_notify.py tests/test_experiment_runner.py tests/test_experiment_promote.py` PASS.
- `pre-commit run --all-files` PASS.
- `make validate-changed` PASS.
- Pre-push hook PASS: mypy changed files, pip-audit, backend tests, full-repo bandit, and docker build test.

## Merge Readiness

- [ ] Current-head CI terminal and required checks passing after latest push.
- [ ] CodeRabbit no actionables after latest push.
- [ ] Cubic no actionables after latest push.
- [ ] Sourcery no actionables or rate-limit-only disposition recorded.
- [ ] Discussion-thread pass repeated after latest review activity.
- [ ] Fixed mapping artifact/body mirror updated after latest review activity.
- [ ] Strict merge-readiness wrapper passes.
- [ ] Required wait-window complete.
