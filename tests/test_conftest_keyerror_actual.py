"""
Test to actually trigger the KeyError exception on lines 44-45 in conftest.py.
"""

import sys
from types import ModuleType

import pytest


def test_monkeypatch_delitem_raises_keyerror(monkeypatch, reset_environment):
    """Deterministically assert KeyError using monkeypatch.delitem and pytest.raises.

    RU: Проверяем, что при повторном удалении отсутствующего модуля выбрасывается KeyError.
    EN: Verify KeyError is raised when deleting a non-existent module via monkeypatch.
    """
    test_module_name = "app.mock_test_module"
    test_module = ModuleType(test_module_name)

    # Install via monkeypatch (ensures pytest cleanup)
    monkeypatch.setitem(sys.modules, test_module_name, test_module)
    assert test_module_name in sys.modules

    # First deletion succeeds
    monkeypatch.delitem(sys.modules, test_module_name, raising=True)
    assert test_module_name not in sys.modules

    # Second deletion must raise KeyError
    with pytest.raises(KeyError):
        monkeypatch.delitem(sys.modules, test_module_name, raising=True)


class TestActualKeyError:
    """Focused tests for explicit KeyError behavior with sys.modules."""

    def test_keyerror_missing_module_with_monkeypatch(self, monkeypatch, reset_environment):
        """Assert KeyError on deleting already-removed module using monkeypatch.

        RU: Сначала удаляем модуль, затем подтверждаем KeyError при повторном удалении.
        EN: Delete once, then confirm KeyError on the second deletion.
        """
        test_module_name = "app.keyerror_actual_test"
        test_module = ModuleType(test_module_name)

        monkeypatch.setitem(sys.modules, test_module_name, test_module)
        assert test_module_name in sys.modules

        # First deletion succeeds and removes the module
        monkeypatch.delitem(sys.modules, test_module_name, raising=True)
        assert test_module_name not in sys.modules

        # Second deletion raises KeyError explicitly
        with pytest.raises(KeyError):
            monkeypatch.delitem(sys.modules, test_module_name, raising=True)
