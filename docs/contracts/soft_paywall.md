# Soft Paywall Hook Contract (Text-only)

**Status:** Canonical contract (documentation-only)
**Last updated:** 2026-08-29
**Scope:** Backend Free → Pro availability hint plus the current public Web projection. **Text-only. No BMI logic.**

## Purpose

The Soft Paywall Hook is a **UX/marketing signal** attached to BMI results.
It must remain **strictly text-only** and **must not** depend on BMI calculation logic.

The backend payload preserves its existing PRO-oriented compatibility contract. Under the
current public channel posture, however, it is not Web purchase, upgrade, navigation, or
entitlement authority. The Web client uses only `availability.pro_available` to decide whether
to show a fixed information card; it does not render or execute the server-authored commercial
message, target, or next-action metadata.

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
| `target`       | `"pro_paywall"`           | yes      | Fixed compatibility literal; not current public Web action authority |

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

## Current public Web projection

The current public Web surface is free and information-only:

1. `hook != null` and `availability.pro_available == true` may show the bounded information card.
2. Visible EN/RU/ES copy comes from the frontend `appleProduct.*` locale bundle, not from
   `message.default_title`, `message.default_body`, `message.default_cta`, or their key fields.
3. The fixed Web CTA is `Learn about PulsePlate for Apple devices` and navigates only to
   `/marketing`.
4. `target: "pro_paywall"`, `next_best_action`, tier hints, and legacy route metadata are accepted
   as compatibility data but do not select Web copy, destination, telemetry meaning, or behavior.
5. The Web projection has no caller-provided action callback, `/pro` acquisition handoff,
   checkout helper, purchase control, trial/restore action, or entitlement mutation.

The public `/pro` URL remains available separately as an information-only compatibility page.
Backend billing, Apple receipt verification, StoreKit, entitlement truth, API schemas, and other
client channels are unchanged by this Web projection.

A future paid Web projection requires a separate exact human GO plus server-authoritative billing
and entitlement architecture. It must update this contract and the corresponding runtime guard in
its own reviewed carrier.

## Env control: SOFT_PAYWALL_ENABLED

The hook enablement is controlled via env `SOFT_PAYWALL_ENABLED` parsed by `_env_bool()`.

* True values: `"1"`, `"true"`, `"t"`, `"yes"`, `"y"`, `"on"` (**case-insensitive, trimmed**)
* False values: `"0"`, `"false"`, `"f"`, `"no"`, `"n"`, `"off"` (**case-insensitive, trimmed**)
* Unset: fallback to `default_enabled`
* Unknown value: fallback to `default_enabled`

## Backend i18n keys and current payload text

The backend hook uses translations from `core/i18n.py` via request language `req.lang`
(normalized with `normalize_lang()`, unknown → `"en"`).

These fields remain backend compatibility data. They are not the current public Web display copy;
the Web projection is fixed by the `appleProduct.*` bundle described above.

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

> Note: EN backend fallback CTA remains `"See PRO"` (not `"Unlock PRO"`). The current public Web
> projection intentionally does not render it.

## Hard invariants (MUST)

1. **Text-only:** no BMI computation, no thresholds, no "risk score".
2. **No `core.bmi.*` imports:** hook must not depend on BMI engine internals.
3. **Thin clients:** clients never derive BMI or entitlement truth from the hook.
4. **Disabled state is `null`:** clients must not expect `{enabled:false}`.
5. **Current Web authority boundary:** backend message, target, and next-action fields cannot author
   public Web copy, destination, acquisition telemetry, payment, or entitlement behavior.
6. **No permanent prohibition:** future Web monetization remains possible only through a separate
   exact admission and server-authoritative architecture.

## Guarding

A guard test exists to ensure the paywall hook does not include BMI logic and does not import `core.bmi.*`.
This contract assumes that guard remains CI-enforced.

**Guard test:** `tests/test_no_bmi_logic_in_paywall.py`

The current Web projection is additionally enforced by:

- `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx`
- `frontend/src/config/__tests__/webMonetizationPosture.test.ts`

---

## Related Documentation

- Audit: `docs/audit/PR_B_SOFT_PAYWALL_CONTRACT_AUDIT.md`
- Router helpers: `app/routers/_helpers.py`
- Schemas: `app/schemas/bmi.py` (SoftPaywallHook, SoftPaywallMessage, SoftPaywallAvailability)
- i18n: `core/i18n.py` (TRANSLATIONS dict)
- Channel posture: `docs/contracts/PRODUCT_TIER_MAP.md`
