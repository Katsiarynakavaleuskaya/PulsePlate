"""
Internationalization (i18n) module for the BMI App.

Provides translation dictionaries and functions for RU/EN/ES localization.
"""

from typing import Any, Literal, Optional

# Translation dictionaries
TRANSLATIONS = {
    "ru": {
        # BMI Categories
        "bmi_underweight": "Недостаточная масса",
        "bmi_normal": "Норма",
        "bmi_overweight": "Избыточная масса",
        "bmi_obese_1": "Ожирение I степени",
        "bmi_obese_2": "Ожирение II степени",
        "bmi_obese_3": "Ожирение III степени",
        # BMI Visualization (dot-keys for contract)
        "bmi.underweight": "Недостаточная масса",
        "bmi.normal": "Норма",
        "bmi.overweight": "Избыточная масса",
        "bmi.obesity": "Ожирение",
        # Activity Levels
        "level_beginner": "Начинающий",
        "level_novice": "Новичок",
        "level_intermediate": "Средний",
        "level_advanced": "Продвинутый",
        "activity_sedentary": "Малоподвижный",
        "activity_light": "Легкая активность",
        "activity_moderate": "Умеренная активность",
        "activity_active": "Активный",
        "activity_very_active": "Очень активный",
        # Validation Errors
        "validation_weight_positive": "Вес должен быть положительным числом",
        "validation_height_positive": "Рост должен быть положительным числом",
        "validation_age_range": "Возраст должен быть от 10 до 120 лет",
        "validation_waist_positive": "Обхват талии должен быть положительным числом",
        "validation_hip_positive": "Обхват бедер должен быть положительным числом",
        "validation_bodyfat_range": "Процент жира должен быть от 0 до 60",
        # Web Form Labels
        "form_weight": "Вес (кг)",
        "form_height": "Рост (см)",
        "form_age": "Возраст",
        "form_gender": "Пол",
        "form_pregnant": "Беременность",
        "form_athlete": "Спортсмен",
        "form_waist": "Талия (см)",
        "form_hip": "Бедра (см)",
        "form_bodyfat": "Процент жира (%)",
        # BMI Pro - Missing data notes
        "bmi_pro_whr_missing_hip": "WHR не рассчитан: нет окружности бёдер (hip_cm). Оценка риска выполнена только по BMI и WHtR.",
        "form_calculate": "Рассчитать",
        "form_male": "Мужской",
        "form_female": "Женский",
        "form_yes": "Да",
        "form_no": "Нет",
        # Bodyfat API Response Labels
        "bodyfat_methods": "методы",
        "bodyfat_median": "медиана",
        "bodyfat_units_percent": "%",
        # Advice Texts
        "advice_underweight": "Вам следует набрать вес. Проконсультируйтесь с врачом "
        "для составления плана питания.",
        "advice_normal": "У вас нормальный вес. Продолжайте поддерживать здоровый образ жизни.",
        "advice_overweight": "Вам следует сбросить вес. Рекомендуется сбалансированная "
        "диета и физическая активность.",
        "advice_obese": "Вам необходимо снизить вес. Обратитесь к врачу для "
        "консультации и составления плана похудения.",
        "advice_athlete_bmi": "У спортсменов BMI может завышать жировую массу",
        # Risk Assessment
        "risk_high_waist": "Высокий риск по талии",
        "risk_increased_waist": "Повышенный риск по талии",
        "risk_high_whr": "WHR ≥ {threshold} для пола → дополнительный риск.",
        "risk_high_bmi": "BMI ≥ 35: высокий общий риск.",
        "risk_moderate_bmi": "BMI 30–34.9: умеренно повышенный риск.",
        "risk_high_central_fat": "Высокий центральный жир (WHtR ≥ 0.6).",
        "risk_moderate_central_fat": "Повышенный центральный жир (WHtR ≥ 0.5).",
        "risk_low_health": "Низкий риск для здоровья",
        "risk_healthy_weight": "Диапазон здорового веса",
        "risk_moderate_health": "Умеренный риск для здоровья",
        "risk_high_health": "Высокий риск для здоровья",
        "risk_high_android_shape": "Высокий риск для здоровья (андроид/яблоко форма)",
        "risk_elderly_note": "У пожилых ИМТ может занижать долю жира (саркопения).",
        "risk_child_note": "Для подростков используйте возрастные центильные таблицы.",
        "risk_teen_note": "Подростковый возраст: учитывайте этап полового созревания.",
        # BMI Pro Labels
        "bmi_pro_low_risk": "Низкий",
        "bmi_pro_moderate_risk": "Умеренный",
        "bmi_pro_high_risk": "Высокий",
        "bmi_pro_analysis_complete": "Анализ BMI Pro завершен",
        # BMI Pro Notes (risk factors and assessments)
        "bmi_pro_risk_factors": "Факторы риска: {count}",
        "bmi_pro_wht_risk": "WHtR риск: {risk}",
        "bmi_pro_whr_risk": "WHR риск: {risk}",
        # Recommendations
        "recommendation_consult_healthcare": "Рассмотрите возможность консультации с "
        "медицинским специалистом для комплексной оценки",
        "recommendation_consult_professional": "Рассмотрите возможность консультации с "
        "медицинским специалистом для комплексной оценки",
        "recommendation_monitor_health": "Следите за показателями здоровья и рассмотрите "
        "возможность изменения образа жизни",
        "recommendation_maintain_habits": "Поддерживайте текущие здоровые привычки",
        # General
        "bmi_not_valid_during_pregnancy": "BMI не применим при беременности",
        "bmi_visualization_success": "Визуализация ИМТ создана успешно",
        "bmr_katch_note": "Использована формула Katch-McArdle (требует процент жира)",
        # BMI Engine Errors
        "bmi_engine_unavailable": "BMI engine недоступен",
        "bmi_calculation_failed": "Ошибка расчета BMI",
        "bmi_invalid_parameters": "Некорректные параметры для расчета BMI",
        # Soft Paywall
        "soft_paywall.title": "Более точная интерпретация",
        "soft_paywall.body": "BMI не учитывает распределение жира и контекст. Хотите более точную интерпретацию рисков (wellness)?",
        "soft_paywall.cta": "Открыть PRO",
        # Business Module
        "business_module_disabled": "Модуль бизнес-анализа отключен",
        "business_payload_too_large": "Слишком большой код (макс 100 KB)",
        "business_analysis_failed": (
            "Ошибка бизнес-анализа. Попробуйте снова или обратитесь в поддержку"
        ),
    },
    "en": {
        # BMI Categories
        "bmi_underweight": "Underweight",
        "bmi_normal": "Normal weight",
        "bmi_overweight": "Overweight",
        "bmi_obese_1": "Obese Class I",
        "bmi_obese_2": "Obese Class II",
        "bmi_obese_3": "Obese Class III",
        # BMI Visualization (dot-keys for contract)
        "bmi.underweight": "Underweight",
        "bmi.normal": "Normal",  # Short for scale label (not "Normal weight")
        "bmi.overweight": "Overweight",
        "bmi.obesity": "Obesity",
        # Activity Levels (English)
        "level_beginner": "Beginner",
        "level_novice": "Novice",
        "level_intermediate": "Intermediate",
        "level_advanced": "Advanced",
        "activity_sedentary": "Sedentary",
        "activity_light": "Light activity",
        "activity_moderate": "Moderate activity",
        "activity_active": "Active",
        "activity_very_active": "Very active",
        # Validation Errors
        "validation_weight_positive": "Weight must be a positive number",
        "validation_height_positive": "Height must be a positive number",
        "validation_age_range": "Age must be between 10 and 120 years",
        "validation_waist_positive": "Waist circumference must be a positive number",
        "validation_hip_positive": "Hip circumference must be a positive number",
        "validation_bodyfat_range": "Body fat percentage must be between 0 and 60",
        # Web Form Labels
        "form_weight": "Weight (kg)",
        "form_height": "Height (cm)",
        "form_age": "Age",
        "form_gender": "Gender",
        "form_pregnant": "Pregnant",
        "form_athlete": "Athlete",
        "form_waist": "Waist (cm)",
        "form_hip": "Hip (cm)",
        "form_bodyfat": "Body Fat %",
        # BMI Pro - Missing data notes
        "bmi_pro_whr_missing_hip": "WHR not computed: missing hip_cm. Risk assessment performed using BMI and WHtR only.",
        "form_calculate": "Calculate",
        "form_male": "Male",
        "form_female": "Female",
        "form_yes": "Yes",
        "form_no": "No",
        # Bodyfat API Response Labels
        "bodyfat_methods": "methods",
        "bodyfat_median": "median",
        "bodyfat_units_percent": "%",
        # Advice Texts
        "advice_underweight": "You should gain weight. Consult a doctor to "
        "develop a nutrition plan.",
        "advice_normal": "You have a normal weight. Continue maintaining a healthy lifestyle.",
        "advice_overweight": "You should lose weight. A balanced diet and "
        "physical activity are recommended.",
        "advice_obese": "You need to reduce your weight. Consult a doctor for "
        "advice and a weight loss plan.",
        "advice_athlete_bmi": "For athletes, BMI may overestimate body fat due to muscle mass",
        # Risk Assessment
        "risk_high_waist": "High waist-related risk",
        "risk_increased_waist": "Increased waist-related risk",
        "risk_high_whr": "WHR ≥ {threshold} for sex → additional risk.",
        "risk_high_bmi": "BMI ≥ 35: high overall risk.",
        "risk_moderate_bmi": "BMI 30–34.9: moderately increased risk.",
        "risk_high_central_fat": "High central fat (WHtR ≥ 0.6).",
        "risk_moderate_central_fat": "Increased central fat (WHtR ≥ 0.5).",
        "risk_low_health": "Low health risk",
        "risk_healthy_weight": "Healthy weight range",
        "risk_moderate_health": "Moderate health risk",
        "risk_high_health": "High health risk",
        "risk_high_android_shape": "High health risk (android/apple shape)",
        "risk_elderly_note": "In older adults, BMI can underestimate body fat (sarcopenia).",
        "risk_child_note": "Use BMI-for-age percentiles for youth.",
        "risk_teen_note": "Teenage years: consider pubertal development stage.",
        # BMI Pro Labels
        "bmi_pro_low_risk": "Low",
        "bmi_pro_moderate_risk": "Moderate",
        "bmi_pro_high_risk": "High",
        "bmi_pro_analysis_complete": "BMI Pro analysis complete",
        # BMI Pro Notes (risk factors and assessments)
        "bmi_pro_risk_factors": "Risk factors: {count}",
        "bmi_pro_wht_risk": "WHtR risk: {risk}",
        "bmi_pro_whr_risk": "WHR risk: {risk}",
        # Recommendations
        "recommendation_consult_healthcare": "Consider consulting with a healthcare "
        "professional for comprehensive assessment",
        "recommendation_consult_professional": "Consider consulting with a healthcare "
        "professional for comprehensive assessment",
        "recommendation_monitor_health": "Monitor health metrics and consider "
        "lifestyle modifications",
        "recommendation_maintain_habits": "Maintain current healthy habits",
        # General
        "bmi_not_valid_during_pregnancy": "BMI is not valid during pregnancy",
        "bmi_visualization_success": "BMI visualization generated successfully",
        "bmr_katch_note": "Using Katch-McArdle formula (requires body fat percentage)",
        # BMI Engine Errors
        "bmi_engine_unavailable": "BMI engine is not available",
        "bmi_calculation_failed": "BMI calculation failed",
        "bmi_invalid_parameters": "Invalid parameters for BMI calculation",
        # Soft Paywall
        "soft_paywall.title": "More accurate interpretation",
        "soft_paywall.body": "BMI doesn't account for fat distribution or context. Want a more accurate wellness interpretation?",
        "soft_paywall.cta": "See PRO",
        # Business Module
        "business_module_disabled": "Business analysis module is disabled",
        "business_payload_too_large": "Code payload too large (max 100 KB)",
        "business_analysis_failed": "Business analysis failed. Please try again or contact support",
    },
    "es": {
        # BMI Categories
        "bmi_underweight": "Bajo peso",
        "bmi_normal": "Peso normal",
        "bmi_overweight": "Sobrepeso",
        "bmi_obese_1": "Obesidad Clase I",
        "bmi_obese_2": "Obesidad Clase II",
        "bmi_obese_3": "Obesidad Clase III",
        # BMI Visualization (dot-keys for contract)
        "bmi.underweight": "Bajo peso",
        "bmi.normal": "Normal",
        "bmi.overweight": "Sobrepeso",
        "bmi.obesity": "Obesidad",
        # Activity Levels (Spanish)
        "level_beginner": "Principiante",
        "level_novice": "Novato",
        "level_intermediate": "Intermedio",
        "level_advanced": "Avanzado",
        # Validation Errors
        "validation_weight_positive": "El peso debe ser un número positivo",
        "validation_height_positive": "La altura debe ser un número positivo",
        "validation_age_range": "La edad debe estar entre 10 y 120 años",
        "validation_waist_positive": "La circunferencia de la cintura debe ser un número positivo",
        "validation_hip_positive": "La circunferencia de la cadera debe ser un número positivo",
        "validation_bodyfat_range": "El porcentaje de grasa corporal debe estar entre 0 y 60",
        # Web Form Labels
        "form_weight": "Peso (kg)",
        "form_height": "Altura (cm)",
        "form_age": "Edad",
        "form_gender": "Género",
        "form_pregnant": "Embarazada",
        "form_athlete": "Atleta",
        "form_waist": "Cintura (cm)",
        "form_hip": "Cadera (cm)",
        "form_bodyfat": "Grasa Corporal %",
        # BMI Pro - Missing data notes
        "bmi_pro_whr_missing_hip": "WHR no calculado: falta hip_cm. Evaluación de riesgo realizada solo con BMI y WHtR.",
        "form_calculate": "Calcular",
        "form_male": "Masculino",
        "form_female": "Femenino",
        "form_yes": "Sí",
        "form_no": "No",
        # Bodyfat API Response Labels
        "bodyfat_methods": "métodos",
        "bodyfat_median": "mediana",
        "bodyfat_units_percent": "%",
        # Advice Texts
        "advice_underweight": "Deberías ganar peso. Consulta con un médico para "
        "desarrollar un plan nutricional.",
        "advice_normal": "Tienes un peso normal. Sigue manteniendo un estilo de vida saludable.",
        "advice_overweight": "Deberías perder peso. Se recomienda una dieta "
        "equilibrada y actividad física.",
        "advice_obese": "Necesitas reducir tu peso. Consulta con un médico para "
        "obtener consejos y un plan de pérdida de peso.",
        "advice_athlete_bmi": "Para atletas, el IMC puede sobreestimar la grasa corporal",
        # Risk Assessment
        "risk_high_waist": "Alto riesgo relacionado con la cintura",
        "risk_increased_waist": "Riesgo aumentado relacionado con la cintura",
        "risk_high_whr": "CCR ≥ {threshold} para el sexo → riesgo adicional.",
        "risk_high_bmi": "IMC ≥ 35: alto riesgo general.",
        "risk_moderate_bmi": "IMC 30–34.9: riesgo moderadamente aumentado.",
        "risk_high_central_fat": "Alta grasa central (CCR ≥ 0.6).",
        "risk_moderate_central_fat": "Grasa central aumentada (CCR ≥ 0.5).",
        "risk_low_health": "Bajo riesgo para la salud",
        "risk_healthy_weight": "Rango de peso saludable",
        "risk_moderate_health": "Riesgo moderado para la salud",
        "risk_high_health": "Alto riesgo para la salud",
        "risk_high_android_shape": "Alto riesgo para la salud (forma androide/manzana)",
        "risk_elderly_note": "En adultos mayores, el IMC puede subestimar la grasa "
        "corporal (sarcopenia).",
        "risk_child_note": "Utilice percentiles de IMC para la edad en jóvenes.",
        "risk_teen_note": "Años adolescentes: considere la etapa de desarrollo puberal.",
        # BMI Pro Labels
        "bmi_pro_low_risk": "Bajo",
        "bmi_pro_moderate_risk": "Moderado",
        "bmi_pro_high_risk": "Alto",
        "bmi_pro_analysis_complete": "Análisis de IMC Pro completado",
        # BMI Pro Notes (risk factors and assessments)
        "bmi_pro_risk_factors": "Factores de riesgo: {count}",
        "bmi_pro_wht_risk": "Riesgo WHtR: {risk}",
        "bmi_pro_whr_risk": "Riesgo WHR: {risk}",
        # Recommendations
        "recommendation_consult_healthcare": "Considera consultar con un profesional "
        "de la salud para una evaluación completa",
        "recommendation_consult_professional": "Considera consultar con un profesional "
        "de la salud para una evaluación completa",
        "recommendation_monitor_health": "Monitorea los indicadores de salud y "
        "considera modificaciones en el estilo de vida",
        "recommendation_maintain_habits": "Mantén tus hábitos saludables actuales",
        "activity_sedentary": "Sedentario",
        "activity_light": "Actividad ligera",
        "activity_moderate": "Actividad moderada",
        "activity_active": "Activo",
        "activity_very_active": "Muy activo",
        # General
        "bmi_not_valid_during_pregnancy": "El IMC no es válido durante el embarazo",
        "bmi_visualization_success": "Visualización del IMC generada con éxito",
        "bmr_katch_note": "Usando fórmula Katch-McArdle (requiere porcentaje de grasa corporal)",
        # BMI Engine Errors
        "bmi_engine_unavailable": "El motor de IMC no está disponible",
        "bmi_calculation_failed": "Error en el cálculo del IMC",
        "bmi_invalid_parameters": "Parámetros inválidos para el cálculo del IMC",
        # Soft Paywall
        "soft_paywall.title": "Interpretación más precisa",
        "soft_paywall.body": "El IMC no tiene en cuenta la distribución de grasa ni el contexto. ¿Quieres una interpretación más precisa (bienestar)?",
        "soft_paywall.cta": "Abrir PRO",
        # Business Module
        "business_module_disabled": "Módulo de análisis empresarial está deshabilitado",
        "business_payload_too_large": "Código demasiado grande (máx 100 KB)",
        "business_analysis_failed": (
            "Error en análisis empresarial. Inténtelo de nuevo o contacte al soporte"
        ),
    },
}

