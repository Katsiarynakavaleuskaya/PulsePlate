from __future__ import annotations

from pathlib import Path

import pytest

import core.recipe_synth as recipe_synth


def test_recipe_template_validator_rejects_empty_item() -> None:
    with pytest.raises(ValueError):
        recipe_synth.RecipeTemplateModel(
            template_id="test",
            name="Test",
            cuisine_type="test",
            base_ingredients=[""],
            cooking_methods=["stir"],
            typical_prep_time=10,
            typical_cook_time=10,
            difficulty="easy",
            instruction_template="Do things",
            nutrition_profile={"calories": 100.0},
        )


def test_default_template_validation_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original_validate = recipe_synth.RecipeTemplateModel.model_validate.__func__  # type: ignore[attr-defined]

    def fake_validate(cls, data, *args, **kwargs):
        if data["template_id"] == "stir_fry":
            raise ValueError("invalid template")
        return original_validate(cls, data, *args, **kwargs)

    monkeypatch.setattr(
        recipe_synth.RecipeTemplateModel,
        "model_validate",
        classmethod(fake_validate),
    )

    with pytest.raises(ValueError):
        recipe_synth.RecipeSynthesizer(templates_dir=tmp_path / "missing")


def test_get_recipe_synthesizer_conflicting_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    recipe_synth.reset_recipe_synthesizer()
    first_dir = tmp_path / "one"
    second_dir = tmp_path / "two"
    first_dir.mkdir()
    second_dir.mkdir()
    recipe_synth.get_recipe_synthesizer(templates_dir=str(first_dir))
    with pytest.raises(ValueError):
        recipe_synth.get_recipe_synthesizer(templates_dir=str(second_dir))
    recipe_synth.reset_recipe_synthesizer()


def test_reset_recipe_synthesizer_clears_singleton(tmp_path: Path) -> None:
    recipe_synth.reset_recipe_synthesizer()
    recipe_synth.get_recipe_synthesizer(templates_dir=str(tmp_path / "dir"))
    recipe_synth.reset_recipe_synthesizer()
    assert recipe_synth._recipe_synthesizer is None
