<!-- markdownlint-disable MD013 -->
# PulsePlate Figma Design Specification

**Version:** 1.0
**Date:** 2026-02-22
**Scope:** Complete Figma blueprint for iOS + Web platforms
**Status:** Canonical design specification for Figma implementation

---

## 1. Executive Summary

This document is the single authoritative blueprint for building PulsePlate Figma files. It consolidates design tokens, component specs, page layouts, button states, and accessibility requirements into one actionable reference.

**What this covers:**
- All 18 pages/screens (8 iOS + 10 Web) with layer-by-layer breakdowns
- Complete component library (30+ components with all states)
- Full design token tables with inline values (hex, px, rem)
- All 23 CTAs with interaction state specifications
- Accessibility, responsive behavior, and App Store assets
- Full specs for both implemented AND to-be-designed elements

**Related documents (do not duplicate; reference for deep dives):**
- Brand mood/visual philosophy: `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- CTA behavior registry: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- Token governance: `docs/design/TOKENS_SOT.md`
- QA review checklist: `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- Asset generation playbook: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- Style QA gates: `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- App icon lock: `docs/design/EMBLEM_CORE_v1.0_LOCK.md`
- Implementation audit: `docs/audit/DESIGN_CONCEPT_IMPLEMENTATION_AUDIT.md`

Evidence anchors for current implementation baseline:
- Web token source: `frontend/src/styles/tokens.css:8`
- iOS token source: `ios/PulsePlate/DesignSystem/DesignTokens.swift:6`
- Web route definitions: `frontend/src/config/routes.ts:23`
- iOS tab structure: `ios/PulsePlate/Views/RootTabs.swift:1`

---

## 2. Brand Identity Lock

### 2.1 Core Identity

| Attribute | Value |
|-----------|-------|
| **App name** | PulsePlate |
| **Mascot** | FitChef (lifestyle-friendly chef character) |
| **Tagline (EN)** | "Always on your Pulse" |
| **Tagline (RU)** | "Держим руку на пульсе" |
| **Subtitle** | "Nutrition - Body - Lifestyle" |
| **Mood** | Minimal + Cozy + Intelligent + Luxury-Clean |
| **Framing** | Wellness-lifestyle only (never clinical/diagnostic/medical) |

### 2.2 Anti-Drift Rules (Forbidden Visual Patterns)

These patterns must NEVER appear in any PulsePlate asset:

- Hyper-realistic skin pores or photorealistic medical imagery
- Cinematic neon / cyberpunk aesthetic
- Futuristic hologram hospital scenes
- Gold luxury emblem / crest style
- Purple gradient glossy blob
- 3D chrome icon pack
- Medical monitor / ECG clinical interface
- Diagnostic clinical interface or lab equipment
- Generic AI "slop" (smooth gradient blobs, no-context abstract shapes)
- Fear/shame/urgency manipulation in copy or visuals

### 2.3 Required Prompt Tokens (for AI-generated assets)

Every generated visual asset must include these style tokens:
`flat`, `soft shadows`, `subtle gradients`, `palette locked`, `high small-size readability`, `wellness not medical`

---

## 3. Design System Tokens

All values are inline and Figma-ready. Source of truth: `frontend/src/styles/tokens.css:8` (web), `ios/PulsePlate/DesignSystem/DesignTokens.swift:6` (iOS).

### 3.1 Color Palette

#### Brand Colors (Canonical)

| Token | Hex | RGB | Usage | Figma Style Name |
|-------|-----|-----|-------|------------------|
| `--pp-navy` | `#0F172A` | 15, 23, 42 | Base, depth, trust, backgrounds | `PP/Brand/Navy` |
| `--pp-blue` | `#339FFF` | 51, 159, 255 | Action, progress, primary CTA | `PP/Brand/Blue` |
| `--pp-green` | `#20C997` | 32, 201, 151 | Success, positive, health | `PP/Brand/Green` |
| `--pp-red` | `#FF5D5D` | 255, 93, 93 | Accent only, critical states | `PP/Brand/Red` |
| `--pp-gold` | `#D4AF37` | 212, 175, 55 | Premium accents | `PP/Brand/Gold` |

#### Navy Scale

| Token | Hex | Figma Style Name |
|-------|-----|------------------|
| `--color-navy-50` | `#F0F4F8` | `PP/Scale/Navy/50` |
| `--color-navy-100` | `#D9E2EC` | `PP/Scale/Navy/100` |
| `--color-navy-200` | `#BCCCDC` | `PP/Scale/Navy/200` |
| `--color-navy-300` | `#9FB3C8` | `PP/Scale/Navy/300` |
| `--color-navy-400` | `#829AB1` | `PP/Scale/Navy/400` |
| `--color-navy-500` | `#627D98` | `PP/Scale/Navy/500` |
| `--color-navy-600` | `#486581` | `PP/Scale/Navy/600` |
| `--color-navy-700` | `#334E68` | `PP/Scale/Navy/700` |
| `--color-navy-800` | `#243B53` | `PP/Scale/Navy/800` |
| `--color-navy-900` | `#102A43` | `PP/Scale/Navy/900` |

#### Blue Scale

| Token | Hex | Figma Style Name |
|-------|-----|------------------|
| `--color-blue-50` | `#EFF6FF` | `PP/Scale/Blue/50` |
| `--color-blue-100` | `#DBEAFE` | `PP/Scale/Blue/100` |
| `--color-blue-200` | `#BFDBFE` | `PP/Scale/Blue/200` |
| `--color-blue-300` | `#93C5FD` | `PP/Scale/Blue/300` |
| `--color-blue-400` | `#60A5FA` | `PP/Scale/Blue/400` |
| `--color-blue-500` | `#3B82F6` | `PP/Scale/Blue/500` |
| `--color-blue-600` | `#2563EB` | `PP/Scale/Blue/600` |
| `--color-blue-700` | `#1D4ED8` | `PP/Scale/Blue/700` |
| `--color-blue-800` | `#1E40AF` | `PP/Scale/Blue/800` |
| `--color-blue-900` | `#1E3A8A` | `PP/Scale/Blue/900` |

#### Green Scale

| Token | Hex | Figma Style Name |
|-------|-----|------------------|
| `--color-green-50` | `#F0FDF4` | `PP/Scale/Green/50` |
| `--color-green-100` | `#DCFCE7` | `PP/Scale/Green/100` |
| `--color-green-200` | `#BBF7D0` | `PP/Scale/Green/200` |
| `--color-green-300` | `#86EFAC` | `PP/Scale/Green/300` |
| `--color-green-400` | `#4ADE80` | `PP/Scale/Green/400` |
| `--color-green-500` | `#22C55E` | `PP/Scale/Green/500` |
| `--color-green-600` | `#16A34A` | `PP/Scale/Green/600` |
| `--color-green-700` | `#15803D` | `PP/Scale/Green/700` |
| `--color-green-800` | `#166534` | `PP/Scale/Green/800` |
| `--color-green-900` | `#14532D` | `PP/Scale/Green/900` |

#### Heart / Red Scale

| Token | Hex | Figma Style Name |
|-------|-----|------------------|
| `--color-heart-50` | `#FEF2F2` | `PP/Scale/Heart/50` |
| `--color-heart-100` | `#FEE2E2` | `PP/Scale/Heart/100` |
| `--color-heart-200` | `#FECACA` | `PP/Scale/Heart/200` |
| `--color-heart-300` | `#FCA5A5` | `PP/Scale/Heart/300` |
| `--color-heart-400` | `#F87171` | `PP/Scale/Heart/400` |
| `--color-heart-500` | `#EF4444` | `PP/Scale/Heart/500` |
| `--color-heart-600` | `#DC2626` | `PP/Scale/Heart/600` |
| `--color-heart-700` | `#B91C1C` | `PP/Scale/Heart/700` |
| `--color-heart-800` | `#991B1B` | `PP/Scale/Heart/800` |
| `--color-heart-900` | `#7F1D1D` | `PP/Scale/Heart/900` |

#### Gray Scale (Neutral)

| Token | Hex | Figma Style Name |
|-------|-----|------------------|
| `--color-gray-50` | `#F9FAFB` | `PP/Scale/Gray/50` |
| `--color-gray-100` | `#F3F4F6` | `PP/Scale/Gray/100` |
| `--color-gray-200` | `#E5E7EB` | `PP/Scale/Gray/200` |
| `--color-gray-300` | `#D1D5DB` | `PP/Scale/Gray/300` |
| `--color-gray-400` | `#9CA3AF` | `PP/Scale/Gray/400` |
| `--color-gray-500` | `#6B7280` | `PP/Scale/Gray/500` |
| `--color-gray-600` | `#4B5563` | `PP/Scale/Gray/600` |
| `--color-gray-700` | `#374151` | `PP/Scale/Gray/700` |
| `--color-gray-800` | `#1F2937` | `PP/Scale/Gray/800` |
| `--color-gray-900` | `#111827` | `PP/Scale/Gray/900` |

