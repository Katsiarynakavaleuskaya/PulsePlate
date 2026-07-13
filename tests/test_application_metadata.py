from __future__ import annotations

from typing import cast

import pytest

import app.application_metadata as metadata_module
from app.application_metadata import build_application_metadata

EXPECTED_BASE_DESCRIPTION = """
## PulsePlate - Nutrition & Meal Planning API

**Mobile-first API** for iOS and web applications with tiered subscription access.

### Subscription Tiers

- **FREE**: BMI calculations, food/recipe search, user management
- **PRO**: Advanced meal planning, WHO-based nutrition targets, macro tracking
- **VIP**: Micronutrient goals, AI recipe synthesis, auto-repair, shopping lists

### Authentication

Premium endpoints require API key in `X-API-Key` header:
- PRO tier: Use API key with PRO access level
- VIP tier: Use API key with VIP access level
"""

EXPECTED_DEVELOPMENT_DESCRIPTION = """
### Test API Keys (Development Only)

- PRO: `YOUR_PRO_TEST_KEY`
- VIP: `YOUR_VIP_TEST_KEY`

**Note**: Replace with actual test keys from your environment variables or Config.plist.
**Production**: Test keys are disabled in production environments.
"""

EXPECTED_DOCUMENTATION_DESCRIPTION = """
### Documentation

- Mobile API Migration Guide: `docs/MOBILE_API_MIGRATION_GUIDE.md`
- iOS Integration: `docs/IOS_API_INTEGRATION.md`
"""

EXPECTED_TAGS = [
    {"name": "health", "description": "Health check and system status endpoints"},
    {"name": "bmi", "description": "BMI calculation endpoints (FREE tier)"},
    {
        "name": "foods",
        "description": "Food database search and retrieval (FREE tier)",
    },
    {
        "name": "recipes",
        "description": "Recipe database search and preview (FREE tier)",
    },
    {"name": "users", "description": "User management endpoints (FREE tier)"},
    {
        "name": "pro",
        "description": (
            "PRO tier features - weekly meal planning, nutrition targets. "
            "**Requires PRO API key**."
        ),
    },
    {
        "name": "premium",
        "description": (
            "[DEPRECATED] PRO tier features - use /api/v1/pro/* instead. "
            "**Requires PRO API key**."
        ),
    },
    {
        "name": "vip",
        "description": (
            "VIP tier features - micronutrients, auto-repair, recipe synthesis, "
            "shopping lists. **Requires VIP API key**."
        ),
    },
    {
        "name": "business",
        "description": "Business analytics and Bayesian analysis (Internal use)",
    },
    {
        "name": "export",
        "description": "Export endpoints for meal plans and shopping lists",
    },
]
EXPECTED_TAG_NAMES = [tag["name"] for tag in EXPECTED_TAGS]


@pytest.mark.parametrize(
    "runtime_env",
    ["", "local", "dev", "development", "test", "testing", " DEV "],
)
def test_application_metadata_preserves_development_description(runtime_env: str) -> None:
    metadata = build_application_metadata(runtime_env=runtime_env)

    assert "### Test API Keys (Development Only)" in metadata.description
    assert "YOUR_PRO_TEST_KEY" in metadata.description
    assert "YOUR_VIP_TEST_KEY" in metadata.description


@pytest.mark.parametrize("runtime_env", ["ci", "staging", "prod", "production"])
def test_application_metadata_omits_development_description(runtime_env: str) -> None:
    metadata = build_application_metadata(runtime_env=runtime_env)

    assert "### Test API Keys (Development Only)" not in metadata.description
    assert "YOUR_PRO_TEST_KEY" not in metadata.description
    assert "YOUR_VIP_TEST_KEY" not in metadata.description


def test_application_metadata_preserves_exact_values_and_tag_order() -> None:
    metadata = build_application_metadata(runtime_env="production")

    assert metadata.title == "PulsePlate"
    assert metadata.version == "0.1.0"
    assert metadata.description == (EXPECTED_BASE_DESCRIPTION + EXPECTED_DOCUMENTATION_DESCRIPTION)
    assert metadata.contact_dict() == {
        "name": "PulsePlate API Support",
        "url": "https://github.com/Katsiarynakavaleuskaya/PulsePlate",
    }
    assert metadata.license_info_dict() == {"name": "MIT"}
    assert metadata.openapi_tags_list() == EXPECTED_TAGS


def test_application_metadata_preserves_exact_development_description() -> None:
    metadata = build_application_metadata(runtime_env="development")

    assert metadata.description == (
        EXPECTED_BASE_DESCRIPTION
        + EXPECTED_DEVELOPMENT_DESCRIPTION
        + EXPECTED_DOCUMENTATION_DESCRIPTION
    )


def test_legacy_metadata_aliases_match_canonical_projection() -> None:
    import legacy_app

    metadata = build_application_metadata(runtime_env=legacy_app._app_env)

    assert legacy_app._api_description == metadata.description
    assert legacy_app.tags_metadata == metadata.openapi_tags_list()


def test_application_metadata_projection_returns_fresh_nested_mutables() -> None:
    metadata = build_application_metadata(runtime_env="production")
    first = metadata.to_fastapi_kwargs()
    second = metadata.to_fastapi_kwargs()

    first_contact = cast(dict[str, str], first["contact"])
    first_license = cast(dict[str, str], first["license_info"])
    first_tags = cast(list[dict[str, str]], first["openapi_tags"])
    second_contact = cast(dict[str, str], second["contact"])
    second_license = cast(dict[str, str], second["license_info"])
    second_tags = cast(list[dict[str, str]], second["openapi_tags"])

    first_contact["name"] = "changed"
    first_license["name"] = "changed"
    first_tags[0]["name"] = "changed"
    first_tags.append({"name": "extra", "description": "extra"})

    assert second_contact["name"] == "PulsePlate API Support"
    assert second_license["name"] == "MIT"
    assert [tag["name"] for tag in second_tags] == EXPECTED_TAG_NAMES
    assert metadata.tags[0].name == "health"


def test_application_metadata_resolves_environment_only_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _runtime_env() -> str:
        calls.append("called")
        return "production"

    monkeypatch.setattr(metadata_module, "get_runtime_env_name", _runtime_env)

    assert "Test API Keys" not in build_application_metadata().description
    assert calls == ["called"]
    assert "Test API Keys" in build_application_metadata(runtime_env="").description
    assert calls == ["called"]


def test_application_metadata_never_interpolates_environment_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "sentinel-real-key-must-not-leak"
    monkeypatch.setenv("API_KEY", sentinel)
    monkeypatch.setenv("VIP_MODULE_KEY", sentinel)

    metadata = build_application_metadata(runtime_env="development")

    assert sentinel not in metadata.description
    assert sentinel not in repr(metadata)
