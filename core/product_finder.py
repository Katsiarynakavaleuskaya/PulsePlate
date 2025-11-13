# -*- coding: utf-8 -*-
"""
RU: Система автоматического поиска и добавления недостающих продуктов.
EN: Automatic product search and addition system.

Этот модуль предоставляет функциональность для поиска недостающих продуктов
в бесплатных источниках данных и автоматического добавления их в базу данных.
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .food_db import FoodItem, parse_food_db
from .food_sources.base import BaseAdapter, FoodRecord
from .food_sources.off import OFFAdapter
from .food_sources.usda import USDAAdapter

logger = logging.getLogger(__name__)

# Try to import fuzzy matching libraries (optional)
try:
    from rapidfuzz import fuzz

    _FUZZY_AVAILABLE = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz

        _FUZZY_AVAILABLE = True
    except ImportError:
        _FUZZY_AVAILABLE = False

# Try to import NLTK for lemmatization (optional)
try:
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from nltk import download as nltk_download

    _NLTK_AVAILABLE = True
    try:
        _stopwords = set(stopwords.words("english"))
        _lemmatizer = WordNetLemmatizer()
    except (LookupError, OSError):
        # NLTK data not downloaded, try to download it
        try:
            nltk_download("stopwords", quiet=True)
            nltk_download("wordnet", quiet=True)
            nltk_download("omw-1.4", quiet=True)
            _stopwords = set(stopwords.words("english"))
            _lemmatizer = WordNetLemmatizer()
        except Exception:
            _NLTK_AVAILABLE = False
            _stopwords = set()
            _lemmatizer = None
except ImportError:
    _NLTK_AVAILABLE = False
    _stopwords = set()
    _lemmatizer = None

# Common English stopwords/articles as fallback
_COMMON_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "was",
    "are",
    "were",
    "been",
    "be",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "must",
    "can",
    "this",
    "that",
    "these",
    "those",
}

# Default similarity threshold (0-100)
_DEFAULT_SIMILARITY_THRESHOLD = 70


# Shared CSV schema for food DB rows
FIELDNAMES: List[str] = [
    "name",
    "unit_per",
    "unit",
    "protein_g",
    "fat_g",
    "carbs_g",
    "fiber_g",
    "Fe_mg",
    "Ca_mg",
    "VitD_IU",
    "B12_ug",
    "Folate_ug",
    "Iodine_ug",
    "K_mg",
    "Mg_mg",
    "price_per_unit",
    "flags",
]


@dataclass
class ProductSearchResult:
    """
    RU: Результат поиска продукта.
    EN: Product search result.
    """

    product_name: str
    found: bool
    source: Optional[str] = None
    food_record: Optional[FoodRecord] = None
    confidence: float = 0.0
    error_message: Optional[str] = None


class ProductFinder:
    """
    RU: Класс для поиска недостающих продуктов в различных источниках.
    EN: Class for finding missing products in various sources.
    """

    DEFAULT_MIN_CONFIDENCE_THRESHOLD = 0.3

    def __init__(self, min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE_THRESHOLD) -> None:
        """
        Initialize the product finder.

        Args:
            min_confidence_threshold: Minimum confidence threshold for product matching
                (default: DEFAULT_MIN_CONFIDENCE_THRESHOLD)
        """
        # Validate threshold early to prevent invalid configuration from propagating.
        # RU: Ранняя проверка порога уверенности (0.0–1.0), принимаются только числа.
        if not isinstance(min_confidence_threshold, (int, float)):
            raise ValueError("min_confidence_threshold must be a numeric value within [0.0, 1.0]")
        threshold_value = float(min_confidence_threshold)
        if threshold_value < 0.0 or threshold_value > 1.0:
            raise ValueError(
                "min_confidence_threshold must be within the inclusive range [0.0, 1.0]"
            )

        self.min_confidence_threshold = threshold_value
        self.usda_adapter = USDAAdapter()
        self.off_adapter = OFFAdapter()
        self.food_db = parse_food_db("data/food_db.csv")

    def find_missing_products(self, recipe_ingredients: List[str]) -> List[str]:
        """
        RU: Найти продукты, которые отсутствуют в базе данных.
        EN: Find products that are missing from the database.

        Args:
            recipe_ingredients: Список ингредиентов из рецептов

        Returns:
            Список недостающих продуктов
        """
        missing_products = []
        food_names = {food.name.lower() for food in self.food_db.values()}

        for ingredient in recipe_ingredients:
            found = False
            for food_name in food_names:
                if (
                    ingredient.lower() in food_name
                    or food_name in ingredient.lower()
                    or self._similar_names(ingredient, food_name)
                ):
                    found = True
                    break

            if not found:
                missing_products.append(ingredient)

        return missing_products

    def similar_names(self, name1: str, name2: str) -> bool:
        """
        RU: Проверить, похожи ли названия продуктов.
        EN: Check if product names are similar.

        Args:
            name1: Первое название
            name2: Второе название

        Returns:
            True, если названия похожи
        """
        return self._similar_names(name1, name2)

    def _normalize_name(self, name: str) -> str:
        """
        RU: Нормализовать название продукта для сравнения.
        EN: Normalize product name for comparison.

        Args:
            name: Исходное название

        Returns:
            Нормализованное название
        """
        if not name:
            return ""

        # Lowercase
        normalized = name.lower()

        # Remove punctuation and collapse whitespace
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = normalized.strip()

        return normalized

    def _remove_stopwords(self, text: str) -> str:
        """
        RU: Удалить стоп-слова из текста.
        EN: Remove stopwords from text.

        Args:
            text: Исходный текст

        Returns:
            Текст без стоп-слов
        """
        words = text.split()
        # Use NLTK stopwords if available, otherwise use common stopwords
        stopword_set = _stopwords if _NLTK_AVAILABLE and _stopwords else _COMMON_STOPWORDS
        filtered_words = [w for w in words if w not in stopword_set]
        return " ".join(filtered_words)

    def _lemmatize_text(self, text: str) -> str:
        """
        RU: Лемматизировать текст (привести слова к базовой форме).
        EN: Lemmatize text (convert words to base form).

        Args:
            text: Исходный текст

        Returns:
            Лемматизированный текст
        """
        if not _NLTK_AVAILABLE or _lemmatizer is None:
            return text  # Fallback: return as-is

        words = text.split()
        lemmatized_words = []
        for word in words:
            # Try noun first (most common for product names), then verb, adjective, adverb
            lemmatized = _lemmatizer.lemmatize(word, pos="n")  # Default to noun
            # If lemmatization changed the word, use it; otherwise try other POS
            if lemmatized != word:
                lemmatized_words.append(lemmatized)
            else:
                # Try other parts of speech
                for pos in ["v", "a", "r"]:
                    lemmatized = _lemmatizer.lemmatize(word, pos=pos)
                    if lemmatized != word:
                        lemmatized_words.append(lemmatized)
                        break
                else:
                    # No change with any POS, keep original
                    lemmatized_words.append(word)

        return " ".join(lemmatized_words)

    def _similar_names(
        self, name1: str, name2: str, threshold: int = _DEFAULT_SIMILARITY_THRESHOLD
    ) -> bool:
        """
        RU: Проверить, похожи ли названия продуктов (внутренняя реализация).
        EN: Check if product names are similar (internal implementation).

        Uses fuzzy matching with normalization, stopword removal, and lemmatization.
        Falls back to substring/word intersection if fuzzy libraries unavailable.

        Args:
            name1: Первое название
            name2: Второе название
            threshold: Порог схожести (0-100), по умолчанию 70

        Returns:
            True, если названия похожи
        """
        if not name1 or not name2:
            return False

        # Normalize names
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        if not norm1 or not norm2:
            return False

        # Exact match after normalization
        if norm1 == norm2:
            return True

        # Remove stopwords
        norm1_no_stop = self._remove_stopwords(norm1)
        norm2_no_stop = self._remove_stopwords(norm2)

        # Lemmatize
        norm1_lemma = self._lemmatize_text(norm1_no_stop)
        norm2_lemma = self._lemmatize_text(norm2_no_stop)

        # Try fuzzy matching if available
        if _FUZZY_AVAILABLE:
            try:
                # Use token_set_ratio for better handling of word order differences
                similarity = fuzz.token_set_ratio(norm1_lemma, norm2_lemma)
                if similarity >= threshold:
                    return True

                # Also try partial_ratio for substring matches
                partial_similarity = fuzz.partial_ratio(norm1_lemma, norm2_lemma)
                if partial_similarity >= threshold:
                    return True

                # Try ratio for overall similarity
                ratio_similarity = fuzz.ratio(norm1_lemma, norm2_lemma)
                if ratio_similarity >= threshold:
                    return True
            except Exception as e:
                logger.debug(f"Fuzzy matching failed: {e}, falling back to simple matching")

        # Fallback: lightweight substring/word intersection logic
        # Check substring containment
        norm1_clean = norm1_lemma.replace(" ", "").replace("_", "")
        norm2_clean = norm2_lemma.replace(" ", "").replace("_", "")
        if norm1_clean in norm2_clean or norm2_clean in norm1_clean:
            return True

        # Check common words
        words1 = set(norm1_lemma.split())
        words2 = set(norm2_lemma.split())
        common_words = words1.intersection(words2)

        # If significant overlap (at least 50% of shorter name's words), consider similar
        if common_words:
            min_len = min(len(words1), len(words2))
            if min_len > 0 and len(common_words) / min_len >= 0.5:
                return True

        return False

    def search_product(self, product_name: str) -> ProductSearchResult:
        """
        RU: Поиск продукта в различных источниках.
        EN: Search for a product in various sources.

        Args:
            product_name: Название продукта для поиска

        Returns:
            Результат поиска
        """
        logger.info(f"Searching for product: {product_name}")

        # Сначала пробуем USDA
        try:
            usda_result = self._search_in_usda(product_name)
            if usda_result.found:
                return usda_result
        except Exception as e:
            logger.warning(f"USDA search failed for {product_name}: {e}")

        # Затем пробуем Open Food Facts
        try:
            off_result = self._search_in_off(product_name)
            if off_result.found:
                return off_result
        except Exception as e:
            logger.warning(f"OFF search failed for {product_name}: {e}")

        # Если ничего не найдено, возвращаем отрицательный результат
        return ProductSearchResult(
            product_name=product_name,
            found=False,
            error_message="Product not found in any source",
        )

    def _search_in_source(
        self, product_name: str, adapter: BaseAdapter, source_name: str
    ) -> ProductSearchResult:
        """
        RU: Поиск продукта в указанном источнике данных.
        EN: Search for product in specified data source.

        Args:
            product_name: Название продукта для поиска
            adapter: Адаптер источника данных (USDA или OFF)
            source_name: Имя источника для логирования и результата

        Returns:
            Результат поиска
        """
        try:
            # Получаем все продукты из источника
            foods = adapter.normalize()

            # Ищем наиболее подходящий продукт
            best_match = None
            best_confidence = 0.0

            for food in foods:
                confidence = self._calculate_confidence(product_name, food.name)
                if confidence > best_confidence and confidence > self.min_confidence_threshold:
                    best_match = food
                    best_confidence = confidence

            if best_match:
                return ProductSearchResult(
                    product_name=product_name,
                    found=True,
                    source=source_name,
                    food_record=best_match,
                    confidence=best_confidence,
                )

        except Exception as e:
            logger.error(f"Error searching in {source_name}: {e}")

        return ProductSearchResult(
            product_name=product_name,
            found=False,
            error_message=f"{source_name} search failed",
        )

    def _search_in_usda(self, product_name: str) -> ProductSearchResult:
        """
        RU: Поиск продукта в USDA базе данных.
        EN: Search for product in USDA database.

        Args:
            product_name: Название продукта

        Returns:
            Результат поиска
        """
        return self._search_in_source(product_name, self.usda_adapter, "USDA")

    def _search_in_off(self, product_name: str) -> ProductSearchResult:
        """
        RU: Поиск продукта в Open Food Facts.
        EN: Search for product in Open Food Facts.

        Args:
            product_name: Название продукта

        Returns:
            Результат поиска
        """
        return self._search_in_source(product_name, self.off_adapter, "OFF")

    def _calculate_confidence(self, search_name: str, found_name: str) -> float:
        """
        RU: Вычислить уверенность в совпадении названий.
        EN: Calculate confidence in name matching.

        Args:
            search_name: Искомое название
            found_name: Найденное название

        Returns:
            Уровень уверенности от 0.0 до 1.0
        """
        search_clean = search_name.lower().replace(" ", "").replace("_", "")
        found_clean = found_name.lower().replace(" ", "").replace("_", "")

        # Точное совпадение
        if search_clean == found_clean:
            return 1.0

        # Одно название содержит другое
        if search_clean in found_clean or found_clean in search_clean:
            return 0.8

        # Проверяем общие слова
        search_words = set(search_name.lower().split())
        found_words = set(found_name.lower().split())
        common_words = search_words.intersection(found_words)

        if common_words:
            return len(common_words) / max(len(search_words), len(found_words))

        return 0.0

    def add_product_to_database(self, search_result: ProductSearchResult) -> bool:
        """
        RU: Добавить найденный продукт в базу данных.
        EN: Add found product to database.

        Args:
            search_result: Результат поиска продукта

        Returns:
            True, если продукт успешно добавлен
        """
        if not search_result.found or not search_result.food_record:
            return False

        try:
            # Конвертируем FoodRecord в FoodItem
            food_item = self._convert_to_food_item(
                search_result.food_record, search_result.product_name
            )

            # Добавляем в базу данных
            self._append_to_food_db(food_item)

            logger.info(f"Successfully added {search_result.product_name} to database")
            return True

        except Exception as e:
            logger.error(f"Failed to add {search_result.product_name}: {e}")
            return False

    def _convert_to_food_item(self, food_record: FoodRecord, product_name: str) -> FoodItem:
        """
        RU: Конвертировать FoodRecord в FoodItem.
        EN: Convert FoodRecord to FoodItem.

        Args:
            food_record: Запись о продукте
            product_name: Название продукта

        Returns:
            FoodItem объект
        """
        return FoodItem(
            name=product_name,
            unit_per=100,
            unit="g",
            protein_g=food_record.protein_g,
            fat_g=food_record.fat_g,
            carbs_g=food_record.carbs_g,
            fiber_g=food_record.fiber_g,
            Fe_mg=food_record.Fe_mg,
            Ca_mg=food_record.Ca_mg,
            VitD_IU=food_record.VitD_IU,
            B12_ug=food_record.B12_ug,
            Folate_ug=food_record.Folate_ug,
            Iodine_ug=food_record.Iodine_ug,
            K_mg=food_record.K_mg,
            Mg_mg=food_record.Mg_mg,
            price_per_unit=0.0,  # По умолчанию
            flags=set(),  # По умолчанию
        )

    def _append_to_food_db(self, food_item: FoodItem) -> None:
        """
        RU: Добавить продукт в файл базы данных.
        EN: Add product to food database file.

        Args:
            food_item: Продукт для добавления
        """
        db_path = Path("data/food_db.csv")

        # Determine if we need to write header: file missing or empty
        need_header = (not db_path.exists()) or (db_path.exists() and db_path.stat().st_size == 0)

        with open(db_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            if need_header:
                writer.writeheader()
            writer.writerow(self._as_row(food_item))

    def auto_expand_database(self, recipe_ingredients: List[str]) -> Dict[str, bool]:
        """
        RU: Автоматически расширить базу данных недостающими продуктами.
        EN: Automatically expand database with missing products.

        Args:
            recipe_ingredients: Список ингредиентов из рецептов

        Returns:
            Словарь с результатами добавления продуктов
        """
        logger.info("Starting automatic database expansion")

        # Находим недостающие продукты
        missing_products = self.find_missing_products(recipe_ingredients)
        logger.info(f"Found {len(missing_products)} missing products")

        results = {}

        for product in missing_products:
            logger.info(f"Processing product: {product}")

            # Ищем продукт
            search_result = self.search_product(product)

            if search_result.found:
                # Добавляем в базу данных
                success = self.add_product_to_database(search_result)
                results[product] = success

                if success:
                    logger.info(f"✅ Successfully added {product}")
                else:
                    logger.error(f"❌ Failed to add {product}")
            else:
                logger.warning(f"⚠️ Product not found: {product}")
                results[product] = False

        logger.info("Automatic database expansion completed")
        return results

    def expand_database(self, products: List[str], csv_path: str) -> Dict[str, bool]:
        """
        RU: Расширить базу данных указанными продуктами и записать/добавить их в CSV.
        EN: Expand the database with provided products and write/append them into a CSV.

        Args:
            products: Список названий продуктов для поиска и добавления
            csv_path: Путь к CSV файлу, куда записывать продукты

        Returns:
            Словарь {product_name: success}
        """
        results: Dict[str, bool] = {}

        # Ensure the directory exists (if any)
        try:
            Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            # Best-effort; writing the file below will surface any errors
            logger.warning("Unable to prepare directory for %s: %s", csv_path, exc)

        # Determine if we need to write header: file missing or empty
        csv_path_obj = Path(csv_path)
        need_header = not csv_path_obj.exists() or (
            csv_path_obj.exists() and csv_path_obj.stat().st_size == 0
        )

        # Open file in append mode; write header if new or empty file
        with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            if need_header:
                writer.writeheader()

            for product in products:
                try:
                    search_result = self.search_product(product)
                    if search_result.found and search_result.food_record:
                        # Convert and write a row
                        food_item = self._convert_to_food_item(search_result.food_record, product)
                        writer.writerow(self._as_row(food_item))
                        results[product] = True
                        logger.info(f"Added product to CSV: {product}")
                    else:
                        results[product] = False
                        logger.warning(f"Product not found and was not added: {product}")
                except Exception as e:
                    # On any error for a single product, mark as False and continue
                    results[product] = False
                    logger.warning(f"Failed to process product '{product}': {e}")

        return results

    def _as_row(self, food_item: FoodItem) -> Dict[str, str | float | int]:
        """Map FoodItem to CSV row using shared FIELDNAMES order."""
        return {
            "name": food_item.name,
            "unit_per": food_item.unit_per,
            "unit": food_item.unit,
            "protein_g": food_item.protein_g,
            "fat_g": food_item.fat_g,
            "carbs_g": food_item.carbs_g,
            "fiber_g": food_item.fiber_g,
            "Fe_mg": food_item.Fe_mg,
            "Ca_mg": food_item.Ca_mg,
            "VitD_IU": food_item.VitD_IU,
            "B12_ug": food_item.B12_ug,
            "Folate_ug": food_item.Folate_ug,
            "Iodine_ug": food_item.Iodine_ug,
            "K_mg": food_item.K_mg,
            "Mg_mg": food_item.Mg_mg,
            "price_per_unit": food_item.price_per_unit,
            "flags": ",".join(sorted(food_item.flags)) if food_item.flags else "",
        }
