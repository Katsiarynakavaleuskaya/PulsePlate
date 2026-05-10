"""Tests for icon core v1 validator behavior."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

from scripts import validate_icon_core_v1 as validator


def _write_icon_core_fixture(
    tmp_root: pathlib.Path,
    *,
    include_masters: bool,
    include_derived: bool = False,
    include_meta: bool = True,
    unexpected_files: list[str] | None = None,
    meta_payload: dict | str | None = None,
) -> pathlib.Path:
    """Create a temporary icon-core fixture and return the core directory path."""

    core_dir = tmp_root / "assets" / "brand" / "icon" / "core" / "v1.0"
    core_dir.mkdir(parents=True, exist_ok=True)

    (core_dir / "README.md").write_text("fixture\n", encoding="utf-8")

    if include_masters:
        for name in (
            "icon_core_v1.svg",
            "icon_core_v1_1024.png",
            "icon_core_v1_60.png",
        ):
            (core_dir / name).write_text(f"{name}\n", encoding="utf-8")

    if include_derived:
        for name in (
            "icon_core_v1_120.png",
            "icon_core_v1_32.png",
            "icon_core_v1_24.png",
        ):
            (core_dir / name).write_text(f"{name}\n", encoding="utf-8")

    if unexpected_files:
        for filename in unexpected_files:
            (core_dir / filename).write_text("unexpected\n", encoding="utf-8")

    if include_meta:
        if isinstance(meta_payload, str):
            payload = meta_payload
        elif meta_payload is None:
            payload = json.dumps(
                {
                    "contract_id": "EMBLEM_CORE_v1.0_LOCK",
                    "version": "v1.0",
                    "master_policy": "dual-master-svg-png",
                    "figma_source_type": "design",
                    "figma_design_url": "spec://design-url",
                    "figma_file_key": "design-file-key",
                    "figma_node_id": "1024:2048",
                    "assets": {
                        "svg_master": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
                        "png_master_1024": "assets/brand/icon/core/v1.0/icon_core_v1_1024.png",
                        "png_master_60": "assets/brand/icon/core/v1.0/icon_core_v1_60.png",
                        "png_derived_120": "assets/brand/icon/core/v1.0/icon_core_v1_120.png",
                        "png_derived_32": "assets/brand/icon/core/v1.0/icon_core_v1_32.png",
                        "png_derived_24": "assets/brand/icon/core/v1.0/icon_core_v1_24.png",
                    },
                    "hashes": {
                        "master_svg_sha256": "sha256:" + "a" * 64,
                        "master_png_1024_sha256": "sha256:" + "b" * 64,
                        "master_png_60_sha256": "sha256:" + "c" * 64,
                        "silhouette_mask_sha256_1024": "sha256:" + "d" * 64,
                        "silhouette_mask_sha256_60": "sha256:" + "e" * 64,
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
        else:
            payload = json.dumps(meta_payload, indent=2, ensure_ascii=False)

        (core_dir / "meta.json").write_text(payload, encoding="utf-8")

    return core_dir


def _run_validator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_root: pathlib.Path,
    *,
    strict: bool = False,
    require_lock_values: bool = False,
    require_canonical_masters: bool = False,
    include_masters: bool = True,
    include_derived: bool = False,
    include_meta: bool = True,
    unexpected_files: list[str] | None = None,
    meta_payload: dict | str | None = None,
    repo_root: pathlib.Path | None = None,
) -> list[str]:
    _write_icon_core_fixture(
        tmp_root,
        include_masters=include_masters,
        include_derived=include_derived,
        include_meta=include_meta,
        unexpected_files=unexpected_files,
        meta_payload=meta_payload,
    )
    root = repo_root if repo_root is not None else tmp_root
    return validator.validate(
        strict=strict,
        require_lock_values=require_lock_values,
        require_canonical_masters=require_canonical_masters,
        repo_root=root,
    )


def test_default_validator_passes_current_repo_fixture() -> None:
    """Current repository fixture should pass in default mode."""

    result = subprocess.run(
        [sys.executable, "scripts/validate_icon_core_v1.py"],
        cwd=pathlib.Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "OK: icon core v1.0 structure valid (default mode)" in result.stdout


def test_require_canonical_masters_catches_missing_masters(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Master enforcement mode should fail when canonical masters are missing."""

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        require_canonical_masters=True,
        include_masters=False,
    )
    assert any(
        err.startswith("missing canonical masters (require-canonical-masters mode)")
        for err in errors
    )


