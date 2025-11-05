import csv
import functools
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _load_aliases(path: Optional[str] = None) -> dict[str, str]:
    """
    RU: Загрузить таблицу синонимов с поддержкой двух схем CSV.
    EN: Load alias table with support for two CSV schemas.

    Supports two CSV formats:
    1. Schema: alias,canonical
       - Maps each alias (lowercased) to its canonical name (kept as provided)
    2. Schema: primary,aliases
       - Splits aliases by ';' or ',', trims/lowercases each alias,
         and maps each to the primary name (kept as provided)

    Args:
        path: Path to aliases CSV file

    Returns:
        Dictionary mapping lowercase aliases to canonical/primary names
        (canonical names are kept as provided, not lowercased)
    """
    if path is None:
        # Default path relative to project root
        path = os.path.join(os.path.dirname(__file__), "..", "data", "food_aliases.csv")

    table: dict[str, str] = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Detect schema by checking available columns
            fieldnames = reader.fieldnames or []
            has_alias_canonical = "alias" in fieldnames and "canonical" in fieldnames
            has_primary_aliases = "primary" in fieldnames and "aliases" in fieldnames

            if has_alias_canonical:
                # Schema 1: alias,canonical
                for row in reader:
                    alias = (row.get("alias") or "").strip().lower()
                    canonical = (row.get("canonical") or "").strip()
                    if alias and canonical:
                        table[alias] = canonical
            elif has_primary_aliases:
                # Schema 2: primary,aliases (split by ; or ,)
                for row in reader:
                    primary = (row.get("primary") or "").strip()
                    aliases_str = (row.get("aliases") or "").strip()
                    if not primary:
                        continue
                    # Split by either ; or , using regex to handle both delimiters uniformly
                    alias_parts = re.split(r"[;,]", aliases_str)
                    # Process each alias part: strip, lower, and add non-empty aliases
                    for alias_raw in alias_parts:
                        alias = alias_raw.strip().lower()
                        if alias:
                            table[alias] = primary
                    # Also map primary itself (lowercased) to primary (as provided)
                    # This allows lookup by canonical name too
                    primary_lower = primary.lower()
                    if primary_lower:
                        table[primary_lower] = primary
            else:
                # If neither schema matches, log warning and return empty dict
                logger.warning(
                    "CSV headers do not match expected schemas. "
                    "Detected headers: %s. "
                    "Expected schemas: 'alias,canonical' or 'primary,aliases'",
                    fieldnames,
                )
    except FileNotFoundError:
        # Return empty table if file doesn't exist
        logger.debug("Alias file not found: %s", path, exc_info=True)
    except (csv.Error, UnicodeDecodeError, OSError) as e:
        # Handle other CSV errors gracefully
        logger.debug(
            "Error loading alias file %s: %s - %s",
            path,
            type(e).__name__,
            str(e),
            exc_info=True,
        )
    return table


def map_to_canonical(raw_name: str, locale: str = "en") -> str:
    """
    RU: Преобразовать сырое имя в каноническое.
    EN: Map raw name to canonical name.

    Args:
        raw_name: Raw food name
        locale: Locale of the name

    Returns:
        Canonical name
    """
    key = (raw_name or "").strip().lower()
    if not key:
        return "unknown"

    table = _load_aliases()
    if key in table:
        return table[key]

    # Fallback: convert to snake_case, handling special characters
    # Remove extra whitespace and special characters, then convert to snake_case
    canonical = re.sub(r"[^\w\s-]", "", key)  # Remove punctuation except spaces and hyphens
    canonical = re.sub(r"[-\s]+", "_", canonical)  # Convert spaces and hyphens to underscores
    canonical = canonical.strip("_")  # Remove leading/trailing underscores
    return canonical or "unknown"


def clear_alias_cache() -> None:
    """Clear the aliases cache to force reload on next access."""
    _load_aliases.cache_clear()


def add_alias(alias: str, canonical: str, path: Optional[str] = None) -> None:
    """
    RU: Добавить новую пару синоним-каноническое имя.
    EN: Add new alias-canonical pair.

    Args:
        alias: Alias name
        canonical: Canonical name
        path: Path to aliases CSV file

    Note:
        This function only writes rows in Schema 1 format (alias,canonical).
        For Schema 2 format (primary,aliases), edit the CSV manually or use
        a separate helper function.
    """
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "data", "food_aliases.csv")

    # Check if file exists, create with header if not
    file_exists = os.path.exists(path)

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["alias", "canonical"])
        writer.writerow([alias.strip().lower(), canonical.strip()])
    # Invalidate cache after adding new alias
    clear_alias_cache()
