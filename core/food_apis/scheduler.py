"""
Database Update Scheduler

RU: Планировщик автообновлений баз данных.
EN: Scheduler for automatic database updates.

This module provides scheduled background tasks for keeping nutrition
databases up to date with minimal impact on application performance.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import threading
from collections.abc import Sequence
from datetime import datetime, timedelta
from types import FrameType
from typing import Any

from ..time_utils import now_utc
from ._testing import is_test_runtime
from .scheduler_runtime import (
    SchedulerConfigurationError,
    SchedulerMode,
    UpdateLeaseContended,
    UpdateLeaseError,
    configured_periodic_owner,
    resolve_scheduler_mode,
    run_with_update_lease,
)
from .update_manager import DatabaseUpdateManager, UpdateResult

logger = logging.getLogger(__name__)


class DatabaseUpdateScheduler:
    """
    RU: Планировщик фоновых обновлений баз данных.
    EN: Background database update scheduler.

    Features:
    - Non-blocking background updates
    - Configurable update intervals
    - Error handling and retry logic
    - Graceful shutdown handling
    - Update notifications and logging
    """

    def __init__(
        self,
        update_interval_hours: int = 24,
        retry_interval_minutes: int = 30,
        max_retries: int = 3,
        *,
        install_signal_handlers: bool = True,
    ) -> None:
        self.update_interval = timedelta(hours=update_interval_hours)
        self.retry_interval = timedelta(minutes=retry_interval_minutes)
        self.max_retries = max_retries

        self.update_manager = DatabaseUpdateManager(update_interval_hours=update_interval_hours)

        # State tracking
        self.is_running = False
        self.last_update_check: datetime | None = None
        self.retry_counts: dict[str, int] = {}

        # Background task
        self._update_task: asyncio.Task[None] | None = None
        self._shutdown_task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        # Setup update callbacks
        self.update_manager.add_update_callback(self._on_update_complete)

        # Preserve direct-constructor compatibility while allowing the API
        # singleton to leave process signal ownership to FastAPI lifespan.
        if install_signal_handlers:
            self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        # RU: В xdist/параллельных воркерах signal.signal() запрещён (не main thread).
        # EN: Under pytest-xdist signal handlers cannot be set in worker threads.
        if threading.current_thread() is not threading.main_thread() or is_test_runtime():
            return

        def signal_handler(signum: int, frame: FrameType | None) -> None:
            logger.info("Received signal %s, initiating graceful shutdown...", signum)

            loop = self._loop
            if loop is None or loop.is_closed() or not loop.is_running():
                logger.warning(
                    "Scheduler shutdown requested but no running event loop is available (loop=%r)",
                    loop,
                )
                return

            def schedule_stop() -> None:
                if self._shutdown_task is None or self._shutdown_task.done():
                    self._shutdown_task = asyncio.create_task(self.stop())

            try:
                loop.call_soon_threadsafe(schedule_stop)
            except Exception as e:
                logger.warning("Could not schedule scheduler shutdown task: %s", e)

        # Handle common shutdown signals
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except Exception as e:
            logger.warning("Could not setup signal handlers: %s", e)

    async def start(self) -> None:
        """
        RU: Запускает планировщик обновлений.
        EN: Start the update scheduler.
        """
        if self.is_running:
            logger.warning("Update scheduler is already running")
            return

        self._loop = asyncio.get_running_loop()
        self.is_running = True
        logger.info("Starting database update scheduler...")

        # Start background update task
        self._update_task = asyncio.create_task(self._update_loop())

        logger.info(f"Update scheduler started (interval: {self.update_interval})")

    async def stop(self) -> None:
        """
        RU: Останавливает планировщик обновлений.
        EN: Stop the update scheduler.
        """
        if not self.is_running:
            return

        logger.info("Stopping database update scheduler...")
        self.is_running = False

        # Cancel background task
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        # Close update manager
        await self.update_manager.close()

        logger.info("Database update scheduler stopped")

    async def _update_loop(self) -> None:
        """Main update loop running in background."""
        while self.is_running:
            try:
                # Check if it's time for updates
                current_time = now_utc()

                if self._should_check_for_updates(current_time):
                    await self._run_update_check()

                # Sleep for a short interval before next check
                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                logger.info("Update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    def _should_check_for_updates(self, current_time: datetime) -> bool:
        """Determine if it's time to check for updates."""
        if self.last_update_check is None:
            return True

        time_since_last_check = current_time - self.last_update_check
        return time_since_last_check >= self.update_interval

    async def _run_update_check(
        self,
        *,
        propagate_lease_errors: bool = False,
    ) -> bool:
        """Check for updates through the canonical attempt-scoped lease."""

        async def _run_due_check() -> bool:
            # The authoritative due check must happen after lease acquisition.
            current_time = now_utc()
            if not self._should_check_for_updates(current_time):
                return True

            logger.info("Checking for database updates...")

            available_updates = await self.update_manager.check_for_updates()
            if not any(available_updates.values()):
                logger.info("No database updates available")
                self.last_update_check = current_time
                return True

            completed = True
            for source, has_updates in available_updates.items():
                if has_updates and not await self._run_source_update(source):
                    completed = False

            if completed:
                self.last_update_check = current_time
            return completed

        try:
            return await run_with_update_lease(_run_due_check)
        except UpdateLeaseContended:
            if propagate_lease_errors:
                raise
            logger.info("Database update attempt skipped because the shared lease is held")
            return False
        except UpdateLeaseError:
            if propagate_lease_errors:
                raise
            logger.error("Database update attempt failed at the shared lease boundary")
            return False
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("Error during update check", exc_info=True)
            return False

    async def _run_source_update(self, source: str) -> bool:
        """Run update for a specific source with retry logic."""
        retry_count = self.retry_counts.get(source, 0)

        try:
            logger.info(f"Running update for {source} (attempt {retry_count + 1})")

            result = await self.update_manager.update_database(source)

            if result.success:
                # Reset retry count on success
                self.retry_counts[source] = 0
                logger.info(
                    f"Successfully updated {source}: "
                    f"+{result.records_added} ~{result.records_updated} "
                    f"-{result.records_removed} records"
                )
                return True
            else:
                # Handle failure
                self._handle_update_failure(source, result.errors)
                return False

        except Exception as e:
            # Handle exception
            self._handle_update_failure(source, [str(e)])
            return False

    def _handle_update_failure(self, source: str, errors: list[str]) -> None:
        """Handle update failure with retry logic."""
        self.retry_counts[source] = self.retry_counts.get(source, 0) + 1

        if self.retry_counts[source] >= self.max_retries:
            logger.error(f"Max retries exceeded for {source} updates. Errors: {errors}")
            # Reset retry count to try again next cycle
            self.retry_counts[source] = 0
        else:
            logger.warning(
                f"Update failed for {source} (attempt {self.retry_counts[source]}). "
                f"Will retry. Errors: {errors}"
            )

    def _on_update_complete(self, result: UpdateResult) -> None:
        """Callback for when an update completes."""
        if result.success:
            logger.info(
                f"Update notification: {result.source} updated successfully "
                f"(v{result.old_version} → v{result.new_version})"
            )
        else:
            logger.warning(f"Update notification: {result.source} update failed - {result.errors}")

    async def force_update(self, source: str | None = None) -> dict[str, UpdateResult]:
        """
        RU: Принудительно запускает обновление.
        EN: Force an immediate update.

        Args:
            source: Specific source to update, or None for all sources

        Returns:
            dict of update results by source
        """

        async def _run_forced_update() -> dict[str, UpdateResult]:
            results: dict[str, UpdateResult] = {}

            if source:
                logger.info("Force updating %s...", source)
                result = await self.update_manager.update_database(source, force=True)
                results[source] = result
            else:
                logger.info("Force updating all sources...")
                available_updates = await self.update_manager.check_for_updates()

                for src in available_updates:
                    result = await self.update_manager.update_database(src, force=True)
                    results[src] = result

            return results

        return await run_with_update_lease(_run_forced_update)

    def get_status(self) -> dict[str, Any]:
        """
        RU: Получает статус планировщика и баз данных.
        EN: Get scheduler and database status.
        """
        try:
            configured_mode = resolve_scheduler_mode()
            configured_owner = configured_periodic_owner(configured_mode)
            configured_mode_value = configured_mode.value
        except SchedulerConfigurationError:
            configured_mode_value = "invalid"
            configured_owner = "none"

        status = {
            "scheduler": {
                "is_running": self.is_running,
                "configured_mode": configured_mode_value,
                "configured_periodic_owner": configured_owner,
                "last_update_check": (
                    self.last_update_check.isoformat() if self.last_update_check else None
                ),
                "update_interval_hours": self.update_interval.total_seconds() / 3600,
                "retry_counts": self.retry_counts.copy(),
            },
            "databases": self.update_manager.get_database_status(),
        }

        return status


