"""Category Mapping.

RU: Маппинг ингредиентов на категории.
EN: Ingredient to category mapping.

This module provides a flat mapping from ingredient keys to categories.
Designed to be easily extended with external data sources (OFF, Carrefour, etc).
"""

# Category display titles
CATEGORY_TITLES = {
    "proteins": "Proteins",
    "grains": "Grains",
    "vegetables": "Vegetables",
    "fruits": "Fruits",
    "dairy": "Dairy",
    "fats": "Fats & Oils",
    "nuts": "Nuts & Seeds",
    "other": "Other",
}

# Flat ingredient -> category mapping
# This is intentionally simple to allow future VIP enhancements:
# - Regional mappings (US vs EU vs Asia)
# - Store-specific categorization
# - Price-aware grouping
INGREDIENT_CATEGORY_MAP = {
    # Proteins
    "chicken_breast": "proteins",
    "chicken": "proteins",
    "salmon": "proteins",
    "tuna": "proteins",
    "beef": "proteins",
    "pork": "proteins",
    "turkey": "proteins",
    "tofu": "proteins",
    "tempeh": "proteins",
    "eggs": "proteins",
    # Grains
    "rice": "grains",
    "quinoa": "grains",
    "oats": "grains",
    "pasta": "grains",
    "bread": "grains",
    "noodles": "grains",
    "couscous": "grains",
    "bulgur": "grains",
    # Vegetables
    "broccoli": "vegetables",
    "carrot": "vegetables",
    "spinach": "vegetables",
    "kale": "vegetables",
    "tomato": "vegetables",
    "bell_peppers": "vegetables",
    "onion": "vegetables",
    "garlic": "vegetables",
    "cucumber": "vegetables",
    "lettuce": "vegetables",
    "zucchini": "vegetables",
    "eggplant": "vegetables",
    "cauliflower": "vegetables",
    "cabbage": "vegetables",
    "mushrooms": "vegetables",
    "peppers": "vegetables",
    # Fruits
    "banana": "fruits",
    "apple": "fruits",
    "orange": "fruits",
    "lemon": "fruits",
    "lime": "fruits",
    "strawberry": "fruits",
    "blueberry": "fruits",
    "mango": "fruits",
    "pineapple": "fruits",
    "avocado": "fruits",
    "berries": "fruits",
    # Dairy
    "milk": "dairy",
    "yogurt": "dairy",
    "cheese": "dairy",
    "butter": "dairy",
    "cream": "dairy",
    # Fats & Oils
    "olive_oil": "fats",
    "coconut_oil": "fats",
    "vegetable_oil": "fats",
    "sesame_oil": "fats",
    "oil": "fats",
    # Nuts & Seeds
    "almonds": "nuts",
    "walnuts": "nuts",
    "cashews": "nuts",
    "peanuts": "nuts",
    "chia_seeds": "nuts",
    "flax_seeds": "nuts",
    "sunflower_seeds": "nuts",
    "pumpkin_seeds": "nuts",
    "sesame_seeds": "nuts",
}


def category_for_ingredient(key: str) -> str:
    """Get category key for ingredient.

    Args:
        key: Normalized ingredient key

    Returns:
        Category key (defaults to "other" if not found)

    Examples:
        "chicken_breast" -> "proteins"
        "rice" -> "grains"
        "unknown_item" -> "other"
    """
    return INGREDIENT_CATEGORY_MAP.get(key, "other")
