"""Regression guards for CI workflow diff-routing contracts."""

from __future__ import annotations

from collections.abc import Iterator
import fnmatch
import json
from pathlib import Path
import re
from typing import cast

import pytest
import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from scripts.ci import ci_risk_profile

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIONLINT_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "actionlint.yml"
BUILD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "build.yml"
CD_TEST_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd-test.yml"
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CODECOV_UPLOAD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "codecov-upload.yml"
CODEQL_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "codeql.yml"
FRONTEND_CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "frontend-ci.yml"
GREENLIGHT_IOS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "greenlight-ios.yml"
IOS_APPSTORE_ASSETS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ios-appstore-assets.yml"
NIGHTLY_FULL_TESTS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "nightly-tests.yml"
NIGHTLY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "nightly.yml"
PR_AUTOMATION_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pr-automation.yml"
SECURITY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "security.yml"
TRIVY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "trivy.yml"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
RUNBOOK_PATH = REPO_ROOT / "RUNBOOK_AGENT.md"
ORCHESTRATION_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "orchestration" / "PR_ORCHESTRATION_CONTRACT_MATRIX.md"
)
CHECKOUT_NODE24_SHA = "".join(
    (
        "de0f",
        "ac2e",
        "4500",
        "dabe",
        "0009",
        "e672",
        "14ff",
        "5f54",
        "47ce",
        "83dd",
    )
)
SETUP_NODE_NODE24_SHA = "".join(
    (
        "53b8",
        "3947",
        "a5a9",
        "8c8d",
        "1131",
        "30e5",
        "6537",
        "7fae",
        "1a50",
        "d02f",
    )
)
PATHS_FILTER_NODE24_SHA = "".join(
    (
        "fbd0",
        "ab8f",
        "3e69",
        "293a",
        "f611",
        "ebae",
        "e636",
        "3fc2",
        "5e6d",
        "187d",
    )
)
DOWNLOAD_ARTIFACT_NODE24_SHA = "".join(
    (
        "3e5f",
        "45b2",
        "cfb9",
        "1720",
        "54b4",
        "087a",
        "40e8",
        "e0b5",
        "a546",
        "1e7c",
    )
)
GITHUB_SCRIPT_NODE24_SHA = "".join(
    (
        "3a28",
        "44b7",
        "e9c4",
        "22d3",
        "c10d",
        "287c",
        "8955",
        "73f7",
        "108d",
        "a1b3",
    )
)
CODECOV_ACTION_NODE24_SHA = "".join(
    (
        "57e3",
        "a136",
        "b779",
        "b570",
        "ffcd",
        "bf80",
        "b3bd",
        "c90e",
        "7fab",
        "3de2",
    )
)
DOCKER_SETUP_BUILDX_NODE24_SHA = "".join(
    (
        "d7f5",
        "e7f5",
        "09e4",
        "5cec",
        "5c76",
        "c4d5",
        "afdd",
        "7de9",
        "3d0b",
        "3df5",
    )
)
DOCKER_LOGIN_NODE24_SHA = "".join(
    (
        "6500",
        "06c6",
        "eb7d",
        "ba73",
        "a995",
        "cc03",
        "b0b2",
        "d7f5",
        "ca91",
        "5bee",
    )
)
DOCKER_METADATA_NODE24_SHA = "".join(
    (
        "80c7",
        "e94d",
        "d9b9",
        "319b",
        "d5eb",
        "7a0e",
        "0fe9",
        "291e",
        "23a2",
        "a2e9",
    )
)
TRIVY_ACTION_NODE24_CACHE_SHA = "".join(
    (
        "ed14",
        "2fd0",
        "673e",
        "97e2",
        "3eac",
        "5462",
        "0cfb",
        "913e",
        "5ce3",
        "6c25",
    )
)
TRIVY_RUNTIME_VERSION = "v0.72.0"
CODEQL_ACTION_V4_37_1_SHA = "".join(
    (
        "7188",
        "fc36",
        "3630",
        "916d",
        "eb70",
        "2c7f",
        "dcf4",
        "e481",
        "b751",
        "f97a",
    )
)
SETUP_GO_NODE24_SHA = "".join(
    (
        "4a36",
        "0112",
        "1dd0",
        "1d16",
        "26a1",
        "e23e",
        "3721",
        "1e32",
        "54c1",
        "c06c",
    )
)
UPLOAD_ARTIFACT_NODE24_SHA = "".join(
    (
        "043f",
        "b46d",
        "1a93",
        "c77a",
        "ae65",
        "6e7c",
        "1c64",
        "a875",
        "d1fc",
        "6a0a",
    )
)
SBOM_ACTION_NODE24_SHA = "".join(
    (
        "e22c",
        "3899",
        "0414",
        "9dbc",
        "22b5",
        "8101",
        "8060",
        "40fa",
        "8d37",
        "a610",
    )
)
PYTHON_TEST_JOB_NAMES = ("test-pr", "test-feature", "test-main")
OLD_CHECKOUT_NODE20_SHA = "".join(
    (
        "08eb",
        "a0b2",
        "7e82",
        "0071",
        "cde6",
        "df94",
        "9e0b",
        "eb9b",
        "a490",
        "6955",
    )
)
OLD_CHECKOUT_V6_NODE20_SHA = "".join(
    (
        "8e8c",
        "483d",
        "b84b",
        "4bee",
        "98b6",
        "0c05",
        "9352",
        "1ed3",
        "4d99",
        "90e8",
    )
)
OLD_DOWNLOAD_ARTIFACT_SHA = "".join(
    (
        "fa0a",
        "91b8",
        "5d4f",
        "404e",
        "444e",
        "00e0",
        "0597",
        "1372",
        "dc80",
        "1d16",
    )
)
OLD_GITHUB_SCRIPT_SHA = "".join(
    (
        "f28e",
        "40c7",
        "f34b",
        "de8b",
        "3046",
        "d885",
        "e986",
        "cb62",
        "90c5",
        "673b",
    )
)
OLD_CODECOV_ACTION_SHA = "".join(
    (
        "af09",
        "b5e3",
        "94c9",
        "3991",
        "b95a",
        "5e76",
        "46ae",
        "b90c",
        "1917",
        "f78f",
    )
)
OLD_DOCKER_SETUP_BUILDX_SHA = "".join(
    (
        "e468",
        "171a",
        "9de2",
        "16ec",
        "0895",
        "6ac3",
        "ada2",
        "f079",
        "1b6b",
        "d435",
    )
)
OLD_DOCKER_LOGIN_SHA = "".join(
    (
        "5e57",
        "cd11",
        "8135",
        "c172",
        "c367",
        "2efd",
        "75eb",
        "4636",
        "0885",
        "c0ef",
    )
)
OLD_DOCKER_METADATA_SHA = "".join(
    (
        "c1e5",
        "1972",
        "afc2",
        "121e",
        "065a",
        "ed6d",
        "45c6",
        "5596",
        "fe44",
        "5f3f",
    )
)
OLD_TRIVY_ACTION_SHA = "".join(
    (
        "57a9",
        "7c7e",
        "7821",
        "a577",
        "6ceb",
        "c9bb",
        "87c9",
        "84fa",
        "69cb",
        "a8f1",
    )
)
OLD_TRIVY_INTERNAL_CACHE_NODE20_SHA = "".join(
    (
        "0400",
        "d5f6",
        "44dc",
        "7451",
        "3175",
        "e3cd",
        "8d07",
        "132d",
        "d486",
        "0809",
    )
)
OLD_SETUP_GO_SHA = "".join(
    (
        "40f1",
        "582b",
        "2485",
        "089d",
        "de7a",
        "bd97",
        "c152",
        "9aa7",
        "68e1",
        "baff",
    )
)
OLD_UPLOAD_ARTIFACT_SHA = "".join(
    (
        "ea16",
        "5f8d",
        "65b6",
        "e75b",
        "5404",
        "49e9",
        "2b48",
        "86f4",
        "3607",
        "fa02",
    )
)
OLD_UPLOAD_ARTIFACT_V7_SHA = "".join(
    (
        "bbbc",
        "a2dd",
        "aa5d",
        "8fea",
        "a63e",
        "36b7",
        "6fda",
        "ad77",
        "386f",
        "024f",
    )
)
OLD_SBOM_ACTION_SHA = "".join(
    (
        "da16",
        "7eac",
        "915b",
        "4e86",
        "f08b",
        "264d",
        "bdbc",
        "867b",
        "61be",
        "6f0c",
    )
)
GITHUB_SCRIPT_V9_TAG_OBJECT_SHA = "".join(
    (
        "d746",
        "ffe3",
        "5508",
        "b191",
        "7358",
        "783b",
        "479e",
        "04fe",
        "bd2b",
        "8f71",
    )
)


def _extract_section(workflow_text: str, start_anchor: str, end_anchor: str) -> str:
    """Return a stable workflow slice with explicit anchor assertions."""

    assert start_anchor in workflow_text, f"Missing workflow anchor: {start_anchor}"
    section_tail = workflow_text.split(start_anchor, maxsplit=1)[1]
    assert end_anchor in section_tail, f"Missing workflow anchor after {start_anchor}: {end_anchor}"
    return section_tail.split(end_anchor, maxsplit=1)[0]


def _extract_job_section(workflow_text: str, job_anchor: str) -> str:
    """Return a top-level GitHub Actions job block bounded by the next job or EOF."""

    assert job_anchor in workflow_text, f"Missing workflow anchor: {job_anchor}"
    start_index = workflow_text.index(job_anchor)
    section_tail = workflow_text[start_index + len(job_anchor) :]
    next_job_match = re.search(r"\n  [A-Za-z0-9][A-Za-z0-9_-]*:\n", section_tail)
    end_index = (
        start_index + len(job_anchor) + next_job_match.start()
        if next_job_match
        else len(workflow_text)
    )
    return workflow_text[start_index:end_index]


def _load_ci_workflow() -> dict[str, object]:
    return _load_workflow(CI_WORKFLOW_PATH)


def _load_workflow(path: Path) -> dict[str, object]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def _active_workflow_paths() -> Iterator[Path]:
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    yield from sorted(workflow_dir.glob("*.yml"))
    yield from sorted(workflow_dir.glob("*.yaml"))


def _iter_job_steps(path: Path) -> Iterator[tuple[str, dict[str, object]]]:
    workflow = _load_workflow(path)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    for job_id, job in jobs.items():
        assert isinstance(job_id, str)
        assert isinstance(job, dict)
        steps = job.get("steps", [])
        assert isinstance(steps, list)
        for step in steps:
            assert isinstance(step, dict)
            yield job_id, step


def _assert_contains_all_tokens(expression: str, expected_tokens: tuple[str, ...]) -> None:
    """Assert that a workflow expression keeps all required routing tokens."""

    for token in expected_tokens:
        assert (
            token in expression
        ), f"Missing token {token!r} in expression excerpt: {expression[:500]!r}"


def _job_step_by_name(
    workflow: dict[str, object],
    *,
    job_id: str,
    step_name: str,
) -> dict[str, object]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[job_id]
    assert isinstance(job, dict)
    steps = job["steps"]
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"missing step {step_name!r} in {job_id!r}")


def _docker_environment_flags(run_script: str) -> set[str]:
    """Return normalized ``docker run -e`` arguments from a workflow script."""

    flags: set[str] = set()
    for line in run_script.splitlines():
        stripped = line.strip()
        if stripped.startswith("-e "):
            flags.add(stripped.removeprefix("-e ").removesuffix("\\").strip())
    return flags


def _contract_suite_targets_by_group(
    workflow: dict[str, object],
    *,
    job_id: str,
) -> dict[str, tuple[str, ...]]:
    step = _job_step_by_name(
        workflow,
        job_id=job_id,
        step_name="Contract and risk suites",
    )
    run_script = step["run"]
    assert isinstance(run_script, str)
    case_match = re.search(r'case "\$group" in(?P<body>.*?)(?=^\s+\*\))', run_script, re.S | re.M)
    assert case_match is not None, f"missing contract/risk case block in {job_id}"
    case_body = case_match.group("body") + "\n              *)"
    blocks: dict[str, tuple[str, ...]] = {}
    for match in re.finditer(
        r"^\s+(?P<group>[a-z_]+)\)\n(?P<body>.*?)(?=^\s+(?:[a-z_]+|\*)\))",
        case_body,
        re.S | re.M,
    ):
        group = match.group("group")
        targets = tuple(re.findall(r"\btests/[^\s\\]+", match.group("body")))
        assert targets, f"contract/risk group {group!r} in {job_id!r} has no test targets"
        blocks[group] = targets
    return blocks


def _nested_minimatch_10_paths(packages: object) -> set[str]:
    """Select only nested minimatch 10.x records, never the root package path."""

    assert isinstance(packages, dict), "frontend lockfile packages must be an object"
    nested_paths: set[str] = set()
    for raw_path, package_info in packages.items():
        package_path = str(raw_path)
        if package_path == "node_modules/minimatch" or not package_path.endswith(
            "node_modules/minimatch"
        ):
            continue
        assert isinstance(package_info, dict), f"{package_path}: package record must be an object"
        if str(package_info.get("version", "")).startswith("10."):
            nested_paths.add(package_path)
    return nested_paths


def test_nested_minimatch_10_selection_keeps_root_assertion_separate() -> None:
    """A future root minimatch 10.x must not reuse nested brace-expansion evidence."""

    packages = {
        "node_modules/minimatch": {"version": "10.9.9"},
        "node_modules/glob/node_modules/minimatch": {"version": "10.2.5"},
        "node_modules/legacy/node_modules/minimatch": {"version": "3.1.5"},
    }

    assert _nested_minimatch_10_paths(packages) == {"node_modules/glob/node_modules/minimatch"}


NODE24_FRONTEND_BUILD_LINE = (
    "FROM node:24.18.1-bookworm-slim@"
    "sha256:235600a8101ab264e117b1768e925532262668dc9b581ef1dd7d96ced463b8e7"
    " AS frontend-build"
)
NODE24_CADDY_BINARY_COPY_LINE = (
    "COPY --from=caddy-build --chmod=0755 /go/bin/caddy /usr/bin/caddy.pulseplate"
)
NODE24_FRONTEND_ASSET_RESET_LINE = 'RUN ["/bin/busybox", "rm", "-rf", "/srv/frontend"]'
NODE24_FRONTEND_ASSET_COPY_LINE = "COPY --from=frontend-build /app/dist /srv/frontend"
NODE24_FRONTEND_ASSET_WRITE_LINES = (
    NODE24_FRONTEND_ASSET_RESET_LINE,
    NODE24_FRONTEND_ASSET_COPY_LINE,
)
NODE24_FINAL_STAGE_COPY_ADD_LINES = (
    NODE24_CADDY_BINARY_COPY_LINE,
    NODE24_FRONTEND_ASSET_COPY_LINE,
)
NODE24_UNSUPPORTED_FROM_ERROR = "FROM stages must use the supported single-line form"
NODE24_SUPPORTED_FROM_RE = re.compile(
    r"\s*FROM(?:\s+--platform=[^\s\\`]+)?\s+[^\s\\`]+" r"(?:\s+AS\s+(?P<alias>[^\s\\`]+))?\s*",
    flags=re.IGNORECASE,
)
NODE24_CONTINUED_FROM_PREFIX_RE = re.compile(
    r"\s*(?:F|FR|FRO|FROM)[\\`]\s*",
    flags=re.IGNORECASE,
)


