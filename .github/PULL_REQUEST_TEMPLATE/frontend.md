---
name: Frontend Feature
about: SPA / web UI changes
labels: [frontend, feat]
---

# feat(frontend): <scope>

## Summary

**What & Why:** [Brief description of changes and business rationale]

**Related Components/Pages:**
- Modified: `ComponentName.tsx`, `PageName.tsx`
- New: `NewComponent.tsx`, `CustomHook.ts`
- Updated: API types, i18n keys, test mocks

**Linked Issues:** #123, #456

## Scope

- **Modified Files:** `src/components/`, `src/pages/`, `src/features/`, `src/lib/`
- **New Components:** UI components, custom hooks, utilities
- **API Changes:** Request/response types, MSW handlers, error handling
- **Styling:** Tailwind classes, responsive design, theme consistency
- **Out of Scope:** Backend changes, database schema, CI/CD pipelines

## Acceptance Criteria

- **Routes & Navigation:** React Router states, protected routes, redirects
- **API Integration:** REST calls via custom hooks, error handling, loading states
- **Forms & Validation:** react-hook-form + zod schemas, error messages
- **Auth & Premium:** API key validation, paywall logic, feature gates
- **i18n:** Text translation in en/ru/es, locale switching
- **Accessibility:** axe-core compliance, keyboard navigation, screen reader support
- **Responsive:** Mobile-first design, Tailwind breakpoints, touch interactions
- **Performance:** Lazy loading, code splitting, bundle size impact
- **MSW Mocks:** API mocking for development/testing, fallback states

## Tests

- [ ] `npm run lint` (ESLint + TypeScript rules)
- [ ] `npm run typecheck` (TypeScript compilation check)
- [ ] `npm run build` (Vite production build)
- [ ] `npm run sb:build` (Storybook accessibility check)
- [ ] **Unit/Integration Tests (Vitest + @testing-library + MSW):**
  - [ ] Компонент рендерится без ошибок
  - [ ] User interactions (click, form submit, navigation)
  - [ ] API calls с MSW моками (success/error states)
  - [ ] Form validation (react-hook-form + zod)
  - [ ] i18n переключение языков (en/ru/es)
  - [ ] Premium/paywall gates и auth states
  - [ ] Error boundaries и fallback states
  - [ ] Accessibility (axe-core в Storybook)
  - [ ] Responsive design (mobile/desktop breakpoints)
  - [ ] Loading states и skeleton screens

```bash
cd frontend
cp .env.example .env   # если нужен VITE_API_BASE
npm ci
npm run dev
```

## QA Notes

- **Visual Changes:** Screenshots/videos of UI changes, responsive testing
- **Manual Testing Scenarios:**
  - Happy path user flows
  - Error states and edge cases
  - Form validation scenarios
  - Cross-browser testing (Chrome, Firefox, Safari)
  - Mobile responsiveness (iOS Safari, Chrome Mobile)
- **Accessibility Testing:** Screen reader navigation, keyboard-only usage
- **Performance:** Lighthouse scores, bundle size impact

## Deployment Checklist

- [ ] Feature flags configured for gradual rollout
- [ ] Environment variables documented
- [ ] API endpoints deployed and tested
- [ ] Database migrations (if applicable)

👉 Additional checklists: [docs/pr-checks.md](../../docs/pr-checks.md)
