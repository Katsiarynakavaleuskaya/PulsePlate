# -*- coding: utf-8 -*-
"""FoodDB access service with FTS and alias expansion.

RU: Сервис доступа к FoodDB (SQLite) с FTS и алиасами.
EN: Access to FoodDB (SQLite) with FTS and alias expansion.
"""

from contextlib import contextmanager
import csv
import sqlite3
from pathlib import Path
import logging
import os
import re
from typing import Any, Dict, Iterator, List, Optional, Mapping, Protocol, Sequence, Tuple
import threading
from collections import defaultdict

# Initialize logger early for setup-time logging
logger = logging.getLogger(__name__)

# DB path can be overridden via env var FOOD_DB_PATH; defaults to data/food.sqlite
_env_db_path = os.getenv("FOOD_DB_PATH")
DB_PATH: Path = Path(_env_db_path) if _env_db_path else Path("data/food.sqlite")

# Ensure parent directory exists for the SQLite file (create parents as necessary)
# Directory creation rarely fails, but if it does, the original OSError provides sufficient context
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except OSError as exc:  # pragma: no cover - extremely rare filesystem errors
    logger.error(
        "CRITICAL: Unable to create DB directory %s: %s",
        DB_PATH.parent,
        exc,
        exc_info=True,
    )
    raise RuntimeError(
        f"Failed to create database directory '{DB_PATH.parent}'. "
        f"This is required for module initialization. Original error: {exc}"
    ) from exc
ALIASES_CSV_PATH: Path = Path(os.getenv("FOOD_ALIASES_CSV", "data/food_aliases.csv"))
MAX_LIMIT: int = 100
DEFAULT_PER_G: float = 100.0
FEATURE_FOOD_SEARCH_COMPAT_ENABLED = "FEATURE_FOOD_SEARCH_COMPAT_ENABLED"
FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED = "FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED"
FOOD_SEARCH_BACKEND_STRATEGY = "FOOD_SEARCH_BACKEND_STRATEGY"
FOOD_SEARCH_SEMANTIC_CANDIDATE_LIMIT = "FOOD_SEARCH_SEMANTIC_CANDIDATE_LIMIT"
DEFAULT_SEMANTIC_CANDIDATE_LIMIT = 250
BARCODE_MIN_LEN = 8
BARCODE_MAX_LEN = 14

DEFAULT_ALIASES: Dict[str, List[str]] = {
    # RU/EN/ES базовые соответствия; расширяй из своего alias CSV
    "йогурт": ["yogurt", "yoghurt"],
    "масло оливковое": ["olive oil", "aceite de oliva"],
    "творог": ["cottage cheese", "queso cottage"],
}

# RU: Реестр лицензий и обязательной атрибуции для источников Food DB.
# EN: License and required attribution registry for Food DB sources.
_FOOD_SOURCE_ATTRIBUTION_REGISTRY: Dict[str, Dict[str, str | None]] = {
    "usda": {
        "source": "USDA FoodData Central",
        "license": "U.S. Government Work (public domain, source attribution required)",
        "attribution": "Contains data from USDA FoodData Central.",
        "source_url": "https://fdc.nal.usda.gov/",
    },
    "open food facts": {
        "source": "Open Food Facts",
        "license": "Open Database License (ODbL) v1.0",
        "attribution": "Contains Open Food Facts data licensed under ODbL v1.0.",
        "source_url": "https://world.openfoodfacts.org/",
    },
    "off": {
        "source": "Open Food Facts",
        "license": "Open Database License (ODbL) v1.0",
        "attribution": "Contains Open Food Facts data licensed under ODbL v1.0.",
        "source_url": "https://world.openfoodfacts.org/",
    },
    "menustat": {
        "source": "MenuStat",
        "license": "Public research dataset (source attribution required)",
        "attribution": "Contains data from MenuStat annual restaurant nutrition datasets.",
        "source_url": "https://www.menustat.org/",
    },
    "nutritionix": {
        "source": "Nutritionix",
        "license": "Nutritionix API terms",
        "attribution": "Contains Nutritionix data used under applicable API terms.",
        "source_url": "https://www.nutritionix.com/business/api",
    },
    "merged(off,usda)": {
        "source": "USDA + Open Food Facts (merged)",
        "license": "Mixed: USDA public domain + Open Food Facts ODbL v1.0",
        "attribution": (
            "Contains merged USDA FoodData Central and Open Food Facts data; "
            "Open Food Facts portion is licensed under ODbL v1.0."
        ),
        "source_url": "https://fdc.nal.usda.gov/",
    },
}
_FOOD_ATTRIBUTION_DEFAULT_KEYS: Tuple[str, ...] = ("usda", "open food facts")


