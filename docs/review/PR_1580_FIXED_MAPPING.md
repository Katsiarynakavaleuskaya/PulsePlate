# PR #1580 Fixed in Commit Mapping

**PR:** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580
**Branch:** `codex/main-payment-auth-isolation-fix`
**Head SHA:** `f15c56ab6e635b65af179ec1093660d7ff03051a`
**Base:** `main`
**Coordinator Packet:** `147c95aed252`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Disposition: FIXED
Commit: f15c56ab6e635b65af179ec1093660d7ff03051a
Evidence: `tests/test_payment_source_contract_api.py` now removes stale/reloaded app-level `get_api_key` dependency overrides before the manual RU/BY fail-closed transport-auth assertion; `../../.venv/bin/python -m pytest -q tests/test_payment_source_contract_api.py` passed with 12 tests.
Reason: Main CI run `25116159382` failed because `test_manual_intent_rejects_env_configured_pro_key_without_app_validator_override` observed `201 Created` instead of `401`, consistent with leaked app-level API-key test override state.

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#issuecomment-4346167776
Reason: CodeRabbit reported an hourly review rate-limit condition, not a code finding. This remains a merge-readiness follow-up: request/retry CodeRabbit review after the rate-limit window before moving the PR out of draft.

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#issuecomment-4346168676
Reason: Sourcery posted a reviewer guide summarizing the single-file test-isolation change and did not identify a code action in that comment.

## Fixed in Commit Mapping

Disposition: FIXED / NOT-A-BUG
Commit: f15c56ab6e635b65af179ec1093660d7ff03051a
Evidence: Main CI failure is fixed by the test-isolation commit; CodeRabbit and Sourcery entries are comment-only NOT-A-BUG dispositions documented above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25116159382/job/73603719884 -> f15c56ab6e635b65af179ec1093660d7ff03051a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#issuecomment-4346167776
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#issuecomment-4346168676

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path tests/test_payment_source_contract_api.py --path app/routers/billing.py --path app/middleware/api_tiers.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `../../.venv/bin/python -m pytest -q tests/test_payment_source_contract_api.py` - PASS (`12 passed`)
- `../../.venv/bin/python -m pytest -q tests/test_ios_receipt_verification_api.py::test_get_app_get_api_key_imports_and_caches_validator tests/test_ios_receipt_verification_api.py::test_require_billing_transport_key_returns_normalized_key tests/test_payment_source_contract_api.py::test_manual_intent_rejects_env_configured_pro_key_without_app_validator_override` - PASS (`3 passed`)
- `../../.venv/bin/python -m pytest -q tests/test_api_tiers.py tests/test_api_tiers_db_lookup.py tests/test_payment_source_contract_api.py` - PASS
- `git diff --check` - PASS
- `pre-commit run --all-files` - PASS
- Commit hooks on `fix(payments): isolate auth override tests` - PASS
- Pre-push hooks on `codex/main-payment-auth-isolation-fix` - PASS

## Merge Readiness

Status: Draft, not merge-ready.

- Current-head PR CI is still in progress.
- CodeRabbit review was rate-limited and must be retried before merge-readiness.
- Full local `make verify` is intentionally deferred per operator plan for this narrow main-CI stabilization lane; GitHub current-head CI is the heavy signal.
