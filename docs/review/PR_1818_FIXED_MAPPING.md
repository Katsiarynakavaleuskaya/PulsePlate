# PR 1818 Fixed in Commit Mapping

## Summary

PR #1818 fixes requested-agent role ordering in the Qoder dispatch bridge and
adds an explicit post-bootstrap role-agent dispatch contract so
`task_bootstrap.py` packet creation cannot be mistaken for actual role-agent
execution.

## Scope

- `scripts/orchestration/qoder_dispatch_bridge.py`
- `scripts/orchestration/task_bootstrap.py`
- `scripts/orchestration/render_codex_start_prompt.py`
- `scripts/orchestration/start_pr_lane.sh`
- `tests/test_qoder_dispatch_bridge.py`
- `tests/test_task_bootstrap.py`
- `tests/test_render_codex_start_prompt.py`
- `tests/test_start_pr_lane.py`
- `tests/test_local_session_bootstrap.py`
- `.cursor/agents/agent-coordinator.md`
- `.cursor/agents/cursor-specialist-agent.md`
- `AGENTS.md`
- `docs/ENGINEERING_LESSONS.md`
- `docs/review/PR_1818_FIXED_MAPPING.md`

## Lane Start Provenance

- Preflight: `python3 scripts/orchestration/check_preflight.py` -> PASS
- Scoped preflight: `python3 scripts/orchestration/check_preflight.py --path ...` -> PASS
- Packet: `artifacts/orchestration/task_packets/00e986e4dde3.json`
- Bootstrap command: `python3 scripts/orchestration/task_bootstrap.py --goal "Close PR #1818 merge-readiness blockers for requested_agents role-order preservation without widening orchestration scope" --task-class Orchestration --pr-phase post_open_review --path scripts/orchestration/qoder_dispatch_bridge.py --path tests/test_qoder_dispatch_bridge.py --path docs/review/PR_1818_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter`
- Dispatch manifest command: `python3 scripts/orchestration/qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/00e986e4dde3.json --pretty`
- Dispatch order used: `agent-coordinator -> architecture-specialist -> security-auditor -> cursor-specialist-agent -> qa-engineer-agent -> bug-hunter`
- Role-agent passes completed: `agent-coordinator`, `architecture-specialist`, `cursor-specialist-agent`, `security-auditor`, `qa-engineer-agent`, `bug-hunter`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1818#discussion_r3294942611
Disposition: FIXED
Commit: 4b81482f4629e540a780e8e161c864b671425565
Evidence: `scripts/orchestration/qoder_dispatch_bridge.py:436` caps requested role occurrences by available packet slots; `scripts/orchestration/qoder_dispatch_bridge.py:457` preserves one mandatory first coordinator without adding a synthetic duplicate when a coordinator slot already exists; `tests/test_qoder_dispatch_bridge.py:335` verifies final manifest order also preserves explicit requested order.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1818#discussion_r3294942611 -> 4b81482f4629e540a780e8e161c864b671425565

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1818#discussion_r3294942613
Disposition: FIXED
Commit: 4b81482f4629e540a780e8e161c864b671425565
Evidence: `tests/test_qoder_dispatch_bridge.py` now has normal top-level spacing and `pre-commit run --all-files` passed after Black formatting.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1818#discussion_r3294942613 -> 4b81482f4629e540a780e8e161c864b671425565

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1818#discussion_r3294942615
Disposition: FIXED
Commit: 4b81482f4629e540a780e8e161c864b671425565
Evidence: `tests/test_qoder_dispatch_bridge.py:297` updates the requested-order assertion to the append contract where required non-requested roles remain appended, and `tests/test_qoder_dispatch_bridge.py:335` covers final manifest preservation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1818#discussion_r3294942615 -> 4b81482f4629e540a780e8e161c864b671425565

## Post-Open Agent Findings

| Role | Finding | Disposition | Evidence |
| --- | --- | --- | --- |
| agent-coordinator | PR must preserve coordinator-first startup and close the three Codex threads with code/test evidence before mapping. | FIXED | Commit `4b81482f4629e540a780e8e161c864b671425565`; this artifact maps all three threads. |
| architecture-specialist | Bootstrap packet creation must not be treated as role-agent execution; add a machine-readable role dispatch contract and prompt guidance. | FIXED | `scripts/orchestration/task_bootstrap.py:362`; `scripts/orchestration/render_codex_start_prompt.py:185`; `tests/test_task_bootstrap.py`; `tests/test_render_codex_start_prompt.py`. |
| cursor-specialist-agent | `start_pr_lane.sh` printed next steps outside the subshell and did not print the exact dispatch-manifest command. | FIXED | `scripts/orchestration/start_pr_lane.sh:425`; `scripts/orchestration/start_pr_lane.sh:429`; `tests/test_start_pr_lane.py`. |
| security-auditor | Avoid collapsing legitimate repeated coordinator packet slots; quote packet paths in copy-paste commands. | FIXED | `scripts/orchestration/qoder_dispatch_bridge.py:457`; `scripts/orchestration/render_codex_start_prompt.py:92`; `scripts/orchestration/start_pr_lane.sh:429`; focused pytest and `bash -n` passed. |
| qa-engineer-agent | Final manifest could move QA/bug-hunter behind explicit requested order; engineering lesson numbering duplicated. | FIXED | `scripts/orchestration/qoder_dispatch_bridge.py:943` disables tail normalization when JSON packet has explicit requested order; `tests/test_qoder_dispatch_bridge.py:335`; `docs/ENGINEERING_LESSONS.md` numbering corrected. |
| bug-hunter | Prompt role order and advisory labels could contradict the dispatch manifest; shell quoting needed unsafe-path coverage. | FIXED | `scripts/orchestration/render_codex_start_prompt.py:104`; `scripts/orchestration/render_codex_start_prompt.py:185`; `tests/test_render_codex_start_prompt.py:119`; `tests/test_render_codex_start_prompt.py:213`. |