def test_missing_meta_json_is_single_governance_error(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Absent meta.json should not produce duplicate governance-line errors."""

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        include_masters=True,
        include_meta=False,
    )
    meta_lines = [e for e in errors if "meta.json" in e]
    assert len(meta_lines) == 1
    assert meta_lines[0].startswith("missing required governance files:")


def test_malformed_meta_json_is_detected(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed meta JSON must be reported as validation error."""

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        include_masters=True,
        meta_payload='{"contract_id": "bad", "assets": ',
    )
    assert any("invalid meta.json" in err for err in errors)
    assert any("JSON parse error at line" in err for err in errors)


def test_meta_json_size_cap(tmp_path: pathlib.Path) -> None:
    """Very large meta.json must fail without feeding megabytes to json.load."""

    core = _write_icon_core_fixture(
        tmp_path,
        include_masters=True,
        include_meta=False,
    )
    (core / "meta.json").write_bytes(b"x" * (validator.META_JSON_MAX_BYTES + 1))
    errors = validator.validate(repo_root=tmp_path)
    assert any("meta.json exceeds max size" in e for e in errors)


def test_symlinked_core_dir_outside_repo_rejected(tmp_path: pathlib.Path) -> None:
    """Resolved icon core path must stay under repo root (symlink escape)."""

    if not hasattr(pathlib.Path, "symlink_to"):
        pytest.skip("symlink_to not available")

    outside = tmp_path / "outside"
    outside.mkdir(parents=True)
    (outside / "README.md").write_text("outside\n", encoding="utf-8")

    repo = tmp_path / "repo"
    link_parent = repo / "assets" / "brand" / "icon" / "core"
    link_parent.mkdir(parents=True)
    link = link_parent / "v1.0"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("cannot create symlink in this environment")

    errors = validator.validate(repo_root=repo)
    assert any("resolves outside repo root" in e for e in errors)


def test_cli_accepts_repo_root(tmp_path: pathlib.Path) -> None:
    """CLI --repo-root must validate a subtree without cwd being that repo."""

    repo = pathlib.Path(__file__).resolve().parents[1]
    _write_icon_core_fixture(tmp_path, include_masters=True)
    script = repo / "scripts" / "validate_icon_core_v1.py"
    result = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(tmp_path)],
        cwd="/",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "OK: icon core v1.0 structure valid" in result.stdout


def test_asset_paths_must_match_canonical_names(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Metadata asset paths must point at canonical icon-core filenames."""

    bad_meta = {
        "contract_id": "EMBLEM_CORE_v1.0_LOCK",
        "version": "v1.0",
        "master_policy": "dual-master-svg-png",
        "figma_source_type": "design",
        "figma_design_url": "spec://design-url",
        "figma_file_key": "design-file-key",
        "figma_node_id": "1024:2048",
        "assets": {
            "svg_master": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "png_master_1024": "assets/brand/icon/core/v1.0/icon_core_1024.png",
            "png_master_60": "assets/brand/icon/core/v1.0/icon_core_60.png",
            "png_derived_120": "assets/brand/icon/core/v1.0/icon_core_v1_120.png",
            "png_derived_32": "assets/brand/icon/core/v1.0/icon_core_v1_32.png",
            "png_derived_24": "assets/brand/icon/core/v1.0/icon_core_v1_24.png",
        },
        "hashes": {
            "master_svg_sha256": "sha256:" + "a" * 64,
            "master_png_1024_sha256": "sha256:" + "b" * 64,
            "master_png_60_sha256": "sha256:" + "c" * 64,
            "silhouette_mask_sha256_1024": "sha256:" + "d" * 64,
            "silhouette_mask_sha256_60": "sha256:" + "e" * 64,
        },
    }

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        strict=True,
        include_masters=True,
        meta_payload=bad_meta,
    )
    assert (
        "meta.json assets.png_master_1024 must be assets/brand/icon/core/v1.0/icon_core_v1_1024.png"
        in errors
    )
    assert (
        "meta.json assets.png_master_60 must be assets/brand/icon/core/v1.0/icon_core_v1_60.png"
        in errors
    )


def test_canonical_derived_files_are_allowed(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repo-owned derived icon files should be allowed when they are later added."""

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        strict=True,
        include_masters=True,
        include_derived=True,
    )
    assert errors == []


