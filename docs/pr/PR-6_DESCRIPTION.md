# PR-6: iOS Keychain Conformance Follow-up

## Summary

Tightens the already-merged iOS Keychain-only runtime contract by aligning tests, guards, and current-state docs with repo truth.

This PR does **not** rewrite monetization or billing flows. It encodes and protects the current runtime truth:

- PRO runtime secrets use **Keychain only**
- default local and CI iOS test lanes explicitly cover roundtrip / ignore-env behavior
- current-state setup docs no longer present `PRO_API_KEY` or placeholder fallback as runtime truth
- guard tests block regressions to insecure storage or noncanonical provider seams

## Scope

- Keychain-only iOS secret-storage conformance
- default local and CI iOS coverage for roundtrip / ignore-env behavior
- current-state iOS setup docs cleanup
- stronger regression guards for insecure secret paths

## Non-goals

- Android Keystore
- StoreKit / billing redesign
- backend billing route changes
- cookie/export hardening
- unrelated iOS refactors

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

## Tests

- `make ios-test`
- Targeted xcodebuild subset if quick rerun is needed:
  - `ThinClientGuardsTests`
  - `ProKeyProviderTests`
  - `KeychainStoreTests`
- `pre-commit run --all-files`
- `make verify`

## DoD

- runtime secret paths remain verified as Keychain-only
- default local + CI lanes explicitly encode roundtrip / ignore-env coverage
- current-state docs no longer advertise `PRO_API_KEY` or placeholder fallback as runtime truth
- guard layer blocks regressions to insecure storage or noncanonical secret-provider paths

## Security Notes

- This PR strengthens **secret-source centralization**, not just test coverage.
- Central invariant:
  - runtime iOS secrets are not sourced from env vars,
  - not persisted via `UserDefaults` / `@AppStorage`,
  - not hardcoded via placeholder fallback,
  - not reintroduced through ad-hoc raw Security/Keychain seams outside canonical storage/provider paths.

## Marketing & GTM

- This PR does not ship a new user-facing feature; it improves trust and launch readiness.
- Product-facing value:
  - stronger mobile secret-storage correctness,
  - lower QA drift risk,
  - clearer developer onboarding,
  - safer future monetization rollout.

## Backlog

- [P1: Mobile secret storage conformance](docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mobile-secret-conformance) (iOS Keychain now, Android Keystore deferred)

## Merge gates (required)

- [x] `python3 scripts/orchestration/check_preflight.py` — PASS
- [x] Coordinator-first task analysis completed
- [x] `pre-commit run --all-files` — PASS
- [x] `make verify` — PASS

## Decision Log

- This PR follows the TOP20/mobile-secret numbering regime; the later cookie/export PR-6 packet is superseded for this branch.
- `PR-6` is the current mobile-secret conformance follow-up, not the old cookie/export packet.
- Android remains deferred.
- Runtime truth is already on `main`; this PR encodes and protects that truth.
- New guards are limited to runtime app sources to preserve stability and avoid noisy failures.
- `ios/AGENTS.md` receives minimal snippet sync only.
- `ios/SANITY_CHECK_RESULTS.md` remains historical evidence, not an operational setup source.

## PR body

### Summary

Tightens the already-merged iOS Keychain-only runtime contract by aligning tests, guards, and current-state docs with repo truth.

No monetization rewrite and no backend/web security scope are included in this PR.

### Scope

- Keychain-only iOS secret-storage conformance
- default local and CI iOS coverage for roundtrip / ignore-env behavior
- current-state iOS setup docs cleanup
- stronger regression guards for insecure secret paths

### Non-goals

- Android Keystore
- StoreKit / billing redesign
- backend billing route changes
- cookie/export hardening
- unrelated iOS refactors

### Files

- `ios/PulsePlateTests/Services/ProKeyProviderTests.swift`
- `ios/PulsePlateTests/Services/KeychainStoreTests.swift`
- `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift`
- `ios/SHOPPING_LIST_SETUP.md`
- `docs/IOS_API_INTEGRATION.md`
- `ios/AGENTS.md`
- `ios/SANITY_CHECK_RESULTS.md`
- `docs/pr/PR-6_DESCRIPTION.md`
- `docs/pr/PR-6_HANDOFF.md`

### Tests

- `make ios-test`
- targeted xcodebuild subset for quick validation if needed
- `pre-commit run --all-files`
- `make verify`

### Backlog

- [P1: Mobile secret storage conformance](docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mobile-secret-conformance)

### Merge gates (required)

- [x] `python3 scripts/orchestration/check_preflight.py` — PASS
- [x] Coordinator-first task analysis completed
- [x] `pre-commit run --all-files` — PASS
- [x] `make verify` — PASS

### DoD

- runtime secret paths remain verified as Keychain-only
- default local + CI lanes explicitly encode roundtrip / ignore-env coverage
- current-state docs no longer advertise `PRO_API_KEY` or placeholder fallback as runtime truth
- guard layer blocks regressions to insecure storage or noncanonical secret-provider paths
