import types
import sys

import pytest

from core import utils


def test_resolve_module_candidate_non_string_returns_candidate() -> None:
    class Some:
        pass

    obj = Some()
    assert utils._resolve_module_candidate(obj) is obj


def test_resolve_attr_prefers_candidate_over_default(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_mod = types.ModuleType("_app_top_module")
    fake_mod.target_value = 123
    sys.modules["_app_top_module"] = fake_mod
    try:
        result = utils.resolve_attr("target_value", local_default=0, candidates=["_app_top_module"])
        assert result == 123
    finally:
        sys.modules.pop("_app_top_module", None)


def test_resolve_attr_falls_back_to_default_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    result = utils.resolve_attr(
        "not_existing", local_default="fallback", candidates=[None, "nope.module"]
    )
    assert result == "fallback"