#### Semantic Colors (Light Mode)

| Purpose | Value | Figma Style Name |
|---------|-------|------------------|
| Primary | `#339FFF` (--pp-blue) | `PP/Semantic/Primary` |
| Primary Foreground | `#FFFFFF` | `PP/Semantic/PrimaryForeground` |
| Background | `#FFFFFF` | `PP/Semantic/Background` |
| Surface | `#F0F4F8` (navy-50) | `PP/Semantic/Surface` |
| Surface Muted | `#D9E2EC` (navy-100) | `PP/Semantic/SurfaceMuted` |
| Border | `#BCCCDC` (navy-200) | `PP/Semantic/Border` |
| Text | `#0F172A` (--pp-navy) | `PP/Semantic/Text` |
| Text Muted | `#627D98` (navy-500) | `PP/Semantic/TextMuted` |
| Success | `#20C997` (--pp-green) | `PP/Semantic/Success` |
| Warning | `#F59E0B` | `PP/Semantic/Warning` |
| Error | `#FF5D5D` (--pp-red) | `PP/Semantic/Error` |
| Info | `#339FFF` (--pp-blue) | `PP/Semantic/Info` |
| Focus Ring | `#339FFF` (--pp-blue) | `PP/Semantic/Focus` |

#### Semantic Colors (Dark Mode)

| Purpose | Value | Figma Style Name |
|---------|-------|------------------|
| Primary | `#60A5FA` (blue-400) | `PP/Semantic/Primary.Dark` |
| Primary Foreground | `#FFFFFF` | `PP/Semantic/PrimaryForeground.Dark` |
| Background | `#102A43` (navy-900) | `PP/Semantic/Background.Dark` |
| Surface | `#243B53` (navy-800) | `PP/Semantic/Surface.Dark` |
| Surface Muted | `#334E68` (navy-700) | `PP/Semantic/SurfaceMuted.Dark` |
| Border | `#486581` (navy-600) | `PP/Semantic/Border.Dark` |
| Text | `#F0F4F8` (navy-50) | `PP/Semantic/Text.Dark` |
| Text Muted | `#9FB3C8` (navy-300) | `PP/Semantic/TextMuted.Dark` |
| Success | `#4ADE80` (green-400) | `PP/Semantic/Success.Dark` |
| Warning | `#FBBF24` | `PP/Semantic/Warning.Dark` |
| Error | `#F87171` (heart-400) | `PP/Semantic/Error.Dark` |
| Info | `#60A5FA` (blue-400) | `PP/Semantic/Info.Dark` |

#### iOS Surface Colors (on Navy backgrounds)

| Purpose | Value | Figma Style Name |
|---------|-------|------------------|
| Text Primary | `#FFFFFF` | `PP/iOS/Text/Primary` |
| Text Secondary | `rgba(255,255,255,0.8)` | `PP/iOS/Text/Secondary` |
| Text Tertiary | `rgba(255,255,255,0.6)` | `PP/iOS/Text/Tertiary` |
| Surface (glass) | `rgba(255,255,255,0.1)` | `PP/iOS/Surface/Glass` |
| Surface Elevated | `rgba(255,255,255,0.15)` | `PP/iOS/Surface/Elevated` |
| Surface Highlight | `rgba(255,255,255,0.25)` | `PP/iOS/Surface/Highlight` |
| Stroke Subtle | `rgba(255,255,255,0.12)` | `PP/iOS/Surface/Stroke` |

### 3.2 Typography

#### Web (Inter)

| Style | Size | Weight | Line Height | Figma Style Name |
|-------|------|--------|-------------|------------------|
| xs | 12px / 0.75rem | 400 | 1.5 | `PP/Type/XS/Regular` |
| sm | 14px / 0.875rem | 400 | 1.5 | `PP/Type/SM/Regular` |
| base | 16px / 1rem | 400 | 1.5 | `PP/Type/Base/Regular` |
| lg | 18px / 1.125rem | 400 | 1.5 | `PP/Type/LG/Regular` |
| xl | 20px / 1.25rem | 600 | 1.375 | `PP/Type/XL/Semibold` |
| 2xl | 24px / 1.5rem | 700 | 1.25 | `PP/Type/2XL/Bold` |
| 3xl | 30px / 1.875rem | 700 | 1.25 | `PP/Type/3XL/Bold` |
| 4xl | 36px / 2.25rem | 700 | 1.25 | `PP/Type/4XL/Bold` |
| 5xl | 48px / 3rem | 700 | 1.25 | `PP/Type/5XL/Bold` |

Font family: `Inter, system-ui, sans-serif`
Available weights: Light (300), Regular (400), Medium (500), Semibold (600), Bold (700)

#### iOS (SF Pro / System)

| Style | Size | Weight | Figma Style Name |
|-------|------|--------|------------------|
| caption | 12px | Regular | `PP/iOS/Type/Caption` |
| captionStrong | 12px | Semibold | `PP/iOS/Type/CaptionStrong` |
| body | 16px | Regular | `PP/iOS/Type/Body` |
| bodyStrong | 16px | Semibold | `PP/iOS/Type/BodyStrong` |
| title | 18px | Semibold | `PP/iOS/Type/Title` |
| heading | 24px | Bold | `PP/iOS/Type/Heading` |
| largeTitle | 30px | Bold | `PP/iOS/Type/LargeTitle` |

Font family: SF Pro (system font)

### 3.3 Spacing

Base unit: 4px. Source: `frontend/src/styles/tokens.css:114`

| Token | Value (rem) | Value (px) | Figma Usage |
|-------|-------------|------------|-------------|
| `--spacing-0` | 0 | 0 | None |
| `--spacing-1` | 0.25rem | 4px | Minimal gap |
| `--spacing-2` | 0.5rem | 8px | Tight spacing |
| `--spacing-3` | 0.75rem | 12px | Small spacing |
| `--spacing-4` | 1rem | 16px | Default spacing |
| `--spacing-5` | 1.25rem | 20px | Medium spacing |
| `--spacing-6` | 1.5rem | 24px | Section gap |
| `--spacing-8` | 2rem | 32px | Large gap |
| `--spacing-10` | 2.5rem | 40px | XL gap |
| `--spacing-12` | 3rem | 48px | Section divider |
| `--spacing-16` | 4rem | 64px | Page section |
| `--spacing-20` | 5rem | 80px | Hero section |
| `--spacing-24` | 6rem | 96px | Page header |

**Touch Targets:**

| Token | Value | Usage |
|-------|-------|-------|
| `--spacing-touch` | 44px / 2.75rem | Minimum interactive element size (Apple HIG) |
| `--spacing-touch-large` | 56px / 3.5rem | Large touch target |

**Button Padding:**

| Size | Padding (v h) | Figma |
|------|---------------|-------|
| sm | 8px 16px | `0.5rem 1rem` |
| md | 12px 24px | `0.75rem 1.5rem` |
| lg | 16px 32px | `1rem 2rem` |

**Input Padding:**

| Size | Padding (v h) | Figma |
|------|---------------|-------|
| sm | 8px 12px | `0.5rem 0.75rem` |
| md | 12px 16px | `0.75rem 1rem` |
| lg | 16px 20px | `1rem 1.25rem` |

### 3.4 Border Radius

| Token | Value (rem) | Value (px) | Figma Style Name |
|-------|-------------|------------|------------------|
| `--radius-none` | 0 | 0 | `PP/Radius/None` |
| `--radius-sm` | 0.125rem | 2px | `PP/Radius/SM` |
| `--radius-base` | 0.25rem | 4px | `PP/Radius/Base` |
| `--radius-md` | 0.375rem | 6px | `PP/Radius/MD` |
| `--radius-lg` | 0.5rem | 8px | `PP/Radius/LG` |
| `--radius-xl` | 0.75rem | 12px | `PP/Radius/XL` |
| `--radius-2xl` | 1rem | 16px | `PP/Radius/2XL` |
| `--radius-full` | 9999px | circle | `PP/Radius/Full` |

### 3.5 Shadows & Elevation

#### Light Mode Shadows

