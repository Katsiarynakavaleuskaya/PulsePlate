from __future__ import annotations

from pathlib import Path


def test_nutrition_log_uses_import_safe_orm_helper() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    router = repo_root / "app" / "routers" / "nutrition_log.py"
    content = router.read_text(encoding="utf-8")

    assert "get_nutrition_event_model" in content, (
        "nutrition_log must use app.openapi.orm_imports.get_nutrition_event_model() "
        "instead of inline runtime imports."
    )
    assert "from typing import TYPE_CHECKING" not in content
    assert "if TYPE_CHECKING:" not in content
    assert "from app.models import NutritionEvent as NutritionEventModel" not in content