def _safe_float(value: int | float | str | None) -> float:
    """Best-effort float conversion; returns 0.0 on None/non-numeric.

    RU: Безопасное приведение к float; возвращает 0.0 для None/нечисловых значений.
    """
    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _validate_csv_quotes(csv_path: Path, is_production: bool) -> bool:
    """
    Validate CSV file using the csv module to detect structural issues.

    RU: Проверяет CSV файл на валидность, используя модуль csv.
    EN: Validates CSV structure using the stdlib csv parser.

    Args:
        csv_path: Path to the CSV file to validate
        is_production: Whether running in production mode

    Returns:
        True if CSV is valid, False otherwise

    Raises:
        FileNotFoundError: If the CSV file does not exist
        csv.Error: In non-production mode if CSV is malformed (re-raised)
        Exception: In non-production mode for other I/O errors (re-raised)
    """
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as validation_f:
            # Use csv.reader to validate CSV structure
            # strict=True is only available in Python 3.12+, so we use a try-except
            # to handle both old and new Python versions
            try:
                reader = csv.reader(validation_f, strict=True)
            except TypeError:
                # Python < 3.12 doesn't support strict parameter
                validation_f.seek(0)
                reader = csv.reader(validation_f)
            for _ in reader:
                continue
        return True
    except FileNotFoundError:
        # Let FileNotFoundError propagate to caller
        raise
    except csv.Error as e:
        # CSV parsing error indicates malformed quotes or structure
        if not is_production:
            # Re-raise the original csv.Error (don't wrap it)
            raise
        # In production, log and return False
        logger.debug("Malformed CSV file %s (production mode, ignoring): %s", csv_path, e)
        return False
    except Exception as e:
        # Other I/O or unexpected errors
        if not is_production:
            # Re-raise the original exception (don't wrap in csv.Error)
            raise
        logger.debug("Error reading CSV file %s (production mode, ignoring): %s", csv_path, e)
        return False


def _parse_alias_canonical_schema(reader: csv.DictReader) -> dict[str, list[str]]:
    """
    Parse alias/canonical schema CSV format.

    RU: Парсит CSV с схемой alias/canonical.
    EN: Parses CSV with alias/canonical schema.

    Args:
        reader: CSV DictReader with alias and canonical columns

    Returns:
        Dictionary mapping canonical (lowercased) to list of aliases
    """
    canonical_to_aliases: dict[str, list[str]] = {}
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


def _parse_primary_aliases_schema(reader: Iterator[Sequence[str]]) -> dict[str, list[str]]:
    """
    Parse primary/aliases schema CSV format.

    RU: Парсит CSV с схемой primary/aliases.
    EN: Parses CSV with primary/aliases schema.

    Args:
        reader: CSV reader positioned after header row

    Returns:
        Dictionary mapping primary (lowercased) to list of aliases
    """
    canonical_to_aliases: dict[str, list[str]] = {}
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
            alias_parts: list[str] = []
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


def _load_aliases_csv(csv_path: Path, is_production: Optional[bool] = None) -> Dict[str, List[str]]:
    """
    Load aliases from CSV file with support for two schemas.

    Detects header names at runtime and supports:
    - alias,canonical: maps each alias to canonical (core/aliases format)
    - primary,aliases: splits aliases and maps each to primary (original format)

    Args:
        csv_path: Path to the CSV file containing aliases.
        is_production: Whether to run in production mode. If None, derives from
            os.getenv("ENVIRONMENT") == "production". In production mode, errors
            are logged and an empty dict is returned instead of raising exceptions.

    Returns:
        Dict[str, List[str]] mapping canonical/primary (lowercased) to list of aliases.
        Returns empty dict on missing file or parse errors in production mode.

    RU: Загружает алиасы из CSV с автоматическим определением схемы заголовков.
    Поддерживает оба формата: alias/canonical и primary/aliases.
    """
    canonical_to_aliases: Dict[str, List[str]] = {}
    if is_production is None:
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

