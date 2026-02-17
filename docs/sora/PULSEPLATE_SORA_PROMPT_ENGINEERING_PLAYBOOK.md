# PulsePlate Sora Prompt Engineering Playbook

## Scope

This playbook covers three requested steps in one execution flow:

1. Planning and engineering framework
2. Audit and parallel brainstorm outputs (with web-backed constraints)
3. Ready-to-use prompt packs and anti-drift dictionary

The goal is consistent, brand-distinct visual generation for PulsePlate assets
(icons, onboarding art, mascot scenes, UI objects, and background textures)
without style drift.

Related visual governance guide for iOS/Web premium execution:

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`

## Step 1 - Planning Framework

### 1.1 Style DNA (non-negotiable invariants)

- Brand mood: minimalism + cozy + intelligent + luxury-clean.
  (`docs/sora/SKILL_PULSEPLATE_SORA_PROMPT_ENGINEERING.md:24`)
- Palette lock:
  - Navy `#0F172A`
  - Blue `#339FFF`
  - Accent Green `#20C997`
  - Heart Red `#FF5D5D` (accent only)
- Visual style: flat forms, soft shadows, subtle gradients, clean geometry.
  (`docs/sora/SKILL_PULSEPLATE_SORA_PROMPT_ENGINEERING.md:30`)
- Mascot policy: FitChef is lifestyle-friendly, never clinical/medical.
  (`docs/sora/SKILL_PULSEPLATE_SORA_PROMPT_ENGINEERING.md:31`)
- Composition policy: one focal center, high readability in small sizes, low clutter.

### 1.2 Parallel Operating Model

- **Lane A (Creative):** creative-designer + frontend-design mindset
  - Output: master style block, scene prompts, variation prompts
- **Lane B (Architecture):** ai-app-architect + architecture-specialist
  - Output: folder layout, naming, versioning, review gates
- **Lane C (Risk):** bug-hunter + security perspective
  - Output: failure modes and anti-drift checks
- **Lane D (External reality):** ai-trend-reporter + web checks
  - Output: external constraints (Sora workflow, App Store risk, accessibility hints)

### 1.3 Delivery Pipeline

Brief -> Prompt spec -> Generate (3-5 candidates) -> QA rubric ->
Iterate -> Approve -> Export -> PR

### 1.4 Project Structure (asset ops)

Recommended structure:

```text
docs/sora/
  PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md
  prompts/
    onboarding/
    paywall/
    home_cards/
    icons/
    mascot/
  qa/
    SORA_STYLE_QA_CHECKLIST.md
assets/generated/sora/
  <asset_family>/
    v1/
      prompt.md
      metadata.json
      outputs/
```

Naming convention:

- Prompt file: `<family>__<screen>__vX.Y.md`
- Generated asset: `<family>__<concept>__vX.Y__varNN.png`
- Metadata file: `<family>__<screen>__vX.Y.metadata.json`

Versioning:

- `v1.0` initial approved prompt
- `v1.1` micro change (wording/composition lock)
- `v2.0` style-level redesign

## Step 2 - Audit and Brainstorm

### 2.1 Web-Backed Constraints (where needed)

- OpenAI Sora prompting resources emphasize treating prompts as production
  specs and using stable prefixes for consistency.
  - `https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide/`
  - `https://developers.openai.com/api/docs/models/sora-2`
- Apple App Review and metadata constraints require originality and
  ownership/permission for visual assets and app identity.
  - `https://developer.apple.com/app-store/review/guidelines`
  - `https://help.apple.com/asc/appsspec/en.lproj/static.html`
- Accessibility baseline for contrast and legibility should be verified for
  icon/button assets.
  - `https://developer.apple.com/help/app-store-connect/manage-app-accessibility/sufficient-contrast-accessibility-evaluation-criteria/`
  - `https://developer.apple.com/design/human-interface-guidelines`

### 2.2 Top Failure Risks and Mitigations

1. Brand drift across generations
   - Prevent: style-lock prefix and fixed palette tokens
   - Detect: QA rule "palette outside allowed set = fail"
2. Generic AI look ("slop")
   - Prevent: explicit negative constraints in every prompt
   - Detect: manual review with anti-slop checklist
3. Inconsistent FitChef appearance
   - Prevent: mascot identity block (shape/mood/pose rules)
   - Detect: side-by-side mascot continuity review
