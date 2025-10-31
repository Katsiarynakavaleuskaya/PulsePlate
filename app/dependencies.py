from functools import lru_cache

from core.recipe_synth import RecipeSynthesizer


@lru_cache(maxsize=1)
def get_recipe_synthesizer() -> RecipeSynthesizer:
    """FastAPI-friendly provider for RecipeSynthesizer.

    RU: Кэшируемый провайдер для инъекции зависимости в FastAPI.
    EN: Cached provider for dependency injection in FastAPI.
    """
    return RecipeSynthesizer()
