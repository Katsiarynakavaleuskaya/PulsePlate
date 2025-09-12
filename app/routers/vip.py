# -*- coding: utf-8 -*-
"""
VIP Module Router

RU: Роутер для VIP функций - микронутриентные цели, авто-ремонт меню, списки покупок
EN: Router for VIP functions - micronutrient goals, auto-repair menu, shopping lists
"""
from typing import Any, Dict

from fastapi import APIRouter

# Import dependencies from core (will be used in future sprints)
try:
    from core.auto_repair import (
        RepairStatus,
        RepairStrategy,
        auto_repair_week_plan,
        get_auto_repair_engine,
        suggest_manual_fixes,
    )
    from core.menu_engine import analyze_nutrient_gaps, make_weekly_menu
    from core.recipe_synth import (
        get_recipe_synthesizer,
        synthesize_recipe_from_ingredients,
        synthesize_recipes_for_week,
    )
    from core.region_catalog import (
        get_available_regions,
        get_price_comparison,
        get_region_catalog,
        search_products,
    )
    from core.shoplist import (
        ShoplistGenerator,
        aggregate_ingredients,
        format_export,
        round_to_packages,
    )
except ImportError:
    # Graceful fallback if core modules are not available
    make_weekly_menu = None
    analyze_nutrient_gaps = None
    ShoplistGenerator = None
    aggregate_ingredients = None
    round_to_packages = None
    format_export = None
    get_region_catalog = None
    search_products = None
    get_available_regions = None
    get_price_comparison = None
    get_recipe_synthesizer = None
    synthesize_recipe_from_ingredients = None
    synthesize_recipes_for_week = None
    get_auto_repair_engine = None
    auto_repair_week_plan = None
    suggest_manual_fixes = None
    RepairStrategy = None
    RepairStatus = None

router = APIRouter(prefix="/api/v1/vip", tags=["vip"])


@router.get("/health")
def vip_health() -> Dict[str, Any]:
    """
    RU: Проверка здоровья VIP модуля
    EN: VIP module health check
    """
    return {
        "status": "healthy",
        "module": "vip",
        "version": "0.1.0",
        "features": ["micronutrient_goals", "auto_repair", "shoplist"],
    }


