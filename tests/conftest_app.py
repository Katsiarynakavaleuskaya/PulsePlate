"""Reusable response assertions for app-group compatibility tests."""

from collections.abc import Collection, Mapping
from typing import Any, Protocol

import pytest


class _ResponseLike(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


def assert_vip_response(
    response: _ResponseLike,
    expected_status_codes: Collection[int] | None = None,
    expected_data_fields: Mapping[str, Any] | None = None,
) -> None:
    """
    Helper function to assert VIP API responses without conditionals in tests.

    Args:
        response: The HTTP response object
        expected_status_codes: List of acceptable status codes (default: [200, 403])
        expected_data_fields: Dict of expected fields in response data (only checked for 200 status)
    """
    if expected_status_codes is None:
        expected_status_codes = [200, 403]

    assert (
        response.status_code in expected_status_codes
    ), f"Expected status code in {expected_status_codes}, got {response.status_code}"

    if response.status_code == 200 and expected_data_fields:
        # Safely parse JSON response
        try:
            data = response.json()
        except Exception as error:
            pytest.fail(
                f"Failed to parse JSON response: {error}. " f"Response text: {response.text[:200]}"
            )

        for field, expected_value in expected_data_fields.items():
            # Check that the field exists in the response data
            assert (
                field in data
            ), f"Expected field '{field}' not found in response data. Available fields: {list(data.keys())}"

            if expected_value == "exists":
                # Just check that the field exists (already verified above)
                continue
            elif isinstance(expected_value, str) and expected_value.startswith("contains:"):
                # Handle "contains:" prefix for partial string matching
                search_text = expected_value[9:]  # Remove "contains:" prefix
                field_value = data[field]

                # Ensure the field value is a string for contains check
                if not isinstance(field_value, str):
                    field_value = str(field_value)

                assert (
                    search_text in field_value
                ), f"Expected '{search_text}' to be contained in field '{field}' (value: '{field_value}')"
            else:
                assert (
                    data[field] == expected_value
                ), f"Expected field '{field}' to equal {expected_value}, got {data[field]}"
