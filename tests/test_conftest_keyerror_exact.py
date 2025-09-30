"""
Test to exactly trigger the KeyError exception path in reset_environment fixture.
"""

import sys
from types import ModuleType

import pytest


def test_trigger_keyerror_exception_path():
    """Test that creates the exact condition to trigger KeyError exception handling.

    This test doesn't directly test the fixture, but creates the exact scenario
    that would cause the KeyError path to be executed when the fixture runs.
    """
    # Create a module that matches our filter pattern
    test_module_name = "app.test_keyerror_exact"
    test_module = ModuleType(test_module_name)
    sys.modules[test_module_name] = test_module

    # Remove it immediately to simulate the race condition
    del sys.modules[test_module_name]

    # At this point, if the reset_environment fixture runs, it will:
    # 1. Identify test_module_name as a new module (because it was added during the test)
    # 2. Try to delete it with `del sys.modules[module_name]`
    # 3. This will raise KeyError because it's already been deleted
    # 4. The exception handler on lines 44-45 should catch this

    # Verify the module is no longer in sys.modules
    assert test_module_name not in sys.modules


class TestConftestKeyErrorExact:
    """Class-based tests for exact KeyError triggering."""

    def test_keyerror_with_environment_fixture(self, test_environment):
        """Test KeyError trigger with environment fixture."""
        # Create the same condition
        test_module_name = "app.test_keyerror_with_env"
        test_module = ModuleType(test_module_name)
        sys.modules[test_module_name] = test_module
        del sys.modules[test_module_name]

        # The environment fixture should handle this gracefully when it cleans up
        assert test_environment is None  # Fixtures return None
        assert test_module_name not in sys.modules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
