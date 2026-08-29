"""Finite Alembic ownership policy shared by env and validation tooling.

The module is intentionally dependency-free and import-side-effect free.  It
does not load ORM metadata or own any database lifecycle; it only recognizes
the exact migration-owned public/default tables for the current schema epoch.
"""

from __future__ import annotations

DEFAULT_SCHEMA_NAMES = frozenset({None, "public"})

MIGRATION_OWNED_TABLE_KEYS = frozenset(
    {
        "pulseplate_migration_ownership",
        "foods",
        "restaurant_chains",
        "restaurant_menu_items",
    }
)


def include_autogenerate_object(
    obj: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Exclude only exact reflected DB-only migration-owned public tables."""

    schema = getattr(obj, "schema", None)
    return not (
        type_ == "table"
        and reflected is True
        and compare_to is None
        and schema in DEFAULT_SCHEMA_NAMES
        and name in MIGRATION_OWNED_TABLE_KEYS
    )


__all__ = [
    "DEFAULT_SCHEMA_NAMES",
    "MIGRATION_OWNED_TABLE_KEYS",
    "include_autogenerate_object",
]
