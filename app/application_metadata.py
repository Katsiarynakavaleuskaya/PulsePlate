"""Canonical application metadata for the PulsePlate FastAPI instance."""

from __future__ import annotations

from dataclasses import dataclass

from settings import get_runtime_env_name

_DEVELOPMENT_ENVIRONMENTS = frozenset({"", "local", "dev", "development", "test", "testing"})

_BASE_DESCRIPTION = """
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

_DEVELOPMENT_DESCRIPTION = """
### Test API Keys (Development Only)

- PRO: `YOUR_PRO_TEST_KEY`
- VIP: `YOUR_VIP_TEST_KEY`

**Note**: Replace with actual test keys from your environment variables or Config.plist.
**Production**: Test keys are disabled in production environments.
"""

_DOCUMENTATION_DESCRIPTION = """
### Documentation

- Mobile API Migration Guide: `docs/MOBILE_API_MIGRATION_GUIDE.md`
- iOS Integration: `docs/IOS_API_INTEGRATION.md`
"""


@dataclass(frozen=True, slots=True)
class OpenAPITagMetadata:
    """Immutable source record for one ordered OpenAPI tag."""

    name: str
    description: str


@dataclass(frozen=True, slots=True)
class ApplicationMetadata:
    """Immutable source values used to construct a FastAPI application."""

    title: str
    version: str
    description: str
    contact_name: str
    contact_url: str
    license_name: str
    tags: tuple[OpenAPITagMetadata, ...]

    def contact_dict(self) -> dict[str, str]:
        return {"name": self.contact_name, "url": self.contact_url}

    def license_info_dict(self) -> dict[str, str]:
        return {"name": self.license_name}

    def openapi_tags_list(self) -> list[dict[str, str]]:
        return [{"name": tag.name, "description": tag.description} for tag in self.tags]

    def to_fastapi_kwargs(self) -> dict[str, object]:
        """Return fresh mutable constructor inputs for an independent app instance."""

        return {
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "contact": self.contact_dict(),
            "license_info": self.license_info_dict(),
            "openapi_tags": self.openapi_tags_list(),
        }


_ORDERED_OPENAPI_TAGS = (
    OpenAPITagMetadata("health", "Health check and system status endpoints"),
    OpenAPITagMetadata("bmi", "BMI calculation endpoints (FREE tier)"),
    OpenAPITagMetadata("foods", "Food database search and retrieval (FREE tier)"),
    OpenAPITagMetadata("recipes", "Recipe database search and preview (FREE tier)"),
    OpenAPITagMetadata("users", "User management endpoints (FREE tier)"),
    OpenAPITagMetadata(
        "pro",
        "PRO tier features - weekly meal planning, nutrition targets. " "**Requires PRO API key**.",
    ),
    OpenAPITagMetadata(
        "premium",
        "[DEPRECATED] PRO tier features - use /api/v1/pro/* instead. " "**Requires PRO API key**.",
    ),
    OpenAPITagMetadata(
        "vip",
        "VIP tier features - micronutrients, auto-repair, recipe synthesis, "
        "shopping lists. **Requires VIP API key**.",
    ),
    OpenAPITagMetadata("business", "Business analytics and Bayesian analysis (Internal use)"),
    OpenAPITagMetadata("export", "Export endpoints for meal plans and shopping lists"),
)


def build_application_metadata(*, runtime_env: str | None = None) -> ApplicationMetadata:
    """Build the exact legacy-compatible metadata for the resolved environment."""

    resolved_env = get_runtime_env_name() if runtime_env is None else runtime_env
    normalized_env = resolved_env.strip().lower()
    description = _BASE_DESCRIPTION
    if normalized_env in _DEVELOPMENT_ENVIRONMENTS:
        description += _DEVELOPMENT_DESCRIPTION
    description += _DOCUMENTATION_DESCRIPTION

    return ApplicationMetadata(
        title="PulsePlate",
        version="0.1.0",
        description=description,
        contact_name="PulsePlate API Support",
        contact_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate",
        license_name="MIT",
        tags=_ORDERED_OPENAPI_TAGS,
    )
