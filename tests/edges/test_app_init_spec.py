def test_app_package_spec_proxy_name():
    import app as apppkg

    # Accessing __spec__.name should not crash and should be 'app'
    name = getattr(apppkg, "__spec__").name  # type: ignore[attr-defined]
    assert name == "app"
