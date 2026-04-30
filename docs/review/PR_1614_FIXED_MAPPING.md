# PR #1614 Fixed Mapping

## Scope

Hotfix PR to restore the `main` coverage floor after PR #1612 left the
Python 3.12 main CI coverage at `96.99%` against the required `97.00%` gate.

## Coordinator Start

- Goal: Restore main Python 3.12 coverage after PR #1612 merge without lowering gates.
- Task class: QA / CI.
- PR phase: pre_open.
- Local packet: `artifacts/orchestration/task_packets/67e0bfdb78a0.json` (not committed).

## Role Order

1. `agent-coordinator`
2. `qa-engineer-agent`
3. `backend-engineer`
4. `architecture-specialist`
5. `security-auditor`
6. `cursor-specialist-agent`
7. `bug-hunter`
8. `agent-coordinator`

## Local Evidence

- `f01cdc857` -> `tests/test_mcp_pulseplate_server_coverage.py`
  - Covers unsafe optional MCP text metadata rejection.
- `f01cdc857` -> `tests/test_product_varieties.py`
  - Covers `plant_based` alternative filtering requiring `VEG`.
- `f01cdc857` -> `tests/test_planner_engines_facades.py`
  - Covers invalid BMR gender rejection and core TDEE exception handling.
- `f01cdc857` -> `tests/test_knowledge_contracts.py`
  - Covers preservation of unrelated active knowledge records during supersession.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Status: CodeRabbit actionable review pass completed for current findings.
- Actionable review comments: fixed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 0036d66a0
Evidence: `tests/test_knowledge_contracts.py` now asserts the targeted fact is superseded and the winning fact remains active; `tests/test_product_varieties.py` now uses an explicitly typed `pytest.MonkeyPatch` test signature.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1614#pullrequestreview-4207906378 -> 0036d66a0

## Validation

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/activate && pytest tests/test_mcp_pulseplate_server_coverage.py tests/test_product_varieties.py tests/test_planner_engines_facades.py tests/test_knowledge_contracts.py -q` PASS (`190 passed`)
- `. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/activate && pytest tests/test_knowledge_contracts.py tests/test_product_varieties.py -q` PASS (`47 passed`)
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` PASS
- `PRE_COMMIT_HOME=/tmp/pulseplate-precommit-cache pre-commit run --all-files` PASS

## Merge Readiness

- Current-head CI is required before merge.
- `check_merge_ready.py --require-auth` is required before merge.
- CodeRabbit, Sourcery, and Cubic actionables must be mapped here if they appear.

## Out of Scope

- Coverage threshold changes.
- Workflow weakening.
- Production runtime behavior changes.
- Rollback of PR #1603 or PR #1612.
