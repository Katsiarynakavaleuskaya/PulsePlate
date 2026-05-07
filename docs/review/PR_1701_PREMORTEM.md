# PR 1701 Premortem

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701
Branch: `codex/fix-codex-coordinator-start-bridge`
Mode: `post_open_review`

Coordinator packets:

- Pre-open: `artifacts/orchestration/task_packets/ee4461176b4f.json`
- Post-open review: `artifacts/orchestration/task_packets/18e3d610ff9c.json`

## Scope Reviewed

- `scripts/orchestration/render_codex_start_prompt.py`
- `scripts/orchestration/start_pr_lane.sh`
- `scripts/orchestration/local_session_bootstrap.sh`
- `docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md`
- `docs/dev/CODEX_SKILLS.md`
- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
- `tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md`
- `tests/test_render_codex_start_prompt.py`
- `tests/test_start_pr_lane.py`
- `tests/test_local_session_bootstrap.py`

## Role Order Used

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `backend-engineer` / orchestration implementer
5. `qa-engineer-agent`
6. `bug-hunter`
7. `pulseplate-premortem-risk-review` as passive risk skill with mandatory
   finding closure

## Frame

It is 48 hours after this PR merged. Codex raw sessions still skip
coordinator-first sequencing, or agents treat premortem findings as optional
because the skill is passive. We are looking backward to understand why.

## Findings And Dispositions

### P1: Codex bridge could be read as host auto-start

Disposition: FIXED
Commit: `e3c3c40bc4ed569288739e2f23ff2f58ebcd34be`
Evidence:

- `scripts/orchestration/render_codex_start_prompt.py` renders copy-paste
  guidance and does not mutate host config or execute session hooks.
- `docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md` and
  `docs/orchestration/AUTOMATION_READINESS_MATRIX.md` state the repo starter is
  explicit guidance, not raw-session auto-start.
- `tests/test_render_codex_start_prompt.py`, `tests/test_start_pr_lane.py`, and
  `tests/test_local_session_bootstrap.py` assert the prompt does not claim
  automatic host startup.

### P1: Premortem skill could be treated as ignorable advisory text

Disposition: FIXED
Commit: `e3c3c40bc4ed569288739e2f23ff2f58ebcd34be`
Evidence:

- `tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md` now states
  that advisory means no execution/merge authority, not permission to ignore
  findings.
- `docs/dev/CODEX_SKILLS.md` states every premortem finding must be fixed or
  formally dispositioned.
- `tests/test_render_codex_start_prompt.py` guards the closure wording.

### P1: PR opened before canonical mapping artifact existed

Disposition: FIXED
Commit: `034fafa64c9791af6d43aea0d5d0070768e399b1`
Evidence:

- `docs/review/PR_1701_FIXED_MAPPING.md` records the canonical
  `Discussion Thread Pass` and `Fixed in Commit Mapping` artifact.
- Local `check_pr_body_phase2_gates.py --body ...` passed after PR body mirror
  update, and the artifact now gives CI an artifact-first source of truth.

### P2: Role-agent/premortem evidence was not visible enough in repo-tracked form

Disposition: FIXED
Commit: `034fafa64c9791af6d43aea0d5d0070768e399b1`
Evidence:

- This artifact records the pre-open/post-open packets, role order, findings,
  and closure state in `docs/review/PR_1701_PREMORTEM.md`.
- `docs/review/PR_1701_FIXED_MAPPING.md` links this premortem artifact as the
  non-thread governance finding record.

### P2: `make validate-changed` did not classify new staged Python additions

Disposition: NOT-A-BUG
Evidence:

- The command exited 0 and reported no Python files changed in its branch-diff
  view.
- Focused pytest covered the new renderer/tests: `24 passed`.
- `pre-commit run --all-files` passed after black formatting.
- Push pre-push hooks passed, including changed-file mypy, pre-push pytest,
  full-repo bandit, and docker build test.

Reason: The changed-file helper behavior is a validation-signal limitation for
new staged files in this worktree, not a product or bridge defect in this PR.

## Residual Risks

- GitHub review bots can still add new findings after this artifact is written.
  Those findings must update `docs/review/PR_1701_FIXED_MAPPING.md` and this
  premortem if they are premortem/governance-relevant.
- This PR does not create Codex host startup hooks. It only makes the repo-side
  explicit bridge harder to miss once invoked.

## Decision

Proceed with changes. All premortem findings identified in this pass are fixed
or formally dispositioned; PR #1701 must remain not-merge-ready until current
head CI and post-open review comments are rechecked.
