def test_app_package_spec_proxy_name():
    import app as apppkg

    # Accessing __spec__.name should not crash and should be 'app'
    name = getattr(apppkg, "__spec__").name  # type: ignore[attr-defined]
    assert name == "app"


def test_app_package_spec_proxy_rebinds_sys_modules():
    import sys

    import app as apppkg

    # Replace sys.modules['app'] with a placeholder to simulate external mutation
    sys.modules["app"] = object()  # type: ignore[assignment]
    # Accessing name should trigger proxy and rebind sys.modules['app'] back to module
    name = getattr(apppkg, "__spec__").name  # type: ignore[attr-defined]
    assert name == "app" and sys.modules["app"] is apppkg


def test_app_getattr_passes_through_and_raises_attribute_error():
    import pytest

    import app as apppkg

    # __getattr__ should delegate to underlying module and raise on missing
    with pytest.raises(AttributeError):
        getattr(apppkg, "__definitely_missing_symbol__")
