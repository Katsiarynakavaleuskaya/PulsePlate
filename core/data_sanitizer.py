"""Minimal data sanitizer for plate inputs used by premium endpoints.

Provides a stable API for tests expecting core.data_sanitizer.
"""

from typing import Any, Dict


def sanity_filter_plate_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return input data unchanged.

    This stub ensures imports succeed in tests. Expand with real
    sanitization rules as needed.
    """
    return data
