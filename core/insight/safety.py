"""Safety helpers for AI Insight.

RU: Сюда выносим sanitization/guardrails, чтобы `legacy_app.py` оставался тонким shim.
EN: Put sanitization/guardrails here so `legacy_app.py` remains a thin shim.
"""

from __future__ import annotations


def redact_rag_context_for_insight(ctx: str) -> str:
    """Redact internal source metadata from RAG context before sending to LLM.

    RU: Удаляем строки с источниками/именами файлов, чтобы не утекала внутренняя
    структура проекта в LLM prompt (и затем потенциально к пользователю).
    EN: Remove source/filename lines to avoid leaking internal project structure into prompts.
    """

    lines: list[str] = []
    for line in ctx.splitlines():
        if line.lstrip().startswith("# Source:"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