4. App Store rejection due to copied-like identity
   - Prevent: originality-first prompt constraints, no derivative logos/icons
   - Detect: legal/design review before release
5. Accessibility regression (icon unreadable at small size)
   - Prevent: small-size readability requirement in prompt
   - Detect: 24px/32px/60px visual test + contrast check
   (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:105`)
6. Over-complex visuals for UI usage
   - Prevent: "single focal center, low clutter" policy
   - Detect: UI mock insertion test
7. Medical/clinical misinterpretation in wellness context
   - Prevent: forbid clinical symbols and diagnosis-like framing
   - Detect: wellness-safe content review
8. Prompt entropy in team edits
   - Prevent: versioning and locked prompt templates
   - Detect: PR diff check against style invariants
9. Mismatch between iOS and social exports
   - Prevent: separate target variants with fixed ratio specs
   - Detect: export matrix validation
10. Unclear traceability to decisions
    - Prevent: metadata.json per asset version
    - Detect: PR must include prompt+metadata+QA evidence

## Step 3 - Ready Prompt Kits

### 3.1 Master Prompt Engineer Template

```text
You are PulsePlate Visual Prompt Engineer for Sora.
Create a brand-consistent asset for: {ASSET_TYPE}.

Brand lock (must keep):
- Mood: minimal + cozy + intelligent + luxury-clean
- Palette only: #0F172A, #339FFF, #20C997, #FF5D5D (accent)
- Style: flat forms, soft shadows, subtle gradients, clear geometry
- FitChef policy: lifestyle-friendly, never clinical/medical
- Composition: one focal center, high readability at small size, low clutter

Forbidden:
- Generic AI look, glossy 3D blobs, neon cyberpunk, purple/gold palette
- Text-heavy graphics, tiny noisy details, medical symbols
- Derivative app-icon appearance

Technical target:
- Ratio: {RATIO}
- Output context: {IOS|WEB|SOCIAL}
- Variant count: 3 controlled variations

Return:
1) Main prompt
2) Negative prompt
3) 3 variation prompts
4) Self-QA in 5 bullets
```

### 3.2 Nano Banana Prompt (fast mode)

Use this one-liner as a stable prefix:

```text
PulsePlate style lock: luxury-clean flat wellness, palette #0F172A #339FFF
#20C997 with #FF5D5D accents, soft shadows, subtle gradients, strong focal
center, high small-size readability, FitChef lifestyle (not medical), no
generic AI/glossy/neon/purple/gold.
```

### 3.3 v1 Screen Prompt Pack

#### Onboarding

Prompt:

```text
{NANO_PREFIX}
Create onboarding illustration for first session habit start. Calm interior
morning mood, one dominant focal object, low clutter, clear silhouette forms,
no text overlays, export for iOS onboarding card ratio 4:5.
```

Variations:

- V1: human + table scene
- V2: abstract wellness path scene
- V3: FitChef cameo at edge (small presence)

#### Paywall

Prompt:

```text
{NANO_PREFIX}
Create premium paywall hero visual that communicates confidence and calm
progress, not pressure. Premium depth via subtle gradient and soft shadow
layering, one central trust anchor, no medical claims, no text.
```

Variations:

- V1: abstract premium gradient field
- V2: minimalist object composition
- V3: FitChef confident gesture (small)

#### Home Cards

Prompt:

```text
{NANO_PREFIX}
Create modular home-card background and object accents for daily wellness
dashboard. Maintain low visual noise, strong contrast for overlay text, clean
geometry, icon-friendly composition.
```

Variations:

- V1: card texture only
- V2: texture + object accent
- V3: texture + soft mascot hint

### 3.4 v1 Asset Prompt Pack

#### App Icon Concept

```text
{NANO_PREFIX}
Create iOS app icon concept with one dominant symbol, no text, square
composition optimized for 60/120/1024 sizes, high recognition in crowded
App Store rows.
```

#### Button Icon Set

```text
{NANO_PREFIX}
Create minimal UI icon set (add, save, close, settings, profile) with
consistent stroke weight and strong legibility at 24-32 px.
```

#### Nutrition Object Set

```text
{NANO_PREFIX}
Create nutrition object set (plate, greens, fruit, simple utensils) for UI
cards, clean silhouettes, low-detail flat style, no realism.
```

#### FitChef Character Frame

```text
{NANO_PREFIX}
Create FitChef mascot frame with friendly lifestyle gesture, clear silhouette
and expression consistency with prior versions, no chef-hat cliché,
no clinical context.
```

## Anti-Drift Dictionary

### A) Forbidden Visual Patterns

- "hyper realistic skin pores"
- "cinematic neon cyberpunk"
- "futuristic hologram hospital"
- "gold luxury emblem"
- "purple gradient glossy blob"
- "3D chrome icon pack"
- "medical monitor ECG scene"
- "diagnostic clinical interface"

### B) Forbidden Semantic Directions

- Diagnosis-like wording
- Cure/treatment implication
- Before/after miracle framing
- Competitive imitation references ("like app X")

### C) Required Prompt Tokens (must include)

- `flat`
- `soft shadows`
- `subtle gradients`
- `palette locked`
- `high small-size readability`
- `wellness not medical`

### D) QA Checks (pass/fail)

1. Palette locked to allowed colors
2. Flat + soft shadow + subtle gradient style present
3. Small-size readability confirmed
4. Wellness-safe semantics confirmed
5. No derivative/copycat visual cues
6. FitChef consistency (if mascot present)

## Negative UX Guard Clauses (Doc-Ready)

Use these blocks as mandatory additions for production prompt templates.

### Must-have prompt guard clauses

- Palette lock: `#0F172A #339FFF #20C997` with `#FF5D5D` as accent only
- Style lock: `flat forms, soft shadows, subtle gradients`
- Tone lock: `calm, supportive, luxury-clean, wellness lifestyle`
- Safety lock: `never medical, never diagnostic, no cure framing`
- Readability lock: `clear silhouette, readable at small size`

