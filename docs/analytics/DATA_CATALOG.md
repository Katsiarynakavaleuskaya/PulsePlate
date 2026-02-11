# Data Catalog (Schemas + Semantics)

**Purpose:** Document the meaning of fields and event properties so analyses are consistent and privacy-safe.

**Status:** Canonical (docs-only). Vendor-agnostic.

---

## Data sources (high-level)

| Source | What it contains | Owner | Notes |
|--------|-------------------|-------|------|
| Primary DB | users, subscriptions, core domain entities | TBD | Vendor-agnostic |
| Client events | user actions and UI state transitions | TBD | Requires privacy/retention decisions before collection |

---

## Tables / entities (example templates)

### users

| Field | Type | Meaning | Example | Notes |
|------|------|---------|---------|------|
| user_id | string/uuid | stable user identifier | `...` | Never export raw IDs outside trusted contexts |
| created_at | timestamp | account creation time (UTC) | `...` |  |

### subscriptions

| Field | Type | Meaning | Example | Notes |
|------|------|---------|---------|------|
| user_id | string/uuid | FK to users | `...` |  |
| tier | enum | FREE / PRO / VIP | `PRO` | SoT for tiers is backend policy (`app/middleware/api_tiers.py`) |
| created_at | timestamp | subscription start time (UTC) | `...` |  |

---

## Events (vendor-agnostic)

### event: <event_name>

| Property | Type | Meaning | Example | Notes |
|----------|------|---------|---------|------|
| user_id | string/uuid | stable identifier | `...` | Anonymize in analysis outputs |
| occurred_at | timestamp | event time (UTC) | `...` |  |
