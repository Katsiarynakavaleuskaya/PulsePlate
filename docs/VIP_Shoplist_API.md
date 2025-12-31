# VIP Shoplist API — Contract Freeze (v1)

> **Status:** Frozen
> **Scope:** Backend contract only (engine-first, adapter-only)
> **Audience:** iOS / React / API consumers
> **Updated:** PR-5

---

## 1. Overview

VIP Shoplist API provides **deterministic shopping list generation** with:
- explainability ("why this many packs"),
- waste/overage analytics,
- strict VIP gating.

### Architecture principles
- **Engine-first**: core engine is pure, offline, deterministic.
- **Adapter-only enrichments**: explainability, analytics, gating live in API adapters.
- **No DB / no I/O** during calculation.
- **Decimal-only math** (no floats).

---

## 2. Authentication & Gating

### Required
- API key (header: `X-API-Key`)
- VIP tier
- `VIP_MODULE_ENABLED = true`

### Gating matrix

| Scenario                               | HTTP Status |
|----------------------------------------|-------------|
| VIP module disabled                    | 404         |
| Missing / invalid API key              | 401 / 403   |
| Valid key, insufficient tier           | 403         |
| Invalid enum / DTO validation error    | 422         |
| Adapter invariant violation            | 500         |

> **Note:** 500 is reserved for internal invariant violations
> (e.g. engine returned `packed`, but adapter cannot find `PackageRule`).

---

## 3. Common Types

### Quantity
```json
{
  "value": "100",
  "unit": "G"
}
```

- `value`: string (Decimal serialization)
- `unit`: enum (see below)

### Enums

#### Unit
- `G` (grams)
- `ML` (milliliters)
- `PCS` (pieces)
- `KG` (kilograms, normalized to G)
- `L` (liters, normalized to ML)

#### FoodForm
- `RAW`
- `COOKED`
- `FROZEN`
- `DRIED`
- `CANNED`

#### RoundingMode
- `CEIL` (round up, never undersupply)
- `NEAREST` (round to nearest, prefer oversupply)
- `NONE` (no rounding, exact match)

**Invalid enum → 422**

---

## 4. Explainability & Analytics (Guaranteed)

### Explainability

- `PackedLineDTO.reasons: string[]`
  - **stable order** (deterministic)
  - Examples: `["min_packs", "rounding"]`, `["rounding"]`
- `UnpackedLineDTO.reason`
  - Default: `"no_packaging_rule"`

### Analytics

Returned when `include_analytics=True` (default for all endpoints):

```json
"analytics": {
  "total_lines": 3,
  "packed_lines": 2,
  "unpacked_lines": 1,
  "total_overage_by_unit": {
    "G": "150",
    "ML": "0"
  }
}
```

- All numeric values → **string (Decimal serialization)**
- `total_overage_by_unit`: aggregated overage per unit type

---

## 5. Endpoints

### 5.1 POST `/api/v1/vip/shoplist/generate`

Generate shopping list with packaging rules applied.

#### Request

```json
{
  "items": [
    {
      "food_id": "carrot",
      "qty": { "value": "100", "unit": "G" },
      "form": "RAW"
    }
  ],
  "packaging_rules": [
    {
      "food_id": "carrot",
      "pack_size": { "value": "500", "unit": "G" },
      "rounding": "CEIL",
      "min_packs": 1
    }
  ]
}
```

**Fields:**
- `items`: list of `ShoplistItemDTO` (required, can be empty)
- `packaging_rules`: list of `PackageRuleDTO` (optional, `null` allowed)

#### Response (200)

```json
{
  "packed": [
    {
      "food_id": "carrot",
      "requested": { "value": "100", "unit": "G" },
      "pack_size": { "value": "500", "unit": "G" },
      "packs": 1,
      "provided": { "value": "500", "unit": "G" },
      "overage": { "value": "400", "unit": "G" },
      "rounding": "CEIL",
      "min_packs": 1,
      "reasons": ["min_packs", "rounding"]
    }
  ],
  "unpacked": [],
  "analytics": {
    "total_lines": 1,
    "packed_lines": 1,
    "unpacked_lines": 0,
    "total_overage_by_unit": { "G": "400" }
  }
}
```

---

### 5.2 POST `/api/v1/vip/shoplist/daily`

Generate daily shopping list. **Same contract as `/generate`**.

#### Request

Same as `/generate`:
```json
{
  "items": [...],
  "packaging_rules": [...]
}
```

#### Response (200)

Same as `/generate`:
```json
{
  "packed": [...],
  "unpacked": [...],
  "analytics": { ... }
}
```

#### Guarantees

- Deterministic output
- Explainability + analytics included (always)
- Missing `packaging_rules` → allowed (items go to `unpacked`)

---

### 5.3 POST `/api/v1/vip/shoplist/weekly`

Generate weekly shopping list (multiple days).

#### Request

