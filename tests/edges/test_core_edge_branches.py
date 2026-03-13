from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from core import recommendations as R
import core.exports_simple as exports_simple
from core.exports_simple import to_pdf_day, to_pdf_week
from core.food_apis.unified_db import UnifiedFoodDatabase
from core.menu_engine_new import DayPlan, build_plate_day
from core.plate import macros_by_rules
from core.rag import simple_rag as RAG
from core.recipe_db import Recipe as OldRecipe
from core.recipe_db import (
    calculate_recipe_nutrients,
    parse_recipe_db,
    scale_recipe_to_kcal,
)
from core.recipe_db_new import Meal
from core.recipe_db_new import RecipeDB as RecipeDBNew


def test_plate_macros_negative_remaining_kcal_triggers_reduction():
    # Force a case where kcal is low relative to protein/fat heuristics
    macros = macros_by_rules(weight_kg=150.0, kcal=900, goal="loss")
    # Should still produce positive, bounded integers with adjustments applied
    assert macros["protein_g"] > 0
    assert macros["fat_g"] > 0
    assert macros["carbs_g"] >= 1


def test_rag_empty_index_returns_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # ROOT is captured at import; override the module variable directly
    monkeypatch.setattr(RAG, "ROOT", tmp_path)
    RAG.invalidate_index()
    assert RAG.retrieve_context("iron") == ""


def test_rag_skips_large_files_and_handles_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Create an oversized markdown file to trigger size skip
    big_file = tmp_path / "big.md"
    big_file.write_bytes(b"x" * (RAG.MAX_FILE_SIZE + 1))

    # Create a normal file but patch read_text to raise to hit exception path
    normal_file = tmp_path / "doc.md"
    normal_file.write_text("Vitamin D helps calcium absorption.")

    def fake_iter_docs():
        # First the big one (skipped), then a broken path (exception), then nothing useful
        yield big_file
        yield normal_file

    monkeypatch.setattr(RAG, "ROOT", tmp_path)
    monkeypatch.setattr(RAG, "_iter_docs", fake_iter_docs)
    # Patch Path.read_text at the class level to raise only for this file
    RAG.invalidate_index()
    _orig_read_text = Path.read_text

    def _read_text_proxy(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == normal_file:
            raise RuntimeError("boom")
        return _orig_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _read_text_proxy, raising=True)
    # No crash and empty context
    assert RAG.retrieve_context("calcium") == ""


def _make_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    import csv

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "meal", "ingredients", "tags"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


class _FakeFood:
    def __init__(self) -> None:
        self.per_g = 100.0
        self.protein_g = 0.0
        self.fat_g = 0.0
        self.carbs_g = 0.0
        self.fiber_g = 0.0
        self.micros: Dict[str, float] = {}


class _FakeFoodDB:
    def get_food(self, name: str) -> _FakeFood:  # type: ignore[override]
        return _FakeFood()


def test_recipe_db_new_get_by_id_and_search_and_scale(tmp_path: Path):
    csv_path = _make_csv(
        tmp_path / "recipes.csv",
        [
            {"name": "Oats", "meal": "breakfast", "ingredients": "oats:100", "tags": "VEG"},
            {"name": "Chicken", "meal": "dinner", "ingredients": "chicken:200", "tags": "OMNI"},
        ],
    )
    db = RecipeDBNew(str(csv_path), _FakeFoodDB())  # pyright: ignore[reportArgumentType]

    # get by name
    assert db.get_recipe_by_id("Oats").name == "Oats"  # type: ignore[union-attr]
    # get by index
    assert db.get_recipe_by_id(0).name == "Oats"  # type: ignore[union-attr]
    # invalid
    assert db.get_recipe_by_id("zzz") is None

    # search with tags and limit
    res = db.search_recipes(query="oat", tags=["veg"], limit=1)
    assert len(res) == 1 and res[0].name == "Oats"

    # scale when kcal computed as zero -> still returns a Meal
    recipe = db.get_recipe_by_id("Oats")
    assert recipe is not None
    meal: Meal = db.scale_recipe_to_kcal(
        recipe, kcal_goal=500, lang="en"
    )  # pyright: ignore[reportArgumentType]
    assert isinstance(meal, Meal)


