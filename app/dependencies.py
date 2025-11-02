import os

from core.recipe_synth import RecipeSynthesizer, get_recipe_synthesizer as get_synth

# Read environment variable once at module load
TEMPLATE_DIR = os.getenv("RECIPE_TEMPLATES_DIR", "data/recipe_templates")


def get_recipe_synthesizer() -> RecipeSynthesizer:
    """FastAPI-friendly provider for RecipeSynthesizer.

    RU: Делегирует в модуль-level singleton для консистентности состояния.
    EN: Delegates to module-level singleton for consistent state.

    Returns:
        RecipeSynthesizer: Singleton instance from core.recipe_synth
    """
    return get_synth(templates_dir=TEMPLATE_DIR)
