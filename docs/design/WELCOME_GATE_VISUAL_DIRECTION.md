# iOS Welcome Gate — Visual Direction (SwiftUI-ready)

**Date:** 6 February 2026
**Scope:** Welcome Gate (PR-653) visual system and asset handoff checklist
**Goal:** trust-first, HIG-clean, minimal, accessible; motion is subtle and optional

---

## 1) Visual direction

### Color system (PulsePlate palette)

- **Background**: Navy `#0F172A`
- **Primary text**: White `#FFFFFF`
- **Secondary text**: White 80% (`#FFFFFFCC`)
- **Tertiary text**: White 60% (`#FFFFFF99`)
- **Accent blue (CTA / active)**: `#339FFF`
- **Accent green (success / pulse highlights, optional)**: `#20C997`
- **Surface elevation**: navy + white overlay ~5% (cards/panels)

### Typography (system-native)

- Use **SF Pro Display** for headings and **SF Pro Text** for body.
- Keep hierarchy simple:
  - Hero: `.largeTitle`
  - Titles: `.title2` / `.title3`
  - Body: `.body`
  - Footer: `.footnote`
- **Dynamic Type** must work out of the box (no hard-coded heights).

### Spacing (touch-friendly)

- Base unit: 4pt
- Horizontal padding: 24–32pt (device-dependent)
- CTA area: at least 32pt above bottom safe area
- Tap targets: **≥44×44pt** everywhere

### Icon / illustration approach

- Prefer **SF Symbols** (line icons, rounded) for consistency and low asset overhead.
- FitChef is optional:
  - If used: only on Screen 1 as a small, friendly “trust anchor”.
  - If not used: use abstract pulse-wave geometry (subtle, non-medical).

---

## 2) Screen concepts (2–3, consistent system)

### Concept A — “Hero + calm promise” (Screen 1)

- Navy background, small FitChef (optional) in the top third.
- Large headline + 1–2 line subtitle.
- One primary CTA (blue) + a gentle “Skip” link (with 44pt hit area).

**Motion:** fade-in + tiny scale-up for hero; subtle pulse-wave ring every ~3s.
Respect Reduce Motion (disable pulse; keep fade-only).

### Concept B — “Feature cards” (Screens 2–3)

- Left-aligned icon + title + 2–3 lines body.
- Plenty of breathing room.
- Consistent “Continue” CTA.

**Motion:** slide-in from right on advance; swipe supported (if already implemented).

### Concept C — “Ready” (Screen 4)

- Icon + final title, short reassurance line.
- Primary CTA (“Get started”) emphasized; optional dot indicator.

**Motion:** gentle CTA emphasis on appear (small scale), then haptic success on completion.

---

## 3) Accessibility notes

- **Contrast:** white-on-navy is AAA; ensure CTA blue has sufficient contrast.
- **Dynamic Type:** layout must reflow; avoid text clipping.
- **VoiceOver:** focus order = icon → title → body → CTA → footer; headings marked as headers.
- **Reduce Motion:** pulse-wave disabled when Reduce Motion is on.

---

## 4) Asset checklist (designer handoff)

### Required (if not using SF Symbols)

- FitChef hero (optional): Lottie JSON or PNG @3x, base ~120×120pt.
- 3–4 icons (24pt line style) as vectors or PNG @3x.
- Page indicator dots (only if not using system default).

### Motion spec (for dev)

- Pulse wave:
  - radius 0 → 200pt
  - duration ~2s
  - repeat interval ~3s
  - stroke ~2pt
  - opacity 0.3 → 0
  - optional gradient green → blue
