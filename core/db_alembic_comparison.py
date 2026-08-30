"""Narrow Alembic comparison helpers for PostgreSQL metadata drift.

The helpers in this module are pure: they inspect the values Alembic already
provides and never query a database, read environment state, or suppress an
unrecognized comparison.  JSON defaults are compared structurally because
PostgreSQL does not define an equality operator for ``json`` values.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import re

from sqlalchemy import Column
from sqlalchemy.dialects import postgresql

_JSON_SQL_LITERAL = re.compile(
    r"^'(?P<payload>(?:[^']|'')*)'(?:\s*::\s*(?P<cast>json|jsonb))?$",
    re.IGNORECASE,
)

AUTOGENERATE_EXEMPT_TABLE_ROOTS = frozenset(
    {
        ("public", "foods"),
        ("public", "pulseplate_migration_ownership"),
        ("public", "restaurant_chains"),
        ("public", "restaurant_menu_items"),
    }
)

_PROVEN_DEFAULT_SCHEMA: ContextVar[str | None] = ContextVar(
    "pulseplate_alembic_proven_default_schema",
    default=None,
)


@contextmanager
def proven_autogenerate_default_schema(default_schema_name: str) -> Iterator[None]:
    """Admit implicit-schema reflection only after an exact public-schema proof."""

    if default_schema_name != "public":
        raise ValueError("autogenerate_default_schema_not_public")
    token = _PROVEN_DEFAULT_SCHEMA.set(default_schema_name)
    try:
        yield
    finally:
        _PROVEN_DEFAULT_SCHEMA.reset(token)


def include_autogenerate_object(
    obj: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Exclude only four exact reflected migration-only table roots.

    PostgreSQL reports default-schema tables with ``schema=None``.  That value
    is interpreted as ``public`` only inside a same-execution proof scope
    established by :func:`proven_autogenerate_default_schema`.
    """

    schema = getattr(obj, "schema", None)
    if schema is None:
        schema = _PROVEN_DEFAULT_SCHEMA.get()
    return not (
        type_ == "table"
        and reflected is True
        and compare_to is None
        and isinstance(name, str)
        and (schema, name) in AUTOGENERATE_EXEMPT_TABLE_ROOTS
    )


@dataclass(frozen=True, slots=True)
class _JsonNumber:
    """One type-tagged exact JSON numeric value."""

    value: Decimal


def _parse_json_number(lexeme: str) -> _JsonNumber:
    """Parse a JSON number exactly without using binary floating point."""

    try:
        value = Decimal(lexeme)
    except InvalidOperation as exc:
        raise ValueError("json_number_unparseable") from exc
    if not value.is_finite():
        raise ValueError("json_number_non_finite")
    return _JsonNumber(value)


def _reject_json_constant(value: str) -> object:
    """Reject non-standard JSON constants such as NaN and Infinity."""

    raise ValueError(f"non_standard_json_constant:{value}")


def _reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build a JSON object while rejecting ambiguous duplicate keys."""

    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_json_object_key:{key}")
        result[key] = value
    return result


def _parse_postgresql_json_default(value: str) -> object:
    """Parse an exact SQL JSON literal or exact raw JSON text."""

    stripped = value.strip()
    match = _JSON_SQL_LITERAL.fullmatch(stripped)
    payload = stripped if match is None else match.group("payload").replace("''", "'")
    try:
        return json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_object_keys,
            parse_float=_parse_json_number,
            parse_int=_parse_json_number,
            parse_constant=_reject_json_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("postgresql_json_default_unparseable") from exc


def _is_postgresql_json_column(column: Column[object]) -> bool:
    """Return whether a column resolves to JSON or JSONB on PostgreSQL."""

    resolved_type = column.type.dialect_impl(postgresql.dialect())
    return isinstance(resolved_type, (postgresql.JSON, postgresql.JSONB))


def compare_postgresql_server_default(
    context: object,
    inspected_column: Column[object],
    metadata_column: Column[object],
    inspected_default: str | None,
    metadata_default: object | None,
    rendered_metadata_default: str | None,
) -> bool | None:
    """Compare JSON defaults without invoking PostgreSQL's missing JSON equality.

    ``False`` means the two recognized JSON defaults are structurally equal,
    ``True`` means they are structurally different, and ``None`` delegates every
    non-JSON comparison back to Alembic.  An unrecognized JSON default fails
    closed instead of being treated as equal or ignored.
    """

    dialect = getattr(context, "dialect", None)
    dialect_name = getattr(dialect, "name", None)
    if dialect_name not in {None, "postgresql"}:
        return None
    if not (
        _is_postgresql_json_column(inspected_column) and _is_postgresql_json_column(metadata_column)
    ):
        return None

    del metadata_default
    if inspected_default is None or rendered_metadata_default is None:
        return inspected_default is not rendered_metadata_default

    inspected_value = _parse_postgresql_json_default(inspected_default)
    metadata_value = _parse_postgresql_json_default(rendered_metadata_default)
    return inspected_value != metadata_value


__all__ = [
    "AUTOGENERATE_EXEMPT_TABLE_ROOTS",
    "compare_postgresql_server_default",
    "include_autogenerate_object",
    "proven_autogenerate_default_schema",
]
