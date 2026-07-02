# PR #2067 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067

Branch: `codex/harden-privileged-surface-review-routing`

## Summary

This PR centralizes privileged-surface review matching in
`scripts/orchestration/bootstrap_sync_policy.py` and makes bootstrap, skill
routing, docs, and tests consume that shared contract.

## Scope

- Privileged prefixes and exact/root-style manifest patterns.
- Shared matcher for `task_bootstrap.py` security review and `skill_router.py`
  security skill reasons.
- Agent-facing docs and deterministic parity tests.
- Backlog closeout for the privileged workflow security-review requirement.

## Out Of Scope

No product runtime, OpenAPI, route registration, Docker remediation behavior,
BOLA, dependency upgrades, or GitHub workflow edits are included.

## Implementation Commit

- `b09ea4d9d` - centralizes the privileged-surface matcher, keeps
  `security-auditor` executable for matched surfaces, adds slash-boundary
  negative tests, and syncs agent-facing docs.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/7e4027b0a5dc.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/harden-privileged-surface-review-routing`
- Pre-open role order executed:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> bug-hunter ->
  cursor-specialist-agent -> architecture-specialist`

## Premortem Closure

Disposition: FIXED
Evidence: `scripts/orchestration/bootstrap_sync_policy.py` now prevents
root-style manifest globs from crossing `/`, and
`tests/test_bootstrap_sync_policy.py` plus `tests/test_skill_router.py` cover
nested/lookalike negative controls.

Disposition: FIXED
Evidence: `AGENTS.md`, `RUNBOOK_AGENT.md`,
`docs/orchestration/AGENT_ROUTING_GRAPH.md`, and
`docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` now point agent-facing
guidance at the shared matcher; `tests/test_skill_router.py` locks the
AGENTS/RUNBOOK sync note.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-b1cddccd9543.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-b1cddccd9543.json`
- Runner mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Oracles: focused pytest, ruff check, and `git diff --check`
- Contribution: material oracle review for PR-open/commit decision; commit
  includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Superseded local infra attempt:
  `artifacts/orchestration/experiments/results/exp-9a5a64cf0a45.json`
  rejected before oracle execution because this macOS host lacks Linux
  `unshare` for network-disabled sandboxing.

## Discussion Thread Pass

- [ ] Discussion-thread pass completed.
- [ ] Fixed in commit mapping completed.
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2067`.
- [x] Initial PR open: no GitHub review comments were resolved before mapping.
- [ ] Post-open `qa-engineer-agent` pass completed.
- [ ] Post-open `bug-hunter` pass completed.
- [ ] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Sourcery actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Cubic actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments at initial PR open.

Future actionable human, bot, role-agent, premortem, Experiment Runner, or
Codex Security findings must be added here with disposition evidence before
merge-readiness claims.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` passed with the existing
  private-index shape warning only.
- `python3 scripts/orchestration/check_agent_consistency.py` passed.
- Focused pytest passed with the repo-resolved interpreter:
  `. scripts/hooks/repo_python.sh; VENV_PYTHON="$(resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_bootstrap_sync_policy.py tests/test_task_bootstrap.py tests/test_skill_router.py`.
- Focused ruff passed with the repo-resolved interpreter:
  `. scripts/hooks/repo_python.sh; VENV_PYTHON="$(resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m ruff check scripts/orchestration/bootstrap_sync_policy.py scripts/orchestration/skill_router.py tests/test_bootstrap_sync_policy.py tests/test_task_bootstrap.py tests/test_skill_router.py`.
- `make validate-changed` passed after commit and selected the three changed
  test files.
- `pre-commit run --all-files` passed.
- Push pre-push hooks passed, including mypy changed files, pip-audit, backend
  tests, full-repo bandit, and docker build test.
