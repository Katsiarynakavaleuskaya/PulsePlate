<!-- markdownlint-disable MD013 -->
# Task Analysis: Web Launch Design Polish V1

**Date:** 2026-04-30
**Task packet:** `41eeba1853f4`
**Branch:** `codex/web-launch-design-polish-v1`
**Status:** draft-override implementation lane

## Goal

Polish the public PulsePlate web launch shell at `/` and `/marketing` using repo
tokens/components as the source of truth and PR #1593's Figma Make packet as
reference-only design direction.

## Scope

In scope:

- `frontend/src/pages/Marketing/PulsePlateMarketingPage.tsx`
- `frontend/src/components/marketing/*`
- focused marketing route/render tests
- design/session evidence for the web launch polish lane
- backlog ledger alignment for this active PR lane

Out of scope:

- backend/API/schema/auth/billing changes
- generated frontend API types
- iOS/SwiftUI changes
- Figma or Canva writes
- Cloudflare, Netlify, Code Connect, or deployment changes
- Figma Make generation or source promotion

## Coordinator Routing

Declared order:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. `monetization-gtm` advisory
5. `qa-engineer-agent`
6. `bug-hunter`

Bootstrap command emitted packet `artifacts/orchestration/task_packets/41eeba1853f4.json`.
The local artifact is gitignored and is not committed.

## Skills And Tool Lane

- `pulseplate-design-launch-system`: source precedence and Figma/Canva boundaries
- `pulseplate-web-launch-site`: wellness-safe launch copy and CTA discipline
- `pulseplate-agent-product`: product surface framing and operator-safe handoff
- `pulseplate-monetization-gtm`: tier copy without unsupported billing claims
- `build-web-apps:react-best-practices`: React surface structure and focused tests
- `browser-use:browser`: local preview evidence after implementation
- `coderabbit:code-review`: post-open advisory review disposition

Figma Make and Canva remain reference/evidence lanes only. Runtime behavior,
routes, billing truth, and product copy are governed by repo code/docs/tests.

## Initial Gates

Passed on updated `main` before creating this worktree:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
```

Passed again inside this worktree before edits:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
```

## Implementation Guardrails

- Keep `/` and `/marketing` public and tabbar-free.
- Reuse existing marketing primitives; do not create a broad new design-system primitive.
- Keep CTAs on existing routes only.
- Remove unsupported proof, diagnosis, medical, guaranteed-outcome, or store/billing claims.
- Improve hierarchy, rhythm, focus/reduced-motion behavior, responsive layout, and touch target clarity.
- Do not run full Figma Make or full local `make verify`; document the machine-heavy deferral.
