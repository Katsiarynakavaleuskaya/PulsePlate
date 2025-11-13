"""
Тесты для core/meal_i18n.py - покрытие недостающих веток
"""

from core.meal_i18n import (
    TIP_TRANSLATIONS,
    translate_food,
    translate_meal_type,
    translate_recipe,
    translate_tip,
)


class TestMealI18nCoverage:
    """Тесты для покрытия недостающих веток в meal_i18n.py"""

    def test_translate_food_invalid_language(self):
        """Тест translate_food с неподдерживаемым языком"""
        # Проверим fallback для неподдерживаемого языка
        result = translate_food("fr", "chicken_breast")  # type: ignore[arg-type]  # Французский не поддерживается
        assert result == "chicken_breast"  # Должен вернуть оригинальное название

    def test_translate_food_missing_key(self):
        """Тест translate_food с отсутствующим ключом"""
        # Проверим fallback для отсутствующего продукта
        result = translate_food("ru", "nonexistent_food")
        assert result == "nonexistent_food"  # Должен вернуть оригинальное название

    def test_translate_recipe_invalid_language(self):
        """Тест translate_recipe с неподдерживаемым языком"""
        result = translate_recipe("de", "oatmeal_breakfast")  # type: ignore[arg-type]  # Немецкий не поддерживается
        assert result == "oatmeal_breakfast"

    def test_translate_recipe_missing_key(self):
        """Тест translate_recipe с отсутствующим ключом"""
        result = translate_recipe("en", "nonexistent_recipe")
        assert result == "nonexistent_recipe"

    def test_translate_meal_type_invalid_language(self):
        """Тест translate_meal_type с неподдерживаемым языком"""
        result = translate_meal_type("pt", "breakfast")  # type: ignore[arg-type]  # Португальский не поддерживается
        assert result == "breakfast"

    def test_translate_meal_type_missing_key(self):
        """Тест translate_meal_type с отсутствующим ключом"""
        result = translate_meal_type("ru", "nonexistent_meal")
        assert result == "nonexistent_meal"

    def test_translate_tip_invalid_language(self) -> None:
        """Тест translate_tip с неподдерживаемым языком"""
        result = translate_tip("fr", "low_Fe_mg", "spinach")  # type: ignore[arg-type]
        assert result == "low_Fe_mg"  # Должен вернуть исходный ключ

    def test_translate_tip_missing_key(self):
        """Тест translate_tip с отсутствующим ключом"""
        result = translate_tip("en", "nonexistent_tip", "spinach")
        assert result == "nonexistent_tip"  # Должен вернуть исходный ключ

    def test_translate_tip_empty_donor(self):
        """Тест translate_tip с пустым donor_food"""
        # Проверим fallback для пустого donor
        result = translate_tip("en", "low_Fe_mg", "")
        assert result == "Low iron → added ingredient"  # Должен использовать fallback

        result = translate_tip("ru", "low_Ca_mg", "")
        assert result == "Низкий уровень кальция → добавлен продукт"

        result = translate_tip("es", "low_VitD_IU", "")
        assert result == "Bajo vitamina D → agregado alimento"

    def test_translate_tip_malformed_template(self):
        """Тест translate_tip с некорректным шаблоном"""
        # Создадим ситуацию с некорректным форматированием
        # Модифицируем словарь временно
        original_tip = TIP_TRANSLATIONS["en"]["low_Fe_mg"]

        # Некорректный формат с несколькими плейсхолдерами
        TIP_TRANSLATIONS["en"]["low_Fe_mg"] = "Low iron → added {0} and {1}"

        try:
            result = translate_tip("en", "low_Fe_mg", "spinach")
            # Должен вернуть оригинальный шаблон при ошибке форматирования
            assert "Low iron" in result
        finally:
            # Восстанавливаем оригинальный шаблон
            TIP_TRANSLATIONS["en"]["low_Fe_mg"] = original_tip

    def test_translate_tip_empty_template_with_braces(self):
        """Тест translate_tip с пустым шаблоном содержащим скобки"""
        # Временно заменим шаблон на пустые скобки
        original_tip = TIP_TRANSLATIONS["ru"]["low_K_mg"]
        TIP_TRANSLATIONS["ru"]["low_K_mg"] = "{}"

        try:
            result = translate_tip("ru", "low_K_mg", "")
            # Должен вернуть fallback при пустом результате форматирования
            assert result == "продукт"
        finally:
            TIP_TRANSLATIONS["ru"]["low_K_mg"] = original_tip

    def test_translate_tip_no_braces_in_template(self):
        """Тест translate_tip с шаблоном без скобок"""
        # Временно заменим шаблон на строку без скобок
        original_tip = TIP_TRANSLATIONS["es"]["low_Mg_mg"]
        TIP_TRANSLATIONS["es"]["low_Mg_mg"] = "Simple message without braces"

        try:
            result = translate_tip("es", "low_Mg_mg", "spinach")
            # Должен вернуть шаблон как есть, без форматирования
            assert result == "Simple message without braces"
        finally:
            TIP_TRANSLATIONS["es"]["low_Mg_mg"] = original_tip

    def test_translate_tip_keyerror_handling(self):
        """Тест translate_tip с KeyError при форматировании"""
        # Временно заменим шаблон на строку с именованным плейсхолдером
        original_tip = TIP_TRANSLATIONS["en"]["low_B12_ug"]
        TIP_TRANSLATIONS["en"]["low_B12_ug"] = "Low B12 → added {food_name}"

        try:
            result = translate_tip("en", "low_B12_ug", "salmon")
            # Должен вернуть оригинальный шаблон при KeyError
            assert result == "Low B12 → added {food_name}"
        finally:
            TIP_TRANSLATIONS["en"]["low_B12_ug"] = original_tip

    def test_translate_tip_empty_template_fallback(self):
        """Тест translate_tip с полностью пустым шаблоном"""
        # Временно заменим шаблон на пустую строку
        original_tip = TIP_TRANSLATIONS["ru"]["low_Folate_ug"]
        TIP_TRANSLATIONS["ru"]["low_Folate_ug"] = ""

        try:
            result = translate_tip("ru", "low_Folate_ug", "")
            # Пустой шаблон возвращает пустую строку - это нормально
            assert result == ""
        finally:
            TIP_TRANSLATIONS["ru"]["low_Folate_ug"] = original_tip

    def test_translate_tip_working_cases(self):
        """Тест translate_tip с работающими случаями"""
        # Проверим нормальные случаи для каждого языка
        result_en = translate_tip("en", "low_Fe_mg", "spinach")
        assert result_en == "Low iron → added Spinach"

        result_ru = translate_tip("ru", "low_Ca_mg", "greek_yogurt")
        assert result_ru == "Низкий уровень кальция → добавлен Греческий йогурт"

        result_es = translate_tip("es", "low_VitD_IU", "salmon")
        assert result_es == "Bajo vitamina D → agregado Salmón"

    def test_all_language_fallbacks(self):
        """Тест fallback'ов для всех языков"""
        # Проверим fallback по языкам
        valid_languages = ["en", "ru", "es"]

        for lang in valid_languages:
            result = translate_food(lang, "unknown_food")  # type: ignore
            assert result == "unknown_food"

        # Проверим недопустимый язык через любое приведение
        result = translate_food("fr", "test_food")  # type: ignore
        assert result == "test_food"
