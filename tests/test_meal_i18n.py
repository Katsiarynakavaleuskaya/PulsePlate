"""
Tests for Meal Internationalization (i18n) module

RU: Тесты для модуля интернационализации планов питания.
EN: Tests for meal internationalization module.
"""

import pytest

from core.meal_i18n import (
    translate_food,
    translate_recipe,
    translate_meal_type,
    translate_tip,
    Language,
    FOOD_TRANSLATIONS,
    RECIPE_TRANSLATIONS,
    MEAL_TRANSLATIONS,
    TIP_TRANSLATIONS
)


class TestTranslateFood:
    """Test translate_food function."""

    def test_translate_food_russian(self):
        """Test food translation to Russian."""
        assert translate_food("ru", "chicken_breast") == "Куриная грудка"
        assert translate_food("ru", "salmon") == "Лосось"
        assert translate_food("ru", "greek_yogurt") == "Греческий йогурт"
        assert translate_food("ru", "tofu") == "Тофу"
        assert translate_food("ru", "spinach") == "Шпинат"
        assert translate_food("ru", "lentils") == "Чечевица"
        assert translate_food("ru", "oats") == "Овсянка"
        assert translate_food("ru", "brown_rice") == "Бурый рис"
        assert translate_food("ru", "olive_oil") == "Оливковое масло"
        assert translate_food("ru", "banana") == "Банан"

    def test_translate_food_english(self):
        """Test food translation to English."""
        assert translate_food("en", "chicken_breast") == "Chicken breast"
        assert translate_food("en", "salmon") == "Salmon"
        assert translate_food("en", "greek_yogurt") == "Greek yogurt"
        assert translate_food("en", "tofu") == "Tofu"
        assert translate_food("en", "spinach") == "Spinach"
        assert translate_food("en", "lentils") == "Lentils"
        assert translate_food("en", "oats") == "Oats"
        assert translate_food("en", "brown_rice") == "Brown rice"
        assert translate_food("en", "olive_oil") == "Olive oil"
        assert translate_food("en", "banana") == "Banana"

    def test_translate_food_spanish(self):
        """Test food translation to Spanish."""
        assert translate_food("es", "chicken_breast") == "Pechuga de pollo"
        assert translate_food("es", "salmon") == "Salmón"
        assert translate_food("es", "greek_yogurt") == "Yogur griego"
        assert translate_food("es", "tofu") == "Tofu"
        assert translate_food("es", "spinach") == "Espinacas"
        assert translate_food("es", "lentils") == "Lentejas"
        assert translate_food("es", "oats") == "Avena"
        assert translate_food("es", "brown_rice") == "Arroz integral"
        assert translate_food("es", "olive_oil") == "Aceite de oliva"
        assert translate_food("es", "banana") == "Plátano"

    def test_translate_food_unknown_food(self):
        """Test food translation with unknown food name."""
        assert translate_food("ru", "unknown_food") == "unknown_food"
        assert translate_food("en", "unknown_food") == "unknown_food"
        assert translate_food("es", "unknown_food") == "unknown_food"

    def test_translate_food_unknown_language(self):
        """Test food translation with unknown language."""
        assert translate_food("fr", "chicken_breast") == "chicken_breast"
        assert translate_food("de", "salmon") == "salmon"
        assert translate_food("it", "tofu") == "tofu"


class TestTranslateRecipe:
    """Test translate_recipe function."""

    def test_translate_recipe_russian(self):
        """Test recipe translation to Russian."""
        assert translate_recipe("ru", "oatmeal_breakfast") == "Овсянка на завтрак"
        assert translate_recipe("ru", "chicken_rice_lunch") == "Курица с рисом на обед"
        assert translate_recipe("ru", "tofu_bowl_dinner") == "Тофу боул на ужин"
        assert translate_recipe("ru", "salmon_plate_dinner") == "Лосось на ужин"
        assert translate_recipe("ru", "lentil_salad_lunch") == "Салат из чечевицы на обед"
        assert translate_recipe("ru", "yogurt_snack") == "Йогурт перекус"

    def test_translate_recipe_english(self):
        """Test recipe translation to English."""
        assert translate_recipe("en", "oatmeal_breakfast") == "Oatmeal breakfast"
        assert translate_recipe("en", "chicken_rice_lunch") == "Chicken and rice lunch"
        assert translate_recipe("en", "tofu_bowl_dinner") == "Tofu bowl dinner"
        assert translate_recipe("en", "salmon_plate_dinner") == "Salmon plate dinner"
        assert translate_recipe("en", "lentil_salad_lunch") == "Lentil salad lunch"
        assert translate_recipe("en", "yogurt_snack") == "Yogurt snack"

    def test_translate_recipe_spanish(self):
        """Test recipe translation to Spanish."""
        assert translate_recipe("es", "oatmeal_breakfast") == "Desayuno de avena"
        assert translate_recipe("es", "chicken_rice_lunch") == "Almuerzo de pollo y arroz"
        assert translate_recipe("es", "tofu_bowl_dinner") == "Cena de tofu bowl"
        assert translate_recipe("es", "salmon_plate_dinner") == "Cena de salmón"
        assert translate_recipe("es", "lentil_salad_lunch") == "Almuerzo de ensalada de lentejas"
        assert translate_recipe("es", "yogurt_snack") == "Merienda de yogur"

    def test_translate_recipe_unknown_recipe(self):
        """Test recipe translation with unknown recipe name."""
        assert translate_recipe("ru", "unknown_recipe") == "unknown_recipe"
        assert translate_recipe("en", "unknown_recipe") == "unknown_recipe"
        assert translate_recipe("es", "unknown_recipe") == "unknown_recipe"

    def test_translate_recipe_unknown_language(self):
        """Test recipe translation with unknown language."""
        assert translate_recipe("fr", "oatmeal_breakfast") == "oatmeal_breakfast"
        assert translate_recipe("de", "chicken_rice_lunch") == "chicken_rice_lunch"


