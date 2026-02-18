# Luxury UI Review Checklist (PR)

Use this checklist for PR review of iOS/Web visuals and generated assets.
This is a short operational gate for premium quality and UX safety.

Related SoT:

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`

## PR Gate (Pass/Fail)

- [ ] **Brand lock:** palette and style stay within PulsePlate visual DNA
      (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:20`,
      `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:26`).
- [ ] **Hierarchy:** one clear focal area and readable information order
      (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:90`,
      `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:93`).
- [ ] **Legibility:** text/icons remain clear at target device sizes
      (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:105`,
      `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:114`).
- [ ] **Motion comfort:** animations are smooth, purposeful,
      and reduced-motion safe
      (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:97`,
      `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:99`).
- [ ] **Accessibility:** WCAG AA contrast baseline is met
      (4.5:1 body, 3:1 large text), focus visibility is clear,
      and controls are obviously tappable/clickable
      (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:50`,
      `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:111`).
- [ ] **Wellness safety:** no clinical/diagnostic framing or manipulative fear tone
      (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:145`,
      `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:182`).
- [ ] **Cross-surface consistency:** iOS, Web, and social variants
      feel like one family
      (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:171`,
      `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:195`).

## Prompt/Generated Visual Add-on (when applicable)

- [ ] Prompt includes mandatory guard clauses and negative constraints
      (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:287`,
      `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:295`).
- [ ] Generated outputs pass anti-drift checks before product/social usage
      (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:274`,
      `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:313`).
- [ ] Fallback static visual is defined if generated media fails QA
      (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:322`,
      `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:326`).

If any required item fails, PR is not ready for design sign-off.