def test_recommendations_micronutrient_targets_pregnant_and_lactating():
    # Build minimal profile
    from core.targets import UserProfile

    base = UserProfile(
        sex="female",
        age=30,
        height_cm=165.0,
        weight_kg=60.0,
        activity="moderate",
        goal="maintain",
    )

    preg = UserProfile(
        sex=base.sex,
        age=base.age,
        height_cm=base.height_cm,
        weight_kg=base.weight_kg,
        activity=base.activity,
        goal=base.goal,
        deficit_pct=base.deficit_pct,
        surplus_pct=base.surplus_pct,
        bodyfat=base.bodyfat,
        region=base.region,
        timezone=base.timezone,
        diet_flags=base.diet_flags,
        life_stage="pregnant",
        medical_conditions=base.medical_conditions,
    )
    mt_preg = R.build_micronutrient_targets(preg)
    assert mt_preg.iron_mg[1] >= 27.0
    assert mt_preg.folate_ug[1] >= 600.0

    lact = UserProfile(
        sex=base.sex,
        age=base.age,
        height_cm=base.height_cm,
        weight_kg=base.weight_kg,
        activity=base.activity,
        goal=base.goal,
        deficit_pct=base.deficit_pct,
        surplus_pct=base.surplus_pct,
        bodyfat=base.bodyfat,
        region=base.region,
        timezone=base.timezone,
        diet_flags=base.diet_flags,
        life_stage="lactating",
        medical_conditions=base.medical_conditions,
    )
    mt_lact = R.build_micronutrient_targets(lact)
    assert mt_lact.iron_mg[1] <= 9.0
    assert mt_lact.folate_ug[1] >= 500.0

    # Age factor helper
    assert R._get_age_factor(10, "child") == 0.8
    assert R._get_age_factor(80, "elderly") == 1.1
    assert R._get_age_factor(15, "teen") == 1.2


def test_recipe_db_parser_and_scaler_with_malformed_entries(tmp_path: Path):
    # Create a CSV with malformed and valid ingredient entries
    csv_path = tmp_path / "old_recipes.csv"
    csv_path.write_text(
        "name,ingredients,flags\n"
        "BadRow,flour:not_a_number;milk:100,\n"
        "GoodRow,oats:100;milk:200,VEG\n",
        encoding="utf-8",
    )

    # Fake food db mapping implementing get_nutrient_amount
    class _FF:
        def get_nutrient_amount(self, key: str, grams: float) -> float:
            return 0.0

    food_db = {"oats": _FF(), "milk": _FF()}

    db = parse_recipe_db(str(csv_path), food_db)  # pyright: ignore[reportArgumentType]
    assert "GoodRow" in db and "BadRow" in db

    # Nutrients calc returns zeros with our fake db
    nutrients = calculate_recipe_nutrients(db["GoodRow"], food_db)  # type: ignore[arg-type]
    assert isinstance(nutrients, dict)

    # Scale with zero calories returns original
    scaled = scale_recipe_to_kcal(
        db["GoodRow"],
        kcal_goal=500,
        food_db=food_db,  # type: ignore[arg-type]
    )
    assert isinstance(scaled, OldRecipe) and scaled.name == "GoodRow"


