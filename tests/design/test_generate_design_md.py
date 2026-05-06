from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts/design/generate_design_md.py"


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_design_md", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_output_is_deterministic_across_repeated_runs():
    module = load_generator_module()

    first = module.render_design_md(REPO_ROOT)
    second = module.render_design_md(REPO_ROOT)

    assert first == second
