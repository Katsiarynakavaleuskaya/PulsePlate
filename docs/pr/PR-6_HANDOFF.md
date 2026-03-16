# PR-6 HANDOFF — iOS Keychain Conformance Follow-up

**Topic:** iOS Keychain Conformance (mobile-secret storage)
**Date:** 2026-03-16
**Status:** Ready for implementation

---

## Canonical numbering

PR-6 = iOS Keychain Conformance Follow-up (TOP20/mobile-secret numbering regime).
Cookie/export hardening lives in separate security PRs: `PR-TBD-SESSION-COOKIE-HARDENING-W1`, `PR-TBD-EXPORT-SIGNING-HARDENING`.

---

## Backlog

- [P1: Mobile secret storage conformance](docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mobile-secret-conformance)

---

## Scope

- Keychain-only iOS secret-storage conformance
- default local and CI iOS coverage for roundtrip / ignore-env behavior
- current-state iOS setup docs cleanup
- stronger regression guards for insecure secret paths

---

## Non-goals

- Android Keystore
- StoreKit / billing redesign
- backend billing route changes
- cookie/export hardening
- unrelated iOS refactors

---

## Files

- `ios/PulsePlateTests/Services/ProKeyProviderTests.swift`
- `ios/PulsePlateTests/Services/KeychainStoreTests.swift`
- `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift`
- `ios/SHOPPING_LIST_SETUP.md`
- `docs/IOS_API_INTEGRATION.md`
- `ios/AGENTS.md`
- `ios/SANITY_CHECK_RESULTS.md`
- `docs/pr/PR-6_DESCRIPTION.md`
- `docs/pr/PR-6_HANDOFF.md`

---

## DoD

- runtime secret paths remain verified as Keychain-only
- default local + CI lanes explicitly encode roundtrip / ignore-env coverage
- current-state docs no longer advertise `PRO_API_KEY` or placeholder fallback as runtime truth
- guard layer blocks regressions to insecure storage or noncanonical secret-provider paths

---

## Merge gates (required)

- [x] `python3 scripts/orchestration/check_preflight.py` — PASS
- [x] Coordinator-first task analysis completed
- [x] `pre-commit run --all-files` — PASS
- [x] `make verify` — PASS

---

## Tests

- `make ios-test`
- Targeted xcodebuild subset if quick rerun needed:
  - `ThinClientGuardsTests`
  - `ProKeyProviderTests`
  - `KeychainStoreTests`
- `pre-commit run --all-files`
- `make verify`

---

## Security invariant

Runtime iOS secrets: not sourced from env vars, not persisted via `UserDefaults` / `@AppStorage`, not hardcoded via placeholder fallback, not reintroduced through ad-hoc raw Security/Keychain seams outside canonical storage/provider paths.
