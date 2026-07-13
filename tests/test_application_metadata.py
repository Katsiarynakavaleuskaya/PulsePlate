from __future__ import annotations

from typing import cast

import pytest

import app.application_metadata as metadata_module
from app.application_metadata import build_application_metadata

EXPECTED_TAG_NAMES = [
    "health",
    "bmi",
    "foods",
    "recipes",
    "users",
    "pro",
    "premium",
    "vip",
    "business",
    "export",
]


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
    assert metadata.contact_dict() == {
        "name": "PulsePlate API Support",
        "url": "https://github.com/Katsiarynakavaleuskaya/PulsePlate",
    }
    assert metadata.license_info_dict() == {"name": "MIT"}
    assert [tag.name for tag in metadata.tags] == EXPECTED_TAG_NAMES
    assert "Nutrition & Meal Planning API" in metadata.description
    assert "docs/MOBILE_API_MIGRATION_GUIDE.md" in metadata.description


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
