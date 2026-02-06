# iOS + Web Thin Client Guards (BMI) — Status Audit

**Status:** 🟢 Implemented (guards exist, audits exist)
**Owner:** @katsiaryna_kavaleuskaya
**Last updated:** 6 February 2026

---

## Scope (canonical)

Both iOS and Web clients must be **thin clients**:

- ✅ **No BMI logic** (no thresholds, no inference, no local BMI math).
- ✅ **Contract-driven UI** (render backend fields; localize backend-provided keys).
- ✅ **One HTTP seam** (no dual-path networking; Web: no direct `fetch()` outside canonical client; iOS: no `URLSession` usage outside `ios/PulsePlate/Networking/*`).

---

## Canonical anchors (policy)

- Root policy: `AGENTS.md` (Thin Client Policy + One BMI Engine invariant)
- Web policy: `frontend/AGENTS.md` (Thin HTTP Adapter Policy)
- iOS policy: `ios/AGENTS.md` (Thin Client Policy + guard tests)

---

## What exists today (evidence pointers)

### iOS guard (BMI logic / thresholds)

- Guard test: `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift`
  - Scans `ios/PulsePlate/**` Swift sources (excluding tests/mocks/fixtures).
  - Flags thresholds and inference patterns (`18.5/25/30`, `if bmi...`, `switch bmi...`) and WHtR division heuristics.

Related audit (verified):

- `docs/audit/PR_598_IOS_BMI_THIN_CLIENT_DEDUP_AUDIT.md`

### Web guard (BMI logic + direct fetch)

- Guard test: `frontend/src/api/__tests__/thin-client-guards.test.ts`
  - Scans `frontend/src/{api,pages,components,features,hooks,lib}`.
  - Forbids BMI thresholds/inference + forbids direct `fetch()` outside `frontend/src/api/client.ts`.

Related audits (verified):

- `docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md`
- `docs/audit/PR_587_WEB_THIN_HTTP_ADAPTER_REMEDIATION_AUDIT.md`
- `docs/audit/PR_599_WEB_THIN_CLIENT_ALIGNMENT_AUDIT.md`

---

## Evidence commands (copy/paste)

### iOS

```bash
# Guard exists + is enforced by iOS test suite
rg -n "final class ThinClientGuardsTests" ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift

# Quick policy scan (app sources only)
rg -n "computeBMI\\(|categoryForBMI\\(|riskForBMI\\(|\\b18[.,]5\\b|\\b25\\b|\\b30\\b" ios/PulsePlate
```

### Web

```bash
# Guard exists
rg -n "describe\\('ThinClientGuards'" frontend/src/api/__tests__/thin-client-guards.test.ts

# Direct fetch violations (guarded)
rg -n "fetch\\(" frontend/src
```

---

## Decision

Thin-client policy for BMI is **not “by convention”**:

- iOS has a **guard test** that blocks reintroduction of BMI thresholds/logic.
- Web has a **guard test** that blocks BMI logic and blocks direct `fetch()` outside canonical API client.

No remediation PR is required for “guards existence”; follow-up work belongs only to feature PRs that touch endpoints/contracts.