def test_unexpected_file_is_detected(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unexpected files in the icon core directory must fail validation."""

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        include_masters=True,
        unexpected_files=["tmp_backup.txt"],
    )
    assert any(err.startswith("unexpected files in") for err in errors)


def test_require_lock_values_rejects_placeholders(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lock mode must reject TBD placeholders and report exact fields."""

    meta_with_placeholders = {
        "contract_id": "EMBLEM_CORE_v1.0_LOCK",
        "version": "v1.0",
        "master_policy": "dual-master-svg-png",
        "figma_source_type": "design",
        "figma_design_url": "TBD_AFTER_WINNER_LOCK",
        "figma_file_key": "TBD_AFTER_WINNER_LOCK",
        "figma_node_id": "TBD_AFTER_WINNER_LOCK",
        "assets": {
            "svg_master": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "png_master_1024": "assets/brand/icon/core/v1.0/icon_core_v1_1024.png",
            "png_master_60": "assets/brand/icon/core/v1.0/icon_core_v1_60.png",
            "png_derived_120": "assets/brand/icon/core/v1.0/icon_core_v1_120.png",
            "png_derived_32": "assets/brand/icon/core/v1.0/icon_core_v1_32.png",
            "png_derived_24": "assets/brand/icon/core/v1.0/icon_core_v1_24.png",
        },
        "hashes": {
            "master_svg_sha256": "TBD_AFTER_WINNER_LOCK",
            "master_png_1024_sha256": "TBD_AFTER_WINNER_LOCK",
            "master_png_60_sha256": "TBD_AFTER_WINNER_LOCK",
            "silhouette_mask_sha256_1024": "TBD_AFTER_WINNER_LOCK",
            "silhouette_mask_sha256_60": "TBD_AFTER_WINNER_LOCK",
        },
    }

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        require_lock_values=True,
        include_masters=True,
        meta_payload=meta_with_placeholders,
    )
    assert any("meta.json lock placeholders found" in err for err in errors)


def test_require_lock_values_rejects_noncanonical_placeholders(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lock mode must reject empty, TBD-like, and non-hash placeholder values."""

    meta_with_noncanonical_placeholders = {
        "contract_id": "EMBLEM_CORE_v1.0_LOCK",
        "version": "v1.0",
        "master_policy": "dual-master-svg-png",
        "figma_source_type": "design",
        "figma_design_url": "TBD",
        "figma_file_key": "",
        "figma_node_id": "unknown",
        "assets": {
            "svg_master": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "png_master_1024": "assets/brand/icon/core/v1.0/icon_core_v1_1024.png",
            "png_master_60": "assets/brand/icon/core/v1.0/icon_core_v1_60.png",
            "png_derived_120": "assets/brand/icon/core/v1.0/icon_core_v1_120.png",
            "png_derived_32": "assets/brand/icon/core/v1.0/icon_core_v1_32.png",
            "png_derived_24": "assets/brand/icon/core/v1.0/icon_core_v1_24.png",
        },
        "hashes": {
            "master_svg_sha256": "",
            "master_png_1024_sha256": "TBD",
            "master_png_60_sha256": "sha256:" + "c" * 64,
            "silhouette_mask_sha256_1024": "not-a-sha",
            "silhouette_mask_sha256_60": "sha256:" + "e" * 64,
        },
    }

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        require_lock_values=True,
        include_masters=True,
        meta_payload=meta_with_noncanonical_placeholders,
    )
    assert any("meta.json lock placeholders found" in err for err in errors)


def test_require_lock_values_rejects_invalid_sha256_digest_shapes(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lock mode must reject sha256-prefixed values without a real digest."""

    invalid_hashes = {
        "master_svg_sha256": "sha256:x",
        "master_png_1024_sha256": "sha256:TBD_AFTER_WINNER_LOCK",
        "master_png_60_sha256": "sha256:not-a-sha",
        "silhouette_mask_sha256_1024": "sha256:ABCDEF",
        "silhouette_mask_sha256_60": "sha256:123",
    }
    meta_with_invalid_hashes = {
        "contract_id": "EMBLEM_CORE_v1.0_LOCK",
        "version": "v1.0",
        "master_policy": "dual-master-svg-png",
        "figma_source_type": "design",
        "figma_design_url": "spec://design-url",
        "figma_file_key": "design-file-key",
        "figma_node_id": "1024:2048",
        "assets": {
            "svg_master": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "png_master_1024": "assets/brand/icon/core/v1.0/icon_core_v1_1024.png",
            "png_master_60": "assets/brand/icon/core/v1.0/icon_core_v1_60.png",
            "png_derived_120": "assets/brand/icon/core/v1.0/icon_core_v1_120.png",
            "png_derived_32": "assets/brand/icon/core/v1.0/icon_core_v1_32.png",
            "png_derived_24": "assets/brand/icon/core/v1.0/icon_core_v1_24.png",
        },
        "hashes": invalid_hashes,
    }

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        require_lock_values=True,
        include_masters=True,
        meta_payload=meta_with_invalid_hashes,
    )

    assert any("meta.json lock placeholders found" in err for err in errors)
    for key in invalid_hashes:
        assert any(f"hashes.{key}=" in err for err in errors)


