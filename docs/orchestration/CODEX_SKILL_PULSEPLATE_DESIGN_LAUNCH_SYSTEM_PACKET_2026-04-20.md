# Codex Skill Wave 2A Packet — `pulseplate-design-launch-system`

**Version:** 2026-04-20 (`America/New_York`)
**Branch:** `codex/pulseplate-design-launch-system`
**PR:** `#1482`
**Title:** `feat(codex-skills): add pulseplate design launch system skill`

## Summary

This packet is the branch-scoped contract for the first custom-skill PR after
`Skill routing wave 2`.

The PR is intentionally narrow:
- add the repo-tracked custom skill bundle
- expose the repo mirror/install contract for the new slug
- activate the skill as a governed conditional helper for design/media/launch
  asset tasks
- preserve passive discovery-only behavior
- include the minimum Frontend CI bootstrap fix required to keep the branch and
  `main` from inheriting the current `build-and-test` red state while this lane
  is open

This PR does **not** implement:
- `pulseplate-web-launch-site`
- `pulseplate-agent-product`
- product/runtime UI changes
- launch-site execution workflows
- design-tooling execution authority

## Scope

### IN
- `tools/codex_skills/pulseplate-design-launch-system/`
- repo mirror and installer/test alignment for the new slug
- routing/policy/docs alignment for the design/media/launch-assets lane
- one packet describing role order, boundaries, and validation
- the minimum Frontend CI dependency-bootstrap fix needed for this PR to stay
  green:
  - canonical `ci-lite` Python setup for frontend-controlled OpenAPI/token
    checks
  - path-filter alignment for the actual backend dependency/install surfaces that the
    workflow consumes

### OUT
- new frontend routes or launch pages
- new iOS/macOS/web runtime behavior
- Figma/Notion/Airweave/Penpot execution control
- any change that lets skills bypass `agent-coordinator` or `task_bootstrap.py`
- bundling `pulseplate-web-launch-site` or `pulseplate-agent-product` into this PR
- broad dependency refreshes or unrelated CI topology redesign

## Files

- `tools/codex_skills/pulseplate-design-launch-system/SKILL.md`
- `.agents/skills/pulseplate-design-launch-system`
- `tools/codex_skills/README.md`
- `docs/dev/CODEX_SKILLS.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `scripts/orchestration/skill_router.py`
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md`
- `.github/workflows/frontend-ci.yml`
- `tests/test_install_codex_skills.py`
- `tests/test_skill_router.py`
- `tests/test_python_supply_chain_controls.py`
- `docs/orchestration/CODEX_SKILL_PULSEPLATE_DESIGN_LAUNCH_SYSTEM_PACKET_2026-04-20.md`

## Role Order

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. `qa-engineer-agent`
5. post-open mandatory `qa-engineer-agent -> bug-hunter`

## Review Path

- `security-auditor` stays in the review path for this PR because the lane
  touches privileged orchestration surfaces under `scripts/orchestration/**`
  and `docs/orchestration/**`.

## Boundaries

- The new skill remains passive/discovery-only.
- It may shape readiness/governance for launch assets, but it must not become
  design execution authority.
- The Frontend CI fix is bootstrap-only and must not widen into a general
  dependency policy rewrite.
- Figma/code-native/tokens source precedence stays governed by
  `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`.
- `docs_only` routing must continue to strip this skill from generic
  documentation-only tasks.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pytest -q tests/test_install_codex_skills.py`
- `pytest -q tests/test_skill_router.py`
- `pytest -q tests/test_task_bootstrap.py`
- `pre-commit run --all-files`
- `make verify`

## DoD

- The new skill exists under `tools/codex_skills/pulseplate-design-launch-system/`
- The repo mirror exposes the same slug under `.agents/skills/`
- Skill docs preserve passive discovery-only boundaries and design-source
  precedence
- Routing exposes the skill as a conditional helper for governed
  design/media/launch-asset work
- `docs_only` envelope keeps the skill out of generic documentation routing
- `Frontend CI` uses the canonical lightweight backend bootstrap for
  OpenAPI/token checks and re-triggers when its real dependency/install surfaces
  change
- `pulseplate-web-launch-site` and `pulseplate-agent-product` remain untouched
- Review/governance artifacts can be added without revising this packet's scope
