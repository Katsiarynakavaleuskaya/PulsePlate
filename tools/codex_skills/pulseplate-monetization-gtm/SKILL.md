---
name: pulseplate-monetization-gtm
description: Handle PulsePlate monetization, paywall, pricing, and wellness-safe GTM work without bypassing coordinator-first policy or inventing unsafe growth claims.
---

# PulsePlate Monetization And GTM

## When to use

- Shaping paywall copy, subscription framing, or pricing experiment notes.
- Reviewing billing-flow docs, subscription activation surfaces, or conversion instrumentation.
- Preparing ASO, SEO, Product Hunt, or launch-channel drafts that must stay wellness-safe.

## Inputs required

- Monetization surface in scope (`paywall`, `pricing`, `subscription_flow`, `growth_channel`, or `launch_copy`).
- Candidate file paths or docs surfaces being changed.
- Expected outcome (`docs-strategy`, `implementation-brief`, or `experiment-plan`).

## Procedure (commands)

1. Load monetization truth and growth context:

   ```bash
   sed -n '1,220p' docs/product/FREE_PRO_SOFT_PAYWALL.md
   sed -n '1,220p' docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md
   sed -n '1,220p' docs/marketing/GTM_NOTES_DEV_ONLY.md
   ```

2. Verify paywall and billing surfaces before editing:

   ```bash
   rg -n "paywall|subscription|pricing|billing|trial|restore|conversion" app/services core docs/marketing docs/analytics docs/product
   pytest -q tests/test_subscription_activation_api.py
   pytest -q tests/test_paywall_exposure_ledger_api.py
   pytest -q tests/test_payment_source_contract_api.py
   ```

3. Keep growth claims and governance fail-closed:

   ```bash
   python3 scripts/orchestration/check_preflight.py
   python3 scripts/orchestration/check_agent_consistency.py
   pre-commit run --all-files
   make verify
   ```

## Output format

- `Monetization surface`: exact paywall / pricing / subscription area touched.
- `Growth surface`: ASO / SEO / Product Hunt / launch channel scope, if any.
- `Evidence`: tests, contracts, analytics, or policy references used.
- `Wellness-safe notes`: claims avoided, disclaimers preserved, and reviewer-sensitive wording.
- `Follow-up`: experiment, launch, or rollout items that remain operator-owned after merge.

## Guardrails

- Do not bypass coordinator-first routing or turn this skill into final business authority.
- Do not recommend coercive paywalls or hide pricing, restore, trial, or cancellation truth.
- Do not treat screenshots, stale metadata, or marketing copy as billing truth; runtime/storefront truth remains authoritative.
- Do not introduce medical, psychological, or outcomes claims that exceed wellness-safe positioning.
- Keep `recommended_skills` additive; this skill should complement, not replace, repo policy.

## SoT links

- `AGENTS.md`
- `docs/product/FREE_PRO_SOFT_PAYWALL.md`
- `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`
- `docs/marketing/GTM_NOTES_DEV_ONLY.md`
- `docs/marketing/WELCOME_GATE_GTM_OUTLINE.md`
- `app/services/payments_activation.py`
- `core/billing_policy.py`
- `tests/test_subscription_activation_api.py`
- `tests/test_paywall_exposure_ledger_api.py`