# Missing food counter/collector for periodic summary logging
_MISSING_FOOD_COUNTER: Dict[str, int] = defaultdict(int)
_MISSING_FOOD_LOCK = threading.Lock()
_MISSING_FOOD_REPORT_THRESHOLD = int(os.getenv("MISSING_FOOD_REPORT_THRESHOLD", "100"))


class FoodSearchBackend(Protocol):
    """Search backend contract used by API compatibility layer."""

    def search_foods(
        self, query: str, limit: int | str = 20, offset: int | str = 0
    ) -> Sequence[Mapping[str, Any]]: ...


class _LegacyFoodSearchBackend:
    """Default backend that keeps existing SQLite/FTS behavior."""

    def search_foods(
        self, query: str, limit: int | str = 20, offset: int | str = 0
    ) -> Sequence[Mapping[str, Any]]:
        return search_foods(query, limit=limit, offset=offset)


class _BootstrapSemanticSearchBackend:
    """
    Lightweight semantic-ish backend for W4 bootstrap.

    RU: Лёгкий semantic bootstrap-бэкенд без внешних зависимостей.
    EN: Lightweight semantic bootstrap backend without external dependencies.
    """

    def __init__(self, candidate_limit: int) -> None:
        self._candidate_limit = candidate_limit

    def search_foods(
        self, query: str, limit: int | str = 20, offset: int | str = 0
    ) -> Sequence[Mapping[str, Any]]:
        normalized_limit, normalized_offset = _validate_pagination_params(limit, offset)
        normalized_query = (query or "").strip()
        if not normalized_query:
            return search_foods(normalized_query, limit=normalized_limit, offset=normalized_offset)

        required_window_size = normalized_limit + normalized_offset
        if required_window_size > self._candidate_limit:
            return search_foods(normalized_query, limit=normalized_limit, offset=normalized_offset)

        candidate_fetch_limit = self._candidate_limit
        candidates = _load_semantic_candidates(limit=candidate_fetch_limit)
        query_tokens = _semantic_tokens(normalized_query)
        if not query_tokens:
            return search_foods(normalized_query, limit=normalized_limit, offset=normalized_offset)

        ranked: List[Tuple[float, Mapping[str, Any]]] = []
        for row in candidates:
            canonical_name = str(row.get("canonical_name", ""))
            score = _semantic_score(query_tokens, canonical_name)
            if score > 0.0:
                ranked.append((score, row))

        if not ranked:
            return search_foods(normalized_query, limit=normalized_limit, offset=normalized_offset)

        ranked.sort(
            key=lambda item: (
                -item[0],
                str(item[1].get("canonical_name", "")).lower(),
                str(item[1].get("id", "")),
            )
        )
        window = ranked[normalized_offset : normalized_offset + normalized_limit]
        return [dict(row) for _, row in window]


_LEGACY_SEARCH_BACKEND: FoodSearchBackend = _LegacyFoodSearchBackend()
_COMPAT_SEARCH_BACKEND: FoodSearchBackend | None = None
_SEMANTIC_SEARCH_BACKEND: FoodSearchBackend | None = None
_STRATEGY_SEARCH_BACKEND: FoodSearchBackend | None = None
_SEARCH_BACKEND_LOCK = threading.Lock()


class FoodRepository:
    """Repository wrapper for food lookups against the local SQLite store."""

    @staticmethod
    def get_by_id(food_id: str) -> Optional[Dict[str, Any]]:
        with _connect() as con:
            row = con.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_gtin(gtin: str) -> Optional[Dict[str, Any]]:
        with _connect() as con:
            row = con.execute(
                "SELECT * FROM foods WHERE gtin = ? ORDER BY id ASC LIMIT 1", (gtin,)
            ).fetchone()
        return dict(row) if row else None


def _is_truthy_env(value: str | None) -> bool:
    """Parse common truthy env representations."""
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _use_compat_search_backend() -> bool:
    """Return True when compatibility adapter path is explicitly enabled."""
    return _is_truthy_env(os.getenv(FEATURE_FOOD_SEARCH_COMPAT_ENABLED))


def _use_semantic_search_backend() -> bool:
    """Return True when semantic search adapter path is explicitly enabled."""
    return _is_truthy_env(os.getenv(FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED))


def _semantic_tokens(value: str) -> set[str]:
    """Tokenize free-text query into normalized tokens."""
    return {token for token in re.findall(r"[0-9a-zа-яё]+", value.lower()) if token}


