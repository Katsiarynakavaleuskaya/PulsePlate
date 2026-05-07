# PR #1698 Fixed Mapping

## Summary

PR #1698 adds the Design Intelligence PR-7 design-agent workflow, design PR template, PR-7 packet, AGENTS.md pointer, docs guard test, and a tiny Makefile interpreter guard so design targets honor `DEV_PYTHON`.

Mapping is evidence after fix or decision, not a substitute for fixing docs/code/tests defects.

## Agent Orchestration

- Pre-open bootstrap packet: `2833673b8f23`
- Post-open bootstrap packet: `18c849419f54`
- Role order used:
  1. `agent-coordinator`
  2. `creative-designer`
  3. `frontend-engineer`
  4. `architecture-specialist`
  5. `security-auditor`
  6. `qa-engineer-agent`
  7. `bug-hunter`
  8. `data-scientist-agent`

## Premortem Findings

Disposition: FIXED
Commit: `2e4f6f166`
Evidence: `docs/orchestration/DESIGN_INTELLIGENCE_PR7_AGENT_WORKFLOW_PACKET_2026-05-06.md`
Reason: Added touched paths to the coordinator bootstrap route so scoped instructions are deterministic.

Disposition: FIXED
Commit: `2e4f6f166`
Evidence: `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`
Reason: Tightened full-local-verify wording so the workflow does not override root `AGENTS.md`; bounded checks are documented only as the operator-approved machine-heavy exception.

Disposition: FIXED
Commit: `741f6072c`
Evidence: `tests/test_design_agent_workflow_docs.py`
Reason: Fixed the docs guard test so it requires the safety phrase `Do not claim green main` without forbidding that same required phrase.

Disposition: FIXED
Commit: `2e4f6f166`, `d903f895f`
Evidence: `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md`, `.github/PULL_REQUEST_TEMPLATE/design.md`
Reason: Distinguished `/tokens` as token authoring truth from generated mirrors as derived runtime artifacts.

Disposition: FIXED
Commit: `d903f895f`
Evidence: `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md`, `.github/PULL_REQUEST_TEMPLATE/design.md`
Reason: Changed PR-body mirror heading to `### Fixed in Commit Mapping` to match repo governance.

Disposition: FIXED
Commit: `741f6072c`
Evidence: `Makefile`, `tests/test_design_agent_workflow_docs.py`
Reason: Made `design-guard` and `tokens-check` invoke `$(DEV_PYTHON)` for `scripts/design_guard.py`, then locked that policy with a docs/tooling guard test.

Disposition: FIXED
Commit: `41f5247d2`
Evidence: `requirements.txt`
Reason: Mandatory pre-push `pip-audit` blocked publication on `mako==1.3.11` and `python-multipart==0.0.26`; raised pinned floors to `mako==1.3.12` and `python-multipart==0.0.27` instead of bypassing hooks.

## Bug-Hunter Pass

Disposition: NOT-A-BUG
Evidence: `git diff --name-only origin/main..HEAD`
Reason: Diff is limited to workflow/template/docs/test, Makefile interpreter guard, and `requirements.txt` security-floor unblock. No `frontend/`, `ios/`, `app/`, `core/`, or `tokens/` paths changed.

Disposition: NOT-A-BUG
Evidence: `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md`, `.github/PULL_REQUEST_TEMPLATE/design.md`
Reason: Figma, Canva, Storybook, DESIGN.md, evidence packs, scorecards, and templates are process/evidence/reference layers only; no second source of truth is introduced.

Disposition: NOT-A-BUG
Evidence: `tests/test_design_agent_workflow_docs.py`
Reason: Required template sections, `.venv` policy, external-design authority boundaries, and Makefile `DEV_PYTHON` guard are covered by deterministic tests.

## Bounded Checks

- `.venv/bin/python scripts/orchestration/check_preflight.py` PASS
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py` PASS
- `.venv/bin/python scripts/design/generate_design_md.py --check` PASS
- `.venv/bin/python scripts/design/reference_manifest.py validate-dir docs/design/reference_manifest/examples` PASS
- `.venv/bin/python scripts/design/screen_evidence_pack.py validate-dir docs/design/screen_evidence/examples` PASS
- `.venv/bin/python scripts/design/design_scorecard.py validate-score docs/design/design_scorecard/examples/web_marketing.scorecard.sample.json` PASS
- `.venv/bin/python scripts/design/design_scorecard.py validate-score docs/design/design_scorecard/examples/ios_home.scorecard.sample.json` PASS
- `.venv/bin/python -m pytest -q tests/test_design_agent_workflow_docs.py` PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make design-guard` PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make tokens-check` PASS
- `PATH=.venv/bin:$PATH pre-commit run --all-files` PASS
- `PATH=.venv/bin:$PATH pre-commit run pip-audit --hook-stage pre-push --all-files` PASS
- Pre-push hooks during `git push` PASS

## Review Thread Mapping

No external CodeRabbit, Sourcery, Cubic, or human review threads were mapped at PR open time.

New actionable review comments must be added here with `FIXED`, `NOT-A-BUG`, or `DEFERRED` disposition before thread resolution.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Deferred / Follow-Ups

- PR-8 GEPA-compatible prompt/rubric evolution lane remains separate.
- App Store asset validation remains separate release/design asset guard lane.
- Live capture lanes remain separate unless explicitly scoped.
