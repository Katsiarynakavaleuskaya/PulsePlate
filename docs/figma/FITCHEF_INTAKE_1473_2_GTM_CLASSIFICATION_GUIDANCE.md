# FitChef intake board `1473:2` — GTM classification guidance

**Status:** `Reference only` (docs lane; no asset or runtime promotion)
**Scope:** `FitChef Mascot Asset Inventory — Intake 2026-04-28`
**Figma:** file `2JDwOByQIbcPgp93FDzHii`, node `1473:2`
**Source counts (sticker QA on board):** `6` `APPROVED-SEED` · `20` `CANDIDATE` · `3` `REFERENCE-ONLY` · `1` `NEEDS-REWORK` (see `docs/figma/FITCHEF_BRAND_REFERENCE_HANDOFF.md:50`)

This document assigns **marketing_use** and **runtime_use** posture per repo key `fitchef-candidate-001`…`030`. Row order **`001–006`** map to the six **APPROVED-SEED** assets named in `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`. Rows **`007–026`** correspond to the **20** `CANDIDATE` frames in **gallery sort order left-to-right, top-to-bottom** on `1473:2` (reconcile visually in Figma before locking ASO picks). Rows **`027–029`** map to **`REFERENCE-ONLY`**. Row **`030`** maps to **`NEEDS-REWORK`**.

---

## 1) Bucket policy mapping (`marketing_use` / `runtime_use`)

Use these enums in spreadsheets, backlog notes, or future promotion PRs. They are **classification labels**, not App Store submissions.

### `marketing_use`

| Value | Meaning | ASO screenshot | Social / paid | Allowed embedded copy |
| --- | --- | --- | --- | --- |
| `approved_seed` | Approved seed PNG from repo canon (`FITCHEF_MASCOT_ASSET_CANON.md`). Safe brand anchor. | **Yes** (mascot corner / personality; not substitute for UI truth) | **Yes** | RU-first or bilingual per market; reject dominant English-only where RU/US campaign rules require locality |
| `social_ready` | OK for IG/TikTok/Stories when composition avoids medical/diagnostic/guarantees and fake product UI reads as illustrative. | Tertiary / supporting only unless paired with compliant headline | **Preferred** | Short wellness lifestyle only |
| `aso_supporting_hold` | Not blocked structurally but **blocked for primary ASO** until localization and text QA pass | Do not ship as Shot 1–3 hero until cleared | Allowed with disclaimers (“illustration”) where needed | Audit for English dominance |
| `reference_archive` | Exploration, mood, or comps; **do not** imply shipped product behavior | **No** (reference / deck / internal only) | Optional with heavy “concept” labeling | Prefer no claim-like text |
| `blocked_gtm` | Fails policy: medical/diagnostic, guarantees, fake UI as truth, or dominant non-localized English per target market rules | **No** | **No** (or creative-only with full rework) | Reject copy as written |

### `runtime_use`

| Value | Meaning |
| --- | --- |
| `canon_aligned` | Asset already has a named file in `docs/design/FITCHEF_MASCOT_ASSET_CANON.md` / `frontend/src/assets/brand/`; runtime mirror may exist in iOS catalog. No **new** promotion from this intake doc. |
| `no_runtime_promotion` | Default for all **CANDIDATE / REFERENCE-ONLY / NEEDS-REWORK** on `1473:2` until a separate PR promotes a governed export per `AGENTS.md` / canon rules. |
| `blocked_runtime` | Must not ship in app UI: typically fake metrics UI, diagnostic framing, or unreleased screens presented as live. |

### Automatic flags (overlay any row)

Apply these **in addition** to the row decision:

- **Dominant embedded English** (where RU/CIS is primary): downgrade `marketing_use` by one tier toward `aso_supporting_hold` or `blocked_gtm` for CIS campaigns unless artist supplies localized overlay.
- **Medical/diagnostic** (“diagnose”, “treatment”, pathology claims, clinician replacement): **`blocked_gtm`** / **`blocked_runtime`**.
- **Guarantee** (“guaranteed lose”, “cure”, “100% results”): **`blocked_gtm`**.
- **Fake UI promises** (mock nutrition score / meal plan screenshot presented as guaranteed live feature): **`blocked_runtime`** for in-app use; **`reference_archive`** or **`blocked_gtm`** for public marketing unless reworked per `FITCHEF_APP_STORE_VISUAL_CONTRACT.md` (real UI mass, illustrative labeling).

