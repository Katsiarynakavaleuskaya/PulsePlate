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

Shared controls live in `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`: source-of-truth hierarchy, forbidden actions, validation bundle, promotion rules, and premortem controls. This packet records the PR-specific plan and evidence and should not fork those shared controls.

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
python3 -m pytest -q --confcutdir=tests/guards tests/guards/test_wellness_language_blockers_guard.py
python3 -m pytest -q --noconftest tests/test_philosophy_validator.py
markdownlint docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md \
  docs/orchestration/DESIGN_INTELLIGENCE_PR0_PACKET_2026-05-05.md \
  docs/design/REFERENCE_MANIFEST_SCHEMA.md \
  docs/design/REFERENCE_SCORECARD.md \
  docs/design/PULSEPLATE_DESIGN_MD_BOOTSTRAP.md
make design-guard
npm --prefix frontend run tokens:check
npm --prefix frontend run build-storybook
make validate-changed
non_docs="$(git diff --name-only origin/main...HEAD | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$" || true)"
test -z "$non_docs"
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
- [ ] `python3 -m pytest -q --confcutdir=tests/guards tests/guards/test_wellness_language_blockers_guard.py`
- [ ] `python3 -m pytest -q --noconftest tests/test_philosophy_validator.py`
- [ ] `markdownlint` on changed Markdown files
- [ ] `make design-guard`
- [ ] `npm --prefix frontend run tokens:check`
- [ ] `npm --prefix frontend run build-storybook`
- [ ] Remove `frontend/storybook-static/` if generated
- [ ] `make validate-changed`
- [ ] docs-only diff guard exits `0` only when the non-docs offender list is empty
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

## AGENTS.md Update Proposal

Root `AGENTS.md` is not changed in PR-0 because `docs/orchestration/AGENTS.md` says initiative-specific routing should stay scoped to orchestration docs. If PR-1 or a later workflow PR promotes this pattern globally, use this exact proposed section:

```markdown
## Design Intelligence PRs

For reference-driven design intelligence lanes:
- Start with `check_preflight.py`, `task_bootstrap.py`, and coordinator routing.
- Keep repo code/docs/tests, `/tokens`, UI vocabulary, and generated runtime mirrors as the source-of-truth chain.
- Treat Figma as design-intent evidence only and Storybook as review/documentation only.
- Treat external UI/UX references as read-only inputs; normalize into PulsePlate vocabulary before implementation.
- Do not copy external assets, brands, screenshots, layouts, proprietary components, copy, or visual identity.
- DESIGN.md, when introduced, must be generated or drift-checked from repo token/component truth and must not become a manual second SoT.
- Future implementation PRs require screenshot, Storybook, accessibility, and platform evidence and must stay thin-client-safe unless explicitly scoped otherwise.
```

## Premortem

The premortem is executed as binding controls across this PR, not only recorded here.

| Risk | Failure mode | Impact | Early warning | Mitigation | Owner | Rollback |
| --- | --- | --- | --- | --- | --- | --- |
| External references become shadow SoT | Agents cite reference corpus as authority over repo tokens/components | Token drift and incoherent UI direction | Briefs say "match reference" without repo mapping | Runbook source precedence and promotion rules require repo normalization first | agent-coordinator | Revert reference policy docs and block future reference PR |
| Agents copy external designs | External layout, brand, asset, or component implementation enters repo | Copyright/licensing risk and brand dilution | Manifest lacks forbidden-copy details | Schema requires `forbidden_copy_elements`, license status, normalization notes, mapped components | creative-designer / security-auditor | Revert copied material and mark source rejected |
| DESIGN.md drifts from `/tokens` | Manual DESIGN.md becomes stale or conflicts with generated mirrors | Second design SoT | DESIGN.md edited without token/component evidence | DESIGN.md bootstrap requires generated or drift-checked output from `/tokens` and vocabulary | architecture-specialist | Revert DESIGN.md changes and require generator/checker PR |
| Figma becomes runtime authority | Figma pages override repo implementation truth | Runtime/client drift | PR cites Figma as product truth | Figma role is read-only design-intent only; promotion requires repo PR | agent-coordinator | Revert Figma-derived claims |
| Storybook becomes authoring authority | Storybook stories author tokens/layouts | Review lane becomes hidden runtime | Storybook-only state appears in implementation brief | Storybook role is review/documentation only | frontend-engineer | Revert Storybook-derived authoring claims |
| Web polish mutates business logic | Later design PR changes API, auth, billing, nutrition, entitlement, or product truth | Thin-client breach | Diff includes API/client logic not in packet | PR train requires thin-client-safe implementation slices and explicit scope for privileged surfaces | frontend-engineer / architecture-specialist | Revert runtime changes and split PR |
| iOS parity breaks App Store readiness | Visual sync changes release claims, permissions, screenshots, HealthKit, or AI disclosure | App Store rejection risk | iOS design PR touches release surfaces casually | PR-6 requires App Store-safe evidence and scoped iOS validation | qa-engineer-agent | Revert iOS visual sync and restore release posture |
| GEPA optimizes bad metrics | Prompt evolution rewards subjective taste or noisy scoring | Unstable design automation | GEPA appears before curated fixtures | GEPA deferred to PR-8 prompt/rubric evolution over curated fixtures only | data-scientist-agent / ml-engineer-agent | Disable GEPA lane and revert eval docs |
| Reference corpus creates licensing risk | Copied assets/copy or unclear license enters repo | Legal/copyright exposure | `license_status` is unknown but decision is adopt/adapt | Manifest and scorecard require license, attribution, legal-copy risk, forbidden-copy elements | security-auditor | Reject reference and remove derived brief |
| Design score becomes subjective LLM taste | Scorecard lacks deterministic anchors | Inconsistent design decisions | Scores without evidence or axes | Scorecard defines axes, scale, decision thresholds, and normalization notes | data-scientist-agent | Revert scorecard usage and require deterministic checker |

## Bug-Hunter Pass

Initial bug-hunter controls for PR-0:

- Docs-only diff guard must return empty output.
- No generated token mirror diff is allowed.
- No runtime UI, backend, iOS runtime, Storybook config, or Figma write is allowed.
- Full `make verify` deferral must be stated; no merge-ready claim from local narrow gates alone.
- `docs/review/PR_<N>_FIXED_MAPPING.md` must be added after PR number exists.

Post-open mandatory lane:

1. `qa-engineer-agent` verifies the narrow gate bundle and docs-only boundary.
2. `bug-hunter` checks false-green risks, missing dispositions, token mirror drift, and Figma/reference copy loopholes.
