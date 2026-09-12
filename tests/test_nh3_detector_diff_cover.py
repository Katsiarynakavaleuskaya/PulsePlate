import app.services.pro_nutrition_plate as plate_service
from core.data_sanitizer import MissingOptionalDependencyError


def test_is_missing_nh3_error_detects_module_not_found() -> None:
    """Recognize nh3 absence from the missing-module name attribute."""
    exc = ModuleNotFoundError("No module named 'nh3'")
    # Ensure the `name` attribute is set (covers the canonical getattr(exc, "name") path).
    exc.name = "nh3"
    assert plate_service._is_missing_nh3_error(exc) is True


def test_is_missing_nh3_error_detects_import_error_message() -> None:
    """Recognize nh3 absence from a plain ImportError message."""
    exc = ImportError("No module named 'nh3'")
    assert plate_service._is_missing_nh3_error(exc) is True


def test_is_missing_nh3_error_detects_missing_optional_dependency_error() -> None:
    """Recognize the canonical optional-dependency error for nh3."""
    exc = MissingOptionalDependencyError(
        "nh3",
        "Optional dependency 'nh3' is required for plate data sanitization.",
    )
    assert plate_service._is_missing_nh3_error(exc) is True


def test_is_missing_nh3_error_detects_same_named_error_class() -> None:
    """Recognize nh3 in a look-alike dependency error without relying on class identity."""

    # Simulate split-brain imports where the error class exists twice as different objects.
    class MissingOptionalDependencyError(RuntimeError):
        def __init__(self, message: str) -> None:
            """Carry only the message used to identify the missing dependency."""
            super().__init__(message)

    exc = MissingOptionalDependencyError("Optional dependency 'nh3' is required.")
    assert plate_service._is_missing_nh3_error(exc) is True


def test_is_missing_nh3_error_detects_same_named_error_class_by_dependency_attr() -> None:
    """Recognize a look-alike dependency error through its explicit dependency attribute."""

    # Simulate split-class scenario where the exception carries the dependency attribute.
    class MissingOptionalDependencyError(RuntimeError):
        def __init__(self, dependency: str) -> None:
            """Expose the dependency name on a distinct local exception class."""
            super().__init__(f"Optional dependency '{dependency}' is required")
            self.dependency = dependency

    exc = MissingOptionalDependencyError("nh3")
    assert plate_service._is_missing_nh3_error(exc) is True


def test_is_missing_nh3_error_returns_false_for_other_module() -> None:
    """Keep an unrelated missing module outside the nh3 error classification."""
    exc = ModuleNotFoundError("No module named 'requests'", name="requests")
    assert plate_service._is_missing_nh3_error(exc) is False


def test_is_missing_nh3_error_returns_false_for_other_import_error() -> None:
    """Keep unrelated symbol-import failures outside the nh3 error classification."""
    exc = ImportError("Cannot import name 'foo'")
    assert plate_service._is_missing_nh3_error(exc) is False


def test_is_missing_nh3_error_returns_false_for_other_dependency() -> None:
    """Reject another optional dependency even when it uses the canonical error class."""
    exc = MissingOptionalDependencyError(
        "bleach",
        "Optional dependency 'bleach' is required.",
    )
    assert plate_service._is_missing_nh3_error(exc) is False
