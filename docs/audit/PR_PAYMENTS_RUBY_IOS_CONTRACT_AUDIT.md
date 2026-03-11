# PR Audit: Payments RU/BY + iOS Baseline Contract (Docs-Only)

- Classification: `contract: safe` (documentation-only, no runtime behavior changes)
- Scope: canonical payment source model, additive API contract design, iOS thin-client transport policy sync, backlog SoT alignment.
- Date: 2026-03-05

## Evidence Anchors

1. Canonical source enum and baseline API contract are defined in:
   - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:8`
   - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:21`
   - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:32`
2. Reconciliation lifecycle, idempotency, and error envelope are defined in:
   - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:63`
   - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:77`
   - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:86`
3. Canonical API map reflects additive billing surface and compatibility policy:
   - `docs/contracts/API_CANONICAL_MAP.md:33`
   - `docs/contracts/API_CANONICAL_MAP.md:45`
   - `docs/contracts/API_CANONICAL_MAP.md:52`
4. iOS thin-client transport constraints for payment flows are documented:
   - `docs/IOS_API_INTEGRATION.md:120`
   - `docs/IOS_API_INTEGRATION.md:124`
5. Backlog SoT tracks the payment wave as active P0 with explicit DoD/test plan:
   - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`
   - `docs/roadmap/BACKLOG_LEDGER.md:49`
6. Temporary-seam governance is explicit via ADR + exit criteria:
   - `docs/architecture/ADR_PAYMENTS_RU_BY_IOS_BASELINE_2026-03-05.md:1`
   - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:125`

## Risk Notes

1. Fraud risk on manual rails (`erip_qr`, `swift_manual`) requires explicit reconciliation and audit trace.
2. Replay risk on webhook/event processing requires signature validation and strict idempotency keys.
3. Reconciliation lag must not silently grant paid entitlements before verification state.
4. iOS digital-goods policy compliance remains a hard gate for App Store path.
5. Data minimization and retention boundaries must remain aligned with existing privacy policies.

## Runtime Follow-Up (Out of Scope for this PR)

Required runtime tests are locked by contract and must be implemented in runtime PR:
- `tests/test_payment_source_contract_api.py`
- `tests/test_subscription_activation_api.py`
- `tests/test_ios_receipt_verification_api.py`
- `tests/test_payment_webhook_signature_api.py`
- `tests/test_payment_reconciliation_api.py`