def test_require_canonical_masters_does_not_require_derived_files(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--require-canonical-masters checks masters only; derived PNGs remain optional on disk."""

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        require_canonical_masters=True,
        include_masters=True,
        include_derived=False,
    )
    assert errors == []


def test_strict_mode_reports_missing_required_top_level_meta_fields(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Strict contract validation must list missing top-level meta fields."""

    meta = {
        "contract_id": "EMBLEM_CORE_v1.0_LOCK",
        "version": "v1.0",
        # Deliberately omit several REQUIRED_META_TOP_LEVEL_FIELDS.
        "master_policy": "dual-master-svg-png",
        "figma_source_type": "design",
    }

    errors = _run_validator(
        monkeypatch,
        tmp_path,
        strict=True,
        include_masters=True,
        meta_payload=meta,
    )
    assert any("meta.json missing required top-level fields" in err for err in errors)
    assert any("assets" in err for err in errors)
    assert any("hashes" in err for err in errors)


def test_strict_mode_reports_missing_asset_keys_without_duplicate_shape_errors(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing assets keys should not also emit a generic non-object error."""

    meta = {
        "contract_id": "EMBLEM_CORE_v1.0_LOCK",
        "version": "v1.0",
        "master_policy": "dual-master-svg-png",
        "figma_source_type": "design",
        "figma_design_url": "spec://design-url",
        "figma_file_key": "design-file-key",
        "figma_node_id": "1024:2048",
        "assets": {
            "svg_master": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
        },
        "hashes": {
            "master_svg_sha256": "sha256:" + "a" * 64,
            "master_png_1024_sha256": "sha256:" + "b" * 64,
            "master_png_60_sha256": "sha256:" + "c" * 64,
            "silhouette_mask_sha256_1024": "sha256:" + "d" * 64,
            "silhouette_mask_sha256_60": "sha256:" + "e" * 64,
        },
    }

    errors = _run_validator(
        monkeypatch, tmp_path, strict=True, include_masters=True, meta_payload=meta
    )
    assert any("meta.json assets missing required keys" in err for err in errors)
    assert "meta.json must define assets as an object" not in errors


def test_strict_mode_rejects_non_object_assets_and_hashes(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """assets/hashes must be JSON objects when present under strict validation."""

    meta_assets_list = {
        "contract_id": "EMBLEM_CORE_v1.0_LOCK",
        "version": "v1.0",
        "master_policy": "dual-master-svg-png",
        "figma_source_type": "design",
        "figma_design_url": "spec://design-url",
        "figma_file_key": "design-file-key",
        "figma_node_id": "1024:2048",
        "assets": [],
        "hashes": {
            "master_svg_sha256": "sha256:" + "a" * 64,
            "master_png_1024_sha256": "sha256:" + "b" * 64,
            "master_png_60_sha256": "sha256:" + "c" * 64,
            "silhouette_mask_sha256_1024": "sha256:" + "d" * 64,
            "silhouette_mask_sha256_60": "sha256:" + "e" * 64,
        },
    }

    errors_assets = _run_validator(
        monkeypatch,
        tmp_path,
        strict=True,
        include_masters=True,
        meta_payload=meta_assets_list,
    )
    assert "meta.json must define assets as an object" in errors_assets

    meta_hashes_str = {
        "contract_id": "EMBLEM_CORE_v1.0_LOCK",
        "version": "v1.0",
        "master_policy": "dual-master-svg-png",
        "figma_source_type": "design",
        "figma_design_url": "spec://design-url",
        "figma_file_key": "design-file-key",
        "figma_node_id": "1024:2048",
        "assets": {
            "svg_master": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "png_master_1024": "assets/brand/icon/core/v1.0/icon_core_v1_1024.png",
            "png_master_60": "assets/brand/icon/core/v1.0/icon_core_v1_60.png",
            "png_derived_120": "assets/brand/icon/core/v1.0/icon_core_v1_120.png",
            "png_derived_32": "assets/brand/icon/core/v1.0/icon_core_v1_32.png",
            "png_derived_24": "assets/brand/icon/core/v1.0/icon_core_v1_24.png",
        },
        "hashes": "not-a-dict",
    }

    errors_hashes = _run_validator(
        monkeypatch,
        tmp_path,
        strict=True,
        include_masters=True,
        meta_payload=meta_hashes_str,
    )
    assert "meta.json must define hashes as an object" in errors_hashes


def test_default_and_compat_strict_cli_regression_without_tbd(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default and strict validation should pass with filled lock values."""

    errors_default = _run_validator(
        monkeypatch,
        tmp_path,
        require_lock_values=True,
        include_masters=True,
    )
    errors_strict = _run_validator(
        monkeypatch,
        tmp_path,
        strict=True,
        require_lock_values=True,
        include_masters=True,
    )
    assert errors_default == []
    assert errors_strict == []