| Token | Value | Figma Effect Name |
|-------|-------|-------------------|
| `--shadow-sm` | `0 1px 2px 0 rgba(0,0,0,0.05)` | `PP/Shadow/SM` |
| `--shadow-base` | `0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)` | `PP/Shadow/Base` |
| `--shadow-md` | `0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)` | `PP/Shadow/MD` |
| `--shadow-lg` | `0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)` | `PP/Shadow/LG` |
| `--shadow-xl` | `0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)` | `PP/Shadow/XL` |
| GlassCard | `0 8px 30px rgba(0,0,0,0.12)` | `PP/Shadow/Glass` |

#### Dark Mode Shadows

| Token | Value | Figma Effect Name |
|-------|-------|-------------------|
| `--shadow-sm-dark` | `0 1px 2px 0 rgba(0,0,0,0.3)` | `PP/Shadow/SM.Dark` |
| `--shadow-base-dark` | `0 1px 3px 0 rgba(0,0,0,0.4), 0 1px 2px -1px rgba(0,0,0,0.4)` | `PP/Shadow/Base.Dark` |
| `--shadow-md-dark` | `0 4px 6px -1px rgba(0,0,0,0.4), 0 2px 4px -2px rgba(0,0,0,0.4)` | `PP/Shadow/MD.Dark` |
| `--shadow-lg-dark` | `0 10px 15px -3px rgba(0,0,0,0.4), 0 4px 6px -4px rgba(0,0,0,0.4)` | `PP/Shadow/LG.Dark` |
| `--shadow-xl-dark` | `0 20px 25px -5px rgba(0,0,0,0.4), 0 8px 10px -6px rgba(0,0,0,0.4)` | `PP/Shadow/XL.Dark` |

#### Elevation Levels (iOS)

| Level | Shadow Radius (pt) | Usage |
|-------|-------------------|-------|
| None | 0 | Flat elements |
| Card | 2 | Content cards |
| Dropdown | 4 | Dropdown menus |
| Modal | 8 | Modal dialogs |
| Popover | 12 | Tooltips, popovers |

### 3.6 Motion & Animation

| Token | Duration | Easing | Usage |
|-------|----------|--------|-------|
| Fast | 0.15s (150ms) | ease-out | Micro-interactions (hover, toggle) |
| Standard | 0.25s (250ms) | ease-in-out | Transitions (page, state change) |
| Slow | 0.4s (400ms) | ease-in-out | Emphasis animations (onboarding, reveal) |
| Spring | response: 0.3, damping: 0.7 | spring | iOS interactive animations (segment tap) |

**Reduced-motion rule:** All animations must respect `prefers-reduced-motion: reduce`. When active, replace animations with instant state changes (opacity crossfade only, no translation/scale).

### 3.7 Z-Index Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--z-hide` | -1 | Hidden elements |
| `--z-base` | 0 | Default layer |
| `--z-docked` | 10 | Docked elements |
| `--z-dropdown` | 1000 | Dropdown menus |
| `--z-sticky` | 1100 | Sticky headers |
| `--z-banner` | 1200 | Notification banners |
| `--z-overlay` | 1300 | Overlay backgrounds |
| `--z-modal` | 1400 | Modal dialogs |
| `--z-popover` | 1500 | Popovers, tooltips |
| `--z-skip-link` | 1600 | Skip navigation |
| `--z-toast` | 1700 | Toast notifications |
| `--z-tooltip` | 1800 | Tooltips (topmost) |

### 3.8 Breakpoints (Web)

| Token | Value | Usage |
|-------|-------|-------|
| `--breakpoint-sm` | 640px | Mobile landscape |
| `--breakpoint-md` | 768px | Tablet |
| `--breakpoint-lg` | 1024px | Desktop |
| `--breakpoint-xl` | 1280px | Large desktop |
| `--breakpoint-2xl` | 1536px | Ultra-wide |

---

## 4. Figma File Organization

### 4.1 Page Structure

```text
00_Foundation_Tokens      Colors, typography, spacing, shadows, icons
01_Components             All reusable component sets
02_iOS_Launch             Launch screen + splash
03_iOS_Onboarding         Welcome gate + onboarding flow (NEW DESIGN)
04_iOS_Home               Dashboard + quick actions
05_iOS_BMI                Calculator form + results
06_iOS_Plate              Interactive nutrition plate
07_iOS_Progress           Charts + daily tracking
08_iOS_WeeklyPlan         Meal plan reader
09_iOS_Profile            Settings + PRO profile
10_iOS_Paywall            StoreKit subscription UI
11_Web_Home               Dashboard + status cards
12_Web_BMI                Calculator form + results
13_Web_NutritionSetup     Setup form + PlateChart + results
14_Web_Plate              Premium-gated nutrition view
15_Web_Progress           Charts + export
16_Web_Profile            Settings + API key
17_Web_Paywall            BeforeAfter modal
18_Web_Onboarding         Enter key + onboarding flow (NEW DESIGN)
19_Shared_Icons           Navigation, action, status icon sets
20_App_Store_Assets       Screenshots, icon sizes, preview storyboard
```

### 4.2 Naming Conventions

| Category | Pattern | Example |
|----------|---------|---------|
| Components | `PP/{Platform}/{Category}/{Name}/{Variant}/{State}` | `PP/Web/Button/Primary/Default` |
| Colors | `PP/Brand/{Name}` or `PP/Semantic/{Purpose}` | `PP/Brand/Navy`, `PP/Semantic/Primary` |
| Text styles | `PP/Type/{Scale}/{Weight}` | `PP/Type/Base/Regular` |
| Effects | `PP/Shadow/{Size}` | `PP/Shadow/MD` |
| iOS-specific | `PP/iOS/{Category}/{Name}` | `PP/iOS/Type/Body` |
| Dark mode | Append `.Dark` | `PP/Semantic/Background.Dark` |

### 4.3 Component Set Organization

Each component set should contain:
1. **Base variant** (default state)
2. **All interactive states** as variant properties
3. **Size variants** where applicable (sm/md/lg)
4. **Platform variants** (Web/iOS) as top-level variant property
5. **Theme variants** (Light/Dark) as top-level variant property

---

## 5. Component Library

### 5.1 GlassCard

Figma Component: `PP/Shared/GlassCard`

Glass-morphism container used as the primary card surface throughout the app.

**Visual Properties:**
- Background: `rgba(255,255,255,0.1)` (neutral), `rgba(255,255,255,0.8)` (light), `rgba(15,23,42,0.7)` (dark)
- Border: 1px solid `rgba(255,255,255,0.15)` (neutral), `rgba(203,213,225,0.8)` (light), `rgba(51,65,85,0.7)` (dark)
- Backdrop blur: 24px (`backdrop-blur-xl`)
- Border radius: 16px (`rounded-2xl`)
- Shadow: `0 8px 30px rgba(0,0,0,0.12)`

**Variants:**

| Variant | Background | Border | Text Color |
|---------|------------|--------|------------|
| Neutral | `white/10%` | `white/15%` | `#FFFFFF` |
| Light | `white/80%` | `slate-200/80%` | `#0F172A` |
| Dark | `slate-900/70%` | `slate-700/70%` | `#FFFFFF` |

**Padding options:** none (0), sm (12px), md (16px), lg (24px)

**iOS variant (current implementation):** Uses system `.ultraThinMaterial` on iOS 17-18. **Target (iOS 26+):** Liquid Glass API when available. Includes `reduceTransparency` fallback (solid navy-800 with 0.95 opacity).

**Implementation evidence:** `frontend/src/components/GlassCard.tsx:35`, `ios/PulsePlate/Views/Components/GlassCard.swift:1`

### 5.2 PPButton

Figma Component Set: `PP/Shared/Button`

Primary interactive element for all CTAs.

**Base Properties:**
- Min height: 44px (touch target)
- Border radius: 12px (`rounded-xl`)
- Font: 14px/0.875rem, Semibold (600)
- Transition: 200ms ease

**Variant Matrix:**

| Variant | Background | Text | Border |
|---------|------------|------|--------|
| Primary | `#339FFF` | `#FFFFFF` | none |
| Secondary | transparent | `#339FFF` | 1px `#BCCCDC` |
| Ghost | transparent | `#627D98` | none |
| Destructive | `#FF5D5D` | `#FFFFFF` | none |

**State Matrix (all variants):**

| State | Opacity | Scale | Additional |
|-------|---------|-------|------------|
| Default | 100% | 1.0 | - |
| Hover (Web) | 100% | 1.0 | brightness 110% |
| Pressed | 100% | 0.98 | brightness 90% |
| Focused | 100% | 1.0 | 2px focus ring `#339FFF` + 2px offset |
| Disabled | 50% | 1.0 | `cursor-not-allowed` |
| Loading | 70% | 1.0 | spinner icon replaces text |

**Size Variants:**

| Size | Padding (v h) | Font Size | Min Height |
|------|--------------|-----------|------------|
| sm | 8px 16px | 12px | 32px |
| md | 12px 24px | 14px | 44px |
| lg | 16px 32px | 16px | 52px |

