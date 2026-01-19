# Soft Paywall Hook Contract (Text-only)

**Status:** Canonical contract (documentation-only)
**Last updated:** 2026-01-19
**Scope:** Free → Pro soft paywall hook. **Text-only. No BMI logic.**

## Purpose

The Soft Paywall Hook is a **UX/marketing signal** shown after BMI results to suggest upgrading to PRO.
It must remain **strictly text-only** and **must not** depend on BMI calculation logic.

## Where it is produced (FACTS)

- Builder: `app/routers/_helpers.py::_build_soft_paywall_hook(lang, default_enabled)`
- FREE endpoint: `POST /api/v1/bmi/calculate` (default_enabled = `true`)
- PRO endpoint: `POST /api/v1/pro/bmi/calculate` (default_enabled = `false`)
- Response field name: `soft_paywall`
- Type: `SoftPaywallHook | null`
- Disabled state: `soft_paywall: null` (not `{enabled:false}`)

Legacy endpoint note:
- `POST /api/v1/pro/bmi` is deprecated and does **not** attach `soft_paywall`.

## Contract

### Response field

`soft_paywall` is an additive field on BMI responses:

```json
{
  "soft_paywall": null
}
```

or

```json
{
  "soft_paywall": {
    "id": "bmi.pro_interpretation_v1",
    "kind": "cta",
    "position": "post_result",
    "priority": 50,
    "message": {
      "lang": "en",
      "title_key": "soft_paywall.title",
      "body_key": "soft_paywall.body",
      "cta_key": "soft_paywall.cta",
      "default_title": "More accurate interpretation",
      "default_body": "BMI doesn't account for fat distribution or context. Want a more accurate wellness interpretation?",
      "default_cta": "See PRO"
    },
    "availability": {
      "pro_available": true,
      "reason_key": null
    },
    "target": "pro_paywall"
  }
}
```

### Schema: SoftPaywallHook

| Field          | Type                      | Required | Notes                                           |
| -------------- | ------------------------- | -------- | ----------------------------------------------- |
| `id`           | `string`                  | yes      | Stable identifier (`bmi.pro_interpretation_v1`) |
| `kind`         | `"cta"`                   | yes      | Fixed literal                                   |
| `position`     | `"post_result"`           | yes      | Fixed literal                                   |
| `priority`     | `integer`                 | yes      | `0..100`, default `50`                          |
| `message`      | `SoftPaywallMessage`      | yes      | Localized text payload                          |
| `availability` | `SoftPaywallAvailability` | yes      | Availability payload                            |
| `target`       | `"pro_paywall"`           | yes      | Fixed literal (client route/action target)      |

### Schema: SoftPaywallMessage

| Field          | Type     | Required | Notes                        |
| -------------- | -------- | -------- | ---------------------------- |
| `lang`         | `string` | yes      | Language tag (BCP-47-like). Server normalizes request language and may add new translations over time. Clients must not validate as a closed enum. |
| `title_key`    | `string` | yes      | i18n key (`soft_paywall.title`) |
| `body_key`     | `string` | yes      | i18n key (`soft_paywall.body`) |
| `cta_key`      | `string` | yes      | i18n key (`soft_paywall.cta`) |
| `default_title`| `string` | yes      | Localized fallback title     |
| `default_body` | `string` | yes      | Localized fallback body, wellness phrasing |
| `default_cta`  | `string` | yes      | Localized fallback CTA       |

### Schema: SoftPaywallAvailability

| Field           | Type             | Required | Notes                              |
| --------------- | ---------------- | -------- | ---------------------------------- |
| `pro_available` | `boolean`        | yes      | Currently always `true`            |
| `reason_key`    | `string or null` | no       | Reserved for future gating reasons |

## FREE vs PRO semantics

| Tier | Endpoint                         | default_enabled | When env is unset      |
| ---- | -------------------------------- | --------------- | ---------------------- |
| FREE | `POST /api/v1/bmi/calculate`     | `true`          | Hook shows by default  |
| PRO  | `POST /api/v1/pro/bmi/calculate` | `false`         | Hook hidden by default |

**Important:** The only difference between FREE and PRO is `default_enabled`.
The hook structure is the same.

## Env control: SOFT_PAYWALL_ENABLED

The hook enablement is controlled via env `SOFT_PAYWALL_ENABLED` parsed by `_env_bool()`.

* True values: `"1"`, `"true"`, `"t"`, `"yes"`, `"y"`, `"on"` (**case-insensitive, trimmed**)
* False values: `"0"`, `"false"`, `"f"`, `"no"`, `"n"`, `"off"` (**case-insensitive, trimmed**)
* Unset: fallback to `default_enabled`
* Unknown value: fallback to `default_enabled`

## i18n keys and current text

The hook uses translations from `core/i18n.py` via request language `req.lang`
(normalized with `normalize_lang()`, unknown → `"en"`).

**Client validation rule:** do **not** treat supported languages as a closed enum.
Clients should accept any BCP-47-like language tag (e.g. `en`, `en-US`, `ru-RU`) and rely on server-side normalization/fallback (`unknown → "en"`).
The current set of shipped translations is RU/EN/ES, but this may expand without breaking the contract.

### RU

* title: `Более точная интерпретация`
* body: `BMI не учитывает распределение жира и контекст. Хотите более точную интерпретацию рисков (wellness)?`
* cta: `Открыть PRO`

### EN

* title: `More accurate interpretation`
* body: `BMI doesn't account for fat distribution or context. Want a more accurate wellness interpretation?`
* cta: `See PRO`

### ES

* title: `Interpretación más precisa`
* body: `El IMC no tiene en cuenta la distribución de grasa ni el contexto. ¿Quieres una interpretación más precisa (bienestar)?`
* cta: `Abrir PRO`

> Note: EN CTA is currently `"See PRO"` (not `"Unlock PRO"`). Text change is out of scope for this contract PR.

## Hard invariants (MUST)

1. **Text-only:** no BMI computation, no thresholds, no "risk score".
2. **No `core.bmi.*` imports:** hook must not depend on BMI engine internals.
3. **Thin clients:** Web/iOS use it only for UI rendering and navigation, never for BMI logic.
4. **Disabled state is `null`:** clients must not expect `{enabled:false}`.

## Guarding

A guard test exists to ensure the paywall hook does not include BMI logic and does not import `core.bmi.*`.
This contract assumes that guard remains CI-enforced.

**Guard test:** `tests/test_no_bmi_logic_in_paywall.py`

---

## Related Documentation

- Audit: `docs/audit/PR_B_SOFT_PAYWALL_CONTRACT_AUDIT.md`
- Router helpers: `app/routers/_helpers.py`
- Schemas: `app/schemas/bmi.py` (SoftPaywallHook, SoftPaywallMessage, SoftPaywallAvailability)
- i18n: `core/i18n.py` (TRANSLATIONS dict)