Cross-ref: wellness copy posture `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md`; FitChef lane `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`.

---

## 2) Thirty row decisions (`fitchef-candidate-001` … `030`)

| Key | Mapped asset / intake slot | `marketing_use` | `runtime_use` | Rationale snippet |
| --- | --- | --- | --- | --- |
| fitchef-candidate-001 | Seed: neutral (`fitchef-portrait-neutral-v1`) | approved_seed | canon_aligned | Baseline mascot; wellness lifestyle; suitable for ASO corner placement and social; no diagnostics in asset class. |
| fitchef-candidate-002 | Seed: wink (`fitchef-portrait-wink-v1`) | approved_seed | canon_aligned | Positive feedback emotion; ASO/supporting screens; verify no overloaded English captions if composited. |
| fitchef-candidate-003 | Seed: thinking (`fitchef-portrait-thinking-v1`) | approved_seed | canon_aligned | Planning/reflection vibe; fits “nutrition insight” metaphors without medical claims when paired with lawful copy. |
| fitchef-candidate-004 | Seed: sleepy (`fitchef-portrait-sleepy-v1`) | approved_seed | canon_aligned | Rest/calm lanes; ASO tertiary; avoid implying sleep/medical outcome guarantees in surrounding copy. |
| fitchef-candidate-005 | Seed: surprised (`fitchef-portrait-surprised-v1`) | approved_seed | canon_aligned | Attention/grab; social-friendly; headline must remain wellness-informational per contract. |
| fitchef-candidate-006 | Seed: onboarding (`fitchef-onboarding-welcome-v1`) | approved_seed | canon_aligned | Welcome/hero archetype; strongest ASO candidate among seeds **if** layout matches composition rules (`FITCHEF_APP_STORE_VISUAL_CONTRACT.md`); still no fake standalone UI chrome. |
| fitchef-candidate-007 | CANDIDATE #1 | social_ready¹ | no_runtime_promotion | Default CANDIDATE: OK for organic social once scanned for embedded English/medical/guarantee/fake UI; hold ASO first position until cleared. |
| fitchef-candidate-008 | CANDIDATE #2 | social_ready¹ | no_runtime_promotion | Same tier as #007; prioritize short-form clips and Stories CTA to real product flows. |
| fitchef-candidate-009 | CANDIDATE #3 | aso_supporting_hold¹ | no_runtime_promotion | Typical compositional drift risk; localize text layers before placing in ASO carousel. |
| fitchef-candidate-010 | CANDIDATE #4 | social_ready¹ | no_runtime_promotion | Social-first; screenshot order only after text-risk pass. |
| fitchef-candidate-011 | CANDIDATE #5 | aso_supporting_hold¹ | no_runtime_promotion | Audit for mock dashboard density; may read as “fake UI promise” if copy overclaims. |
| fitchef-candidate-012 | CANDIDATE #6 | social_ready¹ | no_runtime_promotion | Mascot-forward variant; default social when English does not dominate. |
| fitchef-candidate-013 | CANDIDATE #7 | reference_archive¹ | no_runtime_promotion | Often layout exploration; defer ASO hero use until aligns with seven-shot honesty rules. |
| fitchef-candidate-014 | CANDIDATE #8 | aso_supporting_hold¹ | no_runtime_promotion | If frame nests dense metrics, downgrade to blocked_gtm for CIS until rewritten. |
| fitchef-candidate-015 | CANDIDATE #9 | social_ready¹ | no_runtime_promotion | Short-form friendly; companion to paid UGC tests. |
| fitchef-candidate-016 | CANDIDATE #10 | social_ready¹ | no_runtime_promotion | Default paid social carousel tile if visual passes compliance scan. |
| fitchef-candidate-017 | CANDIDATE #11 | aso_supporting_hold¹ | no_runtime_promotion | Check FitChef-plus-data compositions for “results guarantee” implication. |
| fitchef-candidate-018 | CANDIDATE #12 | reference_archive¹ | no_runtime_promotion | Reserve for decks / qualitative testing; rarely primary ASO. |
| fitchef-candidate-019 | CANDIDATE #13 | blocked_gtm¹ | blocked_runtime | **Flag slot:** commonly food/chart composites—scrub for diagnostic language (“your risk”) and fake live scores; escalate to `aso_supporting_hold`/`social_ready` after rework proof.² |
| fitchef-candidate-020 | CANDIDATE #14 | aso_supporting_hold¹ | no_runtime_promotion | Mid-funnel nurture; localize before Apple-facing use. |
| fitchef-candidate-021 | CANDIDATE #15 | social_ready¹ | no_runtime_promotion | Acceptable mascot-led social proof when paired compliant caption. |
| fitchef-candidate-022 | CANDIDATE #16 | reference_archive¹ | no_runtime_promotion | Mood/atmosphere comps; marketing reference only unless simplified. |
| fitchef-candidate-023 | CANDIDATE #17 | social_ready¹ | no_runtime_promotion | Variant rotation for A/B creatives; watch English density. |
| fitchef-candidate-024 | CANDIDATE #18 | blocked_gtm¹ | blocked_runtime | **Flag slot:** high risk of mock-phone UI implying shipped feature set; treat as illustrative only pending product parity review.² |
| fitchef-candidate-025 | CANDIDATE #19 | aso_supporting_hold¹ | no_runtime_promotion | Conditional ASO: only if headline/supporting lines pass wellness guard; else downgrade. |
| fitchef-candidate-026 | CANDIDATE #20 | social_ready¹ | no_runtime_promotion | Closing social tile in campaigns; reinforce “wellness informational” disclaimers where required. |
| fitchef-candidate-027 | REFERENCE-ONLY #1 | reference_archive | no_runtime_promotion | Board label dictates archive use; internal/Figma-aligned messaging only—not App Store carousel. |
| fitchef-candidate-028 | REFERENCE-ONLY #2 | reference_archive | no_runtime_promotion | Same as #027; no paid promotion asserting product truth without redesign. |
| fitchef-candidate-029 | REFERENCE-ONLY #3 | reference_archive | no_runtime_promotion | Same as #027–028; training / partner deck only. |
| fitchef-candidate-030 | NEEDS-REWORK | blocked_gtm | blocked_runtime | Do not ship in marketing or runtime until rework lands; expect medical/fake-UI/text fixes in Figma export. |

