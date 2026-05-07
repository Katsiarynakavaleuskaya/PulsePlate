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

### P1: Packet-mode role order could contradict coordinator-first

Disposition: FIXED
Commit: `4e6487ff1`
Evidence:

- `scripts/orchestration/render_codex_start_prompt.py` now forces
  `agent-coordinator` to the front of the rendered packet role order even when
  the native packet bridge lists another primary role.
- `tests/test_render_codex_start_prompt.py` covers a packet whose native primary
  is `backend-engineer` and advisory role is `agent-coordinator`.

### P2: Prompt fields could inject pasted Codex instructions through newlines

Disposition: FIXED
Commit: `4e6487ff1`
Evidence:

- `scripts/orchestration/render_codex_start_prompt.py` now renders packet and
  recipe values through prompt-safe single-line data escaping.
- `tests/test_render_codex_start_prompt.py` asserts newline-bearing goals and
  paths render as escaped data rather than new top-level instructions.

### P1: Dry-run prompt implied analyze preflight had already run

Disposition: FIXED
Commit: `4e6487ff1`
Evidence:

- `scripts/orchestration/render_codex_start_prompt.py` now accepts an explicit
  recipe preflight state and prints dry-run wording when preflight did not run.
- `scripts/orchestration/local_session_bootstrap.sh` passes `--preflight-ran`
  because that helper really runs analyze preflight.
- `tests/test_start_pr_lane.py` asserts dry-run output says preflight did not
  run and does not inherit the analyze-preflight helper wording.

### P1: Real packet execute path lacked regression coverage

Disposition: FIXED
Commit: `4e6487ff1`
Evidence:

- `tests/test_start_pr_lane.py` now exercises the non-dry-run path with stubbed
  git/preflight/bootstrap commands and asserts the emitted prompt is packet
  backed, includes `Authoritative bootstrap already ran`, `Task packet:`,
  `Role order:`, passive skills, and the `.venv` reminder.

### P2: Legacy no-argument helper prompt was unpinned

Disposition: FIXED
Commit: `4e6487ff1`
Evidence:

- `tests/test_local_session_bootstrap.py` now covers no-argument helper mode and
  asserts it prints a Codex-ready non-authoritative prompt with placeholder
  goal/class, `agent-coordinator` seed order, task packet absence, and `.venv`
  reminder.

### P2: Semantic malformed packet case lacked regression coverage

Disposition: FIXED
Commit: `4e6487ff1`
Evidence:

- `tests/test_render_codex_start_prompt.py` now covers syntactically valid
  non-object packet JSON (`[]`) and asserts the renderer fails closed without
  printing `Paste into Codex now:`.

### P2: Packet fallback role-order coverage could fail diff coverage

Disposition: FIXED
Commit: `83f0f69a7`
Evidence:

- `tests/test_render_codex_start_prompt.py` now covers packet rendering without
  `native_subagent_bridge`, using top-level `primary_agent`, `reviewer`, and
  `secondary_agents`.
- The same test file also covers the missing optional `secondary_agents` path so
  `_as_string_list` handles non-list packet values under regression coverage.

### P2: Fixed mapping artifact used stale draft lifecycle wording

Disposition: FIXED
Commit: `4e6487ff1`
Evidence:

- `docs/review/PR_1701_FIXED_MAPPING.md` now says role-agent/premortem findings
  require closure before merge readiness or merge, matching PR #1701's
  ready-for-review lifecycle state.

### P2: Packet bridge null role lists could crash prompt rendering

Disposition: FIXED
Commit: `b9895eb71425e6e534e0d63d477582022776653b`
Evidence:

- `scripts/orchestration/render_codex_start_prompt.py` now treats
  `native_subagent_bridge.secondary: null` and
  `native_subagent_bridge.advisory: null` as empty optional lists.
- `tests/test_render_codex_start_prompt.py` covers a packet with both optional
  bridge arrays set to null and asserts the prompt still renders
  coordinator-first role order plus `<none>` advisory roles.

### P3: Premortem skill-file regression test could report missing file as ERROR

Disposition: FIXED
Commit: `b9895eb71425e6e534e0d63d477582022776653b`
Evidence:

- `tests/test_render_codex_start_prompt.py` now catches `FileNotFoundError`
  around `tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md` and
  reports a descriptive `pytest.fail(...)` message with the expected path.

### P3: Fixed mapping evidence used short SHAs

Disposition: FIXED
Commit: `6270cb66bcfc4b440db09c0c88a4a08939c77cfd`
Evidence:

- `docs/review/PR_1701_FIXED_MAPPING.md` now uses 40-character commit SHAs for
  existing FIXED mappings instead of short SHA aliases.

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
