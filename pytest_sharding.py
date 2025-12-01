#!/usr/bin/env python3
"""
Tenant-based test sharding for PulsePlate.

Organizes tests into functional domains (tenants) to optimize memory usage
and maintain logical test grouping. Prevents memory errors from parallel execution.

Usage:
    # Run specific shard (1-6)
    pytest --shard-id=1 tests/

    # Run all shards sequentially (for CI)
    for i in {1..6}; do pytest --shard-id=$i tests/ --cov --cov-append; done

    # Run shards in parallel with limited workers (2-3 max to avoid memory errors)
    pytest --shard-id=1 tests/ & pytest --shard-id=2 tests/ & wait
"""

import pytest
from _pytest.nodes import Item
from typing import List, Dict, TypedDict


class ShardConfig(TypedDict):
    """Type definition for shard configuration entries."""

    name: str
    patterns: List[str]
    description: str


# Tenant-based shard mapping: organized by functional domain
SHARD_MAP: Dict[int, ShardConfig] = {
    1: {
        "name": "app_api",
        "patterns": ["test_app_", "test_api_"],
        "description": "Application and API layer tests",
    },
    2: {
        "name": "database",
        "patterns": ["test_food_", "test_recipe_", "test_unified_db_", "test_db_"],
        "description": "Database and data management tests",
    },
    3: {
        "name": "vip_premium",
        "patterns": ["test_vip_", "test_premium_"],
        "description": "VIP and premium feature tests",
    },
    4: {
        "name": "analytics",
        "patterns": [
            "test_bayesian_",
            "test_comprehensive_",
            "test_integrated_",
            "test_nutrition_bayesian_",
        ],
        "description": "Bayesian analytics and recommendations",
    },
    5: {
        "name": "core",
        "patterns": ["test_core_", "test_bmi_", "test_bodyfat_", "test_nutrition_", "test_schemas"],
        "description": "Core business logic and utilities",
    },
    6: {
        "name": "planning_export",
        "patterns": [
            "test_export_",
            "test_week_",
            "test_shoplist_",
            "test_daily_",
            "test_menu_",
            "test_plate_",
        ],
        "description": "Meal planning and export functionality",
    },
}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add shard selection option to pytest.

    Args:
        parser: Pytest command-line parser for registering custom options
    """
    parser.addoption(
        "--shard-id",
        action="store",
        type=int,
        default=None,
        help=f"Run tests for specific shard (1-{len(SHARD_MAP)}). "
        "Tenant-based sharding by functional domain.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: List[Item]) -> None:
    """Filter tests based on shard selection.

    Args:
        config: Pytest configuration object
        items: List of collected test items to filter
    """
    shard_id = config.getoption("--shard-id")

    if shard_id is None:
        # No sharding - run all tests
        return

    if shard_id not in SHARD_MAP:
        raise pytest.UsageError(
            f"Invalid shard ID: {shard_id}. "
            f"Must be between 1 and {len(SHARD_MAP)}. "
            f"Available shards: {list(SHARD_MAP.keys())}"
        )

    shard_config = SHARD_MAP[shard_id]
    patterns = shard_config["patterns"]

    # Filter items: keep only tests matching shard patterns
    selected_items: List[Item] = []
    deselected_items: List[Item] = []

    for item in items:
        # Get test file name from item's path (pytest 7+ compatible)
        test_file = item.path.name

        # Check if test file matches any pattern in this shard
        if any(test_file.startswith(pattern) for pattern in patterns):
            selected_items.append(item)
        else:
            deselected_items.append(item)

    # Update collection
    config.hook.pytest_deselected(items=deselected_items)
    items[:] = selected_items

    # Log shard info
    if selected_items:
        tw = config.get_terminal_writer()
        tw.line(
            f"\n📦 Shard {shard_id} ({shard_config['name']}): "
            f"{len(selected_items)} tests selected"
        )
        tw.line(f"   Description: {shard_config['description']}")
        tw.line(f"   Patterns: {', '.join(patterns)}\n")
