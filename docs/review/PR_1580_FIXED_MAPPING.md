# PR #1580 Fixed in Commit Mapping

**PR:** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580
**Branch:** `codex/main-payment-auth-isolation-fix`
**Code Fix SHA:** `fce5e048138387b50cda8ee1edb3a2c57c3d05f0`
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

Disposition: FIXED
Commit: fce5e048138387b50cda8ee1edb3a2c57c3d05f0
Evidence: `tests/test_payment_source_contract_api.py` now imports the app-level `get_api_key` once at module load and no longer catches broad `Exception`; `../../.venv/bin/python -m pytest -q tests/test_payment_source_contract_api.py` and the combined api-tiers/payment contract set passed.
Reason: Sourcery review `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#pullrequestreview-4199427355` asked to avoid a broad exception handler and repeated app imports in `_is_app_get_api_key_dependency`.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: f15c56ab6e635b65af179ec1093660d7ff03051a
Evidence: Main CI failure is fixed by the test-isolation commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25116159382/job/73603719884 -> f15c56ab6e635b65af179ec1093660d7ff03051a

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#issuecomment-4346167776
Reason: CodeRabbit reported a temporary rate-limit/retry condition and later current-head status passed as `Review completed`; no code finding was present in the comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#issuecomment-4346167776

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#issuecomment-4346168676
Reason: Sourcery reviewer-guide comment summarized the change and did not identify a code action.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#issuecomment-4346168676

Disposition: FIXED
Commit: see mapping entries below
Evidence: Sourcery review feedback is fixed by the follow-up helper cleanup.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#pullrequestreview-4199427355

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1580#pullrequestreview-4199427355 -> fce5e048138387b50cda8ee1edb3a2c57c3d05f0

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