@router.post("/menu/weekly/plan")
def weekly_menu_plan(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    RU: Планирование недельного меню с VIP функциями
    EN: Weekly menu planning with VIP features

    Args:
        request: Цели и ограничения для планирования

    Returns:
        Echo структура с планом меню
    """
    return {
        "status": "planned",
        "echo": request,
        "menu": {
            "days": 7,
            "meals_per_day": 3,
            "total_calories": 2000,
            "micronutrient_goals": "included",
        },
        "message": "Weekly menu plan generated (echo mode)",
    }


@router.post("/menu/weekly/repair")
def weekly_menu_repair(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    RU: Авто-ремонт недельного меню на основе дефицитов
    EN: Auto-repair weekly menu based on nutrient gaps

    Args:
        request: Меню + недобор/перебор нутриентов

    Returns:
        Echo структура с отремонтированным меню
    """
    return {
        "status": "repaired",
        "echo": request,
        "repairs": {
            "deficits_fixed": 0,
            "boosters_added": [],
            "calories_adjusted": False,
        },
        "message": "Weekly menu repaired (echo mode)",
    }


@router.post("/shoplist/weekly")
def weekly_shoplist(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    RU: Создание списка покупок на неделю с округлением до упаковок
    EN: Create weekly shopping list with package rounding

    Args:
        request: Недельный план питания

    Returns:
        Список покупок с округлением до упаковок
    """
    if ShoplistGenerator is None:
        return {
            "status": "error",
            "message": "Shoplist module not available",
            "echo": request,
        }

    try:
        # Агрегируем ингредиенты
        aggregated = aggregate_ingredients(request)

        # Округляем до упаковок
        shopping_list = round_to_packages(aggregated)

        # Форматируем для экспорта
        formatted = format_export(shopping_list, locale="ru", format_type="json")

        return {
            "status": "success",
            "echo": request,
            "shopping_list": formatted,
            "total_items": len(shopping_list),
            "message": "Weekly shopping list generated with package rounding",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating shopping list: {str(e)}",
            "echo": request,
        }


@router.post("/shoplist/daily")
def daily_shoplist(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    RU: Создание списка покупок на день с округлением до упаковок
    EN: Create daily shopping list with package rounding

    Args:
        request: Дневной план питания

    Returns:
        Список покупок с округлением до упаковок
    """
    if ShoplistGenerator is None:
        return {
            "status": "error",
            "message": "Shoplist module not available",
            "echo": request,
        }

    try:
        # Агрегируем ингредиенты
        aggregated = aggregate_ingredients(request)

        # Округляем до упаковок
        shopping_list = round_to_packages(aggregated)

        # Форматируем для экспорта
        formatted = format_export(shopping_list, locale="ru", format_type="json")

        return {
            "status": "success",
            "echo": request,
            "shopping_list": formatted,
            "total_items": len(shopping_list),
            "message": "Daily shopping list generated with package rounding",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating shopping list: {str(e)}",
            "echo": request,
        }


@router.get("/shoplist/formats")
def available_export_formats() -> Dict[str, Any]:
    """
    RU: Получить доступные форматы экспорта списков покупок
    EN: Get available export formats for shopping lists

    Returns:
        Список поддерживаемых форматов
    """
    return {
        "status": "success",
        "formats": ["json", "csv", "text"],
        "locales": ["ru", "en", "es"],
        "message": "Available export formats for shopping lists",
    }


@router.get("/regions")
def get_regions() -> Dict[str, Any]:
    """
    RU: Получить список доступных регионов
    EN: Get list of available regions

    Returns:
        Список доступных регионов
    """
    if get_available_regions is None:
        return {
            "status": "error",
            "message": "Region catalog module not available",
            "regions": [],
        }

    try:
        regions = get_available_regions()
        return {
            "status": "success",
            "regions": regions,
            "total_regions": len(regions),
            "message": "Available regions retrieved successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving regions: {str(e)}",
            "regions": [],
        }


@router.get("/regions/{region}/search")
def search_region_products(
    region: str, query: str, category: str = None, max_results: int = 20
) -> Dict[str, Any]:
    """
    RU: Поиск продуктов в региональном каталоге
    EN: Search products in regional catalog

    Args:
        region: Код региона (es, us)
        query: Поисковый запрос
        category: Фильтр по категории (опционально)
        max_results: Максимальное количество результатов

    Returns:
        Результаты поиска
    """
    if search_products is None:
        return {
            "status": "error",
            "message": "Region catalog module not available",
            "results": [],
        }

    try:
        search_result = search_products(query, region, category, max_results)

        # Конвертируем продукты в словари для JSON
        products_data = []
        for product in search_result.products:
            products_data.append(
                {
                    "product_id": product.product_id,
                    "name_es": product.name_es,
                    "name_en": product.name_en,
                    "category": product.category,
                    "unit": product.unit,
                    "typical_package_size": product.typical_package_size,
                    "price_eur": product.price_eur,
                    "price_usd": product.price_usd,
                    "store_chain": product.store_chain,
                    "region": product.region,
                }
            )

        return {
            "status": "success",
            "region": region,
            "query": query,
            "category": category,
            "products": products_data,
            "total_count": search_result.total_count,
            "returned_count": len(products_data),
            "message": f"Found {search_result.total_count} products in {region}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error searching products: {str(e)}",
            "region": region,
            "query": query,
            "products": [],
        }


@router.get("/regions/{region}/categories")
def get_region_categories(region: str) -> Dict[str, Any]:
    """
    RU: Получить категории продуктов в регионе
    EN: Get product categories in region

    Args:
        region: Код региона (es, us)

    Returns:
        Список категорий
    """
    if get_region_catalog is None:
        return {
            "status": "error",
            "message": "Region catalog module not available",
            "categories": [],
        }

    try:
        catalog = get_region_catalog()
        categories = catalog.get_categories(region)

        return {
            "status": "success",
            "region": region,
            "categories": categories,
            "total_categories": len(categories),
            "message": f"Retrieved {len(categories)} categories for {region}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving categories: {str(e)}",
            "region": region,
            "categories": [],
        }


@router.get("/regions/{region}/stores")
def get_region_stores(region: str) -> Dict[str, Any]:
    """
    RU: Получить торговые сети в регионе
    EN: Get store chains in region

    Args:
        region: Код региона (es, us)

    Returns:
        Список торговых сетей
    """
    if get_region_catalog is None:
        return {
            "status": "error",
            "message": "Region catalog module not available",
            "stores": [],
        }

    try:
        catalog = get_region_catalog()
        stores = catalog.get_store_chains(region)

        return {
            "status": "success",
            "region": region,
            "stores": stores,
            "total_stores": len(stores),
            "message": f"Retrieved {len(stores)} store chains for {region}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving stores: {str(e)}",
            "region": region,
            "stores": [],
        }


@router.get("/regions/compare/{product_name}")
def compare_product_prices(product_name: str, regions: str = "es,us") -> Dict[str, Any]:
    """
    RU: Сравнить цены продукта в разных регионах
    EN: Compare product prices across regions

    Args:
        product_name: Название продукта
        regions: Список регионов через запятую (по умолчанию: es,us)

    Returns:
        Сравнение цен по регионам
    """
    if get_price_comparison is None:
        return {
            "status": "error",
            "message": "Region catalog module not available",
            "comparison": {},
        }

    try:
        region_list = [r.strip() for r in regions.split(",")]
        comparison = get_price_comparison(product_name, region_list)

        # Форматируем результаты для JSON
        formatted_comparison = {}
        for region, data in comparison.items():
            if data["product"]:
                formatted_comparison[region] = {
                    "product_id": data["product"].product_id,
                    "name_es": data["product"].name_es,
                    "name_en": data["product"].name_en,
                    "category": data["product"].category,
                    "unit": data["product"].unit,
                    "typical_package_size": data["product"].typical_package_size,
                    "price_eur": data["price_eur"],
                    "price_usd": data["price_usd"],
                    "store_chain": data["store_chain"],
                    "region": data["region"],
                }
            else:
                formatted_comparison[region] = {
                    "product_id": None,
                    "name_es": None,
                    "name_en": None,
                    "category": None,
                    "unit": None,
                    "typical_package_size": None,
                    "price_eur": None,
                    "price_usd": None,
                    "store_chain": None,
                    "region": None,
                }

        return {
            "status": "success",
            "product_name": product_name,
            "regions": region_list,
            "comparison": formatted_comparison,
            "message": f"Price comparison for '{product_name}' across {len(region_list)} regions",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error comparing prices: {str(e)}",
            "product_name": product_name,
            "regions": regions.split(","),
            "comparison": {},
        }


@router.post("/recipes/synthesize")
def synthesize_recipe(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    RU: Синтезировать рецепт на основе ингредиентов
    EN: Synthesize recipe based on ingredients

    Args:
        request: Список ингредиентов и предпочтения

    Returns:
        Синтезированный рецепт
    """
    if synthesize_recipe_from_ingredients is None:
        return {
            "status": "error",
            "message": "Recipe synthesis module not available",
            "recipe": None,
        }

    try:
        ingredients = request.get("ingredients", [])
        cuisine_preference = request.get("cuisine_preference", "international")
        difficulty_preference = request.get("difficulty_preference", "easy")
        servings = request.get("servings", 4)

        recipe = synthesize_recipe_from_ingredients(
            ingredients, cuisine_preference, difficulty_preference, servings
        )

        # Конвертируем рецепт в словарь для JSON
        recipe_data = {
            "recipe_id": recipe.recipe_id,
            "title": recipe.title,
            "description": recipe.description,
            "cuisine_type": recipe.cuisine_type,
            "difficulty_level": recipe.difficulty_level,
            "prep_time_minutes": recipe.prep_time_minutes,
            "cook_time_minutes": recipe.cook_time_minutes,
            "total_time_minutes": recipe.total_time_minutes,
            "servings": recipe.servings,
            "ingredients": recipe.ingredients,
            "steps": [
                {
                    "step_number": step.step_number,
                    "instruction": step.instruction,
                    "duration_minutes": step.duration_minutes,
                    "temperature": step.temperature,
                    "equipment": step.equipment,
                }
                for step in recipe.steps
            ],
            "nutrition_per_serving": recipe.nutrition_per_serving,
            "tags": recipe.tags,
            "image_url": recipe.image_url,
        }

        return {
            "status": "success",
            "recipe": recipe_data,
            "message": f"Recipe '{recipe.title}' synthesized successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error synthesizing recipe: {str(e)}",
            "recipe": None,
        }


@router.post("/recipes/weekly")
def synthesize_weekly_recipes(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    RU: Синтезировать рецепты для недельного плана
    EN: Synthesize recipes for weekly meal plan

    Args:
        request: Недельный план питания

    Returns:
        Рецепты для недели
    """
    if synthesize_recipes_for_week is None:
        return {
            "status": "error",
            "message": "Recipe synthesis module not available",
            "weekly_recipes": {},
        }

    try:
        week_plan = request.get("week_plan", {})
        recipes_per_day = request.get("recipes_per_day", 1)

        weekly_recipes = synthesize_recipes_for_week(week_plan, recipes_per_day)

        # Конвертируем рецепты в словари для JSON
        formatted_recipes = {}
        for day, recipes in weekly_recipes.items():
            formatted_recipes[day] = []
            for recipe in recipes:
                recipe_data = {
                    "recipe_id": recipe.recipe_id,
                    "title": recipe.title,
                    "description": recipe.description,
                    "cuisine_type": recipe.cuisine_type,
                    "difficulty_level": recipe.difficulty_level,
                    "prep_time_minutes": recipe.prep_time_minutes,
                    "cook_time_minutes": recipe.cook_time_minutes,
                    "total_time_minutes": recipe.total_time_minutes,
                    "servings": recipe.servings,
                    "ingredients": recipe.ingredients,
                    "steps": [
                        {
                            "step_number": step.step_number,
                            "instruction": step.instruction,
                            "duration_minutes": step.duration_minutes,
                            "temperature": step.temperature,
                            "equipment": step.equipment,
                        }
                        for step in recipe.steps
                    ],
                    "nutrition_per_serving": recipe.nutrition_per_serving,
                    "tags": recipe.tags,
                    "image_url": recipe.image_url,
                }
                formatted_recipes[day].append(recipe_data)

        total_recipes = sum(len(recipes) for recipes in weekly_recipes.values())
        return {
            "status": "success",
            "weekly_recipes": formatted_recipes,
            "total_recipes": total_recipes,
            "message": f"Synthesized {total_recipes} recipes for the week",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error synthesizing weekly recipes: {str(e)}",
            "weekly_recipes": {},
        }


@router.get("/recipes/templates")
def get_recipe_templates() -> Dict[str, Any]:
    """
    RU: Получить доступные шаблоны рецептов
    EN: Get available recipe templates

    Returns:
        Список шаблонов рецептов
    """
    if get_recipe_synthesizer is None:
        return {
            "status": "error",
            "message": "Recipe synthesis module not available",
            "templates": [],
        }

    try:
        synthesizer = get_recipe_synthesizer()
        templates = []

        for template in synthesizer.templates.values():
            template_data = {
                "template_id": template.template_id,
                "name": template.name,
                "cuisine_type": template.cuisine_type,
                "base_ingredients": template.base_ingredients,
                "cooking_methods": template.cooking_methods,
                "typical_prep_time": template.typical_prep_time,
                "typical_cook_time": template.typical_cook_time,
                "difficulty": template.difficulty,
                "nutrition_profile": template.nutrition_profile,
            }
            templates.append(template_data)

        return {
            "status": "success",
            "templates": templates,
            "total_templates": len(templates),
            "message": f"Retrieved {len(templates)} recipe templates",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving templates: {str(e)}",
            "templates": [],
        }


@router.post("/auto-repair/weekly")
def auto_repair_weekly_plan(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    RU: Авто-ремонт недельного плана с UX-петлей
    EN: Auto-repair weekly plan with UX loop

    Args:
        request: Недельный план, цели и предпочтения

    Returns:
        Результат авто-ремонта с историей итераций
    """
    if auto_repair_week_plan is None:
        return {
            "status": "error",
            "message": "Auto-repair module not available",
            "repair_result": None,
        }

    try:
        week_plan = request.get("week_plan", {})
        targets_data = request.get("targets", {})
        strategy_name = request.get("strategy", "balanced")
        user_preferences = request.get("user_preferences", {})

        # Создаем цели по микронутриентам
        from core.targets import MicronutrientTargets

        targets = MicronutrientTargets(**targets_data)

        # Определяем стратегию
        if RepairStrategy is None:
            strategy = "balanced"
        else:
            strategy = RepairStrategy(strategy_name)

        # Выполняем авто-ремонт
        repair_result = auto_repair_week_plan(week_plan, targets, strategy, user_preferences)

        # Конвертируем результат в словарь для JSON
        result_data = {
            "status": (
                repair_result.status.value
                if hasattr(repair_result.status, "value")
                else str(repair_result.status)
            ),
            "repaired_plan": repair_result.repaired_plan,
            "original_plan": repair_result.original_plan,
            "changes_made": repair_result.changes_made,
            "remaining_gaps": repair_result.remaining_gaps,
            "strategy_used": (
                repair_result.strategy_used.value
                if hasattr(repair_result.strategy_used, "value")
                else str(repair_result.strategy_used)
            ),
            "iterations": repair_result.iterations,
            "message": repair_result.message,
            "suggestions": repair_result.suggestions,
        }

        return {
            "status": "success",
            "repair_result": result_data,
            "message": f"Auto-repair completed with status: {result_data['status']}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error during auto-repair: {str(e)}",
            "repair_result": None,
        }


@router.post("/auto-repair/suggestions")
def get_manual_repair_suggestions(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    RU: Получить предложения для ручного ремонта
    EN: Get suggestions for manual repair

    Args:
        request: Недельный план и цели

    Returns:
        Предложения для ручного ремонта
    """
    if suggest_manual_fixes is None:
        return {
            "status": "error",
            "message": "Auto-repair module not available",
            "suggestions": [],
        }

    try:
        week_plan = request.get("week_plan", {})
        targets_data = request.get("targets", {})

        # Создаем цели по микронутриентам
        from core.targets import MicronutrientTargets

        targets = MicronutrientTargets(**targets_data)

        # Получаем предложения
        suggestions = suggest_manual_fixes(week_plan, targets)

        return {
            "status": "success",
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "message": f"Generated {len(suggestions)} manual repair suggestions",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating suggestions: {str(e)}",
            "suggestions": [],
        }


@router.get("/auto-repair/strategies")
def get_repair_strategies() -> Dict[str, Any]:
    """
    RU: Получить доступные стратегии ремонта
    EN: Get available repair strategies

    Returns:
        Список доступных стратегий
    """
    if RepairStrategy is None:
        return {
            "status": "error",
            "message": "Auto-repair module not available",
            "strategies": [],
        }

    try:
        strategies = [
            {
                "name": "conservative",
                "display_name": "Консервативная",
                "description": "Минимальные изменения в плане",
                "use_case": "Когда нужно сохранить оригинальный план максимально",
            },
            {
                "name": "balanced",
                "display_name": "Сбалансированная",
                "description": "Умеренные изменения для оптимального результата",
                "use_case": "Рекомендуется для большинства случаев",
            },
            {
                "name": "aggressive",
                "display_name": "Агрессивная",
                "description": "Максимальные изменения для достижения целей",
                "use_case": "Когда нужно кардинально улучшить план",
            },
        ]

        return {
            "status": "success",
            "strategies": strategies,
            "total_strategies": len(strategies),
            "message": f"Retrieved {len(strategies)} repair strategies",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving strategies: {str(e)}",
            "strategies": [],
        }
