"""Independent export-format contract coverage."""

import pytest


def test_export_format_media_type_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover fail-fast behavior when an ExportFormat mapping is incomplete."""
    from core.export_format import ExportFormat
    import core.export_format as export_format_module

    media_types = dict(export_format_module._MEDIA_TYPES)
    media_types.pop(ExportFormat.JSON, None)
    monkeypatch.setattr(export_format_module, "_MEDIA_TYPES", media_types)

    with pytest.raises(NotImplementedError, match="Missing media_type mapping"):
        _ = ExportFormat.JSON.media_type