def _semantic_score(query_tokens: set[str], candidate_name: str) -> float:
    """
    Rank candidate name against query tokens using deterministic lexical overlap.

    RU: Детерминированный lexical-overlap score для bootstrap semantic path.
    EN: Deterministic lexical-overlap score for bootstrap semantic path.
    """
    candidate_tokens = _semantic_tokens(candidate_name)
    if not query_tokens or not candidate_tokens:
        return 0.0
    overlap = len(query_tokens & candidate_tokens)
    if overlap == 0:
        return 0.0
    union = len(query_tokens | candidate_tokens)
    base_score = overlap / union
    prefix_bonus = 0.1 if candidate_name.lower().startswith(tuple(sorted(query_tokens))) else 0.0
    return base_score + prefix_bonus


def _semantic_candidate_limit() -> int:
    """Return validated candidate pool size for bootstrap semantic search."""
    raw_value = os.getenv(
        FOOD_SEARCH_SEMANTIC_CANDIDATE_LIMIT, str(DEFAULT_SEMANTIC_CANDIDATE_LIMIT)
    )
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_SEMANTIC_CANDIDATE_LIMIT
    if parsed < 1:
        return DEFAULT_SEMANTIC_CANDIDATE_LIMIT
    return min(parsed, 5000)


def get_search_backend_strategy() -> str:
    """Return normalized backend strategy for additive search adapters."""

    strategy = (os.getenv(FOOD_SEARCH_BACKEND_STRATEGY) or "baseline_fts").strip().lower()
    if strategy not in {"baseline_fts", "meili", "hybrid_shadow"}:
        return "baseline_fts"
    return strategy


