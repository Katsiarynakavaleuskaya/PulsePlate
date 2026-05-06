#!/usr/bin/env python3
"""Generate the PulsePlate DESIGN.md semantic wrapper."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Iterable, TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_MD_PATH = Path("docs/design/DESIGN.md")
VOCABULARY_PATH = Path("docs/design/ui_component_vocabulary.json")

WARNING = (
    "DESIGN.md is generated or drift-checked from repo token/component contracts. "
    "It is an agent-readable semantic wrapper, not a source of truth. If it "
    "conflicts with `/tokens`, generated mirrors, UI vocabulary, backend/OpenAPI "
    "contracts, or runtime code, repo truth wins."
)

AUTOMATION_MODULES = [
    (
        "Icon Asset Validator",
        "release/design asset guard module",
    ),
    (
        "Design Evidence Harvester",
        "Design Intelligence PR-3 screen evidence pack module",
    ),
    (
        "Button / Component Drift Inspector",
        "Design Intelligence PR-4 deterministic scorecard + Storybook/vocabulary parity module",
    ),
    (
        "Marketing Asset Pack Compiler",
        "late GTM compiler over approved design/copy truth",
    ),
    (
        "Launch Copy Compliance Linter",
        "marketing/release copy guard aligned with wellness/compliance rules",
    ),
]


def _load_components(repo_root: Path) -> list[dict[str, object]]:
    path = repo_root / VOCABULARY_PATH
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{VOCABULARY_PATH} must contain a JSON array")
    components: list[dict[str, object]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"{VOCABULARY_PATH} entries must be objects")
        component_id = item.get("id")
        canonical_name = item.get("canonical_name")
        if not isinstance(component_id, str) or not isinstance(canonical_name, str):
            raise ValueError("component vocabulary entries require string id and canonical_name")
        components.append(item)
    return sorted(components, key=lambda item: str(item["id"]))


def _component_table(components: Iterable[dict[str, object]]) -> str:
    rows = [
        "| Id | Canonical name | Status | Repo component |",
        "| --- | --- | --- | --- |",
    ]
    for item in components:
        repo_component = item.get("existing_repo_component") or "none"
        rows.append(
            "| {id} | {name} | {status} | `{repo}` |".format(
                id=item["id"],
                name=item["canonical_name"],
                status=item.get("missing_status", "unknown"),
                repo=repo_component,
            )
        )
    return "\n".join(rows)


def render_design_md(repo_root: Path = REPO_ROOT) -> str:
    components = _load_components(repo_root)
    component_ids = ", ".join(f"`{item['id']}`" for item in components)
    module_rows = "\n".join(
        f"- {name} -> {classification}" for name, classification in AUTOMATION_MODULES
    )

    content = f"""<!-- markdownlint-disable MD013 -->
# PulsePlate DESIGN.md

**Status:** Generated or drift-checked semantic wrapper
**Generator:** `scripts/design/generate_design_md.py`

> {WARNING}

## Source List

This file is generated from repo-owned contracts:

- `/tokens`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/ui_component_vocabulary.json`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`
- `docs/design/REFERENCE_MANIFEST_SCHEMA.md`
- `docs/design/REFERENCE_SCORECARD.md`

## Brand Intent

PulsePlate is a planning-first wellness and meal-planning product. Its design intent is premium-clean, calm, trust-safe, and practical for repeated planning work.

PulsePlate is not a medical diagnosis, treatment, therapy, crisis-support, emergency-care, or guaranteed-outcome product. Design copy and screen grammar must stay wellness-only and evidence-careful.

## Source Precedence

1. Repo code, docs, tests, backend contracts, OpenAPI contracts, and merge governance.
2. `/tokens` as the design-token authoring source.
3. Generated runtime mirrors derived from `/tokens`:
   - `frontend/src/styles/tokens.css`
   - `frontend/src/styles/tokens.ts`
   - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
4. UI vocabulary and component contracts:
   - `docs/design/UI_COMPONENT_VOCABULARY.md`
   - `docs/design/ui_component_vocabulary.json`
5. Implemented web and iOS clients as thin presentation layers over backend truth.
6. Storybook as review and documentation only.
7. Figma as design-intent and review evidence only.
8. External references as read-only benchmark inputs only.

DESIGN.md does not override any source above.

## Tokens

`/tokens` remains the token authoring source. Runtime mirrors are generated outputs and must not be edited manually.

Generated mirrors:

