"""Unit tests for the canonical core.ai insight runtime facade."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from core.ai.insight_runtime import (
    DirectInsightProviderStub,
    InsightProviderLoadError,
    InsightTransparencyNotice,
    InsightTransparencyUnavailableError,
    load_insight_provider,
    prepare_insight_runtime,
    require_ai_generated_insight_notice,
)


class _FakeProvider:
    name = "fake-provider"


def test_load_insight_provider_uses_lazy_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    """Facade must stay lazy and return the resolved provider instance."""

    monkeypatch.setattr(
        "core.ai.insight_runtime.load_llm_get_provider",
        lambda: (lambda: _FakeProvider()),
        raising=True,
    )

    provider = load_insight_provider()

    assert provider.name == "fake-provider"


def test_load_insight_provider_raises_on_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Import failures must map to the bounded-context provider error."""

    def _raise_import_failure() -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "core.ai.insight_runtime.load_llm_get_provider",
        _raise_import_failure,
        raising=True,
    )

    with pytest.raises(InsightProviderLoadError, match="LLM module is not available"):
        load_insight_provider()


def test_load_insight_provider_raises_when_provider_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing provider must stay a deterministic bounded-context failure."""

    monkeypatch.setattr(
        "core.ai.insight_runtime.load_llm_get_provider",
        lambda: (lambda: None),
        raising=True,
    )

    with pytest.raises(InsightProviderLoadError, match="No LLM provider configured"):
        load_insight_provider()


def test_require_ai_generated_insight_notice_returns_notice() -> None:
    """Valid transparency metadata must become the canonical notice object."""

    notice = require_ai_generated_insight_notice(
        registry_loader=lambda: {
            "ai_generated_insight": {
                "surface_id": "ai_generated_insight",
                "boundary": "Wellness only.",
            }
        }
    )

    assert notice == InsightTransparencyNotice(
        surface_id="ai_generated_insight",
        wellness_boundary="Wellness only.",
    )


@pytest.mark.parametrize(
    "registry_loader",
    [
        lambda: {},
        lambda: {"ai_generated_insight": {"surface_id": None, "boundary": ""}},
    ],
)
def test_require_ai_generated_insight_notice_fails_closed(
    registry_loader,
) -> None:
    """Malformed transparency metadata must fail closed."""

    with pytest.raises(
        InsightTransparencyUnavailableError,
        match="transparency_registry_unavailable",
    ):
        require_ai_generated_insight_notice(registry_loader=registry_loader)


def test_prepare_insight_runtime_uses_direct_stub_for_local_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local-direct routes must not touch provider loading."""

    class _FakeRuntime:
        def preview_route(
            self, *, text: str, lang: str | None, router_enabled: bool, use_rag: bool
        ):
            del text, lang, router_enabled, use_rag
            return SimpleNamespace(
                needs_generation=False, route_type=SimpleNamespace(value="direct")
            )

    monkeypatch.setattr("core.ai.insight_runtime.PhilosophicalRuntime", _FakeRuntime, raising=True)

    prepared = prepare_insight_runtime(
        text="hello",
        use_rag=False,
        philosophy_router_enabled=False,
        philosophy_linguistic_enabled=False,
        provider_loader=lambda: pytest.fail("provider loader must not run"),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
    )

    assert isinstance(prepared.provider, DirectInsightProviderStub)
    assert prepared.transparency_notice.surface_id == "ai_generated_insight"


def test_prepare_insight_runtime_uses_provider_loader_for_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generation routes must resolve provider and keep the preview decision."""

    @dataclass
    class _FakeDecision:
        needs_generation: bool
        route_type: object

    class _FakeRuntime:
        def preview_route(
            self, *, text: str, lang: str | None, router_enabled: bool, use_rag: bool
        ):
            assert text == "hello"
            assert lang is None
            assert router_enabled is True
            assert use_rag is True
            return _FakeDecision(
                needs_generation=True,
                route_type=SimpleNamespace(value="deep_reasoning"),
            )

    provider = _FakeProvider()
    monkeypatch.setattr("core.ai.insight_runtime.PhilosophicalRuntime", _FakeRuntime, raising=True)

    prepared = prepare_insight_runtime(
        text="hello",
        use_rag=True,
        philosophy_router_enabled=True,
        philosophy_linguistic_enabled=False,
        provider_loader=lambda: provider,
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
    )

    assert prepared.provider is provider
    assert prepared.decision.route_type.value == "deep_reasoning"
    assert prepared.transparency_notice.wellness_boundary == "Wellness only."
