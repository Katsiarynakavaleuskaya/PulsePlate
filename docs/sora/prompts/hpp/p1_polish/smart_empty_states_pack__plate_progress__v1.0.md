<!-- markdownlint-disable MD013 -->
# Smart Empty States Prompt Pack

Version: v1.0
Priority: P1
Surface: Web Plate + Progress (`/plate`, `/progress`)
Target components:
- `frontend/src/pages/Plate.tsx`
- `frontend/src/pages/Progress.tsx`
- `frontend/src/components/ui/EmptyState.tsx`

## 1) Purpose

Unify empty/locked/retry visuals into one consistent family to improve perceived quality.

## 2) Master Prompt (Sora)

```text
Create a 3-variant empty-state illustration family for wellness app.
Variant A: no data baseline, Variant B: premium locked preview,
Variant C: temporary retry state. Keep one visual family and low clutter.
Token-safe palette, calm supportive emotion, no fear cues.
```

## 3) Layout Prompt (Figma)

```text
Design a unified empty-state family for Plate and Progress contexts.
Need variants: no data yet, locked by premium, temporary error/retry.
Keep same visual DNA and spacing system across all states.
Include primary and secondary action placement guidance.
```

## 4) Negative Prompt

```text
no sad-face clichés, no failure drama, no aggressive warning visuals,
no medical emergency motifs
```

## 5) Controlled Variations

### Variant A - No Data Yet

```text
Calm baseline with one supportive visual anchor and next-step CTA space.
```

### Variant B - Premium Locked

```text
Respectful locked-preview state with value-forward tone, no pressure cues.
```

### Variant C - Retry State

```text
Recovery-focused retry visual with clear primary/secondary action hierarchy.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- State intent understandable within first glance
- Visual continuity preserved across all three variants
- No fear/shame manipulation tone
