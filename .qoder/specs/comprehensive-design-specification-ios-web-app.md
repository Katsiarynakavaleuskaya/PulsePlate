# Plan: Comprehensive Design Specification for PulsePlate (iOS + Web)

## Goal

Create a single, comprehensive markdown document (`docs/design/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md`) that serves as a complete blueprint for Figma implementation. The document will consolidate all existing design knowledge (tokens, components, pages, brand, interactions) into one actionable spec that a designer can use to build production Figma files.

## Why This Document Is Needed

The project currently has design information fragmented across 15+ files:
- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md` (brand/mood)
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md` (23 CTAs)
- `docs/design/TOKENS_SOT.md` + `frontend/src/styles/tokens.css` (design tokens)
- `docs/audit/DESIGN_CONCEPT_IMPLEMENTATION_AUDIT.md` (gaps audit)
- `docs/analysis/FRONTEND_IOS_VISUAL_ANALYSIS.md` (visual analysis)
- `ios/PulsePlate/DesignSystem/DesignTokens.swift` (iOS tokens)
- Multiple Figma governance docs

No single document tells a designer: "Here are ALL the pages, ALL the components, ALL the states, ALL the tokens, and how they fit together in Figma."

## Output File

**Path:** `docs/design/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md`

This is a docs-only deliverable. No code changes.

## Document Structure (Sections)

### 1. Executive Summary & Purpose
- Document scope: complete Figma blueprint for iOS + Web
- Relationship to existing design docs (references, not duplication)
- Current implementation state (62% per audit) and what this spec covers

### 2. Brand Identity Lock
- Mood: minimal + cozy + intelligent + luxury-clean
- Brand name: PulsePlate
- Mascot: FitChef (lifestyle-friendly, never clinical)
- Slogans: "Always on your Pulse" (EN), "Nutrition * Body * Lifestyle" (subtitle)
- Anti-drift rules (forbidden visual patterns)
- Wellness-safety framing (never medical/diagnostic)

### 3. Design System Tokens (Figma-Ready)

#### 3.1 Color Palette
- **Canonical brand tokens** with hex values:
  - Navy `#0F172A`, Blue `#339FFF`, Green `#20C997`, Red `#FF5D5D`, Gold `#D4AF37`
- Full color scales (50-900 for Navy, Blue, Green, Heart/Red, Gray)
- Semantic color mapping (primary, surface, text, success, warning, error)
- Dark mode variants
- Figma color style naming convention

#### 3.2 Typography
- Font families: Inter (Web), SF Pro (iOS system)
- Type scale: xs (12px) through 5xl (48px)
- Font weights: light (300), regular (400), medium (500), semibold (600), bold (700)
- Line heights: tight (1.25) through loose (2.0)
- Figma text style naming convention

#### 3.3 Spacing
- 4px base unit system
- Scale: xxSmall (2px) through xxLarge (32px)
- Touch target minimum: 44px (Apple HIG)
- Component-specific spacing (button padding, input padding, card padding)

#### 3.4 Border Radius
- Scale: none (0) through 2xl (16px), full (9999px)

#### 3.5 Shadows & Elevation
- sm through xl shadow definitions
- Dark mode shadow variants
- Elevation levels: Card (2), Dropdown (4), Modal (8), Popover (12)

#### 3.6 Motion & Animation
- Duration tokens: Fast (0.15s), Standard (0.25s), Slow (0.4s)
- Spring parameters (response: 0.3, damping: 0.7)
- Reduced-motion considerations

#### 3.7 Z-Index Scale
- base (0) through tooltip (1800)

### 4. Figma File Organization

#### 4.1 Page Structure
```
00_Foundation_Tokens     (colors, type, spacing, shadows)
01_Components            (all reusable components)
02_iOS_Onboarding        (launch, welcome, onboarding flow)
03_iOS_Home              (dashboard)
04_iOS_BMI               (calculator + results)
05_iOS_Plate             (nutrition plate)
06_iOS_Progress          (charts + tracking)
07_iOS_WeeklyPlan        (meal plan reader)
08_iOS_Profile           (settings + preferences)
09_iOS_Paywall           (subscription)
10_Web_Home              (dashboard)
11_Web_BMI               (calculator + results)
12_Web_NutritionSetup    (setup form + results)
13_Web_Plate             (nutrition plate + premium gate)
14_Web_Progress          (charts + export)
15_Web_Profile           (settings)
16_Web_Paywall           (modal paywall)
17_Web_Onboarding        (enter key + onboarding flow)
18_Shared_Icons          (navigation, action, status icons)
19_App_Store_Assets       (screenshots, previews)
```

