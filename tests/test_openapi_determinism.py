"""Test that OpenAPI generation is deterministic across multiple runs."""

import hashlib
import subprocess
from pathlib import Path


def _sha256(path: Path) -> str:
    """Calculate SHA256 hash of file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_openapi_and_schema_ts_are_deterministic() -> None:
    """
    Verify that full OpenAPI pipeline produces identical output across runs.

    This test ensures that:
    - Normalization in scripts/generate_openapi.py works correctly
    - openapi-typescript generates deterministic schema.ts with --alphabetize flag
    - No drift occurs in openapi.json or schema.ts
    - Full pipeline (make openapi) is deterministic for CI and local development
    """
    repo_root = Path(__file__).resolve().parents[1]
    openapi_path = repo_root / "frontend" / "src" / "api" / "openapi.json"
    schema_path = repo_root / "frontend" / "src" / "api" / "schema.ts"

    # Run full pipeline twice (same as CI)
    # Use make directly (not bash -lc) for better compatibility
    subprocess.check_call(
        ["make", "openapi"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    h1 = (_sha256(openapi_path), _sha256(schema_path))

    subprocess.check_call(
        ["make", "openapi"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    h2 = (_sha256(openapi_path), _sha256(schema_path))

    assert h1 == h2, (
        f"Drift detected:\n" f"  openapi.json: {h1[0]} != {h2[0]}\n"
        if h1[0] != h2[0]
        else (
            "" f"  schema.ts: {h1[1]} != {h2[1]}\n"
            if h1[1] != h2[1]
            else ""
            "This indicates non-deterministic generation.\n"
            "Check scripts/generate_openapi.py and frontend/package.json (openapi-typescript version/flags)."
        )
    )