```json
{
  "days": [
    {
      "items": [
        {
          "food_id": "carrot",
          "qty": { "value": "100", "unit": "G" },
          "form": "RAW"
        }
      ],
      "packaging_rules": [
        {
          "food_id": "carrot",
          "pack_size": { "value": "500", "unit": "G" },
          "rounding": "CEIL",
          "min_packs": 1
        }
      ]
    }
  ]
}
```

**Fields:**
- `days`: list of day requests (each follows `/generate` request format)

#### Response (200)

```json
{
  "days": [
    {
      "packed": [...],
      "unpacked": [...],
      "analytics": { ... }
    }
  ]
}
```

#### Weekly contract

- `days.length` = as requested (no fixed 7-day requirement)
- Each day follows **daily/generate contract**
- Each day has independent analytics

---

## 6. Response Guarantees

### Determinism

- Same input → same output
- Ordering normalized internally
- No time / randomness / external calls

### Decimal Serialization

- All `Decimal` fields in JSON as **string**
- Examples: `"100"`, `"150.5"`, `"0"`

### Explainability

- `PackedLineDTO.reasons`: **stable order**, deterministic
- `UnpackedLineDTO.reason`: always present (default `"no_packaging_rule"`)

### Analytics

- Always included in `/generate`, `/daily`, `/weekly` responses
- `total_overage_by_unit`: aggregated across all packed items

---

## 7. Error Contract

### 422 Unprocessable Content (Validation Error)

Example for invalid enum:

```json
{
  "detail": [
    {
      "loc": ["body", "items", 0, "qty", "unit"],
      "msg": "Input should be 'G', 'ML', 'PCS', 'KG' or 'L'",
      "type": "enum"
    }
  ]
}
```

Example for invalid DTO structure:

```json
{
  "detail": [
    {
      "loc": ["body", "packaging_rules", 0, "min_packs"],
      "msg": "Input should be greater than or equal to 1",
      "type": "greater_than_equal"
    }
  ]
}
```

### 404 Not Found

VIP module disabled:

```json
{
  "detail": "Not Found"
}
```

### 401/403 Unauthorized/Forbidden

Missing or invalid API key / insufficient tier:

```json
{
  "detail": "Invalid API key for VIP tier"
}
```

### 500 Internal Server Error

Adapter invariant violation (should not occur in normal operation):

```json
{
  "detail": "Packed item {food_id} missing packaging rule"
}
```

---

## 8. cURL Examples

### Generate (EN)

```bash
curl -X POST \
  https://api.example.com/api/v1/vip/shoplist/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test_key" \
  -d '{
    "items": [
      {
        "food_id": "carrot",
        "qty": { "value": "100", "unit": "G" },
        "form": "RAW"
      }
    ],
    "packaging_rules": [
      {
        "food_id": "carrot",
        "pack_size": { "value": "500", "unit": "G" },
        "rounding": "CEIL",
        "min_packs": 1
      }
    ]
  }'
```

### Daily (RU)

```bash
curl -X POST \
  https://api.example.com/api/v1/vip/shoplist/daily \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test_key" \
  -d '{
    "items": [
      {
        "food_id": "морковь",
        "qty": { "value": "100", "unit": "G" },
        "form": "RAW"
      }
    ],
    "packaging_rules": [
      {
        "food_id": "морковь",
        "pack_size": { "value": "500", "unit": "G" },
        "rounding": "CEIL",
        "min_packs": 1
      }
    ]
  }'
```

### Weekly (ES)

```bash
curl -X POST \
  https://api.example.com/api/v1/vip/shoplist/weekly \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test_key" \
  -d '{
    "days": [
      {
        "items": [
          {
            "food_id": "zanahoria",
            "qty": { "value": "100", "unit": "G" },
            "form": "RAW"
          }
        ],
        "packaging_rules": [
          {
            "food_id": "zanahoria",
            "pack_size": { "value": "500", "unit": "G" },
            "rounding": "CEIL",
            "min_packs": 1
          }
        ]
      }
    ]
  }'
```

---

## 9. Endpoint Comparison

| Feature                    | `/generate` | `/daily` | `/weekly` |
|----------------------------|-------------|----------|-----------|
| Request format             | Single day  | Single day | Multiple days |
| Response format            | Single day  | Single day | Array of days |
| Analytics                  | ✅ Always   | ✅ Always   | ✅ Always (per day) |
| Explainability (reasons)   | ✅ Always   | ✅ Always   | ✅ Always (per day) |
| VIP gating                 | ✅ Required | ✅ Required | ✅ Required |
| Missing packaging_rules   | ✅ Allowed  | ✅ Allowed  | ✅ Allowed |

---

## 10. Versioning Rules

- This document is **source of truth** for API contract
- Any breaking change:
  - requires version bump
  - must update this file
  - must be documented in changelog
- Adapter-only extensions allowed if backward compatible

---

## 11. Non-Goals

- Region/catalog enrichment
- Pricing / SKU resolution
- UI formatting
- Food name translation

(handled in separate adapters / future PRs)

---

**End of contract**