def _load_semantic_candidates(limit: int) -> List[Dict[str, Any]]:
    """
    Load semantic candidate rows directly from foods table.

    RU: Загружает кандидатов напрямую из foods, без MAX_LIMIT clamp.
    EN: Loads candidates directly from foods, bypassing search pagination clamp.
    """
    with _connect() as con:
        rows = con.execute(
            "SELECT id, canonical_name, kcal, protein_g, fat_g, carbs_g "
            "FROM foods ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def register_semantic_search_backend_adapter(adapter: FoodSearchBackend | None) -> None:
    """Register semantic search backend adapter."""
    global _SEMANTIC_SEARCH_BACKEND
    with _SEARCH_BACKEND_LOCK:
        _SEMANTIC_SEARCH_BACKEND = adapter


def reset_semantic_search_backend_adapter() -> None:
    """Reset semantic search adapter to bootstrap auto-selection mode."""
    register_semantic_search_backend_adapter(None)


def _resolve_semantic_backend(semantic_backend: FoodSearchBackend | None) -> FoodSearchBackend:
    """Resolve semantic backend, creating deterministic bootstrap backend if needed."""
    if semantic_backend is not None:
        return semantic_backend
    bootstrap_backend = _BootstrapSemanticSearchBackend(candidate_limit=_semantic_candidate_limit())
    global _SEMANTIC_SEARCH_BACKEND
    with _SEARCH_BACKEND_LOCK:
        current_semantic = _SEMANTIC_SEARCH_BACKEND
        if current_semantic is not None:
            return current_semantic
        _SEMANTIC_SEARCH_BACKEND = bootstrap_backend
    return bootstrap_backend


def register_search_backend_adapter(adapter: FoodSearchBackend | None) -> None:
    """Register optional compatibility search backend adapter."""
    global _COMPAT_SEARCH_BACKEND
    with _SEARCH_BACKEND_LOCK:
        _COMPAT_SEARCH_BACKEND = adapter


def register_strategy_search_backend_adapter(adapter: FoodSearchBackend | None) -> None:
    """Register additive strategy search backend adapter."""

    global _STRATEGY_SEARCH_BACKEND
    with _SEARCH_BACKEND_LOCK:
        _STRATEGY_SEARCH_BACKEND = adapter


def reset_search_backend_adapter() -> None:
    """Reset compatibility search backend adapter to legacy-only state."""
    register_search_backend_adapter(None)


def reset_strategy_search_backend_adapter() -> None:
    """Reset additive strategy backend adapter."""

    register_strategy_search_backend_adapter(None)


def get_legacy_search_backend() -> FoodSearchBackend:
    """Expose legacy backend for additive wrappers."""

    return _LEGACY_SEARCH_BACKEND


def get_search_backend() -> FoodSearchBackend:
    """
    Resolve active search backend.

    Legacy SQLite backend remains default unless feature flag is enabled and adapter is registered.
    """
    with _SEARCH_BACKEND_LOCK:
        compat_backend = _COMPAT_SEARCH_BACKEND
        semantic_backend = _SEMANTIC_SEARCH_BACKEND
        strategy_backend = _STRATEGY_SEARCH_BACKEND
    if get_search_backend_strategy() != "baseline_fts" and strategy_backend is not None:
        return strategy_backend
    if _use_semantic_search_backend():
        return _resolve_semantic_backend(semantic_backend=semantic_backend)
    if _use_compat_search_backend() and compat_backend is not None:
        return compat_backend
    return _LEGACY_SEARCH_BACKEND


def _discover_food_source_keys() -> List[str]:
    """Discover canonical source keys from foods table, fallback to defaults."""
    try:
        with _connect() as con:
            rows = con.execute(
                "SELECT DISTINCT source FROM foods WHERE source IS NOT NULL ORDER BY source ASC"
            ).fetchall()
    except sqlite3.Error:
        return list(_FOOD_ATTRIBUTION_DEFAULT_KEYS)

    discovered = {str(row["source"]).strip().lower() for row in rows if str(row["source"]).strip()}
    if not discovered:
        return list(_FOOD_ATTRIBUTION_DEFAULT_KEYS)
    return sorted(discovered)


def get_food_source_attributions() -> List[Dict[str, str | None]]:
    """
    Return license/attribution metadata for known and discovered food sources.

    RU: Возвращает метаданные лицензий и атрибуции по источникам Food DB.
    EN: Returns license and attribution metadata for Food DB sources.
    """
    result: List[Dict[str, str | None]] = []
    for source_key in _discover_food_source_keys():
        registry_entry = _FOOD_SOURCE_ATTRIBUTION_REGISTRY.get(source_key)
        if registry_entry is None:
            result.append(
                {
                    "source": source_key.upper(),
                    "license": "Unknown / internal source policy",
                    "attribution": f"Contains data from source '{source_key}'.",
                    "source_url": None,
                }
            )
            continue
        result.append(dict(registry_entry))
    return result


def _log_missing_food(food_id: str) -> None:
    """
    Track missing food and emit periodic summary logs.

    RU: Отслеживает отсутствующие продукты и периодически выводит сводные логи.
    EN: Tracks missing food and emits periodic summary logs.

    Args:
        food_id: The food ID that was not found
    """
    # Note: _MISSING_FOOD_COUNTER is module-level defaultdict, no need for global declaration
    # We only mutate it via methods (.clear(), [key] += 1), not reassign

    # Log individual missing food at DEBUG level to reduce noise
    logger.debug("nutrients_for: food not found for food_id=%s; skipping", food_id)

    # Track in counter for periodic summary
    with _MISSING_FOOD_LOCK:
        _MISSING_FOOD_COUNTER[food_id] += 1
        total_missing = sum(_MISSING_FOOD_COUNTER.values())

        # Emit summary log every N missing foods
        if total_missing >= _MISSING_FOOD_REPORT_THRESHOLD:
            unique_count = len(_MISSING_FOOD_COUNTER)
            # Sort by count (descending) for most common first
            top_missing = sorted(_MISSING_FOOD_COUNTER.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]  # Top 10 most frequently missing

            top_str = ", ".join([f"{fid}({count}x)" for fid, count in top_missing])
            logger.info(
                "nutrients_for: missing food summary - total=%d occurrences, "
                "unique=%d food_ids. Top missing: %s. "
                "Reset counter after reporting.",
                total_missing,
                unique_count,
                top_str,
            )
            # Reset counter after reporting
            _MISSING_FOOD_COUNTER.clear()


def reset_missing_food_counter() -> None:
    """
    Reset the missing food counter (useful for testing or manual resets).

    RU: Сброс счётчика отсутствующих продуктов (полезно для тестов).
    EN: Reset the missing food counter (useful for testing or manual resets).
    """
    # Note: no global needed - we only call .clear() on module-level defaultdict
    with _MISSING_FOOD_LOCK:
        _MISSING_FOOD_COUNTER.clear()


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


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def _validate_pagination_params(limit: int | str, offset: int | str) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters.

    RU: Валидирует и нормализует параметры пагинации.
    EN: Validates and normalizes pagination parameters.

    Args:
        limit: Maximum number of results to return
        offset: Number of results to skip

    Returns:
        Tuple of (normalized_limit, normalized_offset)

    Raises:
        ValueError: If limit or offset are invalid
    """
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
    return limit, offset


def search_foods(query: str, limit: int | str = 20, offset: int | str = 0) -> List[Dict[str, Any]]:
    """Search foods via FTS; parameters are safely bound using placeholders."""
    # Validate and normalize pagination parameters
    limit, offset = _validate_pagination_params(limit, offset)
    terms = expand_query(query) if query else []
    params: List[Any] = []
    if terms:
        # Query uses parameter placeholders for all user inputs;
        # only the number of placeholders is constructed dynamically.
        # Safe but consider phrase/prefix search (e.g., "term*" for prefix matching)
        # for better FTS behavior in future enhancements.
        # Dynamic SQL construction: only clause count is dynamic, all values use placeholders
        # This is safe because we only construct the number of OR clauses, not the actual values
        sql = (
            """
          SELECT f.id, f.canonical_name, f.kcal, f.protein_g, f.fat_g, f.carbs_g
          FROM foods f
          JOIN foods_fts ff ON ff.rowid = f.rowid
          WHERE """
            + " OR ".join(
                ["ff.canonical_name MATCH ?"] * len(terms)
            )  # nosec B608: safe - only clause count is dynamic, all values use placeholders (remove-by: 2026-05-15, ref: PR-search-shadow-foundation)
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
    return FoodRepository.get_by_id(food_id)


def _normalize_barcode(barcode: str) -> str:
    """
    Normalize and validate barcode value.

    RU: Нормализует и валидирует barcode.
    EN: Normalizes and validates barcode.
    """
    normalized = re.sub(r"\D+", "", (barcode or "").strip())
    if not normalized:
        raise ValueError("barcode must contain at least one digit")
    if not (BARCODE_MIN_LEN <= len(normalized) <= BARCODE_MAX_LEN):
        raise ValueError(f"barcode must have length in [{BARCODE_MIN_LEN},{BARCODE_MAX_LEN}]")
    return normalized


def get_food_by_barcode(barcode: str) -> Optional[Dict[str, Any]]:
    """
    Return a single food by barcode (GTIN/EAN/UPC) or None when not found.

    RU: Возвращает продукт по штрихкоду (GTIN/EAN/UPC) или None, если не найден.
    EN: Returns a food by barcode (GTIN/EAN/UPC) or None if not found.
    """
    normalized = _normalize_barcode(barcode)
    row = FoodRepository.get_by_gtin(normalized)
    if row:
        return row

    fallback_candidates: list[str] = []
    if normalized.startswith("0"):
        # First fallback: remove only one padding zero.
        one_zero = normalized[1:]
        if len(one_zero) >= BARCODE_MIN_LEN:
            fallback_candidates.append(one_zero)

    # Second fallback: strip all left-padding zeros for GTIN-14 -> GTIN-12 cases.
    fully_stripped = normalized.lstrip("0")
    if (
        fully_stripped
        and len(fully_stripped) >= BARCODE_MIN_LEN
        and fully_stripped not in {normalized, *fallback_candidates}
    ):
        fallback_candidates.append(fully_stripped)

    for fallback in fallback_candidates:
        row = FoodRepository.get_by_gtin(fallback)
        if row:
            return row
    return None


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


def _safe_per_g(per_g_raw: object, food_id: str) -> float:
    """
    Safely parse per_g value with fallback to DEFAULT_PER_G.

    RU: Безопасно парсит per_g с возвратом к DEFAULT_PER_G при ошибке.
    EN: Safely parses per_g with fallback to DEFAULT_PER_G on error.

    Args:
        per_g_raw: Raw per_g value from food row (can be any type from DB)
        food_id: Food identifier for logging

    Returns:
        Parsed per_g value or DEFAULT_PER_G if invalid/zero
    """
    if per_g_raw is None:
        return DEFAULT_PER_G

    if isinstance(per_g_raw, (int, float)):
        per_g = float(per_g_raw)
    elif isinstance(per_g_raw, str):
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
    else:
        logger.warning(
            "nutrients_for: per_g has unsupported type for food_id=%s (value=%r); defaulting to %s",
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
            _log_missing_food(food_id)
            continue

        per_g_raw = food.get("per_g", DEFAULT_PER_G)
        per_g = _safe_per_g(per_g_raw, food_id)

        ratio = grams / per_g
        for k in keys:
            total[k] += _safe_float(food.get(k, 0.0)) * ratio
    return total
