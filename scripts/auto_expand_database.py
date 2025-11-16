#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to automatically expand the product database.

This utility analyzes recipes, finds missing products, and automatically adds
them to the database from free/open sources.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the import path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.product_finder import ProductFinder
from core.recipe_db import parse_recipe_db

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main function for automatic database expansion."""
    logger.info("🚀 Starting automatic database expansion")

    try:
        # Initialize the product finder
        finder = ProductFinder()
        logger.info("✅ Product finder initialized")

        # Load recipes (food_db not required when only parsing ingredients)
        recipes = parse_recipe_db("data/recipes_extended.csv")
        logger.info(f"📚 Loaded {len(recipes)} recipes")

        # Collect all ingredients from recipes
        all_ingredients: list[str] = []
        for recipe in recipes.values():
            all_ingredients.extend(recipe.ingredients.keys())

        logger.info(f"🥘 Found {len(all_ingredients)} unique ingredients")

        # Find missing products
        missing_products = finder.find_missing_products(all_ingredients)
        logger.info(f"❌ Found {len(missing_products)} missing products")

        if not missing_products:
            logger.info("🎉 All products are already in the database!")
            return

        # Display missing products
        logger.info("📋 Missing products:")
        for i, product in enumerate(missing_products, 1):
            logger.info(f"  {i}. {product}")

        # Start automatic expansion
        logger.info("🔍 Starting product search and addition…")
        results = finder.auto_expand_database(all_ingredients)

        # Display results
        logger.info("📊 Expansion results:")
        successful = 0
        failed = 0

        for product, success in results.items():
            if success:
                logger.info(f"  ✅ {product} - Added successfully")
                successful += 1
            else:
                logger.info(f"  ❌ {product} - Failed to add")
                failed += 1

        logger.info(f"📈 Summary: {successful} successful, {failed} failed")

        # Show database statistics
        updated_food_db = finder.food_db
        logger.info(f"📊 Database now contains {len(updated_food_db)} products")

        logger.info("🎉 Automatic database expansion completed!")

    except Exception as e:
        logger.error(f"💥 Error during database expansion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
