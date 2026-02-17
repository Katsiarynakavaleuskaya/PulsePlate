---
name: pulseplate-openapi-sync
description: Regenerate backend OpenAPI and frontend API types with deterministic checks.
---

# PulsePlate OpenAPI Sync

## When to use
- Backend schema or route contracts changed.
- Frontend API types are stale or mismatched.
- PR includes API contract updates.

## Inputs required
- Target branch/base for diff comparison.
- Confirmation that backend app imports successfully.
- Whether frontend build/test should be run after sync.

## Procedure (commands)
1. Generate canonical OpenAPI:
   ```bash
   python scripts/generate_openapi.py
   ```
2. Regenerate frontend types:
   ```bash
   cd frontend
   npm run generate-types
   cd ..
   ```
3. Inspect resulting diff:
   ```bash
   git status --short
   git diff -- frontend/src/api/openapi.json frontend/src/api/schema.ts
   ```
4. Validate frontend compile/test path:
   ```bash
   cd frontend
   npm test
   npm run build
   cd ..
   ```

## Output format
- `Regeneration status`: openapi/types commands with exit codes.
- `Changed artifacts`: list changed contract files.
- `Contract notes`: notable API shape changes.
- `Validation`: frontend test/build outcome.
- `Rerun commands`: exact commands for reviewers.

Include on failure:
- Raw failing lines.
- `file:line:error` pointers.
- Minimal fix steps.

## Guardrails
- Do not edit generated files manually.
- Do not skip type regeneration after OpenAPI changes.
- Do not merge API contract changes without frontend validation.
- Keep backend schema generation on canonical entrypoint only.

## SoT links
- `scripts/generate_openapi.py`
- `frontend/AGENTS.md`
- `frontend/src/api/openapi.json`
- `frontend/src/api/schema.ts`
- `frontend/package.json`