def _docker_logical_instructions(
    dockerfile_lines: list[str],
) -> tuple[list[tuple[int, int, str]], bool]:
    """Return bounded Docker logical instructions and an incomplete-tail flag."""

    escape_character = "\\"
    for line in dockerfile_lines:
        stripped = line.strip()
        if not stripped:
            break
        directive_match = re.fullmatch(
            r"#\s*(syntax|escape|check)\s*=\s*(\S.*)", stripped, re.IGNORECASE
        )
        if directive_match is None:
            break
        if directive_match.group(1).lower() == "escape":
            escape_value = directive_match.group(2).strip()
            if escape_value in {"\\", "`"}:
                escape_character = escape_value

    instructions: list[tuple[int, int, str]] = []
    current_parts: list[str] = []
    current_start: int | None = None
    for line_index, line in enumerate(dockerfile_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if current_start is None:
            current_start = line_index
        physical_part = line.rstrip()
        continued = physical_part.endswith(escape_character)
        if continued:
            physical_part = physical_part[: -len(escape_character)]
        current_parts.append(physical_part.strip())
        if continued:
            continue
        instructions.append((current_start, line_index, " ".join(current_parts)))
        current_parts = []
        current_start = None
    return instructions, current_start is not None


def _node24_frontend_builder_contract_errors(dockerfile: str) -> list[str]:
    """Return finite carrier errors for the known Caddy SPA Dockerfile."""

    dockerfile_lines = dockerfile.splitlines()
    from_candidate_lines = [
        line for line in dockerfile_lines if re.match(r"\s*FROM(?:\s|$)", line, flags=re.IGNORECASE)
    ]
    unsupported_from_lines = [
        line for line in from_candidate_lines if NODE24_SUPPORTED_FROM_RE.fullmatch(line) is None
    ]
    has_utf8_bom = dockerfile.startswith("\ufeff")
    has_continued_from_keyword = any(
        NODE24_CONTINUED_FROM_PREFIX_RE.fullmatch(line) is not None for line in dockerfile_lines
    )
    frontend_build_owner_lines = [
        line
        for line in dockerfile_lines
        if re.fullmatch(
            r"\s*FROM(?:\s+--platform=[^\s\\`]+)?\s+[^\s\\`]+" r"\s+AS\s+frontend-build\s*",
            line,
            flags=re.IGNORECASE,
        )
    ]
    node_from_stage_lines = [
        line
        for line in dockerfile_lines
        if re.fullmatch(
            r"\s*FROM(?:\s+--platform=[^\s\\`]+)?\s+node:[^\s\\`]+" r"(?:\s+AS\s+[^\s\\`]+)?\s*",
            line,
            flags=re.IGNORECASE,
        )
    ]
    from_stage_aliases: list[str | None] = []
    from_stage_indices: list[int] = []
    for line_index, line in enumerate(dockerfile_lines):
        stage_match = NODE24_SUPPORTED_FROM_RE.fullmatch(line)
        if stage_match is None:
            continue
        alias = stage_match.group("alias")
        from_stage_aliases.append(alias.lower() if alias else None)
        from_stage_indices.append(line_index)
    frontend_asset_write_lines = [
        line
        for line in dockerfile_lines
        if "/srv/frontend" in line and not line.lstrip().startswith("#")
    ]
    frontend_asset_write_indices = [
        line_index
        for line_index, line in enumerate(dockerfile_lines)
        if "/srv/frontend" in line and not line.lstrip().startswith("#")
    ]
    final_stage_start_index = (
        from_stage_indices[-1] if from_stage_indices else len(dockerfile_lines)
    )
    logical_instructions, has_incomplete_logical_instruction = _docker_logical_instructions(
        dockerfile_lines
    )
    final_stage_logical_instructions = [
        instruction
        for start_index, _end_index, instruction in logical_instructions
        if start_index > final_stage_start_index
    ]
    final_stage_copy_add_lines = [
        line
        for line_index, line in enumerate(dockerfile_lines)
        if line_index > final_stage_start_index
        and re.match(r"\s*(?:COPY|ADD)(?:\s|$)", line, flags=re.IGNORECASE)
    ]

    errors: list[str] = []
    if has_utf8_bom or unsupported_from_lines or has_continued_from_keyword:
        errors.append(NODE24_UNSUPPORTED_FROM_ERROR)
    if has_incomplete_logical_instruction:
        errors.append("Dockerfile logical instructions must be complete")
    if frontend_build_owner_lines != [NODE24_FRONTEND_BUILD_LINE]:
        errors.append("frontend-build must have exactly one immutable Node owner")
    if node_from_stage_lines != [NODE24_FRONTEND_BUILD_LINE]:
        errors.append("the immutable frontend-build line must be the only Node FROM stage")
    if from_stage_aliases != ["caddy-build", "frontend-build", None]:
        errors.append("Dockerfile stage aliases must stay finite and ordered")
    if final_stage_copy_add_lines != list(NODE24_FINAL_STAGE_COPY_ADD_LINES):
        errors.append("final-stage COPY/ADD instructions must stay finite and ordered")
    if frontend_asset_write_lines != list(NODE24_FRONTEND_ASSET_WRITE_LINES):
        errors.append("production frontend assets must come only from frontend-build")
    elif not from_stage_indices or frontend_asset_write_indices[0] <= from_stage_indices[-1]:
        errors.append("production frontend asset handoff must belong to the final stage")
    elif has_utf8_bom or unsupported_from_lines or has_continued_from_keyword:
        pass
    elif NODE24_FRONTEND_ASSET_RESET_LINE not in final_stage_logical_instructions:
        errors.append("production frontend asset reset must be an independent logical instruction")
    elif NODE24_FRONTEND_ASSET_COPY_LINE not in final_stage_logical_instructions:
        errors.append(
            "production frontend asset handoff must be an independent logical instruction"
        )
    elif final_stage_logical_instructions[-1] != NODE24_FRONTEND_ASSET_COPY_LINE:
        errors.append("production frontend asset handoff must be the final executable instruction")
    elif final_stage_logical_instructions[-2:] != list(NODE24_FRONTEND_ASSET_WRITE_LINES):
        errors.append("production frontend asset reset must immediately precede the handoff")
    return errors


def test_node24_runtime_baseline_surfaces_stay_coherent() -> None:
    """Guard the repo Node baseline across local, frontend, Docker, and devcontainer surfaces."""

    nvmrc = (REPO_ROOT / ".nvmrc").read_text(encoding="utf-8").strip()
    frontend_package = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    frontend_lock = json.loads(
        (REPO_ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8")
    )
    devcontainer = json.loads(
        (REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
    )
    public_readme = (REPO_ROOT / "README_V2_PUBLIC_DRAFT.md").read_text(encoding="utf-8")
    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")

    assert nvmrc == "24.18.1"
    assert "- Node `24.18.1` for the web client" in public_readme
    assert "`nvm use` reads the repo-root `.nvmrc` and selects Node `24.18.1`." in public_readme
    assert "24.16.0" not in public_readme
    assert frontend_package["engines"]["node"] == ">=24.0.0 <25.0.0"
    assert frontend_lock["packages"][""]["engines"]["node"] == ">=24.0.0 <25.0.0"
    assert frontend_package["overrides"]["minimatch@10"]["brace-expansion"] == "5.0.8"
    assert frontend_package["overrides"]["ws"] == "8.21.0"
    packages = frontend_lock["packages"]
    minimatch_10_paths = _nested_minimatch_10_paths(packages)
    assert minimatch_10_paths, "frontend lockfile must retain a minimatch 10.x subtree"
    for minimatch_path in minimatch_10_paths:
        brace_path = minimatch_path.removesuffix("node_modules/minimatch") + (
            "node_modules/brace-expansion"
        )
        assert packages[brace_path]["version"] == "5.0.8"
    assert packages["node_modules/brace-expansion"]["version"] == "2.1.3"
    assert frontend_lock["packages"]["node_modules/ws"]["version"] == "8.21.0"
    assert devcontainer["features"]["ghcr.io/devcontainers/features/node:1"]["version"] == "24"
    contract_errors = _node24_frontend_builder_contract_errors(dockerfile)
    assert contract_errors == [], "\n".join(contract_errors)
    assert "node:22.22.1" not in dockerfile


def test_node24_frontend_builder_guard_rejects_missing_asset_handoff() -> None:
    """The immutable builder must remain the production SPA asset owner."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    assert dockerfile.count(NODE24_FRONTEND_ASSET_COPY_LINE) == 1
    disconnected = dockerfile.replace(NODE24_FRONTEND_ASSET_COPY_LINE, "", 1)

    errors = _node24_frontend_builder_contract_errors(disconnected)

    assert "production frontend assets must come only from frontend-build" in errors


def test_node24_frontend_builder_guard_rejects_alternate_asset_owner() -> None:
    """A decorative pinned stage cannot mask an alternate mutable builder."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    alternate_stage = "\n".join(
        (
            NODE24_FRONTEND_BUILD_LINE,
            "ARG ALT_NODE_IMAGE=node:25-alpine",
            "FROM ${ALT_NODE_IMAGE} AS alternate-frontend-build",
        )
    )
    redirected = dockerfile.replace(
        NODE24_FRONTEND_BUILD_LINE,
        alternate_stage,
        1,
    ).replace(
        NODE24_FRONTEND_ASSET_COPY_LINE,
        "COPY --from=alternate-frontend-build /app/dist /srv/frontend",
        1,
    )

    errors = _node24_frontend_builder_contract_errors(redirected)

    assert "Dockerfile stage aliases must stay finite and ordered" in errors
    assert "production frontend assets must come only from frontend-build" in errors


def test_node24_frontend_builder_guard_rejects_continued_node_stage() -> None:
    """A continued Node stage cannot escape the finite FROM inventory."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    continued_stage = "\n".join(
        (
            dockerfile,
            "FROM node:25-bookworm-slim \\",
            " AS tooling",
        )
    )

    errors = _node24_frontend_builder_contract_errors(continued_stage)

    assert NODE24_UNSUPPORTED_FROM_ERROR in errors


def test_node24_frontend_builder_guard_rejects_continued_canonical_owner() -> None:
    """The canonical builder owner must use the supported single-line form."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    continued_owner = NODE24_FRONTEND_BUILD_LINE.replace(
        " AS frontend-build",
        " \\\n AS frontend-build",
        1,
    )
    continued = dockerfile.replace(NODE24_FRONTEND_BUILD_LINE, continued_owner, 1)

    errors = _node24_frontend_builder_contract_errors(continued)

    assert NODE24_UNSUPPORTED_FROM_ERROR in errors


def test_node24_frontend_builder_guard_rejects_backtick_continued_stage() -> None:
    """Docker's alternate escape directive cannot hide a continued FROM stage."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    runtime_stage = next(line for line in dockerfile.splitlines() if line.startswith("FROM caddy:"))
    continued = dockerfile.replace(
        "# syntax=docker/dockerfile:1",
        "# syntax=docker/dockerfile:1\n# escape=`",
        1,
    ).replace(
        runtime_stage,
        f"{runtime_stage}`\n AS final-runtime",
        1,
    )

    errors = _node24_frontend_builder_contract_errors(continued)

    assert NODE24_UNSUPPORTED_FROM_ERROR in errors


def test_node24_frontend_builder_guard_rejects_split_from_keyword() -> None:
    """A continued keyword cannot hide a logical FROM instruction."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    for escape_character in ("\\", "`"):
        candidate = dockerfile
        if escape_character == "`":
            candidate = candidate.replace(
                "# syntax=docker/dockerfile:1",
                "# syntax=docker/dockerfile:1\n# escape=`",
                1,
            )
        for continuation_count in (1, 2):
            for split_index in range(1, len("FROM") + 1):
                continuation = f"{escape_character}\n" * continuation_count
                continued_keyword = f"{'FROM'[:split_index]}{continuation}{'FROM'[split_index:]}"
                hidden_stage = (
                    f"{candidate}\n{continued_keyword} node:25-bookworm-slim AS hidden-tooling"
                )

                errors = _node24_frontend_builder_contract_errors(hidden_stage)

                assert errors == [NODE24_UNSUPPORTED_FROM_ERROR], (
                    escape_character,
                    continuation_count,
                    split_index,
                    errors,
                )


def test_node24_frontend_builder_guard_rejects_commented_from_bridge() -> None:
    """A Docker comment cannot hide a continued FROM keyword prefix."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    for escape_character in ("\\", "`"):
        candidate = dockerfile
        if escape_character == "`":
            candidate = candidate.replace(
                "# syntax=docker/dockerfile:1",
                "# syntax=docker/dockerfile:1\n# escape=`",
                1,
            )
        for comment_indent in ("", "  "):
            hidden_stage = "\n".join(
                (
                    candidate,
                    f"FR{escape_character}",
                    f"{comment_indent}# ignored during Docker continuation",
                    "OM node:25-bookworm-slim AS hidden-tooling",
                )
            )

            errors = _node24_frontend_builder_contract_errors(hidden_stage)

            assert errors == [NODE24_UNSUPPORTED_FROM_ERROR], (
                escape_character,
                comment_indent,
                errors,
            )


def test_node24_frontend_builder_guard_rejects_crlf_split_from_keyword() -> None:
    """CRLF line endings cannot hide a continued FROM keyword prefix."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    for escape_character in ("\\", "`"):
        candidate = dockerfile
        if escape_character == "`":
            candidate = candidate.replace(
                "# syntax=docker/dockerfile:1",
                "# syntax=docker/dockerfile:1\n# escape=`",
                1,
            )
        hidden_stage = "\n".join(
            (
                candidate,
                f"FR{escape_character}",
                "OM node:25-bookworm-slim AS hidden-tooling",
            )
        ).replace("\n", "\r\n")

        errors = _node24_frontend_builder_contract_errors(hidden_stage)

        assert errors == [NODE24_UNSUPPORTED_FROM_ERROR], (escape_character, errors)


def test_node24_frontend_builder_guard_rejects_utf8_bom() -> None:
    """Docker's stripped UTF-8 BOM cannot hide an initial FROM instruction."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    bom_prefixed = "\ufeffFROM node:25-bookworm-slim AS hidden-tooling\n" + dockerfile

    errors = _node24_frontend_builder_contract_errors(bom_prefixed)

    assert errors == [NODE24_UNSUPPORTED_FROM_ERROR]


def test_node24_frontend_builder_guard_ignores_non_from_tokens() -> None:
    """Comments and longer identifiers are not Docker FROM instructions."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    non_instructions = dockerfile.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        "\n".join(
            (
                "# FROM node:25-bookworm-slim AS commented-tooling",
                "FROMAGE node:25-bookworm-slim AS identifier-tooling",
                NODE24_FRONTEND_ASSET_RESET_LINE,
            )
        ),
        1,
    )

    assert _node24_frontend_builder_contract_errors(non_instructions) == []


