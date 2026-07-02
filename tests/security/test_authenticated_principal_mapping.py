from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.middleware.api_tiers import (
    derive_subject_id_from_api_key,
    get_current_user,
    get_pro_subject_id,
    require_pro_tier,
)
from app.routers.api_key import validate_app_api_key
from app.routers.billing import _get_effective_manual_billing_key_validator
from app.services import payments_activation
from tests.security._api_authz_contracts import (
    API_AUTHZ_CONTRACTS,
    CONTRACT_BY_KEY,
    AuthClass,
    OwnershipPolicy,
    PrincipalSource,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PRINCIPAL_DOC = REPO_ROOT / "docs/security/AUTHENTICATED_PRINCIPAL_MAPPING.md"
PREMORTEM_DOC = REPO_ROOT / "docs/review/PR_AUTH_PRINCIPAL_MAPPING_PREMORTEM.md"


def test_api_key_subject_derivation_contract_is_stable_bigint_safe() -> None:
    first = derive_subject_id_from_api_key("principal-contract-key-a")
    second = derive_subject_id_from_api_key("principal-contract-key-b")

    assert first == derive_subject_id_from_api_key("principal-contract-key-a")
    assert first != second
    assert 0 < first <= 0x7FFF_FFFF_FFFF_FFFF
    assert 0 < second <= 0x7FFF_FFFF_FFFF_FFFF


def test_current_user_and_billing_issuer_share_subject_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_key = " principal-contract-pro-key "
    normalized_key = raw_key.strip()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")
    monkeypatch.setenv("PRO_API_KEYS", normalized_key)
    monkeypatch.delenv("VIP_API_KEYS", raising=False)
    monkeypatch.delenv("ALLOW_ANONYMOUS_API_KEYS", raising=False)

    validated_key = require_pro_tier(x_api_key=raw_key)
    current_user = asyncio.run(get_current_user(api_key=validated_key))
    subject_id = derive_subject_id_from_api_key(normalized_key)
    issuer = payments_activation.issuer_from_api_key(raw_key)

    assert validated_key == normalized_key
    assert current_user.user_id == subject_id
    assert current_user.api_key == normalized_key
    assert asyncio.run(get_pro_subject_id(current_user=current_user)) == subject_id
    assert issuer == f"subject:{subject_id}"
    assert payments_activation._resolve_user_id(user_id=None, issuer=issuer) == subject_id
    with pytest.raises(ValueError, match="issuer is invalid"):
        payments_activation._resolve_user_id(user_id=None, issuer="manual:issuer")


def test_authz_contract_principal_source_policy_pairs_are_consistent() -> None:
    expected_pairs = {
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT: {OwnershipPolicy.AUTHENTICATED_SUBJECT},
        PrincipalSource.BILLING_ISSUER: {OwnershipPolicy.ISSUER_SCOPED},
        PrincipalSource.CATALOG_RESOURCE: {OwnershipPolicy.CATALOG_RESOURCE},
        PrincipalSource.INTERNAL_OPTIONAL: {OwnershipPolicy.INTERNAL_OPTIONAL},
        PrincipalSource.LEGACY_HIDDEN: {
            OwnershipPolicy.LEGACY_COMPATIBILITY,
            OwnershipPolicy.LEGACY_HIDDEN,
        },
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT: {OwnershipPolicy.LEGACY_COMPATIBILITY},
        PrincipalSource.OPERATOR_CREDENTIAL: {OwnershipPolicy.OPERATOR_GLOBAL},
    }

    mismatches = [
        f"{contract.method} {contract.path}: "
        f"{contract.principal_source.value} -> {contract.ownership_policy.value}"
        for contract in API_AUTHZ_CONTRACTS
        if contract.principal_source in expected_pairs
        and contract.ownership_policy not in expected_pairs[contract.principal_source]
    ]

    assert not mismatches, "Principal source / ownership policy drift:\n" + "\n".join(mismatches)


def test_bayes_adherence_contract_stays_auth_derived_subject() -> None:
    for key in (
        ("POST", "/api/v1/bayes/adherence/event"),
        ("GET", "/api/v1/bayes/adherence/risk"),
    ):
        contract = CONTRACT_BY_KEY[key]
        assert contract.auth_class is AuthClass.PRO_TIER
        assert contract.principal_source is PrincipalSource.CREDENTIAL_DERIVED_SUBJECT
        assert contract.ownership_policy is OwnershipPolicy.AUTHENTICATED_SUBJECT


def test_manual_billing_contract_is_issuer_scoped_not_entitlement_subject() -> None:
    for key in (
        ("POST", "/api/v1/billing/apple/verify-receipt"),
        ("POST", "/api/v1/pro/payments/ru-by/manual-intent"),
        ("POST", "/api/v1/pro/payments/ru-by/reconcile"),
        ("GET", "/api/v1/pro/payments/ru-by/reconcile/{intent_id}"),
    ):
        contract = CONTRACT_BY_KEY[key]
        assert contract.principal_source is PrincipalSource.BILLING_ISSUER
        assert contract.ownership_policy is OwnershipPolicy.ISSUER_SCOPED
        assert contract.principal_source is not PrincipalSource.CREDENTIAL_DERIVED_SUBJECT


def test_manual_billing_validator_uses_app_key_not_tier_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("API_KEY", "manual-transport-key")
    monkeypatch.setenv("PRO_API_KEYS", "manual-pro-tier-key")
    monkeypatch.setenv("VIP_API_KEYS", "manual-vip-tier-key")

    validator = _get_effective_manual_billing_key_validator()

    assert validator is validate_app_api_key
    assert validator("manual-transport-key") == "manual-transport-key"
    for tier_key in ("manual-pro-tier-key", "manual-vip-tier-key"):
        with pytest.raises(HTTPException) as exc_info:
            validator(tier_key)
        assert exc_info.value.status_code == 403


def test_legacy_alias_contract_is_not_weaker_than_canonical_paid_route() -> None:
    canonical = CONTRACT_BY_KEY[("POST", "/api/v1/pro/meal/weekly")]
    alias = CONTRACT_BY_KEY[("POST", "/api/v1/premium/plan/week-flexible")]

    assert canonical.auth_class is AuthClass.PRO_TIER
    assert alias.auth_class is AuthClass.LEGACY_PRO_TIER
    assert alias.minimum_tier is canonical.minimum_tier
    assert alias.principal_source is canonical.principal_source
    assert alias.ownership_policy is canonical.ownership_policy


def test_authenticated_principal_mapping_doc_records_scope_boundaries() -> None:
    text = PRINCIPAL_DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    required_terms = (
        "derive_subject_id_from_api_key",
        "CurrentUser",
        "get_current_user",
        "TierAuthContext",
        "issuer_from_api_key",
        "PrincipalSource",
        "OwnershipPolicy",
        "BILLING_ISSUER",
        "ISSUER_SCOPED",
        "ledger-p1-first-class-auth-principal-mapping",
    )
    for term in required_terms:
        assert term in text
    assert "not a database `users.id`" in normalized
    assert "not a human-authenticated account" in normalized


def test_docs_do_not_claim_runtime_alerting_or_full_bola_closure() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in (PRINCIPAL_DOC, PREMORTEM_DOC)
    ).lower()
    normalized = " ".join(combined.split())

    assert "this pr does not emit" in normalized
    assert "future observability contract only" in normalized
    assert "does not implement runtime alerting" in normalized
    assert "not complete full bola" in normalized
    forbidden_claims = (
        "runtime alerting is implemented",
        "runtime alerts are live",
        "production telemetry is implemented",
        "production emits auth_principal_mismatch",
        "first-class user authentication is implemented",
        "first-class user auth is implemented",
        "bola is complete",
        "bola fully addressed",
        "full bola completion",
        "full bola closure",
    )
    for claim in forbidden_claims:
        assert claim not in normalized
