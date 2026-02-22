"""Re-export OFFClient as OpenFoodFactsClient under the test-expected path.

RU: Реэкспорт OFFClient как OpenFoodFactsClient.
EN: ``from core.food_apis.openfoodfacts import OpenFoodFactsClient`` works after this module.
"""

from __future__ import annotations

from .openfoodfacts_client import OFFClient as OpenFoodFactsClient

__all__ = ["OpenFoodFactsClient"]
