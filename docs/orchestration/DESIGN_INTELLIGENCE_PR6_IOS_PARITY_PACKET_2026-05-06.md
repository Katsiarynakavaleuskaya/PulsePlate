<!-- markdownlint-disable MD013 -->
# Design Intelligence PR-6 iOS Parity Packet

## Goal

Audit iOS visual/design-system parity after PR-5 web acceptance and apply only bounded iOS DesignSystem sync when evidence proves a concrete gap.

## Decision

Proceed with an audit plus one bounded token-facade sync. `ShapeStyle+Theme.swift` must use `PPDesignTokens.ColorToken` for surface aliases instead of manual opacity values. No broad iOS redesign or screen implementation is authorized.

## Coordinator Route

Requested route:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. `architecture-specialist`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`
8. `data-scientist-agent`

The route is established through `task_bootstrap.py` and remains subordinate to repository governance, scoped `AGENTS.md`, and merge-readiness gates.

## Source Precedence

Repo code, tests, `/tokens`, generated mirrors, UI vocabulary, backend/OpenAPI contracts, and runtime code remain canonical.

The following are evidence/reference layers only:

- `docs/design/DESIGN.md`
- reference manifests
- screen evidence packs
- design scorecards
- PR-6 audit docs
- Figma
- Canva
- Storybook
- external references
- prompt outputs

## Evidence Inputs

- PR #1689 merged the web launch shell acceptance brief and moved the train to PR-6.
- PR #1683 added metadata-only screen evidence packs.
- PR #1686 added deterministic scorecard checks.
- `docs/design/screen_evidence/examples/ios_home.sample.json` validates as sample metadata.
- `docs/design/design_scorecard/examples/ios_home.scorecard.sample.json` validates as deterministic scorecard metadata.
- iOS DesignSystem primitives route through `PPDesignTokens`.
- `ShapeStyle+Theme.swift` had a bounded token-facade parity gap and is the only runtime design-system sync in this packet.
- Expected visual delta: `Color.surface` moves from local `Color.white.opacity(0.08)` to generated token-backed `PPDesignTokens.ColorToken.surface` (`Color.white.opacity(0.10)`). This is token parity, not redesign.

Required evidence commands:

```bash
python3 scripts/design/screen_evidence_pack.py validate-dir docs/design/screen_evidence/examples
python3 scripts/design/design_scorecard.py score docs/design/screen_evidence/examples/ios_home.sample.json
python3 scripts/design/design_scorecard.py validate-score docs/design/design_scorecard/examples/ios_home.scorecard.sample.json
python3 scripts/design/design_scorecard.py summarize docs/design/design_scorecard/examples/ios_home.scorecard.sample.json
```

These commands provide governance evidence only. They do not prove live iOS simulator visuals.

## Scope

- Add iOS visual parity audit.
- Add PR-6 orchestration packet.
- Update Design Intelligence ledger status narrowly.
- Sync `ShapeStyle+Theme.swift` surface aliases to the design-token facade.
- Add focused iOS contract coverage for the bounded sync.
- Keep PR-7 design-agent workflow and PR template as the next Design Intelligence lane after PR-6.

## Out Of Scope

- No broad iOS redesign.
- No web changes.
- No backend/OpenAPI changes.
- No billing, auth, StoreKit, HealthKit, entitlement, or App Store changes.
- No `/tokens` changes.
- No manual generated token mirror edits.
- No Figma or Canva writes.
- No screenshots or binary artifacts.
- No visual/pixel comparison.
- No GEPA.

## Plugin And Skill Boundaries

- GitHub/CLI: PR truth, checks, reviews, and merge readiness.
- Build iOS Apps: optional verification context only for targeted iOS checks.
- Figma: read-only evidence only if future review requires it; no writes in PR-6.
- Canva, browser automation, external crawlers, image generation, Remotion, HyperFrames, Supabase, Hugging Face, Jam, Life Science Research, and LaTeX Tectonic are not required for this PR.

## Risks

- False visual-ready claim: mitigated by saying sample evidence is metadata only and not simulator proof.
- Second source of truth: mitigated by repeating repo source precedence.
- Generated-token drift: mitigated by forbidding manual edits to `DesignTokens.generated.swift` and checking token mirror diffs.
- Broad redesign drift: mitigated by limiting code sync to token-backed `ShapeStyle` aliases.
- Thin-client drift: mitigated by avoiding BMI, nutrition, coaching, entitlement, StoreKit, backend, and OpenAPI logic.

## Definition Of Done

- iOS visual parity audit exists.
- PR-6 packet exists.
- Bounded sync decision is explicit.
- `ShapeStyle+Theme.swift` uses `PPDesignTokens.ColorToken` for surface aliases.
- Focused iOS contract test covers the token-facade alias requirement.
- Next lane decision is explicit: PR-7 design-agent workflow and PR template; live iOS capture is separate unless later scoped.
- Generated token mirror remains untouched.
- No frontend/backend/token drift.
- Bounded checks pass.
