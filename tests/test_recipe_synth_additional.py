"""
Additional tests for core.recipe_synth to cover helper APIs and week synthesis.
"""

from __future__ import annotations

from typing import Dict, List

from core.recipe_synth import (
    RecipeSynthesizer,
    RecipeTemplate,
    get_recipe_synthesizer,
    synthesize_recipe_from_ingredients,
    synthesize_recipes_for_week,
)


def test_recipe_template_to_dict_copy_semantics() -> None:
    t = RecipeTemplate(
        template_id="x",
        name="X",
        cuisine_type="intl",
        base_ingredients=["a"],
        cooking_methods=["b"],
        typical_prep_time=1,
        typical_cook_time=2,
        difficulty="easy",
        instruction_template="Do things.",
        nutrition_profile={"calories": 1.0},
    )
    d = t.to_dict()
    assert isinstance(d, dict) and d["template_id"] == "x"
    # ensure it’s a shallow copy, not a live view
    d["name"] = "mutated"
    assert t.name == "X"


def test_wrapper_get_and_synthesize_single() -> None:
    synth = get_recipe_synthesizer()
    r = synthesize_recipe_from_ingredients(
        ingredients=[{"name": "pasta", "amount": 100, "unit": "g"}],
        cuisine_preference="italian",
        difficulty_preference="easy",
        servings=2,
    )
    assert r.servings == 2 and r.cuisine_type in ("italian", "international")


def test_synthesize_recipes_for_week_wrapper() -> None:
    week_plan: Dict = {
        "days": [
            {
                "day": "Mon",
                "meals": [
                    {
                        "name": "lunch",
                        "ingredients": [
                            {"name": "tomato", "amount": 120, "unit": "g"},
                            {"name": "pasta", "amount": 100, "unit": "g"},
                        ],
                    },
                    {
                        "name": "dinner",
                        "ingredients": [
                            {"name": "tofu", "amount": 200, "unit": "g"},
                        ],
                    },
                ],
            }
        ]
    }

    weekly = synthesize_recipes_for_week(week_plan, recipes_per_day=1)
    assert set(weekly.keys()) == {"Mon"}
    assert len(weekly["Mon"]) == 1


def test_load_templates_paths(tmp_path) -> None:
    # Existing empty dir triggers default template creation branch
    empty = tmp_path / "empty"
    empty.mkdir()
    synth = RecipeSynthesizer(templates_dir=str(empty))
    assert synth.templates  # defaults created

    # Dir with invalid JSON file triggers error handling branch
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "t.json").write_text("{not-json}")
    synth2 = RecipeSynthesizer(templates_dir=str(bad))
    # Should not raise; still ends with templates dict (may be empty if no valid files)
    assert isinstance(synth2.templates, dict)


def test_title_and_tags_generation() -> None:
    synth = get_recipe_synthesizer()
    tpl = next(iter(synth.templates.values()))
    ings = [
        {"name": "chicken breast", "amount": 200, "unit": "g"},
        {"name": "mixed vegetables", "amount": 150, "unit": "g"},
        {"name": "fresh herbs", "amount": 5, "unit": "g"},
    ]
    # Private helpers via synthesizer
    title = synth._generate_recipe_title(tpl, ings)
    assert "Chicken" in title or "Delicious" in title
    # Calculate tags
    tags = synth._generate_tags(tpl, ings)
    assert any(t in tags for t in ["protein-rich", "vegetarian", "spicy"])  # heuristic


def test_select_best_template_fallback_branch() -> None:
    synth = get_recipe_synthesizer()
    tpl = synth._select_best_template(
        ingredients=[{"name": "xyz", "amount": 1, "unit": "g"}],
        cuisine_preference="nonexistent",
        difficulty_preference="impossible",
    )
    assert isinstance(tpl, type(next(iter(synth.templates.values()))))


def test_private_extraction_helpers() -> None:
    synth = get_recipe_synthesizer()
    # Duration buckets
    assert synth._estimate_step_duration("Marinate chicken", next(iter(synth.templates.values()))) == 30
    assert synth._estimate_step_duration("Boil water", next(iter(synth.templates.values()))) == 20
    assert synth._estimate_step_duration("Chop veggies", next(iter(synth.templates.values()))) == 5
    assert synth._estimate_step_duration("Heat oil", next(iter(synth.templates.values()))) == 2
    # Temperatures
    assert synth._extract_temperature("Cook on medium heat") == "Medium"
    assert synth._extract_temperature("Keep on low heat") == "Low"
    assert synth._extract_temperature("Preheat oven") == "Preheated"
    assert synth._extract_temperature("High heat stir-fry") == "High"
    # Equipment
    assert synth._extract_equipment("Use a wok or pan") == "Wok or Large Pan"
    assert synth._extract_equipment("Bring to boil in pot") == "Large Pot"
    assert synth._extract_equipment("Grill the protein") == "Grill"
    assert synth._extract_equipment("Mix in bowl") == "Large Bowl"


def test_calculate_nutrition_edges() -> None:
    synth = get_recipe_synthesizer()
    nutrients = synth._calculate_nutrition(
        [
            {"name": "chicken", "amount": 200, "unit": "g"},
            {"name": "vegetables", "amount": 100, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
            {"name": "olive oil", "amount": 10, "unit": "g"},
        ],
        servings=2,
    )
    assert nutrients["calories"] > 0 and nutrients["fat"] > 0


def test_nonexistent_templates_dir_branch() -> None:
    # Provide a path that does not exist to hit the exists()==False branch
    synth = RecipeSynthesizer(templates_dir="surely/does/not/exist/pp")
    assert synth.templates
