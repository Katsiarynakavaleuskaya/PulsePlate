---
name: pulseplate-frontend-ui
description: Implement frontend UI in PulsePlate style using design tokens and thin-client constraints.
---

# PulsePlate Frontend UI

## When to use

- Building or modifying UI in `frontend/`.
- Creating new components/pages in existing web style.
- Reviewing style drift or token violations.

## Inputs required

- UI goal and target user flow.
- Files/components to modify.
- Accessibility and responsiveness constraints.

## Procedure (commands)

1. Load style SoT:

   ```bash
   sed -n '1,260p' frontend/src/styles/tokens.css
   sed -n '1,260p' frontend/src/styles/tokens.ts
   sed -n '1,220p' frontend/tailwind.config.ts
   ```

2. Load code-first UI naming SoT:

   ```bash
   sed -n '1,220p' docs/design/UI_COMPONENT_VOCABULARY.md
   sed -n '1,220p' docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md
   ```

3. Check existing component patterns:

   ```bash
   find frontend/src/components/ui -maxdepth 2 -type f | sort
   ```

4. Enforce thin HTTP adapter policy:

   ```bash
   rg -n "fetch\\(" frontend/src --glob '!frontend/src/api/client.ts'
   ```

5. Validate frontend:

   ```bash
   cd frontend
   npm test
   npm run build
   cd ..
   ```

## Output format

- `UI scope`: touched components/pages.
- `Canonical components`: vocabulary names selected for this UI.
- `Token usage`: which semantic tokens were applied.
- `Policy checks`: thin-client and component pattern checks.
- `Validation`: test/build results.
- `Follow-up`: specific visual or accessibility TODOs.

On failure include:

- Raw failing lines.
- `file:line:error` pointers.
- Minimal fix steps and rerun commands.

## Guardrails

- No ad-hoc hex colors when equivalent semantic tokens exist.
- Normalize vague UI language into canonical component names before implementation.
- No direct `fetch()` outside `frontend/src/api/client.ts`.
- Preserve existing visual language and token hierarchy.
- Do not claim UI done without `npm test` and `npm run build`.

## SoT links

- `frontend/AGENTS.md`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/tokens.ts`
- `frontend/tailwind.config.ts`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`
- `frontend/src/components/ui`
- `frontend/src/api/client.ts`
