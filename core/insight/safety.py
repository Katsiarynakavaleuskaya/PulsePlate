"""Safety helpers for AI Insight.

RU: Сюда выносим sanitization/guardrails, чтобы `legacy_app.py` оставался тонким shim.
EN: Put sanitization/guardrails here so `legacy_app.py` remains a thin shim.
"""

from __future__ import annotations

import re

from core.pii_redaction import redact_pii_from_text

_SOURCE_LINE_PREFIX = "# source:"
_IDENTITY_MARKER_RE = re.compile(
    r"(?<!\w)([\"']?)("
    r"subject[_ -]?id|user[_ -]?id|tenant[_ -]?id|member[_ -]?id|customer[_ -]?id|"
    r"account[_ -]?id|client[_ -]?id|session[_ -]?id|api[_ -]?key"
    r")\1\s*[:=]\s*(?:\"[^\"\n]*\"|'[^'\n]*'|[^\s,;]+)",
    re.IGNORECASE,
)


def _redact_runtime_identity_markers(text: str) -> str:
    """Redact structured identity markers that should never reach the prompt path.

    RU: Скрываем технические identity markers (`subject_id`, `tenant_id`, `api_key`)
    до сборки prompt/source preview, чтобы retrieval-контекст не тащил tenant-specific truth.
    EN: Hide structured identity markers before prompt/source preview assembly so
    retrieval context cannot leak tenant-specific truth into AI surfaces.
    """

    return _IDENTITY_MARKER_RE.sub("[IDENTITY_REDACTED]", text)


def redact_rag_context_for_insight(ctx: str) -> str:
    """Redact internal source metadata from RAG context before sending to LLM.

    RU: Удаляем строки с источниками/именами файлов, чтобы не утекала внутренняя
    структура проекта в LLM prompt (и затем потенциально к пользователю).
    EN: Remove source/filename lines to avoid leaking internal project structure into prompts.
    """

    lines: list[str] = []
    for line in ctx.splitlines():
        if line.lstrip().lower().startswith(_SOURCE_LINE_PREFIX):
            continue
        lines.append(line)
    without_sources = "\n".join(lines).strip()
    without_pii = redact_pii_from_text(without_sources) or ""
    without_identity_markers = _redact_runtime_identity_markers(without_pii)
    return without_identity_markers.strip()