### Must-have negative prompt clauses

- `no generic ai slop`
- `no glossy 3d blobs`
- `no neon cyberpunk or purple/gold drift`
- `no hospital or clinical equipment`
- `no body-shaming or miracle transformation messaging`
- `no copycat competitor style`

## Preflight QA (Before Generation)

- [ ] Prompt includes all style/tone/safety locks
- [ ] Negative prompt block attached
- [ ] Target context declared (`IOS`, `WEB`, `SOCIAL`)
- [ ] Ratio and export purpose declared
- [ ] FitChef continuity constraints added when mascot is used
- [ ] Accessibility intent included (legibility, no flash-heavy motion)

## Post-Generation Acceptance (Release Gate)

- [ ] Palette and style locks preserved
- [ ] No clinical implication or misleading wellness semantics
- [ ] Small-size readability passed (icons/buttons/cards where relevant)
- [ ] Motion comfort passed (no jitter, no flashing, no aggressive transitions)
- [ ] Distinctive PulsePlate identity preserved (not generic/derivative)
- [ ] Product and social messaging are consistent and non-manipulative

## Fallback and Failure Policy

If generated video/visuals fail QA or are unavailable:

1. Fallback to approved static visual from the same prompt family
2. Keep the same palette and style constraints
3. Do not block screen rendering with empty visual placeholders
4. Mark failed variant in metadata and exclude from release

## Social Creative Release Checklist (Derived)

- [ ] First frame communicates value quickly and clearly
- [ ] No fear, shame, or manipulative urgency tone
- [ ] Wellness-only language and visuals (no medical framing)
- [ ] CTA present but calm and trustworthy
- [ ] Mobile-feed legibility validated

## PR Checklist for Sora Asset Changes

- [ ] Prompt file added/updated with version tag
- [ ] Metadata file includes target, ratio, and generation notes
- [ ] QA rubric attached (pass/fail evidence)
- [ ] At least 3 variations reviewed and rationale documented
- [ ] Accessibility quick checks completed (contrast/readability)
- [ ] No medical claim or clinical misrepresentation
- [ ] No out-of-palette drift
- [ ] App icon assets tested at small sizes

## Decision Notes

- Use only trusted visual anchors from the current draft (logo and FitChef image).
- Treat all other rough draft elements as non-authoritative.
- Keep this playbook as the single source for Sora style and anti-drift policy.

## Evidence anchors

- `docs/sora/SKILL_PULSEPLATE_SORA_PROMPT_ENGINEERING.md:24`
- `docs/sora/SKILL_PULSEPLATE_SORA_PROMPT_ENGINEERING.md:30`
- `docs/sora/SKILL_PULSEPLATE_SORA_PROMPT_ENGINEERING.md:31`
- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:105`
