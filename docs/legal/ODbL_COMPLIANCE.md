# ODbL Compliance (Food Data)

## Scope
- Food-source licensing and attribution for data served by Food API contracts.
- Primary affected source: Open Food Facts (ODbL v1.0).

## Runtime Contract
- Canonical attribution endpoint: `GET /api/v1/pro/attribution`
- Endpoint returns:
  - source name
  - license label
  - attribution text
  - source URL (if present)

## Implementation Anchors
- Router: `app/routers/pro_food_attribution.py`
- Source registry: `app/services/food_store.py`
- Response schema: `app/schemas/food.py`
- Contract tests: `tests/test_pro_food_attribution.py`

## Policy
- All Open Food Facts-derived records must keep ODbL attribution in public API payloads.
- Source-license metadata must remain server-side canonical (no client-side hardcoding).
- New food providers must be added to the attribution registry before public rollout.
- Cross-provider onboarding defaults for ingestion, caching, redistribution, and
  commercial-risk review live in
  `docs/legal/EXTERNAL_FOOD_SOURCE_OPERATING_POLICY.md`.

## Follow-ups
- Add UI surface for attribution in web/iOS settings/help.
- Expand legal checklist for derivative DB publication workflow.
- Keep the broader external-source operating matrix aligned when new providers
  are introduced.
