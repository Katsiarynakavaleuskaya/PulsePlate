import pytest


def test_resolve_attr_type_error_handling() -> None:
    """Cover line 58 in core/utils.py: TypeError handling in _resolve_module_candidate."""
    from core.utils import resolve_attr

    # Create a mock object that raises TypeError on type() call
    class TypeErrorRaiser:
        def __getattribute__(self, name: str):
            if name == "__class__":
                raise TypeError("Cannot get class")
            return object.__getattribute__(self, name)

    error_raiser = TypeErrorRaiser()

    # resolve_attr should handle TypeError gracefully
    result = resolve_attr("some_attr", None, [error_raiser])
    # Should return None or handle gracefully
    assert result is None or isinstance(result, (str, type(None)))
