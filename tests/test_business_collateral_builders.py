from __future__ import annotations

import json
import posixpath
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
WORDPROCESSING_ML_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PACKAGE_REL_NAMESPACE = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CONTENT_TYPE_NAMESPACE = "{http://schemas.openxmlformats.org/package/2006/content-types}"
SUBPROCESS_TIMEOUT_SECONDS = 120


def require_feature(feature_key: str, reason: str) -> None:
    expected_reason = f"feature_disabled:{feature_key}"
    if reason != expected_reason:
        pytest.fail(f"invalid feature skip reason: expected {expected_reason!r}, got {reason!r}")
    pytest.skip(reason)


def _node_binary_or_skip() -> str:
    node_binary = shutil.which("node")
    if node_binary is None:
        require_feature("node_runtime", "feature_disabled:node_runtime")
        raise AssertionError("require_feature should always raise pytest skip")
    return node_binary


def _run_subprocess(command: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
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


def _run_node_eval(script: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    node_binary = _node_binary_or_skip()
    return _run_subprocess([node_binary, "-e", script], cwd=cwd)


def _node_package_or_skip(package_name: str, repo_root: Path = REPO_ROOT) -> None:
    result = _run_node_eval(
        f'process.stdout.write(require.resolve("{package_name}"));', cwd=repo_root
    )
    if result.returncode == 0:
        package_dir = repo_root.resolve() / "node_modules" / package_name
        resolved_path = Path(result.stdout).resolve()
        assert resolved_path.is_relative_to(
            package_dir
        ), f"{package_name} resolved outside this worktree: {resolved_path}"
        if package_name == "docx":
            lock = json.loads((repo_root / "package-lock.json").read_text(encoding="utf-8"))
            locked_version = lock["packages"]["node_modules/docx"]["version"]
            installed = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
            assert installed["version"] == locked_version
        return

    stderr = (result.stderr or "").lower()
    if "module_not_found" in stderr or "cannot find module" in stderr:
        require_feature(
            f"node_package_{package_name}",
            f"feature_disabled:node_package_{package_name}",
        )

    pytest.fail(
        "Node failed while checking for optional package "
        f"'{package_name}':\n"
        f"exit code: {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def _read_office_document_xml(output_path: Path, member_name: str) -> str:
    with zipfile.ZipFile(output_path) as archive:
        return archive.read(member_name).decode("utf-8")


def _resolve_relationship_target(base_path: str, target: str) -> str:
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join(base_path, target))


def _extract_docx_blocks(document_xml: str, numbering_xml: str) -> list[tuple[str, str]]:
    # Compare source blocks, not incidental XML run boundaries or DOCX bytes.
    root = ElementTree.fromstring(document_xml)
    numbering_root = ElementTree.fromstring(numbering_xml)
    bullet_abstract_ids = {
        abstract.get(f"{WORDPROCESSING_ML_NAMESPACE}abstractNumId")
        for abstract in numbering_root.findall(f"{WORDPROCESSING_ML_NAMESPACE}abstractNum")
        for level in abstract.findall(f"{WORDPROCESSING_ML_NAMESPACE}lvl")
        if level.get(f"{WORDPROCESSING_ML_NAMESPACE}ilvl") == "0"
        and (number_format := level.find(f"{WORDPROCESSING_ML_NAMESPACE}numFmt")) is not None
        and number_format.get(f"{WORDPROCESSING_ML_NAMESPACE}val") == "bullet"
    }
    bullet_number_ids = {
        number.get(f"{WORDPROCESSING_ML_NAMESPACE}numId")
        for number in numbering_root.findall(f"{WORDPROCESSING_ML_NAMESPACE}num")
        if (abstract_id := number.find(f"{WORDPROCESSING_ML_NAMESPACE}abstractNumId")) is not None
        and abstract_id.get(f"{WORDPROCESSING_ML_NAMESPACE}val") in bullet_abstract_ids
    }
    blocks: list[tuple[str, str]] = []
    for paragraph in root.iter(f"{WORDPROCESSING_ML_NAMESPACE}p"):
        text = "".join(
            node.text or "" for node in paragraph.iter(f"{WORDPROCESSING_ML_NAMESPACE}t")
        )
        properties = paragraph.find(f"{WORDPROCESSING_ML_NAMESPACE}pPr")
        style = (
            properties.find(f"{WORDPROCESSING_ML_NAMESPACE}pStyle")
            if properties is not None
            else None
        )
        numbering = (
            properties.find(f"{WORDPROCESSING_ML_NAMESPACE}numPr")
            if properties is not None
            else None
        )
        style_name = style.get(f"{WORDPROCESSING_ML_NAMESPACE}val") if style is not None else None
        if numbering is not None:
            level = numbering.find(f"{WORDPROCESSING_ML_NAMESPACE}ilvl")
            number_id = numbering.find(f"{WORDPROCESSING_ML_NAMESPACE}numId")
            assert level is not None and level.get(f"{WORDPROCESSING_ML_NAMESPACE}val") == "0"
            assert number_id is not None
            assert number_id.get(f"{WORDPROCESSING_ML_NAMESPACE}val") in bullet_number_ids
            block_type = "bullet"
        else:
            block_type = {
                "Title": "title",
                "Heading1": "heading1",
                "Heading2": "heading2",
                None: "paragraph",
            }[style_name]
        blocks.append((block_type, text))
    return blocks


def test_b2b_proposal_builder_creates_docx(tmp_path: Path) -> None:
    _node_package_or_skip("docx")
    source_result = _run_node_eval(
        'process.stdout.write(JSON.stringify(require("./scripts/business_collateral/content_loader").parseProposalSpec()));'
    )
    assert source_result.returncode == 0, source_result.stderr
    source = json.loads(source_result.stdout)
    source_path = REPO_ROOT / "docs/audience_pack/B2B_PARTNERSHIP_PROPOSAL_SPEC.md"
    assert source["sourcePath"] == str(source_path)
    expected_blocks = [("title", source["title"])] + [
        (block["type"], block["text"]) for block in source["blocks"]
    ]
    placeholders = set(re.findall(r"\[VERIFY_[^\]]+\]", source_path.read_text(encoding="utf-8")))
    assert placeholders

    output_path = tmp_path / "proposal.docx"
    result = _run_builder("scripts/business_collateral/build_b2b_proposal.js", output_path)

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert str(output_path) in result.stdout

    assert zipfile.is_zipfile(output_path)
    required_parts = {
        "[Content_Types].xml",
        "_rels/.rels",
        "word/document.xml",
        "word/_rels/document.xml.rels",
        "word/styles.xml",
        "word/numbering.xml",
    }
    with zipfile.ZipFile(output_path) as archive:
        assert archive.testzip() is None
        assert required_parts <= set(archive.namelist())

        content_types = ElementTree.fromstring(archive.read("[Content_Types].xml"))
        overrides = {
            item.get("PartName"): item.get("ContentType")
            for item in content_types.findall(f"{CONTENT_TYPE_NAMESPACE}Override")
        }
        assert overrides["/word/document.xml"] == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        )
        assert "/word/numbering.xml" in overrides

        for relationships_path, base_path, required_types in (
            ("_rels/.rels", "", {"officeDocument": "word/document.xml"}),
            (
                "word/_rels/document.xml.rels",
                "word",
                {"styles": "word/styles.xml", "numbering": "word/numbering.xml"},
            ),
        ):
            relationships = ElementTree.fromstring(archive.read(relationships_path))
            targets = {
                item.get("Type", "").rsplit("/", 1)[-1]: _resolve_relationship_target(
                    base_path, item.get("Target", "")
                )
                for item in relationships.findall(f"{PACKAGE_REL_NAMESPACE}Relationship")
                if item.get("TargetMode") != "External"
            }
            for relationship_type, target in required_types.items():
                assert targets[relationship_type] == target
                assert target in archive.namelist()

    actual_blocks = _extract_docx_blocks(
        _read_office_document_xml(output_path, "word/document.xml"),
        _read_office_document_xml(output_path, "word/numbering.xml"),
    )
    assert actual_blocks == expected_blocks
    document_text = " ".join(text for _, text in actual_blocks)
    assert placeholders <= set(re.findall(r"\[VERIFY_[^\]]+\]", document_text))
    assert "PulsePlate B2B Partnership Proposal Spec" not in document_text
    assert "markdownlint-disable" not in document_text


def test_docx_relationship_target_resolves_absolute_and_relative_paths() -> None:
    assert _resolve_relationship_target("word", "/word/styles.xml") == "word/styles.xml"
    assert _resolve_relationship_target("word", "styles.xml") == "word/styles.xml"


def test_docx_probe_rejects_parent_node_modules_fallback(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    parent_package = parent / "node_modules/docx"
    parent_package.mkdir(parents=True)
    (parent_package / "package.json").write_text(
        json.dumps({"name": "docx", "version": "9.6.1", "main": "index.js"}), encoding="utf-8"
    )
    (parent_package / "index.js").write_text("module.exports = {};\n", encoding="utf-8")
    child_worktree = parent / "worktrees/child"
    child_worktree.mkdir(parents=True)

    resolution = _run_node_eval(
        'process.stdout.write(require.resolve("docx"));', cwd=child_worktree
    )
    assert resolution.returncode == 0, resolution.stderr
    assert Path(resolution.stdout).resolve().is_relative_to(parent_package)
    with pytest.raises(AssertionError, match="docx resolved outside this worktree"):
        _node_package_or_skip("docx", repo_root=child_worktree)


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


def test_retired_pptx_execution_surface_stays_absent() -> None:
    """The four canonical local-PPTX restore points remain retired."""
    root_manifest = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = root_manifest.get("scripts")
    assert isinstance(scripts, dict)
    assert "build:b2b-pitch-deck" not in scripts
    assert scripts.get("build:business-collateral") == "npm run build:b2b-proposal"

    assert not (REPO_ROOT / "scripts/business_collateral/build_b2b_pitch_deck.js").exists()
    content_loader = (REPO_ROOT / "scripts/business_collateral/content_loader.js").read_text(
        encoding="utf-8"
    )
    assert "parseDeckSpec" not in content_loader