def test_node24_frontend_builder_guard_rejects_asset_overwrite() -> None:
    """A later copy cannot replace a served asset from another stage."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    overwritten = "\n".join(
        (
            dockerfile,
            "COPY --from=caddy-build /usr/bin/caddy /srv/frontend/index.html",
        )
    )

    errors = _node24_frontend_builder_contract_errors(overwritten)

    assert "production frontend assets must come only from frontend-build" in errors


def test_node24_frontend_builder_guard_rejects_post_handoff_run() -> None:
    """No continued RUN may replace an asset after the immutable handoff."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    overwritten = "\n".join(
        (
            dockerfile,
            "RUN printf '<html>alternate</html>' > /srv/front\\",
            "end/index.html",
        )
    )

    errors = _node24_frontend_builder_contract_errors(overwritten)

    assert "production frontend asset handoff must be the final executable instruction" in errors


@pytest.mark.parametrize(
    ("replacement", "expected_error"),
    (
        ("", "production frontend assets must come only from frontend-build"),
        (
            f"{NODE24_FRONTEND_ASSET_RESET_LINE}\nRUN true",
            "production frontend asset reset must immediately precede the handoff",
        ),
    ),
)
def test_node24_frontend_builder_guard_requires_adjacent_asset_reset(
    replacement: str,
    expected_error: str,
) -> None:
    """The final handoff must immediately follow its structural destination reset."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    mutated = dockerfile.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        replacement,
        1,
    )

    errors = _node24_frontend_builder_contract_errors(mutated)

    assert expected_error in errors


def test_node24_frontend_builder_guard_rejects_absorbed_asset_reset() -> None:
    """A prior continuation cannot absorb and short-circuit the reset instruction."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    absorbed = dockerfile.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        "\n".join(
            (
                "WORKDIR /srv",
                "RUN mkdir -p frontend && printf 'seeded' > frontend/extra.js && true || \\",
                NODE24_FRONTEND_ASSET_RESET_LINE,
            )
        ),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(absorbed)

    assert "production frontend asset reset must be an independent logical instruction" in errors


def test_node24_frontend_builder_guard_ignores_late_escape_directive() -> None:
    """An escape comment after the header cannot change Docker continuation rules."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    late_escape = dockerfile.replace(
        "# Multi-stage image: pinned Caddy build + Vite build → hardened Caddy SPA shell.",
        "\n".join(
            (
                "# Multi-stage image: pinned Caddy build + Vite build → hardened Caddy SPA shell.",
                "# escape=`",
            )
        ),
        1,
    )
    absorbed = late_escape.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        "\n".join(
            (
                "WORKDIR /srv",
                "RUN mkdir -p frontend && printf 'seeded' > frontend/extra.js && true || \\",
                NODE24_FRONTEND_ASSET_RESET_LINE,
            )
        ),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(absorbed)

    assert "production frontend asset reset must be an independent logical instruction" in errors


def test_node24_frontend_builder_reset_clears_pre_handoff_seed() -> None:
    """A relative pre-seed remains harmless because the adjacent reset follows it."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    seeded = dockerfile.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        "\n".join(
            (
                "WORKDIR /srv",
                "RUN mkdir -p frontend && printf 'alternate' > front\\",
                "end/extra.js",
                NODE24_FRONTEND_ASSET_RESET_LINE,
            )
        ),
        1,
    )

    assert _node24_frontend_builder_contract_errors(seeded) == []


@pytest.mark.parametrize(
    "asset_write",
    (
        "COPY custom-index.html frontend/index.html",
        "ADD custom-index.html frontend/index.html",
    ),
)
def test_node24_frontend_builder_guard_rejects_relative_asset_overwrite(
    asset_write: str,
) -> None:
    """A final-stage relative COPY or ADD cannot overwrite the served SPA."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    overwritten = dockerfile.replace(
        NODE24_FRONTEND_ASSET_COPY_LINE,
        "\n".join((NODE24_FRONTEND_ASSET_COPY_LINE, "WORKDIR /srv", asset_write)),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(overwritten)

    assert "final-stage COPY/ADD instructions must stay finite and ordered" in errors


def test_node24_frontend_builder_guard_rejects_pre_final_handoff() -> None:
    """The canonical handoff must populate the final production stage."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    dockerfile_lines = dockerfile.splitlines()
    reset_index = dockerfile_lines.index(NODE24_FRONTEND_ASSET_RESET_LINE)
    handoff_lines = dockerfile_lines[reset_index : reset_index + 2]
    del dockerfile_lines[reset_index : reset_index + 2]
    final_stage_index = max(
        index
        for index, line in enumerate(dockerfile_lines)
        if re.match(r"\s*FROM\s+", line, flags=re.IGNORECASE)
    )
    dockerfile_lines[final_stage_index:final_stage_index] = handoff_lines
    relocated = "\n".join(dockerfile_lines)

    errors = _node24_frontend_builder_contract_errors(relocated)

    assert "production frontend asset handoff must belong to the final stage" in errors


def _github_workflow_glob_matches(value: str, pattern: str) -> bool:
    """Match the bounded GitHub ``*``/``**`` forms without crossing slashes."""

    assert not any(token in pattern for token in ("?", "[", "]", "\\"))
    regex_parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            regex_parts.append(".*")
            index += 2
            continue
        character = pattern[index]
        regex_parts.append("[^/]*" if character == "*" else re.escape(character))
        index += 1
    return re.fullmatch("".join(regex_parts), value) is not None


def _workflow_patterns_match(value: str, patterns: list[object]) -> bool:
    """Return GitHub-style ordered include/exclude matching for one known value."""

    matched = False
    for pattern in patterns:
        assert isinstance(pattern, str)
        excluded = pattern.startswith("!")
        candidate = pattern.removeprefix("!")
        if _github_workflow_glob_matches(value, candidate):
            matched = not excluded
    return matched


def _assert_node24_frontend_builder_workflow_contract(
    workflow: dict[str, object],
) -> None:
    """Assert the finite workflow carriers that keep the Node guard blocking."""

    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)

    workflow_env = workflow["env"]
    assert isinstance(workflow_env, dict)
    assert "PYTEST_ADDOPTS" not in workflow_env

    workflow_defaults = workflow.get("defaults", {})
    assert isinstance(workflow_defaults, dict)
    workflow_run_defaults = workflow_defaults.get("run", {})
    assert isinstance(workflow_run_defaults, dict)
    assert "shell" not in workflow_run_defaults

    dockerfile_path = "frontend/Dockerfile.caddy-spa"
    for event_name in ("pull_request", "push"):
        event = on_section[event_name]
        assert isinstance(event, dict)
        branches = event["branches"]
        assert isinstance(branches, list)
        assert _workflow_patterns_match(
            "main", branches
        ), f"{event_name} must run for the main branch"
        paths = event["paths"]
        assert isinstance(paths, list)
        assert _workflow_patterns_match(
            dockerfile_path, paths
        ), f"{event_name} must route {dockerfile_path} through Frontend CI"

    pull_request_event = on_section["pull_request"]
    assert isinstance(pull_request_event, dict)
    pull_request_types = pull_request_event.get("types")
    if pull_request_types is not None:
        assert isinstance(pull_request_types, list)
        assert {"opened", "synchronize", "reopened"}.issubset(pull_request_types)

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["build-and-test"]
    assert isinstance(job, dict)
    assert "if" not in job
    assert "continue-on-error" not in job

    defaults = job["defaults"]
    assert isinstance(defaults, dict)
    run_defaults = defaults["run"]
    assert isinstance(run_defaults, dict)
    assert "shell" not in run_defaults

    job_env = job["env"]
    assert isinstance(job_env, dict)
    assert "PYTEST_ADDOPTS" not in job_env

    step = _job_step_by_name(
        workflow,
        job_id="build-and-test",
        step_name="Run frontend builder governance guard",
    )
    assert set(step) == {"name", "run"}
    assert step["run"] == (
        "cd ..\n"
        "python -m pytest -q \\\n"
        "  tests/test_ci_workflow_pr_size_governance_contract.py \\\n"
        "  -k node24\n"
    )


def test_node24_frontend_builder_guard_runs_for_dockerfile_changes() -> None:
    """Frontend CI must execute the bounded guard on Dockerfile-only changes."""

    workflow = _load_workflow(FRONTEND_CI_WORKFLOW_PATH)
    _assert_node24_frontend_builder_workflow_contract(workflow)


@pytest.mark.parametrize(
    "mutation",
    (
        "pull_request_paths",
        "push_paths",
        "pull_request_path_exclusion",
        "push_path_exclusion",
        "pull_request_root_star_paths",
        "push_root_star_paths",
        "pull_request_branches",
        "push_branches",
        "pull_request_types",
        "step_if",
        "step_continue_on_error",
        "job_continue_on_error",
        "step_shell",
        "job_default_shell",
        "workflow_default_shell",
        "workflow_pytest_collect_only",
        "step_pytest_collect_only",
        "job_pytest_collect_only",
    ),
)
def test_node24_frontend_builder_workflow_guard_rejects_disabled_wiring(
    mutation: str,
) -> None:
    """Every bounded trigger or fail-open carrier must make the guard fail."""

    workflow = _load_workflow(FRONTEND_CI_WORKFLOW_PATH)
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["build-and-test"]
    assert isinstance(job, dict)
    step = _job_step_by_name(
        workflow,
        job_id="build-and-test",
        step_name="Run frontend builder governance guard",
    )

    if mutation in {"pull_request_paths", "push_paths"}:
        event_name = mutation.removesuffix("_paths")
        event = on_section[event_name]
        assert isinstance(event, dict)
        event["paths"] = [".nvmrc"]
    if mutation in {"pull_request_path_exclusion", "push_path_exclusion"}:
        event_name = mutation.removesuffix("_path_exclusion")
        event = on_section[event_name]
        assert isinstance(event, dict)
        event["paths"] = ["frontend/**", "!frontend/Dockerfile.caddy-spa"]
    if mutation in {"pull_request_root_star_paths", "push_root_star_paths"}:
        event_name = mutation.removesuffix("_root_star_paths")
        event = on_section[event_name]
        assert isinstance(event, dict)
        event["paths"] = ["*"]
    if mutation in {"pull_request_branches", "push_branches"}:
        event_name = mutation.removesuffix("_branches")
        event = on_section[event_name]
        assert isinstance(event, dict)
        event["branches"] = ["feat/**"]
    if mutation == "pull_request_types":
        event = on_section["pull_request"]
        assert isinstance(event, dict)
        event["types"] = ["opened", "reopened", "edited"]
    if mutation == "step_if":
        step["if"] = "${{ false }}"
    if mutation == "step_continue_on_error":
        step["continue-on-error"] = True
    if mutation == "job_continue_on_error":
        job["continue-on-error"] = True
    if mutation == "step_shell":
        step["shell"] = "bash -c '{0} || true'"
    if mutation == "job_default_shell":
        defaults = job["defaults"]
        assert isinstance(defaults, dict)
        run_defaults = defaults["run"]
        assert isinstance(run_defaults, dict)
        run_defaults["shell"] = "bash -c '{0} || true'"
    if mutation == "workflow_default_shell":
        workflow["defaults"] = {"run": {"shell": "bash -c '{0} || true'"}}
    if mutation == "workflow_pytest_collect_only":
        workflow_env = workflow["env"]
        assert isinstance(workflow_env, dict)
        workflow_env["PYTEST_ADDOPTS"] = "--collect-only"
    if mutation == "step_pytest_collect_only":
        step["env"] = {"PYTEST_ADDOPTS": "--collect-only"}
    if mutation == "job_pytest_collect_only":
        job_env = job["env"]
        assert isinstance(job_env, dict)
        job_env["PYTEST_ADDOPTS"] = "--collect-only"

    with pytest.raises(AssertionError):
        _assert_node24_frontend_builder_workflow_contract(workflow)


def _extract_shell_conditional_block(
    script_text: str,
    branch_marker: str,
    next_marker: str,
) -> str:
    """Return the shell branch body between two explicit workflow markers."""

    start_anchor = f"{branch_marker}\n"
    end_anchor = f"\n{next_marker}"
    assert start_anchor in script_text, f"Missing shell branch marker: {branch_marker}"
    branch_tail = script_text.split(start_anchor, maxsplit=1)[1]
    assert end_anchor in branch_tail, f"Missing shell branch boundary after {branch_marker}"
    return branch_tail.split(end_anchor, maxsplit=1)[0]


