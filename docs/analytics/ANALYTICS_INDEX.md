# Analytics Index (Catalog)

**Purpose:** A vendor-agnostic catalog of what we measure and where it lives.

**Status:** Canonical (docs-only). Runtime telemetry is out of scope here.

---

## Tracked Metrics

| Metric | Definition (short) | Owner | Source of truth | Update frequency |
|--------|---------------------|-------|-----------------|------------------|
| Activation (first_success) | % users who complete the first core success action | TBD | `METRICS_CATALOG.md` | TBD |
| Free → Pro conversion | % FREE users upgrading to PRO within a defined window | TBD | `METRICS_CATALOG.md` | TBD |
| Retention D7 | % users active on day 7 after first success | TBD | `METRICS_CATALOG.md` | TBD |

Notes:
- “Source of truth” for metric semantics is `METRICS_CATALOG.md` (not dashboards).

---

## Data Sources

| Source | Type | Schema/contract location | Access control | Notes |
|--------|------|---------------------------|----------------|-------|
| Primary DB | transactional | `DATA_CATALOG.md` | TBD | Vendor-agnostic |
| Client events | telemetry/events | `DATA_CATALOG.md` | TBD | Requires privacy decision before collection |
| Billing | payments/subscriptions | `DATA_CATALOG.md` | TBD | Vendor-agnostic |

---

## Dashboards (optional)

| Dashboard | Tool | Owner | Update frequency | Notes |
|----------|------|-------|------------------|------|
| Product health | TBD | TBD | TBD | Vendor-agnostic placeholder |
