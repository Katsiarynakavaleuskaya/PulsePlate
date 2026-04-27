# PR #1552 - Fixed in Commit Mapping (canonical)

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1552>
Branch: `feat/button-runtime-set-code-parity`
Date: 2026-04-28

## Discussion Thread Pass

- [ ] Discussion-thread pass completed (update after review bots / humans)
- [ ] Fixed in commit mapping completed (update after dispositions)

## Fixed in Commit Mapping

<!-- Populate after review with Disposition (FIXED / NOT-A-BUG / DEFERRED), evidence, and thread URLs per `AGENTS.md` review governance. -->

_(No review threads yet — placeholder for post-open bot/human comments.)_

## Scope (PR-1552)

- `frontend/src/components/ui/Button.tsx` — RuntimeSet parity: `success` / `warning` variants, `loading` / `loadingLabel`, `destructive` as sole danger mapping.
- `frontend/src/components/ui/__tests__/Button.test.tsx` — expanded tests.
- `frontend/src/components/ui/Button.stories.tsx` — new Storybook stories.
- `docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md` — Button code parity + evidence anchors.
- `docs/roadmap/BACKLOG_LEDGER.md` — `#ledger-p1-design-button-runtime-code-parity` closed when PR merges.

## Validation (operator checklist)

Run locally before merge (see PR body §14):

- `cd frontend && npm ci && npm run test:ci -- src/components/ui/__tests__/Button.test.tsx && npm run build-storybook`
- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make validate-changed` and `make validate-min`
- Full `make verify` per repo merge bar unless a documented narrow-gate exception applies.
