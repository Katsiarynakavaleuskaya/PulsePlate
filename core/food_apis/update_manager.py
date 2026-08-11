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
import os
import re
import tempfile
import unicodedata
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
)

from core.food_sources.snapshot_manager import SnapshotMeta
from core.off_nutrition.bridge import (
    merge_wire_nutrition_sources,
    nutrition_inputs_from_unified_wire,
)

if TYPE_CHECKING:
    from core.food_sources.off_delta import OFFTransport

from .openfoodfacts_client import OFF_AVAILABLE, OFFClient
from .unified_db import (
    COMMON_FOODS_CACHE_SCHEMA_VERSION,
    COMMON_FOODS_MANIFEST,
    COMMON_FOODS_MANIFEST_VERSION,
    CommonFoodsCacheAdmissionError,
    UnifiedFoodDatabase,
    UnifiedFoodItem,
    _COMMON_FOOD_ITEM_FIELDS,
    _NUTRITION_INPUT_FIELDS,
    _PRIMARY_MACRONUTRIENT_DEFAULTS,
    _has_finite_numeric_shape,
    _load_common_foods_json,
)
from .usda_client import USDAClient
from ..time_utils import isoformat_utc, now_utc, parse_iso8601

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def _maybe_await(value: Union[T, Awaitable[T]]) -> T:
    """Return awaited value if awaitable, otherwise the value itself."""
    if inspect.isawaitable(value):
        return await value
    return value


