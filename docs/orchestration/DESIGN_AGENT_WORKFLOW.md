<!-- markdownlint-disable MD013 -->
# Design Agent Workflow

## Purpose

This workflow governs future design-impacting PulsePlate PRs after the Design Intelligence PR-0 through PR-6 evidence chain.

It is a process layer only. Repo code, tests, `/tokens` as token authoring truth, generated mirrors as derived runtime artifacts, UI vocabulary, backend/OpenAPI contracts, and implemented runtime components remain governed by repo truth.

Future design-epic PR prompts must follow `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` for clean worktree startup, actual-diff premortem execution, coordinator-expanded role order, post-open review chains, and fixed-mapping-after-fix governance.

## 1. Start Gate

Before edits, design-impacting PRs must:

- Sync from `main` with fetch plus fast-forward only.
- Verify `.venv/bin/python` is present and executable.
- Run `.venv/bin/python scripts/orchestration/check_preflight.py`.
- Run `.venv/bin/python scripts/orchestration/check_agent_consistency.py`.
- Run `.venv/bin/python scripts/orchestration/task_bootstrap.py` with `agent-coordinator` first and the PR phase set.
- Lock scope, touched paths, validation, rollback, and Definition of Done before implementation.

Do not claim green main, do not run final full main verification, and do not start a later design slice while the current one is unresolved.

## 2. Source Truth Inspection

Design agents must inspect repo truth before proposing changes:

- Root and scoped `AGENTS.md` files.
- `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`.
- `docs/design/DESIGN.md`, as non-canonical generated evidence.
- Token governance docs and generated mirrors.
- `docs/design/UI_COMPONENT_VOCABULARY.md` and `docs/design/ui_component_vocabulary.json`.
- Relevant screen evidence packs, reference manifests, scorecards, acceptance briefs, and parity audits.
- Actual web, iOS, backend, or tooling code before any implementation proposal.

Figma, Canva, Storybook, Kimi prototypes, external references, prompt outputs, generated briefs, evidence packs, scorecards, and design briefs are evidence/reference layers only and do not override repo truth.

Kimi prototype intake and modernization bridge work must follow `docs/orchestration/KIMI_PROTOTYPE_INTAKE_MODERNIZATION_BRIDGE_PROTOCOL.md`. Kimi page, Drive folder, and desktop code bundle artifacts remain read-only evidence; future modernization must normalize useful direction into repo vocabulary, component contracts, visual regression decisions, accessibility regression decisions, and token/runtime parity boundaries before web or iOS implementation.

## 3. Scope Classification

Classify each design-impacting PR before editing:

- `docs-only`: workflow, decision packet, audit, or acceptance brief.
- `tooling/docs/tests`: deterministic local tooling and tests.
- `web runtime`: bounded frontend code changes only.
- `iOS runtime`: bounded SwiftUI or DesignSystem code changes only.
- `release/assets`: release design asset guard lane.
- `research/prompt evolution`: prompt/rubric/eval lane with no runtime mutation.

The classification determines evidence, reviewers, and bounded checks. Do not mix runtime surfaces unless the packet explicitly scopes and proves the need.

## 4. Evidence Requirements

Use deterministic repo-local evidence:

- External references must use a reference manifest.
- Screen work must use a screen evidence pack.
- Evidence-quality review must use a design scorecard.
- Runtime visual changes should include before/after screenshots only when screenshots are explicitly scoped.
- Binary artifacts are forbidden unless a release asset lane explicitly allows them.

Sample evidence and scorecards prove metadata quality only. They are not live screenshot, simulator, App Store, or pixel-proof evidence.

## 5. Design Automation Module Classification

Design automation items are modules inside the existing Design Intelligence / Design Runtime system:

- Icon Asset Validator -> release/design asset guard module.
- Design Evidence Harvester -> PR-3 screen evidence pack module.
- Button / Component Drift Inspector -> PR-4 deterministic scorecard plus Storybook/vocabulary parity module.
- Marketing Asset Pack Compiler -> late GTM compiler over approved design/copy truth.
- Launch Copy Compliance Linter -> marketing/release copy guard aligned with wellness/compliance rules.