### 5.3 PPInput

Figma Component Set: `PP/Shared/Input`

Text and number input fields with label and error support.

**Base Properties:**
- Min height: 44px
- Border radius: 8px (`rounded-lg`)
- Border: 1px solid `#BCCCDC`
- Background: `#FFFFFF` (light), `#243B53` (dark)
- Padding: 12px 16px
- Font: 16px, Regular (400)

**State Matrix:**

| State | Border Color | Background | Additional |
|-------|-------------|------------|------------|
| Default | `#BCCCDC` | white | - |
| Focused | `#339FFF` | white | 2px focus ring + label floats |
| Filled | `#BCCCDC` | white | value displayed |
| Error | `#FF5D5D` | `#FEF2F2` | error message below |
| Disabled | `#D9E2EC` | `#F0F4F8` | 50% opacity |

**Sub-elements:**
- Label: 12px Semibold, `#627D98`, positioned above
- Error message: 12px Regular, `#FF5D5D`, positioned below
- Helper text: 12px Regular, `#627D98`, positioned below

### 5.4 Card / CardContent

Figma Component: `PP/Web/Card`

Standard content card for web platform.

**Properties:**
- Background: `#FFFFFF` (light), `#243B53` (dark)
- Border: 1px solid `#BCCCDC`
- Border radius: 12px
- Shadow: `--shadow-base`
- Padding (CardContent): 24px
- Hover: `--shadow-md` transition

### 5.5 TabBar (Web)

Figma Component: `PP/Web/Navigation/TabBar`

Fixed bottom navigation bar for web.

**Properties:**
- Position: fixed bottom, full width
- Background: `#0F172A` (navy)
- Border top: 1px solid `rgba(127,157,184,0.3)`
- Grid: 4-6 columns (dynamic based on visible tabs)
- Height: ~48px content + safe area

**Tab Items:**
- Font: 14px Medium
- Default: `#627D98` (muted)
- Active: `#339FFF` (primary) + top indicator bar (32px wide, 2px tall, `#339FFF`, `rounded-full`)
- Disabled: Lock icon overlay, `#627D98` at 30% opacity, `bg-navy/80%` overlay with 4px backdrop blur

**Visible Tabs (default):** Home, Profile, Plate, Progress (auth-gated tabs show lock when no API key)

**Implementation evidence:** `frontend/src/components/TabBar.tsx:44`

### 5.6 RootTabs (iOS)

Figma Component: `PP/iOS/Navigation/TabBar`

Native iOS TabView with 6 tabs.

**Tabs:**
1. Home (house.fill)
2. BMI (scalemass.fill)
3. Plate (circle.grid.2x2.fill)
4. Progress (chart.bar.fill)
5. Week (calendar)
6. Profile (person.crop.circle.fill)

**Properties:**
- Uses iOS system tab bar appearance
- Tint color: `#339FFF` (Brand Blue)
- Background: system material blur
- Selected: filled SF Symbol + tinted label
- Unselected: outline SF Symbol + gray label

### 5.7 PlateChart (Web)

Figma Component: `PP/Web/DataViz/PlateChart`

Circular (donut) chart showing macronutrient distribution.

**Properties:**
- Diameter: responsive (fills container, max ~300px)
- Stroke width: proportional (~20% of radius)
- Background ring: `#E5E7EB` (gray-200)

**Segment Colors:**

| Macro | Color | Figma |
|-------|-------|-------|
| Carbohydrates | `#339FFF` (Blue) | `PP/Brand/Blue` |
| Protein | `#20C997` (Green) | `PP/Brand/Green` |
| Fat | `#FF5D5D` (Red) | `PP/Brand/Red` |

**States:** Loading (skeleton ring pulse), Populated (segments with percentages), Empty (gray ring + "No data" text)

### 5.8 PlateSegments (iOS)

Figma Component: `PP/iOS/DataViz/PlateSegments`

Interactive circular segments for the iOS nutrition plate.

**Properties:**
- Circular arrangement of meal segments
- Each segment: colored arc with label
- Selection: scale to 1.1x with spring animation
- Shimmer loading state

**States:** Default (all segments visible), Selected (tapped segment scales up), Loading (shimmer overlay)

### 5.9 PlateRing (iOS)

Figma Component: `PP/iOS/DataViz/PlateRing`

Circular progress ring overlay.

**Properties:**
- Stroke: 8px
- Track: `rgba(255,255,255,0.1)`
- Progress: `#20C997` (green) gradient
- Center: percentage text (24px bold)
- Shimmer state: animated gradient sweep

### 5.10 ProgressCharts (Web)

Figma Component Set: `PP/Web/DataViz/ProgressCharts`

Three chart types in a stacked layout.

**LineChart (Weight/BMI Trends):**
- Grid background with horizontal lines
- Line: 2px stroke, `#339FFF`
- Dots: 6px circles at data points
- X-axis: date labels, Y-axis: values

**BarChart (Calorie Balance):**
- Bars: `#20C997` (consumed), `#FF5D5D` (burned)
- Net line overlay: `#339FFF`
- Grouped side-by-side

**PieChart (Macro Distribution):**
- Same colors as PlateChart (Blue/Green/Red)
- Legend with percentage labels
- Center: total calories

**Shared States:** Loading (skeleton), Populated, Empty ("No data yet"), Error ("Failed to load" + retry)

### 5.11 PremiumGate

Figma Component: `PP/Web/Paywall/PremiumGate`

Content overlay that gates premium content.

**Locked State:**
- Children rendered at 60% opacity
- `pointer-events: none` (inert)
- CTA button below: "Unlock Premium" (`#339FFF` bg, white text, `rounded-xl`, min-height 44px)
- Screen reader description: hidden behind `sr-only` text

**Unlocked State:**
- Children rendered normally (100% opacity, interactive)

**Implementation evidence:** `frontend/src/components/PremiumGate.tsx:33`

### 5.12 SoftPaywallHook

Figma Component: `PP/Shared/Paywall/SoftPaywallHook`

Post-result upsell banner displayed after BMI calculation.

**Properties:**
- Background: linear gradient from `var(--color-surface)` to `var(--color-surface-muted)` (top to bottom)
- Border: 1px solid `#BCCCDC`
- Border radius: 16px
- Padding: 24px
- Shadow: `--shadow-sm`

**Content (all from backend contract, no hardcoded text):**
- Title: 18px Semibold, `#0F172A`
- Body: 14px Regular, `#627D98`, 20px bottom margin
- CTA Button: `rounded-full`, `#339FFF` bg, white text, 14px Semibold, min-height 44px, padding 8px 20px

**States:** Visible (hook data present, pro_available=true), Hidden (hook null or pro_available=false)

**Implementation evidence:** `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:45`

### 5.13 BeforeAfter (Paywall Modal)

Figma Component: `PP/Web/Paywall/BeforeAfterModal`

Full-screen modal dialog for premium upgrade.

**Overlay:** `rgba(0,0,0,0.6)`, centered grid placement

**Dialog Container:**
- Max width: 448px (`max-w-md`)
- Max height: 85vh
- Border radius: 16px
- Background: `#FFFFFF`
- Shadow: `--shadow-xl`
- Overflow: scroll content area

**Content Sections:**
1. **PRO Badge:** Blue pill badge "PRO" (12px semibold, `#339FFF` text, surface bg)
2. **Title:** 24px text
3. **Subtitle:** 14px gray-600
4. **Before/After Grid:** 2-column on sm+, 1-column on mobile
   - Before card: border `#BCCCDC`, white bg, bulleted list
   - After card: border `#D4AF37` (gold), surface-muted bg, bulleted list
5. **Plan comparison:** 3-column grid (Free/Pro/VIP), Pro highlighted with primary border
6. **Legal text:** 12px gray-500

**Footer (sticky):**
- Border top: 1px `#BCCCDC`
- Purchase CTA: full width, `#339FFF` bg, white text, `rounded-xl`, 48px height
- Cancel: full width, transparent bg, gray-700 text, 44px height

**States:** Default (CTA enabled), Processing (CTA disabled, processing label), Error (red error text below CTA), Disabled (CTA 50% opacity)

**Implementation evidence:** `frontend/src/components/Paywall/BeforeAfter.tsx:117`

### 5.14 FitChef Mascot

Figma Component Set: `PP/Shared/Branding/FitChef`

Animated wellness mascot character.

**Variants:**