¹ **Supersedable:** If the frame at that index is clearly mascot-only with no hazardous copy, operator may raise one tier (e.g. `aso_supporting_hold` → `social_ready`). If scan finds English/medical/guarantee/fake UI, apply **Automatic flags** and lower tier.
² **High-churn slots:** If your Figma sort places a safe mascot-only frame at #19 or #24, swap classification with the nearest `social_ready` neighbor after documented QA.

---

## 3) Shortlist: App Store screenshot vs social-only vs reference-only

| Track | Keys | Notes |
| --- | --- | --- |
| **App Store screenshot candidate (primary / early shots)** | `fitchef-candidate-001`–`006` | Only seed pack with known filenames; pair with real UI stills per `FITCHEF_APP_STORE_VISUAL_CONTRACT.md`. |
| **App Store screenshot (supporting / later shots)** | `fitchef-candidate-009`, `011`, `014`, `017`, `020`, `025` **if** QA upgrades from `aso_supporting_hold` to cleared state | All require localized, non-guarantee headlines. |
| **Social-only (organic + paid)** | `007`, `008`, `010`, `012`, `015`, `016`, `021`, `023`, `026` when `social_ready` holds after scan | Prefer Stories/Reels/short carousel; disclose illustrative composites if mock UI appears. |
| **Reference-only (internal / partner / training)** | `013`, `018`, `022`, **`027`–`029`** | Reference boards; not for consumer ASO shelf without rework PR. |
| **Hold / rework before any public use** | `019`, `024`, **`030`** + any row bumped by **Automatic flags** | Blocklisted until caption or pixels prove wellness-safe parity. |

---

## Evidence anchors

- `docs/figma/FITCHEF_BRAND_REFERENCE_HANDOFF.md:33` (`1473:2` board inventory counts)
- `docs/design/FITCHEF_MASCOT_ASSET_CANON.md` (six approved seed filenames)
- `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md` (composition and copy posture)

---

## Deferred / Follow-ups

- Per-frame QA with screenshots: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-candidate-intake-visual-qa`
- Any repo binary promotion remains a separate PR; this doc **does not** authorize runtime asset changes.
