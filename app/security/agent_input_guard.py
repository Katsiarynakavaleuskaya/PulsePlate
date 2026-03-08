"""Fail-closed AI input guard for prompt/command injection patterns.

RU: Защищает LLM/agent surfaces от prompt injection, command injection и
Unicode-обходов до вызова RAG, quota и provider.generate().
EN: Protects LLM/agent surfaces from prompt injection, command injection, and
Unicode-based bypasses before RAG, quota, and provider.generate().
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import cast
import unicodedata

from fastapi import HTTPException, status

from app.security.goplus_agentguard_bridge import scan_text_with_goplus_agentguard

UNSAFE_AI_INPUT_DETAIL = "unsafe_ai_input"
ENABLE_THIRD_PARTY_AGENT_GUARD = False

_ZERO_WIDTH_OR_BIDI_RE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
_COMMAND_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "command_injection",
        re.compile(
            r"\b(?:curl|wget)\b[\s\S]{0,80}\|\s*(?:ba?sh|sh|zsh|pwsh|powershell)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "command_injection",
        re.compile(
            r"\b(?:(?:bash|sh|zsh|pwsh|powershell)\s+-[ce]|cmd(?:\.exe)?\s+/[ck])\b",
            re.IGNORECASE,
        ),
    ),
    (
        "command_injection",
        re.compile(r"\b(?:npm|pip(?:3)?|brew)\s+install\b", re.IGNORECASE),
    ),
    (
        "command_injection",
        re.compile(r"\b(?:python(?:3)?|node)\s+-c\b", re.IGNORECASE),
    ),
    (
        "command_injection",
        re.compile(r"\b(?:os\.system|subprocess\.(?:run|call|popen)|eval|exec)\b", re.IGNORECASE),
    ),
    (
        "command_injection",
        re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    ),
    (
        "command_injection",
        re.compile(r"\bchmod\s+\+x\b", re.IGNORECASE),
    ),
)
_PROMPT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "prompt_injection",
        re.compile(
            r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prompt_injection",
        re.compile(r"\bdisregard\s+(?:the\s+)?(?:system|developer)\s+prompt\b", re.IGNORECASE),
    ),
    (
        "prompt_injection",
        re.compile(r"\breveal\s+(?:the\s+)?(?:system|hidden|developer)\s+prompt\b", re.IGNORECASE),
    ),
    (
        "prompt_injection",
        re.compile(r"\boverride\s+(?:all\s+)?safety\s+(?:rules|checks)\b", re.IGNORECASE),
    ),
    (
        "prompt_injection",
        re.compile(r"\byou\s+are\s+now\s+(?:in\s+)?developer\s+mode\b", re.IGNORECASE),
    ),
    (
        "prompt_injection",
        re.compile(r"\btool\s+call\b[\s\S]{0,80}\b(?:shell|terminal|command)\b", re.IGNORECASE),
    ),
)
_SUSPICIOUS_ASCII_FOLDS = (
    "curl",
    "wget",
    "bash",
    "powershell",
    "ignore previous instructions",
)
_CYRILLIC_HOMOGLYPHS = str.maketrans(
    {
        "А": "A",
        "В": "B",
        "Е": "E",
        "К": "K",
        "М": "M",
        "Н": "H",
        "О": "O",
        "Р": "P",
        "С": "C",
        "Т": "T",
        "Х": "X",
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "у": "y",
        "х": "x",
        "к": "k",
        "м": "m",
        "т": "t",
        "в": "b",
        "і": "i",
        "ј": "j",
        "ѕ": "s",
    }
)


@dataclass(frozen=True)
class AgentInputThreat:
    """Single detection emitted by the guard."""

    category: str
    severity: str
    reason: str


@dataclass(frozen=True)
class AgentInputScanResult:
    """Deterministic scan result for AI-facing text."""

    is_safe: bool
    threats: tuple[AgentInputThreat, ...]


def _normalize_for_detection(text: str) -> str:
    """Normalize text for pattern matching without mutating user payload."""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = _ZERO_WIDTH_OR_BIDI_RE.sub("", normalized)
    return normalized.translate(_CYRILLIC_HOMOGLYPHS)


def _load_upstream_agent_guard_class() -> type[object] | None:
    """Load optional third-party AgentGuard class when present."""

    try:
        from agent_guard import AgentGuard as upstream_agent_guard
    except Exception:
        return None
    return cast(type[object], upstream_agent_guard)


def _try_upstream_scan(text: str) -> AgentInputScanResult | None:
    """Use a compatible third-party AgentGuard only when the scan contract matches.

    RU: Одноимённый PyPI-пакет сейчас неоднозначен, поэтому доверяем только
    объекту с совместимым `scan(...)->result.is_safe`.
    EN: The PyPI name is currently ambiguous, so only a compatible
    `scan(...)->result.is_safe` contract is accepted.
    """

    upstream_agent_guard = _load_upstream_agent_guard_class()
    if upstream_agent_guard is None:
        return None

    try:
        guard = upstream_agent_guard()
    except Exception:
        return None

    scan = getattr(guard, "scan", None)
    if not callable(scan):
        return None

    try:
        result = scan(text)
    except Exception:
        return None

    is_safe = getattr(result, "is_safe", None)
    if not isinstance(is_safe, bool):
        return None

    if is_safe:
        return AgentInputScanResult(is_safe=True, threats=())

    return AgentInputScanResult(
        is_safe=False,
        threats=(
            AgentInputThreat(
                category="third_party_agent_guard",
                severity="critical",
                reason="upstream_scan_blocked",
            ),
        ),
    )


def scan_ai_agent_input(text: str) -> AgentInputScanResult:
    """Scan AI-bound text and fail closed on risky patterns."""

    goplus_result = scan_text_with_goplus_agentguard(text)
    if goplus_result is not None and goplus_result.should_block:
        categories = {
            "PROMPT_INJECTION": "prompt_injection",
            "OBFUSCATION": "unicode_obfuscation",
            "SHELL_EXEC": "command_injection",
            "AUTO_UPDATE": "command_injection",
            "REMOTE_LOADER": "command_injection",
            "SOCIAL_ENGINEERING": "prompt_injection",
            "SUSPICIOUS_PASTE_URL": "command_injection",
            "TROJAN_DISTRIBUTION": "command_injection",
        }
        goplus_threats = tuple(
            AgentInputThreat(
                category=categories.get(tag, "prompt_injection"),
                severity="critical",
                reason=f"goplus:{tag}",
            )
            for tag in goplus_result.risk_tags
            if tag in categories
        )
        if goplus_threats:
            return AgentInputScanResult(is_safe=False, threats=goplus_threats)

    third_party_flag = os.getenv("ENABLE_THIRD_PARTY_AGENT_GUARD", "")
    if ENABLE_THIRD_PARTY_AGENT_GUARD or third_party_flag.lower() in {"1", "true", "yes", "on"}:
        upstream = _try_upstream_scan(text)
        if upstream is not None and not upstream.is_safe:
            return upstream

    normalized_text = _normalize_for_detection(text)
    threats: list[AgentInputThreat] = []

    if _ZERO_WIDTH_OR_BIDI_RE.search(text):
        threats.append(
            AgentInputThreat(
                category="unicode_obfuscation",
                severity="critical",
                reason="zero_width_or_bidi_control_detected",
            )
        )

    for category, pattern in _COMMAND_PATTERNS:
        if pattern.search(normalized_text):
            threats.append(
                AgentInputThreat(
                    category=category,
                    severity="critical",
                    reason=pattern.pattern,
                )
            )

    for category, pattern in _PROMPT_PATTERNS:
        if pattern.search(normalized_text):
            threats.append(
                AgentInputThreat(
                    category=category,
                    severity="critical",
                    reason=pattern.pattern,
                )
            )

    if normalized_text != unicodedata.normalize("NFKC", text):
        lowered = normalized_text.lower()
        if any(token in lowered for token in _SUSPICIOUS_ASCII_FOLDS):
            threats.append(
                AgentInputThreat(
                    category="unicode_obfuscation",
                    severity="critical",
                    reason="homoglyph_fold_revealed_suspicious_token",
                )
            )

    if not threats:
        return AgentInputScanResult(is_safe=True, threats=())
    return AgentInputScanResult(is_safe=False, threats=tuple(threats))


def require_safe_ai_agent_input(text: str) -> str:
    """Return original text when safe, otherwise raise a stable 400 response."""

    result = scan_ai_agent_input(text)
    if result.is_safe:
        return text
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=UNSAFE_AI_INPUT_DETAIL,
    )


def prepare_safe_ai_prompt_input(text: str, *, max_length: int | None = None) -> str:
    """Validate AI-bound text and enforce prompt limits for thin callers.

    RU: Централизует fail-closed guard и проверку длины prompt, чтобы thin
    callers использовали общий helper, а не собирали политику локально.
    EN: Centralizes the fail-closed guard and prompt-length validation so thin
    callers use a shared helper instead of assembling policy inline.
    """

    safe_text = require_safe_ai_agent_input(text)
    if max_length is not None and len(safe_text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Insight text too long",
        )
    return safe_text
