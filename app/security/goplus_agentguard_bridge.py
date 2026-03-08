"""Bridge to the verified GoPlus AgentGuard Node package.

RU: Тонкий subprocess-мост к `@goplus/agentguard`, чтобы Python-сервисы могли
использовать верифицированный upstream scanner без сетевых вызовов во время
сканирования.
EN: Thin subprocess bridge to `@goplus/agentguard` so Python services can use
the verified upstream scanner without network calls during scans.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess  # nosec B404: Required for local Node bridge to verified scanner (remove-by: 2026-06-30, ref: PR-agentguard-upstream)

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


@dataclass(frozen=True)
class GoPlusAgentGuardScanResult:
    """Normalized scan result returned by the Node bridge."""

    risk_level: str
    risk_tags: tuple[str, ...]
    summary: str

    @property
    def should_block(self) -> bool:
        """Block only on relevant high-signal tags."""

        return any(tag in RELEVANT_RISK_TAGS for tag in self.risk_tags)


def scan_text_with_goplus_agentguard(
    text: str,
    *,
    filename: str = "payload.py",
) -> GoPlusAgentGuardScanResult | None:
    """Run verified GoPlus AgentGuard if local Node runtime and dependency exist."""

    node_binary = shutil.which("node")
    if node_binary is None or not AGENTGUARD_SCAN_SCRIPT.exists():
        return None

    try:
        completed = subprocess.run(  # nosec B603: Static argv with shutil.which('node') and fixed repo script path only (remove-by: 2026-06-30, ref: PR-agentguard-upstream)
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
