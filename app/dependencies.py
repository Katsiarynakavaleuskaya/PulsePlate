import logging
import os

from core.recipe_synth import RecipeSynthesizer
from core.recipe_synth import get_recipe_synthesizer as get_synth

# Read environment variable once at module load
TEMPLATE_DIR: str = os.getenv("RECIPE_TEMPLATES_DIR", "data/recipe_templates")

logger = logging.getLogger(__name__)


def validate_template_dir() -> None:
    """Validate TEMPLATE_DIR at application startup.

    RU: Проверяет существование и корректность директории шаблонов рецептов при старте приложения.
    EN: Validates existence and correctness of recipe templates directory at application startup.

    Raises:
        RuntimeError: If TEMPLATE_DIR does not exist or is not a directory.

    Note:
        Callers may convert RuntimeError to SystemExit if process exit behavior is desired.

    Note:
        This function should be called during FastAPI startup lifecycle to fail fast
        on misconfiguration rather than raising errors during request handling.
    """
    if not os.path.exists(TEMPLATE_DIR):
        error_msg = (
            f"Recipe templates directory does not exist: {TEMPLATE_DIR}. "
            f"Please check the RECIPE_TEMPLATES_DIR environment variable."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    if not os.path.isdir(TEMPLATE_DIR):
        error_msg = (
            f"Recipe templates path is not a directory: {TEMPLATE_DIR}. "
            f"Please check the RECIPE_TEMPLATES_DIR environment variable."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    logger.info(f"Recipe templates directory validated: {TEMPLATE_DIR}")


def get_recipe_synthesizer() -> RecipeSynthesizer:
    """FastAPI-friendly provider for RecipeSynthesizer.

    RU: Делегирует в модуль-level singleton для консистентности состояния.
    EN: Delegates to module-level singleton for consistent state.

    Returns:
        RecipeSynthesizer: Singleton instance from core.recipe_synth

    Note:
        TEMPLATE_DIR validation is performed at application startup via validate_template_dir().
        This function assumes the directory is valid and will not perform runtime checks.
        Return type annotation is explicit and RecipeSynthesizer is imported
        from core.recipe_synth, ensuring full type checker resolution.
        If parameters are added in the future, they should include explicit
        type hints to maintain consistency with project type annotation guidelines.
    """
    return get_synth(templates_dir=TEMPLATE_DIR)
