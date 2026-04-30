from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "design_guard.py"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _run_design_guard(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--manifest", "docs/design/figma-manifest.json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def _locked_manifest(export_sha: str) -> dict[str, object]:
    return {
        "manifest_version": "1.0",
        "contract_status": "locked",
        "token_source": "frontend/src/styles/tokens.css",
        "allowed_palette_hex": ["#102A43", "#3B82F6", "#20C997"],
        "core_lock": {
            "path": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "svg_sha256": "",
            "version": "v1.0",
            "lock_type": "L4",
            "figma_url": "",
            "node_id": "",
            "lock_state": "deferred",
            "deferred_reason": "Icon core masters are absent from this manifest-only lock.",
        },
        "exports": [
            {
                "path": "docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md",
                "sha256": export_sha,
                "figma_url": "https://www.figma.com/design/example/file?node-id=1040-2",
                "node_id": "1040:2",
                "version": "v1.0",
                "lock_type": "L3",
                "palette_hexes": ["#102A43", "#3B82F6"],
            }
        ],
    }


def test_design_guard_bootstrap_manifest_passes(tmp_path: Path) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )

    manifest = {
        "manifest_version": "1.0",
        "contract_status": "bootstrap",
        "token_source": "frontend/src/styles/tokens.css",
        "allowed_palette_hex": ["#102A43", "#3B82F6", "#20C997"],
        "core_lock": {
            "path": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "svg_sha256": "",
            "version": "v1.0",
            "lock_type": "L4",
            "figma_url": "",
            "node_id": "",
        },
        "exports": [],
    }
    manifest_path = tmp_path / "docs/design/figma-manifest.json"
    _write(manifest_path, json.dumps(manifest, indent=2))

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--manifest", "docs/design/figma-manifest.json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: design guard passed" in result.stdout


def test_design_guard_rejects_palette_drift_in_locked_state(tmp_path: Path) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )

    svg_path = tmp_path / "assets/brand/icon/core/v1.0/icon_core_v1.svg"
    svg_content = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
    _write(svg_path, svg_content)

    manifest = {
        "manifest_version": "1.0",
        "contract_status": "locked",
        "token_source": "frontend/src/styles/tokens.css",
        "allowed_palette_hex": ["#102A43", "#3B82F6", "#20C997"],
        "core_lock": {
            "path": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "svg_sha256": _sha256_text(svg_content),
            "version": "v1.0",
            "lock_type": "L4",
            "figma_url": "https://www.figma.com/design/example/file?node-id=1-1",
            "node_id": "1:1",
        },
        "exports": [
            {
                "path": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
                "figma_url": "https://www.figma.com/design/example/file?node-id=1-1",
                "node_id": "1:1",
                "version": "v1.0",
                "lock_type": "L4",
                "palette_hexes": ["#FFFFFF"],
            }
        ],
    }
    manifest_path = tmp_path / "docs/design/figma-manifest.json"
    _write(manifest_path, json.dumps(manifest, indent=2))

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--manifest", "docs/design/figma-manifest.json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "palette drift" in result.stdout


def test_design_guard_rejects_missing_allowed_palette_color_in_token_source(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; }\n",
    )

    manifest = {
        "manifest_version": "1.0",
        "contract_status": "bootstrap",
        "token_source": "frontend/src/styles/tokens.css",
        "allowed_palette_hex": ["#102A43", "#20C997"],
        "core_lock": {
            "path": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
            "svg_sha256": "",
            "version": "v1.0",
            "lock_type": "L4",
            "figma_url": "",
            "node_id": "",
        },
        "exports": [],
    }
    manifest_path = tmp_path / "docs/design/figma-manifest.json"
    _write(manifest_path, json.dumps(manifest, indent=2))

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--manifest", "docs/design/figma-manifest.json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "token drift" in result.stdout


