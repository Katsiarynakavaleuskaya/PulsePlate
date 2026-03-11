from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


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
            "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "simulated",
            "surface": instruction.get("surface"),
            "layout_archetype": instruction.get("layout_archetype"),
            "layout_pattern": instruction.get("layout_pattern"),
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
                    "tool": f"figma.{inst_type}",
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


_ADAPTER_REGISTRY: dict[str, DesignExecutionAdapter] = {
    "deterministic_stub": DeterministicStubExecutionAdapter(),
}


def available_adapter_names() -> tuple[str, ...]:
    """Return supported execution adapter names for CLI wiring."""

    return tuple(sorted(_ADAPTER_REGISTRY))


def resolve_execution_adapter(adapter_name: str) -> DesignExecutionAdapter:
    """Resolve one adapter by name and fail fast on unknown values."""

    try:
        return _ADAPTER_REGISTRY[adapter_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported execution adapter: {adapter_name}") from exc
