"""Narrow Alembic comparison helpers for PostgreSQL metadata drift.

The helpers in this module are pure: they inspect the values Alembic already
provides and never query a database, read environment state, or suppress an
unrecognized comparison.  JSON defaults are compared structurally because
PostgreSQL does not define an equality operator for ``json`` values.
"""

from __future__ import annotations

import json
import re

from sqlalchemy import Column
from sqlalchemy.dialects import postgresql

_JSON_SQL_LITERAL = re.compile(
    r"^'(?P<payload>(?:[^']|'')*)'(?:\s*::\s*(?P<cast>json|jsonb))?$",
    re.IGNORECASE,
)


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
    """Parse one exact SQL string literal with an optional JSON/JSONB cast."""

    match = _JSON_SQL_LITERAL.fullmatch(value.strip())
    if match is None:
        raise ValueError("postgresql_json_default_unparseable")
    payload = match.group("payload").replace("''", "'")
    try:
        return json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_object_keys,
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


__all__ = ["compare_postgresql_server_default"]