def test_design_guard_accepts_locked_manifest_export_with_deferred_core(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )
    export_content = "# Runtime set audit\n"
    export_path = tmp_path / "docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md"
    _write(export_path, export_content)

    manifest_path = tmp_path / "docs/design/figma-manifest.json"
    _write(manifest_path, json.dumps(_locked_manifest(_sha256_text(export_content)), indent=2))

    result = _run_design_guard(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: design guard passed" in result.stdout


def test_design_guard_rejects_locked_manifest_missing_export_sha(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )
    export_content = "# Runtime set audit\n"
    _write(tmp_path / "docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md", export_content)
    manifest = _locked_manifest(_sha256_text(export_content))
    assert isinstance(manifest["exports"], list)
    assert isinstance(manifest["exports"][0], dict)
    manifest["exports"][0].pop("sha256")

    _write(tmp_path / "docs/design/figma-manifest.json", json.dumps(manifest, indent=2))

    result = _run_design_guard(tmp_path)

    assert result.returncode == 1
    assert "exports[0].sha256 is required in locked state" in result.stdout


def test_design_guard_rejects_locked_manifest_stale_export_sha(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )
    _write(tmp_path / "docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md", "# changed\n")
    manifest = _locked_manifest("0" * 64)

    _write(tmp_path / "docs/design/figma-manifest.json", json.dumps(manifest, indent=2))

    result = _run_design_guard(tmp_path)

    assert result.returncode == 1
    assert "exports[0].sha256 mismatch" in result.stdout


def test_design_guard_rejects_locked_manifest_invalid_node_id(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )
    export_content = "# Runtime set audit\n"
    _write(tmp_path / "docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md", export_content)
    manifest = _locked_manifest(_sha256_text(export_content))
    assert isinstance(manifest["exports"], list)
    assert isinstance(manifest["exports"][0], dict)
    manifest["exports"][0]["node_id"] = "TBD_AFTER_CAPTURE"

    _write(tmp_path / "docs/design/figma-manifest.json", json.dumps(manifest, indent=2))

    result = _run_design_guard(tmp_path)

    assert result.returncode == 1
    assert "exports[0].node_id must be a concrete Figma node id" in result.stdout


def test_design_guard_rejects_locked_manifest_absolute_export_path(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )
    export_content = "# Runtime set audit\n"
    export_path = tmp_path / "docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md"
    _write(export_path, export_content)
    manifest = _locked_manifest(_sha256_text(export_content))
    assert isinstance(manifest["exports"], list)
    assert isinstance(manifest["exports"][0], dict)
    manifest["exports"][0]["path"] = str(export_path)

    _write(tmp_path / "docs/design/figma-manifest.json", json.dumps(manifest, indent=2))

    result = _run_design_guard(tmp_path)

    assert result.returncode == 1
    assert "exports[0].path must be repo-relative" in result.stdout


def test_design_guard_rejects_locked_manifest_repo_escaping_export_path(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )
    export_content = "# Runtime set audit\n"
    _write(tmp_path.parent / "escaped.md", export_content)
    manifest = _locked_manifest(_sha256_text(export_content))
    assert isinstance(manifest["exports"], list)
    assert isinstance(manifest["exports"][0], dict)
    manifest["exports"][0]["path"] = "../escaped.md"

    _write(tmp_path / "docs/design/figma-manifest.json", json.dumps(manifest, indent=2))

    result = _run_design_guard(tmp_path)

    assert result.returncode == 1
    assert "exports[0].path must stay within the repo root" in result.stdout


def test_design_guard_rejects_locked_manifest_deferred_core_without_reason(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "frontend/src/styles/tokens.css",
        ":root { --pp-navy: #102A43; --pp-blue: #3B82F6; --pp-accent: #20C997; }\n",
    )
    export_content = "# Runtime set audit\n"
    _write(tmp_path / "docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md", export_content)
    manifest = _locked_manifest(_sha256_text(export_content))
    assert isinstance(manifest["core_lock"], dict)
    manifest["core_lock"].pop("deferred_reason")

    _write(tmp_path / "docs/design/figma-manifest.json", json.dumps(manifest, indent=2))

    result = _run_design_guard(tmp_path)

    assert result.returncode == 1
    assert "core_lock.deferred_reason is required" in result.stdout
