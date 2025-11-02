# -*- coding: utf-8 -*-
"""FoodDB access service with FTS and alias expansion.

RU: Сервис доступа к FoodDB (SQLite) с FTS и алиасами.
EN: Access to FoodDB (SQLite) with FTS and alias expansion.
"""

import csv
import sqlite3
from pathlib import Path
import logging
import os
from typing import Any, Dict, List, Optional, Mapping, Sequence, Tuple
import threading

# Initialize logger early for setup-time logging
logger = logging.getLogger(__name__)

# DB path can be overridden via env var FOOD_DB_PATH; defaults to data/food.sqlite
_env_db_path = os.getenv("FOOD_DB_PATH")
DB_PATH: Path = Path(_env_db_path) if _env_db_path else Path("data/food.sqlite")

# Early validation: warn if FOOD_DB_PATH was provided but parent directory doesn't exist
if _env_db_path and not DB_PATH.parent.exists():
    logger.warning("FOOD_DB_PATH provided but parent directory does not exist: %s", DB_PATH.parent)

# Ensure parent directory exists for the SQLite file (create parents as necessary)
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception as exc:  # pragma: no cover - extremely rare filesystem errors
    # Non-fatal: log at debug to avoid noisy logs in production
    logger.debug("Unable to create DB directory %s: %s", DB_PATH.parent, exc)
ALIASES_CSV_PATH: Path = Path(os.getenv("FOOD_ALIASES_CSV", "data/food_aliases.csv"))
MAX_LIMIT: int = 100
DEFAULT_PER_G: float = 100.0

DEFAULT_ALIASES: Dict[str, List[str]] = {
    # RU/EN/ES базовые соответствия; расширяй из своего alias CSV
    "йогурт": ["yogurt", "yoghurt"],
    "масло оливковое": ["olive oil", "aceite de oliva"],
    "творог": ["cottage cheese", "queso cottage"],
}