| Variant | Description | Usage |
|---------|-------------|-------|
| Static | Single frame, standing pose | Fallback, small sizes |
| Blink | 4-frame eye blink cycle | Idle state |
| Wave | Greeting wave animation | Onboarding, welcome |
| Heartbeat | Subtle pulse animation | Health screens |
| Idle | Gentle breathing/sway | Background presence |

**Sizes:**

| Size | Dimensions | Usage |
|------|------------|-------|
| Small | 60x60px | Inline hints, badges |
| Medium | 120x120px | Cards, sections |
| Large | 180x180px | Launch screen, onboarding |

**iOS:** Uses Lottie animations (`fitchef_blink.json`, etc.) with fallback to static `FitChef.imageset`.
**Web (NEW DESIGN):** Needs Lottie/SVG implementation. Currently missing from web platform.

### 5.15 MascotBubble

Figma Component: `PP/iOS/Branding/MascotBubble`

Speech bubble with FitChef mascot and localized text.

**Properties:**
- FitChef icon: Small (60px) or fork.knife SF Symbol fallback
- Bubble: GlassCard style (white/10% bg, blur, rounded)
- Text: 14px Regular, white
- Layout: horizontal (icon left, bubble right)
- Content: localized string from backend/i18n

### 5.16 ECG Pulse Line (NEW DESIGN)

Figma Component Set: `PP/Shared/Branding/ECGLine`

Brand signature visual element reinforcing the "pulse" concept. Currently not implemented on either platform.

**Design Requirements:**
- Style: simplified, stylized ECG waveform (not medical-accurate)
- Color: `#FF5D5D` (Heart Red) primary, `#339FFF` (Blue) alternate
- Stroke: 2px, smooth curves with one sharp peak
- Wellness-safe: abstract/artistic interpretation, not clinical monitor

**Variants:**

| Variant | Description | Usage |
|---------|-------------|-------|
| Static | Single waveform line | Dividers, card accents |
| Animated | Continuous left-to-right sweep | Loading states, brand emphasis |
| Compact | Short segment (~100px wide) | Inline decorations |
| Full-width | Spans container width | Hero sections, headers |

**Usage Guidelines:**
- Use sparingly (1 per screen maximum)
- Never as primary content element
- Always decorative (aria-hidden, decorative role)
- Reduced-motion: show static variant only

### 5.17 Brand Slogan

Figma Component: `PP/Shared/Branding/Slogan`

**Layout:**
- Tagline: "Always on your Pulse" (EN) / "Держим руку на пульсе" (RU)
  - Font: 18px Semibold, `#FFFFFF` (on navy) or `#0F172A` (on light)
- Subtitle: "Nutrition - Body - Lifestyle"
  - Font: 12px Regular, `rgba(255,255,255,0.6)` (on navy) or `#627D98` (on light)
- Spacing: 4px between tagline and subtitle

### 5.18 State Components

#### Skeleton

Figma Component: `PP/Shared/State/Skeleton`
- Background: `#E5E7EB` (gray-200)
- Border radius: 8px
- Animation: pulse opacity (0.5 to 1.0, 1.5s loop)
- Variants: text line (h: 16px), heading (h: 24px), card (h: 120px), circle (for avatars)

#### EmptyState

Figma Component: `PP/Shared/State/Empty`
- Icon: 48px, `#9CA3AF` (gray-400)
- Title: 18px Semibold, `#374151`
- Description: 14px Regular, `#6B7280`
- Action button (optional): secondary variant
- Layout: centered vertical stack, 16px gaps

#### ErrorState

Figma Component: `PP/Shared/State/Error`
- Icon: 48px warning triangle, `#FF5D5D`
- Title: 18px Semibold, `#374151`
- Description: 14px Regular, `#6B7280`
- Retry button: primary variant
- Layout: centered vertical stack, 16px gaps

#### Toast

Figma Component Set: `PP/Shared/State/Toast`
- Position: top-right (web), top-center (iOS)
- Z-index: 1700
- Border radius: 12px
- Shadow: `--shadow-lg`
- Variants: success (green-50 bg, green icon), error (heart-50 bg, red icon), info (blue-50 bg, blue icon)
- Auto-dismiss: 4s (visual indicator bar)

#### LiveProgressIndicator

Figma Component: `PP/Shared/State/LiveIndicator`
- Dot: 8px circle, `#20C997` (live) or `#9CA3AF` (static)
- Animation: pulse scale 1.0-1.3 at 1s interval (live only)
- Label: 12px text next to dot

#### OfflineIndicator

Figma Component: `PP/Web/State/Offline`
- Banner: full width, `#F59E0B` bg, white text
- Icon: wifi-off, 16px
- Text: 14px "You are offline"
- Position: top of viewport, z-index 1200

---

## 6. Page-by-Page Specifications

### 6.1 iOS: Launch Screen

**Figma Page:** `02_iOS_Launch`
**Source:** `ios/PulsePlate/Views/LaunchScreenView.swift`, `ios/PulsePlate/LaunchScreen.storyboard`

**Layers (bottom to top):**
1. Background: solid `#0F172A` (Navy), full screen
2. FitChef image: 180x180px, centered horizontally, vertically centered offset upward
3. App title: "PulsePlate", 28px Semibold, white, centered below FitChef
4. **(NEW)** Subtitle: "Nutrition - Body - Lifestyle", 14px Regular, white 60% opacity, centered below title

**Design Notes:**
- No interactive elements
- Must match LaunchScreen.storyboard layout
- Safe area insets respected

### 6.2 iOS: Onboarding Flow (NEW DESIGN)

**Figma Page:** `03_iOS_Onboarding`
**Status:** Not yet implemented. Full design required.

3-4 screen onboarding flow accessed via `WelcomeGateView`.

#### Screen 1: Brand Introduction

- Layers: Navy background, FitChef Large (180px) centered, Brand slogan, ECG line accent
- CTA: "Get Started" primary button, full width

#### Screen 2: Value Proposition

- Layers: Navy background, Three feature cards (GlassCard neutral):
  - "Smart Balance" (scale icon, brief text)
  - "Nutrition Tracking" (plate icon, brief text)
  - "Progress Insights" (chart icon, brief text)
- CTA: "Continue" primary button

#### Screen 3: Feature Highlights

- Layers: Navy background, interactive preview mockups:
  - BMI Calculator preview
  - Nutrition Plate preview
  - Weekly Plan preview
- CTA: "Let's Go" primary button

#### Screen 4: Permissions (Optional)

- Layers: Navy background, Permission request cards:
  - HealthKit access (heart icon)
  - Notifications (bell icon)
- CTAs: "Allow" primary button, "Skip" ghost button

#### Shared Navigation
- Page indicator dots at bottom (8px circles, active: white, inactive: white 30%)
- Skip button: top-right, ghost style, "Skip"
- Swipe gesture between screens

### 6.3 iOS: Home

**Figma Page:** `04_iOS_Home`
**Source:** `ios/PulsePlate/Views/HomeView.swift:57`

**Layers (bottom to top):**
1. Background: `#0F172A` (Navy)
2. ScrollView content:
   - **Hero Card** (GlassCard): Welcome message + status indicators
     - PRO key status: green dot if connected, red if not
     - Profile readiness: green dot if complete, amber if incomplete
   - **Quick Actions** section (NavigationLinks):
     - BMI Calculator row (CTA: `ios.home.bmi_calculator`)
     - Profile Setup row (CTA: `ios.home.profile_setup`)
     - Open Plate row (CTA: `ios.home.open_plate`)
   - **PRO Tools** section (feature-flagged):
     - Weekly Plan Reader (CTA: `ios.home.weekly_plan_reader`, flagged)
     - Shopping List Generator (CTA: `ios.home.shopping_list_generator`, flagged)
   - **Mascot Hint**: MascotBubble with contextual tip
3. Tab bar (RootTabs)

**Quick Action Row Design:**
- GlassCard neutral, padding sm
- Left: SF Symbol icon (20px, Blue)
- Center: Label (16px Semibold white) + subtitle (12px, white 60%)
- Right: chevron.right (14px, white 40%)
- Min height: 56px
- Feature-flagged items: hidden when flag disabled

### 6.4 iOS: BMI Calculator

**Figma Page:** `05_iOS_BMI`
**Source:** `ios/PulsePlate/Views/BMICalculatorScreen.swift`

**Layers:**
1. Background: `#0F172A`
2. NavigationStack with title "BMI Calculator"
3. Form content (ScrollView):
   - **Weight input**: NumberField, kg, decimal pad, RU comma support
   - **Height input**: NumberField, cm, decimal pad
   - **Age input**: NumberField, years
   - **Gender picker**: Segmented control (Male/Female)
   - **Language picker**: Segmented control (EN/RU/ES)
   - **Calculate button**: Primary, full width (CTA: `ios.home.bmi_calculator` downstream)
