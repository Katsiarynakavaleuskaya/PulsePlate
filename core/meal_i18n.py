"""
Internationalization (i18n) module for the weekly meal plan feature.

Provides translation dictionaries and functions for RU/EN/ES localization
of food items, recipes, and meal plan messages.
"""

from typing import Literal

# Translation dictionaries for food items
FOOD_TRANSLATIONS = {
    "ru": {
        # Protein sources
        "chicken_breast": "Куриная грудка",
        "salmon": "Лосось",
        "greek_yogurt": "Греческий йогурт",
        "tofu": "Тофу",

        # Vegetables
        "spinach": "Шпинат",
        "lentils": "Чечевица",

        # Grains
        "oats": "Овсянка",
        "brown_rice": "Бурый рис",

        # Fats
        "olive_oil": "Оливковое масло",

        # Fruits
        "banana": "Банан",
    },
    "en": {
        # Protein sources
        "chicken_breast": "Chicken breast",
        "salmon": "Salmon",
        "greek_yogurt": "Greek yogurt",
        "tofu": "Tofu",

        # Vegetables
        "spinach": "Spinach",
        "lentils": "Lentils",

        # Grains
        "oats": "Oats",
        "brown_rice": "Brown rice",

        # Fats
        "olive_oil": "Olive oil",

        # Fruits
        "banana": "Banana",
    },
    "es": {
        # Protein sources
        "chicken_breast": "Pechuga de pollo",
        "salmon": "Salmón",
        "greek_yogurt": "Yogur griego",
        "tofu": "Tofu",

        # Vegetables
        "spinach": "Espinacas",
        "lentils": "Lentejas",

        # Grains
        "oats": "Avena",
        "brown_rice": "Arroz integral",

        # Fats
        "olive_oil": "Aceite de oliva",

        # Fruits
        "banana": "Plátano",
    }
}

# Translation dictionaries for recipes
RECIPE_TRANSLATIONS = {
    "ru": {
        "oatmeal_breakfast": "Овсянка на завтрак",
        "chicken_rice_lunch": "Курица с рисом на обед",
        "tofu_bowl_dinner": "Тофу боул на ужин",
        "salmon_plate_dinner": "Лосось на ужин",
        "lentil_salad_lunch": "Салат из чечевицы на обед",
        "yogurt_snack": "Йогурт перекус",
    },
    "en": {
        "oatmeal_breakfast": "Oatmeal breakfast",
        "chicken_rice_lunch": "Chicken and rice lunch",
        "tofu_bowl_dinner": "Tofu bowl dinner",
        "salmon_plate_dinner": "Salmon plate dinner",
        "lentil_salad_lunch": "Lentil salad lunch",
        "yogurt_snack": "Yogurt snack",
    },
    "es": {
        "oatmeal_breakfast": "Desayuno de avena",
        "chicken_rice_lunch": "Almuerzo de pollo y arroz",
        "tofu_bowl_dinner": "Cena de tofu bowl",
        "salmon_plate_dinner": "Cena de salmón",
        "lentil_salad_lunch": "Almuerzo de ensalada de lentejas",
        "yogurt_snack": "Merienda de yogur",
    }
}

# Translation dictionaries for meal types
MEAL_TRANSLATIONS = {
    "ru": {
        "breakfast": "Завтрак",
        "lunch": "Обед",
        "dinner": "Ужин",
        "snack": "Перекус",
    },
    "en": {
        "breakfast": "Breakfast",
        "lunch": "Lunch",
        "dinner": "Dinner",
        "snack": "Snack",
    },
    "es": {
        "breakfast": "Desayuno",
        "lunch": "Almuerzo",
        "dinner": "Cena",
        "snack": "Merienda",
    }
}

# Translation dictionaries for tips and messages
TIP_TRANSLATIONS = {
    "ru": {
        "low_Fe_mg": "Низкий уровень железа → добавлен {}",
        "low_Ca_mg": "Низкий уровень кальция → добавлен {}",
        "low_VitD_IU": "Низкий уровень витамина D → добавлен {}",
        "low_B12_ug": "Низкий уровень витамина B12 → добавлен {}",
        "low_Folate_ug": "Низкий уровень фолата → добавлен {}",
        "low_Iodine_ug": "Низкий уровень йода → добавлен {}",
        "low_K_mg": "Низкий уровень калия → добавлен {}",
        "low_Mg_mg": "Низкий уровень магния → добавлен {}",
    },
    "en": {
        "low_Fe_mg": "Low iron → added {}",
        "low_Ca_mg": "Low calcium → added {}",
        "low_VitD_IU": "Low vitamin D → added {}",
        "low_B12_ug": "Low vitamin B12 → added {}",
        "low_Folate_ug": "Low folate → added {}",
        "low_Iodine_ug": "Low iodine → added {}",
        "low_K_mg": "Low potassium → added {}",
        "low_Mg_mg": "Low magnesium → added {}",
    },
    "es": {
        "low_Fe_mg": "Bajo hierro → agregado {}",
        "low_Ca_mg": "Bajo calcio → agregado {}",
        "low_VitD_IU": "Bajo vitamina D → agregado {}",
        "low_B12_ug": "Bajo vitamina B12 → agregado {}",
        "low_Folate_ug": "Bajo folato → agregado {}",
        "low_Iodine_ug": "Bajo yodo → agregado {}",
        "low_K_mg": "Bajo potasio → agregado {}",
        "low_Mg_mg": "Bajo magnesio → agregado {}",
    }
}

# Type alias for language codes
Language = Literal["ru", "en", "es"]


def translate_food(lang: Language, food_name: str) -> str:
    """
    Translate a food name to the specified language.

    Args:
        lang: Language code ("ru", "en", or "es")
        food_name: Food name to translate

    Returns:
        Translated food name
    """
    if lang not in FOOD_TRANSLATIONS:
        return food_name

    translations = FOOD_TRANSLATIONS[lang]
    return translations.get(food_name, food_name)


def translate_recipe(lang: Language, recipe_name: str) -> str:
    """
    Translate a recipe name to the specified language.

    Args:
        lang: Language code ("ru", "en", or "es")
        recipe_name: Recipe name to translate

    Returns:
        Translated recipe name
    """
    if lang not in RECIPE_TRANSLATIONS:
        return recipe_name

    translations = RECIPE_TRANSLATIONS[lang]
    return translations.get(recipe_name, recipe_name)


def translate_meal_type(lang: Language, meal_type: str) -> str:
    """
    Translate a meal type to the specified language.

    Args:
        lang: Language code ("ru", "en", or "es")
        meal_type: Meal type to translate

    Returns:
        Translated meal type
    """
    if lang not in MEAL_TRANSLATIONS:
        return meal_type

    translations = MEAL_TRANSLATIONS[lang]
    return translations.get(meal_type, meal_type)


def translate_tip(lang: Language, tip_key: str, donor_food: str = "") -> str:
    """
    Translate a tip message to the specified language.

    Args:
        lang: Language code ("ru", "en", or "es")
        tip_key: Tip key to translate
        donor_food: Donor food name to include in the tip

    Returns:
        Translated tip message
    """
    if lang not in TIP_TRANSLATIONS:
        return tip_key

    translations = TIP_TRANSLATIONS[lang]
    tip_template = translations.get(tip_key, tip_key)

    # Translate the donor food name
    translated_donor = translate_food(lang, donor_food) if donor_food else donor_food

    return tip_template.format(translated_donor)
