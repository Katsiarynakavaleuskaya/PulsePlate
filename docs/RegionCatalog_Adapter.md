# Region Catalog Adapter (Mock-first) — PR-6

## Purpose

Attach optional catalog metadata (SKU/price/aisle/pack label) to VIP shoplist lines.

## Principles

- **Adapter-only enrichment** (engine unchanged)
- **Fail-soft**: missing catalog is not an error
- **Deterministic**: enrichment does not change packs/reasons/analytics
- **Backward compatible**: catalog field is optional

## Architecture

```
Engine (core) → Build Response → Enrichment (adapter) → Final Response
```

Enrichment happens **after** engine calculation, does not affect:
- Pack counts
- Overage calculations
- Explainability reasons
- Analytics

## How to Use

Add optional query parameters to any VIP shoplist endpoint:

- `region_id`: Region identifier (e.g., `es`, `us`)
- `store_id`: Store identifier (e.g., `carrefour_es`, `walmart_us`)

### Example Request

```bash
POST /api/v1/vip/shoplist/generate?region_id=es&store_id=carrefour_es
```

### Example Response

```json
{
  "packed": [
    {
      "food_id": "carrot",
      "packs": 1,
      "reasons": ["min_packs", "rounding"],
      "catalog": {
        "sku": "CRF-ES-000123",
        "store_id": "carrefour_es",
        "region_id": "es",
        "pack_label": "500 g bag",
        "aisle": "Vegetables",
        "price": {
          "value": "1.29",
          "currency": "EUR"
        }
      }
    }
  ]
}
```

## Fields

Response lines may include optional `catalog` field with:

- `sku`: Stock Keeping Unit
- `store_id`: Store identifier
- `region_id`: Region identifier
- `pack_label`: Human-friendly pack label (optional)
- `aisle`: Store aisle/category label (optional)
- `price`: Price estimate with currency (optional)

## Behavior

- **If region_id/store_id not provided**: No enrichment, `catalog` field is `None`
- **If catalog found**: `catalog` field populated with data
- **If catalog not found**: `catalog` field is `None` (fail-soft, no error)

## Current Implementation (PR-6)

- **Mock provider only**: In-memory catalog data
- **No external calls**: No HTTP/DB access
- **Minimal dataset**: Sample data for `carrot` in `es`/`us` regions

## Future (PR-7)

- Real catalog loaders (Carrefour/Walmart APIs)
- Provider interface allows swapping mock → real without contract changes
- Same fail-soft behavior maintained

## Security Notes

- No real API keys in PR-6 (mock-only)
- No external HTTP calls
- Catalog data is static/validated
- Enrichment does not affect gating/authentication

## Related

- [`docs/VIP_Shoplist_API.md`](VIP_Shoplist_API.md) — Base API contract
- [`PR-6_HANDOFF.md`](../PR-6_HANDOFF.md) — Implementation handoff
