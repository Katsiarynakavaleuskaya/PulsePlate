# PR 1813 Fixed in Commit Mapping

## PR

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1813

## Summary

PR #1813 defines the Experiment Runner Slack operator notification identity
boundary and closes the hard-gate ledger drift with a rollout packet. It does
not flip Experiment Runner Evidence required mode and does not grant runner
mutation access to `scripts/ci/**`.

## Scope

- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- `docs/orchestration/EXPERIMENT_RUNNER_EVIDENCE_REQUIRED_MODE_ROLLOUT_PACKET_2026-05-24.md`
- `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.json`
- `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `scripts/AGENTS.md`
- `scripts/orchestration/check_experiment_runner_identity.py`
- `scripts/orchestration/experiment_notify.py`
- `tests/test_experiment_notify.py`
- `tests/test_experiment_runner_identity_policy.py`
- `docs/review/PR_1813_FIXED_MAPPING.md`

## Split Justification

This PR crosses the 800 changed-line governance threshold because the Slack
notification boundary must land with its policy, validator, tests, and rollout
ledger in the same reviewable unit. Splitting the code from the identity policy
or tests would temporarily create either an undocumented notification surface or
an unenforced policy surface. The required-mode default flip and
`scripts/ci/**` runner-mutation threat model remain split into later PRs.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/0b8d52a11458.json`
Packet: `artifacts/orchestration/task_packets/4cf028281a2c.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Pre-open role order completed: `agent-coordinator -> cursor-specialist-agent -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> dev-operator`
- Post-open role order completed: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent -> security-auditor -> dev-operator`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Discussion Threads And Bot Comments

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1813#discussion_r3294816600 -> d19ee18de1d6d751dc150e1ed35e1346fd770e41
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1813#pullrequestreview-4352982294 -> d19ee18de1d6d751dc150e1ed35e1346fd770e41
Disposition: FIXED
Commit: d19ee18de1d6d751dc150e1ed35e1346fd770e41
Evidence: `scripts/orchestration/experiment_notify.py:1294` now catches
unexpected Slack transport exceptions, writes a failed audit, and re-raises a
sanitized `ExperimentSlackDeliveryError`; `tests/test_experiment_notify.py:811`
locks the regression so `send_in_progress` is not left behind and secrets/local
paths are not exposed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1813#issuecomment-4529033449
Disposition: NOT-A-BUG
Evidence: CodeRabbit reported account/rate-limit and organization-credit
unavailability, not a code finding. This PR used compensating Sourcery,
qa-engineer-agent, bug-hunter, security-auditor, dev-operator, premortem, and
local security review passes instead of counting CodeRabbit as completed review
evidence.

- Sourcery generated a review guide and one actionable review thread. The
actionable thread is mapped above; the guide is informational and requires no
separate code change.

- Cubic generated an informational PR summary. No action requested at this
artifact update.

## Role-Agent Findings

| Role | Finding | Disposition | Evidence |
| --- | --- | --- | --- |
| agent-coordinator | Startup authority must remain `check_preflight.py -> task_bootstrap.py -> agent-coordinator`; Experiment Runner joins after bootstrap only. | FIXED | Pre-open packet `0b8d52a11458`; post-open packet `4cf028281a2c`; PR body and this artifact preserve the order. |
| cursor-specialist-agent | Keep starter/orchestration authority unchanged and avoid making Experiment Runner the lane start authority. | FIXED | Diff only adds Slack boundary and identity/ledger updates; no startup authority replacement. |
| architecture-specialist | Slack operator notification must stay a narrow opt-in sink with no Git/review/merge authority. | FIXED | `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.md`; `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.json`; identity tests. |
| security-auditor | Slack token/channel data must stay runtime-only and redacted from audit artifacts. | FIXED | `scripts/orchestration/experiment_notify.py`; `tests/test_experiment_notify.py`; focused pytest and pre-commit security hooks passed. |
| qa-engineer-agent | Missing fixed mapping/PR body mirror, missing split justification, and worktree-local `.venv` wording blocked readiness. | FIXED | This artifact; PR body mirror updated to use the root venv path / `VENV_PYTHON` guidance; `## Split Justification` added. |
| qa-engineer-agent | Unexpected Slack transport exceptions left audit state stuck at `send_in_progress`. | FIXED | Commit `d19ee18de1d6d751dc150e1ed35e1346fd770e41`; regression test `test_slack_unexpected_transport_failure_marks_failed_audit`. |
| bug-hunter | Confirmed the Sourcery audit-stuck finding and PR-body/mapping false-red risks. | FIXED | Commit `d19ee18de1d6d751dc150e1ed35e1346fd770e41`; this mapping artifact and PR body mirror. |
| security-auditor post-fix | No remaining reportable security issue after the Slack transport failure fix. | FIXED | Security-auditor PASS after the fix; pre-commit Bandit changed-files and full pre-push Bandit passed. |
| dev-operator | Worktree had uncommitted post-open fix and missing mapping/body mirror; current-head CI was red on scope/body/readiness. | FIXED | Commit `d19ee18de1d6d751dc150e1ed35e1346fd770e41`; this artifact; PR body mirror update; PR-scoped gates rerun after mapping. |

## Premortem Risk Fix Matrix

| Risk ID | Failure mode | Fix or disposition | Evidence | Disposition |
| --- | --- | --- | --- | --- |
| PM-1813-001 | Slack notification becomes an implicit bot identity or review/merge authority. | Policy and docs define Slack as operator-notification-only. | Governed identity policy docs/JSON and identity tests. | FIXED |
| PM-1813-002 | Slack secrets, channel IDs, local paths, or message bodies leak into repo/audit artifacts. | Runtime-only token/allowlist; audit stores hashes/status only; redaction tests added. | `tests/test_experiment_notify.py`; detect-secrets and Bandit hooks passed. | FIXED |
| PM-1813-003 | A failed custom Slack transport permanently blocks future sends with `send_in_progress`. | Unexpected transport exceptions now mark audit `failed` and re-raise sanitized failure. | Commit `d19ee18de1d6d751dc150e1ed35e1346fd770e41`; focused pytest. | FIXED |
| PM-1813-004 | Ledger closeout is mistaken for required-mode default activation. | Rollout packet and ledger explicitly keep required-mode default flip deferred. | `docs/orchestration/EXPERIMENT_RUNNER_EVIDENCE_REQUIRED_MODE_ROLLOUT_PACKET_2026-05-24.md`; `docs/roadmap/BACKLOG_LEDGER.md`. | FIXED |
| PM-1813-005 | PR size/body governance stays red despite code fix. | Added split justification, fixed mapping, and PR body mirror. | This artifact and PR body. | FIXED |
| PM-1813-006 | CodeRabbit unavailability hides real review risk. | Compensating Sourcery, role-agent, premortem, security, QA, bug-hunter, and dev-operator passes were run/dispositioned. | Role-agent evidence above; CodeRabbit rate-limit comment mapped as NOT-A-BUG. | FIXED |

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-7856ccbc3612.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- `mutated_paths`: `[]`
- `promotion_ready`: `false`
- `contribution_kind`: `review_disposition`
- `coauthor_required`: `true`
- Co-author trailer present in commits `d798bcd6d9b3b8188c16fc8596cde7de9f770915` and `d19ee18de1d6d751dc150e1ed35e1346fd770e41`.

## Bounded Check Evidence

| Command | Result |
| --- | --- |
| `python3 scripts/orchestration/check_preflight.py --path <changed paths>` | PASS |
| `python3 scripts/orchestration/check_agent_consistency.py` | PASS |
| `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_experiment_notify.py tests/test_experiment_runner_identity_policy.py` | PASS |
| `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null --explicit-package-bases scripts/orchestration/experiment_notify.py scripts/orchestration/check_experiment_runner_identity.py tests/test_experiment_notify.py tests/test_experiment_runner_identity_policy.py` | PASS |
| `python3 scripts/orchestration/check_experiment_runner_identity.py` | PASS |
| `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH make validate-changed` | PASS |
| `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH pre-commit run --all-files` | PASS |
| `python3 scripts/ci/check_pr_body_phase2_gates.py --body "$(gh pr view 1813 --json body --jq .body)" --pr-number 1813 --commit-range origin/main..HEAD --experiment-runner-evidence-mode advisory` | PASS |
| `python3 scripts/ci/check_pr_size_governance.py --base-sha "$(git merge-base origin/main HEAD)" --head-sha HEAD --body "$(gh pr view 1813 --json body --jq .body)"` | PASS: split justification accepted for 1044 changed lines. |
| Pre-push hooks | PASS before PR open; rerun on push for the mapping commit. |

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1813#discussion_r3294816600 -> d19ee18de1d6d751dc150e1ed35e1346fd770e41
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1813#pullrequestreview-4352982294 -> d19ee18de1d6d751dc150e1ed35e1346fd770e41
Disposition: FIXED
Commit: d19ee18de1d6d751dc150e1ed35e1346fd770e41
Evidence: `scripts/orchestration/experiment_notify.py:1294`; `tests/test_experiment_notify.py:811`; focused pytest passed.

## Deferred / Follow-ups

- Experiment Runner Evidence required-mode default activation remains deferred to `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-experiment-runner-evidence-required-mode-activation`.
- Experiment Runner mutation access to `scripts/ci/**` remains a separate threat-model PR.

## Merge Readiness

- [ ] Current-head CI completed for this PR after the latest push.
- [ ] Phase2 PR body gate passed for this PR after the PR body mirror update.
- [ ] Strict merge-readiness wrapper passed after latest bot/review activity.
- [ ] No actionable bot comments remain.
- [ ] Mandatory wait window elapsed after latest bot/review activity.
