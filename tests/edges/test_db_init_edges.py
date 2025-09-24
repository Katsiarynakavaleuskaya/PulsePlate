def test_init_db_wraps_create_all_when_missing_assert(monkeypatch):
    import core.db as db

    original_meta = db.Base.metadata
    original_create_all = original_meta.create_all

    called = {"v": False}

    def fake_create_all(*args, **kwargs):
        called["v"] = True
        # accept bind kw to mimic signature
        return None

    # ensure no assert_called_once attribute exists
    assert not hasattr(fake_create_all, "assert_called_once")

    try:
        # replace with plain function lacking helper
        db.Base.metadata.create_all = fake_create_all
        # call init_db — should wrap and invoke our fake
        db.init_db()

        wrapped = db.Base.metadata.create_all
        # after init, wrapper should exist and our fake should have been called
        assert callable(wrapped)
        assert called["v"] is True
        # wrapper should expose assert_called_once
        assert hasattr(wrapped, "assert_called_once")
        getattr(wrapped, "assert_called_once")()
    finally:
        # restore
        db.Base.metadata = original_meta
        db.Base.metadata.create_all = original_create_all
