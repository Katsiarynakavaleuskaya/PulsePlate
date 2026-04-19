# Figma MCP Design System Rules (PulsePlate Frontend)

## Scope

This document is the implementation-facing ruleset for translating Figma MCP
design context into production code in `frontend/`.

Use this with:

- `get_design_context(fileKey,nodeId)`
- `get_metadata(fileKey,nodeId)` for large trees
- `get_screenshot(fileKey,nodeId)` when supported by file type/runtime

## 1) Token Definitions

### Source of truth

- Repo token authoring source: `/tokens`
- Design-intent lane: `Figma Design` with optional `Tokens Studio` support
  inside the same lane
- Web runtime token SoT: `frontend/src/styles/tokens.css`
- Typed runtime mirror/helper: `frontend/src/styles/tokens.ts`
- Tailwind mapping consumer: `frontend/tailwind.config.ts`
- Governance docs:
  - `docs/design/TOKENS_SOT.md`
  - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`

### Token structure

- CSS custom properties in `tokens.css` are the deployed web token contract.
- `tokens.ts` mirrors the same groups for TypeScript consumers
  (`colors`, `spacing`, `typography`, `borderRadius`, etc.).
- Semantic tokens live in runtime CSS first (`--color-primary`,
  `--color-surface`, `--color-text`, status tokens).
- Legacy aliases (`--pp-*`) remain compatibility bridges only.

### Transformation systems

- PulsePlate uses a governed promotion pipeline:
  `Figma` -> optional `Tokens Studio` authoring support -> `/tokens` ->
  generated runtime mirrors -> Storybook/tests/platform validation.
- There is no autonomous export job that overrides repo runtime artifacts.
- Mapping is done by importing CSS variables and extending Tailwind theme.

## 2) Component Library

### Locations

- Shared components: `frontend/src/components/`
- UI primitives: `frontend/src/components/ui/`
- Feature-specific components: nested folders (for example `Paywall/`)
- Barrel export: `frontend/src/components/index.ts`

### Architecture

- Function components + TypeScript props interfaces
- Composition and route-level assembly via `frontend/src/App.tsx`
- Feature pages in `frontend/src/pages/` consume shared components

### Documentation and Storybook

- Storybook is configured in `frontend/package.json`.
- Current review surfaces include stories under `frontend/src/components/ui/`
  and `frontend/src/stories/HppTokenGuidelines.mdx`.
- Storybook is the implementation review/documentation lane, not the token
  authoring lane or runtime SoT.
- Component behavior is still validated primarily through Vitest + RTL tests
  under `__tests__/`.

## 3) Frameworks and Libraries

### UI stack

- React 18 + TypeScript
- Routing: `react-router-dom`
- Forms: `react-hook-form`, `zod`
- Charts: `recharts`
- Icons: `lucide-react`

### Styling stack

- Tailwind CSS + custom utility classes
- CSS variables from `tokens.css`
- App-level CSS in `index.css` and `styles/utilities.css`

### Build and test

- Bundler/build tool: Vite (`frontend/vite.config.ts`)
- Tests: Vitest + jsdom + Testing Library

```json
// frontend/package.json (scripts excerpt)
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest"
  }
}
```

## 4) Asset Management

### Storage and references

- Static/public mocks under `frontend/public/`
- Canonical brand assets live in `frontend/src/assets/brand/`
- FitChef mascot canon and variant naming live in
  `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`
- SVGs are commonly inline in TSX or icon components

### Optimization

- Vite handles bundling and minification
- Current production build warns for large chunks (monitor split points)

### CDN

- No frontend CDN-specific configuration found in Vite config for assets

## 5) Icon System

### Sources

- Primary icon library: `lucide-react`
- Secondary: inline SVG in component markup where needed

### Usage pattern

```tsx
import { Download, TrendingUp } from "lucide-react";
```

### Naming convention

- Use semantic component names matching UI meaning (`Download`, `TrendingUp`)
- For custom inline SVGs, keep usage local to the component context

## 6) Styling Approach

### Methodology

- Utility-first classes + CSS variable tokens
- Minimal inline styles used only for dynamic token combinations and gradients

### Global styles

- `frontend/src/main.tsx` imports:
  - `styles/tokens.css`
  - `index.css`
- Global baseline includes reduced-motion handling and focus-visible behavior

```tsx
// frontend/src/main.tsx
import "./styles/tokens.css";
import "./index.css";
```

### Responsive design

- Tailwind responsive breakpoints (`sm`, `md`, `lg`) in class names
- Tokenized breakpoint values also exist in `tokens.css`

## 7) Project Structure

### High-level organization

- `frontend/src/pages/` -> route surfaces
- `frontend/src/components/` -> reusable UI and feature components
- `frontend/src/features/` -> feature modules (for example progress)
- `frontend/src/api/` -> thin API adapter + generated OpenAPI schema
- `frontend/src/styles/` -> design tokens + utilities

### Feature pattern

- Route component composes feature components and shared UI
- Tests are colocated in `__tests__/` near page/component modules

## Figma MCP Translation Rules (Project-Specific)

1. Start from `get_design_context`, not assumptions.
2. Map Figma colors/spacing into the `/tokens` authoring tree first, regenerate
   `frontend/src/styles/tokens.css`, and update `tokens.ts` only if TS
   consumers need the typed mirror.
3. Reuse existing primitives in `frontend/src/components/ui/` before creating
   new ones.
4. Keep business logic unchanged in design-only passes.
5. Validate with targeted tests and `npm run build`.
6. If runtime/file type does not support screenshot, proceed with context +
   metadata and document the limitation.

## Quick Validation Checklist

- [ ] Layout hierarchy matches Figma node intent
- [ ] Colors map to runtime token SoT (`tokens.css`) with no random hardcoded palette
- [ ] Typed mirror (`tokens.ts`) is aligned when a TS consumer depends on the changed token
- [ ] Touch targets are at least 44px where interactive
- [ ] Existing routes/state/analytics contracts remain intact
- [ ] Related tests pass + frontend build succeeds
