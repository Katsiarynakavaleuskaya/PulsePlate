# TensorTonic Public Pattern Adaptation for PulsePlate

**Status:** Proposed docs-only product direction
**Last updated:** 8 March 2026
**Scope:** Public TensorTonic patterns that fit PulsePlate wellness product constraints

---

## Summary

TensorTonic exposes several strong public product patterns:

- structured challenge catalog,
- modular topic progression,
- concept explanation paired with practical scenarios,
- interactive simulator-style learning,
- visible progress loops.

For PulsePlate, the correct adaptation is **not** an ML curriculum, coding IDE, or
public competition layer. The correct adaptation is:

- deterministic explainers on top of existing FREE / PRO / VIP outputs,
- learning-cycle progression around understanding and behavior,
- interactive confidence/progress framing,
- guided practice loops tied to current wellness logic.

This note is grounded only in public pages because `https://www.tensortonic.com/problems`
redirects to login and is inaccessible without user credentials.

## Public Inputs Reviewed

- `https://www.tensortonic.com/`
- `https://www.tensortonic.com/ml-math`
- `https://www.tensortonic.com/ml-math/statistics/ab-testing`
- `docs/product/FREE_PRO_CONTRACT.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

## Product Fit for PulsePlate

### Best-fit patterns

1. **Explain before upsell**
   - TensorTonic packages learning into understandable units.
   - PulsePlate should package current wellness logic into explainers that clarify
     what the result means, what it misses, and what the next useful step is.

2. **Progress as understanding**
   - TensorTonic makes progress visible.
   - PulsePlate should represent progress as completed explainers, unlocked learning
     cycles, and improved confidence in pattern understanding rather than streak
     pressure.

3. **Interactive practical framing**
   - TensorTonic's public A/B testing lesson combines concept, pitfalls, scenario,
     and simulator.
   - PulsePlate can adapt this into lightweight simulator-style micro-surfaces for
     wellness-safe topics such as adherence confidence and interpretation confidence.

4. **Modular learning path**
   - TensorTonic groups topics into modules.
   - PulsePlate should group user understanding into deterministic cycles:
     baseline, interpretation context, consistency pattern, and adjustment.

### Explicit non-fit

PulsePlate should **not** import these TensorTonic patterns into the consumer app:

- ML curriculum or algorithm problem catalog,
- browser coding IDE,
- public leaderboards,
- addictive streak loops,
- research-paper implementation track inside end-user wellness flows.

These patterns either do not map to the current product contract or create the wrong
motivation model for a wellness product.

## Fit to FREE / PRO / VIP Contract

- **FREE:** explain what BMI captures, what it does not capture, and why the result is
  an orientation layer and informational overview only.
- **PRO:** explain why interpretation changes when additional signals such as waist
  context or other risk signals are present.
- **VIP:** explain why the current plan, target, or action is recommended and what
  pattern the user is improving.

This reinforces the canonical trust-based funnel:

- FREE = where am I now?
- PRO = why does this matter for me?
- VIP = what do I do about it every day?

## Future Interface Direction

These interfaces remain backend-owned and rules-first:

The payload shapes below are **planning-level canonical direction**, not final
runtime schemas. When implementation starts, the concrete names and envelopes
must align with `app/schemas/` and OpenAPI conventions so web and iOS stay thin
render-only clients.

### `explainer_card`

- `title`
- `what_this_means`
- `what_is_missing` or `why_this_matters`
- `next_step`
- optional `learning_cycle_id`

### `learning_cycle_state`

- `cycle_id`
- `label`
- `unlocked_by`
- `what_you_learned`
- `next_action`

### `explainer_progress_event`

- event name for completion or unlock
- surface identifier
- cycle identifier when applicable
- low-cardinality metadata aligned with existing progress instrumentation

## Delivery Constraints

- Backend owns explainer assembly and cycle unlock logic.
- Frontend and iOS render payloads only.
- No new heavy LLM endpoint is introduced on the core path.
- Any optional AI-assisted copy must pass
  `core.insight.philosophy_validator.validate_llm_output(...)`; `BLOCKER` output
  means rewrite before any product copy or coaching use, and the feature must
  remain behind current quota and economic controls.
- Any telemetry must remain low-cardinality and privacy-safe.

These delivery constraints are the canonical explainer guardrails for follow-up
backlog items. Future ledger entries should reference this note instead of
repeating the same bans and LLM/telemetry rules in multiple places.

## GTM Positioning

This work should be positioned as **trust and retention infrastructure**, not
gamification.

Recommended product framing:

> Understand why this wellness result exists, what it misses, and what the next
> useful action is.

This supports FREE -> PRO -> VIP conversion through clarity and confidence rather
than pressure or competition.