def test_nightly_full_tests_uses_process_shards_without_xdist() -> None:
    """Nightly full coverage keeps slow tests but avoids xdist worker shutdown hangs."""

    workflow = _load_workflow(NIGHTLY_FULL_TESTS_WORKFLOW_PATH)
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["tests"]
    assert "continue-on-error" not in job

    checkout_step = _job_step_by_name(workflow, job_id="tests", step_name="Checkout")
    assert checkout_step["uses"] == f"actions/checkout@{CHECKOUT_NODE24_SHA}"
    assert checkout_step["with"]["fetch-depth"] == 0
    assert checkout_step["with"]["persist-credentials"] is False

    test_step = _job_step_by_name(
        workflow,
        job_id="tests",
        step_name="Run full test suite with coverage (include slow/MC)",
    )
    run_script = test_step["run"]
    assert isinstance(run_script, str)
    env = test_step["env"]
    assert isinstance(env, dict)
    assert "continue-on-error" not in test_step

    assert env["BAYESIAN_PERSIST"] == "1"
    assert env["BAYESIAN_HISTORY_PATH"] == "/tmp/test_execution_history.json"
    assert env["MC_SEED"] == "2025"
    assert env["MC_SAMPLES"] == "40"
    assert env["MC_SAMPLES_FEW"] == "15"
    assert env["MAIN_TEST_SHARDS"] == "16"
    assert env["MAIN_TEST_MAX_PARALLEL"] == "4"
    assert env["MAIN_TEST_SHARD_TIMEOUT_SECONDS"] == "4800"
    assert env["MAIN_TEST_COVERAGE_TIMEOUT_SECONDS"] == "1200"

    assert "set -euo pipefail" in run_script
    assert "python scripts/ci/run_main_test_shards.py" in run_script
    assert '--python-version "3.13"' in run_script
    assert '--shard-count "${MAIN_TEST_SHARDS}"' in run_script
    assert '--max-parallel "${MAIN_TEST_MAX_PARALLEL}"' in run_script
    assert '--marker-expression "not demo"' in run_script
    assert '--durations-min "1.0"' in run_script
    assert '--report-chars "fEsxXw"' in run_script
    assert "--htmlcov" in run_script
    assert "TEST_STEP_STARTED_AT=" in run_script
    assert "MAIN_TEST_COVERAGE_TIMEOUT_SECONDS=" in run_script
    assert "TEST_STEP_FINISHED_AT=" in run_script
    assert "set +e" in run_script
    assert "test_exit_code=$?" in run_script
    assert "set -e" in run_script
    assert 'exit "$test_exit_code"' in run_script

    assert "pytest -c pyproject.toml" not in run_script
    assert "-n auto" not in run_script
    assert "--dist=loadgroup" not in run_script
    assert "--cov-fail-under=97" not in run_script

    coverage_upload = _job_step_by_name(
        workflow,
        job_id="tests",
        step_name="Upload coverage artifact",
    )
    html_upload = _job_step_by_name(
        workflow,
        job_id="tests",
        step_name="Upload HTML coverage artifact",
    )
    assert coverage_upload["with"] == {"name": "coverage-xml", "path": "coverage.xml"}
    assert html_upload["with"] == {"name": "htmlcov", "path": "htmlcov"}


def test_pr_size_governance_reruns_when_trusted_approval_labels_change() -> None:
    """Trusted scope labels must trigger fresh PR-size governance event payloads."""

    workflow = _load_ci_workflow()
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)
    pull_request_section = on_section["pull_request"]
    assert isinstance(pull_request_section, dict)
    event_types = pull_request_section["types"]
    assert isinstance(event_types, list)

    assert "labeled" in event_types
    assert "unlabeled" in event_types


def test_pr_size_governance_uses_pull_request_head_sha() -> None:
    """Guard against merge-SHA inflation in PR-size governance diff calculation."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    pr_scope_guard_section = _extract_section(
        workflow_text,
        "pr_scope_guard:",
        "      - name: Design invariant guard",
    )

    assert "permissions:" in pr_scope_guard_section
    assert "contents: read" in pr_scope_guard_section
    assert "pull-requests: read" in pr_scope_guard_section
    assert "python3 scripts/ci/check_pr_size_governance.py \\" in pr_scope_guard_section
    assert '--base-sha "${{ github.event.pull_request.base.sha }}" \\' in pr_scope_guard_section
    assert '--head-sha "${{ github.event.pull_request.head.sha }}" \\' in pr_scope_guard_section
    assert '--event-path "$GITHUB_EVENT_PATH"' in pr_scope_guard_section
    assert '--head-sha "${{ github.sha }}" \\' not in pr_scope_guard_section
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in pr_scope_guard_section
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in pr_scope_guard_section


def test_pr_risk_profile_uses_pull_request_head_sha() -> None:
    """Guard contract-risk routing against merge-SHA based diff calculations."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    risk_profile_section = _extract_section(
        workflow_text,
        "      - name: Build CI risk profile",
        "\n  pr_scope_guard:",
    )

    assert "python3 scripts/ci/ci_risk_profile.py \\" in risk_profile_section
    assert 'BASE_SHA="${{ github.event.pull_request.base.sha }}"' in risk_profile_section
    assert 'HEAD_SHA="${{ github.event.pull_request.head.sha }}"' in risk_profile_section
    assert '--base-sha "${BASE_SHA}" \\' in risk_profile_section
    assert '--head-sha "${HEAD_SHA}" \\' in risk_profile_section


def test_docs_phase1_gates_include_schema_only_contract_changes() -> None:
    """SC-G5 schema-only edits must still run the docs Phase1 validator."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    docs_phase1_section = _extract_job_section(workflow_text, "  docs_phase1_gates:")

    assert "PHASE1_CHANGED_FILES=()" in docs_phase1_section
    assert "'docs/orchestration/contracts/*.schema.json'" in docs_phase1_section
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json'" in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/VERIFICATION_PROVENANCE_ADMISSION_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "':(glob)docs/orchestration/contracts/philosophy_alignment_rules/**/*.json'"
        in docs_phase1_section
    )
    assert (
        "docs/orchestration/contracts/PHILOSOPHY_ALIGNMENT_RULE.schema.json" in docs_phase1_section
    )
    assert (
        "'tests/fixtures/orchestration/philosophy_admission_claim_oracle.json'"
        in docs_phase1_section
    )
    assert (
        "No changed markdown or Phase1 schema files; skipping docs Phase1 gates."
        in docs_phase1_section
    )
    assert (
        'if [ "${PR4_PRECONDITION_CHANGED}" -eq 0 ] && [ "${PR5_SOURCE_CORPUS_CHANGED}" -eq 0 ] && [ "${#PHASE1_CHANGED_FILES[@]}" -eq 0 ] && [ "${#LINT_MD[@]}" -eq 0 ]; then'
        in docs_phase1_section
    )
    assert (
        "No changed docs markdown or Phase1 schema files; skipping docs Phase1 validator."
        in docs_phase1_section
    )
    assert (
        'python scripts/ci/check_docs_phase1_gates.py --files "${PHASE1_CHANGED_FILES[@]}"'
        in docs_phase1_section
    )
    assert "PR4_PRECONDITION_CHANGED=0" in docs_phase1_section
    assert "PR5_SOURCE_CORPUS_CHANGED=0" in docs_phase1_section
    assert "git rev-parse HEAD^2 >/dev/null 2>&1" in (docs_phase1_section)
    assert 'BASE_REF="$(git rev-parse HEAD^1)"' in (docs_phase1_section)
    assert 'BASE_REF="${{ github.event.pull_request.base.sha }}"' in (docs_phase1_section)
    assert docs_phase1_section.index("git rev-parse HEAD^2") < (
        docs_phase1_section.index('BASE_REF="$(git rev-parse HEAD^1)"')
    )
    assert docs_phase1_section.index('BASE_REF="$(git rev-parse HEAD^1)"') < (
        docs_phase1_section.index("github.event.pull_request.base.sha")
    )
    assert 'git diff --name-status -z --diff-filter=ACDMRT "$BASE_REF"...HEAD' in (
        docs_phase1_section
    )
    assert 'case "$status" in' in docs_phase1_section
    assert "R*|C*)" in docs_phase1_section
    assert 'CHANGED_PATHS+=("$old_path" "$new_path")' in docs_phase1_section
    assert 'CHANGED_PATHS+=("$path")' in docs_phase1_section
    for pr4_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json",
        "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.schema.json",
        "tests/fixtures/orchestration/philosophy_admission_claim_oracle.json",
        "docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json",
        "docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.schema.json",
        "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
        "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.schema.json",
        "docs/orchestration/contracts/PHILOSOPHY_ALIGNMENT_RULE.schema.json",
        "docs/orchestration/contracts/philosophy_alignment_rules/*.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR4_GATE_OPEN_PRECONDITIONS_PACKET_2026-05-21.md",
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        "scripts/ci/check_philosophy_gate_open_preconditions.py",
        "tests/test_philosophy_gate_open_preconditions.py",
    ):
        assert pr4_companion_input in docs_phase1_section
    for pr5_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json",
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md",
        "scripts/ci/check_philosophy_source_corpus_index.py",
        "tests/test_philosophy_source_corpus_index.py",
    ):
        assert pr5_companion_input in docs_phase1_section
    pr5_case = _extract_section(
        docs_phase1_section,
        '              case "$path" in\n'
        "                docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json",
        "                  PR5_SOURCE_CORPUS_CHANGED=1",
    )
    for pr5_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md",
        "scripts/ci/check_philosophy_source_corpus_index.py",
        "tests/test_philosophy_source_corpus_index.py",
    ):
        assert pr5_companion_input in pr5_case
    for unrelated_pr5_trigger in (
        "docs/roadmap/BACKLOG_LEDGER.md",
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        "scripts/ci/check_docs_phase1_gates.py",
    ):
        assert unrelated_pr5_trigger not in pr5_case
    assert (
        "python scripts/ci/check_philosophy_gate_open_preconditions.py --check --files"
        in docs_phase1_section
    )
    assert (
        "python scripts/ci/check_philosophy_source_corpus_index.py --check --files"
        in docs_phase1_section
    )
    assert (
        'python scripts/ci/check_docs_phase1_gates.py --files "${CHANGED_DOCS[@]}"'
        not in docs_phase1_section
    )


def test_semantic_cache_contract_suites_include_philosophy_policy_oracle() -> None:
    """Current-head CI must execute the Philosophy policy/oracle drift regressions."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert workflow_text.count("tests/test_philosophy_admission_dry_run_report.py \\") >= 2
    assert workflow_text.count("tests/test_philosophy_admission_policy_oracle.py \\") >= 2
    assert workflow_text.count("tests/test_verification_provenance_admission_report.py \\") >= 2
    assert (
        workflow_text.count("tests/core/ai/test_semantic_cache_offline_admission_runner.py \\") >= 2
    )
    assert (
        workflow_text.count("tests/core/ai/test_semantic_cache_shadow_admission_harness.py \\") >= 2
    )


def test_changes_job_uses_node24_paths_filter_pin_and_keeps_ios_filters() -> None:
    """Guard the Node 24 paths-filter migration and iOS path-gating contract."""

    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    changes = jobs["changes"]
    assert isinstance(changes, dict)
    steps = changes["steps"]
    assert isinstance(steps, list)

    filter_step = next(step for step in steps if step.get("id") == "filter")
    assert filter_step["uses"] == f"dorny/paths-filter@{PATHS_FILTER_NODE24_SHA}"

    with_section = filter_step["with"]
    assert isinstance(with_section, dict)
    assert with_section["token"] == "${{ secrets.GITHUB_TOKEN }}"
    filters = with_section["filters"]
    assert isinstance(filters, str)
    assert "ios:" in filters
    assert "- 'ios/**'" in filters
    assert "- '.github/workflows/**'" in filters
    assert "- '.github/actions/**'" in filters


def test_node24_artifact_and_script_action_pins_use_verified_commit_shas() -> None:
    """Guard remaining Node 20 action migrations against tag-object drift."""

    download_workflows = {
        CI_WORKFLOW_PATH: 6,
        CODECOV_UPLOAD_WORKFLOW_PATH: 1,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH: 1,
        NIGHTLY_WORKFLOW_PATH: 1,
    }
    expected_download_line = (
        f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA} # v8.0.1 / Node 24"
    )

    observed_download_steps = 0
    for workflow_path, expected_count in download_workflows.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert workflow_text.count(expected_download_line) == expected_count
        assert f"actions/download-artifact@{OLD_DOWNLOAD_ARTIFACT_SHA}" not in workflow_text

        for _job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("actions/download-artifact@"):
                observed_download_steps += 1
                assert uses == f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA}"

    assert observed_download_steps == sum(download_workflows.values())

    pr_automation_text = PR_AUTOMATION_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        f"actions/github-script@{GITHUB_SCRIPT_NODE24_SHA} # v9.0.0 / Node 24" in pr_automation_text
    )
    assert f"actions/github-script@{OLD_GITHUB_SCRIPT_SHA}" not in pr_automation_text
    assert GITHUB_SCRIPT_V9_TAG_OBJECT_SHA not in pr_automation_text


def test_codecov_action_pin_uses_node24_transitive_github_script() -> None:
    """Guard Codecov uploads against reintroducing the old Node 20 github-script dependency."""

    expected_codecov_line = (
        f"codecov/codecov-action@{CODECOV_ACTION_NODE24_SHA} "
        "# v6.0.0 / Node 24 transitive github-script"
    )
    workflow_counts = {
        CI_WORKFLOW_PATH: 3,
        CODECOV_UPLOAD_WORKFLOW_PATH: 1,
    }

    observed_codecov_steps = []
    for workflow_path, expected_count in workflow_counts.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert workflow_text.count(expected_codecov_line) == expected_count
        assert f"codecov/codecov-action@{OLD_CODECOV_ACTION_SHA}" not in workflow_text

        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("codecov/codecov-action@"):
                observed_codecov_steps.append((workflow_path, job_id, step))
                assert uses == f"codecov/codecov-action@{CODECOV_ACTION_NODE24_SHA}"

    assert len(observed_codecov_steps) == sum(workflow_counts.values())


