from __future__ import annotations

from typing import TypedDict


class LayoutSectionTemplate(TypedDict):
    id: str
    name: str
    role: str
    components: list[str]


class ComponentNodeTemplate(TypedDict):
    id: str
    canonical_component: str
    section_id: str
    parent_id: str | None
    hierarchy_level: int
    semantic_role: str
    source_ref: str


class ReusableLayoutTemplate(TypedDict):
    layout_sections: list[LayoutSectionTemplate]
    static_component_tree: list[ComponentNodeTemplate]


def _prefix(screen_id: str) -> str:
    return screen_id.replace(".", "-")


def _hero_actions_template(screen_id: str) -> ReusableLayoutTemplate:
    prefix = _prefix(screen_id)
    shell_id = f"{prefix}-shell"
    hero_id = f"{prefix}-hero"
    return {
        "layout_sections": [
            {
                "id": "hero-band",
                "name": "Hero band",
                "role": "context_summary",
                "components": ["hero", "badge", "stats-card"],
            },
            {
                "id": "quick-actions",
                "name": "Quick actions",
                "role": "primary_actions",
                "components": ["card", "button"],
            },
            {
                "id": "footer-nav",
                "name": "Footer navigation",
                "role": "persistent_navigation",
                "components": ["navigation/tab-bar"],
            },
        ],
        "static_component_tree": [
            {
                "id": shell_id,
                "canonical_component": "card",
                "section_id": "hero-band",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": f"template:{screen_id}:shell",
            },
            {
                "id": hero_id,
                "canonical_component": "hero",
                "section_id": "hero-band",
                "parent_id": shell_id,
                "hierarchy_level": 1,
                "semantic_role": "primary_message",
                "source_ref": f"template:{screen_id}:hero",
            },
            {
                "id": f"{prefix}-badge",
                "canonical_component": "badge",
                "section_id": "hero-band",
                "parent_id": hero_id,
                "hierarchy_level": 2,
                "semantic_role": "status_marker",
                "source_ref": f"template:{screen_id}:badge",
            },
            {
                "id": f"{prefix}-summary",
                "canonical_component": "stats-card",
                "section_id": "hero-band",
                "parent_id": shell_id,
                "hierarchy_level": 1,
                "semantic_role": "summary_metrics",
                "source_ref": f"template:{screen_id}:summary",
            },
            {
                "id": f"{prefix}-actions",
                "canonical_component": "card",
                "section_id": "quick-actions",
                "parent_id": shell_id,
                "hierarchy_level": 1,
                "semantic_role": "action_cluster",
                "source_ref": f"template:{screen_id}:actions",
            },
            {
                "id": f"{prefix}-nav",
                "canonical_component": "navigation/tab-bar",
                "section_id": "footer-nav",
                "parent_id": shell_id,
                "hierarchy_level": 1,
                "semantic_role": "persistent_navigation",
                "source_ref": f"template:{screen_id}:nav",
            },
        ],
    }


def _content_actions_template(screen_id: str) -> ReusableLayoutTemplate:
    prefix = _prefix(screen_id)
    shell_id = f"{prefix}-shell"
    summary_card_id = f"{prefix}-summary-card"
    action_panel_id = f"{prefix}-action-panel"
    return {
        "layout_sections": [
            {
                "id": "plate-summary",
                "name": "Plate summary",
                "role": "content_summary",
                "components": ["card", "badge", "progress"],
            },
            {
                "id": "plate-actions",
                "name": "Plate actions",
                "role": "primary_actions",
                "components": ["card", "button", "dialog"],
            },
        ],
        "static_component_tree": [
            {
                "id": shell_id,
                "canonical_component": "card",
                "section_id": "plate-summary",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": f"template:{screen_id}:shell",
            },
            {
                "id": summary_card_id,
                "canonical_component": "card",
                "section_id": "plate-summary",
                "parent_id": shell_id,
                "hierarchy_level": 1,
                "semantic_role": "content_container",
                "source_ref": f"template:{screen_id}:summary-card",
            },
            {
                "id": f"{prefix}-badge",
                "canonical_component": "badge",
                "section_id": "plate-summary",
                "parent_id": summary_card_id,
                "hierarchy_level": 2,
                "semantic_role": "gate_state",
                "source_ref": f"template:{screen_id}:badge",
            },
            {
                "id": f"{prefix}-progress",
                "canonical_component": "progress",
                "section_id": "plate-summary",
                "parent_id": summary_card_id,
                "hierarchy_level": 2,
                "semantic_role": "completion_feedback",
                "source_ref": f"template:{screen_id}:progress",
            },
            {
                "id": action_panel_id,
                "canonical_component": "card",
                "section_id": "plate-actions",
                "parent_id": shell_id,
                "hierarchy_level": 1,
                "semantic_role": "action_cluster",
                "source_ref": f"template:{screen_id}:action-panel",
            },
            {
                "id": f"{prefix}-dialog",
                "canonical_component": "dialog",
                "section_id": "plate-actions",
                "parent_id": action_panel_id,
                "hierarchy_level": 2,
                "semantic_role": "secondary_details",
                "source_ref": f"template:{screen_id}:dialog",
            },
        ],
    }