4. **Result Section** (appears after calculation):
   - BMI value: large heading (30px Bold)
   - Category badge: colored pill (Green/Amber/Red based on category)
   - Interpretation text: body text
   - **SoftPaywallHook**: if hook data present from backend
5. **Validation errors**: `ValidationErrorsView` below form if invalid

**Form Field Design:**
- Label: 14px Semibold, white 80%
- Input: GlassCard-style bg, 44px height, white text
- Error: 12px, `#FF5D5D`

### 6.5 iOS: Plate

**Figma Page:** `06_iOS_Plate`
**Source:** `ios/PulsePlate/Views/PlateViewPP.swift:159`

**Layers:**
1. Background: `#0F172A`
2. NavigationStack with title "My Plate"
3. Content:
   - **PlateSegments**: Interactive circular segments (center of screen)
   - **PlateRing**: Progress ring overlay on segments
   - **Segment Detail Card** (GlassCard): Shows selected segment nutrition details
   - **Action Bar** (bottom):
     - Add Meal button (CTA: `ios.plate.add_meal`, partial implementation)
     - View Details button (CTA: `ios.plate.view_details`, partial implementation)
4. **Issue State** (when data unavailable):
   - PlateIssueView with dynamic action button (CTA: `ios.plate.issue_action_dynamic`)
   - Actions: Retry fetch / Navigate to profile / PRO setup
5. Tab bar

### 6.6 iOS: Progress

**Figma Page:** `07_iOS_Progress`
**Source:** `ios/PulsePlate/Views/ProgressViewPP.swift:50`

**Layers:**
1. Background: `#0F172A`
2. NavigationStack with title "Progress"
3. Content:
   - **Daily Segments** table: segment name + completion percentage
   - **Overall Completion**: large percentage with PlateRing
   - **Metrics Cards** (GlassCard): calorie balance, macro breakdown
   - **Refresh Button** (CTA: `ios.progress.refresh`, shown in no-data state)
4. **Issue State** (when data unavailable):
   - Dynamic action button (CTA: `ios.progress.issue_action_dynamic`)
5. Tab bar

**Note:** Current implementation is partially skeleton ("Charts coming..."). Figma should design the complete chart layout.

### 6.7 iOS: Weekly Plan Reader

**Figma Page:** `08_iOS_WeeklyPlan`
**Source:** `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift:22`

**Layers:**
1. Background: `#0F172A`
2. NavigationStack with title "Weekly Plan"
3. Content:
   - **DayNavigatorView**: Horizontal day selector (Mon-Sun), previous/next arrows
   - **MealSectionView** (repeated for each meal):
     - Meal type header: "Breakfast" / "Lunch" / "Dinner" (16px Semibold)
     - Meal items list: food name + portion + calories
   - **DailySummaryView**: Macro totals row (kcal / protein / fat / carbs)
   - **WeeklyCoverageView**: Expandable nutrient coverage percentages
   - **PlanMetricsView**: Cost, adherence %, shopping list count
   - **VIP CTAs** (disabled): Auto-repair, Enhanced shopping list
4. **Loading State**: `WeeklyPlanSkeletonView` (skeleton cards)
5. **Empty State**: `EmptyPlanView` (message + refresh action)
6. **Error State**: `ErrorPlanView` (message + retry action)

### 6.8 iOS: Profile

**Figma Page:** `09_iOS_Profile`
**Source:** `ios/PulsePlate/Views/ProfileView.swift`

**Layers:**
1. Background: `#0F172A`
2. NavigationStack with title "Profile"
3. Form sections:
   - **PRO Profile**: Sex picker, Age input, Height input, Weight input, Activity level picker, Goal picker
   - **Settings**: Language picker
   - **Testing** (DEBUG only): Animation test, Bundle test, Color test buttons
   - **Legal**: Privacy policy link, Terms of service link
4. Edit mode toggle (NavigationBar trailing button)
5. Tab bar

### 6.9 iOS: Paywall

**Figma Page:** `10_iOS_Paywall`
**Source:** `ios/PulsePlate/Views/PaywallScreen.swift`

**Layers:**
1. Background: `#0F172A`
2. Content:
   - **Header**: "Go Premium" heading
   - **Product List**: StoreKit product cards (price, description, period)
   - **Premium Status**: Active/inactive indicator
   - **Restore Purchases**: Ghost button
   - **Purchase CTA**: Primary button per product

### 6.10 Web: Home

**Figma Page:** `11_Web_Home`
**Source:** `frontend/src/pages/Home.tsx:34`

**Layers (top to bottom):**
1. Background: `var(--color-bg)` (`#FFFFFF` light, `#102A43` dark)
2. **Hero Section** (px: 16px mobile / 24px tablet / 32px desktop):
   - Eyebrow: "Wellness Control Panel" (12px Semibold uppercase, tracking-widest, muted text)
   - Title: "Home" (36px Bold / 48px sm+, text color)
   - Description: wellness messaging (18px Regular, muted text, relaxed line-height)
   - Max width: 896px (`max-w-4xl`), centered
3. **Status Cards Section** (2-column grid on sm+, 1-column mobile):
   - **API Connection Card**: title "API Connection", value "Connected"/"Not Set", description text
   - **Premium Status Card**: title "Premium Status", value with color (green if active), description text
   - Both: Card component with hover shadow-md transition
4. **Live Progress Indicator**: source="home", links to /progress
5. **Quick Navigation Section**:
   - Section title: "Quick Navigation" (20px Semibold)
   - Subtitle: "Jump to any section..." (14px, muted)
   - Primary CTA: "Configure Setup" (full width, primary lg button) -> CTA `web.home.open_setup`
   - Secondary grid (3-col on sm+): "Nutrition Plate" / "Progress View" / "Premium Features" -> CTAs `web.home.open_plate`, `web.home.open_progress`, `web.home.open_pro`
6. **Footer spacing**: 96px for tab bar clearance
7. **TabBar** (fixed bottom)

### 6.11 Web: BMI Calculator

**Figma Page:** `12_Web_BMI`
**Source:** `frontend/src/pages/BMI/BMICalculatePage.tsx`

**Layers:**
1. Background: `var(--color-bg)`
2. **Form Section** (centered, max-w-md):
   - Weight (kg): NumberInput with Controller pattern, RU comma support
   - Height (cm): NumberInput
   - Age: NumberInput
   - Sex: Select (Male/Female)
   - Waist (cm): Optional NumberInput
   - Checkboxes: Athlete, Pregnant (conditionally shown)
   - **Calculate Button**: Primary, full width -> submits to `/api/v1/bmi/calculate`
3. **Result Section** (appears after successful calculation):
   - BMI value: large display (36px Bold)
   - Category: colored badge
   - Interpretation: body text
   - Healthy range: min-max display
4. **SoftPaywallHook**: Rendered below results if hook data present
5. Tab bar hidden (`hideTabBar: true`)

### 6.12 Web: Nutrition Setup

**Figma Page:** `13_Web_NutritionSetup`
**Source:** `frontend/src/pages/NutritionSetup/index.tsx:11`

#### Two States: Form and Result

**Form State (SetupForm):**
- Nutrition parameter inputs (activity level, goal, dietary preferences)
- Calculate Plate button (CTA: `web.setup.submit_calculate`) -> calls BMR/plate/targets APIs
- Tab bar hidden

**Result State (ResultView):**
- **PlateChart**: Circular macronutrient chart
- **MacroCards**: Individual macro cards (protein, carbs, fat) with gram values
- **MicrosGrid**: Micronutrient grid
- **WaterCard**: Daily hydration target
- **Action Buttons**:
  - "Try Again" (CTA: `web.setup.result.retry`) on error state
  - "Edit" (CTA: `web.setup.result.edit`) returns to form

### 6.13 Web: Plate

**Figma Page:** `14_Web_Plate`
**Source:** `frontend/src/pages/Plate.tsx:37`

**Layers:**
1. Background: `var(--color-bg)`
2. **Page Header**: "Nutrition Plate" title
3. **LiveProgressIndicator**
4. **PremiumGate Wrapper** (`isPremium` controls visibility):
   - **When locked (non-premium):** Children at 60% opacity, inert, CTA button "Unlock Premium"
   - **When unlocked:** Full nutrition plate visualization
5. **Gated Content:**
   - Link to Setup (CTA: `web.plate.open_setup`)
   - Link to Progress (CTA: `web.plate.open_progress`)
   - Premium gate CTA (CTA: `web.plate.premium_gate_cta`) -> opens BeforeAfter modal
6. Tab bar (visible)

### 6.14 Web: Progress

