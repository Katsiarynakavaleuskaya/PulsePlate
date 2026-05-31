# PR 1860 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Pre-Open Finding Disposition Evidence

Disposition: FIXED
Commit: 8e609f6c3
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` marks PR #1853 as landed, selects
the Guided Planning MVP roadcut quality pass, keeps root-artifact hygiene as a
separate deferred follow-up, and records the Cursor role-agent readonly scope
expansion.

Disposition: FIXED
Commit: 40103101a
Evidence: `scripts/orchestration/role_dispatch_bridge.py` is the neutral
canonical role-dispatch CLI; `scripts/orchestration/qoder_dispatch_bridge.py`
remains a compatibility facade, disables parallel role execution in the
manifest, and keeps `mandatory_post_open` role-only while adding
`mandatory_post_open_gates` for Codex Security and `pulseplate-pr-review`.

Disposition: FIXED
Commit: 40103101a
Evidence: `scripts/orchestration/check_preflight.py` now fails closed when the
canonical `role_dispatch_bridge.py` is missing or import-broken while keeping
the historical `qoder_dispatch_bridge.py` compatibility smoke non-authoritative.

Disposition: FIXED
Commit: 40103101a
Evidence: `AGENTS.md`, `RUNBOOK_AGENT.md`,
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`,
`docs/orchestration/workflow.md`,
`docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md`, scoped agent docs,
and `docs/ENGINEERING_LESSONS.md` now state that bootstrap-requested custom
roles, premortem, Experiment Runner, Codex Security, and `pulseplate-pr-review`
are mandatory gates for non-trivial PRs.

## Premortem Evidence

`pulseplate-premortem-risk-review` ran against the actual diff.

Findings:
- FIXED: fail-open preflight bridge smoke for the now-mandatory
  `role_dispatch_bridge.py`.
- FIXED: `mandatory_post_open` mixed role and non-role gates; restored
  role-only compatibility and added `mandatory_post_open_gates`.
- FIXED: stale canonical `qoder_dispatch_bridge.py --packet` command surfaces
  in active prompt/runbook/test docs.
- FIXED: Experiment Runner actual-diff context initially missed the new
  untracked bridge file; resolved with intent-to-add before final oracle
  evidence.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-6d219c737a46.json`

Summary: accepted oracle-only governance review, `mutated_paths=[]`,
`shared_tree_untouched=true`, oracle commands passed, and
`coauthor_required=true`.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/1b91068a179d.json`

Role dispatch:
`scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/1b91068a179d.json --pretty`

Pre-open role order executed:
`agent-coordinator -> architecture-specialist -> frontend-engineer -> cursor-specialist-agent -> security-auditor -> qa-engineer-agent -> bug-hunter`

## Validation Evidence

- `python scripts/orchestration/check_preflight.py --mode analyze --path ...` - PASS
- `python scripts/orchestration/check_agent_consistency.py` - PASS
- `python -m pytest -q tests/test_qoder_dispatch_bridge.py tests/test_task_bootstrap.py tests/test_orchestration_preflight.py tests/test_local_session_bootstrap.py tests/test_render_codex_start_prompt.py tests/test_start_pr_lane.py tests/test_experiment_pipeline.py tests/test_philosophy_alignment_ledger_closeout.py` - PASS
- `make validate-changed` - PASS
- `pre-commit run --all-files` - PASS
- pre-push hooks - PASS
- Experiment Runner oracle-only review `exp-6d219c737a46` - accepted

## Agent Findings Summary

| Finding | Role | Disposition | Evidence |
| --- | --- | --- | --- |
| Manifest advertised parallel execution despite mandatory sequence | agent-coordinator | FIXED | `scripts/orchestration/qoder_dispatch_bridge.py`, `tests/test_qoder_dispatch_bridge.py` |
| Neutral bridge help still exposed old adapter name | agent-coordinator | FIXED | `role_dispatch_bridge.py --help`, `tests/test_qoder_dispatch_bridge.py` |
| Post-open gate list was ambiguous | agent-coordinator / security-auditor | FIXED | `mandatory_post_open` remains role-only; `mandatory_post_open_gates` adds full gates |
| Active agent prompt surfaces still named old bridge | architecture-specialist | FIXED | `.cursor/agents/agent-coordinator.md`, `.cursor/agents/cursor-specialist-agent.md` |
| Non-routable specialist docs sounded optional | architecture-specialist | FIXED | `docs/orchestration/AGENT_NON_ROUTABLE_SPECIALISTS.md` |
| Local session bootstrap test expected old bridge | architecture-specialist | FIXED | `tests/test_local_session_bootstrap.py` |
| Preflight smoke failed open for canonical bridge | security-auditor | FIXED | `scripts/orchestration/check_preflight.py`, `tests/test_orchestration_preflight.py` |
| Mixed `mandatory_post_open` compatibility field | security-auditor | FIXED | `scripts/orchestration/qoder_dispatch_bridge.py`, `tests/test_philosophy_alignment_ledger_closeout.py` |
| Active backlog DoD still named old bridge command | security-auditor | FIXED | `docs/roadmap/BACKLOG_LEDGER.md` |

