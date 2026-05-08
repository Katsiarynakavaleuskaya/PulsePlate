<!-- markdownlint-disable MD013 -->
# Design PR Template

Use this template for design-impacting PRs. It is a repo-governed process layer and does not make design evidence canonical.

For future design-epic PR prompts, apply `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` before filling this template.

## Summary

Describe the design-impacting change and the surface it governs.

## Goal

State the concrete outcome and how success is measured.

## Business reason

Explain why this design work matters for launch quality, trust, retention, revenue, automation, or operational leverage.

## Scope

- Include only the docs, tooling, tests, or runtime surfaces explicitly owned by this PR.
- State whether the PR is docs-only, tooling/docs/tests, web runtime, iOS runtime, release/assets, or research/prompt evolution.

## Out of scope

- No broad redesign unless explicitly scoped.
- No Figma/Canva writes unless explicitly scoped.
- No manual edits to generated token mirrors; generated mirror diffs are allowed only when produced by canonical tooling and explicitly scoped to reflect `/tokens` changes.
- No backend/OpenAPI/product truth movement into clients.
- No screenshots, videos, traces, or binary artifacts unless explicitly scoped.

## Source of truth

Repo code/docs/tests, `/tokens` as token authoring truth, generated mirrors as derived runtime artifacts, UI vocabulary, backend/OpenAPI contracts, and runtime code remain governed by repo truth.

DESIGN.md, evidence packs, scorecards, Figma, Canva, Storybook, external references, generated briefs, and this template are evidence/reference/process layers only.

## Design automation module classification

Classify the work:

- Icon Asset Validator -> release/design asset guard module.
- Design Evidence Harvester -> PR-3 screen evidence pack module.
- Button / Component Drift Inspector -> PR-4 deterministic scorecard plus Storybook/vocabulary parity module.
- Marketing Asset Pack Compiler -> late GTM compiler over approved design/copy truth.
- Launch Copy Compliance Linter -> marketing/release copy guard aligned with wellness/compliance rules.
- PR-9 Design-System Automation -> docs-only web+iOS runtime parity lane that requires component contract registry, bridge coverage inventory, visual regression decision, accessibility regression decision, token/runtime parity boundary, and later implementation slices in that order.

For PR-9 Design-System Automation, state explicitly that the PR does not implement web runtime, iOS runtime, Storybook config, token mirrors, Figma/Canva/Penpot writes, screenshots, or Code Connect activation.

## Files changed

List the files changed after implementation.

## Tests / bounded checks

Do not override the root `AGENTS.md` merge gate. If this is an operator-approved machine-heavy design lane using bounded local checks, document the exception and list only commands actually run.

Use repo `.venv`:

- `.venv/bin/python scripts/orchestration/check_preflight.py`
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py`
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed`
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make design-guard`
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make tokens-check`
- `PATH=.venv/bin:$PATH pre-commit run --all-files`

Add targeted evidence/tooling/runtime checks for touched surfaces only. Generated future design-epic PR prompts use the narrower prompt bundle in `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` unless a coordinator packet explicitly supersedes it.

## Security notes

State whether the PR touches secrets, auth, billing, backend, deploy, external integrations, Figma, Canva, screenshots, binary artifacts, or product truth.

## Premortem

Premortem must review the actual docs/code/tests diff. Real findings must be fixed before mapping.

Mapping is evidence after fix or decision; mapping is not the fix.

For future design-epic PR prompts, premortem runs before PR opening and again after the first bot-review cycle.

For PR-9 Design-System Automation, record the pre-open role-agent execution notes and required skill passes before opening the PR.

## Bug-hunter pass

Confirm no second source of truth, no manual generated mirror edits, no runtime drift outside scope, no unsupported wellness claims, and no hidden binary artifacts.

For future design-epic PR prompts, post-open review must include `qa-engineer-agent`, `bug-hunter`, `security-auditor`, and Codex Security. After the first bot review, repeat `agent-coordinator`, `qa-engineer-agent`, `bug-hunter`, `security-auditor`, and premortem on the updated diff.

## Deferred / Follow-ups

List follow-ups with backlog links or state `None`.

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping

See `docs/review/PR_<N>_FIXED_MAPPING.md`.

## Merge Readiness

Do not mark until current-head PR checks, review dispositions, mapping, wait-window, and strict merge-readiness wrapper pass.

Do not claim green main from this PR.

For PR-9 Design-System Automation, also confirm the local Agent Run Summary exists under `artifacts/agent_runs/` or record why host-local summary generation was unavailable. Do not commit local agent-run artifacts.

## Rollback

Describe how to revert this PR. Docs/template PRs should require no runtime rollback.

## DoD

- Workflow/template obligations satisfied.
- Source-of-truth boundaries preserved.
- Required bounded checks pass.
- No manual generated mirror edits; any generated mirror diff is tool-produced from `/tokens` and explicitly scoped.
- No runtime drift outside scope.