def test_cd_test_published_image_health_smoke_is_trusted_and_fail_closed() -> None:
    """Keep the privileged published-image smoke exact, bounded, and diagnostic."""

    workflow_text = CD_TEST_WORKFLOW_PATH.read_text(encoding="utf-8")
    trigger_section = _extract_section(
        workflow_text,
        "name: CD-Test\n",
        "\npermissions:\n",
    ).strip()
    assert trigger_section == (
        "on:\n"
        "  workflow_run:\n"
        '    workflows: ["Docker Build and Push"]\n'
        "    types: [completed]\n"
        "    branches: [ main ]\n"
        "  push:\n"
        "    tags:\n"
        "      - 'v*'"
    )

    workflow = _load_workflow(CD_TEST_WORKFLOW_PATH)
    assert workflow["permissions"] == {
        "contents": "read",
        "packages": "read",
        "id-token": "write",
    }

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    validate_job = jobs["validate-environment"]
    assert isinstance(validate_job, dict)
    assert validate_job["timeout-minutes"] == (
        "${{ fromJSON(vars.CD_TEST_VALIDATE_TIMEOUT_MINUTES || '10') }}"
    )
    assert validate_job["environment"] == {"name": "staging"}

    trusted_run_condition = validate_job["if"]
    assert isinstance(trusted_run_condition, str)
    assert trusted_run_condition == (
        "${{\n"
        "  github.event_name == 'workflow_run' &&\n"
        "  github.event.workflow_run.conclusion == 'success' &&\n"
        "  github.event.workflow_run.event == 'push' &&\n"
        "  github.event.workflow_run.head_branch == 'main' &&\n"
        "  github.event.workflow_run.head_repository.full_name == github.repository\n"
        "}}"
    )

    validate_steps = validate_job["steps"]
    assert isinstance(validate_steps, list)
    validate_checkout = validate_steps[0]
    assert isinstance(validate_checkout, dict)
    assert validate_checkout["uses"] == f"actions/checkout@{CHECKOUT_NODE24_SHA}"
    assert validate_checkout["with"] == {
        "ref": "${{ github.event.workflow_run.head_sha }}",
        "persist-credentials": False,
    }

    exact_image_ref = (
        "ghcr.io/${{ steps.image-name.outputs.image_name }}:"
        "${{ github.event.workflow_run.head_sha }}"
    )
    assert workflow_text.count(exact_image_ref) == 2

    pull_step = _job_step_by_name(
        workflow,
        job_id="validate-environment",
        step_name="Test Docker image pull",
    )
    pull_env = pull_step["env"]
    assert isinstance(pull_env, dict)
    assert pull_env == {
        "GHCR_READ_TOKEN": "${{ secrets.GHCR_READ_TOKEN }}",
        "IMAGE_REF": exact_image_ref,
        "REPOSITORY_OWNER": "${{ github.repository_owner }}",
    }
    pull_script = pull_step["run"]
    assert isinstance(pull_script, str)
    assert pull_step.get("continue-on-error") is None
    assert "|| true" not in pull_script
    assert "|| echo" not in pull_script
    assert "${{ secrets." not in pull_script
    assert "${{ secrets.GHCR_READ_TOKEN }}" not in pull_script
    _assert_contains_all_tokens(
        pull_script,
        (
            'if [ -z "${GHCR_READ_TOKEN:-}" ]',
            "printf '%s' \"$GHCR_READ_TOKEN\"",
            '--username "$REPOSITORY_OWNER"',
            "--password-stdin",
            'docker pull "$IMAGE_REF"',
        ),
    )

    health_step = _job_step_by_name(
        workflow,
        job_id="validate-environment",
        step_name="Test health endpoint locally",
    )
    assert health_step.get("continue-on-error") is None
    assert health_step["env"] == {"IMAGE_REF": exact_image_ref}
    health_script = health_step["run"]
    assert isinstance(health_script, str)
    assert "${{ secrets." not in health_script
    assert "GHCR_READ_TOKEN" not in health_script

    build_workflow = _load_workflow(BUILD_WORKFLOW_PATH)
    build_smoke_step = _job_step_by_name(
        build_workflow,
        job_id="build",
        step_name="Test Docker image",
    )
    build_smoke_script = build_smoke_step["run"]
    assert isinstance(build_smoke_script, str)
    expected_ci_environment = {
        '"${api_key_name}=test_key"',
        '"${allow_dev_api_key_name}=false"',
        '"${export_token_secret_name}=ci-smoke-export-secret"',
        '"${server_salt_name}=StrongServerSaltForCI1234567890!"',
        '"${apple_shared_secret_name}=StrongAppleSharedSecretForCI1234567890!"',
        '"${subscription_db_enabled_name}=true"',
        '"${database_url_name}=sqlite:////app/cache/pulseplate-smoke.db"',
        "APP_ENV=ci",
        "ENVIRONMENT=ci",
    }
    assert _docker_environment_flags(build_smoke_script) == expected_ci_environment
    assert _docker_environment_flags(health_script) == expected_ci_environment
    expected_obfuscated_names = {
        "api_key_name": ("API", "_KEY"),
        "allow_dev_api_key_name": ("ALLOW_DEV_API", "_KEY"),
        "export_token_" + "secret_name": ("EXPORT_TOKEN", "_SECRET"),
        "server_" + "salt_name": ("SERVER", "_SALT"),
        "apple_shared_" + "secret_name": ("APPLE_SHARED", "_SECRET"),
        "subscription_db_enabled_name": ("SUBSCRIPTION_DB", "_ENABLED"),
        "database_" + "url_name": ("DATABASE", "_URL"),
    }
    for variable_name, (prefix, suffix) in expected_obfuscated_names.items():
        assert f'{variable_name}="{prefix}""{suffix}"' in health_script
    _assert_contains_all_tokens(
        health_script,
        (
            "--cap-drop=ALL",
            "--security-opt no-new-privileges",
            '"$IMAGE_REF"',
        ),
    )

    assert "docker run --rm" not in health_script
    assert "-p 127.0.0.1:8000:8000" in health_script
    assert "-p 8000:8000" not in health_script
    assert "Health check failed (expected without frontend)" not in health_script
    assert "|| echo" not in health_script
    assert "|| true" not in health_script
    assert health_script.count("curl -fSs --connect-timeout 2 --max-time 5") == 2
    assert health_script.count("http://localhost:8000/health") == 2
    _assert_contains_all_tokens(
        health_script,
        (
            "trap cleanup EXIT",
            "original_status=$?",
            "trap - EXIT",
            "container_present=false",
            "container_present=true",
            'docker container inspect "$container_name"',
            "docker container ls -a --format '{{.Names}}'",
            'docker rm -f "$container_name"',
            'exit "$original_status"',
            "docker logs --tail 200",
            "max_attempts=30",
            "attempt=1",
            "ready=false",
            'while [ "$attempt" -le "$max_attempts" ]',
            'if [ "$attempt" -eq "$max_attempts" ]',
            "attempt=$((attempt + 1))",
            'if [ "$ready" != "true" ]',
        ),
    )
    assert health_script.index("trap cleanup EXIT") < health_script.index("docker run -d")
    launch_index = health_script.index("if ! docker run -d")
    launch_failure_message_index = health_script.index(
        "Failed to launch health-smoke container",
        launch_index,
    )
    launch_failure_diagnostics_index = health_script.index(
        "show_container_diagnostics",
        launch_failure_message_index,
    )
    launch_failure_exit_index = health_script.index(
        "exit 1",
        launch_failure_diagnostics_index,
    )
    assert launch_index < launch_failure_message_index
    assert launch_failure_message_index < launch_failure_diagnostics_index
    assert launch_failure_diagnostics_index < launch_failure_exit_index
    first_probe_index = health_script.index("if curl -fSs")
    post_probe_liveness_index = health_script.index(
        'if ! docker container inspect "$container_name"',
        first_probe_index,
    )
    early_exit_diagnostics_index = health_script.index(
        "show_container_diagnostics",
        post_probe_liveness_index,
    )
    early_exit_failure_index = health_script.index(
        "exit 1",
        early_exit_diagnostics_index,
    )
    assert first_probe_index < post_probe_liveness_index
    assert post_probe_liveness_index < early_exit_diagnostics_index
    assert early_exit_diagnostics_index < early_exit_failure_index
    timeout_message_index = health_script.index("Health endpoint did not become ready after")
    timeout_diagnostics_index = health_script.index(
        "show_container_diagnostics",
        timeout_message_index,
    )
    timeout_failure_index = health_script.index("exit 1", timeout_diagnostics_index)
    assert timeout_message_index < timeout_diagnostics_index < timeout_failure_index
    final_probe_index = health_script.rindex("curl -fSs --connect-timeout 2 --max-time 5")
    assert final_probe_index > timeout_failure_index
    final_probe_diagnostics_index = health_script.index(
        "show_container_diagnostics",
        final_probe_index,
    )
    final_probe_failure_index = health_script.index(
        "exit 1",
        final_probe_diagnostics_index,
    )
    assert final_probe_index < final_probe_diagnostics_index < final_probe_failure_index

    production_job = jobs["production-validation"]
    assert isinstance(production_job, dict)
    assert production_job["if"] == "startsWith(github.ref, 'refs/tags/v')"
    assert production_job["environment"] == {"name": "production"}
    production_steps = production_job["steps"]
    assert isinstance(production_steps, list)
    production_checkout = production_steps[0]
    assert isinstance(production_checkout, dict)
    assert production_checkout["uses"] == f"actions/checkout@{CHECKOUT_NODE24_SHA}"
    assert "with" not in production_checkout
    production_validation = _job_step_by_name(
        workflow,
        job_id="production-validation",
        step_name="Validate production environment",
    )
    assert production_validation["env"] == {
        "ENVIRONMENT": "production",
        "GHCR_READ_TOKEN": "${{ secrets.GHCR_READ_TOKEN }}",
        "LLM_ENABLED": "false",
    }


