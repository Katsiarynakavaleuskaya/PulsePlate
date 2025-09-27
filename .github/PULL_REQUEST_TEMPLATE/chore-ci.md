# chore(frontend): tooling/CI

## Goal
Единые скрипты, линт, тесты, сборка в GitHub Actions.

## Changes
- package.json scripts
- ESLint/Prettier конфиги
- .github/workflows/frontend-ci.yml

## Acceptance Criteria
- CI: `npm ci`, `npm run lint`, `npm test -- --ci`, `npm run build` — зелёные

## Notes
- Кэш npm включён
- Ветка защищена правилом на успешный workflow
