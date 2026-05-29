#!/usr/bin/env python3
"""Shared Slack-safe redaction helpers for Experiment Runner seams.

RU: Единый источник истины (SoT) для редэкции текста перед отправкой в Slack.
Используется bridge, notify, и KPP renderer. Любое изменение редэкционной логики
должно происходить только здесь.
EN: Single source of truth for text redaction before Slack display. Used by
bridge, notify, and KPP renderer. Any redaction logic changes must happen only
here.
"""

from __future__ import annotations

import re
from typing import Any

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_SECRET_SHAPED_RE = re.compile(
    r"(xapp-[A-Za-z0-9-]{10,}|xox[abcprs]-[A-Za-z0-9-]{10,}|"
    r"gh[pousr]_[A-Za-z0-9._-]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{10,}|sk-[A-Za-z0-9_-]{12,})",
    re.IGNORECASE,
)
SLACK_IDENTIFIER_RE = re.compile(r"\b[ACDEGTUW][A-Z0-9]{7,}\b")
# Backward-compat alias used by legacy bridge imports before extraction.
_SLACK_IDENTIFIER_RE = SLACK_IDENTIFIER_RE
_SLACK_MENTION_RE = re.compile(r"<[@#!]?[A-Z0-9][A-Z0-9_-]{1,79}(?:\|[^>]+)?>")
LOCAL_PATH_RE = re.compile(
    r"(^|\s)(/(?:Users|home|var|opt|tmp|private|Volumes|etc|usr|Library|System)/[^\s]+|"
    r"\.{1,2}/[^\s]+|[A-Za-z]:\\[^\s]+|\\\\[^\s]+)"
)
# Backward-compat alias used by legacy bridge imports before extraction.
_LOCAL_PATH_RE = LOCAL_PATH_RE
_PATCH_MARKER_RE = re.compile(
    r"(diff\s+--git|^@@\s|^\+\+\+\s|^---\s|raw\s+patch|patch\s+text|"
    r"oracle\s+stdout|oracle\s+stderr|raw\s+stdout|raw\s+stderr|"
    r"stdout\s*:|stderr\s*:)",
    re.IGNORECASE,
)
SAFE_ARTIFACT_REF_PREFIXES = (
    "artifacts/orchestration/experiments/",
    "docs/audit/",
    "docs/orchestration/",
    "docs/review/",
    "docs/roadmap/",
    "scripts/orchestration/",
    "tests/",
)
_SAFE_ARTIFACT_HASH_RE = re.compile(r"^[A-Fa-f0-9]{8,64}$")


def slack_text(value: Any, *, limit: int = 240) -> str:
    """Escape untrusted values for Slack mrkdwn-ish display.

    Removes control characters, secrets, Slack identifiers, local paths,
    patch markers, and escapes HTML/meta characters. Truncates to *limit*.

    RU: Единая функция редэкции для всех Experiment Runner Slack seams.
    EN: Unified redaction function for all Experiment Runner Slack seams.
    """
    text = _CONTROL_CHAR_RE.sub(" ", str(value)).strip()
    text = _SECRET_SHAPED_RE.sub("[redacted-secret]", text)
    text = _SLACK_MENTION_RE.sub("[redacted-slack-id]", text)
    text = _SLACK_IDENTIFIER_RE.sub("[redacted-slack-id]", text)
    text = LOCAL_PATH_RE.sub(r"\1[redacted-path]", text)
    text = _PATCH_MARKER_RE.sub("[redacted-log]", text)
    # Note: we intentionally do NOT HTML-escape & < > here. Slack Block Kit JSON
    # handles its own escaping via json.dumps; bridge as_text() outputs plain
    # mrkdwn where these characters are literal. HTML escaping here caused
    # self-redaction of copy text (e.g. "&" became "&amp;" in the final payload).
    # Backticks are sanitized to prevent breaking inline code formatting in mrkdwn.
    text = text.replace("`", "'")
    text = re.sub(r"@(here|channel|everyone)\b", "@[redacted-mention]", text, flags=re.I)
    if not text:
        text = "none"
    if len(text) > limit:
        text = text[: limit - 17].rstrip() + " [truncated=true]"
    return text


def safe_artifact_ref(value: Any) -> str:
    """Redact an artifact reference to a safe display string.

    Returns a relative path or short hash string; strips absolute paths and
    secrets.
    """
    text = str(value).strip()
    text = _CONTROL_CHAR_RE.sub("", text)
    if not text:
        return "none"
    if _SECRET_SHAPED_RE.search(text):
        return "[redacted-ref]"
    if any(char.isspace() or char in "`'\"<>|;&" for char in text):
        return "[redacted-ref]"

    normalized = text.replace("\\", "/")
    if (
        normalized.startswith("/")
        or normalized.startswith("../")
        or normalized.startswith("./../")
        or "/../" in normalized
        or normalized in {".", ".."}
        or re.match(r"^[A-Za-z]:", text)
        or text.startswith("\\\\")
    ):
        return "[redacted-ref]"

    normalized = normalized.removeprefix("./")
    if _SAFE_ARTIFACT_HASH_RE.fullmatch(normalized):
        return normalized[:16]
    if any(normalized.startswith(prefix) for prefix in SAFE_ARTIFACT_REF_PREFIXES):
        return normalized
    return "[redacted-ref]"


def safe_hash(value: Any) -> str:
    """Extract a short hash prefix for audit display."""
    text = str(value).strip()
    text = _CONTROL_CHAR_RE.sub("", text)
    text = _SECRET_SHAPED_RE.sub("[redacted-secret]", text)
    if not text:
        return "none"
    return text[:16]