def _safe_float(value: Any) -> float:
    """Best-effort float conversion; returns 0.0 on None/non-numeric.

    RU: Безопасное приведение к float; возвращает 0.0 для None/нечисловых значений.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _validate_csv_quotes(csv_path: Path, is_production: bool) -> bool:
    """
    Validate CSV file for balanced quotes.

    RU: Проверяет CSV файл на сбалансированные кавычки.
    EN: Validates CSV file for balanced quotes.

    Args:
        csv_path: Path to the CSV file to validate
        is_production: Whether running in production mode

    Returns:
        True if quotes are balanced, False otherwise

    Raises:
        csv.Error: In non-production mode if quotes are unbalanced
    """
    # Python's csv module is lenient, so we check manually for common issues
    with open(csv_path, "r", encoding="utf-8") as validation_f:
        content = validation_f.read()
        # Check for unbalanced quotes (simple heuristic)
        quote_count = content.count('"')
        if quote_count % 2 != 0:
            # Unbalanced quotes - this is a parse error
            if not is_production:
                raise csv.Error("Unbalanced quotes in CSV file")
            # In production, log and return False
            logger.debug("Unbalanced quotes in CSV file %s (production mode, ignoring)", csv_path)
            return False
    return True


def _parse_alias_canonical_schema(reader: csv.DictReader) -> Dict[str, List[str]]:
    """
    Parse alias/canonical schema CSV format.

    RU: Парсит CSV с схемой alias/canonical.
    EN: Parses CSV with alias/canonical schema.

    Args:
        reader: CSV DictReader with alias and canonical columns

    Returns:
        Dictionary mapping canonical (lowercased) to list of aliases
    """
    canonical_to_aliases: Dict[str, List[str]] = {}
    # Schema: alias,canonical (core/aliases format)
    # Transform: from {alias -> canonical} to {canonical -> [aliases]}
    for row in reader:
        alias_raw = (row.get("alias") or "").strip()
        canonical_raw = (row.get("canonical") or "").strip()
        if not alias_raw or not canonical_raw:
            continue
        # Lowercase canonical to match DEFAULT_ALIASES format
        canonical_lower = canonical_raw.lower()
        alias_lower = alias_raw.lower()
        if canonical_lower not in canonical_to_aliases:
            canonical_to_aliases[canonical_lower] = []
        # Add alias if not already present (avoid duplicates)
        if alias_lower not in canonical_to_aliases[canonical_lower]:
            canonical_to_aliases[canonical_lower].append(alias_lower)
    return canonical_to_aliases


def _parse_primary_aliases_schema(reader: csv.DictReader) -> Dict[str, List[str]]:
    """
    Parse primary/aliases schema CSV format.

    RU: Парсит CSV с схемой primary/aliases.
    EN: Parses CSV with primary/aliases schema.

    Args:
        reader: CSV reader positioned after header row

    Returns:
        Dictionary mapping primary (lowercased) to list of aliases
    """
    canonical_to_aliases: Dict[str, List[str]] = {}
    # Schema: primary,aliases (original format)
    # Handle CSV where aliases may contain unquoted commas, requiring special parsing
    header = next(reader, None)
    if header and header[0].lower() == "primary":
        primary_idx = 0
        # Process remaining rows
        for row_values in reader:
            if not row_values or len(row_values) <= primary_idx:
                continue
            primary_raw = (row_values[primary_idx] or "").strip()
            if not primary_raw:
                continue
            primary_lower = primary_raw.lower()
            if primary_lower not in canonical_to_aliases:
                canonical_to_aliases[primary_lower] = []
            # Collect all values after primary as aliases (handles unquoted commas)
            alias_parts: List[str] = []
            for val in row_values[primary_idx + 1 :]:
                # Split each value by semicolon first, then by comma
                for semicolon_part in val.split(";"):
                    alias_parts.extend(semicolon_part.split(","))
            # Process each alias part
            seen = set(canonical_to_aliases[primary_lower])
            for alias_raw in alias_parts:
                alias_lower = alias_raw.strip().lower()
                if alias_lower and alias_lower not in seen:
                    canonical_to_aliases[primary_lower].append(alias_lower)
                    seen.add(alias_lower)
    return canonical_to_aliases


def _load_aliases_csv(csv_path: Path) -> Dict[str, List[str]]:
    """
    Load aliases from CSV file with support for two schemas.

    Detects header names at runtime and supports:
    - alias,canonical: maps each alias to canonical (core/aliases format)
    - primary,aliases: splits aliases and maps each to primary (original format)

    Returns Dict[str, List[str]] mapping canonical/primary (lowercased) to list of aliases.
    Preserves error handling: returns empty dict on missing file or parse errors.

    RU: Загружает алиасы из CSV с автоматическим определением схемы заголовков.
    Поддерживает оба формата: alias/canonical и primary/aliases.
    """
    canonical_to_aliases: Dict[str, List[str]] = {}
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"

    try:
        # Validate CSV file for balanced quotes before parsing
        if not _validate_csv_quotes(csv_path, is_production):
            return {}

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

            # Detect schema by checking available columns
            has_alias_canonical = "alias" in fieldnames and "canonical" in fieldnames
            has_primary_aliases = "primary" in fieldnames and "aliases" in fieldnames

            if has_alias_canonical:
                canonical_to_aliases = _parse_alias_canonical_schema(reader)
            elif has_primary_aliases:
                # Schema: primary,aliases (original format)
                # Handle CSV where aliases may contain unquoted commas, requiring special parsing
                # Use csv.reader to get all columns, then reconstruct
                f.seek(0)  # Reset to read header again
                reader_list = csv.reader(f)
                canonical_to_aliases = _parse_primary_aliases_schema(reader_list)
            # If neither schema matches, return empty dict (preserves current behavior)

    except FileNotFoundError:
        # Return empty dict if file doesn't exist (preserves current behavior)
        pass
    except (csv.Error, UnicodeDecodeError, OSError):
        # Handle CSV parse errors: raise in development, ignore in production
        if not is_production:
            raise
        # In production, log at debug level and return empty dict
        logger.debug("Error loading aliases CSV from %s (production mode, ignoring)", csv_path)

    # Sort alias lists for consistency
    for canonical in canonical_to_aliases:
        canonical_to_aliases[canonical] = sorted(canonical_to_aliases[canonical])

    return canonical_to_aliases


# Lazy alias cache to avoid file I/O at import time
_ALIASES_CACHE: Optional[Dict[str, List[str]]] = None
_ALIASES_LOCK = threading.Lock()


def get_aliases() -> Dict[str, List[str]]:
    """Return merged alias mapping (defaults + CSV), loading lazily on first use."""
    global _ALIASES_CACHE
    if _ALIASES_CACHE is None:
        with _ALIASES_LOCK:
            if _ALIASES_CACHE is None:
                csv_aliases = _load_aliases_csv(ALIASES_CSV_PATH)
                _ALIASES_CACHE = {**DEFAULT_ALIASES, **csv_aliases}
    return _ALIASES_CACHE


def expand_query(q: str) -> List[str]:
    """Expand a query using alias mappings; returns unique lowercase terms."""
    ql = (q or "").strip().lower()
    if not ql:
        return []
    terms = {ql}
    for k, vs in get_aliases().items():
        if ql == k or ql in vs:
            terms.update([k, *vs])
    return list(terms)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def search_foods(query: str, limit: int | str = 20, offset: int | str = 0) -> List[Dict[str, Any]]:
    """Search foods via FTS; parameters are safely bound using placeholders."""
    # Defensive bounds and type validation for pagination
    if not isinstance(limit, int):
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise ValueError("limit must be an integer")
    if not isinstance(offset, int):
        try:
            offset = int(offset)
        except (TypeError, ValueError):
            raise ValueError("offset must be an integer")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    limit = min(limit, MAX_LIMIT)
    if offset < 0:
        raise ValueError("offset must be >= 0")
    terms = expand_query(query) if query else []
    params: List[Any] = []
    if terms:
        # nosec B608: The query uses parameter placeholders for all user inputs;
        # only the number of placeholders is constructed dynamically.
        # Safe but consider phrase/prefix search (e.g., "term*" for prefix matching)
        # for better FTS behavior in future enhancements.
        sql = (
            """
          SELECT f.id, f.canonical_name, f.kcal, f.protein_g, f.fat_g, f.carbs_g
          FROM foods f
          JOIN foods_fts ff ON ff.rowid = f.rowid
          WHERE """
            + " OR ".join(["ff.canonical_name MATCH ?"] * len(terms))  # nosec B608
            + " LIMIT ? OFFSET ?"
        )
        params = [*terms, limit, offset]
    else:
        sql = (
            "SELECT id, canonical_name, kcal, protein_g, fat_g, carbs_g FROM foods LIMIT ? OFFSET ?"
        )
        params = [limit, offset]
    with _connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_food(food_id: str) -> Optional[Dict[str, Any]]:
    """Return a single food by id or None if not found."""
    with _connect() as con:
        row = con.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
    return dict(row) if row else None


def _validate_ingredient_mapping(ing: Mapping[str, Any]) -> Optional[Tuple[str, float]]:
    """
    Validate ingredient mapping and extract food_id and grams.

    RU: Валидирует ингредиент и извлекает food_id и grams.
    EN: Validates ingredient mapping and extracts food_id and grams.

    Args:
        ing: Ingredient mapping with "food_id" and "grams" keys

    Returns:
        Tuple of (food_id, grams) if valid, None otherwise
    """
    if not isinstance(ing, Mapping):
        logger.warning("nutrients_for: ingredient is not a mapping, skipping: %r", ing)
        return None

    food_id = ing.get("food_id")
    if not isinstance(food_id, str) or not food_id.strip():
        logger.warning("nutrients_for: missing or invalid food_id in ingredient: %r", ing)
        return None

    grams_raw = ing.get("grams")
    if not isinstance(grams_raw, (int, float, str)):
        logger.warning(
            "nutrients_for: grams has unsupported type for food_id=%s: %r",
            food_id,
            grams_raw,
        )
        return None
    try:
        grams = float(grams_raw)
    except (TypeError, ValueError):
        logger.warning("nutrients_for: grams is not numeric for food_id=%s: %r", food_id, grams_raw)
        return None
    if grams < 0:
        logger.warning("nutrients_for: grams is negative for food_id=%s: %r", food_id, grams_raw)
        return None

    return (food_id, grams)


def _safe_per_g(per_g_raw: Any, food_id: str) -> float:
    """
    Safely parse per_g value with fallback to DEFAULT_PER_G.

    RU: Безопасно парсит per_g с возвратом к DEFAULT_PER_G при ошибке.
    EN: Safely parses per_g with fallback to DEFAULT_PER_G on error.

    Args:
        per_g_raw: Raw per_g value from food row
        food_id: Food identifier for logging

    Returns:
        Parsed per_g value or DEFAULT_PER_G if invalid/zero
    """
    try:
        per_g = float(per_g_raw)
    except (TypeError, ValueError):
        logger.warning(
            "nutrients_for: per_g invalid for food_id=%s (value=%r); defaulting to %s",
            food_id,
            per_g_raw,
            DEFAULT_PER_G,
        )
        return DEFAULT_PER_G
    if per_g == 0.0:
        logger.warning(
            "nutrients_for: per_g is zero for food_id=%s; defaulting to %s to avoid division by zero",
            food_id,
            DEFAULT_PER_G,
        )
        return DEFAULT_PER_G
    return per_g


def nutrients_for(ings: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    """
    RU: Наивный сумматор нутриентов с валидацией входных данных.

    EN: Naive nutrient aggregator with input validation.

    Expected input structure per ingredient mapping:
      - "food_id" (str): Identifier present in the foods table. If missing/not found -> skipped.
      - "grams" (int|float|str): Amount in grams. Non-numeric or negative -> skipped.

    Behavior:
      - Missing food in DB: ingredient is skipped.
      - Missing/invalid/zero "per_g" on the food row: falls back to DEFAULT_PER_G to avoid division by zero
        and logs at WARNING level.

    Returns a dict with summed nutrient keys as floats.
    """
    keys = [
        "kcal",
        "protein_g",
        "fat_g",
        "carbs_g",
        "Fe_mg",
        "Ca_mg",
        "K_mg",
        "Mg_mg",
        "VitD_IU",
        "B12_ug",
        "Folate_ug",
        "Iodine_ug",
    ]
    total = {k: 0.0 for k in keys}
    for ing in ings:
        validation_result = _validate_ingredient_mapping(ing)
        if validation_result is None:
            continue
        food_id, grams = validation_result

        food = get_food(food_id)
        if not food:
            logger.info("nutrients_for: food not found for food_id=%s; skipping", food_id)
            continue

        per_g_raw = food.get("per_g", DEFAULT_PER_G)
        per_g = _safe_per_g(per_g_raw, food_id)

        ratio = grams / per_g
        for k in keys:
            total[k] += _safe_float(food.get(k, 0.0)) * ratio
    return total