## Premortem Risk Fix Matrix

| Risk ID | Failure mode | Disposition | Evidence |
| --- | --- | --- | --- |
| PM-1818-001 | Agents stop after `task_bootstrap.py`, leaving requested role passes unrun. | FIXED | `role_agent_dispatch_contract` in `scripts/orchestration/task_bootstrap.py:362`; prompt/launcher dispatch guidance in `scripts/orchestration/render_codex_start_prompt.py:185` and `scripts/orchestration/start_pr_lane.sh:429`. |
| PM-1818-002 | Requested-agent order is correct at parser level but false-green at final manifest level. | FIXED | `scripts/orchestration/qoder_dispatch_bridge.py:943`; `tests/test_qoder_dispatch_bridge.py:335`. |
| PM-1818-003 | Role-agent lesson is lost after this PR and future agents repeat the same bootstrap mistake. | FIXED | `AGENTS.md`; `.cursor/agents/agent-coordinator.md`; `.cursor/agents/cursor-specialist-agent.md`; `docs/ENGINEERING_LESSONS.md`. |
| PM-1818-004 | Packet paths with spaces or quotes generate unsafe copy-paste dispatch commands. | FIXED | `scripts/orchestration/render_codex_start_prompt.py:92`; `scripts/orchestration/start_pr_lane.sh:429`; `tests/test_render_codex_start_prompt.py:213`; `tests/test_start_pr_lane.py`. |
| PM-1818-005 | Mapping/body are updated before code fixes, creating invalid review disposition evidence. | FIXED | Code/test commit `4b81482f4629e540a780e8e161c864b671425565` exists before this mapping artifact. |

## Codex Security Diff Scan

- Scope: changed orchestration Python, shell prompt, tests, agent instructions, and governance docs.
- Threat model: no auth, billing, secrets, network, runtime product API, or data migration surface changed.
- Finding discovery: no new subprocess execution of untrusted input; added shell rendering uses `shlex.quote` for prompt copy-paste and Bash `%q` for lane starter output.
- Validation: `pre-commit run --all-files` passed, including Bandit on changed files and detect-secrets.
- Attack path analysis: no reportable path from PR input to command execution, secret exposure, auth bypass, or fail-open merge-readiness weakening.
- Disposition: NOT-A-BUG for security risk; no reportable security finding.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/pr1818-role-dispatch-oracle-full.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-7d9b0476fa50-v2.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- `mutated_paths`: `[]`
- `shared_tree_untouched`: `true`
- `contribution_kind`: `oracle_review`
- `coauthor_required`: `true`
- Co-author trailer present in commit `4b81482f4629e540a780e8e161c864b671425565`: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Diagnostic rejected artifacts:
  - `artifacts/orchestration/experiments/results/exp-f8042f7fd2c7.json`: rejected because the packet context omitted later doc/test surfaces.
  - `artifacts/orchestration/experiments/results/exp-7d9b0476fa50.json`: rejected because `VENV_PYTHON` was not exported for oracle Python commands.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path ...` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS: `OK: agent docs and files are consistent.`
- `pytest -q tests/test_qoder_dispatch_bridge.py tests/test_task_bootstrap.py tests/test_render_codex_start_prompt.py tests/test_start_pr_lane.py tests/test_local_session_bootstrap.py tests/test_native_subagent_bridge.py` -> PASS
- `flake8 scripts/orchestration/qoder_dispatch_bridge.py scripts/orchestration/render_codex_start_prompt.py scripts/orchestration/task_bootstrap.py tests/test_qoder_dispatch_bridge.py tests/test_render_codex_start_prompt.py tests/test_start_pr_lane.py tests/test_local_session_bootstrap.py tests/test_task_bootstrap.py tests/test_native_subagent_bridge.py` -> PASS
- `bash -n scripts/orchestration/start_pr_lane.sh scripts/orchestration/local_session_bootstrap.sh` -> PASS
- `make validate-changed` -> PASS
- `pre-commit run --all-files` -> PASS after Black reformatted `tests/test_render_codex_start_prompt.py`; rerun passed.
- Commit hooks -> PASS with `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH`.
- Full local `make verify`: deferred by operator-approved machine-heavy governance exception; use current-head CI parity before merge.

## Deferred / Follow-ups

- None.

## Merge Readiness

- [ ] PR body mirror refreshed from canonical mapping artifact.
- [x] Local PR-scoped gates passed: preflight, agent consistency, focused pytest, `make validate-changed`, `pre-commit run --all-files`, PR review dry-run, premortem closure, and diff-scoped security scan.
- [ ] Current-head CI passing with all required checks green and no pending jobs.
- [ ] Review-thread disposition guard with auth passed after latest bot/human activity.
- [ ] Strict merge-readiness wrapper with auth passed after latest bot/human activity.
- [ ] CodeRabbit, Sourcery, Cubic, and Codex comments checked and dispositioned.
- [ ] No actionable review threads remain unresolved.
- [ ] Mandatory wait window elapsed after latest bot/review activity.
