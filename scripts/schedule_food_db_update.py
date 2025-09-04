#!/usr/bin/env python3
"""
Food Database Update Scheduler

RU: Планировщик обновления базы данных продуктов.
EN: Food database update scheduler.
"""

import logging
import os
import subprocess
import sys

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, "logs", "food_db_update.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def update_food_database():
    """
    RU: Обновить базу данных продуктов.
    EN: Update food database.
    """
    logger.info("Starting food database update...")

    try:
        # Run the build script
        build_script = os.path.join(project_root, "scripts", "build_food_db.py")
        result = subprocess.run(
            [sys.executable, build_script],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            logger.info("Food database update completed successfully")
            logger.debug(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"Food database update failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Food database update timed out")
        return False
    except Exception as e:
        logger.error(f"Food database update failed with exception: {e}")
        return False


def main():
    """
    RU: Основная функция планировщика.
    EN: Main scheduler function.
    """
    logger.info("Food database update scheduler started")

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(project_root, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Update the food database
    success = update_food_database()

    if success:
        logger.info("Food database update scheduler completed successfully")
        sys.exit(0)
    else:
        logger.error("Food database update scheduler failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
