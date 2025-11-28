"""
Configuration module for Bayesian test analyzer recommendations.

Provides centralized, internationalizable recommendation messages for error types
and symptoms. Supports multiple languages with fallback to default (Russian).
"""

import os
from enum import Enum

# Default language (fallback) - configurable via BAYESIAN_DEFAULT_LANGUAGE env var
# Empty string in env var falls back to "ru" (prevents BAYESIAN_DEFAULT_LANGUAGE="" from breaking)
DEFAULT_LANGUAGE = os.getenv("BAYESIAN_DEFAULT_LANGUAGE") or "ru"

# Public API
__all__ = [
    "DEFAULT_LANGUAGE",
    "RECOMMENDATIONS",
    "get_recommendations",
    "get_error_type_key",
    "get_symptom_key",
    "get_all_error_type_keys",
    "get_all_symptom_keys",
]

# Recommendation messages organized by language and error type/symptom
RECOMMENDATIONS: dict[str, dict[str, list[str]]] = {
    "ru": {
        # Error type recommendations
        "error_type.assertion_error": [
            "Проверьте ожидаемые и фактические значения в assert",
            "Убедитесь, что моки настроены правильно",
            "Проверьте типы данных в сравнениях",
        ],
        "error_type.import_error": [
            "Проверьте правильность импортов",
            "Убедитесь, что все зависимости установлены",
            "Проверьте PYTHONPATH и sys.path",
        ],
        "error_type.type_error": [
            "Проверьте типы аргументов функций",
            "Убедитесь в правильности сигнатур методов",
            "Проверьте аннотации типов",
        ],
        "error_type.attribute_error": [
            "Проверьте существование атрибутов/методов",
            "Убедитесь, что объекты инициализированы правильно",
            "Проверьте правильность моков",
        ],
        "error_type.value_error": [
            "Проверьте диапазоны значений переменных",
            "Убедитесь в корректности входных данных",
            "Проверьте валидацию параметров",
        ],
        "error_type.runtime_error": [
            "Проверьте логику выполнения кода",
            "Убедитесь в корректности условий выполнения",
            "Проверьте обработку исключений",
        ],
        "error_type.timeout_error": [
            "Увеличьте таймаут для медленных операций",
            "Проверьте производительность кода",
            "Убедитесь, что нет бесконечных циклов",
        ],
        "error_type.coverage_error": [
            "Добавьте тесты для непокрытых ветвей кода",
            "Проверьте полноту тестового покрытия",
            "Убедитесь, что все важные сценарии протестированы",
        ],
        "error_type.mock_error": [
            "Проверьте правильность настройки моков",
            "Убедитесь, что патчи применяются в правильном порядке",
            "Проверьте, что моки не конфликтуют друг с другом",
        ],
        "error_type.async_error": [
            "Используйте AsyncMock для асинхронных методов",
            "Проверьте правильность await в тестах",
            "Убедитесь, что тесты помечены @pytest.mark.asyncio",
        ],
        # Symptom-based recommendations
        "symptom.async_context": [
            "Проверьте асинхронную логику теста",
        ],
        "symptom.mock_context": [
            "Пересмотрите настройку моков",
        ],
        "symptom.coverage_context": [
            "Добавьте тесты для непокрытых строк кода",
        ],
    },
    "en": {
        # Error type recommendations
        "error_type.assertion_error": [
            "Check expected and actual values in assert statements",
            "Ensure mocks are configured correctly",
            "Verify data types in comparisons",
        ],
        "error_type.import_error": [
            "Check import statements for correctness",
            "Ensure all dependencies are installed",
            "Verify PYTHONPATH and sys.path configuration",
        ],
        "error_type.type_error": [
            "Check function argument types",
            "Verify method signatures are correct",
            "Review type annotations",
        ],
        "error_type.attribute_error": [
            "Check existence of attributes/methods",
            "Ensure objects are initialized properly",
            "Verify mock configurations",
        ],
        "error_type.value_error": [
            "Check variable value ranges",
            "Ensure input data is valid",
            "Verify parameter validation",
        ],
        "error_type.runtime_error": [
            "Check code execution logic",
            "Verify execution conditions are correct",
            "Review exception handling",
        ],
        "error_type.timeout_error": [
            "Increase timeout for slow operations",
            "Check code performance",
            "Ensure there are no infinite loops",
        ],
        "error_type.coverage_error": [
            "Add tests for uncovered code branches",
            "Check test coverage completeness",
            "Ensure all important scenarios are tested",
        ],
        "error_type.mock_error": [
            "Check mock configuration correctness",
            "Ensure patches are applied in correct order",
            "Verify mocks don't conflict with each other",
        ],
        "error_type.async_error": [
            "Use AsyncMock for async methods",
            "Check await usage in tests",
            "Ensure tests are marked with @pytest.mark.asyncio",
        ],
        # Symptom-based recommendations
        "symptom.async_context": [
            "Review async test logic",
        ],
        "symptom.mock_context": [
            "Review mock configuration",
        ],
        "symptom.coverage_context": [
            "Add tests for uncovered code lines",
        ],
    },
    "es": {
        # Error type recommendations
        "error_type.assertion_error": [
            "Verifique los valores esperados y reales en assert",
            "Asegúrese de que los mocks estén configurados correctamente",
            "Verifique los tipos de datos en las comparaciones",
        ],
        "error_type.import_error": [
            "Verifique la corrección de las importaciones",
            "Asegúrese de que todas las dependencias estén instaladas",
            "Verifique PYTHONPATH y sys.path",
        ],
        "error_type.type_error": [
            "Verifique los tipos de argumentos de las funciones",
            "Asegúrese de que las firmas de métodos sean correctas",
            "Verifique las anotaciones de tipo",
        ],
        "error_type.attribute_error": [
            "Verifique la existencia de atributos/métodos",
            "Asegúrese de que los objetos estén inicializados correctamente",
            "Verifique la configuración de mocks",
        ],
        "error_type.value_error": [
            "Verifique los rangos de valores de las variables",
            "Asegúrese de que los datos de entrada sean válidos",
            "Verifique la validación de parámetros",
        ],
        "error_type.runtime_error": [
            "Verifique la lógica de ejecución del código",
            "Asegúrese de que las condiciones de ejecución sean correctas",
            "Revise el manejo de excepciones",
        ],
        "error_type.timeout_error": [
            "Aumente el tiempo de espera para operaciones lentas",
            "Verifique el rendimiento del código",
            "Asegúrese de que no haya bucles infinitos",
        ],
        "error_type.coverage_error": [
            "Agregue pruebas para ramas de código no cubiertas",
            "Verifique la integridad de la cobertura de pruebas",
            "Asegúrese de que todos los escenarios importantes estén probados",
        ],
        "error_type.mock_error": [
            "Verifique la corrección de la configuración de mocks",
            "Asegúrese de que los parches se apliquen en el orden correcto",
            "Verifique que los mocks no entren en conflicto entre sí",
        ],
        "error_type.async_error": [
            "Use AsyncMock para métodos asíncronos",
            "Verifique el uso de await en las pruebas",
            "Asegúrese de que las pruebas estén marcadas con @pytest.mark.asyncio",
        ],
        # Symptom-based recommendations
        "symptom.async_context": [
            "Revise la lógica asíncrona de la prueba",
        ],
        "symptom.mock_context": [
            "Revise la configuración de mocks",
        ],
        "symptom.coverage_context": [
            "Agregue pruebas para líneas de código no cubiertas",
        ],
    },
}


