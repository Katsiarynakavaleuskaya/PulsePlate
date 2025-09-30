"""
Tests to boost coverage for core/utils.py module.
Focus on covering the missing lines 68-69, 78-80.
"""

import types
from unittest.mock import Mock

from core.utils import resolve_attr


class TestUtilsCoverage:
    """Test class to boost coverage of core/utils.py."""

    def test_resolve_attr_exception_during_mock_detection(self):
        """Test resolve_attr when exception occurs during mock detection (lines 68-69)."""

        # Create a candidate that will raise an exception during mock detection
        class BadCandidate:
            def __getattribute__(self, name):
                if name == "__class__":
                    raise Exception("Simulated exception during mock detection")
                return super().__getattribute__(name)

        bad_candidate = BadCandidate()

        # Create a good candidate with the attribute we want
        good_module = types.ModuleType("good_module")
        good_module.test_attr = "found_value"

        candidates = [bad_candidate, good_module]

        # Should skip bad candidate due to exception and find value in good module
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "found_value"

    def test_resolve_attr_exception_during_getattr(self):
        """Test resolve_attr when exception occurs during getattr (lines 78-80)."""

        # Create a module-like object that raises exception on getattr
        class BadModule:
            def __class__(self):
                return types.ModuleType

            def __getattr__(self, name):
                raise Exception("Simulated exception during getattr")

        bad_module = BadModule()

        # Create a good candidate
        good_module = types.ModuleType("good_module")
        good_module.test_attr = "found_value"

        candidates = [bad_module, good_module]

        # Should skip bad module due to exception and find value in good module
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "found_value"

    def test_resolve_attr_no_matching_candidates(self):
        """Test resolve_attr when no candidates have the attribute."""

        # Create candidates without the requested attribute
        module1 = types.ModuleType("module1")
        module1.other_attr = "other_value"

        module2 = types.ModuleType("module2")
        module2.different_attr = "different_value"

        candidates = [module1, module2]

        # Should return default when no candidates have the attribute
        result = resolve_attr("nonexistent_attr", "default_value", candidates)
        assert result == "default_value"

    def test_resolve_attr_mock_detection_with_real_module(self):
        """Test resolve_attr properly detects real modules vs mocks."""

        # Create a real module with an attribute
        real_module = types.ModuleType("real_module")
        real_module.test_attr = "real_value"

        # Create a mock without the attribute in __dict__ initially
        mock_candidate = Mock()
        # Don't set the attribute explicitly so it's not in __dict__

        candidates = [mock_candidate, real_module]

        # Should skip mock (no attr in __dict__) and use real module
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "real_value"

    def test_resolve_attr_with_empty_candidates(self):
        """Test resolve_attr with empty candidates list."""

        candidates = []

        # Should return default when no candidates provided
        result = resolve_attr("any_attr", "default_value", candidates)
        assert result == "default_value"

    def test_resolve_attr_with_none_candidates(self):
        """Test resolve_attr with None in candidates list."""

        # Include None in candidates
        real_module = types.ModuleType("real_module")
        real_module.test_attr = "real_value"

        candidates = [None, real_module]

        # Should skip None and find value in real module
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "real_value"