def _restore_exact_file_state(path: Path, existed: bool, content: bytes) -> None:
    """Restore one same-parent file state after a bounded publication failure."""
    temporary_path: Path | None = None
    try:
        if existed:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.restore.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        else:
            path.unlink(missing_ok=True)

        parent_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.error(
                    "File-state restore cleanup failed; category=%s",
                    type(exc).__name__,
                )


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

    def _save_versions(self) -> None:
        """Atomically publish database version information or raise."""
        temporary_path: Path | None = None
        try:
            if self.versions_file.is_symlink() or (
                self.versions_file.exists() and not self.versions_file.is_file()
            ):
                raise CommonFoodsCacheAdmissionError("Database versions path is not a regular file")
            data = {source: asdict(version) for source, version in self.versions.items()}
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.versions_file.parent,
                prefix=f".{self.versions_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(data, temporary_file, indent=2, allow_nan=False)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            with open(temporary_path, "r", encoding="utf-8") as temporary_file:
                if json.load(temporary_file) != data:
                    raise CommonFoodsCacheAdmissionError(
                        "Database versions staged content is inconsistent"
                    )

            if self.versions_file.is_symlink() or (
                self.versions_file.exists() and not self.versions_file.is_file()
            ):
                raise CommonFoodsCacheAdmissionError("Database versions path is not a regular file")
            prior_target_exists = self.versions_file.exists()
            prior_target_bytes = self.versions_file.read_bytes() if prior_target_exists else b""
            os.replace(temporary_path, self.versions_file)
            temporary_path = None
            try:
                parent_descriptor = os.open(self.versions_file.parent, os.O_RDONLY)
                try:
                    os.fsync(parent_descriptor)
                finally:
                    os.close(parent_descriptor)
            except OSError:
                _restore_exact_file_state(
                    self.versions_file,
                    prior_target_exists,
                    prior_target_bytes,
                )
                raise
        except CommonFoodsCacheAdmissionError:
            raise
        except Exception as exc:
            raise CommonFoodsCacheAdmissionError("Database versions publication failed") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as exc:
                    logger.error(
                        "Database versions temporary cleanup failed; category=%s",
                        type(exc).__name__,
                    )

    def sync_openfoodfacts_raw_snapshot(
        self,
        raw_root: str | Path | None = None,
        *,
        project_root: Path | None = None,
        force: bool = False,
        transport: "OFFTransport | None" = None,
        today_provider: Callable[[], date] | None = None,
    ) -> SnapshotMeta | None:
        """
        Sync OFF raw snapshots into the canonical raw tree (lazy import of sync module).

        RU: Делегирует загрузку сырого снапшота OFF в ``snapshot_sync``.
        EN: Delegates OFF raw snapshot sync to :mod:`core.food_apis.snapshot_sync`.
        When ``raw_root`` is None, ``project_root`` selects the default snapshot tree
        (same semantics as :func:`snapshot_sync.default_raw_snapshot_root`).
        """
        from . import snapshot_sync

        root = Path(raw_root) if raw_root is not None else None
        return snapshot_sync.sync_openfoodfacts_snapshot(
            root,
            project_root=project_root,
            force=force,
            transport=transport,
            today_provider=today_provider,
        )

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for data integrity."""
        # Convert to sorted JSON string for consistent hashing
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

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
        active_cache_file = self.unified_db.cache_dir / "common_foods.json"
        if active_cache_file.is_symlink() or (
            active_cache_file.exists() and not active_cache_file.is_file()
        ):
            return UpdateResult(
                success=False,
                source=source,
                old_version=old_version,
                new_version=None,
                records_added=0,
                records_updated=0,
                records_removed=0,
                errors=["common_food_cache_admission_failed"],
                duration_seconds=0.0,
            )
        prior_cache_exists = active_cache_file.exists()
        prior_cache_bytes = active_cache_file.read_bytes() if prior_cache_exists else b""
        acquisition_completed = False
        metadata_committed = False

        def compensate_active_cache() -> None:
            if not acquisition_completed or metadata_committed:
                return
            try:
                _restore_exact_file_state(
                    active_cache_file,
                    prior_cache_exists,
                    prior_cache_bytes,
                )
            except Exception as exc:
                raise CommonFoodsCacheAdmissionError("USDA update compensation failed") from exc

        try:
            # Create backup of current data
            if current_version:
                await self._create_backup(source, current_version.version)

            # Get updated common foods from USDA
            logger.info("Fetching updated USDA food data...")
            updated_foods = await self.unified_db.get_common_foods_database(force_refresh=force)
            acquisition_completed = True

            # Calculate new version info
            new_version = now_utc().strftime("%Y%m%d_%H%M%S")
            checksum = self._calculate_checksum(
                {name: self._food_to_dict(food) for name, food in updated_foods.items()}
            )

            # Check if data actually changed (unless forced)
            if not force and current_version and current_version.checksum == checksum:
                metadata_committed = True
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
                try:
                    compensate_active_cache()
                except CommonFoodsCacheAdmissionError:
                    validation_errors = ["common_food_cache_admission_failed"]
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
            metadata_committed = True

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

        except asyncio.CancelledError:
            if current_version is None:
                self.versions.pop(source, None)
            else:
                self.versions[source] = current_version
            try:
                compensate_active_cache()
            except CommonFoodsCacheAdmissionError as exc:
                logger.error(
                    "USDA cancellation compensation failed; category=%s",
                    type(exc).__name__,
                )
            raise
        except CommonFoodsCacheAdmissionError as exc:
            if current_version is None:
                self.versions.pop(source, None)
            else:
                self.versions[source] = current_version
            try:
                compensate_active_cache()
            except CommonFoodsCacheAdmissionError as compensation_exc:
                logger.error(
                    "USDA update compensation failed; category=%s",
                    type(compensation_exc).__name__,
                )
            logger.error(
                "Database update stopped; source=%s; category=%s",
                source,
                type(exc).__name__,
            )
            return UpdateResult(
                success=False,
                source=source,
                old_version=old_version,
                new_version=None,
                records_added=0,
                records_updated=0,
                records_removed=0,
                errors=["common_food_cache_admission_failed"],
                duration_seconds=0.0,
            )
        except Exception as e:
            if current_version is None:
                self.versions.pop(source, None)
            else:
                self.versions[source] = current_version
            try:
                compensate_active_cache()
            except CommonFoodsCacheAdmissionError as compensation_exc:
                logger.error(
                    "USDA update compensation failed; category=%s",
                    type(compensation_exc).__name__,
                )
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
        published_backup_file: Path | None = None
        prior_backup_exists = False
        prior_backup_bytes = b""
        metadata_committed = False

        def compensate_backup_publication() -> None:
            if published_backup_file is None or metadata_committed:
                return
            try:
                _restore_exact_file_state(
                    published_backup_file,
                    prior_backup_exists,
                    prior_backup_bytes,
                )
            except Exception as exc:
                raise CommonFoodsCacheAdmissionError(
                    "Open Food Facts update compensation failed"
                ) from exc

        try:
            # Create backup of current data
            if current_version:
                await self._create_backup(source, current_version.version)

            # For Open Food Facts, we'll fetch a sample of popular products
            # In a real implementation, this would be more sophisticated
            logger.info("Fetching Open Food Facts data...")

            # This is a simplified approach - in reality, we'd want to implement
            # a more comprehensive update strategy for Open Food Facts.
            if self.off_client is None:
                raise CommonFoodsCacheAdmissionError("Open Food Facts client is unavailable")
            sample_products = []
            common_searches = (
                "apple",
                "banana",
                "chicken",
                "bread",
                "milk",
                "cheese",
                "rice",
            )
            for search_index, search_term in enumerate(common_searches):
                try:
                    products = await self.off_client.search_products(search_term, page_size=5)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    raise CommonFoodsCacheAdmissionError(
                        "Open Food Facts acquisition sweep failed"
                    ) from exc
                if not products:
                    raise CommonFoodsCacheAdmissionError(
                        "Open Food Facts acquisition sweep was incomplete"
                    )
                sample_products.extend(products)
                if search_index < len(common_searches) - 1:
                    await asyncio.sleep(0.1)

            # Convert to unified format
            unified_foods = {}
            for off_item in sample_products:
                try:
                    unified_item = UnifiedFoodItem.from_off_item(off_item)
                except Exception as exc:
                    raise CommonFoodsCacheAdmissionError(
                        "Open Food Facts conversion sweep failed"
                    ) from exc
                # Use a standardized name for the key
                key = self._generate_food_key(unified_item.name)
                unified_foods[key] = unified_item
            if not unified_foods:
                raise CommonFoodsCacheAdmissionError("Open Food Facts acquired snapshot is empty")

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

            backup_file = self._resolve_backup_path(source, new_version)
            prior_backup_exists = backup_file.exists()
            prior_backup_bytes = backup_file.read_bytes() if prior_backup_exists else b""
            self._write_backup_snapshot(source, new_version, unified_foods)
            published_backup_file = backup_file
            persisted_foods = await self._load_backup(source, new_version)
            if not persisted_foods:
                raise CommonFoodsCacheAdmissionError(
                    "Open Food Facts persisted snapshot is unrestorable"
                )
            persisted_mapping = {name: asdict(food) for name, food in persisted_foods.items()}
            actual_record_count = len(persisted_mapping)
            checksum = self._calculate_checksum(persisted_mapping)

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
            metadata_committed = True

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

        except asyncio.CancelledError:
            if current_version is None:
                self.versions.pop(source, None)
            else:
                self.versions[source] = current_version
            try:
                compensate_backup_publication()
            except CommonFoodsCacheAdmissionError as exc:
                logger.error(
                    "OFF cancellation compensation failed; category=%s",
                    type(exc).__name__,
                )
            raise
        except CommonFoodsCacheAdmissionError as exc:
            if current_version is None:
                self.versions.pop(source, None)
            else:
                self.versions[source] = current_version
            try:
                compensate_backup_publication()
            except CommonFoodsCacheAdmissionError as compensation_exc:
                logger.error(
                    "OFF update compensation failed; category=%s",
                    type(compensation_exc).__name__,
                )
            logger.error(
                "Database update stopped; source=%s; category=%s",
                source,
                type(exc).__name__,
            )
            return UpdateResult(
                success=False,
                source=source,
                old_version=old_version,
                new_version=None,
                records_added=0,
                records_updated=0,
                records_removed=0,
                errors=["common_food_cache_admission_failed"],
                duration_seconds=0.0,
            )
        except Exception as e:
            if current_version is None:
                self.versions.pop(source, None)
            else:
                self.versions[source] = current_version
            try:
                compensate_backup_publication()
            except CommonFoodsCacheAdmissionError as compensation_exc:
                logger.error(
                    "OFF update compensation failed; category=%s",
                    type(compensation_exc).__name__,
                )
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

    async def _create_backup(self, source: str, version: str) -> None:
        """Create backup of current database version."""
        try:
            backup_file = self._resolve_backup_path(source, version)
            current_data: object
            if source == "usda":
                cache_file = self.unified_db.cache_dir / "common_foods.json"
                if cache_file.is_symlink() or (cache_file.exists() and not cache_file.is_file()):
                    raise CommonFoodsCacheAdmissionError(
                        "Established common-food cache is not a regular file"
                    )
                with open(cache_file, "r", encoding="utf-8") as file_object:
                    loaded = _load_common_foods_json(file_object)
                if type(loaded) is not dict:
                    raise ValueError("common-food cache must be a mapping")
                if set(loaded) == {"schema_version", "manifest_version", "items"}:
                    current_data = self.unified_db._validate_common_foods_envelope(loaded)
                else:
                    if set(loaded) != set(COMMON_FOODS_MANIFEST):
                        raise CommonFoodsCacheAdmissionError(
                            "Legacy USDA backup membership is not exact"
                        )
                    reconstructed = self._reconstruct_backup_snapshot(loaded)
                    current_data = self.unified_db._validate_common_foods_envelope(
                        {
                            "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
                            "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
                            "items": {name: asdict(food) for name, food in reconstructed.items()},
                        }
                    )
            elif source == "openfoodfacts":
                with open(backup_file, "r", encoding="utf-8") as file_object:
                    current_data = _load_common_foods_json(file_object)
                self._reconstruct_backup_snapshot(current_data)
            else:
                raise ValueError("unsupported backup source")

            if source == "usda":
                self._write_backup_snapshot(source, version, current_data)

            logger.info("Prepared backup for %s version %s", source, version)
        except Exception as exc:
            raise CommonFoodsCacheAdmissionError(
                "Established source snapshot cannot be backed up"
            ) from exc

    def _resolve_backup_path(self, source: str, version: str | None) -> Path:
        """Resolve one supported backup path inside the configured cache directory."""
        if source not in {"usda", "openfoodfacts"}:
            raise CommonFoodsCacheAdmissionError("Unsupported backup source")

        cache_dir = self.cache_dir.path.resolve(strict=True)
        if not cache_dir.is_dir():
            raise CommonFoodsCacheAdmissionError("Backup cache directory is invalid")
        if version is None:
            return cache_dir
        if (
            type(version) is not str
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", version) is None
            or ".." in version
        ):
            raise CommonFoodsCacheAdmissionError("Invalid backup version")

        backup_file = cache_dir / f"{source}_backup_{version}.json"
        if backup_file.parent.resolve(strict=True) != cache_dir:
            raise CommonFoodsCacheAdmissionError("Backup path escapes cache directory")
        if backup_file.is_symlink() or (backup_file.exists() and not backup_file.is_file()):
            raise CommonFoodsCacheAdmissionError("Backup path is not a regular file")
        return backup_file

    @staticmethod
    def _reconstruct_backup_snapshot(snapshot: object) -> Dict[str, UnifiedFoodItem]:
        """Reconstruct one complete, non-empty source snapshot or reject it."""
        if type(snapshot) is not dict or not snapshot:
            raise CommonFoodsCacheAdmissionError("Backup snapshot is empty or invalid")

        foods: Dict[str, UnifiedFoodItem] = {}
        admitted_evidence_pairs: set[tuple[str, str]] = set()
        for name, food_data in snapshot.items():
            if type(name) is not str or not name.strip():
                raise CommonFoodsCacheAdmissionError("Backup snapshot contains invalid identity")
            if isinstance(food_data, UnifiedFoodItem):
                candidate = asdict(food_data)
            elif type(food_data) is dict:
                candidate = food_data
            else:
                raise CommonFoodsCacheAdmissionError("Backup snapshot contains invalid item")
            if set(candidate) != _COMMON_FOOD_ITEM_FIELDS:
                raise CommonFoodsCacheAdmissionError("Backup snapshot contains invalid fields")

            identity_fields = (candidate["name"], candidate["source"], candidate["source_id"])
            if any(type(value) is not str or not value.strip() for value in identity_fields):
                raise CommonFoodsCacheAdmissionError("Backup snapshot contains invalid identity")
            category = candidate["category"]
            if category is not None and type(category) is not str:
                raise CommonFoodsCacheAdmissionError("Backup snapshot contains invalid category")
            if any(
                type(candidate[field]) is not list
                or any(type(value) is not str for value in candidate[field])
                for field in ("tags", "availability_regions")
            ):
                raise CommonFoodsCacheAdmissionError("Backup snapshot contains invalid lists")

            nutrients = candidate["nutrients_per_100g"]
            cost = candidate["cost_per_100g"]
            confidence = candidate["nutrition_confidence"]
            if (
                type(nutrients) is not dict
                or not nutrients
                or any(
                    type(key) is not str
                    or not key.strip()
                    or not _has_finite_numeric_shape(value)
                    or value < 0.0
                    for key, value in nutrients.items()
                )
                or any(key.endswith("_g") and value > 100.0 for key, value in nutrients.items())
                or (nutrients.get("protein_g", 0.0) <= 0.0 and nutrients.get("fat_g", 0.0) <= 0.0)
                or not _has_finite_numeric_shape(cost)
                or cost < 0.0
                or not _has_finite_numeric_shape(confidence)
                or not 0.0 <= confidence <= 1.0
            ):
                raise CommonFoodsCacheAdmissionError("Backup snapshot contains invalid nutrition")

            nutrition_inputs = candidate["nutrition_inputs"]
            if type(nutrition_inputs) is not list or not nutrition_inputs:
                raise CommonFoodsCacheAdmissionError("Backup snapshot lacks nutrition evidence")
            item_evidence_pairs: set[tuple[str, str]] = set()
            source_id_is_bound = False
            for nutrition_input in nutrition_inputs:
                if (
                    type(nutrition_input) is not dict
                    or set(nutrition_input) != _NUTRITION_INPUT_FIELDS
                    or type(nutrition_input["source"]) is not str
                    or not nutrition_input["source"].strip()
                    or (
                        nutrition_input["record_id"] is not None
                        and (
                            type(nutrition_input["record_id"]) is not str
                            or not nutrition_input["record_id"].strip()
                        )
                    )
                    or (
                        nutrition_input["version_ref"] is not None
                        and (
                            type(nutrition_input["version_ref"]) is not str
                            or not nutrition_input["version_ref"].strip()
                        )
                    )
                ):
                    raise CommonFoodsCacheAdmissionError(
                        "Backup snapshot contains invalid evidence identity"
                    )
                input_nutrients = nutrition_input["nutrients"]
                raw_payload = nutrition_input["raw_payload"]
                if (
                    type(input_nutrients) is not dict
                    or not input_nutrients
                    or any(
                        type(key) is not str
                        or not key.strip()
                        or not _has_finite_numeric_shape(value)
                        or value < 0.0
                        for key, value in input_nutrients.items()
                    )
                    or type(raw_payload) is not dict
                    or any(
                        type(key) is not str
                        or not key.strip()
                        or not (
                            value is None
                            or type(value) is str
                            or (type(value) in (int, float) and _has_finite_numeric_shape(value))
                        )
                        for key, value in raw_payload.items()
                    )
                ):
                    raise CommonFoodsCacheAdmissionError(
                        "Backup snapshot contains invalid nutrition evidence"
                    )

                record_id = nutrition_input["record_id"]
                if record_id is not None:
                    evidence_pair = (
                        nutrition_input["source"].strip().lower(),
                        record_id.strip(),
                    )
                    if evidence_pair in item_evidence_pairs:
                        raise CommonFoodsCacheAdmissionError(
                            "Backup snapshot contains duplicate nutrition evidence"
                        )
                    if evidence_pair in admitted_evidence_pairs:
                        raise CommonFoodsCacheAdmissionError(
                            "Backup snapshot reuses nutrition evidence across items"
                        )
                    item_evidence_pairs.add(evidence_pair)
                    if record_id.strip() == candidate["source_id"].strip():
                        source_id_is_bound = True

            if not source_id_is_bound:
                raise CommonFoodsCacheAdmissionError(
                    "Backup snapshot source identity is not bound to evidence"
                )
            admitted_evidence_pairs.update(item_evidence_pairs)

            provenance = candidate["nutrition_provenance"]
            nutrient_confidence = candidate["nutrition_nutrient_confidence"]
            if (
                type(provenance) is not dict
                or not provenance
                or any(
                    type(key) is not str
                    or not key.strip()
                    or type(value) is not str
                    or not value.strip()
                    for key, value in provenance.items()
                )
                or type(nutrient_confidence) is not dict
                or set(nutrient_confidence) != set(provenance)
                or not set(provenance).issubset(nutrients)
                or any(
                    not _has_finite_numeric_shape(value) or not 0.0 <= value <= 1.0
                    for value in nutrient_confidence.values()
                )
            ):
                raise CommonFoodsCacheAdmissionError(
                    "Backup snapshot contains invalid provenance evidence"
                )

            replayed_inputs = nutrition_inputs_from_unified_wire(
                nutrition_inputs_wire=nutrition_inputs,
                nutrients_per_100g=nutrients,
                fallback_source=nutrition_inputs[0]["source"],
                record_id=candidate["source_id"],
            )
            replayed = merge_wire_nutrition_sources(
                primary_inputs=replayed_inputs,
                secondary_inputs=[],
            )
            replayed_nutrients = dict(replayed.nutrients)
            for nutrient, default_value in _PRIMARY_MACRONUTRIENT_DEFAULTS.items():
                replayed_nutrients.setdefault(nutrient, default_value)
            if (
                replayed_nutrients != nutrients
                or dict(replayed.provenance) != provenance
                or dict(replayed.nutrient_confidence) != nutrient_confidence
                or replayed.confidence != confidence
            ):
                raise CommonFoodsCacheAdmissionError(
                    "Backup snapshot nutrition evidence does not replay"
                )
            try:
                foods[name] = UnifiedFoodItem(**candidate)
            except (TypeError, ValueError) as exc:
                raise CommonFoodsCacheAdmissionError(
                    "Backup snapshot contains unrestorable item"
                ) from exc
        return foods

    def _write_backup_snapshot(self, source: str, version: str, snapshot: object) -> None:
        """Validate and atomically publish one complete source snapshot."""
        backup_file = self._resolve_backup_path(source, version)
        foods = self._reconstruct_backup_snapshot(snapshot)
        temporary_path: Path | None = None
        rollback_path: Path | None = None
        try:
            serialized = json.dumps(
                {name: asdict(food) for name, food in foods.items()},
                indent=2,
                allow_nan=False,
            )
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=backup_file.parent,
                prefix=f".{backup_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(serialized)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            with open(temporary_path, "r", encoding="utf-8") as temporary_file:
                staged_snapshot = _load_common_foods_json(temporary_file)
            self._reconstruct_backup_snapshot(staged_snapshot)
            prior_target_exists = backup_file.exists()
            prior_target_bytes = backup_file.read_bytes() if prior_target_exists else b""
            os.replace(temporary_path, backup_file)
            temporary_path = None
            try:
                parent_descriptor = os.open(backup_file.parent, os.O_RDONLY)
                try:
                    os.fsync(parent_descriptor)
                finally:
                    os.close(parent_descriptor)
            except OSError:
                if prior_target_exists:
                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        dir=backup_file.parent,
                        prefix=f".{backup_file.name}.rollback.",
                        suffix=".tmp",
                        delete=False,
                    ) as rollback_file:
                        rollback_path = Path(rollback_file.name)
                        rollback_file.write(prior_target_bytes)
                        rollback_file.flush()
                        os.fsync(rollback_file.fileno())
                    os.replace(rollback_path, backup_file)
                    rollback_path = None
                else:
                    backup_file.unlink(missing_ok=True)

                rollback_parent_descriptor = os.open(backup_file.parent, os.O_RDONLY)
                try:
                    os.fsync(rollback_parent_descriptor)
                finally:
                    os.close(rollback_parent_descriptor)
                raise
        except CommonFoodsCacheAdmissionError:
            raise
        except Exception as exc:
            raise CommonFoodsCacheAdmissionError("Backup snapshot write failed") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as exc:
                    logger.error(
                        "Backup snapshot temporary cleanup failed; category=%s",
                        type(exc).__name__,
                    )
            if rollback_path is not None:
                try:
                    rollback_path.unlink(missing_ok=True)
                except OSError as exc:
                    logger.error(
                        "Backup snapshot rollback cleanup failed; category=%s",
                        type(exc).__name__,
                    )

    async def _load_backup(self, source: str, version: str) -> Dict[str, UnifiedFoodItem]:
        """Load a backup only when the complete snapshot is restorable."""
        try:
            backup_file = self._resolve_backup_path(source, version)
            with open(backup_file, "r", encoding="utf-8") as file_object:
                data = _load_common_foods_json(file_object)
            return self._reconstruct_backup_snapshot(data)
        except Exception as exc:
            logger.debug(
                "Backup snapshot rejected; source=%s; category=%s",
                source,
                type(exc).__name__,
            )
            return {}

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
            cache_dir = self._resolve_backup_path(source, None)
            backup_pattern = f"{source}_backup_*.json"
            backup_files: list[Path] = []
            prefix = f"{source}_backup_"
            for candidate in cache_dir.glob(backup_pattern):
                version = candidate.name[len(prefix) : -len(".json")]
                try:
                    backup_files.append(self._resolve_backup_path(source, version))
                except CommonFoodsCacheAdmissionError:
                    logger.warning(
                        "Ignoring invalid backup candidate during cleanup; "
                        "source=%s; category=CommonFoodsCacheAdmissionError",
                        source,
                    )
                    continue

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
        established_version = self.versions.get(source)
        published_rollback_file: Path | None = None
        prior_rollback_exists = False
        prior_rollback_bytes = b""
        active_cache_file: Path | None = None
        prior_active_exists = False
        prior_active_bytes = b""
        active_published = False
        metadata_committed = False

        def compensate_rollback_publication() -> None:
            try:
                if active_published and active_cache_file is not None:
                    _restore_exact_file_state(
                        active_cache_file,
                        prior_active_exists,
                        prior_active_bytes,
                    )

                if published_rollback_file is not None and not metadata_committed:
                    _restore_exact_file_state(
                        published_rollback_file,
                        prior_rollback_exists,
                        prior_rollback_bytes,
                    )
            except Exception as exc:
                raise CommonFoodsCacheAdmissionError(
                    "Rollback publication compensation failed"
                ) from exc

        try:
            # Load backup data
            backup_data = await self._load_backup(source, target_version)
            if not backup_data:
                logger.warning("Rollback refused; source=%s; backup is unrestorable", source)
                return False

            # Restore the data (implementation depends on storage method)
            # For now, just update the version tracking
            if source in self.versions:
                old_version = self.versions[source]
                rollback_version_name = f"{target_version}_rollback_{now_utc().strftime('%H%M%S')}"
                rollback_checksum = self._calculate_checksum(
                    {name: asdict(food) for name, food in backup_data.items()}
                )

                # Create new version entry for rollback
                rollback_version = DatabaseVersion(
                    source=source,
                    version=rollback_version_name,
                    last_updated=isoformat_utc(),
                    record_count=len(backup_data),
                    checksum=rollback_checksum,
                    metadata={
                        "update_type": "rollback",
                        "rolled_back_from": old_version.version,
                        "rolled_back_to": target_version,
                    },
                )

                active_envelope: dict[str, object] | None = None
                if source == "usda":
                    active_envelope = {
                        "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
                        "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
                        "items": {name: asdict(food) for name, food in backup_data.items()},
                    }
                    self.unified_db._validate_common_foods_envelope(active_envelope)

                rollback_file = self._resolve_backup_path(source, rollback_version_name)
                prior_rollback_exists = rollback_file.exists()
                prior_rollback_bytes = rollback_file.read_bytes() if prior_rollback_exists else b""
                self._write_backup_snapshot(source, rollback_version_name, backup_data)
                published_rollback_file = rollback_file
                if active_envelope is not None:
                    active_cache_file = self.unified_db.cache_dir / "common_foods.json"
                    if active_cache_file.is_symlink() or (
                        active_cache_file.exists() and not active_cache_file.is_file()
                    ):
                        raise CommonFoodsCacheAdmissionError(
                            "Active common-food cache is not a regular file"
                        )
                    prior_active_exists = active_cache_file.exists()
                    prior_active_bytes = (
                        active_cache_file.read_bytes() if prior_active_exists else b""
                    )
                    self.unified_db._publish_common_foods_envelope(
                        active_cache_file,
                        active_envelope,
                    )
                    active_published = True

                self.versions[source] = rollback_version
                self._save_versions()
                metadata_committed = True

                logger.info("Successfully rolled back %s to version %s", source, target_version)
                return True

        except asyncio.CancelledError:
            if established_version is None:
                self.versions.pop(source, None)
            else:
                self.versions[source] = established_version
            try:
                compensate_rollback_publication()
            except CommonFoodsCacheAdmissionError as exc:
                logger.error(
                    "Rollback cancellation compensation failed; category=%s",
                    type(exc).__name__,
                )
            raise
        except Exception as exc:
            if established_version is None:
                self.versions.pop(source, None)
            else:
                self.versions[source] = established_version
            try:
                compensate_rollback_publication()
            except CommonFoodsCacheAdmissionError as compensation_exc:
                logger.error(
                    "Rollback compensation failed; category=%s",
                    type(compensation_exc).__name__,
                )
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
    return cast(dict[str, object], scheduler.get_status())


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
