from __future__ import annotations

import re
from pathlib import Path

CONTRACT_TEXT = Path("tests/security/_api_authz_contracts.py").read_text(encoding="utf-8")


def _has_contract(path: str) -> bool:
    return bool(
        re.search(
            rf'_contract\(\s*"POST",\s*"{re.escape(path)}",\s*'
            r"AuthClass\.NON_PRODUCTION_TEST_GUARD,\s*"
            r"MinimumTier\.NONE,\s*"
            r"PrincipalSource\.INTERNAL_OPTIONAL,\s*"
            r"OwnershipPolicy\.INTERNAL_OPTIONAL,\s*"
            r"ApiExposure\.HIDDEN_RUNTIME,\s*\)",
            CONTRACT_TEXT,
        )
    )


def test_non_production_test_guard_classifies_hidden_mutating_test_routes() -> None:
    assert "from app.routers.test import _ensure_non_production" in CONTRACT_TEXT
    assert 'NON_PRODUCTION_TEST_GUARD = "non_production_test_guard"' in CONTRACT_TEXT
    assert _has_contract("/api/v1/test/rate-limit")
    assert _has_contract("/api/v1/test/echo")
    assert '"/api/v1/test/health"' not in CONTRACT_TEXT


def test_non_production_test_guard_maps_to_route_dependency() -> None:
    assert re.search(
        r"AuthClass\.NON_PRODUCTION_TEST_GUARD:\s*_ensure_non_production",
        CONTRACT_TEXT,
    )