class TestTranslateMealType:
    """Test translate_meal_type function."""

    def test_translate_meal_type_russian(self):
        """Test meal type translation to Russian."""
        assert translate_meal_type("ru", "breakfast") == "Завтрак"
        assert translate_meal_type("ru", "lunch") == "Обед"
        assert translate_meal_type("ru", "dinner") == "Ужин"
        assert translate_meal_type("ru", "snack") == "Перекус"

    def test_translate_meal_type_english(self):
        """Test meal type translation to English."""
        assert translate_meal_type("en", "breakfast") == "Breakfast"
        assert translate_meal_type("en", "lunch") == "Lunch"
        assert translate_meal_type("en", "dinner") == "Dinner"
        assert translate_meal_type("en", "snack") == "Snack"

    def test_translate_meal_type_spanish(self):
        """Test meal type translation to Spanish."""
        assert translate_meal_type("es", "breakfast") == "Desayuno"
        assert translate_meal_type("es", "lunch") == "Almuerzo"
        assert translate_meal_type("es", "dinner") == "Cena"
        assert translate_meal_type("es", "snack") == "Merienda"

    def test_translate_meal_type_unknown_meal_type(self):
        """Test meal type translation with unknown meal type."""
        assert translate_meal_type("ru", "unknown_meal") == "unknown_meal"
        assert translate_meal_type("en", "unknown_meal") == "unknown_meal"
        assert translate_meal_type("es", "unknown_meal") == "unknown_meal"

    def test_translate_meal_type_unknown_language(self):
        """Test meal type translation with unknown language."""
        assert translate_meal_type("fr", "breakfast") == "breakfast"
        assert translate_meal_type("de", "lunch") == "lunch"


class TestTranslateTip:
    """Test translate_tip function."""

    def test_translate_tip_russian(self):
        """Test tip translation to Russian."""
        assert translate_tip("ru", "low_Fe_mg", "spinach") == "Низкий уровень железа → добавлен Шпинат"
        assert translate_tip("ru", "low_Ca_mg", "greek_yogurt") == "Низкий уровень кальция → добавлен Греческий йогурт"
        assert translate_tip("ru", "low_VitD_IU", "salmon") == "Низкий уровень витамина D → добавлен Лосось"
        assert translate_tip("ru", "low_B12_ug", "tofu") == "Низкий уровень витамина B12 → добавлен Тофу"
        assert translate_tip("ru", "low_Folate_ug", "lentils") == "Низкий уровень фолата → добавлен Чечевица"
        assert translate_tip("ru", "low_Iodine_ug", "banana") == "Низкий уровень йода → добавлен Банан"
        assert translate_tip("ru", "low_K_mg", "olive_oil") == "Низкий уровень калия → добавлен Оливковое масло"
        assert translate_tip("ru", "low_Mg_mg", "oats") == "Низкий уровень магния → добавлен Овсянка"

    def test_translate_tip_english(self):
        """Test tip translation to English."""
        assert translate_tip("en", "low_Fe_mg", "spinach") == "Low iron → added Spinach"
        assert translate_tip("en", "low_Ca_mg", "greek_yogurt") == "Low calcium → added Greek yogurt"
        assert translate_tip("en", "low_VitD_IU", "salmon") == "Low vitamin D → added Salmon"
        assert translate_tip("en", "low_B12_ug", "tofu") == "Low vitamin B12 → added Tofu"
        assert translate_tip("en", "low_Folate_ug", "lentils") == "Low folate → added Lentils"
        assert translate_tip("en", "low_Iodine_ug", "banana") == "Low iodine → added Banana"
        assert translate_tip("en", "low_K_mg", "olive_oil") == "Low potassium → added Olive oil"
        assert translate_tip("en", "low_Mg_mg", "oats") == "Low magnesium → added Oats"

    def test_translate_tip_spanish(self):
        """Test tip translation to Spanish."""
        assert translate_tip("es", "low_Fe_mg", "spinach") == "Bajo hierro → agregado Espinacas"
        assert translate_tip("es", "low_Ca_mg", "greek_yogurt") == "Bajo calcio → agregado Yogur griego"
        assert translate_tip("es", "low_VitD_IU", "salmon") == "Bajo vitamina D → agregado Salmón"
        assert translate_tip("es", "low_B12_ug", "tofu") == "Bajo vitamina B12 → agregado Tofu"
        assert translate_tip("es", "low_Folate_ug", "lentils") == "Bajo folato → agregado Lentejas"
        assert translate_tip("es", "low_Iodine_ug", "banana") == "Bajo yodo → agregado Plátano"
        assert translate_tip("es", "low_K_mg", "olive_oil") == "Bajo potasio → agregado Aceite de oliva"
        assert translate_tip("es", "low_Mg_mg", "oats") == "Bajo magnesio → agregado Avena"

    def test_translate_tip_without_donor_food(self):
        """Test tip translation without donor food."""
        assert translate_tip("ru", "low_Fe_mg") == "Низкий уровень железа → добавлен "
        assert translate_tip("en", "low_Ca_mg") == "Low calcium → added "
        assert translate_tip("es", "low_VitD_IU") == "Bajo vitamina D → agregado "

    def test_translate_tip_unknown_tip_key(self):
        """Test tip translation with unknown tip key."""
        assert translate_tip("ru", "unknown_tip", "spinach") == "unknown_tip"
        assert translate_tip("en", "unknown_tip", "spinach") == "unknown_tip"
        assert translate_tip("es", "unknown_tip", "spinach") == "unknown_tip"

    def test_translate_tip_unknown_language(self):
        """Test tip translation with unknown language."""
        assert translate_tip("fr", "low_Fe_mg", "spinach") == "low_Fe_mg"
        assert translate_tip("de", "low_Ca_mg", "greek_yogurt") == "low_Ca_mg"

    def test_translate_tip_unknown_donor_food(self):
        """Test tip translation with unknown donor food."""
        assert translate_tip("ru", "low_Fe_mg", "unknown_food") == "Низкий уровень железа → добавлен unknown_food"
        assert translate_tip("en", "low_Ca_mg", "unknown_food") == "Low calcium → added unknown_food"
        assert translate_tip("es", "low_VitD_IU", "unknown_food") == "Bajo vitamina D → agregado unknown_food"


