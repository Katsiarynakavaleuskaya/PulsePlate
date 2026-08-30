"""Guard the finite set of enumerated direct TestClient constructor spellings.

At invocation time, the guard searches each exact ``BAD_PATTERNS`` substring in
decoded ``tests/**/*.py`` sources remaining after ``ALLOWLIST`` and
``COVERAGE_BOOST_PATTERNS`` exclusions. A passing result proves only zero enumerated
literal hits in that bounded decoded-text universe. It does not prove that all tests
use managed clients and does not resolve aliases, formatting variants, wrappers,
reflection, dynamic lookup, generated code, or runtime mutation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

# Files allowed to create TestClient directly
ALLOWLIST: Final[set[str]] = {
    "tests/conftest.py",  # Defines canonical fixtures
    "tests/_client.py",  # Canonical factory
    "tests/test_legacy_app_diff_coverage.py",  # Legacy suite (intentional)
    "tests/test_no_direct_testclient.py",  # This guard test
}

# Patterns allowed in coverage boost files (tech debt, low priority).
#
# Tech-debt note:
# These files predate `tests._client.open_test_client(...)` and may still construct
# TestClient directly.
# Tracking: docs/tracking/ISSUE-TESTCLIENT-FACTORY-MIGRATION.md • Owner: @Katsiarynakavaleuskaya • Target: 2026-03-31
# Once migrated, remove the relevant patterns from this allowlist.
COVERAGE_BOOST_PATTERNS: Final[tuple[str, ...]] = (
    "test_coverage_97",
    "test_coverage_boost",
    "test_coverage_final",  # coverage final push files
    "test_vip_coverage",
    "test_app_coverage",
    "test_premium_targets",
    "test_plate_targets",
    "test_plate_alignment",  # plate alignment tests
    "test_vip_simple",
    "test_vip_integration",
    "test_vip_production",
    "test_app_middleware_coverage",
    "test_app_openapi_coverage",
    "test_app_router_inclusion_coverage",
    "test_app_additional_critical_paths",
    "test_app_key_coverage",
    "test_app_vip_comprehensive",
    "test_app_missing_lines_extra",
    "test_app_bmi_bodyfat_coverage",
    "test_app_creation_coverage",  # app creation coverage
    "test_final_coverage",
    "test_final_97_coverage",
    "test_vip_shoplist_preview",
    "test_vip_anonymous_api_key_safety",
    "test_vip_api",  # vip api tests
    "test_update_manager",
    "test_api.py",  # Legacy mega test file
    "disabled_hypothesis",  # Disabled tests
    "edges/",  # Edge case tests
)

# Forbidden patterns (bypass canonical entrypoint)
BAD_PATTERNS: Final[tuple[str, ...]] = (
    "TestClient(app.app)",
    "TestClient(app_module.app)",
    "TestClient(app_mod.app)",
    "TestClient(cast(ASGIApp, app.app))",
    "TestClient(cast(ASGIApp, app_module.app))",
    "TestClient(cast(ASGIApp, app_mod.app))",
    "TestClient(legacy_app.app)",
    "TestClient(cast(ASGIApp, legacy_app.app))",
    "TestClient(fastapi_app)",
    "TestClient(fastapi_app, headers=self.headers)",
    "TestClient(fastapi_app, headers=self.headers_pro)",
    'TestClient(fastapi_app, headers={"X-API-Key": "invalid_key"})',
)


def test_no_direct_testclient_bypass() -> None:
    """Reject the exact enumerated spellings outside the explicit exclusions.

    Rationale:
    The listed direct TestClient entrypoint forms bypass the canonical managed
    lifecycle owner and can miss bootstrap or cleanup behavior.

    Allowed:
    - conftest.py: defines canonical fixtures
    - _client.py: canonical factory
    - test_legacy_app_diff_coverage.py: legacy suite (intentional)

    Forbidden:
    - Exact BAD_PATTERNS substrings in other scan-time decoded tests/**/*.py files

    Boundary:
    - This substring scan does not resolve aliases, reflection, or runtime mutation.
    """
    repo = Path(__file__).resolve().parents[1]
    tests_dir = repo / "tests"
    bad_hits: list[str] = []

    for path in tests_dir.rglob("*.py"):
        rel = str(path.relative_to(repo))
        if rel in ALLOWLIST:
            continue

        # Skip coverage boost files (tech debt, not critical for PR)
        if any(pattern in rel for pattern in COVERAGE_BOOST_PATTERNS):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in BAD_PATTERNS:
            if pattern in text:
                bad_hits.append(f"{rel}: contains '{pattern}'")

    assert not bad_hits, (
        "Enumerated textual TestClient constructor forms were found in scanned "
        "non-excluded test files.\n"
        "Use: tests._client.open_test_client(...) or canonical conftest fixtures.\n"
        "Scope: exact BAD_PATTERNS substring matches after ALLOWLIST and "
        "COVERAGE_BOOST_PATTERNS exclusions.\n"
        "Violations:\n" + "\n".join(bad_hits)
    )
