# Agent instructions (scope: frontend/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `frontend/` and below.
- Key directories: `frontend/src/`, `frontend/src/api/`, `frontend/public/`.

## Commands (run from `frontend/`)
- Install: `npm install`
- Dev: `npm run dev`
- Build: `npm run build`
- Preview: `npm run preview`
- Test: `npm run test`, `npm run test:ci`, `npm run test:coverage`
- Generate API types: `npm run generate-types`

## Conventions
- API base is `/api/v1`; keep client paths aligned with backend routers.
- OpenAPI types are generated from `src/api/openapi.json` into `src/api/schema.ts`.
- Keep UI changes in sync with backend schema updates.
