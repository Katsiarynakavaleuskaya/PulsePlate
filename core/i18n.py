"""
Internationalization (i18n) module for the BMI App.

Provides translation dictionaries and functions for RU/EN/ES localization.
"""

from typing import Any, Literal

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
        "form_calculate": "Рассчитать",
        "form_male": "Мужской",
        "form_female": "Женский",
        "form_yes": "Да",
        "form_no": "Нет",

        # Advice Texts
        "advice_underweight": "Вам следует набрать вес. Проконсультируйтесь с врачом "
                          "для составления плана питания.",
        "advice_normal": "У вас нормальный вес. Продолжайте поддерживать здоровый "
                     "образ жизни.",
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

        # Recommendations
        "recommendation_consult_healthcare": "Рассмотрите возможность консультации с "
                                         "медицинским специалистом для комплексной оценки",
        "recommendation_monitor_health": "Следите за показателями здоровья и рассмотрите "
                                     "возможность изменения образа жизни",
        "recommendation_maintain_habits": "Поддерживайте текущие здоровые привычки",

        # Levels
        "level_advanced": "продвинутый",
        "level_intermediate": "средний",
        "level_novice": "начальный",
        "level_beginner": "базовый",

        # General
        "bmi_not_valid_during_pregnancy": "BMI не применим при беременности",
        "bmi_visualization_success": "Визуализация ИМТ создана успешно",
    },
    "en": {
        # BMI Categories
        "bmi_underweight": "Underweight",
        "bmi_normal": "Normal weight",
        "bmi_overweight": "Overweight",
        "bmi_obese_1": "Obese Class I",
        "bmi_obese_2": "Obese Class II",
        "bmi_obese_3": "Obese Class III",

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
        "form_calculate": "Calculate",
        "form_male": "Male",
        "form_female": "Female",
        "form_yes": "Yes",
        "form_no": "No",

        # Advice Texts
        "advice_underweight": "You should gain weight. Consult a doctor to "
                          "develop a nutrition plan.",
        "advice_normal": "You have a normal weight. Continue maintaining a "
                     "healthy lifestyle.",
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

        # Recommendations
        "recommendation_consult_healthcare": "Consider consulting with a healthcare "
                                         "professional for comprehensive assessment",
        "recommendation_monitor_health": "Monitor health metrics and consider "
                                     "lifestyle modifications",
        "recommendation_maintain_habits": "Maintain current healthy habits",

        # Levels
        "level_advanced": "advanced",
        "level_intermediate": "intermediate",
        "level_novice": "novice",
        "level_beginner": "beginner",

        # General
        "bmi_not_valid_during_pregnancy": "BMI is not valid during pregnancy",
        "bmi_visualization_success": "BMI visualization generated successfully",
    },
    "es": {
        # BMI Categories
        "bmi_underweight": "Bajo peso",
        "bmi_normal": "Peso normal",
        "bmi_overweight": "Sobrepeso",
        "bmi_obese_1": "Obesidad Clase I",
        "bmi_obese_2": "Obesidad Clase II",
        "bmi_obese_3": "Obesidad Clase III",

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
        "form_calculate": "Calcular",
        "form_male": "Masculino",
        "form_female": "Femenino",
        "form_yes": "Sí",
        "form_no": "No",

        # Advice Texts
        "advice_underweight": "Deberías ganar peso. Consulta con un médico para "
                          "desarrollar un plan nutricional.",
        "advice_normal": "Tienes un peso normal. Sigue manteniendo un estilo de "
                     "vida saludable.",
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

        # Recommendations
        "recommendation_consult_healthcare": "Considera consultar con un profesional "
                                         "de la salud para una evaluación completa",
        "recommendation_monitor_health": "Monitorea los indicadores de salud y "
                                     "considera modificaciones en el estilo de vida",
        "recommendation_maintain_habits": "Mantén tus hábitos saludables actuales",

        # Levels
        "level_advanced": "avanzado",
        "level_intermediate": "intermedio",
        "level_novice": "novato",
        "level_beginner": "principiante",

        # General
        "bmi_not_valid_during_pregnancy": "El IMC no es válido durante el embarazo",
        "bmi_visualization_success": "Visualización del IMC generada con éxito",
    }
}

# Type alias for language codes
Language = Literal["ru", "en", "es"]


def t(lang: Language, key: str, **kwargs: Any) -> str:
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
