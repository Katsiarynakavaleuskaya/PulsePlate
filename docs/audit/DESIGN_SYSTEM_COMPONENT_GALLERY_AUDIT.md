# Design System Enrichment Audit: Component Gallery Reference

**Date:** 2026-02-28
**Status:** Audit (evidence-based)
**Scope:** Whether and how to enrich PulsePlate design system using [The Component Gallery](https://component.gallery/components/) as a reference catalog.
**Branch:** `docs/audit-design-system-component-gallery` (audit only; no changes to colleague-owned documents).

---

## 1. Scope and Constraints

- **Colleague work:** Documents and branches owned by other contributors are not modified. This audit adds one new file only (`docs/audit/DESIGN_SYSTEM_COMPONENT_GALLERY_AUDIT.md`).
- **Reference source:** [Component Gallery — Components](https://component.gallery/components/) (catalog of 50+ component types with definitions and example counts). Component Gallery is a project by Iain Bean (Astro, Airtable, Tailwind, Instrument Serif/Sans, JetBrains Mono); it is a **reference taxonomy**, not a dependency.
- **Evidence policy:** All claims about current state cite `file:line` or repo paths; recommendations reference existing audits and SoT.

---

## 2. Current Design System — Evidence

### 2.1 Tokens and Brand (SoT)

| Asset | Location | Evidence |
|-------|----------|----------|
| Token SoT | `docs/design/TOKENS_SOT.md` | Defines `frontend/src/styles/tokens.css` as canonical; `--pp-navy`, `--pp-blue`, `--pp-green`, `--pp-red`, `--pp-gold`; migration policy PR-1/2/3. |
| Web token governance | `docs/sora/SORA_STYLE_QA_CHECKLIST.md` | Section «Web Token Governance» — canonical policy (ref. TOKENS_SOT). |
| Luxury guidelines | `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:1–60` | Mood: minimalism + cozy + luxury-clean; palette Navy/Blue/Green/Red; flat, soft shadows. |

### 2.2 Frontend UI Components (Existing)

**Exports (public API):** `frontend/src/components/ui/index.ts:1–18`

| Component | File | Evidence / purpose |
|-----------|------|--------------------|
| Button | `frontend/src/components/ui/Button.tsx` | `buttonClasses()`, variants primary/secondary/ghost, sizes sm/md/lg. |
| Card | `frontend/src/components/ui/Card.tsx` | Container; used in `frontend/src/pages/Home.tsx:35–70` (Card + CardContent). |
| Dialog | `frontend/src/components/ui/Dialog.tsx` | Modal wrapper. |
| EmptyState | `frontend/src/components/ui/EmptyState.tsx` | No-data state. |
| ErrorBoundary | `frontend/src/components/ui/ErrorBoundary.tsx` | Error UI with AlertTriangle icon. |
| FormField | `frontend/src/components/ui/FormField.tsx` | Form field wrapper. |
| Input | `frontend/src/components/ui/Input.tsx` | Text input. |
| NumberInput | `frontend/src/components/ui/NumberInput.tsx` | Numeric input (locale, validation). |
| MobileMenu | `frontend/src/components/ui/MobileMenu.tsx` | Uses Headless UI Dialog. |
| OfflineIndicator | `frontend/src/components/ui/OfflineIndicator.tsx` | Connectivity feedback. |
| Skeleton | `frontend/src/components/ui/Skeleton.tsx` | ChartSkeleton, CardSkeleton, ProgressPageSkeleton (see `frontend/src/components/ui/__tests__/Skeleton.test.tsx:4–48`). |
| SegmentedControl | `frontend/src/components/ui/SegmentedControl.tsx` | Toggle group. |
| Toast | `frontend/src/components/ui/Toast.tsx` | react-hot-toast wrapper. |
| Toggle | `frontend/src/components/ui/Toggle.tsx` | Switch. |
| PullToRefresh, SwipeContainer | `frontend/src/components/ui/*.tsx` | Mobile patterns. |

**Other UI:** TabBar (tabs as navigation), VipBadge, VipFeatureCard, Paywall/BeforeAfter (modal), ProgressCharts (Recharts + Tooltip), GlassCard/pageCardStyle — see `docs/audit/FRONTEND_MODERN_COMPONENTS_AUDIT.md:44–98` for gap list.

---

## 3. Component Gallery Catalog vs PulsePlate (Gap Map)

Component Gallery lists **58 component types** (table below). Below: **Evidence** = our implementation; **Gap** = missing or partial; **Ref** = Component Gallery definition (for enrichment).

| # | Gallery component | Our state | Evidence / gap |
|---|-------------------|-----------|----------------|
| 1 | Accordion | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:73 — «Accordion — нет». No `frontend/src/components/ui/Accordion*.tsx`. |
| 2 | Alert | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:89 — «Alert — нет». ErrorBoundary is error-only, not generic Alert. |
| 3 | Avatar | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:106 — «Avatar — нет». No `Avatar` in ui/index. |
| 4 | Badge | Partial | VipBadge exists; no generic Badge (FRONTEND_MODERN_COMPONENTS_AUDIT:90). |
| 5 | Breadcrumbs | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:74 — «Breadcrumbs — нет». |
| 6 | Button | Have | `frontend/src/components/ui/Button.tsx:26–66` (buttonClasses, Button). |
| 7 | Button group | Partial | SegmentedControl is related; no generic ButtonGroup. |
| 8 | Card | Have | `frontend/src/components/ui/Card.tsx`; Home.tsx uses Card + CardContent. |
| 9 | Carousel | Gap | No carousel in ui/. |
| 10 | Checkbox | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:55 — «Checkbox — нет унифицированного». |
| 11 | Color picker | Gap | Not in scope for current product. |
| 12 | Combobox | Gap | No autocomplete/combobox in ui/. |
| 13 | Date input / Datepicker | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:57 — «DatePicker — нет». |
| 14 | Drawer | Gap | No drawer/sheet; MobileMenu is Dialog. |
| 15 | Dropdown menu | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:72 — «Dropdown Menu — нет». |
| 16 | Empty state | Have | `frontend/src/components/ui/EmptyState.tsx`. |
| 17 | Fieldset | Gap | No Fieldset wrapper; FormField exists. |
| 18 | File / File upload | Gap | Not in current scope. |
| 19 | Footer | Gap | No shared Footer component. |
| 20 | Form | Partial | React Hook Form + FormField; no unified Form wrapper. |
| 21 | Header | Partial | Per-page headers; no shared Header component. |
| 22 | Heading | Gap | No Heading component (typography). |
| 23 | Hero | Gap | No Hero/Jumbotron. |
| 24 | Icon | Have | lucide-react used across app. |
| 25 | Image | Partial | Native img / next/image if any; no design-system Image. |
| 26 | Label | Partial | FormField/labels; no standalone Label. |
| 27 | Link | Partial | React Router Link; no design-system Link. |
| 28 | List | Gap | No unified List component. |
| 29 | Modal | Partial | Dialog used as modal implementation (`frontend/src/components/ui/Dialog.tsx`) + BeforeAfter pattern; no generic Modal.tsx. |
| 30 | Navigation | Partial | TabBar, MobileMenu; no generic Nav. |
| 31 | Pagination | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:104. |
| 32 | Popover | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:94. |
| 33 | Progress bar | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:91 — «Progress — нет»; LiveProgressIndicator is feature-specific. |
| 34 | Progress indicator (stepper) | Partial | ProgressCharts; no generic Stepper. |
| 35 | Quote | Gap | Not in scope. |
| 36 | Radio button | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:54 — «RadioGroup — нет». |
| 37 | Rating | Gap | Not in scope. |
| 38 | Rich text editor | Gap | Not in scope. |
| 39 | Search input | Gap | No Search input component. |
| 40 | Segmented control | Have | `frontend/src/components/ui/SegmentedControl.tsx`. |
| 41 | Select | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:53 — «Select — нет кастомного». |
| 42 | Separator | Gap | No Separator/Divider. |
| 43 | Skeleton | Have | `frontend/src/components/ui/Skeleton.tsx` + variants. |
| 44 | Skip link | Gap | No Skip link component. |
| 45 | Slider | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:58. |
| 46 | Spinner | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:92 — «Spinner — нет» (Skeleton used for loading). |
| 47 | Stack | Gap | No Stack layout component (Tailwind space-y etc. used). |
| 48 | Stepper (nudger) | Gap | No quantity stepper. |
| 49 | Table | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:103–104. |
| 50 | Tabs | Partial | TabBar is nav; no content Tabs (FRONTEND_MODERN_COMPONENTS_AUDIT:73). |
| 51 | Text input | Have | Input + NumberInput. |
| 52 | Textarea | Gap | FRONTEND_MODERN_COMPONENTS_AUDIT:56. |
| 53 | Toast | Have | `frontend/src/components/ui/Toast.tsx` + react-hot-toast. |
| 54 | Toggle | Have | `frontend/src/components/ui/Toggle.tsx`. |
| 55 | Tooltip | Partial | Recharts Tooltip in ProgressCharts; no global Tooltip (FRONTEND_MODERN_COMPONENTS_AUDIT:93). |
| 56 | Tree view | Gap | Not in scope. |
| 57 | Video | Gap | Not in scope. |
| 58 | Visually hidden | Gap | No screen reader–only utility. |

---

## 4. Should We Enrich Using Component Gallery?

**Conclusion: yes, as a taxonomy and prioritization reference, not as a code dependency.**

- **Component Gallery** is a **catalog of component types and definitions** (names, aliases, one-line descriptions). It does not ship code; it helps align our design system with common naming and semantics.
- **Evidence:** [Component Gallery — About](https://component.gallery/components/) (accessed 2026-02-28): «The Component Gallery is a project by Iain Bean, built with Astro, using data from Airtable.» Our stack is React + Tailwind; we do not add Component Gallery as a runtime dependency. We use it to:
  1. **Validate gaps** — our existing audit (FRONTEND_MODERN_COMPONENTS_AUDIT) already lists missing components; Component Gallery confirms taxonomy (e.g. Alert vs Notification, Breadcrumbs, Dropdown menu, Progress bar, Tooltip).
  2. **Prioritize** — same P0/P1/P2 order as in FRONTEND_MODERN_COMPONENTS_AUDIT (forms first, then layout/nav, then feedback).
  3. **Name and document** — when adding components, we can align names and descriptions with Gallery (e.g. «Alert» for prominent feedback, «Progress bar» for completion status).

---

## 5. How to Enrich: Recommendations with Evidence

### 5.1 Use Component Gallery For

1. **Naming and semantics**
   When introducing a new component, check Gallery for the canonical name and aliases (e.g. Modal/Dialog/Popup) and document in our design system so naming stays consistent.

2. **Gap checklist**
   Use the 58-type list as a checklist against `frontend/src/components/ui/index.ts` and `docs/audit/FRONTEND_MODERN_COMPONENTS_AUDIT.md` to avoid missing a category (e.g. Separator, Skip link, Visually hidden).

3. **Documentation**
   In design system or Storybook, add one-line definitions from Gallery where useful (e.g. «Alert — a way of informing the user of important changes in a prominent way»).

### 5.2 Do Not Use Component Gallery For

- **Code or dependencies** — we do not import or copy code from Component Gallery; it does not provide code.
- **Replacing our audits** — FRONTEND_MODERN_COMPONENTS_AUDIT and TOKENS_SOT remain the source of truth; this audit only adds a cross-reference and enrichment strategy.

### 5.3 Prioritized Enrichment (Aligned with FRONTEND_MODERN_COMPONENTS_AUDIT)

| Priority | Component (Gallery name) | Action | Evidence / note |
|----------|--------------------------|--------|------------------|
| P0 | Input, NumberInput, Select, Button | Already have Button, Input, NumberInput; add **Select** (custom dropdown). | FRONTEND_MODERN_COMPONENTS_AUDIT:152–172; `frontend/src/components/ui/Input.tsx`, `NumberInput.tsx`, `Button.tsx`. |
| P0 | Checkbox, Radio, Textarea | Add unified **Checkbox**, **RadioGroup**, **Textarea**. | FRONTEND_MODERN_COMPONENTS_AUDIT:54–56. |
| P1 | Card, Dialog | Have; ensure variants and docs. | `frontend/src/components/ui/Card.tsx`, `Dialog.tsx`. |
| P1 | Alert | Add **Alert** (success/warning/error/info). | FRONTEND_MODERN_COMPONENTS_AUDIT:89; Gallery: «Alert — a way of informing the user of important changes in a prominent way». |
| P1 | Badge | Add generic **Badge**; keep VipBadge as variant/specialization. | FRONTEND_MODERN_COMPONENTS_AUDIT:90. |
| P1 | Dropdown menu | Add **Dropdown menu** for actions/navigation. | FRONTEND_MODERN_COMPONENTS_AUDIT:72; Gallery: «options hidden by default, shown by interacting with a button». |
| P1 | Tabs | Add content **Tabs** (not only TabBar nav). | FRONTEND_MODERN_COMPONENTS_AUDIT:73. |
| P1 | Progress bar | Add **Progress** (progress bar). | FRONTEND_MODERN_COMPONENTS_AUDIT:91; `frontend/src/features/progress/LiveProgressIndicator.tsx` is feature-specific. |
| P1 | Tooltip | Add **Tooltip**. | FRONTEND_MODERN_COMPONENTS_AUDIT:93; Recharts Tooltip in `frontend/src/features/progress/ProgressCharts.tsx:174` is chart-only. |
| P2 | Accordion, Breadcrumbs, Spinner, Separator | Add when needed; document in design system. | FRONTEND_MODERN_COMPONENTS_AUDIT:73–74, 92. |
| P2 | Table, Pagination | Add for data-heavy views. | FRONTEND_MODERN_COMPONENTS_AUDIT:103–104. |
| A11y | Skip link, Visually hidden | Add for accessibility; Gallery lists them. | No current file:line; recommend adding to tokens or ui. |

### 5.4 Design System Doc Update (When Implementing)

- Add a short «Component taxonomy» section that references Component Gallery as a **naming and semantics reference** (not a dependency).
- Optionally add a table: Gallery name → our component path → one-line definition (e.g. for Alert, Badge, Progress, Tooltip).
- Keep TOKENS_SOT and PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES unchanged; new components must conform to existing token and luxury guidelines.

---

## 6. Summary

| Question | Answer | Evidence |
|----------|--------|----------|
| Should we enrich our design system using Component Gallery? | Yes, as a **reference taxonomy and naming source**, not as code. | §4; §5.1–5.2. |
| How can we enrich? | (1) Use Gallery for naming/semantics and gap checklist; (2) add missing components per FRONTEND_MODERN_COMPONENTS_AUDIT priority; (3) document taxonomy in design system. | §5.1, §5.3, §5.4. |
| Current coverage | We have Button, Card, Dialog, EmptyState, ErrorBoundary, FormField, Input, NumberInput, Skeleton, SegmentedControl, Toast, Toggle; partial Badge (VipBadge), Modal, Tabs (TabBar). Gaps: Alert, Accordion, Breadcrumbs, Checkbox, Radio, Select, Textarea, Dropdown menu, Progress bar, Tooltip, Spinner, Table, Pagination, etc. | §2.2; §3; `frontend/src/components/ui/index.ts`. |

---

## 7. References

- **Component Gallery (source):** <https://component.gallery/components/>
- **Token SoT:** `docs/design/TOKENS_SOT.md`
- **Luxury guidelines:** `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- **Frontend components audit:** `docs/audit/FRONTEND_MODERN_COMPONENTS_AUDIT.md`
- **UI exports:** `frontend/src/components/ui/index.ts`
- **Web token governance:** `docs/sora/SORA_STYLE_QA_CHECKLIST.md` (Web Token Governance)

---

**Audit by:** Agent (web-research + coordinator/designer alignment)
**Branch:** `docs/audit-design-system-component-gallery`
**Colleague docs:** Not modified; only this new audit file added.
