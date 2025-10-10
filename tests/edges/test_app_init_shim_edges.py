"""
Edges for app package shim (__init__.py): passthrough attr and spec proxy name.
"""

import app as apppkg


def test_app_package_spec_proxy_and_getattr_passthrough():
    # Accessing __spec__.name returns 'app' and keeps module bound
    spec = getattr(apppkg, "__spec__")
    name = getattr(spec, "name", None)
    assert name == "app"

    # getattr passthrough for an attribute via underlying module
    setattr(apppkg._mod, "_tmp_attr", "value")
    try:
        assert getattr(apppkg, "_tmp_attr") == "value"
    finally:
        delattr(apppkg._mod, "_tmp_attr")


def test_app_package_spec_proxy_attrs_exist():
    spec = getattr(apppkg, "__spec__")
    # origin/loader/submodule_search_locations should be accessible without raising
    _ = getattr(spec, "origin", None)
    _ = getattr(spec, "loader", None)
    loc = getattr(spec, "submodule_search_locations", [])
    assert isinstance(loc, (list, tuple))


def test_app_package_all_and_sysmodules_binding(monkeypatch):
    import sys

    # Ensure __all__ exposes app
    exported = getattr(apppkg, "__all__", [])
    assert "app" in exported

    # Break binding and verify spec.name rebinds sys.modules['app'] to this module
    monkeypatch.setitem(sys.modules, "app", object())
    spec = getattr(apppkg, "__spec__")
    _ = getattr(spec, "name")
    assert sys.modules.get("app") is apppkg


def test_app_getattr_missing_raises_attributeerror():
    try:
        getattr(apppkg, "__definitely_missing_attribute__")
        raised = False
    except AttributeError:
        raised = True
    assert raised
