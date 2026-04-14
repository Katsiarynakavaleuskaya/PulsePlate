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
- `vercel-composition-patterns`
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
- `build-web-apps:frontend-skill`
- `build-web-apps:web-design-guidelines`
- `build-ios-apps:swiftui-ui-patterns`
- `build-ios-apps:swiftui-view-refactor`
- `build-ios-apps:ios-debugger-agent`

### Tier 2: Useful and should route conditionally

- `vercel-react-native-skills`
- `build-web-apps:react-best-practices`
- `build-ios-apps:swiftui-performance-audit`
- `linear`
- `notion-research-documentation`
- `notion-knowledge-capture`
- `notion-spec-to-implementation`
- `vercel-deploy`
- `netlify-deploy`
- `render-deploy`
- `cloudflare-deploy`
- `build-web-apps:stripe-best-practices`

### Tier 3: Missing custom PulsePlate skills

- `pulseplate-app-store-release`
- `pulseplate-monetization-gtm`
- `pulseplate-design-launch-system`
- `pulseplate-agent-product`
- `pulseplate-web-launch-site`

## Planned Creation Waves

### Wave 1

- `pulseplate-app-store-release`
- `pulseplate-monetization-gtm`

### Wave 2

- `pulseplate-design-launch-system`
- `pulseplate-web-launch-site`

### Wave 3

- `pulseplate-agent-product`

## Scope of This PR Family

Allowed in this alignment wave:

- improve deterministic skill discovery,
- improve additive routing quality,
- document current/conditional/missing skill coverage,
- record missing custom skills in backlog.

Not allowed in this alignment wave:

- replacing coordinator-first routing,
- turning skills into execution control,
- altering Cursor runtime behavior,
- introducing a parallel orchestration layer.
