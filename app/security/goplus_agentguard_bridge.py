"""Bridge to the local Node-based agent guard scanner.

RU: Тонкий subprocess-мост к локальному Node-сканеру, чтобы Python-сервисы
использовали детерминированную эвристику без внешнего npm runtime path.
EN: Thin subprocess bridge to the local Node scanner so Python services can use
deterministic heuristics without an external npm runtime dependency path.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404: Required for local Node bridge to verified scanner (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTGUARD_SCAN_SCRIPT = REPO_ROOT / "tools" / "agentguard" / "scan_text.mjs"
RELEVANT_RISK_TAGS = frozenset(
    {
        "PROMPT_INJECTION",
        "OBFUSCATION",
        "SHELL_EXEC",
        "AUTO_UPDATE",
        "REMOTE_LOADER",
        "SOCIAL_ENGINEERING",
        "SUSPICIOUS_PASTE_URL",
        "TROJAN_DISTRIBUTION",
    }
)
TEST_RUNTIME_ENV = "TESTING"
PYTEST_RUNTIME_ENV = "PYTEST_CURRENT_TEST"
TEST_RUNTIME_OPT_IN_ENV = "GOPLUS_AGENTGUARD_IN_TESTS"


@dataclass(frozen=True)
class GoPlusAgentGuardScanResult:
    """Normalized scan result returned by the Node bridge.

    RU: Историческое имя сохранено ради совместимости импортов.
    EN: The legacy class name stays in place to preserve import compatibility.
    """

    risk_level: str
    risk_tags: tuple[str, ...]
    summary: str

    @property
    def should_block(self) -> bool:
        """Block only on relevant high-signal tags."""

        return any(tag in RELEVANT_RISK_TAGS for tag in self.risk_tags)


def _is_truthy(value: str | None) -> bool:
    """Interpret repo-standard boolean env flags deterministically."""

    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def scan_text_with_goplus_agentguard(
    text: str,
    *,
    filename: str = "payload.py",
) -> GoPlusAgentGuardScanResult | None:
    """Run the local Node scanner when the runtime and script are available."""

    # RU: В тестах bridge по умолчанию отключён, чтобы full suite не плодил
    # дорогие Node subprocess-вызовы на каждый guarded request.
    # EN: In tests the bridge is disabled by default so the full suite does not
    # spawn expensive Node subprocesses for every guarded request.
    if (
        _is_truthy(os.getenv(TEST_RUNTIME_ENV))
        and os.getenv(PYTEST_RUNTIME_ENV)
        and not _is_truthy(os.getenv(TEST_RUNTIME_OPT_IN_ENV))
    ):
        return None

    node_binary = shutil.which("node")
    if node_binary is None or not AGENTGUARD_SCAN_SCRIPT.exists():
        return None

    try:
        completed = subprocess.run(  # nosec B603: Static argv with shutil.which('node') and fixed repo script path only (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)
            [node_binary, str(AGENTGUARD_SCAN_SCRIPT)],
            check=False,
            capture_output=True,
            cwd=str(REPO_ROOT),
            input=json.dumps({"text": text, "filename": filename}),
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0 or not completed.stdout.strip():
        return None

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    risk_level = payload.get("risk_level")
    risk_tags = payload.get("risk_tags")
    summary = payload.get("summary")
    if not isinstance(risk_level, str) or not isinstance(summary, str):
        return None
    if not isinstance(risk_tags, list) or not all(isinstance(tag, str) for tag in risk_tags):
        return None

    return GoPlusAgentGuardScanResult(
        risk_level=risk_level,
        risk_tags=tuple(risk_tags),
        summary=summary,
    )