# Global scheduler instance
_scheduler_instance: DatabaseUpdateScheduler | None = None


async def get_update_scheduler() -> DatabaseUpdateScheduler:
    """
    RU: Получить глобальный экземпляр планировщика обновлений.
    EN: Get global update scheduler instance.
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DatabaseUpdateScheduler(install_signal_handlers=False)
    return _scheduler_instance


async def start_background_updates(update_interval_hours: int = 24) -> None:
    """
    RU: Запускает фоновые обновления баз данных.
    EN: Start background database updates.
    """
    scheduler = await get_update_scheduler()
    if not scheduler.is_running:
        await scheduler.start()
        logger.info(f"Background database updates started (every {update_interval_hours}h)")


async def stop_background_updates() -> None:
    """
    RU: Останавливает фоновые обновления баз данных.
    EN: Stop background database updates.
    """
    if _scheduler_instance and _scheduler_instance.is_running:
        await _scheduler_instance.stop()
        logger.info("Background database updates stopped")


# ---------------------------------------------------------------------------
# Thin facades (satisfy test imports; see tests/feature_manifest.py food_apis)
# ---------------------------------------------------------------------------

FoodAPIScheduler = DatabaseUpdateScheduler
"""Alias expected by some test suites."""


def check_update_status(**kwargs: object) -> dict[str, object]:
    """Return current scheduler status dict (empty when scheduler is idle)."""
    if _scheduler_instance is not None:
        return _scheduler_instance.get_status()
    return {}


def schedule_update(**kwargs: object) -> None:
    """No-op synchronous scheduling facade."""


def _worker_argument_parser() -> argparse.ArgumentParser:
    """Build the dedicated no-ingress scheduler worker CLI."""

    parser = argparse.ArgumentParser(description="Run the food update scheduler worker")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--serve", action="store_true", help="serve periodic update attempts")
    action.add_argument("--once", action="store_true", help="run one leased due-check cycle")
    return parser


def _initialize_worker_database() -> None:
    """Initialize the existing public DB/session factory for lease ownership."""

    from core.db import init_db

    init_db()


async def _serve_worker() -> int:
    """Run the external periodic worker until a worker-owned signal stops it."""

    mode = resolve_scheduler_mode()
    if mode is not SchedulerMode.EXTERNAL:
        raise SchedulerConfigurationError("--serve requires external scheduler mode")

    _initialize_worker_database()
    scheduler = DatabaseUpdateScheduler(install_signal_handlers=True)
    update_task: asyncio.Task[None] | None = None
    try:
        await scheduler.start()
        update_task = scheduler._update_task
        if update_task is None:
            raise RuntimeError("scheduler worker task was not created")
        await update_task
        return 0
    finally:
        shutdown_task = scheduler._shutdown_task
        if shutdown_task is not None:
            await shutdown_task
        elif scheduler.is_running:
            await scheduler.stop()
        elif update_task is None:
            await scheduler.update_manager.close()


async def _run_worker_once() -> int:
    """Run one explicit leased due-check cycle and exit without ingress."""

    mode = resolve_scheduler_mode()
    if mode is SchedulerMode.IN_PROCESS_DEV:
        raise SchedulerConfigurationError("--once is unavailable in in_process_dev mode")

    _initialize_worker_database()
    scheduler = DatabaseUpdateScheduler(install_signal_handlers=False)
    try:
        try:
            completed = await scheduler._run_update_check(propagate_lease_errors=True)
        except UpdateLeaseContended:
            logger.info("One-shot update attempt observed shared lease contention")
            return 0
        return 0 if completed else 1
    finally:
        await scheduler.update_manager.close()


def worker_main(argv: Sequence[str] | None = None) -> int:
    """Synchronous CLI entrypoint for the dedicated scheduler process."""

    args = _worker_argument_parser().parse_args(argv)
    try:
        if args.serve:
            return asyncio.run(_serve_worker())
        return asyncio.run(_run_worker_once())
    except SchedulerConfigurationError:
        logger.error("Scheduler worker configuration is invalid")
        return 2
    except UpdateLeaseError:
        logger.error("Scheduler worker could not establish the update lease")
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception:
        logger.error("Scheduler worker failed", exc_info=True)
        return 1


if __name__ == "__main__":  # pragma: no cover - exercised through CLI subprocess checks
    raise SystemExit(worker_main())
