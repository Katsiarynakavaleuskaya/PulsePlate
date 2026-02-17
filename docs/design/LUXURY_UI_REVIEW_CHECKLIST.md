# Luxury UI Review Checklist (PR)

Use this checklist for PR review of iOS/Web visuals and generated assets.
This is a short operational gate for premium quality and UX safety.

Related SoT:

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`

## PR Gate (Pass/Fail)

- [ ] **Brand lock:** palette and style stay within PulsePlate visual DNA.
- [ ] **Hierarchy:** one clear focal area and readable information order.
- [ ] **Legibility:** text/icons remain clear at target device sizes.
- [ ] **Motion comfort:** animations are smooth, purposeful,
      and reduced-motion safe.
- [ ] **Accessibility:** contrast and interaction affordances satisfy baseline checks.
- [ ] **Wellness safety:** no clinical/diagnostic framing or manipulative fear tone.
- [ ] **Cross-surface consistency:** iOS, Web, and social variants
      feel like one family.

## Prompt/Generated Visual Add-on (when applicable)

- [ ] Prompt includes mandatory guard clauses and negative constraints.
- [ ] Generated outputs pass anti-drift checks before product/social usage.
- [ ] Fallback static visual is defined if generated media fails QA.

If any required item fails, PR is not ready for design sign-off.
