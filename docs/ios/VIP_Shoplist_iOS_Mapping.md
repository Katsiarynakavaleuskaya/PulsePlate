# VIP Shoplist API — iOS Mapping Table

> **Status:** Reference for iOS integration
> **Contract:** [`docs/VIP_Shoplist_API.md`](../VIP_Shoplist_API.md)
> **Swift Models:** [`VIPShoplistDTO.swift`](VIPShoplistDTO.swift)

---

## JSON ↔ Swift Type Mapping

---

## JSON ↔ Swift Type Mapping

| JSON Path                          | JSON Type      | Swift Type                    | Notes                                    |
|------------------------------------|----------------|-------------------------------|------------------------------------------|
| `qty.value`                        | string         | `String`                      | Decimal-as-string (parse with `asDecimal()`) |
| `qty.unit`                         | enum string    | `Unit`                        | `"G"`, `"ML"`, `"PCS"`, `"KG"`, `"L"`   |
| `item.form`                        | enum string    | `FoodForm`                    | `"RAW"`, `"COOKED"`, `"FROZEN"`, etc.   |
| `rule.rounding`                    | enum string    | `RoundingMode`                | `"CEIL"`, `"NEAREST"`, `"NONE"`         |
| `rule.min_packs`                   | int            | `Int`                         | `>= 1`                                   |
| `packed[].reasons`                 | string[]       | `[String]`                    | Stable order (deterministic)            |
| `unpacked[].reason`                | string         | `String`                      | Default: `"no_packaging_rule"`           |
| `analytics.total_overage_by_unit` | object map     | `[Unit: String]`              | Values are Decimal strings              |
| `days[]`                           | array          | `[ShoplistGenerateResponse]` | Weekly endpoint response; length = as requested (no fixed 7-day requirement) |

---

## Key Principles

### 1. Decimal Serialization

All `Decimal` fields arrive as **strings** in JSON. Parse when needed:

```swift
let quantity = QuantityDTO(value: "100.5", unit: .g)
if let decimal = quantity.decimalValue {
    // Use Decimal for calculations
}
```

### 2. Enums

All enums are `String, Codable`:

```swift
enum Unit: String, Codable, Hashable {
    case g = "G"
    case ml = "ML"
    // ...
}
```

### 3. Snake Case → Camel Case

Swift models use camelCase with `CodingKeys`:

```swift
struct ShoplistItemDTO: Codable {
    let foodId: String  // JSON: "food_id"

    enum CodingKeys: String, CodingKey {
        case foodId = "food_id"
    }
}
```

### 4. Optional Fields

- `packaging_rules`: `[PackageRuleDTO]?` (can be `null`)
- `analytics`: `ShoplistAnalyticsDTO?` (included by default, but optional in contract)

---

## Usage Examples

### Generate Request

```swift
let request = ShoplistGenerateRequest(
    items: [
        ShoplistItemDTO(
            foodId: "carrot",
            qty: QuantityDTO(value: "100", unit: .g),
            form: .raw
        )
    ],
    packagingRules: [
        PackageRuleDTO(
            foodId: "carrot",
            packSize: QuantityDTO(value: "500", unit: .g),
            rounding: .ceil,
            minPacks: 1
        )
    ]
)
```

### Weekly Request

```swift
let weeklyRequest = ShoplistWeeklyRequest(
    days: [
        ShoplistWeeklyDayRequest(
            items: [...],
            packagingRules: [...]
        )
    ]
)
```

### Response Handling

```swift
let response: ShoplistGenerateResponse = // ... decoded from JSON

// Access packed items
for packed in response.packed {
    print("\(packed.foodId): \(packed.packs) packs")
    print("Reasons: \(packed.reasons.joined(separator: ", "))")
}

// Access analytics
if let analytics = response.analytics {
    print("Total lines: \(analytics.totalLines)")
    print("Overage: \(analytics.totalOverageByUnit)")
}
```

---

## Error Handling

### HTTP Status Codes

| Status | Meaning                          | Swift Handling                    |
|--------|----------------------------------|-----------------------------------|
| 200    | Success                          | Decode `ShoplistGenerateResponse`  |
| 401    | Missing/invalid API key          | Show auth error                   |
| 403    | Insufficient VIP tier             | Show upgrade prompt                |
| 404    | VIP module disabled               | Show feature unavailable          |
| 422    | Validation error (invalid enum)   | Show field-specific error         |
| 500    | Internal error (invariant)        | Log and show generic error        |

### Example Error Response (422)

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

---

## Determinism Guarantees

- **Same input → same output**: Identical requests produce identical responses
- **Stable ordering**: `packed[].reasons` order is deterministic
- **Decimal strings**: No floating-point precision issues

---

## See Also

- [`docs/VIP_Shoplist_API.md`](../VIP_Shoplist_API.md) — Full API contract
- [`VIPShoplistDTO.swift`](VIPShoplistDTO.swift) — Complete Swift models
