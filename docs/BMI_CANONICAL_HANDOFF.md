# PulsePlate — BMI Canonical Track (Context Handoff)

**Status:** Canonical / source-of-truth document for BMI track.

## Invariants

1. **One BMI Engine**
   - All BMI math/thresholds live only in `core/bmi/*`.
   - `app/*`, web, iOS are adapters/renderers only.

2. **Free BMI = expanded screening**
   - Groups: `too_young`, `child`, `teen`, `general`, `athlete`, `elderly`, `pregnant`.
   - Optional WHtR + waist risk.
   - Medical disclaimers included.
   - No calories/nutrition/products in Free tier.

3. **Children ≠ Teens**
   - Separate domain logic and interpretations.

## Anti-duplication enforcement (required)

- Policy: No BMI math outside `core/bmi/*`.
- Golden parity tests: legacy ↔ engine numeric invariants.
- Guard test: CI fails if BMI math appears outside `core/bmi`.

## Roadmap

- **PR-453:** Engine + schemas (domain + API contract)
- **PR-454:** Legacy BMI → thin proxy to engine
- **PR-455:** Public endpoint `POST /api/v1/bmi/calculate`
- **PR-456/457:** Thin clients (web/iOS) call API only

## Notes

- `category=None` is valid for `pregnant`, `too_young`, `child`, `teen` (medical disclaimer).