def test_exports_pdf_fallback_day_week(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    # Force import error for reportlab to exercise fallback
    def boom():
        raise ImportError("no reportlab")

    monkeypatch.setattr(exports_simple, "_load_reportlab_components", boom)
    plate: Dict[str, Any] = {
        "kcal": 2000,
        "macros": {"protein_g": 120, "fat_g": 70, "carbs_g": 250, "fiber_g": 30},
        "meals": [
            {"title": "A", "kcal": 600, "protein_g": 30, "fat_g": 20, "carbs_g": 70},
        ],
    }
    day_pdf = tmp_path / "day.pdf"
    to_pdf_day(plate, day_pdf)
    assert day_pdf.exists() and day_pdf.read_bytes()

    week = {"days": [{"kcal": 2000, "macros": plate["macros"]}]}
    week_pdf = tmp_path / "week.pdf"
    to_pdf_week(week, week_pdf)
    assert week_pdf.exists() and week_pdf.read_bytes()


def test_unified_db_cache_load_error_and_save_throttle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Write invalid JSON to trigger load error path
    (cache_dir / "unified_food_cache.json").write_text("not json", encoding="utf-8")

    db = UnifiedFoodDatabase(cache_dir=str(cache_dir))
    # Prepare some memory cache to trigger save
    from core.food_apis.unified_db import UnifiedFoodItem

    db._memory_cache["k"] = UnifiedFoodItem(
        name="x",
        nutrients_per_100g={},
        cost_per_100g=1.0,
        tags=[],
        availability_regions=[],
        source="s",
        source_id="id",
    )

    # Throttle save to early-return
    monkeypatch.setenv("UNIFIED_DB_SAVE_THROTTLE_MS", "1000")
    import time as _t

    db._last_save_ts = _t.monotonic()
    db._save_cache()  # should return early without error


@pytest.mark.asyncio
async def test_unified_db_off_exception_and_invalid_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    db = UnifiedFoodDatabase(cache_dir=str(tmp_path))

    class OffMock:
        async def search_products(self, *args: Any, **kwargs: Any):  # noqa: D401
            raise RuntimeError("OFF boom")

        async def get_product_details(self, code: str):  # noqa: D401
            raise RuntimeError("detail boom")

        async def close(self) -> None:
            return None

    db.off_client = OffMock()
    # Force OFF path by preferring openfoodfacts and ensure empty result on exception
    res = await db.search_food("milk", prefer_source="openfoodfacts")
    assert res == []

    # Invalid USDA id path
    assert await db.get_food_by_id("usda", "abc") is None
    # OFF detail exception path
    assert await db.get_food_by_id("openfoodfacts", "123") is None


def test_product_finder_error_paths_and_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from core.food_sources.base import FoodRecord
    from core.product_finder import ProductFinder, ProductSearchResult

    pf = ProductFinder()

    class BadUSDA:
        def normalize(self):
            raise RuntimeError("usda fail")

    class BadOFF:
        def normalize(self):
            raise RuntimeError("off fail")

    monkeypatch.setattr(pf, "usda_adapter", BadUSDA())
    monkeypatch.setattr(pf, "off_adapter", BadOFF())

    res = pf.search_product("nonexistent")
    assert res.found is False and res.error_message

    # expand_database writes CSV rows when search_product mocked to found
    def fake_search(name: str) -> ProductSearchResult:
        fr = FoodRecord(
            name=name,
            locale="en",
            per_g=100.0,
            kcal=150.0,
            protein_g=10.0,
            fat_g=5.0,
            carbs_g=20.0,
            fiber_g=3.0,
            Fe_mg=1.0,
            Ca_mg=10.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=0.0,
            Iodine_ug=0.0,
            K_mg=0.0,
            Mg_mg=0.0,
            flags=[],
            price=1.0,
            source="mock",
            version_date="2025-01-01",
        )
        return ProductSearchResult(
            product_name=name, found=True, source="USDA", food_record=fr, confidence=0.9
        )

    monkeypatch.setattr(pf, "search_product", fake_search)
    csv_path = tmp_path / "added.csv"
    results = pf.expand_database(["buckwheat"], str(csv_path))
    assert results.get("buckwheat") is True
    assert csv_path.exists() and "buckwheat" in csv_path.read_text(encoding="utf-8")


def test_menu_engine_default_strategy_and_boosters_branch():
    from core.menu_engine import FoodItem as MEFood
    from core.menu_engine import (
        WeekMenu,
        _apply_repair_strategy,
        _find_booster_foods,
    )

    # Default strategy falls back to boosters_first (returns plan unchanged)
    plan = WeekMenu(
        week_start="w",
        daily_menus=[],
        weekly_coverage={},
        shopping_list={},
        total_cost=0.0,
        adherence_score=0.0,
    )
    same = _apply_repair_strategy(plan, {}, {}, "unknown", {}, None)
    assert same is plan

    # boosters branch: with gaps and nutrient content >0 we should list candidates
    food_db = {
        "spinach": MEFood(
            name="spinach",
            nutrients_per_100g={"iron_mg": 2.0},
            cost_per_100g=1.0,
            tags=[],
            availability_regions=[],
        )
    }
    boosters = _find_booster_foods(
        {"iron_mg": 10.0}, None, food_db
    )  # pyright: ignore[reportArgumentType]
    assert "iron_mg" in boosters and boosters["iron_mg"][0].name == "spinach"


class _StubFood:
    def __init__(self, kcal_zero: bool = False) -> None:
        self.per_g = 100.0
        self.fat_g = 0.0
        self.carbs_g = 0.0
        self.fiber_g = 0.0
        self.micros: Dict[str, float] = {}
        self.protein_g = 0.0 if kcal_zero else 1.0


class _StubFoodDB:
    def __init__(self, donor: str | None, kcal_zero: bool = False) -> None:
        self._donor = donor
        self._kcal_zero = kcal_zero

    def pick_booster_for(self, mk: str, diet_flags: list[str]) -> str | None:  # type: ignore[override]
        return self._donor

    def get_food(self, name: str) -> _StubFood:  # type: ignore[override]
        return _StubFood(kcal_zero=self._kcal_zero)

    def get_translated_food_name(self, name: str, lang: str) -> str:  # type: ignore[override]
        return name


class _StubRecipeDB:
    def pick_base_recipe(self, diet_flags: list[str], i: int) -> Any:  # type: ignore[override]
        return None  # no base recipes

    def scale_recipe_to_kcal(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        raise AssertionError("should not be called without base recipe")


def test_menu_engine_new_booster_none_path():
    # With no meals and high micro targets, cov < 80 triggers booster path.
    targets = {
        "kcal": 2000,
        "micro": {
            k: 100.0 for k in __import__("core.food_db_new", fromlist=["MICRO_KEYS"]).MICRO_KEYS
        },
    }
    plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
        targets=targets,
        diet_flags=[],
        lang="en",
        fooddb=_StubFoodDB(donor=None),
        recipedb=_StubRecipeDB(),
    )
    # No crash and plan is returned
    assert isinstance(plan, DayPlan)


def test_menu_engine_new_kcal_100_zero_path():
    # Force donor and zero macro food so kcal_100 == 0 and branch is skipped.
    targets = {
        "kcal": 2000,
        "micro": {
            k: 100.0 for k in __import__("core.food_db_new", fromlist=["MICRO_KEYS"]).MICRO_KEYS
        },
    }
    plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
        targets=targets,
        diet_flags=[],
        lang="en",
        fooddb=_StubFoodDB(donor="spinach", kcal_zero=True),
        recipedb=_StubRecipeDB(),
    )
    assert isinstance(plan, DayPlan)