def test_node24_checkout_and_docker_action_pins_use_verified_commit_shas() -> None:
    """Guard remaining Node 20 workflow action migrations against regression."""

    active_workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in _active_workflow_paths()
    )
    old_node20_shas = (
        OLD_CHECKOUT_NODE20_SHA,
        OLD_CHECKOUT_V6_NODE20_SHA,
        OLD_DOCKER_SETUP_BUILDX_SHA,
        OLD_DOCKER_LOGIN_SHA,
        OLD_DOCKER_METADATA_SHA,
        OLD_TRIVY_ACTION_SHA,
        OLD_TRIVY_INTERNAL_CACHE_NODE20_SHA,
        OLD_SETUP_GO_SHA,
        OLD_UPLOAD_ARTIFACT_SHA,
        OLD_UPLOAD_ARTIFACT_V7_SHA,
    )
    for old_sha in old_node20_shas:
        assert old_sha not in active_workflow_text

    forbidden_override_env_vars = (
        "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION",
        "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24",
        "CI_ALLOW_MERGE_OVERRIDE",
    )
    for env_var in forbidden_override_env_vars:
        assert env_var not in active_workflow_text

    checkout_workflows = {
        ACTIONLINT_WORKFLOW_PATH: 1,
        CD_TEST_WORKFLOW_PATH: 2,
        CODECOV_UPLOAD_WORKFLOW_PATH: 1,
        CODEQL_WORKFLOW_PATH: 1,
        GREENLIGHT_IOS_WORKFLOW_PATH: 1,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH: 3,
        SECURITY_WORKFLOW_PATH: 1,
    }
    expected_checkout_line = f"actions/checkout@{CHECKOUT_NODE24_SHA} # v6.0.2 / Node 24"

    observed_checkout_steps = 0
    for workflow_path, expected_count in checkout_workflows.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert workflow_text.count(expected_checkout_line) == expected_count

        for _job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("actions/checkout@"):
                observed_checkout_steps += 1
                assert uses == f"actions/checkout@{CHECKOUT_NODE24_SHA}"

    assert observed_checkout_steps == sum(checkout_workflows.values())

    expected_docker_lines = {
        BUILD_WORKFLOW_PATH: {
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA} # v4.1.0 / Node 24": 2,
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA} # v4.2.0 / Node 24": 1,
            f"docker/metadata-action@{DOCKER_METADATA_NODE24_SHA} # v6.1.0 / Node 24": 1,
        },
        CD_WORKFLOW_PATH: {
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA} # v4.1.0 / Node 24": 2,
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA} # v4.2.0 / Node 24": 2,
        },
        TRIVY_WORKFLOW_PATH: {
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA} # v4.1.0 / Node 24": 1,
        },
    }
    for workflow_path, expected_counts in expected_docker_lines.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for expected_line, expected_count in expected_counts.items():
            assert workflow_text.count(expected_line) == expected_count

    expected_trivy_lines = {
        BUILD_WORKFLOW_PATH: {
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA} "
            "# v0.36.0 / Node 24 cache path": 2,
        },
        CD_WORKFLOW_PATH: {
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA} "
            "# v0.36.0 / Node 24 cache path": 2,
        },
        TRIVY_WORKFLOW_PATH: {
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA} "
            "# v0.36.0 / Node 24 cache path": 1,
        },
    }
    for workflow_path, expected_counts in expected_trivy_lines.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for expected_line, expected_count in expected_counts.items():
            assert workflow_text.count(expected_line) == expected_count

    observed_docker_contracts = []
    for workflow_path in (BUILD_WORKFLOW_PATH, CD_WORKFLOW_PATH, TRIVY_WORKFLOW_PATH):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.startswith("docker/"):
                continue
            if uses.startswith("docker/build-push-action@"):
                continue
            observed_docker_contracts.append(
                (
                    str(workflow_path.relative_to(REPO_ROOT)),
                    job_id,
                    step.get("name"),
                    uses,
                    step.get("with"),
                    step.get("if"),
                    step.get("env"),
                    step.get("continue-on-error"),
                )
            )

    assert observed_docker_contracts == [
        (
            ".github/workflows/build.yml",
            "build",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Extract metadata",
            f"docker/metadata-action@{DOCKER_METADATA_NODE24_SHA}",
            {
                "images": ("${{ env.REGISTRY }}/${{ steps.image-name.outputs.image_name }}"),
                "tags": (
                    "type=raw,value=${{ github.sha }}\n"
                    "type=raw,value=sha-${{ github.sha }}\n"
                    "type=ref,event=branch\n"
                    "type=semver,pattern={{version}}\n"
                    "type=semver,pattern={{major}}.{{minor}}\n"
                    "type=raw,value=latest,enable={{is_default_branch}}\n"
                ),
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Log in to GHCR",
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA}",
            {
                "registry": "${{ env.REGISTRY }}",
                "username": "${{ github.repository_owner }}",
                "password": "${{ secrets.GITHUB_TOKEN }}",
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Log in to Container Registry",
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA}",
            {
                "registry": "ghcr.io",
                "username": "${{ github.actor }}",
                "password": "${{ secrets.GITHUB_TOKEN }}",
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build-production",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build-production",
            "Log in to Container Registry",
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA}",
            {
                "registry": "ghcr.io",
                "username": "${{ github.actor }}",
                "password": "${{ secrets.GITHUB_TOKEN }}",
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/trivy.yml",
            "build",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
    ]

    observed_trivy_contracts = []
    for workflow_path in (BUILD_WORKFLOW_PATH, CD_WORKFLOW_PATH, TRIVY_WORKFLOW_PATH):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("aquasecurity/trivy-action@"):
                observed_trivy_contracts.append(
                    (
                        str(workflow_path.relative_to(REPO_ROOT)),
                        job_id,
                        step.get("name"),
                        uses,
                        step.get("with"),
                        step.get("if"),
                        step.get("env"),
                        step.get("continue-on-error"),
                    )
                )

    assert observed_trivy_contracts == [
        (
            ".github/workflows/build.yml",
            "security-scan",
            "Run Trivy vulnerability scanner (filesystem scan)",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "fs",
                "scan-ref": ".",
                "cache-dir": "/tmp/trivy-cache",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "scanners": "vuln",
                "format": "sarif",
                "output": "${{ runner.temp }}/pulseplate-trivy/trivy-results.sarif",
                "skip-dirs": "trivy",
                "severity": "CRITICAL,HIGH",
                "limit-severities-for-sarif": True,
                "exit-code": "1",
                "trivyignores": ".trivyignore",
                "version": TRIVY_RUNTIME_VERSION,
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Run Trivy vulnerability scanner (image scan, fail-closed)",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "image",
                "image-ref": "${{ steps.image-ref.outputs.ref }}",
                "cache-dir": "/tmp/trivy-cache",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "scanners": "vuln",
                "format": "sarif",
                "output": "trivy-image.sarif",
                "severity": "CRITICAL,HIGH",
                "limit-severities-for-sarif": True,
                "trivyignores": ".trivyignore",
                "exit-code": "1",
                "version": TRIVY_RUNTIME_VERSION,
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Scan staged backend image",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "image",
                "image-ref": "${{ steps.staging-image-refs.outputs.backend_ref }}",
                "scanners": "vuln,secret",
                "format": "table",
                "vuln-type": "os,library",
                "severity": "CRITICAL,HIGH",
                "exit-code": "1",
                "timeout": "15m",
                "trivyignores": ".trivyignore",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "version": TRIVY_RUNTIME_VERSION,
                "cache-dir": "/tmp/trivy-cache-staging-backend",
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Scan staged Caddy image",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "image",
                "image-ref": "${{ steps.staging-image-refs.outputs.caddy_ref }}",
                "scanners": "vuln,secret",
                "format": "table",
                "vuln-type": "os,library",
                "severity": "CRITICAL,HIGH",
                "exit-code": "1",
                "timeout": "15m",
                "trivyignores": ".trivyignore-caddy",
                "version": TRIVY_RUNTIME_VERSION,
                "cache-dir": "/tmp/trivy-cache-staging-caddy",
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/trivy.yml",
            "build",
            "Run Trivy vulnerability scanner",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "image",
                "image-ref": "pulseplate:trivy-scan-${{ github.sha }}",
                "cache-dir": "/tmp/trivy-cache",
                "scanners": "vuln",
                "timeout": "15m",
                "format": "sarif",
                "output": "trivy-results.sarif",
                "severity": "CRITICAL,HIGH",
                "limit-severities-for-sarif": True,
                "ignore-unfixed": True,
                "trivyignores": ".trivyignore",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "exit-code": "1",
                "version": TRIVY_RUNTIME_VERSION,
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
    ]
    assert len(observed_trivy_contracts) == 5


def test_build_workflow_trivy_fs_sarif_is_temp_isolated_before_upload() -> None:
    workflow = _load_workflow(BUILD_WORKFLOW_PATH)
    prepare_step = _job_step_by_name(
        workflow,
        job_id="security-scan",
        step_name="Prepare Trivy SARIF output path and ignore policy",
    )
    scanner_step = _job_step_by_name(
        workflow,
        job_id="security-scan",
        step_name="Run Trivy vulnerability scanner (filesystem scan)",
    )
    sarif_check_step = _job_step_by_name(
        workflow,
        job_id="security-scan",
        step_name="Check Trivy filesystem SARIF output",
    )
    upload_step = _job_step_by_name(
        workflow,
        job_id="security-scan",
        step_name="Upload Trivy scan results to GitHub Security tab",
    )

    prepare_run = str(prepare_step["run"])
    assert "rm -rf -- trivy-results.sarif" in prepare_run
    assert 'rm -rf "${RUNNER_TEMP}/pulseplate-trivy"' in prepare_run
    assert 'mkdir -p "${RUNNER_TEMP}/pulseplate-trivy"' in prepare_run
    assert scanner_step["with"]["exit-code"] == "1"
    assert scanner_step.get("continue-on-error") is None
    assert scanner_step["with"]["output"] == (
        "${{ runner.temp }}/pulseplate-trivy/trivy-results.sarif"
    )

    sarif_check_run = str(sarif_check_step["run"])
    assert sarif_check_step["id"] == "trivy_fs_sarif"
    assert sarif_check_step["if"] == "${{ always() }}"
    assert 'sarif_path="${RUNNER_TEMP}/pulseplate-trivy/trivy-results.sarif"' in sarif_check_run
    assert 'if [ -s "$sarif_path" ]; then' in sarif_check_run
    assert 'cp -- "$sarif_path" trivy-results.sarif' in sarif_check_run
    assert 'echo "present=true" >> "${GITHUB_OUTPUT}"' in sarif_check_run
    assert 'echo "present=false" >> "${GITHUB_OUTPUT}"' in sarif_check_run

    assert upload_step["if"] == (
        "${{ always() && steps.trivy_fs_sarif.outputs.present == 'true' }}"
    )
    assert upload_step["uses"].startswith("github/codeql-action/upload-sarif@")
    assert upload_step["continue-on-error"] is True
    assert upload_step["with"]["sarif_file"] == "trivy-results.sarif"


def test_active_upload_artifact_refs_all_use_node24_sha() -> None:
    """Guard every active upload-artifact use, not only historically touched workflows."""

    expected_uses = f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}"
    expected_line = f"{expected_uses} # v7.0.1 / Node 24"
    observed_upload_steps: list[tuple[str, str, object]] = []

    for workflow_path in _active_workflow_paths():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow_upload_count = 0
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.startswith("actions/upload-artifact@"):
                continue
            workflow_upload_count += 1
            observed_upload_steps.append(
                (str(workflow_path.relative_to(REPO_ROOT)), job_id, step.get("name"))
            )
            assert uses == expected_uses

        if workflow_upload_count:
            assert workflow_text.count(expected_line) == workflow_upload_count

    assert observed_upload_steps


def test_active_sbom_action_refs_use_verified_v0_24_0_sha_and_preserve_contracts() -> None:
    """Guard every active SBOM action use and its fail-closed generation contract."""

    def iter_uses_source_mappings(node: Node) -> Iterator[tuple[ScalarNode, ScalarNode]]:
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if isinstance(key_node, ScalarNode) and key_node.value == "uses":
                    if isinstance(value_node, ScalarNode):
                        yield key_node, value_node
                yield from iter_uses_source_mappings(value_node)
        elif isinstance(node, SequenceNode):
            for value_node in node.value:
                yield from iter_uses_source_mappings(value_node)

    expected_uses = f"anchore/sbom-action@{SBOM_ACTION_NODE24_SHA}"
    expected_line = f"{expected_uses} # v0.24.0"
    expected_counts = {
        ".github/workflows/build.yml": 1,
        ".github/workflows/cd.yml": 3,
    }
    observed_counts: dict[str, int] = {}
    observed_contracts: list[
        tuple[str, str, object, str, object, object, object, object, object]
    ] = []

    for workflow_path in _active_workflow_paths():
        workflow_relative_path = str(workflow_path.relative_to(REPO_ROOT))
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow_lines = workflow_text.splitlines()
        workflow = _load_workflow(workflow_path)
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        assert OLD_SBOM_ACTION_SHA not in workflow_text
        workflow_document = yaml.compose(workflow_text)
        assert isinstance(workflow_document, Node)
        sbom_source_node_count = 0
        for uses_key_node, uses_value_node in iter_uses_source_mappings(workflow_document):
            uses = uses_value_node.value
            if not uses.casefold().startswith("anchore/sbom-action@"):
                continue

            sbom_source_node_count += 1
            assert uses == expected_uses
            assert workflow_lines[uses_key_node.start_mark.line].strip() == (
                f"uses: {expected_line}"
            )

        workflow_sbom_count = 0
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.casefold().startswith("anchore/sbom-action@"):
                continue

            job = jobs[job_id]
            assert isinstance(job, dict)
            workflow_sbom_count += 1
            assert uses == expected_uses
            assert "continue-on-error" not in job
            assert "if" not in step
            assert "continue-on-error" not in step
            observed_contracts.append(
                (
                    workflow_relative_path,
                    job_id,
                    step.get("name"),
                    uses,
                    step.get("with"),
                    job.get("if"),
                    job.get("continue-on-error"),
                    step.get("if"),
                    step.get("continue-on-error"),
                )
            )

        assert sbom_source_node_count == workflow_sbom_count
        if workflow_sbom_count:
            assert workflow_relative_path in expected_counts
            observed_counts[workflow_relative_path] = workflow_sbom_count

    assert observed_counts == expected_counts
    assert observed_contracts == [
        (
            ".github/workflows/build.yml",
            "publish",
            "Generate SBOM",
            expected_uses,
            {
                "image": "${{ steps.image-ref.outputs.ref }}",
                "format": "spdx-json",
                "output-file": "sbom.spdx.json",
            },
            "github.event_name != 'pull_request'",
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Generate staged backend image SBOM",
            expected_uses,
            {
                "image": (
                    "${{ env.REGISTRY }}/${{ steps.image-name.outputs.image_name }}"
                    "@${{ steps.build.outputs.digest }}"
                ),
                "format": "spdx-json",
                "output-file": "backend-image-sbom.spdx.json",
            },
            "github.ref == 'refs/heads/main'",
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Generate staged Caddy image SBOM",
            expected_uses,
            {
                "image": (
                    "${{ env.REGISTRY }}/${{ steps.image-name.outputs.image_name }}"
                    "@${{ steps.build-caddy.outputs.digest }}"
                ),
                "format": "spdx-json",
                "output-file": "caddy-image-sbom.spdx.json",
            },
            "github.ref == 'refs/heads/main'",
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build-production",
            "Generate production image SBOM",
            expected_uses,
            {
                "image": (
                    "${{ env.REGISTRY }}/${{ steps.image-name.outputs.image_name }}"
                    "@${{ steps.build.outputs.digest }}"
                ),
                "format": "spdx-json",
                "output-file": "docker-image-sbom.spdx.json",
            },
            "startsWith(github.ref, 'refs/tags/v')",
            None,
            None,
            None,
        ),
    ]


def test_active_codeql_action_refs_use_verified_v4_37_1_sha() -> None:
    """Guard every active CodeQL action ref against pin and location drift."""

    def iter_uses_source_mappings(node: Node) -> Iterator[tuple[ScalarNode, ScalarNode]]:
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if isinstance(key_node, ScalarNode) and key_node.value == "uses":
                    if isinstance(value_node, ScalarNode):
                        yield key_node, value_node
                yield from iter_uses_source_mappings(value_node)
        elif isinstance(node, SequenceNode):
            for value_node in node.value:
                yield from iter_uses_source_mappings(value_node)

    expected_uses_by_component = {
        "init": f"github/codeql-action/init@{CODEQL_ACTION_V4_37_1_SHA}",
        "analyze": f"github/codeql-action/analyze@{CODEQL_ACTION_V4_37_1_SHA}",
        "upload-sarif": f"github/codeql-action/upload-sarif@{CODEQL_ACTION_V4_37_1_SHA}",
    }
    expected_comment_counts_by_component = {
        "init": 1,
        "analyze": 1,
        "upload-sarif": 3,
    }
    expected_line_counts = {
        BUILD_WORKFLOW_PATH: {
            f"uses: {expected_uses_by_component['upload-sarif']} # v4.37.1": 2,
        },
        CODEQL_WORKFLOW_PATH: {
            f"uses: {expected_uses_by_component['init']} # v4.37.1": 1,
            f"uses: {expected_uses_by_component['analyze']} # v4.37.1": 1,
        },
        TRIVY_WORKFLOW_PATH: {
            f"uses: {expected_uses_by_component['upload-sarif']} # v4.37.1": 1,
        },
    }
    observed_contracts: list[tuple[str, str, object, str]] = []
    observed_comment_counts_by_component = {
        component: 0 for component in expected_comment_counts_by_component
    }

    for workflow_path in _active_workflow_paths():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow_lines = workflow_text.splitlines()
        expected_source_line_counts = expected_line_counts.get(workflow_path, {})
        observed_source_line_counts = {
            expected_line: 0 for expected_line in expected_source_line_counts
        }
        workflow_document = yaml.compose(workflow_text)
        assert isinstance(workflow_document, Node)
        for uses_key_node, uses_value_node in iter_uses_source_mappings(workflow_document):
            uses = uses_value_node.value
            normalized_uses = uses.casefold()
            if not normalized_uses.startswith("github/codeql-action/"):
                continue

            assert uses.startswith("github/codeql-action/")
            component = normalized_uses.removeprefix("github/codeql-action/").split(
                "@", maxsplit=1
            )[0]
            assert component in expected_uses_by_component
            observed_comment_counts_by_component[component] += 1
            expected_line = f"uses: {uses} # v4.37.1"
            assert workflow_lines[uses_key_node.start_mark.line].strip() == expected_line
            if expected_line in observed_source_line_counts:
                observed_source_line_counts[expected_line] += 1

        assert observed_source_line_counts == expected_source_line_counts

        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str):
                continue
            normalized_uses = uses.casefold()
            if not normalized_uses.startswith("github/codeql-action/"):
                continue

            assert uses.startswith("github/codeql-action/")
            component = normalized_uses.removeprefix("github/codeql-action/").split(
                "@", maxsplit=1
            )[0]
            assert component in expected_uses_by_component
            assert uses == expected_uses_by_component[component]
            observed_contracts.append(
                (
                    str(workflow_path.relative_to(REPO_ROOT)),
                    job_id,
                    step.get("name"),
                    uses,
                )
            )

    assert observed_comment_counts_by_component == expected_comment_counts_by_component
    assert observed_contracts == [
        (
            ".github/workflows/build.yml",
            "security-scan",
            "Upload Trivy scan results to GitHub Security tab",
            expected_uses_by_component["upload-sarif"],
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Upload Trivy image scan results",
            expected_uses_by_component["upload-sarif"],
        ),
        (
            ".github/workflows/codeql.yml",
            "analyze",
            "Initialize CodeQL",
            expected_uses_by_component["init"],
        ),
        (
            ".github/workflows/codeql.yml",
            "analyze",
            "Perform CodeQL Analysis",
            expected_uses_by_component["analyze"],
        ),
        (
            ".github/workflows/trivy.yml",
            "build",
            "Upload Trivy scan results to GitHub Security tab",
            expected_uses_by_component["upload-sarif"],
        ),
    ]


def test_node24_setup_go_and_upload_artifact_pins_preserve_workflow_contracts() -> None:
    """Guard direct Node 20 setup/upload action migrations in touched workflows."""

    expected_action_lines = {
        BUILD_WORKFLOW_PATH: {
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA} # v7.0.1 / Node 24": 4,
        },
        GREENLIGHT_IOS_WORKFLOW_PATH: {
            f"actions/setup-go@{SETUP_GO_NODE24_SHA} # v6.4.0 / Node 24": 1,
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA} # v7.0.1 / Node 24": 1,
        },
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH: {
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA} # v7.0.1 / Node 24": 1,
        },
        SECURITY_WORKFLOW_PATH: {
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA} # v7.0.1 / Node 24": 1,
        },
    }
    for workflow_path, expected_counts in expected_action_lines.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for expected_line, expected_count in expected_counts.items():
            assert workflow_text.count(expected_line) == expected_count

    observed_contracts = []
    for workflow_path in (
        BUILD_WORKFLOW_PATH,
        GREENLIGHT_IOS_WORKFLOW_PATH,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH,
        SECURITY_WORKFLOW_PATH,
    ):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str):
                continue
            if not (
                uses.startswith("actions/setup-go@") or uses.startswith("actions/upload-artifact@")
            ):
                continue
            observed_contracts.append(
                (
                    str(workflow_path.relative_to(REPO_ROOT)),
                    job_id,
                    step.get("name"),
                    uses,
                    step.get("with"),
                    step.get("if"),
                    step.get("env"),
                    step.get("continue-on-error"),
                )
            )

    assert observed_contracts == [
        (
            ".github/workflows/build.yml",
            "build",
            "Upload Docker telemetry artifact",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "docker-image-telemetry-build",
                "path": (
                    "docker-runtime-dependency-surface.json\n"
                    "docker-image-telemetry.json\n"
                    "docker-image-telemetry.md\n"
                ),
                "if-no-files-found": "warn",
                "retention-days": 14,
            },
            "${{ always() }}",
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "build",
            "Upload Docker budget check artifact",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "docker-image-budget-check-build",
                "path": "docker-image-budget-check.json\ndocker-image-budget-check.md\n",
                "if-no-files-found": "warn",
                "retention-days": 14,
            },
            "${{ always() }}",
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Upload release-control-plane build digest sources",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "release-control-plane-build-sources",
                "path": (
                    "release-control-plane-build-sources/artifact_digest.txt\n"
                    "release-control-plane-build-sources/sbom_digest.txt\n"
                    "release-control-plane-build-sources/attestation_check_digest.txt\n"
                    "release-control-plane-build-sources/provenance_digest.txt\n"
                    "release-control-plane-build-sources/attestation_status.txt\n"
                ),
                "if-no-files-found": "error",
                "retention-days": 14,
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Upload SBOM",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {"name": "sbom", "path": "sbom.spdx.json", "retention-days": 30},
            None,
            None,
            None,
        ),
        (
            ".github/workflows/greenlight-ios.yml",
            "greenlight-ios",
            "Setup Go",
            f"actions/setup-go@{SETUP_GO_NODE24_SHA}",
            {"go-version": "1.24"},
            None,
            None,
            None,
        ),
        (
            ".github/workflows/greenlight-ios.yml",
            "greenlight-ios",
            "Upload Greenlight report artifact",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "greenlight-ios-report",
                "path": "greenlight-report.json",
                "if-no-files-found": "error",
            },
            "always()",
            None,
            None,
        ),
        (
            ".github/workflows/ios-appstore-assets.yml",
            "validate-assets",
            "Upload screenshot artifacts",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "ios-appstore-screenshots",
                "path": "ios/fastlane/screenshots",
                "if-no-files-found": "warn",
            },
            "always()",
            None,
            None,
        ),
        (
            ".github/workflows/security.yml",
            "bandit",
            "Upload security reports",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "security-reports",
                "path": ("bandit-report.json\npip-audit-*.json\n"),
                "if-no-files-found": "ignore",
            },
            "always()",
            None,
            None,
        ),
    ]


