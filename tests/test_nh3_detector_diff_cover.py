from core.data_sanitizer import MissingOptionalDependencyError
import legacy_app


def test_is_missing_nh3_error_detects_module_not_found() -> None:
    exc = ModuleNotFoundError("No module named 'nh3'")
    # Ensure the `name` attribute is set (covers legacy_app getattr(exc, "name") path).
    exc.name = "nh3"  # type: ignore[attr-defined]
    assert legacy_app._is_missing_nh3_error(exc) is True


def test_is_missing_nh3_error_detects_import_error_message() -> None:
    exc = ImportError("No module named 'nh3'")
    assert legacy_app._is_missing_nh3_error(exc) is True


def test_is_missing_nh3_error_detects_missing_optional_dependency_error() -> None:
    exc = MissingOptionalDependencyError(
        "nh3",
        "Optional dependency 'nh3' is required for plate data sanitization.",
    )
    assert legacy_app._is_missing_nh3_error(exc) is True


def test_is_missing_nh3_error_returns_false_for_other_module() -> None:
    exc = ModuleNotFoundError("No module named 'requests'", name="requests")
    assert legacy_app._is_missing_nh3_error(exc) is False


def test_is_missing_nh3_error_returns_false_for_other_import_error() -> None:
    exc = ImportError("Cannot import name 'foo'")
    assert legacy_app._is_missing_nh3_error(exc) is False


def test_is_missing_nh3_error_returns_false_for_other_dependency() -> None:
    exc = MissingOptionalDependencyError(
        "bleach",
        "Optional dependency 'bleach' is required.",
    )
    assert legacy_app._is_missing_nh3_error(exc) is False
