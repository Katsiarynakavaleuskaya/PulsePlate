from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
WORDPROCESSING_ML_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
SUBPROCESS_TIMEOUT_SECONDS = 120


def _node_binary_or_skip() -> str:
    node_binary = shutil.which("node")
    if node_binary is None:
        pytest.skip("node executable not found in PATH")
    return node_binary


def _run_subprocess(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"subprocess timed out after {SUBPROCESS_TIMEOUT_SECONDS}s: {exc.cmd}")


def _run_builder(script_relative_path: str, output_path: Path) -> subprocess.CompletedProcess[str]:
    node_binary = _node_binary_or_skip()
    script_path = REPO_ROOT / script_relative_path
    return _run_subprocess([node_binary, str(script_path), "--output", str(output_path)])


def _run_node_eval(script: str) -> subprocess.CompletedProcess[str]:
    node_binary = _node_binary_or_skip()
    return _run_subprocess([node_binary, "-e", script])


def _read_office_document_xml(output_path: Path, member_name: str) -> str:
    with zipfile.ZipFile(output_path) as archive:
        return archive.read(member_name).decode("utf-8")


def _extract_docx_text(document_xml: str) -> str:
    # RU: Собираем текст из всех text-run, чтобы тест не зависел от внутреннего XML-разбиения DOCX.
    # EN: Join all DOCX text runs so assertions do not depend on internal XML run splitting.
    root = ElementTree.fromstring(document_xml)
    return "".join(node.text or "" for node in root.iter(WORDPROCESSING_ML_NAMESPACE))


def test_b2b_proposal_builder_creates_docx(tmp_path: Path) -> None:
    output_path = tmp_path / "proposal.docx"
    result = _run_builder("scripts/business_collateral/build_b2b_proposal.js", output_path)

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert str(output_path) in result.stdout

    document_xml = _read_office_document_xml(output_path, "word/document.xml")
    document_text = _extract_docx_text(document_xml)

    assert "PulsePlate partnership proposal for wellness and nutrition workflows" in document_text
    assert "PulsePlate B2B Partnership Proposal Spec" not in document_text
    assert "markdownlint-disable" not in document_text


def test_markdown_parser_skips_multiline_html_comments() -> None:
    script = """
const { parseMarkdownBlocks } = require("./scripts/business_collateral/content_loader");
const result = parseMarkdownBlocks(`<!-- markdownlint-disable
still a comment -->

## Visible Heading

Visible paragraph.`);
process.stdout.write(JSON.stringify(result));
"""
    result = _run_node_eval(script)

    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)

    assert payload["blocks"] == [
        {"type": "heading1", "text": "Visible Heading"},
        {"type": "paragraph", "text": "Visible paragraph."},
    ]


def test_b2b_pitch_deck_builder_creates_pptx(tmp_path: Path) -> None:
    output_path = tmp_path / "deck.pptx"
    result = _run_builder("scripts/business_collateral/build_b2b_pitch_deck.js", output_path)

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert str(output_path) in result.stdout

    with zipfile.ZipFile(output_path) as archive:
        assert "ppt/presentation.xml" in archive.namelist()
