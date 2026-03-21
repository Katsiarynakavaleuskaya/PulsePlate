from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

from scripts.design.canvas_artifact import (
    CANVAS_ARTIFACT_VERSION,
    build_canvas_artifact,
    build_render_plan_from_canvas,
)

DETERMINISTIC_EXECUTED_AT = "2026-01-01T00:00:00Z"


class DesignExecutionAdapter(Protocol):
    """Stable seam for future design execution backends."""

    adapter_name: str
    adapter_mode: str

    def execute(self, instruction: dict[str, Any]) -> dict[str, Any]:
        """Execute one instruction payload and return manifest-safe results."""


@dataclass(frozen=True)
class DeterministicStubExecutionAdapter:
    """Deterministic local adapter used until live MCP execution is introduced."""

    adapter_name: str = "deterministic_stub"
    adapter_mode: str = "simulated"

    def execute(self, instruction: dict[str, Any]) -> dict[str, Any]:
        screen_id = instruction.get("screen_id", "unknown")
        instructions_list = instruction.get("instructions", [])
        sections = instruction.get("sections", [])

        results: dict[str, Any] = {
            "screen_id": screen_id,
            "executed_at": DETERMINISTIC_EXECUTED_AT,
            "status": "simulated",
            "surface": instruction.get("surface"),
            "layout_archetype": instruction.get("layout_archetype"),
            "layout_pattern": instruction.get("layout_pattern"),
            "interaction_contract": instruction.get("interaction_contract"),
            "section_count": len(sections) if isinstance(sections, list) else 0,
            "adapter_name": self.adapter_name,
            "adapter_mode": self.adapter_mode,
            "simulation_mode": "deterministic_contract_stub",
            "created_nodes": [],
            "mcp_calls": [],
        }

        for index, inst in enumerate(instructions_list):
            if not isinstance(inst, dict):
                continue

            inst_type = inst.get("type", "unknown")
            inst_name = inst.get("name", f"Node_{index}")
            results["mcp_calls"].append(
                {
                    "adapter": self.adapter_name,
                    "tool": f"design_runtime.{inst_type}",
                    "params": {"name": inst_name},
                    "status": "simulated",
                }
            )
            results["created_nodes"].append(
                {
                    "type": inst_type,
                    "name": inst_name,
                    "node_id": f"simulated:{screen_id}:{index}",
                    "status": "pending_real_execution",
                    "canonical_component": inst.get("canonical_component"),
                    "component_id": inst.get("component_id"),
                    "section_id": inst.get("section_id"),
                    "parent_component_id": inst.get("parent_component_id"),
                    "hierarchy_level": inst.get("hierarchy_level"),
                    "semantic_role": inst.get("semantic_role"),
                    "order": inst.get("order"),
                }
            )

        return results


@dataclass(frozen=True)
class CodeNativeCanvasExecutionAdapter:
    """Code-native design runtime adapter backed by the canonical canvas artifact."""

    adapter_name: str = "code_native_canvas"
    adapter_mode: str = "artifact_emit"

    def execute(self, instruction: dict[str, Any]) -> dict[str, Any]:
        screen_id = instruction.get("screen_id", "unknown")
        artifact = build_canvas_artifact(instruction)
        render_plan = build_render_plan_from_canvas(artifact)
        sections = artifact["sections"]
        nodes = artifact["nodes"]

        return {
            "screen_id": screen_id,
            "executed_at": DETERMINISTIC_EXECUTED_AT,
            "status": "simulated",
            "surface": instruction.get("surface"),
            "layout_archetype": instruction.get("layout_archetype"),
            "layout_pattern": instruction.get("layout_pattern"),
            "interaction_contract": artifact["interaction_contract"],
            "section_count": len(sections),
            "component_count": len(nodes),
            "adapter_name": self.adapter_name,
            "adapter_mode": self.adapter_mode,
            "simulation_mode": "code_native_canvas_artifact",
            "artifact_type": CANVAS_ARTIFACT_VERSION,
            "artifact_version": CANVAS_ARTIFACT_VERSION,
            "created_nodes": [
                {
                    "type": str(item.get("instruction_type", "render_component")),
                    "name": str(item.get("name", item.get("canonical_component", "component"))),
                    "node_id": f"canvas:{screen_id}:{index}",
                    "status": "planned",
                    "canonical_component": item.get("canonical_component"),
                    "component_id": item.get("component_id"),
                    "section_id": item.get("section_id"),
                    "parent_component_id": item.get("parent_component_id"),
                    "hierarchy_level": item.get("hierarchy_level"),
                    "semantic_role": item.get("semantic_role"),
                    "order": item.get("order"),
                }
                for index, item in enumerate(render_plan)
            ],
            "mcp_calls": [
                {
                    "adapter": self.adapter_name,
                    "tool": "code_native.emit_canvas_artifact",
                    "params": {
                        "screen_id": screen_id,
                        "section_count": len(sections),
                        "artifact_type": CANVAS_ARTIFACT_VERSION,
                    },
                    "status": "simulated",
                }
            ],
            "canvas_artifact": artifact,
            "render_plan": render_plan,
        }


_ADAPTER_REGISTRY = {
    "deterministic_stub": DeterministicStubExecutionAdapter(),
    "code_native_canvas": CodeNativeCanvasExecutionAdapter(),
}


def available_adapter_names() -> tuple[str, ...]:
    """Return supported execution adapter names for CLI wiring."""

    return tuple(sorted(_ADAPTER_REGISTRY))


def resolve_execution_adapter(adapter_name: str) -> DesignExecutionAdapter:
    """Resolve one adapter by name and fail fast on unknown values."""

    try:
        return cast(DesignExecutionAdapter, _ADAPTER_REGISTRY[adapter_name])
    except KeyError as exc:
        raise ValueError(f"Unsupported execution adapter: {adapter_name}") from exc