def test_menu_engine_new_booster_food_missing():
    from core.food_db_new import MICRO_KEYS

    class _MissingFoodDB:
        def pick_booster_for(self, _mk: str, _diet_flags: list[str]) -> str | None:
            return "donor"

        def get_food(self, _name: str):
            return None

    class _EmptyRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], _i: int) -> Any:
            return None

    targets = {"kcal": 2000, "micro": {k: 100.0 for k in MICRO_KEYS}}
    plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
        targets=targets,
        diet_flags=[],
        lang="en",
        fooddb=_MissingFoodDB(),
        recipedb=_EmptyRecipeDB(),
    )
    assert isinstance(plan, DayPlan)


def test_menu_engine_new_booster_per_g_defaulted():
    from core.food_db_new import MICRO_KEYS

    class _PerGInvalidFood:
        def __init__(self) -> None:
            self.per_g = "bad"
            self.protein_g = None
            self.fat_g = 1.0
            self.carbs_g = "bad"
            self.fiber_g = None
            self.micros = {MICRO_KEYS[0]: "2.5"}

    class _PerGInvalidFoodDB:
        def pick_booster_for(self, mk: str, _diet_flags: list[str]) -> str | None:
            return "donor" if mk == MICRO_KEYS[0] else None

        def get_food(self, _name: str) -> _PerGInvalidFood:
            return _PerGInvalidFood()

        def get_translated_food_name(self, name: str, _lang: str) -> str:
            return name

    class _EmptyRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], _i: int) -> Any:
            return None

    targets = {"kcal": 2000, "micro": {MICRO_KEYS[0]: 100.0}}
    plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
        targets=targets,
        diet_flags=[],
        lang="en",
        fooddb=_PerGInvalidFoodDB(),
        recipedb=_EmptyRecipeDB(),
    )
    assert isinstance(plan, DayPlan)


