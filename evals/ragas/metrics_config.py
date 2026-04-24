"""RU: Конфиг bootstrap-метрик. EN: Bootstrap metric configuration."""

from __future__ import annotations

DEFAULT_RAGAS_METRICS: tuple[str, ...] = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
)

REPORT_ONLY_MODE: bool = True