# Type alias for language codes
Language = Literal["ru", "en", "es"]

# Backwards-compatible alias for internal use when normalizing
Lang = Language

# Configuration for locale special-case handling
# Each base language can have a default fallback and exception regions
LOCALE_SPECIAL_CASES: dict[str, dict[str, Any]] = {
    # English: Always maps to English (no exceptions needed)
    "en": {
        "default": "en",
        "exceptions": set(),  # All English regions → English
    },
    # Russian: Product goal - RU/ES/EN localization for iOS
    # ru-RU and ru → ru (not en)
    "ru": {
        "default": "ru",  # Changed: ru regions → ru (not en)
        "exceptions": set(),  # All Russian regions → Russian
    },
    # Spanish: Product goal - Spain priority (not Mexico-only)
    # es-ES and es → es (not en)
    "es": {
        "default": "es",  # Changed: es regions → es (not en)
        "exceptions": set(),  # All Spanish regions → Spanish
    },
}

# Aliases mapping for language normalization
#
# FALLBACK STRATEGY EXPLAINED:
# This is a market-based localization strategy, not purely linguistic.
#
# Current product goal: RU/ES/EN native localization for iOS.
#
# 1) ENGLISH MARKETS: All English locales (en, en-US, en-GB, …) → English
# 2) RUSSIAN MARKETS: All Russian locales (ru, ru-RU, ru-KZ, ru-BY, …) → Russian
# 3) SPANISH MARKETS: All Spanish locales (es, es-ES, es-MX, es-AR, …) → Spanish
#
# Implementation note:
# - Exact aliases are handled via LANG_ALIASES.
# - Implicit regional variants are handled via LOCALE_SPECIAL_CASES.
LANG_ALIASES: dict[str, Lang] = {
    # =================================================================
    # BASE LANGUAGES (core supported languages)
    # =================================================================
    "ru": "ru",
    "en": "en",
    "es": "es",
    # =================================================================
    # LANGUAGE NAME ALIASES (multilingual support)
    # =================================================================
    "russian": "ru",
    "english": "en",
    "spanish": "es",
    "español": "es",
    "русский": "ru",
    # =================================================================
    # LOCALE MAPPINGS (redundant - handled by LOCALE_SPECIAL_CASES)
    # =================================================================
    # Note: Regional locale mappings (ru-*, es-*, en-*) are handled by
    # LOCALE_SPECIAL_CASES in normalize_lang() Step 2, so explicit aliases
    # here are redundant. Removed to avoid "two sources of truth".
    # Behavior unchanged: ru-ru/es-*/en-* → handled by LOCALE_SPECIAL_CASES
}