def test_node24_artifact_migration_preserves_download_contracts() -> None:
    """Guard artifact names, paths, and merge behavior during action runtime bumps."""

    expected_download_contracts = [
        (
            ".github/workflows/ci.yml",
            "coverage-pr",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "diff-coverage",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            None,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-feature",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.11)",
            {"name": "coverage-main-xml-3.11", "path": "./coverage-artifacts/3.11"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.12)",
            {"name": "coverage-main-xml-3.12", "path": "./coverage-artifacts/3.12"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.13)",
            {"name": "coverage-main-xml-3.13", "path": "./coverage-artifacts/3.13"},
            True,
        ),
        (
            ".github/workflows/codecov-upload.yml",
            "upload",
            "Download coverage artifact",
            {"name": "${{ inputs['coverage-artifact'] }}", "path": "./coverage-artifact"},
            None,
        ),
        (
            ".github/workflows/nightly.yml",
            "coverage-merge",
            "Download coverage artifacts",
            {
                "pattern": "coverage-reports-shard-*",
                "merge-multiple": True,
                "path": "coverage-artifacts",
            },
            None,
        ),
        (
            ".github/workflows/ios-appstore-assets.yml",
            "upload-assets",
            "Download screenshot artifacts",
            {"name": "ios-appstore-screenshots", "path": "ios/fastlane/screenshots"},
            None,
        ),
    ]

    observed_download_contracts = []
    for workflow_path in (
        CI_WORKFLOW_PATH,
        CODECOV_UPLOAD_WORKFLOW_PATH,
        NIGHTLY_WORKFLOW_PATH,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH,
    ):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("actions/download-artifact@"):
                observed_download_contracts.append(
                    (
                        str(workflow_path.relative_to(REPO_ROOT)),
                        job_id,
                        step.get("name"),
                        step.get("with"),
                        step.get("continue-on-error"),
                    )
                )

    assert observed_download_contracts == expected_download_contracts


def test_node24_github_script_migration_preserves_pr_read_permissions() -> None:
    """Guard the PR automation script runtime bump against permission drift."""

    workflow = _load_workflow(PR_AUTOMATION_WORKFLOW_PATH)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    validate_pr_job = jobs["validate-pr"]
    assert isinstance(validate_pr_job, dict)

    assert validate_pr_job["permissions"] == {"pull-requests": "read"}

    github_script_steps = []
    for _job_id, step in _iter_job_steps(PR_AUTOMATION_WORKFLOW_PATH):
        uses = step.get("uses")
        if isinstance(uses, str) and uses.startswith("actions/github-script@"):
            github_script_steps.append(step)

    assert len(github_script_steps) == 1
    script_step = github_script_steps[0]
    assert script_step["uses"] == f"actions/github-script@{GITHUB_SCRIPT_NODE24_SHA}"
    with_section = script_step["with"]
    assert isinstance(with_section, dict)
    assert sorted(with_section) == ["github-token", "script"]
    assert with_section["github-token"] == "${{ secrets.GITHUB_TOKEN }}"
    assert "github.rest.pulls.get" in str(with_section["script"])


