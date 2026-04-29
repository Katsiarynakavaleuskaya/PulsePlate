# PR #1583 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1583>
Branch: `codex/web-launch-figma-make-shell`
Date: 2026-04-29

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1583#discussion_r3163785317 -> e9182b20a
Disposition: FIXED
Commit: e9182b20a
Evidence: `frontend/src/pages/Onboarding/EnterKey.tsx` now defaults direct `/enter-key` success to `/app` and still preserves protected source routes such as `/plate`; `frontend/src/pages/Onboarding/__tests__/EnterKey.test.tsx` covers both flows.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1583#discussion_r3163820036 -> 0a1347656
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1583#discussion_r3163820048 -> 0a1347656
Disposition: FIXED
Commit: 0a1347656
Evidence: `docs/review/PR_1583_FIXED_MAPPING.md` now uses `VENV_PYTHON=$VENV_PYTHON` instead of a local `/Users/...` path and keeps Merge Readiness checkboxes unchecked until final merge-cycle verification.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1583#discussion_r3163820053 -> 46453d8ca
Disposition: FIXED
Commit: 46453d8ca
Evidence: `frontend/src/components/NotFound.tsx` now sends the Go Home fallback to `/app`; `frontend/src/components/__tests__/NotFound.test.tsx` covers the preserved app-home fallback. The related `/enter-key` fallback was fixed in commit `e9182b20a`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1583#pullrequestreview-4200318636 -> 0a1347656
Disposition: FIXED
Commit: 0a1347656
Evidence: CodeRabbit review aggregated the artifact privacy/checklist findings fixed in commit `0a1347656` and the root fallback findings fixed in commits `e9182b20a` and `46453d8ca`.

## Implementation Evidence

Disposition: FIXED
Commit: 1ec414beb
Evidence: `frontend/src/config/routes.ts` promotes the public `/` route to the launch shell and preserves the app Home surface at `/app`; `frontend/src/config/__tests__/routes.design-preview.test.ts` locks both route contracts.

Disposition: FIXED
Commit: 1ec414beb
Evidence: `frontend/src/components/marketing/HeroSection.tsx` and `frontend/src/components/marketing/marketing.css` replace the internal dashboard-style hero with a FitChef-backed launch offer using existing repo assets and wellness-safe copy.

Disposition: FIXED
Commit: 1ec414beb
Evidence: `frontend/src/__tests__/App.test.tsx`, `frontend/src/pages/__tests__/Home.test.tsx`, and `frontend/src/components/__tests__/TabBar.test.tsx` preserve the app shell/tab behavior on `/app` while keeping `/` hidden from the tab bar.

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `python3 scripts/orchestration/task_bootstrap.py --goal "Align public web launch shell with Figma Make PulsePlate_Web while preserving app routes" --task-class "Design" --pr-phase pre_open` (PASS; packet `16d88e9da8d9`)
- `python3 scripts/orchestration/task_bootstrap.py --goal "Post-open review for PR 1583 web launch shell root route alignment" --task-class "Design" --pr-phase post_open_review` (PASS; packet `daadc35d842d`)
- `cd frontend && npm test -- --run src/config/__tests__/routes.design-preview.test.ts src/__tests__/App.test.tsx src/pages/__tests__/Home.test.tsx src/components/__tests__/TabBar.test.tsx` (PASS; 40 passed)
- `cd frontend && npm run build` (PASS)
- `cd frontend && npm run smoke:css` (PASS)
- Browser smoke: `/` and `/app` on desktop and mobile via local preview (PASS)
- `pre-commit run --all-files` (PASS)
- `make validate-changed VENV_PYTHON=$VENV_PYTHON` (PASS; no Python files changed)
- Pre-push hooks: backend pre-push pytest, full-repo Bandit, docker build test (PASS)

## Merge Readiness

- [ ] CI green on current head
- [ ] No unresolved actionable review threads
- [ ] CodeRabbit/Sourcery/Cubic statuses reviewed
- [ ] Fixed-mapping artifact and PR body mirror aligned
- [ ] `check_merge_ready.py --require-auth` PASS
