# PR #1746 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1746
- Branch: `codex/fix-main-design-agent-workflow-kimi-contract`
- Base: `main`
- Evidence head at mapping creation: `c396702a4ad245869a366ebb2c4d7787acd56365`
- Note: later mapping-only commits may advance the branch head; use GitHub PR current-head checks for live merge-readiness truth.

## Scope

Fix the main `test-main` design-governance failure by aligning the Kimi evidence/reference contract across the design PR template, PR7/PR8 design-intelligence packets, and deterministic docs guard tests.

## Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Coordinator / Premortem / Agent Findings

- Coordinator scope lock: FIXED by `e264e9e129ed5b7c299a657f64125b4cab276280`
  - Evidence: `tests/test_design_agent_workflow_docs.py` asserts Kimi evidence wording in the workflow and template source-of-truth sections.
  - Evidence: `.github/PULL_REQUEST_TEMPLATE/design.md` keeps Kimi prototypes evidence/reference/process only.
- Architecture finding: FIXED by `e264e9e129ed5b7c299a657f64125b4cab276280`
  - Finding: GitHub design PR template omitted Kimi prototypes while the repo design PR template included them.
  - Evidence: `.github/PULL_REQUEST_TEMPLATE/design.md` source-of-truth paragraph includes Kimi prototypes as evidence/reference/process only.
  - Evidence: `tests/test_design_agent_workflow_docs.py` asserts the Kimi wording inside `## Source of truth` for both design PR templates.
- QA finding: FIXED by `e264e9e129ed5b7c299a657f64125b4cab276280`
  - Finding: Broad substring assertion could pass outside the `## Source of truth` section.
  - Evidence: `tests/test_design_agent_workflow_docs.py` adds `_section(...)` and checks the Kimi-inclusive wording inside the source-of-truth section.
- Bug-hunter finding: FIXED by `e264e9e129ed5b7c299a657f64125b4cab276280`
  - Finding: PR7/PR8 packets still contained stale `Figma, Canva, Storybook, external references` wording.
  - Evidence: `docs/orchestration/DESIGN_INTELLIGENCE_PR7_AGENT_WORKFLOW_PACKET_2026-05-06.md` and `docs/orchestration/DESIGN_INTELLIGENCE_PR8_GEPA_PACKET_2026-05-07.md` include Kimi prototypes in the evidence-layer wording.
  - Evidence: `tests/test_design_agent_workflow_docs.py` includes the PR8 packet in the combined guard and rejects the stale exact phrase.
- Premortem finding 1: FIXED by `e264e9e129ed5b7c299a657f64125b4cab276280`
  - Finding: Adjacent PR7/PR8 negative guardrails named Figma/Canva/Storybook but not Kimi.
  - Evidence: PR7 packet names Kimi prototype drift in bug-hunter review risk.
  - Evidence: PR8 packet blocks Kimi-generated code/layout/copy mutation and write paths.
  - Evidence: `tests/test_design_agent_workflow_docs.py` asserts `Kimi prototype drift` and `Kimi-generated code`.
- Premortem dangerous-failure scenario: NOT-A-BUG
  - Evidence: `docs/orchestration/DESIGN_AGENT_WORKFLOW.md` and `docs/orchestration/KIMI_PROTOTYPE_INTAKE_MODERNIZATION_BRIDGE_PROTOCOL.md` already prohibit treating Kimi evidence as product/runtime truth.
  - Reason: The scenario is already blocked by current repo contracts and reinforced by this PR.

### Review Threads

- CodeRabbit review https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1746#pullrequestreview-4281537842 -> `32c7fa884`
  - Disposition: FIXED
  - Evidence: `tests/test_design_agent_workflow_docs.py` now asserts all template headings before calling `_section(...)`.
- CodeRabbit review https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1746#pullrequestreview-4281596223 -> `fa4693fbb`
  - Disposition: FIXED
  - Evidence: this artifact now includes `## Discussion Thread Pass` with required checklist lines.
- Sourcery review https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1746#pullrequestreview-4281517715
  - Disposition: NOT-A-BUG
  - Evidence: Sourcery reported a weekly rate limit, not a code or governance defect.
- Cubic review https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1746#pullrequestreview-4281550117
  - Disposition: NOT-A-BUG
  - Evidence: Cubic reported "No issues found" across the first four changed files.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path tests/test_design_agent_workflow_docs.py --path docs/orchestration/DESIGN_AGENT_WORKFLOW.md --path .github/PULL_REQUEST_TEMPLATE/design.md --path docs/orchestration/DESIGN_INTELLIGENCE_PR7_AGENT_WORKFLOW_PACKET_2026-05-06.md --path docs/orchestration/DESIGN_INTELLIGENCE_PR8_GEPA_PACKET_2026-05-07.md` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `.venv/bin/python -m pytest -q tests/test_design_agent_workflow_docs.py` - PASS (`4 passed`)
- `.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py -k kimi` - PASS (`9 passed`)
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS (`No Python files changed`)
- `PATH=.venv/bin:$PATH pre-commit run --all-files` - PASS after black hook formatting
- `git push` pre-push hooks - PASS, including `backend tests (pytest, pre-push)` and `bandit (pre-push, full repo)`

## Current-Head CI

- PR current-head checks started for the pushed branch head; use GitHub PR current-head checks for live status.
- Merge readiness is not claimed while checks and review-bot signals are pending.
