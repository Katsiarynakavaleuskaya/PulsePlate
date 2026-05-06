from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts/design/generate_design_md.py"


def load_generator_module() -> SimpleNamespace:
    return SimpleNamespace(**runpy.run_path(str(MODULE_PATH)))


def make_temp_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    design_dir = repo_root / "docs/design"
    design_dir.mkdir(parents=True)
    shutil.copyfile(
        REPO_ROOT / "docs/design/ui_component_vocabulary.json",
        design_dir / "ui_component_vocabulary.json",
    )
    return repo_root


def test_generated_design_md_contains_source_of_truth_warning():
    module = load_generator_module()

    output = module.render_design_md(REPO_ROOT)

    assert module.WARNING in output
    assert "not a source of truth" in output
    assert "repo truth wins" in output


def test_generated_design_md_names_token_authoring_source_and_review_lanes():
    module = load_generator_module()

    output = module.render_design_md(REPO_ROOT)

    assert "`/tokens` remains the token authoring source" in output
    assert "Storybook as review and documentation only" in output
    assert "Figma as design-intent and review evidence only" in output
    assert "External references are read-only" in output


def test_generated_design_md_includes_canonical_component_vocabulary():
    module = load_generator_module()

    output = module.render_design_md(REPO_ROOT)

    assert "`button`" in output
    assert "`segmented_control`" in output
    assert "| navigation_tab_bar | navigation/tab-bar | existing |" in output
    assert (
        "| select | select | existing-runtime-detected | "
        "`frontend/src/components/ui/Select.tsx` |"
    ) in output