Do not create a standalone plugin architecture or a second source of truth.

PR-9 design-system automation opens the next docs-only web+iOS runtime parity lane. It is not an implementation slice. Future work must follow `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR9_DESIGN_SYSTEM_AUTOMATION_PACKET_2026-05-08.md` and this sequence before runtime work starts:

1. Component contract registry.
2. Bridge coverage inventory.
3. Visual regression decision gate.
4. Accessibility regression decision gate.
5. Token/runtime parity boundary.
6. Later web+iOS implementation slices.

PR-9 must not implement web runtime, iOS runtime, Storybook config, token mirrors, Figma writes, Canva writes, Penpot writes, screenshots, or Code Connect activation.

Kimi prototype modernization bridge -> docs/governance intake lane over Kimi page, Drive folder, and desktop code bundle evidence. It does not copy Kimi code, assets, layouts, copy, routes, or token values; it records provenance, source-of-truth boundaries, and the normalization sequence into component contracts, bridge coverage, visual/a11y gates, and later web+iOS slices.

## 6. Authority Boundaries

Hard boundaries:

- `/tokens` remains token authoring source of truth.
- Generated mirrors must not be edited by hand.
- Backend/OpenAPI remains product and runtime contract truth.
- Web and iOS clients remain thin presentation layers.
- Wellness copy must not become diagnosis, treatment, therapy, crisis-support, or emergency-care copy.
- Figma and Canva writes require separate explicit operator scope.

Design agents may recommend bounded changes only after repo evidence identifies a concrete gap.

## 7. Premortem And Bug-Hunter

Premortem must inspect the actual code/docs/tests diff, not just the mapping artifact.

Real premortem findings must be fixed in docs/code/tests before mapping. Mapping is evidence after fix or decision; it is not the fix.

Bug-hunter must inspect the actual diff for:

- source-of-truth drift,
- generated mirror edits,
- runtime drift outside scope,
- unsupported wellness claims,
- hidden binary artifacts,
- missing bounded checks,
- stale or duplicate prior Design Intelligence work.

For PR-9 design-system automation, every declared role agent and required skill pass must leave an execution record or pass/finding note. Before merge readiness, the local Agent Run Summary must exist under `artifacts/agent_runs/` or the PR body/fixed mapping must record why host-local summary generation was unavailable. These artifacts are local evidence only and must not be committed.

## 8. Review Mapping

After the PR number exists, create `docs/review/PR_<N>_FIXED_MAPPING.md`.

Map CodeRabbit, Sourcery, Cubic, Codex, and human review comments as:

- `FIXED`: commit SHA plus evidence.
- `NOT-A-BUG`: evidence plus rationale.
- `DEFERRED`: backlog link plus rationale.

Do not resolve review threads without explicit disposition evidence. Do not update mapping before fixing the underlying issue.

## 9. Merge Readiness

Design-impacting PRs use bounded local checks and current-head PR checks.

The command bundle below is general merge-readiness evidence for design-impacting PRs. Generated future design-epic PR prompts use the narrower bounded prompt bundle in `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` unless a coordinator packet explicitly supersedes it.

Use `.venv/bin/python` for repo Python commands and:

```bash
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make design-guard
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make tokens-check
PATH=.venv/bin:$PATH pre-commit run --all-files
```

Do not override the root `AGENTS.md` merge gate. If an operator-approved machine-heavy design lane uses bounded local checks instead of full local `make verify`, document that exception in the PR body and fixed mapping artifact.

Before merge, run the strict wrapper:

```bash
GH_TOKEN=$(gh auth token) GITHUB_TOKEN=$(gh auth token) \
.venv/bin/python scripts/orchestration/check_merge_ready.py \
  --pr-number <PR_NUMBER> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```

After merge, sync local `main` with fetch plus fast-forward merge, then inspect current-head health for `main` before starting the next PR.
Do not treat this as a requirement to run a full local `make verify` on `main` unless separately required by the lane.
