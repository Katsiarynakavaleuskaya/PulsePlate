from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

WORKFLOW = REPO_ROOT / "docs/orchestration/DESIGN_AGENT_WORKFLOW.md"
DOC_TEMPLATE = REPO_ROOT / "docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md"
GITHUB_TEMPLATE = REPO_ROOT / ".github/PULL_REQUEST_TEMPLATE/design.md"
MAKEFILE = REPO_ROOT / "Makefile"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_design_agent_workflow_required_sections() -> None:
    text = _read(WORKFLOW)

    required = [
        "## 1. Start Gate",
        "## 2. Source Truth Inspection",
        "## 3. Scope Classification",
        "## 4. Evidence Requirements",
        "## 5. Design Automation Module Classification",
        "## 6. Authority Boundaries",
        "## 7. Premortem And Bug-Hunter",
        "## 8. Review Mapping",
        "## 9. Merge Readiness",
        ".venv/bin/python",
        "agent-coordinator",
        "Mapping is evidence after fix or decision; it is not the fix.",
        "Figma, Canva, Storybook, external references",
    ]

    for item in required:
        assert item in text


def test_design_pr_templates_have_required_governance_sections() -> None:
    for path in [DOC_TEMPLATE, GITHUB_TEMPLATE]:
        text = _read(path)
        for heading in [
            "## Summary",
            "## Goal",
            "## Business reason",
            "## Scope",
            "## Out of scope",
            "## Source of truth",
            "## Design automation module classification",
            "## Files changed",
            "## Tests / bounded checks",
            "## Security notes",
            "## Premortem",
            "## Bug-hunter pass",
            "## Deferred / Follow-ups",
            "## Discussion Thread Pass",
            "### Fixed in Commit Mapping",
            "## Merge Readiness",
            "## Rollback",
            "## DoD",
        ]:
            assert heading in text

        assert ".venv/bin/python" in text
        assert "DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python" in text
        assert "Mapping is evidence after fix or decision; mapping is not the fix." in text
        assert "generated token mirror edits" in text


def test_design_workflow_does_not_promote_external_design_truth() -> None:
    combined = "\n".join([_read(WORKFLOW), _read(DOC_TEMPLATE), _read(GITHUB_TEMPLATE)])

    forbidden_claims = [
        "Figma is source of truth",
        "Canva is source of truth",
        "Storybook is source of truth",
        "evidence packs are source of truth",
        "scorecards are source of truth",
        "DESIGN.md is canonical",
        "generated mirrors may be edited by hand",
        "claim that main is green",
    ]

    for claim in forbidden_claims:
        assert claim not in combined

    assert "Do not claim green main" in combined
    assert "Do not override the root `AGENTS.md` merge gate." in combined


def test_design_make_targets_honor_dev_python_policy() -> None:
    text = _read(MAKEFILE)

    assert (
        "$(DEV_PYTHON) scripts/design_guard.py --manifest docs/design/figma-manifest.json" in text
    )
    assert "python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json" not in text
