<!-- markdownlint-disable MD013 -->
# Design Agent Workflow

## Purpose

This workflow governs future design-impacting PulsePlate PRs after the Design Intelligence PR-0 through PR-6 evidence chain.

It is a process layer only. Repo code, tests, `/tokens` as token authoring truth, generated mirrors as derived runtime artifacts, UI vocabulary, backend/OpenAPI contracts, and implemented runtime components remain governed by repo truth.

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

Figma, Canva, Storybook, external references, prompt outputs, generated briefs, evidence packs, scorecards, and design briefs are evidence/reference layers only and do not override repo truth.

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

## 8. Review Mapping

After the PR number exists, create `docs/review/PR_<N>_FIXED_MAPPING.md`.

Map CodeRabbit, Sourcery, Cubic, Codex, and human review comments as:

- `FIXED`: commit SHA plus evidence.
- `NOT-A-BUG`: evidence plus rationale.
- `DEFERRED`: backlog link plus rationale.

Do not resolve review threads without explicit disposition evidence. Do not update mapping before fixing the underlying issue.

## 9. Merge Readiness

Design-impacting PRs use bounded local checks and current-head PR checks.

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
