#!/usr/bin/env python3
"""
Скрипт для удаления неиспользуемых импортов Optional из файлов.
"""

from pathlib import Path
import re
import sys


def fix_unused_optional_imports(file_path: Path) -> bool:
    """Исправляет неиспользуемые импорты Optional в файле."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # Паттерн для поиска импортов Optional
        # Ищем строки вида: from typing import Optional, ...
        # или: from typing import ..., Optional, ...
        optional_pattern = r"from typing import ([^;]+)"

        def replace_import(match):
            imports_str = match.group(1)
            imports = [imp.strip() for imp in imports_str.split(",")]

            # Удаляем Optional если он есть
            if "Optional" in imports:
                imports.remove("Optional")

                # Если остались другие импорты, возвращаем их
                if imports:
                    return f"from typing import {', '.join(imports)}"
                else:
                    # Если только Optional был, удаляем всю строку
                    return ""
            else:
                return match.group(0)

        # Применяем замену
        content = re.sub(optional_pattern, replace_import, content)

        # Удаляем пустые строки импорта
        content = re.sub(r"^from typing import\s*$", "", content, flags=re.MULTILINE)

        # Убираем лишние пустые строки
        content = re.sub(r"\n\n\n+", "\n\n", content)

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            print(f"✅ Исправлен {file_path}")
            return True
        else:
            print(f"⏭️  Пропущен {file_path} (нет изменений)")
            return False

    except Exception as e:
        print(f"❌ Ошибка в {file_path}: {e}")
        return False


def main():
    """Основная функция."""
    # Список файлов с неиспользуемыми импортами Optional
    files_to_fix = [
        "core/lifestage_nutrition.py",
        "nutrition_plate.py",
        "core/schemas.py",
        "app/routers/plan_export.py",
        "core/food_apis/scheduler.py",
        "core/product_finder.py",
        "app/routers/premium_week.py",
        "app/schemas/vip.py",
        "app/services/food_store.py",
        "core/food_apis/update_manager.py",
        "core/food_apis/unified_db.py",
        "core/bmi_extras_pro.py",
        "app/routers/shoplist_export.py",
        "core/time_utils.py",
        "core/recipe_db_new.py",
        "bmi_core.py",
        "core/daily_plate.py",
        "core/sports_nutrition.py",
        "core/utils.py",
        "core/food_db_new.py",
        "providers/stub.py",
        "core/product_varieties.py",
        "core/db.py",
        "core/targets.py",
        "core/auto_repair.py",
        "core/food_apis/usda_client.py",
        "bmi_visualization.py",
        "core/metabolism.py",
        "core/recipe_synth.py",
        "app/services/recipe_store.py",
        "app/routers/vip.py",
        "app/__init__.py",
        "app/schemas/food.py",
        "core/bmi_extras.py",
        "core/exports.py",
        "core/food_apis/openfoodfacts_client.py",
        "core/food_db.py",
        "core/menu_engine.py",
        "core/region_catalog.py",
        "core/shoplist.py",
        "example_nutrition_api.py",
    ]

    fixed_count = 0
    total_count = len(files_to_fix)

    for file_path_str in files_to_fix:
        file_path = Path(file_path_str)
        if file_path.exists():
            if fix_unused_optional_imports(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  Файл не найден: {file_path}")

    print(f"\n📊 Результат: исправлено {fixed_count} из {total_count} файлов")
    return 0


if __name__ == "__main__":
    sys.exit(main())
