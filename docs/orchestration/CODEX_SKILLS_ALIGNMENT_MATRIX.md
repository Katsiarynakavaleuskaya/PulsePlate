# Codex Skills Alignment Matrix

Purpose: record the current PulsePlate Codex skill posture without changing
coordinator-first orchestration authority.

Canonical host-path semantics live in [`docs/dev/CODEX_SKILLS.md`](../dev/CODEX_SKILLS.md).
This matrix records alignment posture and references that contract instead of
duplicating host-path rules independently.

## Non-Interference Contract

This alignment wave is passive/discovery-only. It must preserve these invariants:

- `agent-coordinator` remains the canonical task-start and routing authority.
- `scripts/orchestration/task_bootstrap.py` remains the canonical bootstrap entrypoint.
- `recommended_skills` remain additive metadata in the task packet.
- `native_subagent_bridge` remains transport-only; repo agent slug remains the canonical identity.
- Cursor `.cursor/agents/*.md`, lane packets, role order, handoff rules, and merge-readiness semantics are not replaced here.
- No installer, docs, or skill change in this wave may implicitly mutate Cursor session behavior, launcher behavior, shell profiles, or user config.
- Plugin-provided skills remain plugin-provided; they are not duplicated into repo install flow.

## Discovery Precedence

1. Repo source of truth: `tools/codex_skills/*`
2. Repo discovery mirror: `.agents/skills/*`
3. Primary user install target: `$AGENTS_HOME/skills/*` (fallback: `$HOME/.agents/skills/*`)
4. Compatibility-only legacy target: `$CODEX_HOME/skills/*` (fallback: `~/.codex/skills/*`)

Interpretation:

- `.agents/skills/` is a discovery layer, not a second canonical repository of skill content.
- Compatibility installs into `$CODEX_HOME/skills` remain explicit and operator-invoked only.

## Skill Matrix

### Tier 1: Needed now and should auto-route

- `pulseplate-workflow`
- `pulseplate-frontend-ui`
- `pulseplate-backend-endpoints`
- `pulseplate-openapi-sync`
- `pulseplate-playwright-e2e`
- `pulseplate-gates`
- `pulseplate-guards`
- `vercel-react-best-practices`
- `figma`
- `figma-implement-design`
- `playwright`
- `openai-docs`
- `gh-fix-ci`
- `gh-address-comments`
- `create-pr`
- `docs-sync`
- `bug-triage`
- `pulseplate-pr-review`
- `build-web-apps:frontend-skill`
- `build-web-apps:web-design-guidelines`
- `build-ios-apps:swiftui-ui-patterns`
- `build-ios-apps:swiftui-view-refactor`
- `build-ios-apps:ios-debugger-agent`

### Tier 2: Useful and should route conditionally

- `pulseplate-app-store-release`
- `pulseplate-monetization-gtm`
- `build-web-apps:react-best-practices`
- `build-ios-apps:swiftui-performance-audit`
- `linear`
- `notion-research-documentation`
- `notion-knowledge-capture`
- `notion-spec-to-implementation`
- `build-web-apps:stripe-best-practices`
- `pulseplate-premortem-risk-review`

### Manual-only for now: available, but not wired into SkillRule auto-routing yet

- `vercel-composition-patterns`
- `vercel-react-native-skills`
- `vercel-deploy`
- `netlify-deploy`
- `render-deploy`
- `cloudflare-deploy`

### Tier 3: Custom PulsePlate skills closed

- `pulseplate-design-launch-system` — delivered via PR `#1482` / `d881d5f211478c493d4f18984cb6c335d867be6f`.
- `pulseplate-web-launch-site` — delivered via PR `#1565`.
- `pulseplate-agent-product` — delivered via PR `#1565`.

## Skill Delivery Waves

### Wave 1 — Delivered

- `pulseplate-app-store-release` (merged via PR `#1436` / `0b3f2de82892a230789d70648fccfd0f7806641f`; evidence: `docs/review/PR_1436_FIXED_MAPPING.md:1`, `tools/codex_skills/pulseplate-app-store-release/SKILL.md:1`)
- `pulseplate-monetization-gtm` (merged via PR `#1439` / `28c2bd2dd18e57a058386670161b0e350e078c5a`; PR `#1438` closed as superseded; evidence: `docs/roadmap/BACKLOG_LEDGER.md:4752`, `docs/review/PR_1439_FIXED_MAPPING.md:1`, `tools/codex_skills/pulseplate-monetization-gtm/SKILL.md:1`)

### Wave 2 — Delivered

- `pulseplate-design-launch-system` — governance-only skill bundle for design-system readiness, token/brand consistency, and launch-asset boundaries (evidence: `tools/codex_skills/pulseplate-design-launch-system/SKILL.md:1`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:15`, `tests/test_skill_router.py:750`)
- `pulseplate-web-launch-site` — launch-site pages, CTA funnels, waitlist/lead-capture paths, SEO/ASO launch copy, and deploy-adjacent web launch handoff (PR `#1565`).

### Wave 3 — Delivered

- `pulseplate-agent-product` — agent-product surfaces, operator workflows, HITL boundaries, and product handoffs that preserve coordinator authority (PR `#1565`).

### Wave 4 — Risk / Decision Extensions

- `pulseplate-premortem-risk-review` — premortem risk analysis on high-downside plans (PR, epic, launch, security, CI/CD, AI/RAG, App Store, monetization, design decisions). Advisory only; does not replace coordinator or merge-readiness authority. (evidence: `tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md:1`, `scripts/orchestration/skill_router.py`)

## Scope of This PR Family

Allowed in this alignment wave:

- verify installed skill completeness against repo source of truth,
- improve deterministic skill discovery,
- improve additive routing quality,
- document current/conditional/missing skill coverage,
- record missing custom skills in backlog.

## Verification

- Verifier script: `scripts/verify_codex_skills_install.py`
- Diagnosis runbook: `docs/dev/OPENCODE_SKILL_DISCOVERY_RUNBOOK.md`

Not allowed in this alignment wave:

- replacing coordinator-first routing,
- turning skills into execution control,
- altering Cursor runtime behavior,
- introducing a parallel orchestration layer.
