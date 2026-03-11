from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VOCABULARY_PATH = REPO_ROOT / "docs" / "design" / "ui_component_vocabulary.json"
REQUIRED_COMPONENTS = {
    "button",
    "input",
    "select",
    "textarea",
    "checkbox",
    "radio-group",
    "card",
    "alert",
    "badge",
    "dialog",
    "dropdown-menu",
    "tabs",
    "progress",
    "tooltip",
    "empty-state",
    "segmented-control",
    "toggle",
    "skeleton",
    "mobile-menu",
    "navigation/tab-bar",
    "hero",
    "stats-card",
    "form-field",
    "stepper/progress-indicator",
}
REQUIRED_KEYS = {
    "id",
    "canonical_name",
    "aliases",
    "intent",
    "when_to_use",
    "when_not_to_use",
    "anatomy",
    "states",
    "accessibility_notes",
    "token_guidance",
    "react_mapping",
    "swiftui_mapping",
    "existing_repo_component",
    "missing_status",
    "prompt_terms",
    "anti_generic_terms",
    "stitch_normalization_hint",
}


def _load_vocabulary() -> list[dict[str, object]]:
    return json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))


def test_ui_component_vocabulary_contract_is_valid() -> None:
    vocabulary = _load_vocabulary()

    assert isinstance(vocabulary, list)
    assert vocabulary

    canonical_names: set[str] = set()
    aliases: set[str] = set()

    for entry in vocabulary:
        assert REQUIRED_KEYS == set(entry.keys())

        canonical_name = str(entry["canonical_name"]).strip()
        normalized_canonical_name = canonical_name.lower()

        assert canonical_name
        assert normalized_canonical_name not in canonical_names
        canonical_names.add(normalized_canonical_name)

        prompt_terms = entry["prompt_terms"]
        anti_generic_terms = entry["anti_generic_terms"]
        existing_repo_component = entry["existing_repo_component"]

        assert isinstance(prompt_terms, list)
        assert prompt_terms
        assert all(isinstance(term, str) and term.strip() for term in prompt_terms)

        assert isinstance(anti_generic_terms, list)
        assert anti_generic_terms
        assert all(isinstance(term, str) and term.strip() for term in anti_generic_terms)

        entry_aliases = entry["aliases"]
        assert isinstance(entry_aliases, list)
        assert entry_aliases

        for alias in entry_aliases:
            normalized_alias = str(alias).strip().lower()

            assert normalized_alias
            assert normalized_alias != normalized_canonical_name
            assert normalized_alias not in aliases
            aliases.add(normalized_alias)

        if existing_repo_component is not None:
            resolved_path = REPO_ROOT / str(existing_repo_component)
            assert resolved_path.exists(), str(resolved_path)


def test_required_canonical_components_are_present() -> None:
    vocabulary = _load_vocabulary()
    canonical_names = {str(entry["canonical_name"]) for entry in vocabulary}

    assert REQUIRED_COMPONENTS == canonical_names


def test_design_and_agent_docs_reference_the_vocabulary_layer() -> None:
    required_references = {
        REPO_ROOT
        / "docs"
        / "design"
        / "DESIGN_SYSTEM_FOR_CODE.md": [
            "UI_COMPONENT_VOCABULARY.md",
            "CODE_FIRST_UI_PROMPT_COOKBOOK.md",
            "UI_SCREEN_BRIEF_TEMPLATES.md",
        ],
        REPO_ROOT
        / "docs"
        / "design"
        / "VISUAL_IMPLEMENTATION_MAP.md": [
            "UI_COMPONENT_VOCABULARY.md",
            "CODE_FIRST_UI_PROMPT_COOKBOOK.md",
        ],
        REPO_ROOT
        / "docs"
        / "runbooks"
        / "DESIGN_TOOLING_OPERATING_MODEL.md": [
            "STITCH_AI_REFERENCE_ADAPTER.md",
            "stitch_reference",
            "ui_component_vocabulary.json",
        ],
        REPO_ROOT
        / ".cursor"
        / "agents"
        / "creative-designer.md": [
            "UI_COMPONENT_VOCABULARY.md",
            "UI_SCREEN_BRIEF_TEMPLATES.md",
            "CODE_FIRST_UI_PROMPT_COOKBOOK.md",
        ],
        REPO_ROOT
        / ".cursor"
        / "agents"
        / "frontend-engineer.md": [
            "UI_COMPONENT_VOCABULARY.md",
            "CODE_FIRST_UI_PROMPT_COOKBOOK.md",
        ],
        REPO_ROOT
        / "docs"
        / "orchestration"
        / "AGENT_CONTEXT_MAP.md": [
            "UI_COMPONENT_VOCABULARY.md",
            "CODE_FIRST_UI_PROMPT_COOKBOOK.md",
        ],
        REPO_ROOT
        / "tools"
        / "codex_skills"
        / "pulseplate-workflow"
        / "SKILL.md": [
            "UI_COMPONENT_VOCABULARY.md",
            "CODE_FIRST_UI_PROMPT_COOKBOOK.md",
        ],
        REPO_ROOT
        / "tools"
        / "codex_skills"
        / "pulseplate-frontend-ui"
        / "SKILL.md": [
            "UI_COMPONENT_VOCABULARY.md",
            "CODE_FIRST_UI_PROMPT_COOKBOOK.md",
            "Canonical components",
        ],
    }

    for path, snippets in required_references.items():
        text = path.read_text(encoding="utf-8")

        for snippet in snippets:
            assert snippet in text, f"{snippet} missing in {path}"
