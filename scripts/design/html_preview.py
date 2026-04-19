#!/usr/bin/env python3
"""
Deterministic HTML preview lane for pulseplate_canvas_v1.

This preview is derived from the canonical canvas artifact and remains
read-only, local-only, and internal to the design runtime.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any, TypedDict, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.design.contracts import validate_canvas_artifact_contract

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HTML_PREVIEW_VERSION = "pulseplate_html_preview_v1"


class HtmlPreviewArtifact(TypedDict):
    preview_version: str
    screen_id: str
    output_path: str
    section_count: int
    node_count: int
    render_op_count: int
    interaction_mode: str


def default_preview_output_path(screen_id: str) -> Path:
    return PROJECT_ROOT / "artifacts" / "design_previews" / f"{screen_id.replace('.', '_')}.html"


def _resolve_preview_paths(screen_id: str, output_path: Path | None) -> tuple[Path, str]:
    """Return absolute write path plus manifest-safe repo-relative metadata path."""

    project_root = PROJECT_ROOT.resolve()
    candidate_output_path = output_path or default_preview_output_path(screen_id)
    if not candidate_output_path.is_absolute():
        candidate_output_path = project_root / candidate_output_path

    resolved_output_path = candidate_output_path.resolve()
    try:
        manifest_output_path = resolved_output_path.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise ValueError(
            "HTML preview output must stay within the repo root for manifest-safe metadata"
        ) from exc

    return resolved_output_path, manifest_output_path


def _html_list_item(label: str, value: str) -> str:
    return (
        f'<li><span class="label">{html.escape(label)}</span>'
        f'<span class="value">{html.escape(value)}</span></li>'
    )


def render_html_preview(
    canvas_artifact: dict[str, Any],
    *,
    title: str | None = None,
) -> str:
    """Render a deterministic HTML preview from one validated canvas artifact."""

    interaction_contract = cast(dict[str, Any], canvas_artifact["interaction_contract"])
    sections = cast(list[dict[str, Any]], canvas_artifact["sections"])
    nodes = cast(list[dict[str, Any]], canvas_artifact["nodes"])
    render_ops = cast(list[dict[str, Any]], canvas_artifact["render_ops"])
    page_title = title or f"PulsePlate Preview - {canvas_artifact['screen_id']}"

    section_cards = "\n".join(
        (
            '<article class="section-card" '
            f"data-section-id=\"{html.escape(str(section['section_id']))}\">"
            f"<h3>{html.escape(str(section['name']))}</h3>"
            f"<p class=\"role\">{html.escape(str(section['role']))}</p>"
            '<ul class="component-list">'
            + "".join(
                f"<li>{html.escape(str(component_id))}</li>"
                for component_id in section.get("component_ids", [])
            )
            + "</ul></article>"
        )
        for section in sections
    )
    node_rows = "\n".join(
        (
            "<tr>"
            f"<td>{html.escape(str(node['component_id']))}</td>"
            f"<td>{html.escape(str(node['canonical_component']))}</td>"
            f"<td>{html.escape(str(node['section_id']))}</td>"
            f"<td>{html.escape(str(node.get('parent_component_id') or '-'))}</td>"
            f"<td>{html.escape(str(node['semantic_role']))}</td>"
            f"<td>{html.escape(str(node['hierarchy_level']))}</td>"
            "</tr>"
        )
        for node in nodes
    )
    render_op_rows = "\n".join(
        (
            "<tr>"
            f"<td>{html.escape(str(render_op['order']))}</td>"
            f"<td>{html.escape(str(render_op['instruction_type']))}</td>"
            f"<td>{html.escape(str(render_op['name']))}</td>"
            f"<td>{html.escape(str(render_op['component_id']))}</td>"
            f"<td>{html.escape(', '.join(render_op.get('states', [])) or '-')}</td>"
            "</tr>"
        )
        for render_op in render_ops
    )
    summary_items = "\n".join(
        [
            _html_list_item("Screen", str(canvas_artifact["screen_id"])),
            _html_list_item("Platform", str(canvas_artifact["platform"])),
            _html_list_item("Surface", str(canvas_artifact["surface"])),
            _html_list_item("Layout archetype", str(canvas_artifact["layout_archetype"])),
            _html_list_item("Layout pattern", str(canvas_artifact["layout_pattern"])),
            _html_list_item("Interaction mode", str(interaction_contract["interaction_mode"])),
            _html_list_item("Checkpoint policy", str(interaction_contract["checkpoint_policy"])),
            _html_list_item(
                "Adaptation scope",
                ", ".join(str(item) for item in interaction_contract["adaptation_scope"]),
            ),
            _html_list_item(
                "Modality hints",
                ", ".join(str(item) for item in interaction_contract["modality_hints"]),
            ),
            _html_list_item(
                "Explanation strategy",
                str(interaction_contract["explanation_strategy"]),
            ),
        ]
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(page_title)}</title>
    <style>
      :root {{
        color-scheme: light;
        --ink: #122033;
        --muted: #55657c;
        --line: #d7deea;
        --surface: #f6f8fb;
        --panel: #ffffff;
        --accent: #1d5fd0;
      }}
      body {{
        margin: 0;
        font-family: "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif;
        color: var(--ink);
        background: linear-gradient(180deg, #edf2fa 0%, #f7f9fc 100%);
      }}
      main {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 32px 24px 48px;
      }}
      .hero {{
        display: grid;
        gap: 20px;
        margin-bottom: 24px;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 20px 22px;
        box-shadow: 0 14px 40px rgba(18, 32, 51, 0.06);
      }}
      .summary-list {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px 20px;
        padding: 0;
        margin: 16px 0 0;
        list-style: none;
      }}
      .summary-list li {{
        display: grid;
        gap: 4px;
      }}
      .label {{
        color: var(--muted);
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      .value {{
        font-size: 15px;
        font-weight: 600;
      }}
      .section-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 16px;
      }}
      .section-card {{
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 16px;
      }}
      .section-card h3 {{
        margin: 0 0 6px;
      }}
      .role {{
        margin: 0 0 12px;
        color: var(--muted);
      }}
      .component-list {{
        margin: 0;
        padding-left: 18px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
      }}
      th, td {{
        border-bottom: 1px solid var(--line);
        padding: 10px 8px;
        text-align: left;
        vertical-align: top;
      }}
      th {{
        color: var(--muted);
        font-size: 12px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      .eyebrow {{
        color: var(--accent);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }}
    </style>
  </head>
  <body>
    <main data-preview-version="{HTML_PREVIEW_VERSION}" data-screen-id="{html.escape(str(canvas_artifact['screen_id']))}">
      <section class="hero panel">
        <div class="eyebrow">PulsePlate Internal Preview</div>
        <h1>{html.escape(str(canvas_artifact["screen_id"]))}</h1>
        <p>This read-only preview is derived from <code>{html.escape(str(canvas_artifact["canvas_version"]))}</code>.</p>
        <ul class="summary-list">
          {summary_items}
        </ul>
      </section>
      <section class="panel">
        <h2>Sections</h2>
        <div class="section-grid">
          {section_cards}
        </div>
      </section>
      <section class="panel">
        <h2>Component Hierarchy</h2>
        <table data-table="nodes">
          <thead>
            <tr>
              <th>Component ID</th>
              <th>Canonical component</th>
              <th>Section</th>
              <th>Parent</th>
              <th>Role</th>
              <th>Level</th>
            </tr>
          </thead>
          <tbody>
            {node_rows}
          </tbody>
        </table>
      </section>
      <section class="panel">
        <h2>Render Operations</h2>
        <table data-table="render-ops">
          <thead>
            <tr>
              <th>Order</th>
              <th>Instruction type</th>
              <th>Name</th>
              <th>Component ID</th>
              <th>States</th>
            </tr>
          </thead>
          <tbody>
            {render_op_rows}
          </tbody>
        </table>
      </section>
    </main>
  </body>
</html>
"""