def get_recommendations(
    key: str, language: str | None = None, fallback: list[str] | None = None
) -> list[str]:
    """
    Get recommendations for a given key and language.

    Args:
        key: Recommendation key (e.g., "error_type.assertion_error" or "symptom.async_context")
        language: Language code (ru/en/es). Defaults to DEFAULT_LANGUAGE.
        fallback: Fallback recommendations if key not found. Defaults to empty list.

    Returns:
        List of recommendation strings.

    Examples:
        >>> get_recommendations("error_type.assertion_error", "en")
        ['Check expected and actual values in assert statements', ...]
        >>> get_recommendations("unknown_key", "ru", ["Default recommendation"])
        ['Default recommendation']
    """
    if language is None:
        language = DEFAULT_LANGUAGE

    # Validate language input against supported set
    if language not in RECOMMENDATIONS:
        language = DEFAULT_LANGUAGE

    if fallback is None:
        fallback = []

    # Try requested language
    lang_dict = RECOMMENDATIONS.get(language, {})
    recommendations = lang_dict.get(key, [])

    # Fallback to default language if not found
    if not recommendations and language != DEFAULT_LANGUAGE:
        default_dict = RECOMMENDATIONS.get(DEFAULT_LANGUAGE, {})
        recommendations = default_dict.get(key, [])

    # Use provided fallback if still empty
    if not recommendations:
        return list(fallback)
    return list(recommendations)


def get_error_type_key(error_type: Enum) -> str:
    """
    Convert ErrorType enum to recommendation key.

    Args:
        error_type: ErrorType enum value.

    Returns:
        Recommendation key string (e.g., "error_type.assertion_error").

    Raises:
        TypeError: If error_type is not an Enum instance with a .name attribute.
    """
    if not isinstance(error_type, Enum):
        raise TypeError(
            f"Expected Enum type for error_type, got {type(error_type).__name__}: {error_type!r}"
        )
    if not hasattr(error_type, "name"):
        raise TypeError(f"Enum instance {error_type!r} missing required 'name' attribute")
    error_name = error_type.name.lower()
    return f"error_type.{error_name}"


def get_symptom_key(symptom: str) -> str:
    """
    Convert symptom string to recommendation key.

    Args:
        symptom: Symptom string (e.g., "async_context").

    Returns:
        Recommendation key string (e.g., "symptom.async_context").
    """
    return f"symptom.{symptom}"


def get_all_error_type_keys() -> list[str]:
    """
    Get all error type recommendation keys.

    Returns:
        List of all error type keys.
    """
    lang_dict = RECOMMENDATIONS.get(DEFAULT_LANGUAGE, {})
    return [key for key in lang_dict.keys() if key.startswith("error_type.")]


def get_all_symptom_keys() -> list[str]:
    """
    Get all symptom recommendation keys.

    Returns:
        List of all symptom keys.
    """
    lang_dict = RECOMMENDATIONS.get(DEFAULT_LANGUAGE, {})
    return [key for key in lang_dict.keys() if key.startswith("symptom.")]
