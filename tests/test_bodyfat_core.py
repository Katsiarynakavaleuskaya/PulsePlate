from __future__ import annotations

import pytest

from core import bodyfat as bf


def test_as_float_rejects_bool() -> None:
    with pytest.raises(TypeError, match="bool is not a valid float input"):
        bf._as_float(True)


def test_as_float_accepts_str() -> None:
    assert bf._as_float("1.5") == 1.5


def test_as_float_rejects_unsupported_type() -> None:
    with pytest.raises(TypeError, match=r"Unsupported float input type:"):
        bf._as_float(object())


def test_as_int_rejects_bool() -> None:
    with pytest.raises(TypeError, match="bool is not a valid int input"):
        bf._as_int(False)


def test_as_int_rejects_non_integer_float() -> None:
    with pytest.raises(ValueError, match="float value must be an integer"):
        bf._as_int(1.5)


def test_as_int_accepts_integer_float() -> None:
    assert bf._as_int(2.0) == 2


def test_as_int_accepts_str() -> None:
    assert bf._as_int("7") == 7


def test_as_int_rejects_unsupported_type() -> None:
    with pytest.raises(TypeError, match=r"Unsupported int input type:"):
        bf._as_int(object())