#### 4.2 Naming Conventions
- Components: `PP/{Platform}/{Category}/{Name}/{Variant}/{State}`
- Colors: `PP/Brand/{Name}` and `PP/Semantic/{Purpose}`
- Text styles: `PP/Type/{Scale}/{Weight}`
- Effects: `PP/Shadow/{Size}`

### 5. Component Library (Reusable Elements)

#### 5.1 Foundation Components
- **GlassCard** - Glass morphism container (backdrop blur, soft border)
  - Variants: neutral, light, dark
  - States: default, hover, pressed
- **PPButton** - Primary action button
  - Variants: primary, secondary, ghost, destructive
  - States: default, hover, pressed, disabled, loading
  - Size: sm, md, lg
  - Touch target: min 44px height
- **PPInput** - Text input field
  - States: default, focused, filled, error, disabled
  - Variants: text, number, password
- **PPCard** - Content card container
  - Variants: elevated, flat, outlined

#### 5.2 Navigation Components
- **TabBar** (Web) - Bottom 6-tab navigation
  - Tab states: default, active (top underline), disabled (lock overlay)
  - Icons: Home, BMI, Plate, Progress, Profile + Pro
- **RootTabs** (iOS) - 6-tab TabView
  - Tab states: default, selected
  - SF Symbols for icons
- **TopBar** - Screen header
  - Variants: with back button, with action buttons

#### 5.3 Data Visualization Components
- **PlateChart** - Circular macronutrient chart (SVG/Canvas)
  - Color coding: Blue (carbs), Green (protein), Red (fat)
  - States: loading (skeleton), populated, empty
- **PlateSegments** (iOS) - Interactive circular segments
  - States: default, selected (scale animation), shimmer loading
- **PlateRing** - Progress ring overlay
  - States: 0% through 100%, shimmer loading
- **ProgressCharts** - Line/Bar/Pie chart set
  - Line: weight/BMI trends
  - Bar: calorie consumed vs burned
  - Pie: macro distribution
  - States: loading, populated, empty, error

#### 5.4 Premium/Paywall Components
- **PremiumGate** - Content overlay for premium content
  - States: locked (dimmed + CTA), unlocked (full content)
- **SoftPaywallHook** - Post-result upsell banner
  - Fields: title, body, CTA text (all from backend contract)
  - States: visible, hidden/null
- **BeforeAfter** (Paywall Modal) - Feature comparison dialog
  - Sections: before (free features), after (pro features)
  - Buttons: purchase CTA, cancel
  - States: open, closing

#### 5.5 Branding Components
- **FitChef Mascot** - Animated character
  - Variants: static, blink, wave, heartbeat, idle
  - Sizes: small (60px), medium (120px), large (180px)
- **MascotBubble** - Speech bubble with FitChef
  - Content: localized text
  - Style: glass morphism background
- **ECG Line** (missing - to be designed)
  - Brand signature visual element
  - Variants: static, animated pulse
- **Brand Slogan**
  - "Always on your Pulse" (EN) / subtitle "Nutrition * Body * Lifestyle"

#### 5.6 State Components
- **Skeleton** - Loading placeholder
- **EmptyState** - Empty data state (icon + message + action)
- **ErrorState** - Error state (icon + message + retry)
- **OfflineIndicator** - Network status banner
- **Toast** - Notification popup (success, error, info)
- **LiveProgressIndicator** - Real-time status dot

### 6. Page-by-Page Specifications

For each page, the spec will define:
- **Layer breakdown** (background, content area, navigation, overlays)
- **Component inventory** (which components appear on this page)
- **Interactive elements** (buttons with all states from CTA matrix)
- **Data requirements** (what API data populates the page)
- **Platform differences** (iOS vs Web variations)
- **Responsive behavior** (breakpoints for web, Dynamic Type for iOS)
- **Accessibility** (labels, contrast, touch targets, focus order)

#### Pages Covered (18 total):

**iOS (8 screens):**
1. Launch Screen - Navy bg + FitChef (180px) + "PulsePlate" title
2. Welcome/Onboarding - Brand intro flow (3-4 screens, currently missing)
3. Home - Dashboard with quick actions, status cards, mascot hint
4. BMI Calculator - Form + results + soft paywall hook
5. Plate - Interactive segments, progress ring, meal actions
6. Progress - Charts (daily segments, completion, metrics)
7. Weekly Plan Reader - Day navigator, meal sections, VIP CTAs
8. Profile - PRO profile form, settings, legal links

**Web (10 pages):**
1. Home - Hero section, API status, premium status, quick nav
2. Enter Key (Onboarding) - API key entry form
3. Onboarding Flow (missing - to be designed)
4. BMI Calculator - Form + results + soft paywall hook
5. Nutrition Setup - Form + PlateChart + MacroCards + results
6. Plate - PremiumGate wrapper, nutrition dashboard
7. Progress - SegmentedControl + ProgressCharts + export
8. Profile - API key status, about section
9. Pro Paywall - BeforeAfter modal with feature comparison
10. App Store Assets page (screenshots template)