def test_duplicate_component_ids_fail_closed(tmp_path):
    module = load_generator_module()
    repo_root = make_temp_repo(tmp_path)
    vocabulary_path = repo_root / "docs/design/ui_component_vocabulary.json"
    vocabulary = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    vocabulary.append(dict(vocabulary[0]))
    vocabulary_path.write_text(json.dumps(vocabulary), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate component id"):
        module.render_design_md(repo_root)


def test_stale_declared_component_path_uses_runtime_fallback(tmp_path):
    module = load_generator_module()
    repo_root = make_temp_repo(tmp_path)
    fallback_path = repo_root / "frontend/src/components/ui/Select.tsx"
    fallback_path.parent.mkdir(parents=True)
    fallback_path.write_text("export function Select() {}\n", encoding="utf-8")
    vocabulary_path = repo_root / "docs/design/ui_component_vocabulary.json"
    vocabulary = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    for item in vocabulary:
        if item["id"] == "select":
            item["existing_repo_component"] = "frontend/src/components/ui/StaleSelect.tsx"
            item["missing_status"] = "existing"
            break
    vocabulary_path.write_text(json.dumps(vocabulary), encoding="utf-8")

    output = module.render_design_md(repo_root)

    assert "frontend/src/components/ui/StaleSelect.tsx" not in output
    assert (
        "| select | select | existing-runtime-detected | "
        "`frontend/src/components/ui/Select.tsx` |"
    ) in output


def test_declared_absolute_component_path_is_rejected(tmp_path):
    module = load_generator_module()
    repo_root = make_temp_repo(tmp_path)
    external_component = tmp_path / "external_component.tsx"
    external_component.write_text("export function External() {}\n", encoding="utf-8")
    fallback_path = repo_root / "frontend/src/components/ui/Select.tsx"
    fallback_path.parent.mkdir(parents=True)
    fallback_path.write_text("export function Select() {}\n", encoding="utf-8")
    vocabulary_path = repo_root / "docs/design/ui_component_vocabulary.json"
    vocabulary = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    for item in vocabulary:
        if item["id"] == "select":
            item["existing_repo_component"] = str(external_component)
            item["missing_status"] = "existing"
            break
    vocabulary_path.write_text(json.dumps(vocabulary), encoding="utf-8")

    output = module.render_design_md(repo_root)

    assert str(external_component) not in output
    assert "frontend/src/components/ui/Select.tsx" not in output
    assert "| select | select | invalid-declared-path | `none` |" in output


def test_declared_traversal_component_path_is_rejected(tmp_path):
    module = load_generator_module()
    repo_root = make_temp_repo(tmp_path)
    external_component = tmp_path / "outside_component.tsx"
    external_component.write_text("export function Outside() {}\n", encoding="utf-8")
    vocabulary_path = repo_root / "docs/design/ui_component_vocabulary.json"
    vocabulary = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    for item in vocabulary:
        if item["id"] == "button":
            item["existing_repo_component"] = "../outside_component.tsx"
            item["missing_status"] = "existing"
            break
    vocabulary_path.write_text(json.dumps(vocabulary), encoding="utf-8")

    output = module.render_design_md(repo_root)

    assert "../outside_component.tsx" not in output
    assert "| button | button | invalid-declared-path | `none` |" in output


def test_declared_in_repo_non_frontend_component_path_is_rejected(tmp_path):
    module = load_generator_module()
    repo_root = make_temp_repo(tmp_path)
    disallowed_component = repo_root / "docs/design/not_a_component.tsx"
    disallowed_component.write_text("export const x = 1;\n", encoding="utf-8")
    vocabulary_path = repo_root / "docs/design/ui_component_vocabulary.json"
    vocabulary = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    for item in vocabulary:
        if item["id"] == "button":
            item["existing_repo_component"] = "docs/design/not_a_component.tsx"
            item["missing_status"] = "existing"
            break
    vocabulary_path.write_text(json.dumps(vocabulary), encoding="utf-8")

    output = module.render_design_md(repo_root)

    assert "docs/design/not_a_component.tsx" not in output
    assert "| button | button | invalid-declared-path | `none` |" in output


def test_generated_design_md_classifies_automation_as_internal_modules():
    module = load_generator_module()

    output = module.render_design_md(REPO_ROOT)

    assert "modules inside the existing PulsePlate Design Intelligence" in output
    assert "not standalone plugins" in output
    assert "Icon Asset Validator -> release/design asset guard module" in output
    assert (
        "Button / Component Drift Inspector -> Design Intelligence PR-4 deterministic scorecard"
        in output
    )


def test_check_fails_on_drift(tmp_path, capsys):
    module = load_generator_module()
    repo_root = make_temp_repo(tmp_path)
    design_md = repo_root / "docs/design/DESIGN.md"
    design_md.write_text("drifted\n", encoding="utf-8")

    result = module.run(["--check"], repo_root=repo_root)
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR: docs/design/DESIGN.md is out of date." in captured.err
    assert "Run: python3 scripts/design/generate_design_md.py" in captured.err


def test_check_fails_when_design_md_missing(tmp_path, capsys):
    module = load_generator_module()
    repo_root = make_temp_repo(tmp_path)

    result = module.run(["--check"], repo_root=repo_root)
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR: docs/design/DESIGN.md is missing." in captured.err
    assert "Run: python3 scripts/design/generate_design_md.py" in captured.err


def test_check_passes_after_regeneration(tmp_path, capsys):
    module = load_generator_module()
    repo_root = make_temp_repo(tmp_path)

    assert module.run([], repo_root=repo_root) == 0
    assert module.run(["--check"], repo_root=repo_root) == 0
    captured = capsys.readouterr()

    assert "OK: docs/design/DESIGN.md is up to date." in captured.out


def test_check_passes_against_committed_design_md(capsys):
    module = load_generator_module()

    assert module.run(["--check"], repo_root=REPO_ROOT) == 0
    captured = capsys.readouterr()

    assert "OK: docs/design/DESIGN.md is up to date." in captured.out


def test_output_is_deterministic_across_repeated_runs():
    module = load_generator_module()

    first = module.render_design_md(REPO_ROOT)
    second = module.render_design_md(REPO_ROOT)

    assert first == second