def write_html_preview(
    screen_id: str,
    canvas_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> HtmlPreviewArtifact:
    """Write one deterministic HTML preview artifact to a local-only path."""

    resolved_output_path, manifest_output_path = _resolve_preview_paths(screen_id, output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    html_preview = render_html_preview(canvas_artifact)
    resolved_output_path.write_text(html_preview, encoding="utf-8")

    interaction_contract = cast(dict[str, Any], canvas_artifact["interaction_contract"])
    return {
        "preview_version": HTML_PREVIEW_VERSION,
        "screen_id": screen_id,
        "output_path": manifest_output_path,
        "section_count": len(cast(list[dict[str, Any]], canvas_artifact["sections"])),
        "node_count": len(cast(list[dict[str, Any]], canvas_artifact["nodes"])),
        "render_op_count": len(cast(list[dict[str, Any]], canvas_artifact["render_ops"])),
        "interaction_mode": str(interaction_contract["interaction_mode"]),
    }


def _load_instruction(screen_id: str) -> dict[str, Any]:
    instruction_path = (
        PROJECT_ROOT / "scripts" / "design" / "instructions" / f"{screen_id.replace('.', '_')}.json"
    )
    if not instruction_path.exists():
        raise FileNotFoundError(f"Instruction file not found: {instruction_path}")
    return cast(dict[str, Any], json.loads(instruction_path.read_text(encoding="utf-8")))


def _load_canvas_artifact_from_manifest(screen_id: str) -> dict[str, Any]:
    manifest_path = PROJECT_ROOT / "docs" / "design" / "figma-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    exports = manifest.get("exports", [])
    export = next(
        (
            entry
            for entry in exports
            if isinstance(entry, dict) and entry.get("screen_id") == screen_id
        ),
        None,
    )
    if export is None:
        raise FileNotFoundError(f"Manifest export not found for screen: {screen_id}")

    canvas_artifact = export.get("canvas_artifact")
    if not isinstance(canvas_artifact, dict):
        raise ValueError(f"Manifest export for {screen_id} does not contain canvas_artifact")
    return canvas_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic HTML preview")
    parser.add_argument("--screen", required=True, help="Screen ID (e.g. web.progress)")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output HTML path. Defaults to artifacts/design_previews/<screen>.html",
    )
    args = parser.parse_args()

    try:
        instruction = _load_instruction(args.screen)
        canvas_artifact = _load_canvas_artifact_from_manifest(args.screen)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    errors = validate_canvas_artifact_contract(canvas_artifact, instruction)
    if errors:
        print("Canvas validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    preview_artifact = write_html_preview(args.screen, canvas_artifact, args.output)
    print(f"HTML preview written: {preview_artifact['output_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