def _dashboard_recovery_template(screen_id: str) -> ReusableLayoutTemplate:
    prefix = _prefix(screen_id)
    shell_id = f"{prefix}-shell"
    chart_id = f"{prefix}-chart"
    recovery_id = f"{prefix}-recovery"
    sections: list[LayoutSectionTemplate] = [
        {
            "id": "progress-summary",
            "name": "Progress summary",
            "role": "summary_metrics",
            "components": ["stats-card", "progress"],
        },
        {
            "id": "progress-recovery",
            "name": "Recovery lane",
            "role": "state_recovery",
            "components": ["alert", "button"],
        },
    ]
    nodes: list[ComponentNodeTemplate] = [
        {
            "id": shell_id,
            "canonical_component": "card",
            "section_id": "progress-summary",
            "parent_id": None,
            "hierarchy_level": 0,
            "semantic_role": "surface_shell",
            "source_ref": f"template:{screen_id}:shell",
        },
        {
            "id": f"{prefix}-stats",
            "canonical_component": "stats-card",
            "section_id": "progress-summary",
            "parent_id": shell_id,
            "hierarchy_level": 1,
            "semantic_role": "summary_metrics",
            "source_ref": f"template:{screen_id}:stats",
        },
        {
            "id": chart_id,
            "canonical_component": "progress",
            "section_id": "progress-summary",
            "parent_id": shell_id,
            "hierarchy_level": 1,
            "semantic_role": "trend_visualization",
            "source_ref": f"template:{screen_id}:chart",
        },
        {
            "id": recovery_id,
            "canonical_component": "alert",
            "section_id": "progress-recovery",
            "parent_id": shell_id,
            "hierarchy_level": 1,
            "semantic_role": "recovery_message",
            "source_ref": f"template:{screen_id}:recovery",
        },
    ]

    if screen_id.startswith("ios."):
        sections[1]["components"].insert(1, "empty-state")
        nodes.append(
            {
                "id": f"{prefix}-empty",
                "canonical_component": "empty-state",
                "section_id": "progress-recovery",
                "parent_id": recovery_id,
                "hierarchy_level": 2,
                "semantic_role": "no_data_fallback",
                "source_ref": f"template:{screen_id}:empty",
            }
        )
    else:
        sections.insert(
            0,
            {
                "id": "progress-header",
                "name": "Progress header",
                "role": "utility_actions",
                "components": ["card", "button"],
            },
        )
        nodes.insert(
            1,
            {
                "id": f"{prefix}-header-utilities",
                "canonical_component": "card",
                "section_id": "progress-header",
                "parent_id": shell_id,
                "hierarchy_level": 1,
                "semantic_role": "utility_cluster",
                "source_ref": f"template:{screen_id}:header-utilities",
            },
        )
        sections[1]["components"].append("tooltip")
        nodes.append(
            {
                "id": f"{prefix}-tooltip",
                "canonical_component": "tooltip",
                "section_id": "progress-summary",
                "parent_id": chart_id,
                "hierarchy_level": 2,
                "semantic_role": "supporting_hint",
                "source_ref": f"template:{screen_id}:tooltip",
            }
        )

    return {"layout_sections": sections, "static_component_tree": nodes}


def _form_stack_template(screen_id: str) -> ReusableLayoutTemplate:
    prefix = _prefix(screen_id)
    shell_id = f"{prefix}-shell"
    return {
        "layout_sections": [
            {
                "id": "form-progress",
                "name": "Form progress",
                "role": "step_context",
                "components": ["stepper/progress-indicator"],
            },
            {
                "id": "form-fields",
                "name": "Form fields",
                "role": "data_collection",
                "components": ["form-field", "input", "select"],
            },
            {
                "id": "form-actions",
                "name": "Form actions",
                "role": "primary_actions",
                "components": ["button"],
            },
        ],
        "static_component_tree": [
            {
                "id": shell_id,
                "canonical_component": "card",
                "section_id": "form-progress",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": f"template:{screen_id}:shell",
            }
        ],
    }


def _navigation_overlay_template(screen_id: str) -> ReusableLayoutTemplate:
    prefix = _prefix(screen_id)
    shell_id = f"{prefix}-shell"
    return {
        "layout_sections": [
            {
                "id": "nav-primary",
                "name": "Primary navigation",
                "role": "persistent_navigation",
                "components": ["navigation/tab-bar"],
            },
            {
                "id": "nav-overlay",
                "name": "Overlay navigation",
                "role": "secondary_navigation",
                "components": ["mobile-menu", "button"],
            },
        ],
        "static_component_tree": [
            {
                "id": shell_id,
                "canonical_component": "card",
                "section_id": "nav-primary",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": f"template:{screen_id}:shell",
            }
        ],
    }


REUSABLE_LAYOUT_TEMPLATE_REGISTRY = {
    "hero_actions": _hero_actions_template,
    "content_actions": _content_actions_template,
    "dashboard_recovery": _dashboard_recovery_template,
    "form_stack": _form_stack_template,
    "navigation_overlay": _navigation_overlay_template,
}


def build_reusable_layout_template(
    template_key: str,
    screen_id: str,
) -> ReusableLayoutTemplate:
    """Resolve one reusable layout template for a concrete screen id."""

    template_builder = REUSABLE_LAYOUT_TEMPLATE_REGISTRY.get(template_key)
    if template_builder is None:
        raise ValueError(f"Unsupported layout template '{template_key}' for screen '{screen_id}'")
    return template_builder(screen_id)