def test_menu_engine_new_booster_per_g_negative():
    from core.food_db_new import MICRO_KEYS

    class _PerGNegativeFood:
        def __init__(self) -> None:
            self.per_g = -1.0
            self.protein_g = 1.0
            self.fat_g = None
            self.carbs_g = 1.0
            self.fiber_g = 1.0
            self.micros = {k: 0.0 for k in MICRO_KEYS}

    class _PerGNegativeFoodDB:
        def pick_booster_for(self, mk: str, _diet_flags: list[str]) -> str | None:
            return "donor" if mk == MICRO_KEYS[0] else None

        def get_food(self, _name: str) -> _PerGNegativeFood:
            return _PerGNegativeFood()

        def get_translated_food_name(self, name: str, _lang: str) -> str:
            return name

    class _EmptyRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], _i: int) -> Any:
            return None

    targets = {"kcal": 2000, "micro": {MICRO_KEYS[0]: 100.0}}
    plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
        targets=targets,
        diet_flags=[],
        lang="en",
        fooddb=_PerGNegativeFoodDB(),
        recipedb=_EmptyRecipeDB(),
    )
    assert isinstance(plan, DayPlan)


def test_menu_engine_new_coerces_string_kcal() -> None:
    from types import SimpleNamespace

    from core.food_db_new import MICRO_KEYS

    class _NoBoosterFoodDB:
        def pick_booster_for(self, _mk: str, _diet_flags: list[str]) -> Optional[str]:
            return None

    class _OneMealRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], meal_index: int) -> Any:
            return object() if meal_index == 0 else None

        def scale_recipe_to_kcal(
            self, _recipe: object, _kcal_goal: int, _lang: str, **_kw: Any
        ) -> "SimpleNamespace":
            return SimpleNamespace(
                title="base",
                title_translated="base",
                grams={"x": 100.0},
                kcal="250",
                macros={"protein_g": 10.0, "fat_g": 5.0, "carbs_g": 20.0, "fiber_g": 3.0},
                micros={k: 0.0 for k in MICRO_KEYS},
            )

    plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
        targets={"kcal": 1000, "micro": {}},
        diet_flags=[],
        lang="en",
        fooddb=_NoBoosterFoodDB(),
        recipedb=_OneMealRecipeDB(),
    )
    assert isinstance(plan, DayPlan)
    assert plan.meals and isinstance(plan.meals[0]["kcal"], int)