def test_feature_push_risk_profile_uses_origin_main_merge_base() -> None:
    """Feature/fix pushes must diff against origin/main merge-base."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    risk_profile_section = _extract_section(
        workflow_text,
        "      - name: Build CI risk profile",
        "\n  pr_scope_guard:",
    )

    assert "git fetch --no-tags --prune origin main" in risk_profile_section
    assert 'BASE_SHA="$(git merge-base origin/main "${GITHUB_SHA}")"' in risk_profile_section
    assert 'HEAD_SHA="${GITHUB_SHA}"' in risk_profile_section
    assert "Risk-profile diff: ${BASE_SHA}...${HEAD_SHA}" in risk_profile_section


def test_feature_push_branches_include_feature_prefix() -> None:
    workflow = _load_ci_workflow()
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)
    push_section = on_section["push"]
    assert isinstance(push_section, dict)
    push_branches = push_section["branches"]
    assert isinstance(push_branches, list)

    assert {"main", "feat/**", "fix/**", "feature/**"}.issubset(set(push_branches))
    representative_branches = (
        "main",
        "feat/design-accessibility-regression-decision-gate",
        "fix/ci-github-token-format-and-run-diagnostics",
        "feature/example",
    )
    for branch in representative_branches:
        assert any(fnmatch.fnmatchcase(branch, pattern) for pattern in push_branches)


def test_feature_push_jobs_use_changes_gate_and_smoke_risk_topology() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    feature_push_tokens = (
        "github.event_name == 'push'",
        "refs/heads/feat/",
        "refs/heads/fix/",
        "refs/heads/feature/",
    )

    test_feature = jobs["test-feature"]
    assert isinstance(test_feature, dict)
    test_feature_needs = test_feature["needs"]
    assert isinstance(test_feature_needs, list)
    assert "changes" in test_feature_needs
    test_feature_if = test_feature["if"]
    assert isinstance(test_feature_if, str)
    _assert_contains_all_tokens(test_feature_if, feature_push_tokens)
    assert "needs.changes.outputs.run_backend_blocking == 'true'" in test_feature_if
    feature_step_names = [step.get("name") for step in test_feature["steps"]]
    assert "Critical smoke (deterministic merge blocker)" in feature_step_names
    assert "Contract and risk suites" in feature_step_names
    assert "Finalize coverage artifacts" in feature_step_names
    assert "Start fast-feedback timing" in feature_step_names
    assert "Summarize fast-feedback budget" in feature_step_names
    assert "Upload fast-feedback budget artifact" in feature_step_names
    test_feature_env = test_feature["env"]
    assert isinstance(test_feature_env, dict)
    assert test_feature_env["FEATURE_FEEDBACK_TARGET_MINUTES"] == "45"

    coverage_feature = jobs["coverage-feature"]
    assert isinstance(coverage_feature, dict)
    coverage_feature_needs = coverage_feature["needs"]
    assert isinstance(coverage_feature_needs, list)
    assert "changes" in coverage_feature_needs
    assert "test-feature" in coverage_feature_needs
    coverage_feature_if = coverage_feature["if"]
    assert isinstance(coverage_feature_if, str)
    _assert_contains_all_tokens(coverage_feature_if, feature_push_tokens)
    assert "needs.changes.outputs.run_backend_blocking == 'true'" in coverage_feature_if
    coverage_feature_step_names = [step.get("name") for step in coverage_feature["steps"]]
    assert (
        "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})"
        in coverage_feature_step_names
    )
    assert "Upload to Codecov" in coverage_feature_step_names


def test_ci_changes_outputs_cover_risk_profile_outputs() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    changes = jobs["changes"]
    assert isinstance(changes, dict)
    outputs = changes["outputs"]
    assert isinstance(outputs, dict)

    risk_output_keys = set(ci_risk_profile.build_risk_profile([]).to_outputs())

    assert risk_output_keys.issubset(outputs)
    assert (
        outputs["operator_plane_slack"] == "${{ steps.risk_profile.outputs.operator_plane_slack }}"
    )


def test_contract_risk_suite_blocks_stay_in_sync_and_cover_required_targets() -> None:
    workflow = _load_ci_workflow()
    test_pr_groups = _contract_suite_targets_by_group(workflow, job_id="test-pr")
    test_feature_groups = _contract_suite_targets_by_group(workflow, job_id="test-feature")
    expected_slack_operator_targets = (
        "tests/test_ci_risk_profile.py",
        "tests/test_ci_workflow_pr_size_governance_contract.py",
        "tests/test_experiment_operator_ledger.py",
        "tests/test_experiment_slack_kpp_renderer.py",
        "tests/test_experiment_slack_socket_bridge.py",
        "tests/test_runtime_toolchain_alignment.py",
    )

    assert test_pr_groups == test_feature_groups
    assert "tests/test_admin_scheduler_access.py" in test_pr_groups["food_catalog"]
    assert "tests/test_scheduler_final_coverage.py" in test_pr_groups["food_catalog"]
    assert "tests/test_admin_scheduler_access.py" in test_feature_groups["food_catalog"]
    assert "tests/test_scheduler_final_coverage.py" in test_feature_groups["food_catalog"]
    assert set(ci_risk_profile.ALL_RISK_GROUPS).issubset(test_pr_groups)
    assert test_pr_groups["operator_plane_slack"] == expected_slack_operator_targets
    assert "tests/test_bmi_compat_router.py" in test_pr_groups["route_contract_safety"]
    assert "tests/test_api_key_dependency_ownership.py" in test_pr_groups["route_contract_safety"]
    assert "tests/test_lenient_mode_warning.py" in test_pr_groups["route_contract_safety"]
    assert "tests/test_legacy_bmi_shims.py" in test_pr_groups["route_contract_safety"]
    assert (
        "tests/test_legacy_premium_weekly_plan_registration_bootstrap.py"
        in test_pr_groups["route_contract_safety"]
    )
    assert (
        "tests/test_legacy_weekly_menu_builder_access.py" in test_pr_groups["route_contract_safety"]
    )
    assert "tests/test_legacy_weekly_plan_alias_api.py" in test_pr_groups["route_contract_safety"]
    assert "tests/test_route_family_bootstrap.py" in test_pr_groups["route_contract_safety"]


def test_contract_risk_suites_use_bounded_coverage_batches() -> None:
    workflow = _load_ci_workflow()
    for job_id in ("test-pr", "test-feature"):
        step = _job_step_by_name(
            workflow,
            job_id=job_id,
            step_name="Contract and risk suites",
        )
        run_script = step["run"]
        assert isinstance(run_script, str)
        assert "contract_batch_size=24" in run_script
        assert "for ((batch_start=0;" in run_script
        assert "batch_targets=(" in run_script
        assert "python -m coverage run --append -m pytest -q" in run_script
        assert "-p no:xdist" in run_script
        assert '"${batch_targets[@]}"' in run_script
        assert '--junitxml="${junit_path}"' in run_script

        upload_step = _job_step_by_name(
            workflow,
            job_id=job_id,
            step_name="Upload JUnit test report",
        )
        upload_with = upload_step["with"]
        assert isinstance(upload_with, dict)
        assert "tests/contract-results*.xml" in str(upload_with["path"])


def test_ci_workflow_declares_canonical_main_and_feature_push_jobs() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    required_job_ids = {
        "changes",
        "lint",
        "security",
        "test-feature",
        "coverage-feature",
        "test-main",
        "coverage-main",
        "diff-coverage",
    }
    assert required_job_ids <= set(jobs)
    for job_id in required_job_ids:
        job = jobs[job_id]
        assert isinstance(job, dict)
        assert "runs-on" in job or "uses" in job

    test_main = jobs["test-main"]
    assert isinstance(test_main, dict)
    assert "github.ref == 'refs/heads/main'" in str(test_main["if"])

    coverage_main = jobs["coverage-main"]
    assert isinstance(coverage_main, dict)
    assert coverage_main["needs"] == "test-main"
    assert "github.ref == 'refs/heads/main'" in str(coverage_main["if"])


def test_feature_push_fast_feedback_budget_is_warning_only_evidence() -> None:
    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    test_feature_section = _extract_job_section(workflow_text, "  test-feature:")

    assert "Feature/fix fast-feedback exceeded" in test_feature_section
    assert "::warning::Feature/fix fast-feedback exceeded" in test_feature_section
    assert "Fast-feedback timing seed is missing" in test_feature_section
    assert 'status="timing_unavailable"' in test_feature_section
    assert "elapsed_seconds=-1" in test_feature_section
    assert "FEATURE_FEEDBACK_STARTED_AT:-$(date +%s)" not in test_feature_section
    assert "feature-feedback-budget.json" in test_feature_section
    assert "feature-feedback-budget-${{ env.PYTHON_VERSION }}" in test_feature_section
    assert "if-no-files-found: error" in test_feature_section


def test_feature_branch_alias_stays_in_sync_for_ios_push_jobs() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    ios_routing_tokens = (
        "github.event_name == 'pull_request'",
        "refs/heads/feat/",
        "refs/heads/fix/",
        "refs/heads/feature/",
        "refs/heads/main",
    )

    ios_tests = jobs["ios-tests"]
    assert isinstance(ios_tests, dict)
    ios_tests_if = ios_tests["if"]
    assert isinstance(ios_tests_if, str)
    _assert_contains_all_tokens(ios_tests_if, ios_routing_tokens)

    ios_ui_smoke = jobs["ios-ui-smoke"]
    assert isinstance(ios_ui_smoke, dict)
    ios_ui_smoke_if = ios_ui_smoke["if"]
    assert isinstance(ios_ui_smoke_if, str)
    _assert_contains_all_tokens(ios_ui_smoke_if, ios_routing_tokens)


def test_ios_unit_tests_stay_in_blocking_ios_job() -> None:
    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    ios_tests_section = _extract_job_section(workflow_text, "  ios-tests:")
    ios_ui_smoke_section = _extract_job_section(workflow_text, "  ios-ui-smoke:")

    assert 'ONLY_TESTING="$(../scripts/ios_test_targets.sh)"' in ios_tests_section
    assert "::error::ONLY_TESTING is empty" in ios_tests_section
    assert "no test targets were found" in ios_tests_section
    assert '"xcodebuild", "test-without-building"' in ios_tests_section
    assert 'ONLY_TESTING="$(../scripts/ios_test_targets.sh)"' not in ios_ui_smoke_section


def test_machine_heavy_local_verify_deferral_contract_is_documented() -> None:
    agents_text = AGENTS_PATH.read_text(encoding="utf-8")
    runbook_text = RUNBOOK_PATH.read_text(encoding="utf-8")
    contract_text = ORCHESTRATION_CONTRACT_PATH.read_text(encoding="utf-8")

    required_tokens = (
        "Machine-heavy PR exception",
        "operator-approved",
        "`make verify` by default",
        "canonical current-head CI parity",
        "`lint`",
        "required/current-head checks",
        "relevant `test-main` matrix",
        "`diff-coverage`",
        "≥97%",
        "security/governance checks",
        "`check_merge_ready.py --require-auth`",
        "`make validate-changed`",
        "`pre-commit run --all-files`",
    )
    _assert_contains_all_tokens(agents_text, required_tokens)

    runbook_tokens = (
        "Machine-heavy CI/tooling PRs",
        "operator explicitly defers full local",
        "canonical current-head CI parity",
        "`lint`",
        "required/current-head checks",
        "relevant `test-main` matrix",
        "`diff-coverage` at ≥97%",
        "security/governance checks",
        "`check_merge_ready.py --require-auth`",
        "documented narrow bundle",
    )
    _assert_contains_all_tokens(runbook_text, runbook_tokens)

    contract_tokens = (
        "Operator-approved machine-heavy deferral",
        "fixed mapping document the deferral",
        "canonical current-head CI parity is green",
        "relevant `test-main` matrix",
        "`diff-coverage` ≥97%",
        "security/governance checks",
    )
    _assert_contains_all_tokens(contract_text, contract_tokens)


def test_ci_lint_all_files_pre_commit_uses_full_history_checkout() -> None:
    workflow = _load_ci_workflow()

    checkout_step = _job_step_by_name(workflow, job_id="lint", step_name="Checkout")
    assert checkout_step["uses"] == f"actions/checkout@{CHECKOUT_NODE24_SHA}"
    assert checkout_step["with"]["fetch-depth"] == 0

    pre_commit_step = _job_step_by_name(
        workflow,
        job_id="lint",
        step_name="Pre-commit (lint/format/security quick checks)",
    )
    assert "pre-commit run --all-files" in pre_commit_step["run"]


def test_ci_lint_all_files_pre_commit_uses_project_node_version() -> None:
    workflow = _load_ci_workflow()

    setup_node_step = _job_step_by_name(workflow, job_id="lint", step_name="Setup Node.js")
    assert setup_node_step["uses"] == f"actions/setup-node@{SETUP_NODE_NODE24_SHA}"
    assert setup_node_step["with"]["node-version-file"] == "${{ env.FRONTEND_NODE_VERSION_FILE }}"

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    lint_steps = jobs["lint"]["steps"]
    step_names = [step.get("name") for step in lint_steps]
    assert step_names.index("Setup Node.js") < step_names.index(
        "Pre-commit (lint/format/security quick checks)"
    )


def test_main_branch_python_sharded_runner_preserves_required_check_policy() -> None:
    workflow = _load_ci_workflow()
    workflow_env = workflow["env"]
    assert workflow_env["PULSEPLATE_PYTHON_INDEX_URL"] == "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
    assert (
        workflow_env["PULSEPLATE_PYTHON_TRUSTED_HOST"]
        == "${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
    )

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    test_main = jobs["test-main"]
    assert isinstance(test_main, dict)
    test_main_needs = test_main["needs"]
    assert isinstance(test_main_needs, list)
    assert "changes" in test_main_needs
    test_main_if = test_main["if"]
    assert isinstance(test_main_if, str)
    assert "github.ref == 'refs/heads/main'" in test_main_if
    assert "needs.changes.outputs.run_main_ci_diagnostic == 'true'" in test_main_if

    permissions = test_main["permissions"]
    assert permissions == {"contents": "read", "actions": "read"}

    test_main_env = test_main["env"]
    assert test_main_env == {
        "PULSEPLATE_PYTHON_INDEX_URL": "",
        "PULSEPLATE_PYTHON_TRUSTED_HOST": "",
    }

    steps = test_main["steps"]
    assert isinstance(steps, list)
    step_names = [step["name"] for step in steps]
    assert step_names.index("Resolve PR diagnostic package proxy") < step_names.index(
        "Setup Python environment"
    )
    assert step_names.index("Resolve protected package proxy") < step_names.index(
        "Setup Python environment"
    )

    pr_proxy_step = next(
        step for step in steps if step["name"] == "Resolve PR diagnostic package proxy"
    )
    assert pr_proxy_step["if"] == "github.event_name == 'pull_request'"
    assert pr_proxy_step["env"] == {
        "PULSEPLATE_PR_PYTHON_INDEX_URL": "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}",
        "PULSEPLATE_PR_PYTHON_TRUSTED_HOST": ("${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"),
    }
    pr_proxy_script = pr_proxy_step["run"]
    assert "secrets." not in pr_proxy_script
    assert "PULSEPLATE_PR_PYTHON_INDEX_URL" in pr_proxy_script
    assert 'if [[ -z "$resolved_index" ]]; then' in pr_proxy_script
    assert "credential-free diagnostic package proxy" in pr_proxy_script
    assert "must be credential-free" in pr_proxy_script
    assert "*://*@*)" in pr_proxy_script
    assert "DEVPI_CI_USER/DEVPI_CI_PASSWORD" in pr_proxy_script
    assert "exit 1" in pr_proxy_script
    assert "*$'\\n'*|*$'\\r'*)" in pr_proxy_script
    assert "must be single-line values" in pr_proxy_script
    assert "$GITHUB_ENV" in pr_proxy_script

    protected_proxy_step = next(
        step for step in steps if step["name"] == "Resolve protected package proxy"
    )
    assert protected_proxy_step["if"] == "github.event_name != 'pull_request'"
    assert protected_proxy_step["env"] == {
        "PULSEPLATE_PROTECTED_PYTHON_INDEX_URL": "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}",
        "PULSEPLATE_PROTECTED_PYTHON_TRUSTED_HOST": ("${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"),
    }
    protected_proxy_script = protected_proxy_step["run"]
    assert "PULSEPLATE_PROTECTED_PYTHON_INDEX_URL" in protected_proxy_script
    assert 'if [[ -z "$resolved_index" ]]; then' in protected_proxy_script
    assert "Set PULSEPLATE_PYTHON_INDEX_URL repository variable" in protected_proxy_script
    assert "exit 1" in protected_proxy_script
    assert "*://*@*)" in protected_proxy_script
    assert "PULSEPLATE_PYTHON_INDEX_URL must be credential-free" in protected_proxy_script
    assert "DEVPI_CI_USER/DEVPI_CI_PASSWORD" in protected_proxy_script
    assert "*$'\\n'*|*$'\\r'*)" in protected_proxy_script
    assert "must be single-line values" in protected_proxy_script
    assert "$GITHUB_ENV" in protected_proxy_script

    setup_python_step = next(step for step in steps if step["name"] == "Setup Python environment")
    assert setup_python_step["env"] == {
        "DEVPI_CI_USER": "${{ github.event_name != 'pull_request' && secrets.DEVPI_CI_USER || '' }}",
        "DEVPI_CI_PASSWORD": (
            "${{ github.event_name != 'pull_request' && secrets.DEVPI_CI_PASSWORD || '' }}"
        ),
    }

    matrix = test_main["strategy"]["matrix"]["include"]
    assert isinstance(matrix, list)

    timeouts = {entry["python-version"]: entry["timeout-minutes"] for entry in matrix}
    assert timeouts == {"3.11": 60, "3.12": 90, "3.13": 90}

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    test_main_section = _extract_job_section(workflow_text, "  test-main:")
    assert "https://pypi.org/simple" not in test_main_section
    assert "pypi.org" not in test_main_section
    assert (
        "python-version: ${{ matrix.python-version == '3.13' && env.PYTHON_VERSION || "
        "matrix.python-version }}"
    ) in test_main_section

    py311_block = _extract_shell_conditional_block(
        test_main_section,
        'if [[ "$PYVER" == 3.11* ]]; then',
        '          elif [[ "$PYVER" == 3.12* ]]; then',
    )
    py312_block = _extract_shell_conditional_block(
        test_main_section,
        '          elif [[ "$PYVER" == 3.12* ]]; then',
        '          elif [[ "$PYVER" == 3.13* ]]; then',
    )
    py313_block = _extract_shell_conditional_block(
        test_main_section,
        '          elif [[ "$PYVER" == 3.13* ]]; then',
        "          else",
    )
    default_block = _extract_shell_conditional_block(
        test_main_section,
        "          else",
        "          fi",
    )
    shared_shard_runner_block = _extract_shell_conditional_block(
        test_main_section,
        '          if [[ -n "${MAIN_TEST_SHARDS:-}" ]]; then',
        '          echo "PYTEST_XDIST_ARGS=${PYTEST_XDIST_ARGS[*]}"',
    )

    assert "MAIN_TEST_SHARDS=4" in py311_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py311_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py311_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py311_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py311_block

    assert "MAIN_TEST_SHARDS=16" in py312_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py312_block
    assert "export MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800" in py312_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py312_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py312_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py312_block
    assert "TEST_STEP_STARTED_AT=" in test_main_section
    assert "TEST_STEP_FINISHED_AT=" in shared_shard_runner_block

    assert "MAIN_TEST_SHARDS=8" in py313_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py313_block
    assert "export MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800" in py313_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py313_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py313_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py313_block

    assert "python scripts/ci/run_main_test_shards.py" in shared_shard_runner_block
    assert '--python-version "${PYVER}"' in shared_shard_runner_block
    assert '--shard-count "${MAIN_TEST_SHARDS}"' in shared_shard_runner_block
    assert '--max-parallel "${MAIN_TEST_MAX_PARALLEL}"' in shared_shard_runner_block
    assert 'echo "MAIN_TEST_SHARDS=${MAIN_TEST_SHARDS}"' in shared_shard_runner_block
    assert 'echo "MAIN_TEST_MAX_PARALLEL=${MAIN_TEST_MAX_PARALLEL}"' in shared_shard_runner_block
    assert (
        'echo "MAIN_TEST_SHARD_TIMEOUT_SECONDS=${MAIN_TEST_SHARD_TIMEOUT_SECONDS:-default}"'
        in shared_shard_runner_block
    )
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in shared_shard_runner_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in shared_shard_runner_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in shared_shard_runner_block

    assert '-m "not slow"' in test_main_section
    assert '-m "not serial and not slow"' not in test_main_section
    assert '-m "serial and not slow"' not in test_main_section
    assert "--cov-append" not in test_main_section
    assert "tests/results-serial.xml" not in test_main_section
    assert "tests/results-py312-shard-*.xml" in test_main_section
    assert "tests/results-py313-shard-*.xml" in test_main_section
    assert (
        "name: coverage-main-xml-${{ matrix.python-version }}\n"
        "          path: coverage.xml\n"
        "          if-no-files-found: ignore\n"
        "          overwrite: true"
    ) in test_main_section
    assert (
        "name: junit-main-${{ matrix.python-version }}\n"
        "          path: |\n"
        "            tests/results.xml\n"
        "            tests/results-py311-shard-*.xml\n"
        "            tests/results-py312-shard-*.xml\n"
        "            tests/results-py313-shard-*.xml\n"
        "          if-no-files-found: ignore\n"
        "          overwrite: true"
    ) in test_main_section
    coverage_main_section = _extract_job_section(workflow_text, "  coverage-main:")
    assert "name: coverage-main-xml-3.11" in coverage_main_section
    assert "name: coverage-main-xml-3.12" in coverage_main_section
    assert "name: coverage-main-xml-3.13" in coverage_main_section

    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" in default_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in default_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in default_block


def test_python_test_jobs_install_frontend_dependencies_before_pytest() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    for job_name in PYTHON_TEST_JOB_NAMES:
        steps = jobs[job_name]["steps"]
        step_names = [step.get("name") for step in steps]
        root_index = step_names.index("Install root Node dependencies")
        frontend_index = step_names.index("Install frontend dependencies")
        clean_index = step_names.index("Clean Python cache")

        root_step = steps[root_index]
        frontend_step = steps[frontend_index]
        assert root_step["uses"] == "./.github/actions/npm-ci-with-retry"
        assert root_step["with"]["working-directory"] == "."
        assert frontend_step["uses"] == "./.github/actions/npm-ci-with-retry"
        assert frontend_step["with"]["working-directory"] == "frontend"
        assert root_index < frontend_index < clean_index
