#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RU: Демонстрационный скрипт для работы с сортами продуктов.
EN: Demo script for working with product varieties.

Этот скрипт демонстрирует, как система работает с различными
сортами и марками продуктов, учитывая их пищевую ценность.
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.product_varieties import ProductVarietiesManager


def main():
    """Main function for product varieties demo."""
    print("🚀 Демонстрация системы сортов продуктов")
    print("=" * 50)

    # Инициализируем менеджер сортов
    manager = ProductVarietiesManager()

    # Показываем статистику
    stats = manager.get_statistics()
    print("📊 Статистика базы данных:")
    print(f"  Всего продуктов: {stats['total_products']}")
    print(f"  Всего сортов: {stats['total_varieties']}")
    print(
        f"  Среднее количество сортов на продукт: {stats['avg_varieties_per_product']}"
    )
    print()

    # Демонстрируем работу с молочными продуктами
    demo_products = ["Молоко", "Сыр", "Йогурт", "Творог"]

    for product_name in demo_products:
        print(f"🥛 Анализ продукта: {product_name}")
        print("-" * 30)

        varieties = manager.get_varieties(product_name)
        if not varieties:
            print(f"  ❌ Сорта для {product_name} не найдены")
            print()
            continue

        print(f"  📋 Найдено сортов: {len(varieties)}")

        # Показываем все сорта
        for i, variety in enumerate(varieties, 1):
            print(f"    {i}. {variety.variety} ({variety.brand})")
            print(
                f"       Белок: {variety.protein_g}g, Жиры: {variety.fat_g}g, "
                f"Углеводы: {variety.carbs_g}g, Сахар: {variety.sugar_g}g"
            )
            print(f"       Калории: {variety.get_calories():.1f} ккал")
            if variety.notes:
                print(f"       Примечание: {variety.notes}")

        # Показываем сравнение питательной ценности
        comparison = manager.get_nutritional_comparison(product_name)
        if comparison:
            print("  📊 Сравнение питательной ценности:")
            for variety_name, nutrition in comparison.items():
                print(f"    {variety_name}:")
                print(
                    f"      Калории: {nutrition['calories']:.1f}, "
                    f"Белок: {nutrition['protein']}g, "
                    f"Жиры: {nutrition['fat']}g, "
                    f"Сахар: {nutrition['sugar']}g"
                )

        # Демонстрируем рекомендации
        print("  🎯 Рекомендации:")

        # Низкосахарный вариант
        low_sugar = manager.get_best_variety(product_name, "low_sugar")
        if low_sugar:
            print(
                f"    Низкий сахар: {low_sugar.variety} ({low_sugar.sugar_g}g сахара)"
            )

        # Высокобелковый вариант
        high_protein = manager.get_best_variety(product_name, "high_protein")
        if high_protein:
            print(
                f"    Высокий белок: {high_protein.variety} ({high_protein.protein_g}g белка)"
            )

        # Низкожирный вариант
        low_fat = manager.get_best_variety(product_name, "low_fat")
        if low_fat:
            print(f"    Низкие жиры: {low_fat.variety} ({low_fat.fat_g}g жиров)")

        print()

    # Демонстрируем персонализированные рекомендации
    print("👤 Персонализированные рекомендации")
    print("=" * 50)

    user_profiles = [
        {"name": "Диабетик", "preferences": {"low_sugar": True, "low_fat": True}},
        {"name": "Спортсмен", "preferences": {"high_protein": True, "low_sugar": True}},
        {
            "name": "Вегетарианец",
            "preferences": {"vegetarian": True, "gluten_free": True},
        },
    ]

    for profile in user_profiles:
        print(f"👤 Профиль: {profile['name']}")
        print(f"   Предпочтения: {profile['preferences']}")

        for product_name in ["Молоко", "Сыр"]:
            recommended = manager.recommend_variety(
                product_name, profile["preferences"]
            )
            if recommended:
                print(f"   {product_name}: {recommended.variety} ({recommended.brand})")
                print(
                    f"     Белок: {recommended.protein_g}g, Жиры: {recommended.fat_g}g, "
                    f"Сахар: {recommended.sugar_g}g"
                )
            else:
                print(f"   {product_name}: рекомендации не найдены")
        print()

    # Демонстрируем поиск по критериям
    print("🔍 Поиск по критериям")
    print("=" * 50)

    search_examples = [
        ("Молоко", "обезжиренное", None),
        ("Сыр", "твердый", None),
        ("Йогурт", None, "стандарт"),
    ]

    for product_name, variety_name, brand in search_examples:
        print(f"🔍 Поиск: {product_name}")
        if variety_name:
            print(f"   Сорт: {variety_name}")
        if brand:
            print(f"   Марка: {brand}")

        results = manager.search_varieties(product_name, variety_name, brand)

        if results:
            print(f"   Найдено: {len(results)} результатов")
            for variety in results:
                print(f"     - {variety.variety} ({variety.brand})")
                print(
                    f"       Белок: {variety.protein_g}g, Жиры: {variety.fat_g}g, "
                    f"Сахар: {variety.sugar_g}g"
                )
        else:
            print("   Результаты не найдены")
        print()

    print("✅ Демонстрация завершена!")
    print()
    print("💡 Ключевые возможности системы:")
    print("  • Учет различных сортов и марок продуктов")
    print("  • Детальная информация о питательной ценности")
    print("  • Персонализированные рекомендации")
    print("  • Поиск по критериям (сорт, марка)")
    print("  • Сравнение питательной ценности")
    print("  • Учет содержания сахара и добавок")


if __name__ == "__main__":
    main()
