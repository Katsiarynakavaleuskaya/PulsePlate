"""
Tests to boost coverage for core/utils.py module.
Focus on covering defensive branches and edge cases.
"""

import types
from unittest.mock import AsyncMock, MagicMock, Mock

from core.utils import _is_mock_like, resolve_attr


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

    def test_resolve_attr_custom_getattribute_raises_on_isinstance(self):
        """Test resolve_attr when custom __getattribute__ raises during isinstance check."""

        # Create object that raises Exception when isinstance is called
        class CustomGetAttribute:
            def __getattribute__(self, name: str):
                # Raise when Python tries to check isinstance by accessing __class__
                if name == "__class__":
                    raise Exception("Custom __getattribute__ raises")
                return super().__getattribute__(name)

        bad_candidate = CustomGetAttribute()
        good_module = types.ModuleType("good_module")
        good_module.test_attr = "found_value"

        candidates = [bad_candidate, good_module]
        # Should skip bad candidate due to exception during isinstance check
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "found_value"

    def test_is_mock_like_with_mock_children(self):
        """Test _is_mock_like detects objects with _mock_children attribute."""
        mock_obj = Mock()
        mock_obj._mock_children = {}
        assert _is_mock_like(mock_obj) is True

    def test_is_mock_like_with_mock_class_name(self):
        """Test _is_mock_like detects Mock, MagicMock, AsyncMock by class name."""
        assert _is_mock_like(Mock()) is True
        assert _is_mock_like(MagicMock()) is True
        assert _is_mock_like(AsyncMock()) is True

    def test_is_mock_like_with_unittest_mock_module(self):
        """Test _is_mock_like detects objects with __module__ starting with unittest.mock."""
        mock_obj = Mock()
        # Set __module__ to unittest.mock variant
        mock_obj.__module__ = "unittest.mock"
        assert _is_mock_like(mock_obj) is True

    def test_is_mock_like_with_custom_getattr_raises(self):
        """Test _is_mock_like handles AttributeError/TypeError from attribute access."""

        class CustomGetAttr:
            def __getattr__(self, name: str):
                raise AttributeError("Custom __getattr__ raises")

        obj = CustomGetAttr()
        # Should return False when AttributeError is raised
        assert _is_mock_like(obj) is False

    def test_is_mock_like_with_type_error(self):
        """Test _is_mock_like handles TypeError from accessing __class__.__name__."""

        class TypeErrorOnClass:
            def __getattribute__(self, name: str):
                if name == "__class__":
                    raise TypeError("Cannot access __class__")
                return super().__getattribute__(name)

        obj = TypeErrorOnClass()
        # Should return False when TypeError is raised
        assert _is_mock_like(obj) is False

    def test_resolve_attr_raises_attribute_error(self):
        """Test resolve_attr handles AttributeError and logs debug message."""

        class AttributeErrorCandidate:
            def __getattr__(self, name: str):
                raise AttributeError("Attribute not found")

            def __dict__(self):
                raise AttributeError("No __dict__")

        bad_candidate = AttributeErrorCandidate()
        good_module = types.ModuleType("good_module")
        good_module.test_attr = "found_value"

        candidates = [bad_candidate, good_module]
        # Should skip bad candidate due to AttributeError and find value in good module
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "found_value"

    def test_resolve_attr_raises_type_error(self):
        """Test resolve_attr handles TypeError and logs debug message."""

        class TypeErrorCandidate:
            @property
            def __dict__(self):
                raise TypeError("Type error accessing __dict__")

        bad_candidate = TypeErrorCandidate()
        good_module = types.ModuleType("good_module")
        good_module.test_attr = "found_value"

        candidates = [bad_candidate, good_module]
        # Should skip bad candidate due to TypeError and find value in good module
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "found_value"

    def test_resolve_attr_raises_import_error(self):
        """Test resolve_attr handles ImportError and logs debug message."""

        class ImportErrorCandidate:
            def __getattr__(self, name: str):
                raise ImportError("Import error")

        bad_candidate = ImportErrorCandidate()
        good_module = types.ModuleType("good_module")
        good_module.test_attr = "found_value"

        candidates = [bad_candidate, good_module]
        # Should skip bad candidate due to ImportError and find value in good module
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "found_value"

    def test_resolve_attr_mock_like_object_skipped(self):
        """Test resolve_attr skips mock-like objects."""
        # Create a mock-like object that will be detected by _is_mock_like
        mock_candidate = Mock()
        # Don't set test_attr in __dict__ so it's not found via __dict__ check
        # and will be detected as mock-like and skipped

        real_module = types.ModuleType("real_module")
        real_module.test_attr = "real_value"

        candidates = [mock_candidate, real_module]
        # Should skip mock and find value in real module
        result = resolve_attr("test_attr", "default_value", candidates)
        assert result == "real_value"