- `frontend/src/styles/tokens.css`
- `frontend/src/styles/tokens.ts`
- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`

Do not promote raw hex values from prompts, Figma, screenshots, external references, Storybook stories, or DESIGN.md into implementation. Token changes must go through `/tokens`, deterministic regeneration, and token parity gates.

## Components

Canonical component vocabulary comes from `docs/design/ui_component_vocabulary.json`. Agents must use existing ids and names; do not invent component vocabulary in prompts, DESIGN.md edits, external reference notes, or implementation briefs.

Canonical component ids:

{component_ids}

{_component_table(components)}

## Screen Grammar

Backend and OpenAPI contracts remain product and runtime truth. Web and iOS clients are thin presentation clients and cannot invent pricing, billing, entitlement, nutrition, medical, compliance, App Store, or backend-derived state.

Future implementation briefs must map screen structure to repo-owned routes, contracts, tokens, and component vocabulary before code changes begin.

## Accessibility

Design work must preserve:

- contrast and readable hierarchy,
- visible focus states,
- keyboard access,
- touch target comfort,
- non-color-only state communication,
- reduced-motion-safe behavior.

Motion must not carry required product meaning by itself.

## External Reference Policy

External references are read-only. They may provide derived metadata only after normalization into PulsePlate vocabulary.

Do not copy external screenshots, assets, brands, exact layouts, proprietary components, visual identity, or marketing copy. Future references require the manifest and scorecard controls before they can inform a brief:

- `docs/design/REFERENCE_MANIFEST_SCHEMA.md`
- `docs/design/REFERENCE_SCORECARD.md`

## Design Automation Modules

Design automation items are modules inside the existing PulsePlate Design Intelligence / Design Runtime system, not standalone plugins and not a separate source of truth.

{module_rows}

This PR records classification only. These modules are not implemented by DESIGN.md generation.

## Do / Don't

Do:

- use repo tokens, UI vocabulary, reviewed components, and backend contracts,
- cite evidence links when producing design briefs,
- keep Storybook in the review/documentation lane,
- keep Figma in the design-intent lane,
- keep external references read-only until a later manifest and scorecard approve normalized use.

Don't:

- create a second source of truth,
- manually edit generated token mirrors,
- move backend, OpenAPI, billing, auth, nutrition, compliance, or App Store truth into clients,
- copy external assets, brands, exact layouts, screenshots, proprietary components, or marketing copy,
- treat DESIGN.md as runtime, token, Figma, Storybook, or product authority.

## Evidence Links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`
- `docs/orchestration/DESIGN_INTELLIGENCE_PR0_PACKET_2026-05-05.md`
- `docs/design/PULSEPLATE_DESIGN_MD_BOOTSTRAP.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/ui_component_vocabulary.json`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/design/REFERENCE_MANIFEST_SCHEMA.md`
- `docs/design/REFERENCE_SCORECARD.md`
"""
    return content.rstrip() + "\n"


def check_design_md(repo_root: Path, stdout: TextIO, stderr: TextIO) -> int:
    expected = render_design_md(repo_root)
    path = repo_root / DESIGN_MD_PATH
    if not path.exists():
        print(
            f"ERROR: {DESIGN_MD_PATH} is missing. Run: python3 scripts/design/generate_design_md.py",
            file=stderr,
        )
        return 1
    actual = path.read_text(encoding="utf-8")
    if actual == expected:
        print(f"OK: {DESIGN_MD_PATH} is up to date.", file=stdout)
        return 0
    diff = difflib.unified_diff(
        actual.splitlines(),
        expected.splitlines(),
        fromfile=str(DESIGN_MD_PATH),
        tofile=f"{DESIGN_MD_PATH} (generated)",
        lineterm="",
    )
    print(f"ERROR: {DESIGN_MD_PATH} is out of date.", file=stderr)
    print("Run: python3 scripts/design/generate_design_md.py", file=stderr)
    print("\n".join(diff), file=stderr)
    return 1


def write_design_md(repo_root: Path, stdout: TextIO) -> int:
    path = repo_root / DESIGN_MD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_design_md(repo_root), encoding="utf-8")
    print(f"Wrote {DESIGN_MD_PATH}", file=stdout)
    return 0


def run(
    argv: list[str] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if docs/design/DESIGN.md differs from generated output.",
    )
    args = parser.parse_args(argv)
    if args.check:
        return check_design_md(repo_root, stdout, stderr)
    return write_design_md(repo_root, stdout)


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