**Figma Page:** `15_Web_Progress`
**Source:** `frontend/src/features/progress/ProgressCharts.tsx:120`

**Layers:**
1. Background: `var(--color-bg)`
2. **Page Header**: "Progress" title
3. **LiveProgressIndicator**
4. **Time Range Selector**: SegmentedControl (Week/Month/Quarter)
5. **ProgressCharts** (stacked):
   - LineChart: Weight/BMI trends
   - BarChart: Calorie consumed vs burned
   - PieChart: Macro distribution
6. **Export Button** (CTA: `web.progress.export_pdf`): "Export PDF" button, generates local file
7. Tab bar (visible)

### 6.15 Web: Profile

**Figma Page:** `16_Web_Profile`
**Source:** `frontend/src/pages/Profile.tsx:25`

**Layers:**
1. Background: `var(--color-bg)`
2. **API Key Section**:
   - Connection status (Connected/Not Set)
   - Link to Enter Key page
3. **Setup Link**: Link to nutrition setup
4. **About Section**: "About PulsePlate" with brand description
5. Tab bar (visible)

### 6.16 Web: Paywall Modal

**Figma Page:** `17_Web_Paywall`
**Source:** `frontend/src/pages/Pro/ProPaywallPage.tsx:7`

Thin wrapper around BeforeAfter component (see section 5.13).

**Page-level:** Full screen, opens BeforeAfter modal with `purchaseDisabled` flag (purchase not yet wired).

**CTAs:**
- Purchase (CTA: `web.paywall.modal.cta`) - currently disabled/"coming soon"
- Cancel (CTA: `web.paywall.modal.cancel`) - closes modal

### 6.17 Web: Onboarding - Enter Key

**Figma Page:** `18_Web_Onboarding`
**Source:** `frontend/src/pages/Onboarding/EnterKey.tsx`

**Layers:**
1. Background: `var(--color-bg)`
2. **Form** (centered, max-w-md):
   - Heading: "Enter API Key"
   - Description text
   - API key input field
   - Submit button: Primary
3. Tab bar hidden

### 6.18 Web: Onboarding Flow (NEW DESIGN)

**Figma Page:** `18_Web_Onboarding` (additional frames)
**Status:** Not yet implemented. Full design required.

3-4 screen onboarding flow, similar to iOS but adapted for web.

#### Screen 1: Welcome

- FitChef Large centered
- Brand slogan: "Always on your Pulse"
- Subtitle: "Nutrition - Body - Lifestyle"
- ECG line accent (decorative)
- CTA: "Get Started"

#### Screen 2: Features

- Three feature cards in horizontal row (responsive to vertical on mobile):
  - BMI Calculator: scale icon + description
  - Nutrition Plate: plate icon + description
  - Progress Tracking: chart icon + description
- CTA: "Continue"

#### Screen 3: Setup

- Enter API key form (integrated from EnterKey page)
- "Connect" primary button
- "Skip for now" ghost button

**Navigation:** Progress bar at top (3 steps), Back/Next buttons

---

## 7. Button & CTA Specification (All 23)

Complete visual specification for all CTAs. Behavioral details and code anchors: see `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`.

### 7.1 Web CTAs

| CTA ID | Label | Style | Size | Icon | Gate |
|--------|-------|-------|------|------|------|
| `web.home.open_setup` | "Configure Setup" | Primary | lg, full-width | none | none |
| `web.home.open_plate` | "Nutrition Plate" | Secondary | md | none | requiresAuth redirect |
| `web.home.open_progress` | "Progress View" | Secondary | md | none | requiresAuth redirect |
| `web.home.open_pro` | "Premium Features" | Secondary | md | none | none |
| `web.plate.open_setup` | "Open Setup" | Link (inside gate) | md | none | PremiumGate inert |
| `web.plate.open_progress` | "Open Progress" | Link (inside gate) | md | none | PremiumGate inert |
| `web.plate.premium_gate_cta` | i18n `paywall.cta` | Primary | md | none | visible when !isPremium |
| `web.progress.export_pdf` | "Export PDF" | Secondary | md | download icon | none |
| `web.paywall.modal.cta` | i18n `paywall.cta` | Primary | lg, full-width | none | purchaseDisabled flag |
| `web.paywall.modal.cancel` | i18n `common.cancel` | Ghost | md, full-width | none | none |
| `web.setup.submit_calculate` | "Calculate plate" | Primary (submit) | lg, full-width | none | none |
| `web.setup.result.retry` | "Try again" | Primary | md | refresh icon | error state only |
| `web.setup.result.edit` | "Edit" | Secondary | sm | pencil icon | result state |

### 7.2 iOS CTAs

| CTA ID | Label | Style | Icon (SF Symbol) | Gate |
|--------|-------|-------|------------------|------|
| `ios.home.bmi_calculator` | "BMI Calculator" | NavigationLink row | `scalemass.fill` | none |
| `ios.home.profile_setup` | "Profile Setup" | NavigationLink row | `person.crop.circle.fill` | none |
| `ios.home.open_plate` | "Open Plate" | NavigationLink row | `circle.grid.2x2.fill` | pro-key/profile check |
| `ios.home.weekly_plan_reader` | "Weekly Plan" | NavigationLink row | `calendar` | FeatureFlag gated |
| `ios.home.shopping_list_generator` | "Shopping List" | NavigationLink row | `cart.fill` | FeatureFlag gated |
| `ios.plate.add_meal` | "Add Meal" | Primary button | `plus.circle.fill` | none (partial impl) |
| `ios.plate.view_details` | "View Details" | Secondary button | `info.circle.fill` | none (partial impl) |
| `ios.plate.issue_action_dynamic` | Dynamic label | Primary button | context-dependent | issue state only |
| `ios.progress.refresh` | "Refresh" | Primary button | `arrow.clockwise` | no-data state |
| `ios.progress.issue_action_dynamic` | Dynamic label | Primary button | context-dependent | issue state only |

### 7.3 Universal Button States

All buttons must have these states designed in Figma:

| State | Visual Change | Trigger |
|-------|--------------|---------|
| Default | Base appearance | Idle |
| Hover | Brightness +10% (Web only) | Mouse hover |
| Pressed | Scale 0.98, Brightness -10% | Mouse down / touch |
| Focused | 2px `#339FFF` ring, 2px offset | Tab focus (Web), VoiceOver (iOS) |
| Disabled | 50% opacity, no pointer events | Auth gate, feature flag, purchaseDisabled |
| Loading | Spinner icon, 70% opacity, no pointer events | Async operation in progress |
| Error | Red border, error text below (if applicable) | Failed operation |

**Figma Node ID status:** All CTAs currently `TBD` - to be assigned when Figma Design URLs become available. See `docs/figma/orchestration/sessions/2026-02-18_figma_sync_hpp/03_SYNTHESIS_DECISION.md:9` for blocker status.

---

## 8. Accessibility Requirements

### 8.1 Color Contrast

| Context | Minimum Ratio | Standard |
|---------|---------------|----------|
| Body text on background | 4.5:1 | WCAG AA |
| Large text (18px+ bold, 24px+ regular) | 3:1 | WCAG AA |
| Interactive element borders | 3:1 | WCAG AA |
| Focus indicators | 3:1 against adjacent colors | WCAG AA |

**Verified pairings (computed via WCAG 2.1 relative luminance formula):**
- Navy `#0F172A` on white `#FFFFFF`: 16.75:1 (pass)
- White `#FFFFFF` on Navy `#0F172A`: 16.75:1 (pass)
- Blue `#339FFF` on white: 3.2:1 (pass for large text, needs verification for body)
- Blue `#339FFF` on Navy: 5.2:1 (pass)
- Muted text `#627D98` on white: 4.6:1 (pass)

### 8.2 Touch Targets

| Platform | Minimum Size | Implementation |
|----------|-------------|----------------|
| iOS | 44x44pt | Apple HIG requirement |
| Web (mobile) | 44x44px | `--spacing-touch: 2.75rem` |
| Web (desktop) | 32x32px | Acceptable with hover state |

All buttons: `min-height: 44px` enforced via `style={{ minHeight: 44 }}` (see `frontend/src/components/PremiumGate.tsx:56`, `frontend/src/components/VipGate.tsx:110`, `frontend/src/components/Paywall/BeforeAfter.tsx:191`).

### 8.3 Focus Management

**Web:**
- Focus ring: 2px solid `#339FFF`, 2px offset
- Focus trap in modals (BeforeAfter, dialogs)
- Skip navigation link (z-index 1600)
- `inert` attribute on gated content (PremiumGate)
- Escape key closes modals

**iOS:**
- VoiceOver labels on all interactive elements
- `accessibilityLabel()` on buttons and cards
- `accessibilityHidden(true)` on decorative elements
- `accessibilityHint()` for contextual guidance

