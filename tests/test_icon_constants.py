"""Tests for iOS icon constants validation."""

import re
from typing import Set

import pytest

from ios.Scripts.icon_constants import IOS_ICON_DUPLICATE_ALLOWLIST, IOS_ICON_SIZES


# Required canonical iOS icon filenames
REQUIRED_ICON_FILENAMES: Set[str] = {
    # iPhone
    "icon_iphone_20pt@2x.png",
    "icon_iphone_20pt@3x.png",
    "icon_iphone_29pt@2x.png",
    "icon_iphone_29pt@3x.png",
    "icon_iphone_40pt@2x.png",
    "icon_iphone_40pt@3x.png",
    "icon_iphone_60pt@2x.png",
    "icon_iphone_60pt@3x.png",
    # iPad
    "icon_ipad_20pt.png",
    "icon_ipad_20pt@2x.png",
    "icon_ipad_29pt.png",
    "icon_ipad_29pt@2x.png",
    "icon_ipad_40pt.png",
    "icon_ipad_40pt@2x.png",
    "icon_ipad_76pt.png",
    "icon_ipad_76pt@2x.png",
    "icon_ipad_83_5pt@2x.png",
    # App Store
    "icon_marketing_1024.png",
}


# iOS icon filename regex pattern
IOS_ICON_FILENAME_PATTERN = re.compile(
    r"^icon_(?:marketing_\d+|(?:iphone|ipad)_\d+(?:[._]\d+)?pt(?:@[23]x)?)\.png$"
)


class TestIconConstants:
    """Test iOS icon constants validation."""

    def test_all_filenames_match_pattern(self) -> None:
        """Assert every filename matches the expected iOS icon filename regex pattern."""
        for filename in IOS_ICON_SIZES.keys():
            assert IOS_ICON_FILENAME_PATTERN.match(
                filename
            ), f"Filename {filename!r} does not match iOS icon naming pattern"

    def test_all_sizes_are_positive_integers(self) -> None:
        """Assert every mapped size is an int > 0."""
        for filename, size in IOS_ICON_SIZES.items():
            assert isinstance(size, int), f"Size for {filename} must be int, got {type(size)}"
            assert size > 0, f"Size for {filename} must be > 0, got {size}"

    def test_required_filenames_exist(self) -> None:
        """Assert the set of keys includes the required canonical iOS icon filenames."""
        keys_set = set(IOS_ICON_SIZES.keys())
        assert (
            REQUIRED_ICON_FILENAMES <= keys_set
        ), f"Missing required filenames: {REQUIRED_ICON_FILENAMES - keys_set}"

    def test_no_duplicate_sizes(self) -> None:
        """Assert there are no duplicate sizes for different filenames."""
        size_to_filenames: dict[int, list[str]] = {}
        for filename, size in IOS_ICON_SIZES.items():
            if size not in size_to_filenames:
                size_to_filenames[size] = []
            size_to_filenames[size].append(filename)

        duplicates = {
            size: tuple(sorted(filenames))
            for size, filenames in size_to_filenames.items()
            if len(filenames) > 1
        }
        expected_duplicates = {
            size: tuple(sorted(filenames))
            for size, filenames in IOS_ICON_DUPLICATE_ALLOWLIST.items()
        }
        assert (
            duplicates == expected_duplicates
        ), f"Duplicate sizes mismatch.\nExpected: {expected_duplicates}\nFound: {duplicates}"
