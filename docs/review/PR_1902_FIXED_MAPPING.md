# PR 1902 Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed at PR creation
- [x] Fixed in commit mapping completed for pre-open premortem findings

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1902 -> d775b58ad
  Disposition: FIXED
  Commit: d775b58ad
  Evidence: .cursor/agents/prompt-engineering-eval-agent.md
  Reason: Registered `prompt-engineering-eval-agent` as readonly advisory owner for prompt contracts, offline eval harnesses, SC-G3 false-hit observability, and LLM red-team matrices.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1902 -> d775b58ad
  Disposition: FIXED
  Commit: d775b58ad
  Evidence: .cursor/agents/project-planning-agent.md
  Reason: Registered `project-planning-agent` as readonly advisory owner for gate sequencing, milestone planning, risk registers, and OKR-to-backlog mapping without coordinator or merge-readiness authority.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1902 -> d775b58ad
  Disposition: FIXED
  Commit: d775b58ad
  Evidence: docs/orchestration/AGENT_NON_ROUTABLE_SPECIALISTS.md
  Reason: Both Phase 1 agents are non-routable specialists by default; `AGENT_ROUTING_GRAPH.md` was not modified.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1902 -> d775b58ad
  Disposition: FIXED
  Commit: d775b58ad
  Evidence: scripts/orchestration/native_subagent_bridge.py
  Reason: Both Phase 1 agents use advisory `ANALYSIS_PROFILE` bridge entries, not implementation/read-write profiles.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1902 -> d775b58ad
  Disposition: FIXED
  Commit: d775b58ad
  Evidence: scripts/orchestration/skill_router.py; docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md; tests/test_skill_router.py
  Reason: Requested-agent skill bundles are limited to docs/governance helper skills and have parity test coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1902 -> d775b58ad
  Disposition: FIXED
  Commit: d775b58ad
  Evidence: docs/roadmap/BACKLOG_LEDGER.md
  Reason: Phase 2 agents are deferred with Owner, Priority, Target PR, Reason, Links, and DoD.

## Premortem Finding Closure
- F1 registration drift: FIXED by synced registration surfaces and `check_agent_consistency.py` PASS.
- F2 bridge write authority: FIXED by `ANALYSIS_PROFILE` bridge entries and bridge tests PASS.
- F3 planning authority bleed: FIXED by `project-planning-agent` hard boundaries.
- F4 SC-G3/runtime widening: FIXED by `prompt-engineering-eval-agent` hard boundaries and no runtime files in diff.
- F5 empty/uncommitted diff: FIXED by pushed 14-file PR diff.
- F6 Phase 2 ledger: FIXED by four `BACKLOG_LEDGER.md` entries.
- F7 Sora prompt confusion: FIXED by explicit scope boundary in `prompt-engineering-eval-agent`.
- F8 graph promotion: FIXED by no `AGENT_ROUTING_GRAPH.md` edits and no-match check.
- F9 PR scope: NOT-A-BUG; 13 files, standard governance plus narrow orchestration.
- F10 skill over-empowerment: FIXED by docs/governance helper bundles only.

## Evidence
- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS: `OK: agent docs and files are consistent.`
- `python -m pytest -q tests/guards/test_agent_consistency_guard.py tests/test_agent_docs_registry_guard.py` PASS: 25 tests.
- `python -m pytest -q tests/test_native_subagent_bridge.py tests/test_skill_router.py` PASS: 153 tests.
- `python -m pytest -q tests/test_task_bootstrap.py -k "non_routable or graph_slot"` PASS: 4 tests.
- `make validate-min` PASS with explicit repo `VENV_PYTHON`.
- `pre-commit run --all-files` PASS.
- Experiment Runner oracle-only artifact `artifacts/orchestration/experiments/results/scientific_workforce_phase1_oracle.json` status `accepted`, 3 oracle exits `0`.