### 7. Button & CTA Specification

Complete specification for all 23 CTAs from the Button Action Matrix:

For each button:
- Visual properties (color, size, border radius, icon)
- All interaction states (default, hover, pressed, focused, disabled, loading, error)
- Platform-specific rendering (Web: CSS, iOS: SwiftUI)
- Auth/feature gate behavior (what happens when gated)
- Figma node ID placeholder (TBD until Design URLs available)

### 8. Accessibility Requirements
- WCAG AA minimum contrast (4.5:1 body, 3:1 large text)
- Touch targets: 44x44pt minimum (Apple HIG)
- Focus indicators: 2px solid outline
- Screen reader support (ARIA for web, VoiceOver for iOS)
- Dynamic Type support (iOS)
- Reduced motion support
- Color-blind friendly palette verification

### 9. Responsive & Adaptive Behavior
- Web breakpoints (mobile, tablet, desktop)
- iOS device matrix (iPhone SE through iPhone 16 Pro Max)
- iPad layout considerations
- Dark mode specifications (all semantic colors)

### 10. App Store Assets Specification
- Screenshot templates (6.7", 6.1")
- Required 5 screenshots: Welcome, My Plate, Weekly Plan, Progress, Holistic Health
- App icon specifications (all sizes from 20x20 to 1024x1024)
- App Preview video storyboard (15-30 seconds)

### 11. Implementation Gap Tracker
- Table mapping each spec section to current implementation status
- Cross-reference with DESIGN_CONCEPT_IMPLEMENTATION_AUDIT.md
- Priority tags (P0-A, P0-B, P1) aligned with release readiness

## Key Source Files Referenced

| File | Purpose |
|------|---------|
| `frontend/src/styles/tokens.css` | Canonical web design tokens |
| `frontend/src/styles/tokens.ts` | TypeScript token exports |
| `ios/PulsePlate/DesignSystem/DesignTokens.swift` | iOS design tokens |
| `ios/PulsePlate/DesignSystem/PPTypography.swift` | iOS typography system |
| `frontend/src/config/routes.ts` | Web routing/page structure |
| `ios/PulsePlate/Views/RootTabs.swift` | iOS tab navigation |
| `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md` | Visual guidelines |
| `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md` | 23 CTAs registry |
| `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md` | QA checklist |
| `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md` | Asset generation |
| `docs/sora/SORA_STYLE_QA_CHECKLIST.md` | Style QA gates |
| `docs/audit/DESIGN_CONCEPT_IMPLEMENTATION_AUDIT.md` | Implementation audit |
| `docs/analysis/FRONTEND_IOS_VISUAL_ANALYSIS.md` | Visual analysis |
| `docs/design/TOKENS_SOT.md` | Token governance |
| `docs/design/figma-manifest.json` | Figma manifest |
| `docs/design/EMBLEM_CORE_v1.0_LOCK.md` | App icon lock spec |

## Constraints

- **Docs-only**: No code changes in this deliverable
- **No duplication**: Reference existing docs, don't copy large sections verbatim
- **Figma-actionable**: Every spec item should be directly implementable in Figma
- **Platform parity**: Cover both iOS and Web for every component/page
- **Brand compliance**: All specs must pass Luxury UI Review Checklist gates
- **Wellness-safe**: No medical/clinical framing in any spec text
- **English-first**: Primary language English (RU translations noted where relevant for i18n)

## Implementation Steps

1. Read all source token files to extract exact inline values:
   - `frontend/src/styles/tokens.css` (full color scales, spacing, typography, shadows, z-index)
   - `ios/PulsePlate/DesignSystem/DesignTokens.swift` (iOS token values)
   - `ios/PulsePlate/DesignSystem/PPTypography.swift` (iOS type system)
2. Read key page/component files for accurate layer and element descriptions:
   - All page files in `frontend/src/pages/` and `ios/PulsePlate/Views/`
   - Key components (GlassCard, PlateSegments, PremiumGate, TabBar, etc.)
3. Write the comprehensive spec document at `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md`
   - All 11 sections as outlined above
   - Inline exact token values (hex, px, rem) throughout
   - Full specs for missing/new elements (ECG line, onboarding, FitChef web)
   - All 23 CTAs from the Button Matrix with visual specs
4. Verify the document

## Verification

After writing the document:
1. Run `python scripts/ci/check_docs_phase1_gates.py --files docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md` to verify evidence anchors
2. Validate that all 23 CTAs from the Button Matrix are covered
3. Verify all token values match `frontend/src/styles/tokens.css` source
4. Confirm all 18 pages (8 iOS + 10 Web) are specified
5. Check cross-references to existing docs are accurate
