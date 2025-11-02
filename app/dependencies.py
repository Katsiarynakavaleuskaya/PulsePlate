import os
from functools import lru_cache

from core.recipe_synth import RecipeSynthesizer

# Read environment variable once at module load
TEMPLATE_DIR = os.getenv("RECIPE_TEMPLATES_DIR", "data/recipe_templates")


@lru_cache(maxsize=1)
def get_recipe_synthesizer() -> RecipeSynthesizer:
    """FastAPI-friendly provider for RecipeSynthesizer.

    RU: Кэшируемый провайдер для инъекции зависимости в FastAPI.
    EN: Cached provider for dependency injection in FastAPI.
    """
    return RecipeSynthesizer(templates_dir=TEMPLATE_DIR)