def test_menu_engine_new_skips_meal_with_non_numeric_kcal():
    from types import SimpleNamespace

    from core.food_db_new import MICRO_KEYS

    class _NoBoosterFoodDB:
        def pick_booster_for(self, _mk: str, _diet_flags: list[str]) -> Optional[str]:
            return None

    class _BadKcalRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], meal_index: int) -> Any:
            return object() if meal_index == 0 else None

        def scale_recipe_to_kcal(
            self, _recipe: object, _kcal_goal: int, _lang: str, **_kw: Any
        ) -> "SimpleNamespace":
            return SimpleNamespace(
                title="bad",
                title_translated="bad",
                grams={"x": 100.0},
                kcal="bad",
                macros={"protein_g": 1.0, "fat_g": 1.0, "carbs_g": 1.0, "fiber_g": 0.0},
                micros={k: 0.0 for k in MICRO_KEYS},
            )

    with pytest.warns(RuntimeWarning, match="non-numeric kcal"):
        plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
            targets={"kcal": 1000, "micro": {}},
            diet_flags=[],
            lang="en",
            fooddb=_NoBoosterFoodDB(),
            recipedb=_BadKcalRecipeDB(),
        )
    assert plan.meals == []


def test_menu_engine_new_skips_meal_with_non_positive_kcal():
    from types import SimpleNamespace

    from core.food_db_new import MICRO_KEYS

    class _NoBoosterFoodDB:
        def pick_booster_for(self, _mk: str, _diet_flags: list[str]) -> str | None:
            return None

    class _ZeroKcalRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], meal_index: int) -> Any:
            return object() if meal_index == 0 else None

        def scale_recipe_to_kcal(self, _recipe: object, _kcal_goal: int, _lang: str, **_kw: Any):
            return SimpleNamespace(
                title="zero",
                title_translated="zero",
                grams={"x": 100.0},
                kcal=0,
                macros={"protein_g": 1.0, "fat_g": 1.0, "carbs_g": 1.0, "fiber_g": 0.0},
                micros={k: 0.0 for k in MICRO_KEYS},
            )

    with pytest.warns(RuntimeWarning, match="non-positive kcal"):
        plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
            targets={"kcal": 1000, "micro": {}},
            diet_flags=[],
            lang="en",
            fooddb=_NoBoosterFoodDB(),
            recipedb=_ZeroKcalRecipeDB(),
        )
    assert plan.meals == []


def test_menu_engine_new_handles_immutable_kcal_assignment():
    from core.food_db_new import MICRO_KEYS

    class _NoBoosterFoodDB:
        def pick_booster_for(self, _mk: str, _diet_flags: list[str]) -> str | None:
            return None

    class _FrozenKcalMeal:
        __slots__ = ("title", "title_translated", "grams", "kcal", "macros", "micros")

        def __init__(self) -> None:
            object.__setattr__(self, "title", "base")
            object.__setattr__(self, "title_translated", "base")
            object.__setattr__(self, "grams", {"x": 100.0})
            object.__setattr__(self, "kcal", 250.5)
            object.__setattr__(
                self,
                "macros",
                {"protein_g": 10.0, "fat_g": 5.0, "carbs_g": 20.0, "fiber_g": 3.0},
            )
            object.__setattr__(self, "micros", {k: 0.0 for k in MICRO_KEYS})

        def __setattr__(self, name: str, value: object) -> None:
            if name == "kcal":
                raise AttributeError("immutable kcal")
            object.__setattr__(self, name, value)

    class _FrozenKcalRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], meal_index: int) -> Any:
            return object() if meal_index == 0 else None

        def scale_recipe_to_kcal(self, _recipe: object, _kcal_goal: int, _lang: str, **_kw: Any):
            return _FrozenKcalMeal()

    plan: DayPlan = build_plate_day(  # pyright: ignore[reportArgumentType]
        targets={"kcal": 1000, "micro": {}},
        diet_flags=[],
        lang="en",
        fooddb=_NoBoosterFoodDB(),
        recipedb=_FrozenKcalRecipeDB(),
    )
    assert plan.meals
