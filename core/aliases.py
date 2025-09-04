import csv
import os
import re
from typing import Dict


def _load_aliases(path: str = None) -> Dict[str, str]:
    """
    RU: Загрузить таблицу синонимов.
    EN: Load alias table.

    Args:
        path: Path to aliases CSV file

    Returns:
        Dictionary mapping aliases to canonical names
    """
    if path is None:
        # Default path relative to project root
        path = os.path.join(os.path.dirname(__file__), "..", "data", "food_aliases.csv")

    table = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                alias = row["alias"].strip().lower()
                canonical = row["canonical"].strip()
                table[alias] = canonical
    except FileNotFoundError:
        # Return empty table if file doesn't exist
        pass
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
    canonical = re.sub(r'[^\w\s-]', '', key)  # Remove punctuation except spaces and hyphens
    canonical = re.sub(r'[-\s]+', '_', canonical)  # Convert spaces and hyphens to underscores
    canonical = canonical.strip('_')  # Remove leading/trailing underscores
    return canonical or "unknown"


def add_alias(alias: str, canonical: str, path: str = None):
    """
    RU: Добавить новую пару синоним-каноническое имя.
    EN: Add new alias-canonical pair.

    Args:
        alias: Alias name
        canonical: Canonical name
        path: Path to aliases CSV file
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