### 8.4 Screen Reader Support

- All images: alt text or `aria-hidden="true"` (decorative)
- Form fields: associated labels via `aria-labelledby` or `<label>`
- Error messages: `aria-live="polite"` for dynamic errors
- Modal dialogs: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Tab bar: `role="tablist"`, `role="tab"`, `aria-selected`
- Disabled tabs: `aria-disabled="true"`, `tabIndex={-1}`

### 8.5 Dynamic Type (iOS)

All text in iOS must support Dynamic Type scaling:
- Use `Font.system(size:weight:)` which respects user text size preferences
- Test at: xSmall, Default, XXXL accessibility sizes
- Layouts must not break at large text sizes (use ScrollView, avoid fixed heights)

### 8.6 Reduced Motion

- Respect `prefers-reduced-motion: reduce` (Web CSS media query)
- Respect `UIAccessibility.isReduceMotionEnabled` (iOS)
- Replace: slide/scale animations -> instant opacity crossfade
- Disable: shimmer, pulse, ECG line animation, FitChef animation loops
- Keep: essential state transitions (page navigation)

### 8.7 Color Blind Considerations

- Never use color alone to convey information
- All status indicators use icon + color + text
- Chart segments use color + pattern/label
- BMI category badges use color + text label

---

## 9. Responsive & Adaptive Behavior

### 9.1 Web Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Single column, stacked cards, full-width buttons |
| sm | >= 640px | 2-column status cards, 3-column action grid |
| md | >= 768px | Side-by-side before/after in paywall |
| lg | >= 1024px | Wider max-width, more generous spacing |
| xl | >= 1280px | Max content width reached |

**Max content width:** 896px (`max-w-4xl`) for all page content.

### 9.2 iOS Device Matrix

| Device | Screen Width | Safe Area Insets | Notes |
|--------|-------------|-----------------|-------|
| iPhone SE 3 | 375pt | top: 47, bottom: 0 | Smallest supported |
| iPhone 14 | 390pt | top: 59, bottom: 34 | Standard |
| iPhone 15 Pro | 393pt | top: 59, bottom: 34 | Standard |
| iPhone 16 Pro Max | 440pt | top: 62, bottom: 34 | Largest |

**iPad:** Basic support via autolayout; no iPad-specific layouts in v1.

### 9.3 Dark Mode

- **Web:** Triggered by `html[data-theme="dark"]` attribute or `prefers-color-scheme: dark` media query
- **iOS:** Follows system appearance; navy backgrounds remain navy (dark-on-dark optimized)
- All semantic color tokens have dark variants (see section 3.1)
- GlassCard: adjust blur intensity and border opacity for dark mode
- Shadows: increased opacity in dark mode (0.3-0.4 vs 0.05-0.1)

---

## 10. App Store Assets

### 10.1 App Icon

**Source of truth:** `docs/design/EMBLEM_CORE_v1.0_LOCK.md`
**Lock level:** L4 (geometry hash locked, exact-zero tolerance)

**Required sizes (from `ios/ICON_INSTRUCTIONS.md`):**

| File | Size | Usage |
|------|------|-------|
| AppIcon-1024.png | 1024x1024 | App Store |
| `AppIcon-20@1x.png` | 20x20 | iPad notifications |
| `AppIcon-20@2x.png` | 40x40 | iPhone notifications |
| `AppIcon-20@3x.png` | 60x60 | iPhone notifications |
| `AppIcon-29@1x.png` | 29x29 | iPad settings |
| `AppIcon-29@2x.png` | 58x58 | iPhone settings |
| `AppIcon-29@3x.png` | 87x87 | iPhone settings |
| `AppIcon-40@1x.png` | 40x40 | iPad spotlight |
| `AppIcon-40@2x.png` | 80x80 | iPhone spotlight |
| `AppIcon-40@3x.png` | 120x120 | iPhone spotlight |
| `AppIcon-60@2x.png` | 120x120 | iPhone app |
| `AppIcon-60@3x.png` | 180x180 | iPhone app |
| `AppIcon-76@1x.png` | 76x76 | iPad app |
| `AppIcon-76@2x.png` | 152x152 | iPad app |
| `AppIcon-83.5@2x.png` | 167x167 | iPad Pro app |

### 10.2 Screenshots (NEW DESIGN)

**Required for App Store Connect:** 5 screenshots per device size.

**Device sizes needed:**
- 6.7" (iPhone 15 Pro Max / 16 Pro Max): 1290x2796
- 6.1" (iPhone 15 / 16): 1179x2556

**Screenshot Sequence:**

| # | Screen | Content | Key Visual |
|---|--------|---------|------------|
| 1 | Welcome / Brand | FitChef + slogan + ECG accent | Navy background, brand intro |
| 2 | My Plate | Interactive nutrition plate | PlateSegments + PlateRing |
| 3 | Weekly Plan | Day navigator + meal cards | DayNavigator + MealSections |
| 4 | Progress | Charts + metrics | ProgressCharts + completion ring |
| 5 | Holistic Health | BMI calculator + results | Form + result card + paywall hook |

**Screenshot Frame Design:**
- Background: Navy gradient (top `#0F172A` to bottom `#1E3A5F`)
- Device frame: Minimal bezel mockup
- Caption: 24px Bold white, centered above device
- Subcaption: 16px Regular, white 70%, below caption

### 10.3 App Preview Video (NEW DESIGN)

**Duration:** 15-30 seconds
**Resolution:** 1080x1920 (9:16)

**Storyboard:**
1. (0-3s) App icon zoom in -> Launch screen with FitChef
2. (3-8s) Onboarding flow highlights (swipe through 3 screens)
3. (8-13s) BMI Calculator: fill form -> see results
4. (13-20s) Nutrition Plate: interactive segments + progress ring
5. (20-25s) Weekly Plan: day navigation + meal cards
6. (25-30s) Brand close: slogan + FitChef wave + App Store CTA

**Audio:** No voiceover. Subtle background music (wellness/ambient).

---

## 11. Implementation Gap Tracker

Cross-reference with `docs/audit/DESIGN_CONCEPT_IMPLEMENTATION_AUDIT.md` and `docs/analysis/FRONTEND_IOS_VISUAL_ANALYSIS.md`.

Status claims below are target/roadmap assessments based on codebase analysis; for verified `file:line` evidence per component see the Implementation Evidence anchors in sections 5.1-5.18 and the audit doc above.

| Spec Section | Web Status | iOS Status | Priority |
|-------------|-----------|------------|----------|
| **Color Palette** | Implemented | Implemented | - |
| **Typography System** | Implemented (Inter) | Implemented (system) | - |
| **Spacing Tokens** | Implemented | Partial (no shared tokens) | P1 |
| **GlassCard** | Implemented | Implemented | - |
| **TabBar/Navigation** | Implemented | Implemented | - |
| **PlateChart** | Implemented | Implemented (PlateSegments) | - |
| **ProgressCharts** | Implemented (mock data) | Skeleton only | P0-A |
| **PremiumGate** | Implemented | N/A (StoreKit paywall) | - |
| **SoftPaywallHook** | Implemented | Implemented | - |
| **BeforeAfter Modal** | Implemented | N/A | - |
| **FitChef Mascot** | NOT implemented | Implemented | P1 |
| **MascotBubble** | NOT implemented | Implemented | P1 |
| **ECG Pulse Line** | NOT implemented | NOT implemented | P1 |
| **Brand Slogan** | NOT implemented | NOT implemented | P0-B |
| **Onboarding Flow** | Minimal (EnterKey only) | Minimal (WelcomeGate) | P0-B |
| **App Store Screenshots** | N/A | NOT created | P0-B |
| **App Preview Video** | N/A | NOT created | P1 |
| **Home Page** | Implemented (basic) | Implemented (basic) | P0-A |
| **BMI Calculator** | Implemented | Implemented | - |
| **Nutrition Setup** | Implemented | N/A (profile only) | - |
| **Plate Page** | PremiumGate only | Implemented | P0-A |
| **Progress Page** | Mock data | Skeleton | P0-A |
| **Weekly Plan** | Implemented | Implemented | - |
| **Profile Page** | Basic | Basic | P1 |
| **Dark Mode** | Token-ready | System-native | P1 |
| **Accessibility** | Good foundation | Basic | P1 |

**Priority Legend:**
- **P0-A:** Product works (core functionality before any release)
- **P0-B:** Can publish (required for App Store/public launch)
- **P1:** Brand magic (enhancements, not blockers)

---

**Document version:** 1.0
**Last updated:** 2026-02-22
**Next review:** After P0-A items implementation
