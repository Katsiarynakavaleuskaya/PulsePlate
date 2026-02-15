"""
Nutrition Database Auto-Update Manager

RU: Менеджер автообновления баз данных питания.
EN: Manager for automatically updating nutrition databases.

This module handles automatic updates from open food databases when new
information becomes available, with version tracking, validation, and rollback.
"""

from __future__ import annotations

import asyncio
import inspect
import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, is_dataclass
from datetime import timedelta
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from .openfoodfacts_client import OFF_AVAILABLE, OFFClient
from .unified_db import UnifiedFoodDatabase, UnifiedFoodItem
from .usda_client import USDAClient
from ..time_utils import isoformat_utc, now_utc, parse_iso8601

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def _maybe_await(value: Union[T, Awaitable[T]]) -> T:
    """Return awaited value if awaitable, otherwise the value itself."""
    if inspect.isawaitable(value):
        return await value
    return value


class _PatchablePathWrapper:
    """
    Lightweight wrapper around pathlib.Path that allows instance-level attribute
    patching (e.g., monkeypatching .glob in tests). Delegates all operations to
    the underlying Path instance while remaining patch-friendly.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        """Explicit public accessor for the underlying pathlib.Path.

        This property exists to provide a stable contract for tests and
        integrations. Do not rely on __getattr__ for contract-level attributes.
        """
        return self._path

    # Commonly used methods/ops
    def glob(self, pattern: str):
        return self._path.glob(pattern)

    def __truediv__(self, other):  # support: wrapper / "filename"
        return self._path / other

    def __fspath__(self):  # support os.fspath
        return self._path.__fspath__()

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"_PatchablePathWrapper({self._path!r})"

    def __getattr__(self, name: str) -> object:
        # Delegate any other attribute access to the underlying Path
        return getattr(self._path, name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _PatchablePathWrapper):
            return self._path == other._path
        return self._path == other

    def __hash__(self) -> int:
        return hash(self._path)


@dataclass
class DatabaseVersion:
    """
    RU: Информация о версии базы данных.
    EN: Database version information.
    """

    source: str  # "usda", "openfoodfacts", etc.
    version: str
    last_updated: str  # ISO datetime
    record_count: int
    checksum: str  # Hash of all data for integrity
    metadata: Dict[str, Any]


@dataclass
class UpdateResult:
    """
    RU: Результат обновления базы данных.
    EN: Database update result.
    """

    success: bool
    source: str
    old_version: Optional[str]
    new_version: Optional[str]
    records_added: int
    records_updated: int
    records_removed: int
    errors: List[str]
    duration_seconds: float


class DatabaseUpdateManager:
    """
    RU: Менеджер автообновления баз данных питания.
    EN: Manager for automatic nutrition database updates.

    Features:
    - Version tracking and change detection
    - Scheduled updates with configurable intervals
    - Data validation and integrity checks
    - Rollback mechanisms for failed updates
    - Notification system for update events
    """

    _OFF_SQLITE_FILENAME: ClassVar[str] = "off.sqlite"
    _OFF_JSONL_PATTERNS: ClassVar[List[str]] = [
        "*.openfoodfacts.org.products.jsonl",
        "*.openfoodfacts.org.products.ndjson",
        "*off*.jsonl",
        "*off*.ndjson",
        "*products*.jsonl",
        "*products*.ndjson",
    ]
    _OFF_CSV_PATTERNS: ClassVar[List[str]] = [
        "*.openfoodfacts.org.products.csv",
        "*.csv",
        "*.tsv",
        "*_export.csv",
        "*off*.csv",
        "*products*.csv",
    ]

    def __init__(
        self,
        cache_dir: str | Path = "cache/food_db",
        update_interval_hours: int = 24,
        max_rollback_versions: int = 5,
    ):
        real_cache_path = Path(cache_dir)
        real_cache_path.mkdir(parents=True, exist_ok=True)
        # Wrap with a patch-friendly wrapper so tests can monkeypatch methods like .glob
        self.cache_dir = _PatchablePathWrapper(real_cache_path)

        self.update_interval = timedelta(hours=update_interval_hours)
        self.max_rollback_versions = max_rollback_versions

        # Data sources
        self.usda_client = USDAClient()
        self.off_client = OFFClient() if OFF_AVAILABLE else None
        self.unified_db = UnifiedFoodDatabase(str(real_cache_path))

        # Update callbacks
        self.update_callbacks: List[Callable[[UpdateResult], None]] = []

        # Load version tracking
        # Use real path for file ops composition
        self.versions_file = real_cache_path / "database_versions.json"
        self.versions = self._load_versions()

    def _load_versions(self) -> Dict[str, DatabaseVersion]:
        """Load database version information."""
        if not self.versions_file.exists():
            return {}

        try:
            with open(self.versions_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return {
                source: DatabaseVersion(**version_data) for source, version_data in data.items()
            }

        except Exception as e:
            logger.error("Error loading versions: %s", e)
            return {}

    def _save_versions(self):
        """Save database version information."""
        try:
            data = {source: asdict(version) for source, version in self.versions.items()}

            with open(self.versions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error("Error saving versions: %s", e, exc_info=True)

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for data integrity."""
        # Convert to sorted JSON string for consistent hashing
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _find_off_export_file(self, cache_dir: Path, file_types: Sequence[str]) -> Optional[Path]:
        """Return a deterministically selected OFF export file for the given types.

        Selection strategy:
        - Collect matches for each pattern
        - Sort by modification time (newest first) to prefer the most recent export
        - Return the single chosen Path for stable, repeatable behavior
        """
        pattern_map: dict[str, List[str]] = {
            "jsonl": self._OFF_JSONL_PATTERNS,
            "csv": self._OFF_CSV_PATTERNS,
        }
        for file_type in file_types:
            for pattern in pattern_map.get(file_type, []):
                matches = list(cache_dir.glob(pattern))
                if matches:
                    # Deterministic selection: newest by modification time
                    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    return matches[0]
        return None

    async def check_for_updates(self) -> Dict[str, bool]:
        """
        RU: Проверяет наличие обновлений для всех источников данных.
        EN: Check for updates across all data sources.

        Returns:
            Dict mapping source names to whether updates are available
        """
        updates_available = {}

        # Check USDA updates
        try:
            usda_available = await self._check_usda_updates()
            updates_available["usda"] = usda_available
        except Exception as e:
            logger.error("Error checking USDA updates: %s", e)
            updates_available["usda"] = False

        # Check Open Food Facts updates
        if self.off_client and OFF_AVAILABLE:
            try:
                off_available = await self._check_off_updates()
                updates_available["openfoodfacts"] = off_available
            except Exception as e:
                logger.error("Error checking Open Food Facts updates: %s", e)
                updates_available["openfoodfacts"] = False

        return updates_available

    async def _check_usda_updates(self) -> bool:
        """Check if USDA database has updates."""
        current_version = self.versions.get("usda")

        # If no current version, updates are available
        if not current_version:
            return True

        # Check if enough time has passed for an update
        last_update = parse_iso8601(current_version.last_updated)
        return bool(now_utc() - last_update >= self.update_interval)

    async def _check_off_updates(self) -> bool:
        """Check if Open Food Facts database has updates."""
        current_version = self.versions.get("openfoodfacts")

        # If no current version, updates are available
        if not current_version:
            return True

        # Check if enough time has passed for an update
        last_update = parse_iso8601(current_version.last_updated)
        return bool(now_utc() - last_update >= self.update_interval)

    async def update_database(self, source: str, force: bool = False) -> UpdateResult:
        """
        RU: Обновляет базу данных из указанного источника.
        EN: Update database from specified source.

        Args:
            source: Data source name ("usda", "openfoodfacts")
            force: Force update even if no changes detected

        Returns:
            UpdateResult with details of the update operation
        """
        start_time = now_utc()

        if source == "usda":
            result = await self._update_usda_database(force)
        elif source == "openfoodfacts" and self.off_client and OFF_AVAILABLE:
            result = await self._update_off_database(force)
        else:
            result = UpdateResult(
                success=False,
                source=source,
                old_version=None,
                new_version=None,
                records_added=0,
                records_updated=0,
                records_removed=0,
                errors=[f"Unknown source: {source}"],
                duration_seconds=0.0,
            )

        # Calculate duration
        result.duration_seconds = (now_utc() - start_time).total_seconds()

        # Notify callbacks
        for callback in self.update_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error("Error in update callback: %s", e)

        return result

    async def _update_usda_database(self, force: bool = False) -> UpdateResult:
        """Update USDA food database."""
        source = "usda"
        current_version = self.versions.get(source)
        old_version = current_version.version if current_version else None

        try:
            # Create backup of current data
            if current_version:
                await self._create_backup(source, current_version.version)

            # Get updated common foods from USDA
            logger.info("Fetching updated USDA food data...")
            updated_foods = await self.unified_db.get_common_foods_database()

            # Calculate new version info
            new_version = now_utc().strftime("%Y%m%d_%H%M%S")
            checksum = self._calculate_checksum(
                {name: self._food_to_dict(food) for name, food in updated_foods.items()}
            )

            # Check if data actually changed (unless forced)
            if not force and current_version and current_version.checksum == checksum:
                return UpdateResult(
                    success=True,
                    source=source,
                    old_version=old_version,
                    new_version=old_version,  # No change
                    records_added=0,
                    records_updated=0,
                    records_removed=0,
                    errors=[],
                    duration_seconds=0.0,
                )

            # Validate new data
            validation_errors = await self._validate_food_data(updated_foods)
            if validation_errors:
                return UpdateResult(
                    success=False,
                    source=source,
                    old_version=old_version,
                    new_version=None,
                    records_added=0,
                    records_updated=0,
                    records_removed=0,
                    errors=validation_errors,
                    duration_seconds=0.0,
                )

            # Calculate changes
            old_foods = {}
            if current_version:
                try:
                    old_foods = await self._load_backup(source, current_version.version)
                except Exception as e:
                    logger.warning("Could not load old data for comparison: %s", e)

            records_added = len(updated_foods) - len(old_foods)
            records_updated = len(set(updated_foods.keys()) & set(old_foods.keys()))
            records_removed = len(old_foods) - len(updated_foods)

            # Update version tracking
            new_db_version = DatabaseVersion(
                source=source,
                version=new_version,
                last_updated=isoformat_utc(),
                record_count=len(updated_foods),
                checksum=checksum,
                metadata={
                    "update_type": "forced" if force else "scheduled",
                    "api_source": "USDA FoodData Central",
                },
            )

            self.versions[source] = new_db_version
            self._save_versions()

            # Clean up old backups
            await self._cleanup_old_backups(source)

            logger.info("Successfully updated %s database: %d foods", source, len(updated_foods))

            return UpdateResult(
                success=True,
                source=source,
                old_version=old_version,
                new_version=new_version,
                records_added=max(0, records_added),
                records_updated=records_updated,
                records_removed=max(0, records_removed),
                errors=[],
                duration_seconds=0.0,
            )

        except Exception as e:
            logger.error("Error updating %s database: %s", source, e)
            return UpdateResult(
                success=False,
                source=source,
                old_version=old_version,
                new_version=None,
                records_added=0,
                records_updated=0,
                records_removed=0,
                errors=[str(e)],
                duration_seconds=0.0,
            )

    async def _update_off_database(self, force: bool = False) -> UpdateResult:
        """Update Open Food Facts database."""
        source = "openfoodfacts"
        current_version = self.versions.get(source)
        old_version = current_version.version if current_version else None

        try:
            # Create backup of current data
            if current_version:
                await self._create_backup(source, current_version.version)

            # For Open Food Facts, we'll fetch a sample of popular products
            # In a real implementation, this would be more sophisticated
            logger.info("Fetching Open Food Facts data...")

            # This is a simplified approach - in reality, we'd want to implement
            # a more comprehensive update strategy for Open Food Facts
            sample_products = []
            if self.off_client:
                # Search for some common products to include in our database
                common_searches = [
                    "apple",
                    "banana",
                    "chicken",
                    "bread",
                    "milk",
                    "cheese",
                    "rice",
                ]
                for search_term in common_searches:
                    try:
                        products = await self.off_client.search_products(search_term, page_size=5)
                        sample_products.extend(products)
                        # Small delay to respect API limits
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.warning("Error searching for %s: %s", search_term, e)

            # Convert to unified format
            unified_foods = {}
            for off_item in sample_products:
                try:
                    unified_item = UnifiedFoodItem.from_off_item(off_item)
                    # Use a standardized name for the key
                    key = self._generate_food_key(unified_item.name)
                    unified_foods[key] = unified_item
                except Exception as e:
                    logger.warning("Error converting OFF item to unified format: %s", e)

            # Calculate new version info
            new_version = now_utc().strftime("%Y%m%d_%H%M%S")

            # Calculate checksum for change detection
            temp_checksum = self._calculate_checksum(
                {name: self._food_to_dict(food) for name, food in unified_foods.items()}
            )

            # Check if data actually changed (unless forced)
            if not force and current_version and current_version.checksum == temp_checksum:
                return UpdateResult(
                    success=True,
                    source=source,
                    old_version=old_version,
                    new_version=old_version,  # No change
                    records_added=0,
                    records_updated=0,
                    records_removed=0,
                    errors=[],
                    duration_seconds=0.0,
                )

            # Validate new data
            validation_errors = await self._validate_food_data(unified_foods)
            if validation_errors:
                return UpdateResult(
                    success=False,
                    source=source,
                    old_version=old_version,
                    new_version=None,
                    records_added=0,
                    records_updated=0,
                    records_removed=0,
                    errors=validation_errors,
                    duration_seconds=0.0,
                )

            # Calculate changes
            old_foods = {}
            if current_version:
                try:
                    old_foods = await self._load_backup(source, current_version.version)
                except Exception as e:
                    logger.warning("Could not load old data for comparison: %s", e)

            records_added = len(unified_foods) - len(old_foods)
            records_updated = len(set(unified_foods.keys()) & set(old_foods.keys()))
            records_removed = len(old_foods) - len(unified_foods)

            actual_record_count, checksum = await self._get_validated_record_count_and_checksum(
                source, unified_foods
            )

            # Update version tracking
            new_db_version = DatabaseVersion(
                source=source,
                version=new_version,
                last_updated=isoformat_utc(),
                record_count=actual_record_count,
                checksum=checksum,
                metadata={
                    "update_type": "forced" if force else "scheduled",
                    "api_source": "Open Food Facts",
                    "sample_size": len(sample_products),
                },
            )

            self.versions[source] = new_db_version
            self._save_versions()

            # Clean up old backups
            await self._cleanup_old_backups(source)

            logger.info("Successfully updated %s database: %d foods", source, len(unified_foods))

            return UpdateResult(
                success=True,
                source=source,
                old_version=old_version,
                new_version=new_version,
                records_added=max(0, records_added),
                records_updated=records_updated,
                records_removed=max(0, records_removed),
                errors=[],
                duration_seconds=0.0,
            )

        except Exception as e:
            logger.error("Error updating %s database: %s", source, e)
            return UpdateResult(
                success=False,
                source=source,
                old_version=old_version,
                new_version=None,
                records_added=0,
                records_updated=0,
                records_removed=0,
                errors=[str(e)],
                duration_seconds=0.0,
            )

    async def _get_actual_record_count(self, source: str) -> int:
        """Get the actual record count from the existing database."""
        try:
            # Try to count from cache files
            cache_dir = Path(self.cache_dir)
            if source == "openfoodfacts":
                # Check for SQLite database first
                sqlite_file = cache_dir / self._OFF_SQLITE_FILENAME
                if sqlite_file.exists():
                    import sqlite3

                    conn = sqlite3.connect(str(sqlite_file))
                    try:
                        cur = conn.execute("SELECT COUNT(*) FROM products")
                        (count,) = cur.fetchone()
                        return int(count or 0)
                    finally:
                        conn.close()

                export_file = self._find_off_export_file(cache_dir, ("jsonl", "csv"))
                if export_file:
                    if export_file.suffix in {".csv", ".tsv"}:
                        with export_file.open("r", encoding="utf-8") as f:
                            count = sum(1 for _ in f)
                            return int(max(0, count - 1))
                    else:
                        with export_file.open("r", encoding="utf-8") as f:
                            count = sum(1 for _ in f)
                            return int(count)

            # If no database files found, return 0
            logger.warning("No database files found for %s", source)
            return 0

        except Exception as e:
            logger.error("Error getting record count for %s: %s", source, e)
            return 0

    async def _get_cache_data_for_checksum(self, source: str) -> Dict[str, Any]:
        """Get cache data for checksum calculation."""
        try:
            cache_dir = self.cache_dir
            if source == "openfoodfacts":
                # Try to get data from SQLite cache
                sqlite_file = cache_dir / self._OFF_SQLITE_FILENAME
                if sqlite_file.exists():
                    import sqlite3

                    conn = sqlite3.connect(str(sqlite_file))
                    try:
                        cur = conn.execute("SELECT name, data FROM products")
                        cache_data = {}
                        for name, data in cur:
                            try:
                                # For checksum purposes, we can hash the raw data without parsing JSON
                                # This avoids the memory overhead of json.loads() for every row
                                # If we only need checksums, hash the raw data string
                                checksum = hashlib.sha256(data.encode("utf-8")).hexdigest()
                                cache_data[name] = {"checksum": checksum}
                            except (json.JSONDecodeError, UnicodeEncodeError):
                                continue
                        return cache_data
                    finally:
                        conn.close()

                json_export = self._find_off_export_file(Path(str(cache_dir)), ("jsonl",))
                if json_export:
                    cache_data = {}
                    with json_export.open("r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                data = json.loads(line.strip())
                            except json.JSONDecodeError:
                                continue
                            if isinstance(data, dict) and "name" in data:
                                cache_data[data["name"]] = data
                    return cache_data

                csv_export = self._find_off_export_file(Path(str(cache_dir)), ("csv",))
                if csv_export:
                    cache_data = {}
                    with csv_export.open("r", encoding="utf-8") as f:
                        import csv

                        reader = csv.DictReader(f)
                        for row in reader:
                            if isinstance(row, dict) and "name" in row:
                                cache_data[row["name"]] = row
                    return cache_data
        except Exception as e:
            logger.warning("Could not get cache data for checksum for %s: %s", source, e)

        return {}

    async def _get_validated_record_count_and_checksum(
        self, source: str, unified_foods: Dict[str, UnifiedFoodItem]
    ) -> tuple[int, str]:
        """Return record count and checksum with cache-aware fallbacks."""
        record_count = await self._get_actual_record_count(source)
        if record_count == 0:
            record_count = len(unified_foods)

        cache_data = await self._get_cache_data_for_checksum(source)
        if cache_data:
            checksum = self._calculate_checksum(cache_data)
        else:
            checksum = self._calculate_checksum(
                {name: self._food_to_dict(food) for name, food in unified_foods.items()}
            )

        if record_count == 0:
            logger.warning(
                "No records found in %s database. This may indicate an empty cache.", source
            )
            logger.warning("Consider running the ingestion pipeline to populate the database.")

        return record_count, checksum

    def _generate_food_key(self, name: str) -> str:
        """Generate a standardized key for food items."""
        # Track which whitespace-separated tokens originally ended with accented 'é'
        original_tokens = name.strip().split()
        accented_e_flags: List[bool] = []
        for tok in original_tokens:
            lt = tok.strip().lower()
            accented_e_flags.append(lt.endswith("é"))

        # Build an ASCII, underscore-separated skeleton that preserves multiple underscores
        lower_name = name.lower()
        normalized = unicodedata.normalize("NFKD", lower_name)
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        # Replace any whitespace run with single underscore
        s = re.sub(r"\s+", "_", ascii_name)
        # Remove any non [a-z0-9_]
        key = "".join(ch for ch in s if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "_")

        # Trim any leading/trailing underscores
        key = key.strip("_")

        # Now trim trailing 'e' only for parts corresponding to original tokens
        # that ended with accented 'é'. Determine which original tokens are
        # alphanumeric (non-empty after cleaning) to align with parts.
        token_flags_alnum: List[bool] = []
        for tok, flag in zip(original_tokens, accented_e_flags):
            norm_tok = (
                unicodedata.normalize("NFKD", tok.lower()).encode("ascii", "ignore").decode("ascii")
            )
            alnum_tok = "".join(ch for ch in norm_tok if ch.isalnum())
            if alnum_tok:
                token_flags_alnum.append(flag)
        # Iterate parts, mapping flags to non-empty parts only
        parts = key.split("_")
        new_parts: List[str] = []
        flag_idx = 0
        for part in parts:
            if part == "":
                new_parts.append(part)
                continue
            # Map next available flag if any
            flag = token_flags_alnum[flag_idx] if flag_idx < len(token_flags_alnum) else False
            if flag and part.endswith("e"):
                part = part[:-1]
            new_parts.append(part)
            flag_idx += 1

        key2 = "_".join(new_parts)

        # Collapse any run of 3+ underscores into exactly two underscores
        key2 = re.sub(r"_{3,}", "__", key2)
        # Trim potential leading/trailing underscores again
        return key2.strip("_")

    async def _validate_food_data(self, foods: Dict[str, UnifiedFoodItem]) -> List[str]:
        """
        RU: Проверяет валидность данных о продуктах.
        EN: Validate food data integrity and quality.
        """
        errors = []

        for name, food in foods.items():
            # Check required fields
            if not food.name or not food.source:
                errors.append(f"Food {name} missing required fields")
                continue

            # Check nutrition data quality
            nutrients = food.nutrients_per_100g

            # Should have at least ONE primary macronutrient with meaningful value
            # Note: carbs_g is optional - pure protein/fat foods may have 0 carbs
            # Check VALUES not just key presence (setdefault ensures keys always exist)
            protein_g = float(nutrients.get("protein_g", 0.0) or 0.0)
            fat_g = float(nutrients.get("fat_g", 0.0) or 0.0)

            if protein_g <= 0.0 and fat_g <= 0.0:
                errors.append(
                    f"Food {name} missing primary macronutrients (needs protein_g OR fat_g > 0)"
                )

            # Check for reasonable values
            for nutrient, value in nutrients.items():
                if value < 0:
                    errors.append(f"Food {name} has negative {nutrient}: {value}")
                elif nutrient.endswith("_g") and value > 100:
                    errors.append(f"Food {name} has unrealistic {nutrient}: {value}g per 100g")

        return errors

    async def _create_backup(self, source: str, version: str):
        """Create backup of current database version."""
        try:
            current_data = await self.unified_db.get_common_foods_database()
            backup_file = self.cache_dir / f"{source}_backup_{version}.json"

            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(
                    {name: self._food_to_dict(food) for name, food in current_data.items()},
                    f,
                    indent=2,
                )

            logger.info("Created backup for %s version %s", source, version)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("Error creating backup for %s: %s", source, str(exc), exc_info=True)
        except Exception as exc:
            logger.error(
                "Unexpected error creating backup for %s: %s", source, str(exc), exc_info=True
            )

    async def _load_backup(self, source: str, version: str) -> Dict[str, UnifiedFoodItem]:
        """Load backup database version."""
        backup_file = self.cache_dir / f"{source}_backup_{version}.json"

        try:
            with open(backup_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    logger.debug("Backup file %s is empty", backup_file)
                    return {}
                data = json.loads(content)
        except json.JSONDecodeError as json_err:
            logger.debug("Failed to parse backup file %s: %s", backup_file, str(json_err))
            return {}
        except FileNotFoundError:
            logger.debug("Backup file %s not found", backup_file)
            return {}

        # Basic schema validation: ensure minimal keys exist
        required = {
            "name",
            "nutrients_per_100g",
            "cost_per_100g",
            "tags",
            "availability_regions",
            "source",
            "source_id",
        }
        foods: Dict[str, UnifiedFoodItem] = {}
        if not isinstance(data, dict):
            logger.debug("Backup file %s does not contain a dict", backup_file)
            return {}

        for name, food_data in data.items():
            try:
                if not isinstance(food_data, dict) or not required.issubset(food_data.keys()):
                    continue
                foods[name] = UnifiedFoodItem(**food_data)
            except (TypeError, ValueError) as parse_err:
                logger.debug("Skipping malformed backup entry %s: %s", name, parse_err)
                continue

        return foods

    def _food_to_dict(self, food: Any) -> Dict[str, Any]:
        """Safely convert a food item to a serializable dict.

        - If dataclass: use asdict
        - If dict: return as-is
        - If has to_dict/model_dump: call it
        - Fallback: return a dict with all expected keys and placeholder values
        """
        try:
            # Only call asdict on dataclass instances, not types
            if is_dataclass(food) and not isinstance(food, type):
                return asdict(food)
        except (TypeError, ValueError) as dataclass_err:
            logger.debug("Failed dataclass conversion for %s: %s", food, dataclass_err)

        if isinstance(food, dict):
            return food

        for method_name in ("to_dict", "model_dump"):
            if hasattr(food, method_name):
                try:
                    result = getattr(food, method_name)()
                    return dict(result) if not isinstance(result, dict) else result
                except (TypeError, ValueError, AttributeError) as transform_err:
                    logger.debug(
                        "Conversion method %s failed for %s: %s", method_name, food, transform_err
                    )
                    continue

        # Fallback: return a dict with all required keys and placeholder values
        food_id = getattr(food, "id", None)
        food_name = getattr(food, "name", None)
        food_identifier = (
            food_id if food_id is not None else (food_name if food_name is not None else "unknown")
        )
        logger.warning(
            "Using fallback placeholder serialization for food item '%s' (dataclass conversion and method-based transforms failed)",
            food_identifier,
        )
        return {
            "name": getattr(food, "name", "unknown"),
            "nutrients_per_100g": getattr(food, "nutrients_per_100g", {}),
            "cost_per_100g": getattr(food, "cost_per_100g", 0.0),
            "tags": getattr(food, "tags", []),
            "availability_regions": getattr(food, "availability_regions", []),
            "source": getattr(food, "source", "unknown"),
            "source_id": getattr(food, "source_id", "unknown"),
        }

    async def _cleanup_old_backups(self, source: str):
        """Remove old backup files beyond the retention limit."""
        try:
            backup_pattern = f"{source}_backup_*.json"
            backup_files = list(self.cache_dir.glob(backup_pattern))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            # Remove old backups beyond the limit
            for old_backup in backup_files[self.max_rollback_versions :]:
                old_backup.unlink()
                logger.info("Removed old backup: %s", old_backup.name)

        except Exception as exc:
            logger.error("Error cleaning up backups for %s: %s", source, str(exc), exc_info=True)

    async def rollback_database(self, source: str, target_version: str) -> bool:
        """
        RU: Откатывает базу данных к предыдущей версии.
        EN: Rollback database to a previous version.

        Args:
            source: Data source name
            target_version: Version to rollback to

        Returns:
            True if rollback successful, False otherwise
        """
        try:
            # Load backup data
            backup_data = await self._load_backup(source, target_version)

            # Restore the data (implementation depends on storage method)
            # For now, just update the version tracking
            if source in self.versions:
                old_version = self.versions[source]

                # Create new version entry for rollback
                rollback_version = DatabaseVersion(
                    source=source,
                    version=f"{target_version}_rollback_{now_utc().strftime('%H%M%S')}",
                    last_updated=isoformat_utc(),
                    record_count=len(backup_data),
                    checksum=self._calculate_checksum(
                        {name: asdict(food) for name, food in backup_data.items()}
                    ),
                    metadata={
                        "update_type": "rollback",
                        "rolled_back_from": old_version.version,
                        "rolled_back_to": target_version,
                    },
                )

                self.versions[source] = rollback_version
                self._save_versions()

                logger.info("Successfully rolled back %s to version %s", source, target_version)
                return True

        except Exception as exc:
            logger.error(
                "Error rolling back %s to %s: %s", source, target_version, str(exc), exc_info=True
            )

        return False

    def add_update_callback(self, callback: Callable[[UpdateResult], None]):
        """
        RU: Добавляет callback для уведомлений об обновлениях.
        EN: Add callback for update notifications.
        """
        self.update_callbacks.append(callback)

    def get_database_status(self) -> Dict[str, Dict[str, Any]]:
        """
        RU: Получает статус всех баз данных.
        EN: Get status of all databases.
        """
        status = {}

        for source, version in self.versions.items():
            last_update = parse_iso8601(version.last_updated)
            time_since_update = now_utc() - last_update

            status[source] = {
                "version": version.version,
                "last_updated": version.last_updated,
                "hours_since_update": time_since_update.total_seconds() / 3600,
                "record_count": version.record_count,
                "checksum": version.checksum[:8] + "...",  # Truncated for display
                "metadata": version.metadata,
            }

        return status

    async def close(self):
        """Close all connections."""
        await self.usda_client.close()
        if self.off_client and OFF_AVAILABLE:
            await self.off_client.close()
        await self.unified_db.close()


# Convenience functions for scheduled updates
async def run_scheduled_update(
    update_manager: DatabaseUpdateManager,
) -> Dict[str, UpdateResult]:
    """
    RU: Запускает плановое обновление всех баз данных.
    EN: Run scheduled update for all databases.
    """
    available_updates = await update_manager.check_for_updates()
    results = {}

    for source, has_updates in available_updates.items():
        if has_updates:
            logger.info("Running scheduled update for %s", source)
            result = await update_manager.update_database(source)
            results[source] = result
        else:
            logger.info("No updates available for %s", source)

    return results


def _empty_scheduler_status() -> dict[str, object]:
    """Return deterministic status payload when scheduler is not initialized."""
    return {
        "scheduler": {
            "is_running": False,
            "last_update_check": None,
            "update_interval_hours": None,
            "retry_counts": {},
        },
        "databases": {},
    }


async def get_update_status() -> dict[str, object]:
    """
    Async wrapper returning current scheduler status.

    Deterministic and side-effect free:
    - does not create or start scheduler instance
    - does not mutate scheduler state
    """
    from . import scheduler as scheduler_mod

    scheduler = scheduler_mod._scheduler_instance
    if scheduler is None:
        return _empty_scheduler_status()
    return scheduler.get_status()


def __getattr__(name: str) -> object:
    """Lazy re-export of scheduler API to avoid import cycle at module import time."""
    if name in {"DatabaseUpdateScheduler", "get_update_scheduler"}:
        from . import scheduler as scheduler_mod

        return getattr(scheduler_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":  # pragma: no cover
    # Test the update manager
    async def test_update_manager():
        manager = DatabaseUpdateManager(update_interval_hours=1)  # Short interval for testing

        try:
            print("Testing database update manager...")

            # Check current status
            status = manager.get_database_status()
            print(f"Current database status: {status}")

            # Check for updates
            updates = await manager.check_for_updates()
            print(f"Updates available: {updates}")

            # Run update if available
            if updates.get("usda", False):
                print("Running USDA update...")
                result = await manager.update_database("usda")
                print(f"Update result: {result}")

        finally:
            await manager.close()

    # Run test
    asyncio.run(test_update_manager())
