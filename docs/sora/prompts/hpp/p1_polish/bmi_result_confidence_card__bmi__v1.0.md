<!-- markdownlint-disable MD013 -->
# BMI Result Confidence Card Prompt Pack

Version: v1.0
Priority: P1
Surface: Web BMI (`/bmi`)
Target component:
- `frontend/src/pages/BMI/BMICalculatePage.tsx`

## 1) Purpose

Improve trust and readability of BMI results while preserving wellness-safe tone.

## 2) Master Prompt (Sora)

```text
Create lightweight visual motifs for BMI result card background accents.
Style: precise, calm analytics, not clinical.
Use restrained token palette and geometric cues for confidence.
No text in image. Provide 3 low-intensity variants.
```

## 3) Layout Prompt (Figma)

```text
Design a BMI result confidence card with clear metric hierarchy.
Sections: primary value, range context, lifestyle-safe recommendation block,
optional next action to setup/progression pages.
Must not imply diagnosis. Keep language and visuals wellness-oriented.
```

## 4) Negative Prompt

```text
no medical chart aesthetics, no hospital iconography,
no red-alert visual panic, no shame-based body framing
```

## 5) Controlled Variations

### Variant A - Metric Focus

```text
Primary metric dominance with restrained contextual range band.
```

### Variant B - Guidance Focus

```text
Balanced value plus short recommendation support block.
```

### Variant C - Confidence Focus

```text
Use geometric confidence frame around result value with low-intensity accents.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Pass `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- No medical diagnosis implication in visuals
- Long localized strings remain readable
- CTA to next action remains visually clear