class TestTranslationDictionaries:
    """Test translation dictionaries structure."""

    def test_food_translations_structure(self):
        """Test FOOD_TRANSLATIONS dictionary structure."""
        assert "ru" in FOOD_TRANSLATIONS
        assert "en" in FOOD_TRANSLATIONS
        assert "es" in FOOD_TRANSLATIONS
        
        # Test that all languages have the same keys
        ru_keys = set(FOOD_TRANSLATIONS["ru"].keys())
        en_keys = set(FOOD_TRANSLATIONS["en"].keys())
        es_keys = set(FOOD_TRANSLATIONS["es"].keys())
        
        assert ru_keys == en_keys == es_keys

    def test_recipe_translations_structure(self):
        """Test RECIPE_TRANSLATIONS dictionary structure."""
        assert "ru" in RECIPE_TRANSLATIONS
        assert "en" in RECIPE_TRANSLATIONS
        assert "es" in RECIPE_TRANSLATIONS
        
        # Test that all languages have the same keys
        ru_keys = set(RECIPE_TRANSLATIONS["ru"].keys())
        en_keys = set(RECIPE_TRANSLATIONS["en"].keys())
        es_keys = set(RECIPE_TRANSLATIONS["es"].keys())
        
        assert ru_keys == en_keys == es_keys

    def test_meal_translations_structure(self):
        """Test MEAL_TRANSLATIONS dictionary structure."""
        assert "ru" in MEAL_TRANSLATIONS
        assert "en" in MEAL_TRANSLATIONS
        assert "es" in MEAL_TRANSLATIONS
        
        # Test that all languages have the same keys
        ru_keys = set(MEAL_TRANSLATIONS["ru"].keys())
        en_keys = set(MEAL_TRANSLATIONS["en"].keys())
        es_keys = set(MEAL_TRANSLATIONS["es"].keys())
        
        assert ru_keys == en_keys == es_keys

    def test_tip_translations_structure(self):
        """Test TIP_TRANSLATIONS dictionary structure."""
        assert "ru" in TIP_TRANSLATIONS
        assert "en" in TIP_TRANSLATIONS
        assert "es" in TIP_TRANSLATIONS
        
        # Test that all languages have the same keys
        ru_keys = set(TIP_TRANSLATIONS["ru"].keys())
        en_keys = set(TIP_TRANSLATIONS["en"].keys())
        es_keys = set(TIP_TRANSLATIONS["es"].keys())
        
        assert ru_keys == en_keys == es_keys

    def test_language_type_alias(self):
        """Test Language type alias."""
        # Test that Language type accepts valid values
        valid_languages = ["ru", "en", "es"]
        for lang in valid_languages:
            assert isinstance(lang, str)
            assert lang in ["ru", "en", "es"]
