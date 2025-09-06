"""
Nutrition Database Auto-Update Manager

RU: Менеджер автообновления баз данных питания.
EN: Manager for automatically updating nutrition databases.

This module handles automatic updates from open food databases when new
information becomes available, with version tracking, validation, and rollback.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .openfoodfacts_client import OFF_AVAILABLE, OFFClient
from .unified_db import UnifiedFoodDatabase, UnifiedFoodItem
from .usda_client import USDAClient

logger = logging.getLogger(__name__)


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
        cache_dir: str = "cache/food_db",
        update_interval_hours: int = 24,
        max_rollback_versions: int = 5,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.update_interval = timedelta(hours=update_interval_hours)
        self.max_rollback_versions = max_rollback_versions

        # Data sources
        self.usda_client = USDAClient()
        self.off_client = OFFClient() if OFF_AVAILABLE else None
        self.unified_db = UnifiedFoodDatabase(str(self.cache_dir))

        # Update callbacks
        self.update_callbacks: List[Callable[[UpdateResult], None]] = []

        # Load version tracking
        self.versions_file = self.cache_dir / "database_versions.json"
        self.versions = self._load_versions()

    def _load_versions(self) -> Dict[str, DatabaseVersion]:
        """Load database version information."""
        if not self.versions_file.exists():
            return {}

        try:
            with open(self.versions_file, "r") as f:
                data = json.load(f)

            versions = {}
            for source, version_data in data.items():
                versions[source] = DatabaseVersion(**version_data)

            return versions

        except Exception as e:
            logger.error(f"Error loading versions: {e}")
            return {}

    def _save_versions(self):
        """Save database version information."""
        try:
            data = {source: asdict(version) for source, version in self.versions.items()}

            with open(self.versions_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving versions: {e}")

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
            logger.error(f"Error checking USDA updates: {e}")
            updates_available["usda"] = False

        # Check Open Food Facts updates
        if self.off_client and OFF_AVAILABLE:
            try:
                off_available = await self._check_off_updates()
                updates_available["openfoodfacts"] = off_available
            except Exception as e:
                logger.error(f"Error checking Open Food Facts updates: {e}")
                updates_available["openfoodfacts"] = False

        return updates_available

    async def _check_usda_updates(self) -> bool:
        """Check if USDA database has updates."""
        current_version = self.versions.get("usda")

        # If no current version, updates are available
        if not current_version:
            return True

        # Check if enough time has passed for an update
        last_update = datetime.fromisoformat(current_version.last_updated)
        if datetime.now() - last_update < self.update_interval:
            return False

        # For USDA, we can check their data release schedule
        # For now, assume updates available if interval passed
        return True

    async def _check_off_updates(self) -> bool:
        """Check if Open Food Facts database has updates."""
        current_version = self.versions.get("openfoodfacts")

        # If no current version, updates are available
        if not current_version:
            return True

        # Check if enough time has passed for an update
        last_update = datetime.fromisoformat(current_version.last_updated)
        if datetime.now() - last_update < self.update_interval:
            return False

        # For Open Food Facts, check for updates based on their update frequency
        # For now, assume updates available if interval passed
        return True

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
        start_time = datetime.now()

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
        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        # Notify callbacks
        for callback in self.update_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in update callback: {e}")

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
            new_version = datetime.now().strftime("%Y%m%d_%H%M%S")
            checksum = self._calculate_checksum(
                {name: asdict(food) for name, food in updated_foods.items()}
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
                    logger.warning(f"Could not load old data for comparison: {e}")

            records_added = len(updated_foods) - len(old_foods)
            records_updated = len(set(updated_foods.keys()) & set(old_foods.keys()))
            records_removed = len(old_foods) - len(updated_foods)

            # Update version tracking
            new_db_version = DatabaseVersion(
                source=source,
                version=new_version,
                last_updated=datetime.now().isoformat(),
                record_count=len(updated_foods),
                checksum=checksum,
                metadata={
                    "update_type": "scheduled" if not force else "forced",
                    "api_source": "USDA FoodData Central",
                },
            )

            self.versions[source] = new_db_version
            self._save_versions()

            # Clean up old backups
            await self._cleanup_old_backups(source)

            logger.info(f"Successfully updated {source} database: {len(updated_foods)} foods")

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
            logger.error(f"Error updating {source} database: {e}")
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
                        logger.warning(f"Error searching for {search_term}: {e}")

            # Convert to unified format
            unified_foods = {}
            for off_item in sample_products:
                try:
                    unified_item = UnifiedFoodItem.from_off_item(off_item)
                    # Use a standardized name for the key
                    key = self._generate_food_key(unified_item.name)
                    unified_foods[key] = unified_item
                except Exception as e:
                    logger.warning(f"Error converting OFF item to unified format: {e}")

            # Calculate new version info
            new_version = datetime.now().strftime("%Y%m%d_%H%M%S")
            checksum = self._calculate_checksum(
                {name: asdict(food) for name, food in unified_foods.items()}
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
                    logger.warning(f"Could not load old data for comparison: {e}")

            records_added = len(unified_foods) - len(old_foods)
            records_updated = len(set(unified_foods.keys()) & set(old_foods.keys()))
            records_removed = len(old_foods) - len(unified_foods)

            # Update version tracking
            new_db_version = DatabaseVersion(
                source=source,
                version=new_version,
                last_updated=datetime.now().isoformat(),
                record_count=len(unified_foods),
                checksum=checksum,
                metadata={
                    "update_type": "scheduled" if not force else "forced",
                    "api_source": "Open Food Facts",
                    "sample_size": len(sample_products),
                },
            )

            self.versions[source] = new_db_version
            self._save_versions()

            # Clean up old backups
            await self._cleanup_old_backups(source)

            logger.info(f"Successfully updated {source} database: {len(unified_foods)} foods")

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
            logger.error(f"Error updating {source} database: {e}")
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
        # Convert to lowercase and replace spaces with underscores
        key = name.lower().strip().replace(" ", "_")
        # Remove special characters
        key = "".join(c for c in key if c.isalnum() or c == "_")
        return key

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

            # Should have at least basic macronutrients
            required_nutrients = ["protein_g", "fat_g", "carbs_g"]
            missing_nutrients = [n for n in required_nutrients if n not in nutrients]
            if missing_nutrients:
                errors.append(f"Food {name} missing nutrients: {missing_nutrients}")

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

            with open(backup_file, "w") as f:
                json.dump(
                    {name: asdict(food) for name, food in current_data.items()},
                    f,
                    indent=2,
                )

            logger.info(f"Created backup for {source} version {version}")

        except Exception as e:
            logger.error(f"Error creating backup: {e}")

    async def _load_backup(self, source: str, version: str) -> Dict[str, UnifiedFoodItem]:
        """Load backup database version."""
        backup_file = self.cache_dir / f"{source}_backup_{version}.json"

        with open(backup_file, "r") as f:
            data = json.load(f)

        foods = {}
        for name, food_data in data.items():
            foods[name] = UnifiedFoodItem(**food_data)

        return foods

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
                logger.info(f"Removed old backup: {old_backup.name}")

        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")

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
                    version=f"{target_version}_rollback_{datetime.now().strftime('%H%M%S')}",
                    last_updated=datetime.now().isoformat(),
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

                logger.info(f"Successfully rolled back {source} to version {target_version}")
                return True

        except Exception as e:
            logger.error(f"Error rolling back {source} to {target_version}: {e}")

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
            last_update = datetime.fromisoformat(version.last_updated)
            time_since_update = datetime.now() - last_update

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
            logger.info(f"Running scheduled update for {source}")
            result = await update_manager.update_database(source)
            results[source] = result
        else:
            logger.info(f"No updates available for {source}")

    return results


if __name__ == "__main__":
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
