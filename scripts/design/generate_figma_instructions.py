#!/usr/bin/env python3
"""
Figma Instruction Generator for PulsePlate Design Execution.

Transforms design documentation (button matrix, visual guidelines, tokens)
into structured Figma AI instructions.

Usage:
    python scripts/design/generate_figma_instructions.py --screen ios.home --validate
    python scripts/design/generate_figma_instructions.py --screen ios.home --output instructions/ios_home.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.design.contracts import validate_instruction_contract
from scripts.design.layout_templates import (
    ComponentNodeTemplate,
    LayoutSectionTemplate,
    build_reusable_layout_template,
)

# Project root for resolving paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class CTASpec:
    """Specification for a single CTA/button."""

    cta_id: str
    platform: str
    screen: str
    ui_label: str
    trigger_type: str
    status: str
    variant: str
    placement_zone: str
    prompt_stub: str
    figma_node_id: str = ""
    states: list[str] = field(
        default_factory=lambda: ["default", "hover", "disabled", "loading", "error"]
    )


@dataclass
class ScreenInstruction:
    """Instruction set for a single screen."""

    screen_id: str
    page: str
    platform: str
    surface: str
    layout_archetype: str
    layout_pattern: str
    sections: list["LayoutSectionSpec"]
    component_hierarchy: list["ComponentNodeSpec"]
    primary_components: list[str]
    supporting_components: list[str]
    states: list[str]
    dimensions: dict[str, int]
    background_token: str
    token_constraints: list[str]
    ctas: list[CTASpec]
    governance_checks: list[str]
    context_version: str = ""


@dataclass
class LayoutSectionSpec:
    """Declarative section metadata for layout assembly."""

    section_id: str
    name: str
    role: str
    component_ids: list[str] = field(default_factory=list)


@dataclass
class ComponentNodeSpec:
    """Flat component tree node with explicit parent linkage."""

    component_id: str
    canonical_component: str
    section_id: str
    parent_component_id: str | None
    hierarchy_level: int
    semantic_role: str
    source_ref: str


class ScreenContentModel(TypedDict):
    surface: str
    layout_archetype: str
    layout_pattern: str
    layout_template_key: str
    layout_sections: list[LayoutSectionTemplate]
    static_component_tree: list[ComponentNodeTemplate]
    cta_section_id: str
    cta_parent_id: str
    primary_components: list[str]
    supporting_components: list[str]
    states: list[str]
    token_constraints: list[str]


# Screen dimension presets
SCREEN_DIMENSIONS = {
    "ios": {"width": 390, "height": 844},  # iPhone 14 Pro
    "web": {"width": 1440, "height": 900},  # Desktop
}

PLATFORM_CANONICAL_NAMES = {
    "ios": "iOS",
    "web": "Web",
}

# Page mapping from governance index
PAGE_MAPPING = {
    "ios.home": "10_iOS_Home",
    "ios.plate": "11_iOS_Plate",
    "ios.progress": "12_iOS_Progress",
    "web.home": "20_Web_Parity",
    "web.plate": "20_Web_Parity",
    "web.progress": "20_Web_Parity",
}

SCREEN_CONTENT_MODEL: dict[str, ScreenContentModel] = {
    "ios.home": {
        "surface": "ios_home_screen",
        "layout_archetype": "hero_shell",
        "layout_pattern": "hero-plus-quick-actions",
        "layout_template_key": "hero_actions",
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
                "id": "ios-home-shell",
                "canonical_component": "card",
                "section_id": "hero-band",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": "static:ios-home-shell",
            },
            {
                "id": "ios-home-hero",
                "canonical_component": "hero",
                "section_id": "hero-band",
                "parent_id": "ios-home-shell",
                "hierarchy_level": 1,
                "semantic_role": "primary_message",
                "source_ref": "static:ios-home-hero",
            },
            {
                "id": "ios-home-badge",
                "canonical_component": "badge",
                "section_id": "hero-band",
                "parent_id": "ios-home-hero",
                "hierarchy_level": 2,
                "semantic_role": "status_marker",
                "source_ref": "static:ios-home-badge",
            },
            {
                "id": "ios-home-summary",
                "canonical_component": "stats-card",
                "section_id": "hero-band",
                "parent_id": "ios-home-shell",
                "hierarchy_level": 1,
                "semantic_role": "summary_metrics",
                "source_ref": "static:ios-home-summary",
            },
            {
                "id": "ios-home-actions",
                "canonical_component": "card",
                "section_id": "quick-actions",
                "parent_id": "ios-home-shell",
                "hierarchy_level": 1,
                "semantic_role": "action_cluster",
                "source_ref": "static:ios-home-actions",
            },
            {
                "id": "ios-home-nav",
                "canonical_component": "navigation/tab-bar",
                "section_id": "footer-nav",
                "parent_id": "ios-home-shell",
                "hierarchy_level": 1,
                "semantic_role": "persistent_navigation",
                "source_ref": "static:ios-home-nav",
            },
        ],
        "cta_section_id": "quick-actions",
        "cta_parent_id": "ios-home-actions",
        "primary_components": ["hero", "button", "card"],
        "supporting_components": ["stats-card", "navigation/tab-bar", "badge"],
        "states": ["default", "feature-flagged", "loading", "error"],
        "token_constraints": ["Color.navy", "Color.appPrimary", "Color.surface"],
    },
    "ios.plate": {
        "surface": "ios_plate_screen",
        "layout_archetype": "content_shell",
        "layout_pattern": "content-card-with-primary-actions",
        "layout_template_key": "content_actions",
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
                "id": "ios-plate-shell",
                "canonical_component": "card",
                "section_id": "plate-summary",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": "static:ios-plate-shell",
            },
            {
                "id": "ios-plate-summary-card",
                "canonical_component": "card",
                "section_id": "plate-summary",
                "parent_id": "ios-plate-shell",
                "hierarchy_level": 1,
                "semantic_role": "content_container",
                "source_ref": "static:ios-plate-summary-card",
            },
            {
                "id": "ios-plate-badge",
                "canonical_component": "badge",
                "section_id": "plate-summary",
                "parent_id": "ios-plate-summary-card",
                "hierarchy_level": 2,
                "semantic_role": "gate_state",
                "source_ref": "static:ios-plate-badge",
            },
            {
                "id": "ios-plate-progress",
                "canonical_component": "progress",
                "section_id": "plate-summary",
                "parent_id": "ios-plate-summary-card",
                "hierarchy_level": 2,
                "semantic_role": "completion_feedback",
                "source_ref": "static:ios-plate-progress",
            },
            {
                "id": "ios-plate-action-panel",
                "canonical_component": "card",
                "section_id": "plate-actions",
                "parent_id": "ios-plate-shell",
                "hierarchy_level": 1,
                "semantic_role": "action_cluster",
                "source_ref": "static:ios-plate-action-panel",
            },
            {
                "id": "ios-plate-dialog",
                "canonical_component": "dialog",
                "section_id": "plate-actions",
                "parent_id": "ios-plate-action-panel",
                "hierarchy_level": 2,
                "semantic_role": "secondary_details",
                "source_ref": "static:ios-plate-dialog",
            },
        ],
        "cta_section_id": "plate-actions",
        "cta_parent_id": "ios-plate-action-panel",
        "primary_components": ["card", "button"],
        "supporting_components": ["badge", "dialog", "progress"],
        "states": ["default", "issue-recovery", "loading", "error"],
        "token_constraints": ["Color.navy", "Color.surface", "Color.appPrimary"],
    },
    "ios.progress": {
        "surface": "ios_progress_screen",
        "layout_archetype": "dashboard_shell",
        "layout_pattern": "dashboard-summary-stack",
        "layout_template_key": "dashboard_recovery",
        "layout_sections": [
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
                "components": ["alert", "empty-state", "button"],
            },
        ],
        "static_component_tree": [
            {
                "id": "ios-progress-shell",
                "canonical_component": "card",
                "section_id": "progress-summary",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": "static:ios-progress-shell",
            },
            {
                "id": "ios-progress-stats",
                "canonical_component": "stats-card",
                "section_id": "progress-summary",
                "parent_id": "ios-progress-shell",
                "hierarchy_level": 1,
                "semantic_role": "summary_metrics",
                "source_ref": "static:ios-progress-stats",
            },
            {
                "id": "ios-progress-chart",
                "canonical_component": "progress",
                "section_id": "progress-summary",
                "parent_id": "ios-progress-shell",
                "hierarchy_level": 1,
                "semantic_role": "trend_visualization",
                "source_ref": "static:ios-progress-chart",
            },
            {
                "id": "ios-progress-recovery",
                "canonical_component": "alert",
                "section_id": "progress-recovery",
                "parent_id": "ios-progress-shell",
                "hierarchy_level": 1,
                "semantic_role": "recovery_message",
                "source_ref": "static:ios-progress-recovery",
            },
            {
                "id": "ios-progress-empty",
                "canonical_component": "empty-state",
                "section_id": "progress-recovery",
                "parent_id": "ios-progress-recovery",
                "hierarchy_level": 2,
                "semantic_role": "no_data_fallback",
                "source_ref": "static:ios-progress-empty",
            },
        ],
        "cta_section_id": "progress-recovery",
        "cta_parent_id": "ios-progress-recovery",
        "primary_components": ["progress", "button"],
        "supporting_components": ["stats-card", "empty-state", "alert"],
        "states": ["default", "empty", "loading", "error"],
        "token_constraints": ["Color.navy", "Color.surface", "Color.accentGreen"],
    },
    "web.home": {
        "surface": "web_home_screen",
        "layout_archetype": "hero_shell",
        "layout_pattern": "hero-plus-status-grid",
        "layout_template_key": "hero_actions",
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
                "id": "web-home-shell",
                "canonical_component": "card",
                "section_id": "hero-band",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": "static:web-home-shell",
            },
            {
                "id": "web-home-hero",
                "canonical_component": "hero",
                "section_id": "hero-band",
                "parent_id": "web-home-shell",
                "hierarchy_level": 1,
                "semantic_role": "primary_message",
                "source_ref": "static:web-home-hero",
            },
            {
                "id": "web-home-badge",
                "canonical_component": "badge",
                "section_id": "hero-band",
                "parent_id": "web-home-hero",
                "hierarchy_level": 2,
                "semantic_role": "status_marker",
                "source_ref": "static:web-home-badge",
            },
            {
                "id": "web-home-summary",
                "canonical_component": "stats-card",
                "section_id": "hero-band",
                "parent_id": "web-home-shell",
                "hierarchy_level": 1,
                "semantic_role": "summary_metrics",
                "source_ref": "static:web-home-summary",
            },
            {
                "id": "web-home-actions",
                "canonical_component": "card",
                "section_id": "quick-actions",
                "parent_id": "web-home-shell",
                "hierarchy_level": 1,
                "semantic_role": "action_cluster",
                "source_ref": "static:web-home-actions",
            },
            {
                "id": "web-home-nav",
                "canonical_component": "navigation/tab-bar",
                "section_id": "footer-nav",
                "parent_id": "web-home-shell",
                "hierarchy_level": 1,
                "semantic_role": "persistent_navigation",
                "source_ref": "static:web-home-nav",
            },
        ],
        "cta_section_id": "quick-actions",
        "cta_parent_id": "web-home-actions",
        "primary_components": ["hero", "button"],
        "supporting_components": ["stats-card", "navigation/tab-bar", "badge"],
        "states": ["default", "feature-flagged", "loading", "error"],
        "token_constraints": ["--pp-navy", "--color-primary", "--color-surface"],
    },
    "web.plate": {
        "surface": "web_plate_screen",
        "layout_archetype": "content_shell",
        "layout_pattern": "content-card-with-upgrade-actions",
        "layout_template_key": "content_actions",
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
                "id": "web-plate-shell",
                "canonical_component": "card",
                "section_id": "plate-summary",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": "static:web-plate-shell",
            },
            {
                "id": "web-plate-summary-card",
                "canonical_component": "card",
                "section_id": "plate-summary",
                "parent_id": "web-plate-shell",
                "hierarchy_level": 1,
                "semantic_role": "content_container",
                "source_ref": "static:web-plate-summary-card",
            },
            {
                "id": "web-plate-badge",
                "canonical_component": "badge",
                "section_id": "plate-summary",
                "parent_id": "web-plate-summary-card",
                "hierarchy_level": 2,
                "semantic_role": "premium_state",
                "source_ref": "static:web-plate-badge",
            },
            {
                "id": "web-plate-progress",
                "canonical_component": "progress",
                "section_id": "plate-summary",
                "parent_id": "web-plate-summary-card",
                "hierarchy_level": 2,
                "semantic_role": "completion_feedback",
                "source_ref": "static:web-plate-progress",
            },
            {
                "id": "web-plate-action-panel",
                "canonical_component": "card",
                "section_id": "plate-actions",
                "parent_id": "web-plate-shell",
                "hierarchy_level": 1,
                "semantic_role": "action_cluster",
                "source_ref": "static:web-plate-action-panel",
            },
            {
                "id": "web-plate-dialog",
                "canonical_component": "dialog",
                "section_id": "plate-actions",
                "parent_id": "web-plate-action-panel",
                "hierarchy_level": 2,
                "semantic_role": "upgrade_explainer",
                "source_ref": "static:web-plate-dialog",
            },
        ],
        "cta_section_id": "plate-actions",
        "cta_parent_id": "web-plate-action-panel",
        "primary_components": ["card", "button"],
        "supporting_components": ["badge", "dialog", "progress"],
        "states": ["default", "premium-gated", "loading", "error"],
        "token_constraints": ["--pp-navy", "--color-primary", "--color-surface"],
    },
    "web.progress": {
        "surface": "web_progress_screen",
        "layout_archetype": "dashboard_shell",
        "layout_pattern": "dashboard-detail-stack",
        "layout_template_key": "dashboard_recovery",
        "layout_sections": [
            {
                "id": "progress-header",
                "name": "Progress header",
                "role": "utility_actions",
                "components": ["card", "button"],
            },
            {
                "id": "progress-summary",
                "name": "Progress summary",
                "role": "summary_metrics",
                "components": ["stats-card", "progress", "tooltip"],
            },
            {
                "id": "progress-recovery",
                "name": "Recovery lane",
                "role": "state_recovery",
                "components": ["alert", "button"],
            },
        ],
        "static_component_tree": [
            {
                "id": "web-progress-shell",
                "canonical_component": "card",
                "section_id": "progress-summary",
                "parent_id": None,
                "hierarchy_level": 0,
                "semantic_role": "surface_shell",
                "source_ref": "static:web-progress-shell",
            },
            {
                "id": "web-progress-header-utilities",
                "canonical_component": "card",
                "section_id": "progress-header",
                "parent_id": "web-progress-shell",
                "hierarchy_level": 1,
                "semantic_role": "utility_cluster",
                "source_ref": "static:web-progress-header-utilities",
            },
            {
                "id": "web-progress-stats",
                "canonical_component": "stats-card",
                "section_id": "progress-summary",
                "parent_id": "web-progress-shell",
                "hierarchy_level": 1,
                "semantic_role": "summary_metrics",
                "source_ref": "static:web-progress-stats",
            },
            {
                "id": "web-progress-chart",
                "canonical_component": "progress",
                "section_id": "progress-summary",
                "parent_id": "web-progress-shell",
                "hierarchy_level": 1,
                "semantic_role": "trend_visualization",
                "source_ref": "static:web-progress-chart",
            },
            {
                "id": "web-progress-tooltip",
                "canonical_component": "tooltip",
                "section_id": "progress-summary",
                "parent_id": "web-progress-chart",
                "hierarchy_level": 2,
                "semantic_role": "supporting_hint",
                "source_ref": "static:web-progress-tooltip",
            },
            {
                "id": "web-progress-recovery",
                "canonical_component": "alert",
                "section_id": "progress-recovery",
                "parent_id": "web-progress-shell",
                "hierarchy_level": 1,
                "semantic_role": "recovery_message",
                "source_ref": "static:web-progress-recovery",
            },
        ],
        "cta_section_id": "progress-header",
        "cta_parent_id": "web-progress-header-utilities",
        "primary_components": ["progress", "button"],
        "supporting_components": ["stats-card", "tooltip", "alert"],
        "states": ["default", "loading", "empty", "error", "export-success"],
        "token_constraints": ["--pp-navy", "--color-success", "--color-surface"],
    },
}

# CTA registry parsed from docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md
# This is a simplified extraction - in production would parse the markdown
CTA_REGISTRY = {
    # iOS Home CTAs
    "ios.home.bmi_calculator": CTASpec(
        cta_id="ios.home.bmi_calculator",
        platform="iOS",
        screen="Home",
        ui_label="BMI Calculator",
        trigger_type="NavigationLink",
        status="Implemented",
        variant="V1",
        placement_zone="I_HOME_QUICK_ACTIONS",
        prompt_stub="stub://icon-nav/bmi",
        figma_node_id="PP/iOS/Home/QuickActions/BMI/Row/Default (TBD)",
    ),
    "ios.home.profile_setup": CTASpec(
        cta_id="ios.home.profile_setup",
        platform="iOS",
        screen="Home",
        ui_label="Profile Setup",
        trigger_type="NavigationLink",
        status="Implemented",
        variant="V1",
        placement_zone="I_HOME_QUICK_ACTIONS",
        prompt_stub="stub://icon-nav/profile-setup",
        figma_node_id="PP/iOS/Home/QuickActions/ProfileSetup/Row/Default (TBD)",
    ),
    "ios.home.open_plate": CTASpec(
        cta_id="ios.home.open_plate",
        platform="iOS",
        screen="Home",
        ui_label="Open Plate",
        trigger_type="NavigationLink",
        status="Implemented",
        variant="V1",
        placement_zone="I_HOME_QUICK_ACTIONS",
        prompt_stub="stub://icon-nav/open-plate",
        figma_node_id="PP/iOS/Home/QuickActions/OpenPlate/Row/Default (TBD)",
    ),
    "ios.home.weekly_plan_reader": CTASpec(
        cta_id="ios.home.weekly_plan_reader",
        platform="iOS",
        screen="Home",
        ui_label="Weekly Plan Reader",
        trigger_type="NavigationLink",
        status="Blocked by flag",
        variant="V3",
        placement_zone="I_HOME_PRO_TOOLS",
        prompt_stub="stub://cta/pro-tool/weekly-plan",
        figma_node_id="PP/iOS/Home/ProTools/WeeklyPlanReader/Row/Flagged (TBD)",
    ),
    "ios.home.shopping_list_generator": CTASpec(
        cta_id="ios.home.shopping_list_generator",
        platform="iOS",
        screen="Home",
        ui_label="Shopping List Generator",
        trigger_type="NavigationLink",
        status="Blocked by flag",
        variant="V3",
        placement_zone="I_HOME_PRO_TOOLS",
        prompt_stub="stub://cta/pro-tool/shopping-list",
        figma_node_id="PP/iOS/Home/ProTools/ShoppingList/Row/Flagged (TBD)",
    ),
    # iOS Plate CTAs
    "ios.plate.add_meal": CTASpec(
        cta_id="ios.plate.add_meal",
        platform="iOS",
        screen="Plate",
        ui_label="Add Meal",
        trigger_type="button",
        status="Partial",
        variant="V1",
        placement_zone="I_PLATE_BOTTOMBAR_PRIMARY",
        prompt_stub="stub://cta/primary/add-meal",
        figma_node_id="PP/iOS/Plate/BottomBar/AddMeal/Button/Default (TBD)",
    ),
    "ios.plate.view_details": CTASpec(
        cta_id="ios.plate.view_details",
        platform="iOS",
        screen="Plate",
        ui_label="View Details",
        trigger_type="button",
        status="Partial",
        variant="V3",
        placement_zone="I_PLATE_BOTTOMBAR_PRIMARY",
        prompt_stub="stub://cta/secondary/view-details",
        figma_node_id="PP/iOS/Plate/BottomBar/ViewDetails/Button/Default (TBD)",
    ),
    "ios.plate.issue_action_dynamic": CTASpec(
        cta_id="ios.plate.issue_action_dynamic",
        platform="iOS",
        screen="Plate",
        ui_label="Retry / Open Profile / PRO Settings",
        trigger_type="button",
        status="Implemented",
        variant="V1",
        placement_zone="I_PLATE_ISSUE_RECOVERY",
        prompt_stub="stub://cta/error-state/dynamic-issue-action",
        figma_node_id="PP/iOS/Plate/IssueState/PrimaryAction/Button/Stateful (TBD)",
    ),
    # iOS Progress CTAs
    "ios.progress.refresh": CTASpec(
        cta_id="ios.progress.refresh",
        platform="iOS",
        screen="Progress",
        ui_label="Refresh",
        trigger_type="button",
        status="Implemented",
        variant="V1",
        placement_zone="I_PROGRESS_EMPTY_RECOVERY",
        prompt_stub="stub://cta/loading-state/refresh",
        figma_node_id="PP/iOS/Progress/EmptyState/Refresh/Button/Default (TBD)",
    ),
    "ios.progress.issue_action_dynamic": CTASpec(
        cta_id="ios.progress.issue_action_dynamic",
        platform="iOS",
        screen="Progress",
        ui_label="Retry / Open profile / Open PRO setup",
        trigger_type="button",
        status="Implemented",
        variant="V1",
        placement_zone="I_PROGRESS_ISSUE_RECOVERY",
        prompt_stub="stub://cta/error-state/dynamic-issue-action",
        figma_node_id="PP/iOS/Progress/IssueState/PrimaryAction/Button/Stateful (TBD)",
    ),
    # Web Home CTAs
    "web.home.open_setup": CTASpec(
        cta_id="web.home.open_setup",
        platform="Web",
        screen="Home",
        ui_label="Open setup",
        trigger_type="Link",
        status="Implemented",
        variant="V1",
        placement_zone="W_HOME_QA_GRID",
        prompt_stub="stub://cta/primary/setup",
        figma_node_id="PP/Web/Home/QuickActions/OpenSetup/Button/Default (TBD)",
    ),
    "web.home.open_plate": CTASpec(
        cta_id="web.home.open_plate",
        platform="Web",
        screen="Home",
        ui_label="Open plate",
        trigger_type="Link",
        status="Implemented",
        variant="V3",
        placement_zone="W_HOME_QA_GRID",
        prompt_stub="stub://cta/secondary/open-plate",
        figma_node_id="PP/Web/Home/QuickActions/OpenPlate/Button/Default (TBD)",
    ),
    "web.home.open_progress": CTASpec(
        cta_id="web.home.open_progress",
        platform="Web",
        screen="Home",
        ui_label="Open progress",
        trigger_type="Link",
        status="Implemented",
        variant="V3",
        placement_zone="W_HOME_QA_GRID",
        prompt_stub="stub://cta/secondary/open-progress",
        figma_node_id="PP/Web/Home/QuickActions/OpenProgress/Button/Default (TBD)",
    ),
    "web.home.open_pro": CTASpec(
        cta_id="web.home.open_pro",
        platform="Web",
        screen="Home",
        ui_label="Open Pro",
        trigger_type="Link",
        status="Implemented",
        variant="V2",
        placement_zone="W_HOME_QA_GRID",
        prompt_stub="stub://cta/secondary/open-pro",
        figma_node_id="PP/Web/Home/QuickActions/OpenPro/Button/Default (TBD)",
    ),
    # Web Plate CTAs
    "web.plate.open_setup": CTASpec(
        cta_id="web.plate.open_setup",
        platform="Web",
        screen="Plate",
        ui_label="Open setup",
        trigger_type="Link",
        status="Implemented",
        variant="V1",
        placement_zone="W_PLATE_GATE_ACTIONS",
        prompt_stub="stub://cta/primary/pro-open-setup",
        figma_node_id="PP/Web/Plate/ProControls/OpenSetup/Button/Default (TBD)",
    ),
    "web.plate.open_progress": CTASpec(
        cta_id="web.plate.open_progress",
        platform="Web",
        screen="Plate",
        ui_label="Open progress",
        trigger_type="Link",
        status="Implemented",
        variant="V3",
        placement_zone="W_PLATE_GATE_ACTIONS",
        prompt_stub="stub://cta/secondary/pro-open-progress",
        figma_node_id="PP/Web/Plate/ProControls/OpenProgress/Button/Default (TBD)",
    ),
    "web.plate.premium_gate_cta": CTASpec(
        cta_id="web.plate.premium_gate_cta",
        platform="Web",
        screen="Plate",
        ui_label="Unlock Premium",
        trigger_type="button",
        status="Implemented",
        variant="V2",
        placement_zone="W_PLATE_GATE_ACTIONS",
        prompt_stub="stub://cta/paywall-unlock",
        figma_node_id="PP/Web/Plate/PremiumGate/UnlockCTA/Button/Default (TBD)",
    ),
    # Web Progress CTAs
    "web.progress.export_pdf": CTASpec(
        cta_id="web.progress.export_pdf",
        platform="Web",
        screen="Progress",
        ui_label="Export PDF",
        trigger_type="button",
        status="Implemented",
        variant="V3",
        placement_zone="W_PROGRESS_HEADER_UTIL",
        prompt_stub="stub://cta/utility/export-pdf",
        figma_node_id="PP/Web/Progress/Header/ExportPDF/Button/Default (TBD)",
    ),
}


def get_ctas_for_screen(screen_id: str) -> list[CTASpec]:
    """Get all CTAs for a given screen ID."""
    prefix = screen_id + "."
    return [cta for cta_id, cta in CTA_REGISTRY.items() if cta_id.startswith(prefix)]


def build_layout_sections(
    screen_id: str,
    content_model: ScreenContentModel,
    component_tree: list[ComponentNodeSpec],
) -> list[LayoutSectionSpec]:
    """Materialize layout sections for the instruction payload."""
    template_payload = build_reusable_layout_template(
        content_model["layout_template_key"],
        screen_id,
    )
    layout_sections = template_payload["layout_sections"]
    component_ids_by_section: dict[str, list[str]] = {}
    for node in component_tree:
        component_ids_by_section.setdefault(node.section_id, []).append(node.component_id)
    return [
        LayoutSectionSpec(
            section_id=section["id"],
            name=section["name"],
            role=section["role"],
            component_ids=component_ids_by_section.get(section["id"], []),
        )
        for section in layout_sections
    ]


def build_component_tree(
    screen_id: str,
    content_model: ScreenContentModel,
    ctas: list[CTASpec],
) -> list[ComponentNodeSpec]:
    """Build a flat component tree with parent links and CTA nodes."""
    template_payload = build_reusable_layout_template(
        content_model["layout_template_key"],
        screen_id,
    )
    component_tree = [
        ComponentNodeSpec(
            component_id=node["id"],
            canonical_component=node["canonical_component"],
            section_id=node["section_id"],
            parent_component_id=node["parent_id"],
            hierarchy_level=node["hierarchy_level"],
            semantic_role=node["semantic_role"],
            source_ref=node["source_ref"],
        )
        for node in template_payload["static_component_tree"]
    ]

    parent_levels = {node.component_id: node.hierarchy_level for node in component_tree}
    cta_parent_id = content_model["cta_parent_id"]
    cta_base_level = parent_levels.get(cta_parent_id, 0) + 1

    for cta in ctas:
        status_text = cta.status.lower()
        semantic_role = "primary_cta" if cta.variant == "V1" else "secondary_cta"
        if "blocked" in status_text or "flag" in status_text:
            semantic_role = "flagged_cta"
        elif "issue" in cta.cta_id or "RECOVERY" in cta.placement_zone:
            semantic_role = "recovery_cta"
        elif "export" in cta.cta_id:
            semantic_role = "utility_cta"

        component_tree.append(
            ComponentNodeSpec(
                component_id=f"node:{cta.cta_id}",
                canonical_component="button",
                section_id=content_model["cta_section_id"],
                parent_component_id=cta_parent_id,
                hierarchy_level=cta_base_level,
                semantic_role=semantic_role,
                source_ref=f"cta:{cta.cta_id}",
            )
        )

    return component_tree


def generate_screen_instruction(screen_id: str) -> ScreenInstruction:
    """Generate instruction set for a screen."""
    parts = screen_id.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid screen_id format: {screen_id}")

    platform, screen = parts
    ctas = get_ctas_for_screen(screen_id)

    if not ctas:
        raise ValueError(f"No CTAs found for screen: {screen_id}")

    dimensions = SCREEN_DIMENSIONS.get(platform, SCREEN_DIMENSIONS["web"])
    page = PAGE_MAPPING.get(screen_id, "20_Web_Parity")
    background_token = "--pp-navy" if platform == "web" else "Color.navy"
    content_model = SCREEN_CONTENT_MODEL.get(screen_id)

    if content_model is None:
        raise ValueError(f"No content model found for screen: {screen_id}")

    component_tree = build_component_tree(screen_id, content_model, ctas)
    layout_sections = build_layout_sections(screen_id, content_model, component_tree)

    return ScreenInstruction(
        screen_id=screen_id,
        page=page,
        platform=PLATFORM_CANONICAL_NAMES.get(platform, platform.title()),
        surface=content_model["surface"],
        layout_archetype=content_model["layout_archetype"],
        layout_pattern=content_model["layout_pattern"],
        sections=layout_sections,
        component_hierarchy=component_tree,
        primary_components=content_model["primary_components"],
        supporting_components=content_model["supporting_components"],
        states=content_model["states"],
        dimensions=dimensions,
        background_token=background_token,
        token_constraints=content_model["token_constraints"],
        ctas=ctas,
        governance_checks=[
            "verify_token_usage",
            "verify_hpp_compliance",
            "verify_cta_registry_match",
            "verify_instruction_contract",
        ],
        context_version="code-first-ui-v1",
    )


def validate_instruction(instruction: ScreenInstruction) -> list[str]:
    """Validate instruction against governance rules."""
    errors = []

    # Check all CTAs have required fields
    for cta in instruction.ctas:
        if not cta.cta_id:
            errors.append(f"CTA missing cta_id: {cta}")
        if not cta.ui_label:
            errors.append(f"CTA {cta.cta_id} missing ui_label")
        if not cta.variant:
            errors.append(f"CTA {cta.cta_id} missing variant")

    # Check page mapping exists
    if not instruction.page:
        errors.append(f"No page mapping for screen: {instruction.screen_id}")

    # Check dimensions are valid
    if instruction.dimensions["width"] <= 0 or instruction.dimensions["height"] <= 0:
        errors.append("Invalid screen dimensions")

    instruction_dict = instruction_to_dict(instruction)
    errors.extend(validate_instruction_contract(instruction_dict))

    return errors


def build_sections_payload(instruction: ScreenInstruction) -> list[dict[str, Any]]:
    """Translate internal section specs into the external contract shape."""
    component_ids_by_section: dict[str, list[str]] = {}
    for node in instruction.component_hierarchy:
        component_ids_by_section.setdefault(node.section_id, []).append(node.component_id)

    return [
        {
            "section_id": section.section_id,
            "name": section.name,
            "role": section.role,
            "component_ids": component_ids_by_section.get(section.section_id, []),
        }
        for section in instruction.sections
    ]


def _frame_instruction_name(instruction: ScreenInstruction, node: ComponentNodeSpec) -> str:
    """Return a stable frame name for one component-hierarchy node."""
    if node.parent_component_id is None:
        platform_name = PLATFORM_CANONICAL_NAMES.get(
            instruction.platform.lower(), instruction.platform.title()
        )
        return f"{platform_name} {instruction.screen_id.split('.')[1].title()} Screen"
    return node.component_id


def _frame_instruction_payload(
    instruction: ScreenInstruction,
    node: ComponentNodeSpec,
    order: int,
) -> dict[str, Any]:
    """Serialize one non-button hierarchy node into a create_frame instruction."""
    payload: dict[str, Any] = {
        "type": "create_frame",
        "name": _frame_instruction_name(instruction, node),
        "canonical_component": node.canonical_component,
        "section_id": node.section_id,
        "component_id": node.component_id,
        "parent_component_id": node.parent_component_id,
        "hierarchy_level": node.hierarchy_level,
        "semantic_role": node.semantic_role,
        "order": order,
    }
    if node.parent_component_id is None:
        payload["dimensions"] = instruction.dimensions
        payload["background"] = instruction.background_token
    return payload


def _button_states_for_node(cta: CTASpec, node: ComponentNodeSpec) -> list[str]:
    """Return explicit button states for one CTA node."""
    states = [state for state in cta.states if not (cta.platform == "iOS" and state == "hover")]
    if node.semantic_role == "flagged_cta" and "feature-flagged" not in states:
        states.append("feature-flagged")
    return states


def _button_instruction_payload(
    cta: CTASpec,
    node: ComponentNodeSpec,
    order: int,
) -> dict[str, Any]:
    """Serialize one CTA-backed hierarchy node into a create_button instruction."""
    return {
        "type": "create_button",
        "name": cta.ui_label,
        "cta_key": cta.cta_id,
        "style": "primary" if cta.variant == "V1" else "secondary",
        "variant": cta.variant,
        "placement_zone": cta.placement_zone,
        "figma_node_id": cta.figma_node_id,
        "prompt_stub": cta.prompt_stub,
        "states": _button_states_for_node(cta, node),
        "canonical_component": "button",
        "section_id": node.section_id,
        "component_id": node.component_id,
        "parent_component_id": node.parent_component_id,
        "hierarchy_level": node.hierarchy_level,
        "semantic_role": node.semantic_role,
        "order": order,
    }


def instruction_to_dict(instruction: ScreenInstruction) -> dict[str, Any]:
    """Convert instruction to JSON-serializable dict."""
    ctas_by_source_ref = {f"cta:{cta.cta_id}": cta for cta in instruction.ctas}

    instruction_payload: list[dict[str, Any]] = []
    for order, node in enumerate(instruction.component_hierarchy):
        if node.canonical_component == "button":
            cta = ctas_by_source_ref.get(node.source_ref)
            if cta is None:
                raise ValueError(
                    f"CTA node {node.component_id} references unknown CTA source {node.source_ref}"
                )
            instruction_payload.append(_button_instruction_payload(cta, node, order))
            continue

        instruction_payload.append(_frame_instruction_payload(instruction, node, order))

    return {
        "screen_id": instruction.screen_id,
        "page": instruction.page,
        "platform": instruction.platform,
        "surface": instruction.surface,
        "layout_archetype": instruction.layout_archetype,
        "layout_pattern": instruction.layout_pattern,
        "sections": build_sections_payload(instruction),
        "component_hierarchy": [
            {
                "component_id": node.component_id,
                "canonical_component": node.canonical_component,
                "section_id": node.section_id,
                "parent_component_id": node.parent_component_id,
                "hierarchy_level": node.hierarchy_level,
                "semantic_role": node.semantic_role,
                "source_ref": node.source_ref,
            }
            for node in instruction.component_hierarchy
        ],
        "primary_components": instruction.primary_components,
        "supporting_components": instruction.supporting_components,
        "states": instruction.states,
        "dimensions": instruction.dimensions,
        "background_token": instruction.background_token,
        "token_constraints": instruction.token_constraints,
        "governance_checks": instruction.governance_checks,
        "context_version": instruction.context_version,
        "instructions": instruction_payload,
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Figma instructions from design documentation"
    )
    parser.add_argument(
        "--screen",
        help="Screen ID (e.g., ios.home, web.plate)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path (relative to scripts/design/)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate instruction only, do not generate output",
    )
    parser.add_argument(
        "--list-screens",
        action="store_true",
        help="List available screen IDs",
    )

    args = parser.parse_args()

    if args.list_screens:
        screens = sorted(set(PAGE_MAPPING.keys()))
        print("Available screens:")
        for screen in screens:
            ctas = get_ctas_for_screen(screen)
            print(f"  {screen} ({len(ctas)} CTAs)")
        return 0

    if not args.screen:
        parser.error("--screen is required unless using --list-screens")

    try:
        instruction = generate_screen_instruction(args.screen)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    errors = validate_instruction(instruction)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Generated instruction for {args.screen}:")
    print(f"  Page: {instruction.page}")
    print(f"  Platform: {instruction.platform}")
    print(f"  Dimensions: {instruction.dimensions}")
    print(f"  CTAs: {len(instruction.ctas)}")
    for cta in instruction.ctas:
        print(f"    - {cta.cta_id}: {cta.ui_label} ({cta.status})")

    if args.validate:
        print("\nValidation passed!")
        return 0

    if args.output:
        output_path = PROJECT_ROOT / "scripts" / "design" / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)

        instruction_dict = instruction_to_dict(instruction)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(instruction_dict, f, indent=2)

        print(f"\nInstruction written to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