## Post-Open Finding Disposition Evidence

Disposition: FIXED
Commit: 528a8a748
Evidence: `docs/review/PR_1860_FIXED_MAPPING.md` now uses the exact Phase2
checkbox labels and keeps `- No actionable review comments` as the only
canonical fixed-mapping entry while no GitHub review threads exist. Local
validation passed with
`python scripts/ci/check_pr_body_phase2_gates.py --pr-number 1860 --body "$(gh pr view 1860 --json body --jq .body)" --commit-range origin/main..HEAD --experiment-runner-evidence-mode required`.
Role: `qa-engineer-agent`
Reason: The post-open QA pass correctly found that GitHub still pointed at the
previous head where the artifact mixed detail lines with the no-actionable
marker and used non-canonical checkbox wording. The fix commit existed locally
before the QA pass and is being mapped before push.

Disposition: FIXED
Commit: f3131376d869b70b7d9beb56ef2ee753f3b77ba5
Evidence: `scripts/orchestration/qoder_dispatch_bridge.py` disables
mandatory post-open tail normalization for the public explicit `--roles`
fallback path, while packet-based post-open normalization remains governed by
packet phase/order metadata. `tests/test_qoder_dispatch_bridge.py` covers the
operator pre-open order
`agent-coordinator -> architecture-specialist -> frontend-engineer -> cursor-specialist-agent -> security-auditor -> qa-engineer-agent -> bug-hunter`.
Validation passed with
`python -m pytest -q tests/test_qoder_dispatch_bridge.py`,
`role_dispatch_bridge.py --roles ... --pretty`, and
`role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/1b91068a179d.json --pretty`.
Role: `bug-hunter`
Reason: The post-open bug-hunter pass found that explicit fallback dispatch
could silently move `security-auditor` after QA/bug, contradicting the
declared operator pre-open order.

Disposition: FIXED
Commit: 35176844d7004c5586db0261b56f08b800000e11
Evidence: `docs/orchestration/AGENTS.md` now states that repo-global
post-open review gates supersede historical scoped shorthand and updates scoped
lane bullets to reference those gates. `docs/ENGINEERING_LESSONS.md` records
that scoped `AGENTS.md` files must not narrow the global post-open gate and
that explicit `--roles` fallback dispatch must preserve declared order.
`docs/review/PR_1860_FIXED_MAPPING.md` now records Phase2 validation in
required Experiment Runner evidence mode. Validation passed with
`rg -n "mandatory post-open lane: .*qa-engineer-agent -> bug-hunter" docs/orchestration/AGENTS.md`
returning no matches,
`python scripts/orchestration/check_agent_consistency.py`, and
`python scripts/ci/check_pr_body_phase2_gates.py --pr-number 1860 --body "$(gh pr view 1860 --json body --jq .body)" --commit-range origin/main..HEAD --experiment-runner-evidence-mode required`.
Role: `security-auditor`
Reason: The post-open security-auditor pass found scoped orchestration rules
that could narrow current mandatory post-open gates, plus advisory-mode
evidence wording inconsistent with the mandatory Experiment Runner gate.

## Post-Open Review Tracking

- [x] `qa-engineer-agent` post-open pass - BLOCK finding fixed by `528a8a748`
- [x] `bug-hunter` post-open pass - BLOCK finding fixed by `f3131376d`
- [x] `security-auditor` post-open pass - BLOCK findings fixed by `35176844`
- [ ] Codex Security diff scan / finding discovery
- [ ] `pulseplate-pr-review`
- [ ] Bot/human review thread disposition pass

## Merge Readiness

- [x] Pre-open agents completed in declared order
- [x] Premortem findings fixed/dispositioned
- [x] Experiment Runner oracle-only review accepted
- [x] `make validate-changed` passed
- [x] `pre-commit run --all-files` passed
- [x] pre-push hooks passed
- [ ] Post-open review sequence completed
- [ ] Current-head CI checked
- [ ] Bot/human review comments dispositioned
- [ ] Strict merge-readiness wrapper passed

No merge-readiness claim is made by this artifact.
