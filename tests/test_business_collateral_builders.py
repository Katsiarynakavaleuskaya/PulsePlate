from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_builder(script_relative_path: str, output_path: Path) -> subprocess.CompletedProcess[str]:
    script_path = REPO_ROOT / script_relative_path
    return subprocess.run(
        ["node", str(script_path), "--output", str(output_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_b2b_proposal_builder_creates_docx(tmp_path: Path) -> None:
    output_path = tmp_path / "proposal.docx"
    result = _run_builder("scripts/business_collateral/build_b2b_proposal.js", output_path)

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert str(output_path) in result.stdout

    with zipfile.ZipFile(output_path) as archive:
        assert "word/document.xml" in archive.namelist()


def test_b2b_pitch_deck_builder_creates_pptx(tmp_path: Path) -> None:
    output_path = tmp_path / "deck.pptx"
    result = _run_builder("scripts/business_collateral/build_b2b_pitch_deck.js", output_path)

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert str(output_path) in result.stdout

    with zipfile.ZipFile(output_path) as archive:
        assert "ppt/presentation.xml" in archive.namelist()
