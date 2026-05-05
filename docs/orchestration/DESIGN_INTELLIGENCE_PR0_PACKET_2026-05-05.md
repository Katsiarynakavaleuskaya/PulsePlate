<!-- markdownlint-disable MD013 -->
# Design Intelligence PR-0 Packet

**Date:** 2026-05-05
**Branch:** `docs/design-intelligence-wave-v1`
**PR title:** `docs(design): open reference-driven design intelligence wave for web and iOS`
**Task packet:** `artifacts/orchestration/task_packets/a105100eca33.json` (local, gitignored)
**Mode:** docs-only governance PR; open as a normal ready-for-review PR after local narrow gates pass

## Summary

PR-0 starts the PulsePlate design intelligence wave with repo-first governance for external UI/UX references, Figma read-only evidence, Storybook review evidence, future DESIGN.md generation, and deterministic scoring.

This PR is not a redesign. It creates the rules future PRs must follow before any automation or implementation can use external references.

## Goal

Create the canonical packet and contracts that let future PulsePlate agents compare web/iOS surfaces against strong real-world references without creating a second source of truth.

## Business Reason

PulsePlate needs a governed design-intelligence layer to improve conversion, activation, trust, premium perception, and cross-platform coherence while preserving wellness-only safety, App Store readiness, accessibility, legal safety, and thin-client architecture.

## Scope

- Add `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`.
- Add this PR-0 packet.
- Add `docs/design/REFERENCE_MANIFEST_SCHEMA.md`.
- Add `docs/design/REFERENCE_SCORECARD.md`.
- Add `docs/design/PULSEPLATE_DESIGN_MD_BOOTSTRAP.md`.
- Add backlog anchor `ledger-p1-design-intelligence-wave`.
- Record AGENTS.md update proposal without mutating root `AGENTS.md` in PR-0.
- Execute premortem controls inside the created docs.

## Out Of Scope

- Web redesign.
- iOS redesign.
- Figma writes.
- Prototype links.
- External assets, screenshots, brands, layouts, copy, or proprietary component import.
- Reference crawler.
- GEPA implementation.
- Semantic design scoring runtime.
- New frontend components.
- `/tokens` changes or token regeneration.
- Generated mirror edits.
- Storybook config changes.
- Backend, OpenAPI, billing, auth, compliance, StoreKit, App Store release, or deployment changes.

## Files Likely Touched

- `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`
- `docs/orchestration/DESIGN_INTELLIGENCE_PR0_PACKET_2026-05-05.md`
- `docs/design/REFERENCE_MANIFEST_SCHEMA.md`
- `docs/design/REFERENCE_SCORECARD.md`
- `docs/design/PULSEPLATE_DESIGN_MD_BOOTSTRAP.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_<N>_FIXED_MAPPING.md` after the PR number exists

## Tests

Required local narrow bundle:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open
markdownlint docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md \
  docs/orchestration/DESIGN_INTELLIGENCE_PR0_PACKET_2026-05-05.md \
  docs/design/REFERENCE_MANIFEST_SCHEMA.md \
  docs/design/REFERENCE_SCORECARD.md \
  docs/design/PULSEPLATE_DESIGN_MD_BOOTSTRAP.md
make design-guard
npm --prefix frontend run tokens:check
npm --prefix frontend run build-storybook
make validate-changed
git diff --name-only origin/main...HEAD | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$"
git diff -- frontend/src/styles/tokens.css frontend/src/styles/tokens.ts ios/PulsePlate/DesignSystem/DesignTokens.generated.swift
pre-commit run --all-files
git status --short
```

Full local `make verify` must not be run for this PR by operator machine-budget decision because the full suite is too heavy for this machine. This PR must not claim merge readiness from local narrow gates alone.

## Security Notes

- No secrets, credentials, tokens, external service integrations, auth, billing, deployment, backend, or App Store release code changes.
- External references are treated as untrusted read-only inputs.
- Legal/copyright risk is captured in manifest fields and scorecard axes before any future implementation brief.
- Wellness-only boundaries remain mandatory; no medical diagnosis, treatment, therapy, crisis-support, or emergency-care claims.

## Rollback / Risks

Rollback is a docs-only revert of this PR. No runtime, generated token mirror, Figma, external asset, backend, iOS, deployment, billing, or auth rollback is required.

Primary risks are handled in the premortem table and promoted into controls in the runbook, schema, scorecard, DESIGN.md bootstrap, and backlog entry.

## DoD

- PR-0 runbook exists.
- PR-0 packet exists.
- External reference policy exists.
- Reference manifest schema exists.
- Reference scorecard exists.
- DESIGN.md bootstrap exists.
- Backlog anchor exists and is not marked closed before merge.
- AGENTS.md update proposal is included in this packet.
- Premortem controls are implemented in the docs, not only listed.
- No runtime UI mutation.
- No Figma mutation.
- No generated token mirror diff.
- Normal PR opened after local narrow gates pass; not draft.

## Commit Breakdown

1. `docs(design): add design intelligence runbook`
2. `docs(design): add PR0 packet and external reference contracts`
3. `docs(roadmap): add design intelligence backlog anchor`
4. `docs(orchestration): add AGENTS update proposal and premortem evidence`

## Pre-Push Checklist

- [ ] `python3 scripts/orchestration/check_preflight.py`
- [ ] `python3 scripts/orchestration/check_agent_consistency.py`
- [ ] `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open`
- [ ] `markdownlint` on changed Markdown files
- [ ] `make design-guard`
- [ ] `npm --prefix frontend run tokens:check`
- [ ] `npm --prefix frontend run build-storybook`
- [ ] Remove `frontend/storybook-static/` if generated
- [ ] `make validate-changed`
- [ ] docs-only diff guard returns empty output
- [ ] generated token mirror diff check returns empty output
- [ ] `pre-commit run --all-files`
- [ ] `git status --short`

## Post-Merge Checklist

1. `git checkout main`
2. `git fetch --prune origin`
3. `git merge --ff-only origin/main`
4. Confirm PR state is `MERGED`.
5. Confirm `git rev-list --left-right --count HEAD...origin/main` is `0 0`.
6. Clean only this branch and PR-0 temp artifacts.
7. Inspect current-head `main` health before PR-1.

## Deferred / Follow-Ups

- PR-1: generate PulsePlate DESIGN.md from token and component contracts.
- PR-2: add external reference manifest and normalization tooling.
- PR-3: add screen evidence pack for web and iOS review surfaces.
- PR-4: add deterministic design scorecard checks.
- PR-5: align web launch shell to design intelligence brief.
- PR-6: add iOS design parity audit and bounded visual sync.
- PR-7: add design-agent workflow and PR template.
- PR-8: add GEPA-compatible prompt/rubric evolution lane.