def t(lang: Language, key: str, **kwargs: Any) -> str:  # noqa: ANN401
    """
    Translate a key to the specified language.

    Args:
        lang: Language code ("ru", "en", or "es")
        key: Translation key
        **kwargs: Optional formatting arguments

    Returns:
        Translated string

    Raises:
        KeyError: If the key is not found in the translations
    """
    if lang not in TRANSLATIONS:
        raise KeyError(f"Unsupported language: {lang}")

    translations = TRANSLATIONS[lang]
    if key not in translations:
        raise KeyError(f"Translation key '{key}' not found for language '{lang}'")

    template = translations[key]
    if kwargs:
        return template.format(**kwargs)
    return template


def validate_translation_key(key: str) -> bool:
    """
    Validate that a translation key exists in all languages.

    Args:
        key: Translation key to validate

    Returns:
        True if key exists in all languages, False otherwise
    """
    return all(key in translations for translations in TRANSLATIONS.values())


def normalize_lang(lang: Optional[str]) -> Lang:
    """
    Normalize input language code to supported languages ('ru'|'en'|'es').

    Uses a configurable market-based localization strategy where locale fallbacks
    are determined by business requirements defined in LOCALE_SPECIAL_CASES.

    Strategy:
    1. Check exact aliases from LANG_ALIASES first
    2. For unknown locales (xx-YY), apply configurable rules from LOCALE_SPECIAL_CASES:
       - Each base language has a default fallback and exception regions
       - If region is in exceptions → return base language
       - Otherwise → return configured default
    3. Unknown languages → English (default)

    Args:
        lang: Input language code (can be None, empty, or any format)

    Returns:
        Normalized language code: 'ru', 'en', or 'es'

    Examples:
        >>> normalize_lang("en-US")    # → "en" (en default)
        >>> normalize_lang("es-MX")    # → "es" (es default)
        >>> normalize_lang("es-ES")    # → "es" (es default, changed: not en)
        >>> normalize_lang("ru-RU")    # → "ru" (ru default, changed: not en)
        >>> normalize_lang("français") # → "en" (unsupported)
    """
    if not lang:
        return "en"

    key = lang.strip().lower().replace("_", "-")

    # Step 1: Check exact aliases first
    if key in LANG_ALIASES:
        return LANG_ALIASES[key]

    # Step 2: Handle unknown locales with configurable market-based rules
    if "-" in key:
        base, region = key.split("-", 1)

        # Normalize base and region to lowercase for consistent lookup
        base = base.lower()
        region = region.lower()

        # Apply locale special-case rules if base language has configuration
        if base in LOCALE_SPECIAL_CASES:
            config = LOCALE_SPECIAL_CASES[base]

            # If region is in exceptions, return the base language
            if region in config["exceptions"]:
                return base  # type: ignore[return-value]

            # Otherwise return the configured default
            return config["default"]  # type: ignore

    # Step 3: Check direct base languages
    if key in ("ru", "en", "es"):
        return key  # type: ignore[return-value]

    # Step 4: Default fallback for all unknown languages
    return "en"
