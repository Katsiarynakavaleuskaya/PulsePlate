#!/usr/bin/env python3
"""PulsePlate RAG / Insight release-gates runner.

RU: Канонический deterministic runner для internal release-gates lane.
EN: Canonical deterministic runner for the internal release-gates lane.

The committed notebook remains the analyst-friendly exploration surface.
This runner owns CI-friendly execution, artifact emission, and the schema
contract that later can be mirrored into PostgreSQL without changing logic.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# Safe defaults for local PulsePlate imports.
os.environ.setdefault("SERVER_SALT", "pulseplate-rag-eval-local-dummy-salt")

SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")
TOKEN_RE = re.compile(r"[\wА-Яа-яЁё]+", flags=re.UNICODE)

DEFAULT_INPUT_PATH = REPO_ROOT / "data" / "evals" / "pulseplate_rag_eval_sample.jsonl"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "rag_eval"
DEFAULT_NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "pulseplate_rag_release_gates.ipynb"
SAFE_EXPERIMENT_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")
RAG_GATE_RESULT_SCHEMA_VERSION = "release-rag-gate-result.v1"
RAG_GATE_RESULT_HASH_ALGORITHM = "sha256"
RAG_GATE_RESULT_CANONICALIZATION = "json-sorted-compact-utf8-single-trailing-newline"
RAG_GATE_RESULT_FILENAME = "rag_gate_result.json"
RAG_GATE_SOURCE_ARTIFACT_KEYS: tuple[str, ...] = (
    "gate_report",
    "latest_executed_notebook",
    "metrics_summary",
    "parquet_or_csv",
    "traces_jsonl",
)

DEFAULT_SAMPLE_ROWS: list[dict[str, Any]] = [
    {
        "query_id": "local_smoke_001",
        "query_text": "Какие tiers являются каноническими в PulsePlate?",
        "gold_doc_ids": ["AGENTS.md"],
        "gold_answer": "Канонические tiers — FREE, PRO и VIP.",
        "expected_claims": ["PulsePlate canonical tiers are FREE, PRO, and VIP."],
        "evidence_quotes": ["FREE", "PRO", "VIP"],
        "user_tier": "PRO",
        "subject_id": None,
        "human_label_if_any": None,
    },
    {
        "query_id": "local_smoke_002",
        "query_text": "Что делает RAG orchestration layer?",
        "gold_doc_ids": ["core/rag/orchestration.py"],
        "gold_answer": (
            "RAG orchestration retrieves chunks, validates them, and builds " "a formatted prompt."
        ),
        "expected_claims": [
            "RAG orchestration retrieves chunks.",
            "RAG orchestration validates chunks.",
            "RAG orchestration builds a formatted prompt.",
        ],
        "evidence_quotes": ["retrieval", "formatted prompt"],
        "user_tier": "PRO",
        "subject_id": None,
        "human_label_if_any": None,
    },
]

GATE_THRESHOLDS = {
    "evidence_exact_match_rate": 0.70,
    "mean_nli_entailment": 0.85,
    "support_precision": 0.80,
    "ece": 0.08,
    "escalation_min": 0.10,
    "escalation_max": 0.25,
    "recall_at_50": 0.80,
}

SUPPORT_ENTAILMENT_THRESHOLD = 0.50
ROUTING_CONFIDENCE_THRESHOLD = 0.65

# Canonical committed eval fixture (weekly CI / workflow_dispatch default input).
CANONICAL_RAG_EVAL_SAMPLE_FILENAME = "pulseplate_rag_eval_sample.jsonl"
CANONICAL_RAG_EVAL_SAMPLE_PATH = DEFAULT_INPUT_PATH.resolve()
# Numeric aggregate gates (A, B*, C2) are not statistically meaningful on tiny n;
# weekly lane still enforces strict runtime hygiene (gate_d1) and calibration (gate_c1).
SMALL_FIXTURE_NUMERIC_GATES_ADVISORY_MAX_N = 16
SMALL_FIXTURE_NUMERIC_GATE_KEYS: tuple[str, ...] = (
    "gate_a_recall_at_effective_k",
    "gate_b1_evidence_exact_match",
    "gate_b2_mean_nli_entailment",
    "gate_b3_support_precision",
    "gate_c2_escalation_corridor",
)

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "artifacts",
    "worktrees",
}
INCLUDED_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt"}
DEFAULT_CORPUS_DIRS = [
    "docs",
    "core",
    "app",
    "tests/guards",
    "AGENTS.md",
    "RUNBOOK_AGENT.md",
]


def _truthy_env(value: str | None, *, default: bool = False) -> bool:
    """Return a bool from an env-style value."""

    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _small_fixture_numeric_gates_advisory(
    *,
    dataset_path_used: str,
    trace_count: int,
) -> bool:
    """Return True when aggregate numeric gates A/B/C2 are advisory-only."""

    if trace_count <= 0 or trace_count > SMALL_FIXTURE_NUMERIC_GATES_ADVISORY_MAX_N:
        return False
    return Path(dataset_path_used).resolve() == CANONICAL_RAG_EVAL_SAMPLE_PATH


def _iso_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: Any) -> str:
    """Return a short deterministic hash for minimized trace context."""

    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_text(text: str) -> str:
    """Normalize whitespace and case for matching."""

    return re.sub(r"\s+", " ", text.lower()).strip()


def tokenize(text: str) -> list[str]:
    """Tokenize text for lexical matching and local TF-IDF."""

    return TOKEN_RE.findall(normalize_text(text))


def _json_or_list(value: Any) -> list[str]:
    """Normalize JSON/list/CSV-like values into a stable string list."""

    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
        if isinstance(parsed, str):
            return [parsed]
        if "|" in stripped:
            return [part.strip() for part in stripped.split("|") if part.strip()]
        if "," in stripped and not stripped.startswith("docs/"):
            return [part.strip() for part in stripped.split(",") if part.strip()]
        return [stripped]
    return [str(value)]


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    """Return a finite float or the provided default."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(numeric):
        return default
    return numeric


def _safe_int(value: Any, *, default: int = 0) -> int:
    """Return an int or the provided default."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_nonnegative_int(value: Any) -> int:
    """Return a real nonnegative integer, otherwise zero."""

    return value if type(value) is int and value >= 0 else 0


def _require_positive_int(value: int, *, label: str) -> int:
    """Fail closed when a numeric config would silently disable evaluation."""

    if value <= 0:
        raise ValueError(f"{label} must be > 0")
    return value


def nanmean(values: Iterable[float]) -> float:
    """Return a NaN-safe mean for numeric iterables."""

    numbers = [
        float(value) for value in values if value is not None and not math.isnan(float(value))
    ]
    return sum(numbers) / len(numbers) if numbers else float("nan")


@dataclass(frozen=True)
class EvalConfig:
    """Runner configuration resolved from CLI/env."""

    project_root: Path
    input_path: Path
    artifact_root: Path
    experiment_id: str
    sample_size: int
    top_k: int
    random_seed: int
    retriever_mode: str
    generator_mode: str
    enable_nli_model: bool
    nli_model_name: str
    notebook_path: Path
    require_pass: bool
    companion_metrics_json: Path | None = None
    allow_dataset_fallback: bool = True
    allow_runtime_fallbacks: bool = True


@dataclass(frozen=True)
class EvalRow:
    """Canonical input row for the release-gates dataset."""

    query_id: str
    query_text: str
    gold_doc_ids: list[str] = field(default_factory=list)
    gold_answer: str = ""
    expected_claims: list[str] = field(default_factory=list)
    evidence_quotes: list[str] = field(default_factory=list)
    user_tier: str = "PRO"
    subject_id: int | None = None
    human_label_if_any: int | None = None


@dataclass(frozen=True)
class CorpusChunk:
    """Single offline corpus chunk used by the local retriever."""

    doc_id: str
    source_url: str
    text: str


@dataclass
class PulsePlateImports:
    """Optional repo imports used by strict modes."""

    scan_ai_agent_input: Any = None
    validate_llm_output: Any = None
    retrieve_and_validate_rag: Any = None
    prepare_insight_runtime: Any = None
    generate_traced_insight: Any = None
    import_errors: dict[str, str] = field(default_factory=dict)

    @property
    def status(self) -> dict[str, bool]:
        """Return a stable availability summary."""

        return {
            "scan_ai_agent_input": self.scan_ai_agent_input is not None,
            "validate_llm_output": self.validate_llm_output is not None,
            "retrieve_and_validate_rag": self.retrieve_and_validate_rag is not None,
            "prepare_insight_runtime": self.prepare_insight_runtime is not None,
            "generate_traced_insight": self.generate_traced_insight is not None,
        }


@dataclass
class EvalRuntimeState:
    """Mutable runtime state used across a single evaluation run."""

    config: EvalConfig
    pulseplate_imports: PulsePlateImports
    local_retriever: "LocalTfidfRetriever | None" = None
    local_corpus_size: int = 0
    warnings: list[str] = field(default_factory=list)
    strict_violations: list[str] = field(default_factory=list)


def _resolve_path(value: str | Path) -> Path:
    """Resolve a path without requiring it to exist yet."""

    return Path(value).expanduser().resolve()


def _ensure_within(child: Path, parent: Path, *, label: str) -> Path:
    """Ensure a path stays inside the documented repo boundary."""

    try:
        child.relative_to(parent)
    except ValueError as exc:
        raise ValueError(f"{label} must stay within {parent}") from exc
    return child


def sanitize_experiment_id(raw_value: str) -> str:
    """Normalize experiment IDs into safe artifact directory names."""

    cleaned = SAFE_EXPERIMENT_ID_RE.sub("_", raw_value.strip()).strip("_")
    if not cleaned:
        raise ValueError("experiment_id must contain at least one safe character")
    return cleaned


def resolve_git_sha() -> str:
    """Resolve the current git SHA without relying on CI-only env vars."""

    env_sha = os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA")
    if env_sha:
        return env_sha

    git_metadata_path = REPO_ROOT / ".git"
    git_dir = git_metadata_path
    if git_metadata_path.is_file():
        content = git_metadata_path.read_text(encoding="utf-8").strip()
        if not content.startswith("gitdir:"):
            return "unknown"
        git_dir = (REPO_ROOT / content.split("gitdir:", maxsplit=1)[1].strip()).resolve()

    head_path = git_dir / "HEAD"
    if not head_path.is_file():
        return "unknown"

    try:
        head_value = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"

    if head_value.startswith("ref:"):
        ref_path = git_dir / head_value.split("ref:", maxsplit=1)[1].strip()
        try:
            return ref_path.read_text(encoding="utf-8").strip() or "unknown"
        except OSError:
            return "unknown"
    return head_value or "unknown"


def _record_strict_violation(state: EvalRuntimeState, message: str) -> None:
    """Track deterministic strict-lane violations once per unique message."""

    state.warnings.append(message)
    if not state.config.allow_runtime_fallbacks and message not in state.strict_violations:
        state.strict_violations.append(message)


def _json_safe_float(value: float) -> float | None:
    """Return a JSON-safe float, preserving NaN as null."""

    return None if math.isnan(value) else float(value)


def _require_finite_metric(value: Any, *, label: str) -> float:
    """Parse a metric value and fail closed when it is not finite."""

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} must be numeric") from exc
    if not math.isfinite(numeric):
        raise RuntimeError(f"{label} must be finite")
    return numeric


def _repo_relative_display_path(path: Path, *, project_root: Path) -> str:
    """Return a stable repo-relative artifact path for emitted metadata."""

    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_companion_metrics(path: Path | None, *, project_root: Path) -> dict[str, Any] | None:
    """Load an optional companion RAGAS artifact for informational reporting."""

    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Companion metrics JSON not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Companion metrics JSON is invalid: {path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Companion metrics JSON root must be an object")
    expected_payload_keys = {"dataset_path", "sample_count", "report_only", "metrics"}
    if set(payload) != expected_payload_keys:
        raise RuntimeError(
            "Companion metrics JSON must contain exactly: "
            "dataset_path, sample_count, report_only, metrics"
        )

    dataset_path = str(payload.get("dataset_path") or "").strip()
    if not dataset_path:
        raise RuntimeError("Companion metrics JSON must contain a non-empty dataset_path")

    sample_count = _safe_int(payload.get("sample_count"), default=-1)
    if sample_count <= 0:
        raise RuntimeError("Companion metrics JSON must contain a positive sample_count")

    report_only = payload.get("report_only")
    if report_only is not True:
        raise RuntimeError("Companion metrics JSON must declare report_only=true")

    metrics = payload.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise RuntimeError("Companion metrics JSON must contain a non-empty metrics object")
    expected_metric_keys = {"faithfulness", "answer_relevancy", "context_precision"}
    if set(metrics) != expected_metric_keys:
        raise RuntimeError(
            "Companion metrics JSON must contain exactly: "
            "faithfulness, answer_relevancy, context_precision"
        )

    normalized_metrics: dict[str, float] = {}
    for metric_name in ("faithfulness", "answer_relevancy", "context_precision"):
        metric_value = _require_finite_metric(
            metrics[metric_name],
            label=f"companion metric '{metric_name}'",
        )
        if not 0.0 <= metric_value <= 1.0:
            raise RuntimeError(f"companion metric '{metric_name}' must stay within [0, 1]")
        normalized_metrics[metric_name] = metric_value

    return {
        "ragas": {
            "source_path": _repo_relative_display_path(path, project_root=project_root),
            "dataset_path": dataset_path,
            "sample_count": sample_count,
            "report_only": True,
            "metrics": normalized_metrics,
        }
    }


def _build_threshold_results(
    retrieval_summary: dict[str, float],
    faithfulness_summary: dict[str, float],
    calibration_metrics: dict[str, float],
    routing_summary: dict[str, float],
    gate_checks: dict[str, bool],
    *,
    strict_violation_count: int,
) -> list[dict[str, Any]]:
    """Return deterministic threshold rows for reports and artifact summaries."""

    return [
        {
            "gate_id": "gate_a_recall_at_effective_k",
            "metric_key": "recall_at_effective_k",
            "threshold_key": "recall_at_50",
            "value": _json_safe_float(retrieval_summary["recall_at_effective_k"]),
            "target": GATE_THRESHOLDS["recall_at_50"],
            "comparison": "gte",
            "passed": gate_checks["gate_a_recall_at_effective_k"],
        },
        {
            "gate_id": "gate_b1_evidence_exact_match",
            "metric_key": "evidence_exact_match_rate",
            "threshold_key": "evidence_exact_match_rate",
            "value": _json_safe_float(faithfulness_summary["evidence_exact_match_rate"]),
            "target": GATE_THRESHOLDS["evidence_exact_match_rate"],
            "comparison": "gte",
            "passed": gate_checks["gate_b1_evidence_exact_match"],
        },
        {
            "gate_id": "gate_b2_mean_nli_entailment",
            "metric_key": "mean_nli_entailment",
            "threshold_key": "mean_nli_entailment",
            "value": _json_safe_float(faithfulness_summary["mean_nli_entailment"]),
            "target": GATE_THRESHOLDS["mean_nli_entailment"],
            "comparison": "gte",
            "passed": gate_checks["gate_b2_mean_nli_entailment"],
        },
        {
            "gate_id": "gate_b3_support_precision",
            "metric_key": "support_precision",
            "threshold_key": "support_precision",
            "value": _json_safe_float(faithfulness_summary["support_precision"]),
            "target": GATE_THRESHOLDS["support_precision"],
            "comparison": "gte",
            "passed": gate_checks["gate_b3_support_precision"],
        },
        {
            "gate_id": "gate_c1_ece",
            "metric_key": "ece",
            "threshold_key": "ece",
            "value": _json_safe_float(calibration_metrics["ece"]),
            "target": GATE_THRESHOLDS["ece"],
            "comparison": "lte",
            "passed": gate_checks["gate_c1_ece"],
        },
        {
            "gate_id": "gate_c2_escalation_corridor",
            "metric_key": "escalation_rate",
            "threshold_key": "escalation_corridor",
            "value": _json_safe_float(routing_summary["escalation_rate"]),
            "target": {
                "min": GATE_THRESHOLDS["escalation_min"],
                "max": GATE_THRESHOLDS["escalation_max"],
            },
            "comparison": "between_inclusive",
            "passed": gate_checks["gate_c2_escalation_corridor"],
        },
        {
            "gate_id": "gate_d1_no_runtime_mode_fallbacks",
            "metric_key": "strict_violation_count",
            "threshold_key": "strict_violation_count",
            "value": strict_violation_count,
            "target": 0,
            "comparison": "eq",
            "passed": gate_checks["gate_d1_no_runtime_mode_fallbacks"],
        },
    ]


def _format_threshold_target(target: Any) -> str:
    """Render threshold targets for Markdown tables."""

    if isinstance(target, dict):
        lower = target.get("min")
        upper = target.get("max")
        return f"{lower}..{upper}"
    return str(target)


def _format_threshold_value(value: Any) -> str:
    """Render threshold values for Markdown tables."""

    if value is None:
        return "null"
    return str(value)


def _record_runtime_fallback(state: EvalRuntimeState, warning: str) -> None:
    """Track runtime degradations and mark strict lanes as failed-closed."""

    _record_strict_violation(state, warning)


def _try_import(imports: PulsePlateImports, name: str, import_fn: Any) -> None:
    """Load a repo symbol and record deterministic error text if unavailable."""

    try:
        setattr(imports, name, import_fn())
    except Exception as exc:  # pragma: no cover - exercised by environment
        setattr(imports, name, None)
        imports.import_errors[name] = f"{type(exc).__name__}: {exc}"


def load_pulseplate_imports() -> PulsePlateImports:
    """Load optional repo hooks for strict retrieval/runtime validation."""

    imports = PulsePlateImports()
    _try_import(
        imports,
        "scan_ai_agent_input",
        lambda: __import__(
            "app.security.agent_input_guard",
            fromlist=["scan_ai_agent_input"],
        ).scan_ai_agent_input,
    )
    _try_import(
        imports,
        "validate_llm_output",
        lambda: __import__(
            "core.insight.philosophy_validator",
            fromlist=["validate_llm_output"],
        ).validate_llm_output,
    )
    _try_import(
        imports,
        "retrieve_and_validate_rag",
        lambda: __import__(
            "core.rag.orchestration",
            fromlist=["retrieve_and_validate_rag"],
        ).retrieve_and_validate_rag,
    )
    _try_import(
        imports,
        "prepare_insight_runtime",
        lambda: __import__(
            "core.ai",
            fromlist=["prepare_insight_runtime"],
        ).prepare_insight_runtime,
    )
    _try_import(
        imports,
        "generate_traced_insight",
        lambda: __import__(
            "app.services.insight_runtime",
            fromlist=["generate_traced_insight"],
        ).generate_traced_insight,
    )
    return imports


def _is_excluded(path: Path) -> bool:
    """Exclude local/artifact paths from the offline fallback corpus."""

    return bool(set(path.parts) & EXCLUDED_DIRS)


def _read_text(path: Path) -> str:
    """Best-effort text reader for corpus/doc ingestion."""

    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def chunk_text(text: str, *, max_chars: int = 1_200, overlap: int = 160) -> list[str]:
    """Chunk large documents into overlap windows for retrieval."""

    cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not cleaned:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
            continue
        start = 0
        while start < len(paragraph):
            end = min(start + max_chars, len(paragraph))
            chunks.append(paragraph[start:end])
            if end >= len(paragraph):
                break
            start = max(0, end - overlap)
        current = ""
    if current:
        chunks.append(current)
    return chunks


def build_local_corpus(project_root: Path) -> list[CorpusChunk]:
    """Build the offline fallback corpus from canonical repo surfaces."""

    files: list[Path] = []
    for entry in DEFAULT_CORPUS_DIRS:
        candidate = project_root / entry
        if candidate.is_file() and candidate.suffix.lower() in INCLUDED_SUFFIXES:
            files.append(candidate)
            continue
        if not candidate.is_dir():
            continue
        for child in candidate.rglob("*"):
            if not child.is_file():
                continue
            if child.suffix.lower() not in INCLUDED_SUFFIXES:
                continue
            if _is_excluded(child):
                continue
            files.append(child)

    corpus: list[CorpusChunk] = []
    for file_path in sorted(set(files)):
        text = _read_text(file_path)
        if not text.strip():
            continue
        rel_path = file_path.relative_to(project_root).as_posix()
        for chunk_index, chunk in enumerate(chunk_text(text), start=1):
            corpus.append(
                CorpusChunk(
                    doc_id=f"{rel_path}#chunk-{chunk_index}",
                    source_url=rel_path,
                    text=chunk,
                ),
            )
    return corpus


class LocalTfidfRetriever:
    """Pure-Python TF-IDF retriever for deterministic CI and local smoke."""

    def __init__(self, chunks: Sequence[CorpusChunk]) -> None:
        self.chunks = list(chunks)
        self.chunk_tokens = [tokenize(chunk.text) for chunk in self.chunks]
        self.document_frequencies = self._compute_document_frequencies()
        self.idf = self._compute_inverse_document_frequencies()

    def _compute_document_frequencies(self) -> Counter[str]:
        """Compute document frequencies across the corpus."""

        frequencies: Counter[str] = Counter()
        for tokens in self.chunk_tokens:
            frequencies.update(set(tokens))
        return frequencies

    def _compute_inverse_document_frequencies(self) -> dict[str, float]:
        """Compute IDF weights with smoothing."""

        total_documents = max(len(self.chunk_tokens), 1)
        return {
            token: math.log((1 + total_documents) / (1 + count)) + 1.0
            for token, count in self.document_frequencies.items()
        }

    def _score(self, query_tokens: Sequence[str], doc_tokens: Sequence[str]) -> float:
        """Compute cosine similarity over TF-IDF weights."""

        if not query_tokens or not doc_tokens:
            return 0.0
        query_tf = Counter(query_tokens)
        doc_tf = Counter(doc_tokens)
        overlap = set(query_tf) | set(doc_tf)
        numerator = 0.0
        query_norm = 0.0
        doc_norm = 0.0
        for token in overlap:
            weight = self.idf.get(token, 1.0)
            query_value = query_tf.get(token, 0) * weight
            doc_value = doc_tf.get(token, 0) * weight
            numerator += query_value * doc_value
            query_norm += query_value * query_value
            doc_norm += doc_value * doc_value
        if query_norm == 0.0 or doc_norm == 0.0:
            return 0.0
        return numerator / (math.sqrt(query_norm) * math.sqrt(doc_norm))

    def retrieve(self, query: str, *, top_k: int) -> list[dict[str, Any]]:
        """Return the top retrieved chunks for the query."""

        query_tokens = tokenize(query)
        scored: list[tuple[float, int]] = []
        for index, tokens in enumerate(self.chunk_tokens):
            score = self._score(query_tokens, tokens)
            if score <= 0.0:
                continue
            scored.append((score, index))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for rank, (score, index) in enumerate(scored[:top_k], start=1):
            chunk = self.chunks[index]
            results.append(
                {
                    "rank": rank,
                    "doc_id": chunk.doc_id,
                    "source_url": chunk.source_url,
                    "retrieval_score": round(score, 6),
                    "doc_snippet": chunk.text[:1_400],
                    "retriever": "local_tfidf",
                    "chunk_id": chunk.doc_id,
                    "hop": 1,
                },
            )
        return results


def map_rag_chunk(chunk: Any, *, rank: int, retriever: str) -> dict[str, Any]:
    """Map a real `RAGChunk` into the trace schema."""

    file_path = str(getattr(chunk, "file", ""))
    doc_id = str(getattr(chunk, "chunk_id", file_path))
    return {
        "rank": rank,
        "doc_id": doc_id,
        "source_url": file_path,
        "retrieval_score": round(_safe_float(getattr(chunk, "score", 0.0)), 6),
        "doc_snippet": str(getattr(chunk, "content", ""))[:1_400],
        "retriever": retriever,
        "chunk_id": doc_id,
        "hop": _safe_int(getattr(chunk, "hop", 1), default=1),
    }


def map_orchestration_result_to_retrieved(
    orchestration_result: Any,
    *,
    retriever: str = "pulseplate",
    context_compaction_enabled: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Map `RAGOrchestrationResult` into retrieved rows and retrieval metadata."""

    if type(context_compaction_enabled) is not bool:
        raise TypeError("context_compaction_enabled must be a built-in bool")

    chunks = list(getattr(orchestration_result, "chunks", []) or [])
    context_compaction_attempted = (
        getattr(orchestration_result, "context_compaction_attempted", False) is True
    )
    raw_chunks_compacted = getattr(orchestration_result, "chunks_compacted", 0)
    context_compaction_result_observed = (
        context_compaction_enabled is True
        and context_compaction_attempted is True
        and getattr(orchestration_result, "context_compaction_completed", False) is True
        and getattr(orchestration_result, "rag_actually_used", False) is True
        and getattr(orchestration_result, "degraded_reason", None) is None
        and type(raw_chunks_compacted) is int
        and raw_chunks_compacted >= 0
    )
    chunks_compacted = raw_chunks_compacted if context_compaction_result_observed else 0
    retrieved = [
        map_rag_chunk(chunk, rank=rank, retriever=retriever)
        for rank, chunk in enumerate(chunks, start=1)
    ]
    metadata = {
        "rag_actually_used": bool(getattr(orchestration_result, "rag_actually_used", False)),
        "confidence": getattr(orchestration_result, "confidence", None),
        "hops": _safe_int(getattr(orchestration_result, "hops", 0), default=0),
        "latency_ms": _safe_int(
            getattr(orchestration_result, "latency_ms", 0),
            default=0,
        ),
        "warnings": list(getattr(orchestration_result, "warnings", []) or []),
        "chunks_retrieved": _safe_int(
            getattr(orchestration_result, "chunks_retrieved", len(chunks)),
            default=len(chunks),
        ),
        "chunks_filtered": _safe_int(
            getattr(orchestration_result, "chunks_filtered", 0),
            default=0,
        ),
        "recursive_executed": bool(
            getattr(orchestration_result, "recursive_executed", False),
        ),
        "degraded_reason": (str(getattr(orchestration_result, "degraded_reason", "")) or None),
        "formatted_prompt_present": bool(
            str(getattr(orchestration_result, "formatted_prompt", "")).strip(),
        ),
        "context_compaction_enabled": context_compaction_enabled,
        "context_compaction_attempted": context_compaction_attempted,
        "context_compaction_result_observed": context_compaction_result_observed,
        "chunks_compacted": chunks_compacted,
    }
    return retrieved, metadata


def ensure_local_retriever(state: EvalRuntimeState) -> LocalTfidfRetriever:
    """Build or reuse the deterministic local retriever."""

    if state.local_retriever is None:
        corpus = build_local_corpus(state.config.project_root)
        state.local_corpus_size = len(corpus)
        state.local_retriever = LocalTfidfRetriever(corpus)
    return state.local_retriever


async def pulseplate_retrieve(
    state: EvalRuntimeState,
    query: str,
    *,
    top_k: int,
    subject_id: int | None,
    context_compaction_enabled: bool | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Execute the real orchestration path and map the output into trace rows."""

    if context_compaction_enabled is None:
        context_compaction_enabled = _truthy_env(
            os.getenv("FEATURE_RAG_CONTEXT_COMPACTION"),
        )
    elif type(context_compaction_enabled) is not bool:
        raise TypeError("context_compaction_enabled must be a built-in bool")

    retrieve_and_validate_rag = state.pulseplate_imports.retrieve_and_validate_rag
    if retrieve_and_validate_rag is None:
        raise RuntimeError("PulsePlate retrieve_and_validate_rag is unavailable")

    recursive_enabled = _truthy_env(os.getenv("FEATURE_RAG_RECURSIVE"))
    optimization_enabled = _truthy_env(
        os.getenv("FEATURE_RAG_RECURSIVE_OPTIMIZATION"),
    )
    result = await retrieve_and_validate_rag(
        query,
        max_chunks=top_k,
        philo_validation_enabled=True,
        recursive_rag_enabled=recursive_enabled,
        optimization_enabled=optimization_enabled,
        context_compaction_enabled=context_compaction_enabled,
        subject_id=subject_id,
    )
    retrieved, metadata = map_orchestration_result_to_retrieved(
        result,
        retriever="pulseplate",
        context_compaction_enabled=context_compaction_enabled,
    )
    metadata["max_supported_top_k"] = len(retrieved) or top_k
    metadata["requested_top_k"] = top_k
    if (
        context_compaction_enabled is True
        and metadata["context_compaction_attempted"] is True
        and metadata["context_compaction_result_observed"] is not True
    ):
        _record_strict_violation(state, "rag_context_compaction_failed")
    return retrieved, metadata


async def retrieve(
    state: EvalRuntimeState,
    query: str,
    *,
    top_k: int,
    subject_id: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Retrieve evidence using the requested mode with safe fallback."""

    context_compaction_enabled = False
    if state.config.retriever_mode == "pulseplate":
        context_compaction_enabled = _truthy_env(
            os.getenv("FEATURE_RAG_CONTEXT_COMPACTION"),
        )
        try:
            return await pulseplate_retrieve(
                state,
                query,
                top_k=top_k,
                subject_id=subject_id,
                context_compaction_enabled=context_compaction_enabled,
            )
        except Exception as exc:
            _record_runtime_fallback(
                state,
                "pulseplate_retriever_fallback:" f"{type(exc).__name__}:{exc}",
            )
    local_retriever = ensure_local_retriever(state)
    return local_retriever.retrieve(query, top_k=top_k), {
        "rag_actually_used": bool(local_retriever.chunks),
        "confidence": None,
        "hops": 1,
        "latency_ms": 0,
        "warnings": [],
        "chunks_retrieved": 0,
        "chunks_filtered": 0,
        "recursive_executed": False,
        "degraded_reason": None,
        "formatted_prompt_present": False,
        "context_compaction_enabled": context_compaction_enabled,
        "context_compaction_attempted": False,
        "context_compaction_result_observed": False,
        "chunks_compacted": 0,
        "max_supported_top_k": top_k,
        "requested_top_k": top_k,
    }


def _first_useful_sentence(
    text: str,
    *,
    min_chars: int = 40,
    max_chars: int = 420,
) -> str:
    """Extract the first reasonably informative sentence."""

    for sentence in SENTENCE_RE.split(text):
        candidate = re.sub(r"\s+", " ", sentence).strip()
        if len(candidate) >= min_chars:
            return candidate[:max_chars]
    return re.sub(r"\s+", " ", text).strip()[:max_chars]


def _confidence_from_retrieval(retrieved: list[dict[str, Any]]) -> float:
    """Derive a baseline confidence from the top retrieval score."""

    if not retrieved:
        return 0.05
    raw = _safe_float(retrieved[0].get("retrieval_score"), default=0.0)
    return max(0.01, min(raw, 0.99))


def extractive_grounded_generate(
    query: str,
    retrieved: list[dict[str, Any]],
) -> tuple[str, float, dict[str, Any]]:
    """Generate an inexpensive answer by quoting top retrieved evidence."""

    if not retrieved:
        return (
            "Недостаточно подтверждённого контекста для ответа. Требуется эскалация.",
            0.05,
            {"generator": "extractive_stub", "reason": "no_retrieved_context"},
        )

    top = retrieved[0]
    evidence = _first_useful_sentence(str(top.get("doc_snippet", "")))
    answer = (
        f"На основе найденного источника `{top.get('source_url')}`: "
        f'"{evidence}"\n\n'
        f"Ответ на запрос: {query}\n"
        "Ограничение: это evidence-grounded offline evaluation response, "
        "не медицинская рекомендация."
    )
    return (
        answer,
        _confidence_from_retrieval(retrieved),
        {
            "generator": "extractive_stub",
            "evidence_source": top.get("source_url"),
            "top_doc_id": top.get("doc_id"),
        },
    )


class EvalStubProvider:
    """Provider stub used by the strict runtime path to avoid paid calls."""

    name = "pulseplate_eval_stub"

    def __init__(self, retrieved: list[dict[str, Any]]) -> None:
        self.retrieved = retrieved

    async def generate(self, text: str) -> str:
        """Mirror a provider contract while staying fully offline."""

        answer, _, _ = extractive_grounded_generate(text, self.retrieved)
        return answer


async def pulseplate_runtime_generate(
    state: EvalRuntimeState,
    query: str,
    retrieved: list[dict[str, Any]],
    *,
    user_tier: str,
    subject_id: int | None,
) -> tuple[str, float, dict[str, Any]]:
    """Execute the real runtime path with an offline stub provider."""

    prepare_insight_runtime = state.pulseplate_imports.prepare_insight_runtime
    generate_traced_insight = state.pulseplate_imports.generate_traced_insight
    if prepare_insight_runtime is None or generate_traced_insight is None:
        raise RuntimeError("PulsePlate runtime imports unavailable")

    provider = EvalStubProvider(retrieved)
    prepared = prepare_insight_runtime(
        text=query,
        use_rag=True,
        philosophy_router_enabled=_truthy_env(
            os.getenv("FEATURE_PHILOSOPHY_ROUTER"),
        ),
        philosophy_linguistic_enabled=_truthy_env(
            os.getenv("FEATURE_PHILOSOPHY_LINGUISTIC"),
        ),
        philosophy_phase12_enabled=_truthy_env(
            os.getenv("FEATURE_PHILOSOPHY_PHASE12"),
        ),
        philosophy_pragmatic_enabled=_truthy_env(
            os.getenv("FEATURE_PHILOSOPHY_PRAGMATIC"),
        ),
        provider_loader=lambda: provider,
        transparency_loader=lambda: (
            "ai_generated_insight",
            "Educational wellness information only; no diagnosis or treatment.",
        ),
        direct_provider_factory=lambda: provider,
    )
    result = await generate_traced_insight(
        runtime=prepared.runtime,
        text=query,
        lang=None,
        provider=prepared.provider,
        use_rag=True,
        philo_validation_enabled=True,
        recursive_rag_enabled=False,
        subject_id=subject_id,
        knowledge_policy=prepared.knowledge_policy,
        route_path="/api/v1/insight",
        route_type=prepared.decision.route_type.value,
        user_tier=user_tier,
        rollout_policy=prepared.rollout_policy,
    )
    answer = str(getattr(result, "insight", ""))
    confidence = _safe_float(
        getattr(result, "confidence", None),
        default=_confidence_from_retrieval(retrieved),
    )
    confidence = max(0.01, min(confidence, 0.99))
    return (
        answer,
        confidence,
        {
            "generator": "pulseplate_runtime_with_eval_stub_provider",
            "provider_name": getattr(result, "provider_name", None),
            "rag_used": getattr(result, "rag_used", None),
            "hops": getattr(result, "hops", None),
            "latency_ms": getattr(result, "latency_ms", None),
        },
    )


async def generate_answer(
    state: EvalRuntimeState,
    query: str,
    retrieved: list[dict[str, Any]],
    *,
    user_tier: str,
    subject_id: int | None,
) -> tuple[str, float, dict[str, Any]]:
    """Generate an answer using strict runtime when requested, else stub."""

    if state.config.generator_mode == "pulseplate_runtime":
        try:
            return await pulseplate_runtime_generate(
                state,
                query,
                retrieved,
                user_tier=user_tier,
                subject_id=subject_id,
            )
        except Exception as exc:
            _record_runtime_fallback(
                state,
                "pulseplate_runtime_generator_fallback:" f"{type(exc).__name__}:{exc}",
            )
    return extractive_grounded_generate(query, retrieved)


def extract_claims(answer: str, *, max_claims: int = 8) -> list[dict[str, Any]]:
    """Extract rough claim spans from the generated answer."""

    claims: list[dict[str, Any]] = []
    cursor = 0
    for sentence in SENTENCE_RE.split(answer):
        span_text = sentence.strip()
        if len(span_text) < 20:
            cursor += len(sentence) + 1
            continue
        start = answer.find(span_text, cursor)
        end = start + len(span_text) if start >= 0 else -1
        claims.append({"span_text": span_text, "start": start, "end": end})
        cursor = max(cursor, end)
        if len(claims) >= max_claims:
            break
    return claims


def answer_contains_exact_evidence(
    answer: str,
    contexts: list[str],
    *,
    min_tokens: int = 8,
) -> bool:
    """Check whether the answer copies exact evidence from retrieved context."""

    answer_normalized = normalize_text(answer)
    context_normalized = "\n".join(normalize_text(context) for context in contexts)

    for quoted in re.findall(r'"([^"]{20,})"', answer):
        quoted_normalized = normalize_text(quoted)
        if quoted_normalized and quoted_normalized in context_normalized:
            return True

    for sentence in SENTENCE_RE.split(answer):
        if len(tokenize(sentence)) < min_tokens:
            continue
        sentence_normalized = normalize_text(sentence)
        if sentence_normalized and sentence_normalized in context_normalized:
            return True

    answer_tokens = tokenize(answer_normalized)
    for length in range(min_tokens, min(len(answer_tokens), 18) + 1):
        for index in range(0, max(0, len(answer_tokens) - length + 1)):
            phrase = " ".join(answer_tokens[index : index + length])
            if phrase in context_normalized:
                return True
    return False


def lexical_support_score(claim: str, contexts: list[str]) -> float:
    """Compute lexical support when an NLI model is unavailable."""

    claim_tokens = set(tokenize(claim))
    if not claim_tokens:
        return 0.0
    best = 0.0
    for context in contexts:
        context_tokens = set(tokenize(context))
        if not context_tokens:
            continue
        overlap = len(claim_tokens & context_tokens) / max(1, len(claim_tokens))
        best = max(best, overlap)
    return max(0.0, min(best, 1.0))


_NLI_PIPELINE: Any = None


def load_nli_pipeline(config: EvalConfig) -> Any:
    """Load an optional transformers NLI pipeline when explicitly enabled."""

    global _NLI_PIPELINE
    if _NLI_PIPELINE is not None:
        return _NLI_PIPELINE
    if not config.enable_nli_model:
        return None
    try:
        from transformers import pipeline
    except Exception:
        return None
    try:
        _NLI_PIPELINE = pipeline(
            "text-classification",
            model=config.nli_model_name,
            tokenizer=config.nli_model_name,
            truncation=True,
        )
    except Exception:
        _NLI_PIPELINE = None
    return _NLI_PIPELINE


def nli_entailment_score(
    config: EvalConfig,
    claim: str,
    contexts: list[str],
) -> float:
    """Return an entailment score or lexical fallback support."""

    nli = load_nli_pipeline(config)
    if nli is None:
        return lexical_support_score(claim, contexts)

    premise = "\n\n".join(contexts[:8])[:3_500]
    if not premise.strip() or not claim.strip():
        return 0.0

    try:
        outputs = nli({"text": premise, "text_pair": claim}, top_k=None)
    except Exception:
        outputs = nli(f"{premise}\n\nHypothesis: {claim}", top_k=None)

    if isinstance(outputs, dict):
        outputs = [outputs]
    best = 0.0
    for item in outputs:
        label = str(item.get("label", "")).lower()
        score = _safe_float(item.get("score"), default=0.0)
        if "entail" in label:
            best = max(best, score)
    return max(0.0, min(best, 1.0))


def evaluate_faithfulness(
    config: EvalConfig,
    answer: str,
    retrieved: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measure basic faithfulness and evidence support."""

    contexts = [str(item.get("doc_snippet", "")) for item in retrieved]
    claims = extract_claims(answer)
    entailments: list[float] = []
    support_flags: list[bool] = []
    for claim in claims:
        score = nli_entailment_score(config, claim["span_text"], contexts)
        entailments.append(score)
        support_flags.append(score >= SUPPORT_ENTAILMENT_THRESHOLD)

    return {
        "extracted_claim_spans": claims,
        "per_span_entailment_score": entailments,
        "support_flags": support_flags,
        "evidence_exact_match": answer_contains_exact_evidence(answer, contexts),
        "mean_nli_entailment": (sum(entailments) / len(entailments) if entailments else 0.0),
        "support_precision": (
            sum(1 for flag in support_flags if flag) / len(support_flags) if support_flags else 0.0
        ),
    }


def validate_output_with_pulseplate(
    imports: PulsePlateImports,
    answer: str,
) -> dict[str, Any]:
    """Run the deterministic philosophy validator when available."""

    validate_llm_output = imports.validate_llm_output
    if validate_llm_output is None:
        return {
            "philosophy_validator_available": False,
            "ok": False,
            "blockers": [
                {
                    "code": "validator_unavailable",
                    "start": None,
                    "end": None,
                    "matched": None,
                },
            ],
        }
    try:
        report = validate_llm_output(answer, domain="rag_eval")
    except Exception as exc:
        return {
            "philosophy_validator_available": True,
            "ok": False,
            "blockers": [
                {
                    "code": "validator_error",
                    "start": None,
                    "end": None,
                    "matched": None,
                },
            ],
            "error": f"{type(exc).__name__}: {exc}",
        }

    blockers = [
        {
            "code": getattr(blocker, "code", None),
            "start": getattr(blocker, "start", None),
            "end": getattr(blocker, "end", None),
            "matched": getattr(blocker, "matched", None),
        }
        for blocker in getattr(report, "blockers", [])
    ]
    return {
        "philosophy_validator_available": True,
        "ok": bool(getattr(report, "ok", False)),
        "blockers": blockers,
    }


def _doc_matches(doc_id: str, source_url: str, gold: str) -> bool:
    """Perform path-fragment-tolerant matching against gold doc identifiers."""

    doc_normalized = normalize_text(doc_id)
    source_normalized = normalize_text(source_url)
    gold_normalized = normalize_text(gold)
    if not gold_normalized:
        return False
    return (
        gold_normalized in doc_normalized
        or gold_normalized in source_normalized
        or doc_normalized in gold_normalized
        or source_normalized in gold_normalized
    )


def recall_at_k(
    retrieved: list[dict[str, Any]],
    gold_doc_ids: list[str],
    *,
    k: int,
) -> float:
    """Compute recall@k for tolerant doc-id matching."""

    if not gold_doc_ids:
        return float("nan")
    found = set()
    for item in retrieved[:k]:
        for gold in gold_doc_ids:
            if _doc_matches(str(item.get("doc_id", "")), str(item.get("source_url", "")), gold):
                found.add(gold)
    return len(found) / max(1, len(set(gold_doc_ids)))


def mrr_at_k(
    retrieved: list[dict[str, Any]],
    gold_doc_ids: list[str],
    *,
    k: int,
) -> float:
    """Compute mean reciprocal rank at k for tolerant matching."""

    if not gold_doc_ids:
        return float("nan")
    for index, item in enumerate(retrieved[:k], start=1):
        if any(
            _doc_matches(str(item.get("doc_id", "")), str(item.get("source_url", "")), gold)
            for gold in gold_doc_ids
        ):
            return 1.0 / index
    return 0.0


def ndcg_at_k(
    retrieved: list[dict[str, Any]],
    gold_doc_ids: list[str],
    *,
    k: int,
) -> float:
    """Compute nDCG@k for tolerant matching."""

    if not gold_doc_ids:
        return float("nan")
    relevance = [
        (
            1
            if any(
                _doc_matches(str(item.get("doc_id", "")), str(item.get("source_url", "")), gold)
                for gold in gold_doc_ids
            )
            else 0
        )
        for item in retrieved[:k]
    ]
    dcg = sum(score / math.log2(index + 2) for index, score in enumerate(relevance))
    ideal_relevant = min(len(set(gold_doc_ids)), k)
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_relevant))
    return dcg / idcg if idcg > 0 else 0.0


def coerce_subject_id(value: Any) -> int | None:
    """Normalize optional subject IDs for tenant-aware retrieval."""

    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return int(value)
    except Exception:
        return None


def scan_agent_input(
    imports: PulsePlateImports,
    query_text: str,
) -> dict[str, Any]:
    """Run the shared AI input guard when available."""

    scan_ai_agent_input = imports.scan_ai_agent_input
    if scan_ai_agent_input is None:
        return {
            "available": False,
            "is_safe": False,
            "threats": [
                {
                    "category": "guard_unavailable",
                    "severity": "critical",
                    "reason": "scan_ai_agent_input_missing",
                },
            ],
        }
    try:
        scan = scan_ai_agent_input(query_text)
    except Exception as exc:
        return {
            "available": True,
            "is_safe": False,
            "threats": [
                {
                    "category": "guard_error",
                    "severity": "critical",
                    "reason": str(exc),
                },
            ],
        }
    return {
        "available": True,
        "is_safe": bool(getattr(scan, "is_safe", False)),
        "threats": [
            {
                "category": getattr(threat, "category", None),
                "severity": getattr(threat, "severity", None),
                "reason": getattr(threat, "reason", None),
            }
            for threat in getattr(scan, "threats", [])
        ],
    }


async def evaluate_one(
    state: EvalRuntimeState,
    row: EvalRow,
) -> dict[str, Any]:
    """Evaluate a single query and emit a canonical trace row."""

    query_text = row.query_text
    trace_id = f"{state.config.experiment_id}:{row.query_id}"
    started = time.perf_counter()
    guard_result = scan_agent_input(state.pulseplate_imports, query_text)
    if not guard_result.get("available", False):
        _record_strict_violation(
            state,
            "agent_input_guard_unavailable:scan_ai_agent_input_missing",
        )
    user_context_hash = stable_hash(
        {"subject_id": row.subject_id, "user_tier": row.user_tier},
    )

    if not guard_result["is_safe"]:
        latency_ms = int((time.perf_counter() - started) * 1_000)
        return {
            "trace_id": trace_id,
            "timestamp": _iso_now(),
            "experiment_id": state.config.experiment_id,
            "query_id": row.query_id,
            "query_text": query_text,
            "user_context_hash": user_context_hash,
            "top_k_retrieved": [],
            "retrieval_stats": {},
            "generator_output": "",
            "extracted_claim_spans": [],
            "per_span_entailment_score": [],
            "support_flags": [],
            "generator_logprob": None,
            "confidence": 0.0,
            "post_hoc_calibrated_confidence": None,
            "routing_decision": "blocked_by_agent_input_guard",
            "latency": latency_ms,
            "human_label_if_any": row.human_label_if_any,
            "gold_doc_ids": row.gold_doc_ids,
            "gold_answer": row.gold_answer,
            "expected_claims": row.expected_claims,
            "evidence_quotes": row.evidence_quotes,
            "agent_input_guard": guard_result,
            "philosophy_output_validation": None,
            "retrieval_metrics": {},
            "faithfulness_metrics": {},
            "generator_metadata": {},
        }

    retrieved, retrieval_stats = await retrieve(
        state,
        query_text,
        top_k=state.config.top_k,
        subject_id=row.subject_id,
    )
    answer, confidence, generator_metadata = await generate_answer(
        state,
        query_text,
        retrieved,
        user_tier=row.user_tier,
        subject_id=row.subject_id,
    )
    faithfulness = evaluate_faithfulness(state.config, answer, retrieved)
    output_validation = validate_output_with_pulseplate(
        state.pulseplate_imports,
        answer,
    )
    if not output_validation.get("philosophy_validator_available", False):
        _record_strict_violation(
            state,
            "philosophy_validator_unavailable:validate_llm_output_missing",
        )
    elif output_validation.get("error"):
        _record_strict_violation(
            state,
            "philosophy_validator_error:" f"{output_validation['error']}",
        )
    latency_ms = int((time.perf_counter() - started) * 1_000)
    retrieval_metrics = {
        "recall_at_3": recall_at_k(retrieved, row.gold_doc_ids, k=3),
        "recall_at_10": recall_at_k(retrieved, row.gold_doc_ids, k=10),
        "recall_at_50": recall_at_k(retrieved, row.gold_doc_ids, k=50),
        "recall_at_effective_k": recall_at_k(
            retrieved,
            row.gold_doc_ids,
            k=max(
                1,
                min(
                    state.config.top_k,
                    _safe_int(
                        retrieval_stats.get("max_supported_top_k"),
                        default=state.config.top_k,
                    ),
                ),
            ),
        ),
        "mrr_at_10": mrr_at_k(retrieved, row.gold_doc_ids, k=10),
        "ndcg_at_10": ndcg_at_k(retrieved, row.gold_doc_ids, k=10),
    }
    return {
        "trace_id": trace_id,
        "timestamp": _iso_now(),
        "experiment_id": state.config.experiment_id,
        "query_id": row.query_id,
        "query_text": query_text,
        "user_context_hash": user_context_hash,
        "top_k_retrieved": retrieved,
        "retrieval_stats": retrieval_stats,
        "generator_output": answer,
        "extracted_claim_spans": faithfulness["extracted_claim_spans"],
        "per_span_entailment_score": faithfulness["per_span_entailment_score"],
        "support_flags": faithfulness["support_flags"],
        "generator_logprob": None,
        "confidence": confidence,
        "post_hoc_calibrated_confidence": None,
        "routing_decision": "pending_calibration",
        "latency": latency_ms,
        "human_label_if_any": row.human_label_if_any,
        "gold_doc_ids": row.gold_doc_ids,
        "gold_answer": row.gold_answer,
        "expected_claims": row.expected_claims,
        "evidence_quotes": row.evidence_quotes,
        "agent_input_guard": guard_result,
        "philosophy_output_validation": output_validation,
        "retrieval_metrics": retrieval_metrics,
        "faithfulness_metrics": {
            "evidence_exact_match": faithfulness["evidence_exact_match"],
            "mean_nli_entailment": faithfulness["mean_nli_entailment"],
            "support_precision": faithfulness["support_precision"],
        },
        "generator_metadata": generator_metadata,
    }


async def run_evaluation(
    state: EvalRuntimeState,
    rows: Sequence[EvalRow],
) -> list[dict[str, Any]]:
    """Evaluate all rows sequentially for deterministic output ordering."""

    traces: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        traces.append(await evaluate_one(state, row))
        if index % 25 == 0 or index == len(rows):
            print(f"evaluated {index}/{len(rows)}")
    return traces


def proxy_correctness(trace: dict[str, Any]) -> int:
    """Compute correctness labels for post-hoc calibration."""

    label = trace.get("human_label_if_any")
    if label is not None:
        try:
            return int(float(label) >= 0.5)
        except (TypeError, ValueError):
            pass
    faithfulness = trace.get("faithfulness_metrics", {}) or {}
    output_validation = trace.get("philosophy_output_validation") or {}
    if output_validation.get("ok") is False:
        return 0
    return int(
        bool(faithfulness.get("evidence_exact_match", False))
        and _safe_float(
            faithfulness.get("support_precision"),
            default=0.0,
        )
        >= GATE_THRESHOLDS["support_precision"]
        and _safe_float(
            faithfulness.get("mean_nli_entailment"),
            default=0.0,
        )
        >= min(0.75, GATE_THRESHOLDS["mean_nli_entailment"])
    )


def sigmoid(value: float) -> float:
    """Return the logistic sigmoid."""

    return 1.0 / (1.0 + math.exp(-value))


def logit(probability: float) -> float:
    """Return the logit transform with clipping."""

    clipped = max(1e-6, min(probability, 1 - 1e-6))
    return math.log(clipped / (1 - clipped))


def nll_binary(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """Compute mean binary negative log-likelihood."""

    if not labels:
        return 0.0
    losses = []
    for label, probability in zip(labels, probabilities):
        clipped = max(1e-6, min(probability, 1 - 1e-6))
        losses.append(-(label * math.log(clipped) + (1 - label) * math.log(1 - clipped)))
    return sum(losses) / len(losses)


def temperature_scale_confidence(
    confidences: Sequence[float],
    labels: Sequence[int],
) -> tuple[float, list[float]]:
    """Calibrate confidence with a deterministic grid-search temperature."""

    if not confidences:
        return 1.0, []
    clipped_confidences = [max(1e-6, min(value, 1 - 1e-6)) for value in confidences]
    logits = [logit(value) for value in clipped_confidences]
    candidates = [0.25 + 4.75 * (index / 399) for index in range(400)]
    losses: list[tuple[float, float]] = []
    for temperature in candidates:
        scaled = [sigmoid(logit_value / temperature) for logit_value in logits]
        losses.append((nll_binary(labels, scaled), temperature))
    _, best_temperature = min(losses, key=lambda item: item[0])
    return best_temperature, [sigmoid(logit_value / best_temperature) for logit_value in logits]


def expected_calibration_error(
    labels: Sequence[int],
    probabilities: Sequence[float],
    *,
    n_bins: int = 10,
) -> float:
    """Compute ECE for the calibrated confidence values."""

    if not labels:
        return 0.0
    bins = [index / n_bins for index in range(n_bins + 1)]
    total = len(probabilities)
    ece = 0.0
    for lower, upper in zip(bins[:-1], bins[1:]):
        bucket = [
            (label, probability)
            for label, probability in zip(labels, probabilities)
            if lower <= probability
            and (probability < upper or (upper == 1.0 and probability <= upper))
        ]
        if not bucket:
            continue
        accuracy = sum(label for label, _ in bucket) / len(bucket)
        confidence = sum(probability for _, probability in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(accuracy - confidence)
    return ece


def brier_score(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """Compute the Brier score."""

    if not labels:
        return 0.0
    return sum(
        (probability - label) ** 2 for label, probability in zip(labels, probabilities)
    ) / len(labels)


def apply_calibration(traces: list[dict[str, Any]]) -> dict[str, float]:
    """Calibrate trace confidences and set routing decisions."""

    labels = [proxy_correctness(trace) for trace in traces]
    raw_confidences = [_safe_float(trace.get("confidence"), default=0.0) for trace in traces]
    temperature, calibrated = temperature_scale_confidence(raw_confidences, labels)

    for trace, calibrated_confidence in zip(traces, calibrated):
        trace["post_hoc_calibrated_confidence"] = calibrated_confidence
        if trace.get("routing_decision") == "blocked_by_agent_input_guard":
            continue
        faithfulness = trace.get("faithfulness_metrics", {}) or {}
        # Per-trace support_precision is the fraction of claims with entailment >=
        # SUPPORT_ENTAILMENT_THRESHOLD (see evaluate_faithfulness). Do not compare
        # it to GATE_THRESHOLDS["support_precision"] (aggregate gate_b3 bar): that
        # forced near-100% escalation and broke gate_c2 on small evals.
        should_escalate = (
            calibrated_confidence < ROUTING_CONFIDENCE_THRESHOLD
            or not faithfulness.get("evidence_exact_match", False)
            or _safe_float(
                faithfulness.get("support_precision"),
                default=0.0,
            )
            < SUPPORT_ENTAILMENT_THRESHOLD
        )
        trace["routing_decision"] = "escalate" if should_escalate else "ship_candidate"

    return {
        "temperature": temperature,
        "ece": expected_calibration_error(labels, calibrated),
        "brier": brier_score(labels, calibrated),
        "mean_raw_confidence": (
            sum(raw_confidences) / len(raw_confidences) if raw_confidences else 0.0
        ),
        "mean_calibrated_confidence": (sum(calibrated) / len(calibrated) if calibrated else 0.0),
    }


def build_metrics_summary(
    state: EvalRuntimeState,
    traces: list[dict[str, Any]],
    calibration_metrics: dict[str, float],
    *,
    dataset_fallback_used: bool,
    dataset_path_used: str,
    companion_metrics: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, bool], str]:
    """Build summary metrics, gate checks, and the release decision."""

    context_compaction_summary = {
        "enabled_trace_count": sum(
            1
            for trace in traces
            if isinstance(trace.get("retrieval_stats"), dict)
            and trace["retrieval_stats"].get("context_compaction_enabled") is True
        ),
        "attempted_trace_count": sum(
            1
            for trace in traces
            if isinstance(trace.get("retrieval_stats"), dict)
            and trace["retrieval_stats"].get("context_compaction_enabled") is True
            and trace["retrieval_stats"].get("context_compaction_attempted") is True
        ),
        "result_observed_trace_count": sum(
            1
            for trace in traces
            if isinstance(trace.get("retrieval_stats"), dict)
            and trace["retrieval_stats"].get("context_compaction_enabled") is True
            and trace["retrieval_stats"].get("context_compaction_result_observed") is True
        ),
        "chunks_compacted_total": sum(
            _safe_nonnegative_int(trace["retrieval_stats"].get("chunks_compacted"))
            for trace in traces
            if isinstance(trace.get("retrieval_stats"), dict)
            and trace["retrieval_stats"].get("context_compaction_enabled") is True
            and trace["retrieval_stats"].get("context_compaction_result_observed") is True
        ),
    }

    retrieval_summary = {
        "recall_at_3": nanmean(
            trace["retrieval_metrics"].get("recall_at_3", float("nan")) for trace in traces
        ),
        "recall_at_10": nanmean(
            trace["retrieval_metrics"].get("recall_at_10", float("nan")) for trace in traces
        ),
        "recall_at_50": nanmean(
            trace["retrieval_metrics"].get("recall_at_50", float("nan")) for trace in traces
        ),
        "recall_at_effective_k": nanmean(
            trace["retrieval_metrics"].get("recall_at_effective_k", float("nan"))
            for trace in traces
        ),
        "mrr_at_10": nanmean(
            trace["retrieval_metrics"].get("mrr_at_10", float("nan")) for trace in traces
        ),
        "ndcg_at_10": nanmean(
            trace["retrieval_metrics"].get("ndcg_at_10", float("nan")) for trace in traces
        ),
    }
    faithfulness_summary = {
        "evidence_exact_match_rate": (
            sum(
                1
                for trace in traces
                if trace.get("faithfulness_metrics", {}).get("evidence_exact_match", False)
            )
            / len(traces)
            if traces
            else 0.0
        ),
        "mean_nli_entailment": (
            sum(
                _safe_float(
                    trace.get("faithfulness_metrics", {}).get("mean_nli_entailment"),
                    default=0.0,
                )
                for trace in traces
            )
            / len(traces)
            if traces
            else 0.0
        ),
        "support_precision": (
            sum(
                _safe_float(
                    trace.get("faithfulness_metrics", {}).get("support_precision"),
                    default=0.0,
                )
                for trace in traces
            )
            / len(traces)
            if traces
            else 0.0
        ),
    }
    routing_summary = {
        "escalation_rate": (
            sum(1 for trace in traces if trace.get("routing_decision") == "escalate") / len(traces)
            if traces
            else 0.0
        ),
        "blocked_by_guard_rate": (
            sum(
                1
                for trace in traces
                if trace.get("routing_decision") == "blocked_by_agent_input_guard"
            )
            / len(traces)
            if traces
            else 0.0
        ),
        "ship_candidate_rate": (
            sum(1 for trace in traces if trace.get("routing_decision") == "ship_candidate")
            / len(traces)
            if traces
            else 0.0
        ),
    }
    gate_checks = {
        "gate_a_recall_at_effective_k": (
            retrieval_summary["recall_at_effective_k"] >= GATE_THRESHOLDS["recall_at_50"]
            if not math.isnan(retrieval_summary["recall_at_effective_k"])
            else False
        ),
        "gate_b1_evidence_exact_match": (
            faithfulness_summary["evidence_exact_match_rate"]
            >= GATE_THRESHOLDS["evidence_exact_match_rate"]
        ),
        "gate_b2_mean_nli_entailment": (
            faithfulness_summary["mean_nli_entailment"] >= GATE_THRESHOLDS["mean_nli_entailment"]
        ),
        "gate_b3_support_precision": (
            faithfulness_summary["support_precision"] >= GATE_THRESHOLDS["support_precision"]
        ),
        "gate_c1_ece": calibration_metrics["ece"] <= GATE_THRESHOLDS["ece"],
        "gate_c2_escalation_corridor": (
            GATE_THRESHOLDS["escalation_min"]
            <= routing_summary["escalation_rate"]
            <= GATE_THRESHOLDS["escalation_max"]
        ),
        "gate_d1_no_runtime_mode_fallbacks": (
            not state.strict_violations if not state.config.allow_runtime_fallbacks else True
        ),
    }
    small_fixture_advisory = _small_fixture_numeric_gates_advisory(
        dataset_path_used=dataset_path_used,
        trace_count=len(traces),
    )
    small_fixture_raw_gate_checks: dict[str, bool] | None = None
    if small_fixture_advisory:
        small_fixture_raw_gate_checks = {
            gate_key: gate_checks[gate_key] for gate_key in SMALL_FIXTURE_NUMERIC_GATE_KEYS
        }
        for gate_key in SMALL_FIXTURE_NUMERIC_GATE_KEYS:
            gate_checks[gate_key] = True
        state.warnings.append(
            "small_fixture_metric_gates_advisory: gates A and B1-B3 and C2 are "
            f"advisory-only for canonical sample (n={len(traces)}); "
            "raw pass/fail preserved in metrics_summary['small_fixture_raw_gate_checks']."
        )
    threshold_results = _build_threshold_results(
        retrieval_summary,
        faithfulness_summary,
        calibration_metrics,
        routing_summary,
        gate_checks,
        strict_violation_count=len(state.strict_violations),
    )
    release_decision = "PASS" if all(gate_checks.values()) else "NO-GO"
    metrics_summary = {
        "experiment_id": state.config.experiment_id,
        "timestamp": _iso_now(),
        "git_sha": resolve_git_sha(),
        "sample_size": len(traces),
        "retriever_mode": state.config.retriever_mode,
        "generator_mode": state.config.generator_mode,
        "dataset_path_used": dataset_path_used,
        "dataset_fallback_used": dataset_fallback_used,
        "local_corpus_size": state.local_corpus_size,
        "pulseplate_import_status": state.pulseplate_imports.status,
        "runtime_warnings": state.warnings,
        "strict_violations": state.strict_violations,
        "retrieval": retrieval_summary,
        "faithfulness": faithfulness_summary,
        "calibration": calibration_metrics,
        "routing": routing_summary,
        "context_compaction": context_compaction_summary,
        "thresholds": GATE_THRESHOLDS,
        "threshold_results": threshold_results,
        "gate_checks": gate_checks,
        "release_decision": release_decision,
        "small_fixture_metric_gates_advisory": small_fixture_advisory,
    }
    if small_fixture_raw_gate_checks is not None:
        metrics_summary["small_fixture_raw_gate_checks"] = small_fixture_raw_gate_checks
    if companion_metrics is not None:
        metrics_summary["companion_metrics"] = companion_metrics
    return metrics_summary, gate_checks, release_decision


def build_gate_report_markdown(metrics_summary: dict[str, Any]) -> str:
    """Render the gate report markdown."""

    retrieval = metrics_summary["retrieval"]
    faithfulness = metrics_summary["faithfulness"]
    calibration = metrics_summary["calibration"]
    routing = metrics_summary["routing"]
    gate_checks = metrics_summary["gate_checks"]
    threshold_results = metrics_summary.get("threshold_results", [])
    lines = [
        f"# PulsePlate RAG Release Gate Report — {metrics_summary['experiment_id']}",
        "",
        f"- Decision: **{metrics_summary['release_decision']}**",
        f"- Timestamp: `{metrics_summary['timestamp']}`",
        f"- Git SHA: `{metrics_summary['git_sha']}`",
        f"- Sample size: `{metrics_summary['sample_size']}`",
        f"- Dataset: `{metrics_summary['dataset_path_used']}`",
        f"- Dataset fallback used: `{metrics_summary['dataset_fallback_used']}`",
        f"- Retriever mode: `{metrics_summary['retriever_mode']}`",
        f"- Generator mode: `{metrics_summary['generator_mode']}`",
    ]
    if metrics_summary.get("small_fixture_metric_gates_advisory"):
        lines.extend(
            [
                "",
                "- **Small-fixture advisory lane:** gates A, B1-B3, and C2 are marked "
                "PASS here for CI on the canonical tiny sample; see "
                "`metrics_summary.json` → `small_fixture_raw_gate_checks` for raw "
                "threshold pass/fail before advisory override.",
            ],
        )
    lines.extend(
        [
            "",
            "## Gate checks",
        ],
    )
    lines.extend(
        f"- [{'x' if passed else ' '}] `{gate_name}`" for gate_name, passed in gate_checks.items()
    )
    if threshold_results:
        lines.extend(
            [
                "",
                "## Threshold results",
                "",
                "Gate | Metric | Value | Target | Comparison | Passed",
                "--- | --- | --- | --- | --- | ---",
                *[
                    (
                        f"`{row['gate_id']}` | `{row['metric_key']}` | "
                        f"`{_format_threshold_value(row['value'])}` | "
                        f"`{_format_threshold_target(row['target'])}` | "
                        f"`{row['comparison']}` | "
                        f"`{row['passed']}`"
                    )
                    for row in threshold_results
                ],
            ],
        )
    lines.extend(
        [
            "",
            "## Retrieval",
            *[f"- `{key}`: `{value}`" for key, value in retrieval.items()],
            "",
            "## Faithfulness",
            *[f"- `{key}`: `{value}`" for key, value in faithfulness.items()],
            "",
            "## Calibration",
            *[f"- `{key}`: `{value}`" for key, value in calibration.items()],
            "",
            "## Routing",
            *[f"- `{key}`: `{value}`" for key, value in routing.items()],
        ],
    )
    companion_metrics = metrics_summary.get("companion_metrics", {})
    ragas_metrics = companion_metrics.get("ragas") if isinstance(companion_metrics, dict) else None
    if isinstance(ragas_metrics, dict):
        lines.extend(
            [
                "",
                "## Companion RAGAS metrics",
                f"- Source path: `{ragas_metrics['source_path']}`",
                f"- Dataset path: `{ragas_metrics['dataset_path']}`",
                f"- Sample count: `{ragas_metrics['sample_count']}`",
                f"- Report only: `{ragas_metrics['report_only']}`",
                "",
                "Metric | Score",
                "--- | ---:",
                *[
                    f"`{metric_name}` | `{metric_value}`"
                    for metric_name, metric_value in ragas_metrics["metrics"].items()
                ],
            ],
        )
    if metrics_summary["runtime_warnings"]:
        lines.extend(
            [
                "",
                "## Runtime warnings",
                *[f"- `{warning}`" for warning in metrics_summary["runtime_warnings"]],
            ],
        )
    if metrics_summary.get("strict_violations"):
        lines.extend(
            [
                "",
                "## Strict mode violations",
                *[f"- `{violation}`" for violation in metrics_summary["strict_violations"]],
            ],
        )
    return "\n".join(lines)


def _json_default(obj: Any) -> Any:
    """Serialize non-JSON-native values into strings."""

    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def _canonical_json_bytes(payload: Any) -> bytes:
    """Serialize JSON for release-control-plane hashing."""

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=_json_default,
    )
    return f"{serialized}\n".encode("utf-8")


def _sha256_lower_hex(payload: bytes) -> str:
    """Return lowercase SHA-256 hex without an algorithm prefix."""

    return hashlib.new(RAG_GATE_RESULT_HASH_ALGORITHM, payload).hexdigest()


def _write_jsonl(path: Path, traces: Sequence[dict[str, Any]]) -> None:
    """Write traces as JSONL."""

    with path.open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(
                json.dumps(
                    trace,
                    ensure_ascii=False,
                    default=_json_default,
                )
                + "\n"
            )


def _flat_trace_rows(traces: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten traces for CSV/Parquet analytics export."""

    rows: list[dict[str, Any]] = []
    for trace in traces:
        top_hit = trace["top_k_retrieved"][0] if trace.get("top_k_retrieved") else {}
        faithfulness = trace.get("faithfulness_metrics", {}) or {}
        retrieval = trace.get("retrieval_metrics", {}) or {}
        rows.append(
            {
                "trace_id": trace.get("trace_id"),
                "timestamp": trace.get("timestamp"),
                "experiment_id": trace.get("experiment_id"),
                "query_id": trace.get("query_id"),
                "query_text": trace.get("query_text"),
                "confidence": trace.get("confidence"),
                "post_hoc_calibrated_confidence": trace.get(
                    "post_hoc_calibrated_confidence",
                ),
                "routing_decision": trace.get("routing_decision"),
                "latency": trace.get("latency"),
                "human_label_if_any": trace.get("human_label_if_any"),
                "recall_at_3": retrieval.get("recall_at_3"),
                "recall_at_10": retrieval.get("recall_at_10"),
                "recall_at_50": retrieval.get("recall_at_50"),
                "mrr_at_10": retrieval.get("mrr_at_10"),
                "ndcg_at_10": retrieval.get("ndcg_at_10"),
                "evidence_exact_match": faithfulness.get("evidence_exact_match"),
                "mean_nli_entailment": faithfulness.get("mean_nli_entailment"),
                "support_precision": faithfulness.get("support_precision"),
                "top_doc_id": top_hit.get("doc_id"),
                "top_source_url": top_hit.get("source_url"),
            },
        )
    return rows


def _write_flat_export(run_dir: Path, traces: Sequence[dict[str, Any]]) -> str:
    """Write Parquet when available; otherwise fall back to CSV."""

    flat_rows = _flat_trace_rows(traces)
    csv_path = run_dir / "traces.csv"
    parquet_path = run_dir / "traces.parquet"
    try:
        import pandas as pd

        pd.DataFrame(flat_rows).to_parquet(parquet_path, index=False)
        return str(parquet_path)
    except Exception:
        fieldnames = list(flat_rows[0].keys()) if flat_rows else []
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if fieldnames:
                writer.writeheader()
                writer.writerows(flat_rows)
        return str(csv_path)


def _run_dir_relative_path(path: Path, *, run_dir: Path) -> str:
    """Return a deterministic run-dir-relative artifact path."""

    resolved_path = path.resolve()
    resolved_run_dir = run_dir.resolve()
    try:
        return resolved_path.relative_to(resolved_run_dir).as_posix()
    except ValueError:
        return path.name


def _artifact_manifest_entry(kind: str, path: Path, *, run_dir: Path) -> dict[str, str]:
    """Build one safe eval artifact manifest entry."""

    return {
        "kind": kind,
        "path": _run_dir_relative_path(path, run_dir=run_dir),
        "hash": _sha256_lower_hex(path.read_bytes()),
    }


def build_eval_artifact_manifest(
    artifacts: dict[str, str],
    *,
    run_dir: Path,
) -> list[dict[str, str]]:
    """Return deterministic safe-artifact entries for the RAG gate export."""

    entries: list[dict[str, str]] = []
    for kind in RAG_GATE_SOURCE_ARTIFACT_KEYS:
        raw_path = artifacts.get(kind)
        if raw_path is None:
            continue
        path = Path(raw_path)
        if not path.is_file():
            continue
        entries.append(_artifact_manifest_entry(kind, path, run_dir=run_dir))
    return entries


def build_rag_gate_result_export(
    metrics_summary: dict[str, Any],
    artifacts: dict[str, str],
    *,
    run_dir: Path,
) -> dict[str, Any]:
    """Build the deterministic release-control-plane RAG gate result export."""

    source_artifacts = build_eval_artifact_manifest(artifacts, run_dir=run_dir)
    eval_artifact_hash = _sha256_lower_hex(
        _canonical_json_bytes(
            {
                "artifacts": source_artifacts,
                "canonicalization": RAG_GATE_RESULT_CANONICALIZATION,
                "schema_version": RAG_GATE_RESULT_SCHEMA_VERSION,
            }
        )
    )
    export_payload: dict[str, Any] = {
        "schema_version": RAG_GATE_RESULT_SCHEMA_VERSION,
        "hash_algorithm": RAG_GATE_RESULT_HASH_ALGORITHM,
        "canonicalization": RAG_GATE_RESULT_CANONICALIZATION,
        "experiment_id": metrics_summary["experiment_id"],
        "timestamp": metrics_summary["timestamp"],
        "git_sha": metrics_summary["git_sha"],
        "sample_size": metrics_summary["sample_size"],
        "retriever_mode": metrics_summary["retriever_mode"],
        "generator_mode": metrics_summary["generator_mode"],
        "dataset_path_used": metrics_summary["dataset_path_used"],
        "dataset_fallback_used": metrics_summary["dataset_fallback_used"],
        "release_decision": metrics_summary["release_decision"],
        "gate_checks": metrics_summary["gate_checks"],
        "threshold_results": metrics_summary.get("threshold_results", []),
        "strict_violations": metrics_summary.get("strict_violations", []),
        "runtime_warnings": metrics_summary.get("runtime_warnings", []),
        "small_fixture_metric_gates_advisory": metrics_summary.get(
            "small_fixture_metric_gates_advisory",
            False,
        ),
        "eval_artifact_hash": eval_artifact_hash,
        "source_artifacts": source_artifacts,
    }
    if "small_fixture_raw_gate_checks" in metrics_summary:
        export_payload["small_fixture_raw_gate_checks"] = metrics_summary[
            "small_fixture_raw_gate_checks"
        ]
    for optional_key in ("mlflow_run_id", "model_version"):
        optional_value = metrics_summary.get(optional_key)
        if optional_value:
            export_payload[optional_key] = optional_value

    export_payload["rag_gate_result_hash"] = _sha256_lower_hex(
        _canonical_json_bytes(export_payload)
    )
    return export_payload


def write_rag_gate_result_export(
    run_dir: Path,
    metrics_summary: dict[str, Any],
    artifacts: dict[str, str],
) -> Path:
    """Write the PR-2 RAG/ML gate-result export artifact."""

    export_path = run_dir / RAG_GATE_RESULT_FILENAME
    export_payload = build_rag_gate_result_export(metrics_summary, artifacts, run_dir=run_dir)
    export_path.write_text(
        json.dumps(export_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return export_path


def write_summary_notebook(
    run_dir: Path,
    metrics_summary: dict[str, Any],
    gate_report: str,
    *,
    template_notebook_path: Path | None = None,
) -> Path:
    """Write an executed notebook artifact derived from the tracked template."""

    notebook_path = run_dir / "latest_executed.ipynb"
    notebook: dict[str, Any]
    if template_notebook_path is not None:
        notebook = json.loads(template_notebook_path.read_text(encoding="utf-8"))
    else:
        notebook = {
            "cells": [],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }

    notebook.setdefault("cells", [])
    notebook["cells"].extend(
        [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# PulsePlate RAG Release Gates — Executed Summary\n",
                    "\n",
                    f"- Experiment: `{metrics_summary['experiment_id']}`\n",
                    f"- Decision: `{metrics_summary['release_decision']}`\n",
                    f"- Retriever mode: `{metrics_summary['retriever_mode']}`\n",
                    f"- Generator mode: `{metrics_summary['generator_mode']}`\n",
                    f"- Dataset: `{metrics_summary['dataset_path_used']}`\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": [gate_report + "\n"],
                    },
                ],
                "source": [
                    "# Generated by scripts/evals/run_rag_release_gates.py\n",
                    "print('See gate report below in the captured output cell.')\n",
                ],
            },
        ],
    )
    notebook_path.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return notebook_path


def write_artifacts(
    run_dir: Path,
    traces: list[dict[str, Any]],
    metrics_summary: dict[str, Any],
    *,
    template_notebook_path: Path | None = None,
) -> dict[str, str]:
    """Write the canonical artifact pack for the evaluation run."""

    run_dir.mkdir(parents=True, exist_ok=True)
    traces_path = run_dir / "traces.jsonl"
    metrics_path = run_dir / "metrics_summary.json"
    report_path = run_dir / "gate_report.md"

    _write_jsonl(traces_path, traces)
    parquet_or_csv_status = _write_flat_export(run_dir, traces)
    metrics_path.write_text(
        json.dumps(metrics_summary, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    gate_report = build_gate_report_markdown(metrics_summary)
    report_path.write_text(gate_report, encoding="utf-8")
    notebook_path = write_summary_notebook(
        run_dir,
        metrics_summary,
        gate_report,
        template_notebook_path=template_notebook_path,
    )
    artifacts = {
        "traces_jsonl": str(traces_path),
        "parquet_or_csv": parquet_or_csv_status,
        "metrics_summary": str(metrics_path),
        "gate_report": str(report_path),
        "latest_executed_notebook": str(notebook_path),
    }
    artifacts["rag_gate_result"] = str(
        write_rag_gate_result_export(run_dir, metrics_summary, artifacts)
    )
    return artifacts


def _write_github_step_summary(metrics_summary: dict[str, Any], artifacts: dict[str, str]) -> None:
    """Append a compact markdown summary for GitHub Actions."""

    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    summary_lines = [
        "## PulsePlate RAG Release Gates",
        "",
        f"- Decision: **{metrics_summary['release_decision']}**",
        f"- Sample size: `{metrics_summary['sample_size']}`",
        f"- Retriever mode: `{metrics_summary['retriever_mode']}`",
        f"- Generator mode: `{metrics_summary['generator_mode']}`",
        "",
        "### Artifacts",
        f"- Gate report: `{artifacts['gate_report']}`",
        f"- Metrics summary: `{artifacts['metrics_summary']}`",
        f"- RAG gate result: `{artifacts['rag_gate_result']}`",
        f"- Traces: `{artifacts['traces_jsonl']}`",
    ]
    threshold_results = metrics_summary.get("threshold_results", [])
    if threshold_results:
        summary_lines[6:6] = [
            "### Threshold results",
            "",
            "Gate | Value | Target | Comparison | Passed",
            "--- | --- | --- | --- | ---",
            *[
                (
                    f"`{row['gate_id']}` | "
                    f"`{_format_threshold_value(row['value'])}` | "
                    f"`{_format_threshold_target(row['target'])}` | "
                    f"`{row['comparison']}` | "
                    f"`{row['passed']}`"
                )
                for row in threshold_results
            ],
            "",
        ]
    companion_metrics = metrics_summary.get("companion_metrics", {})
    ragas_metrics = companion_metrics.get("ragas") if isinstance(companion_metrics, dict) else None
    if isinstance(ragas_metrics, dict):
        summary_lines.extend(
            [
                "",
                "### Companion RAGAS metrics",
                f"- Source path: `{ragas_metrics['source_path']}`",
                f"- Sample count: `{ragas_metrics['sample_count']}`",
                f"- Report only: `{ragas_metrics['report_only']}`",
                *[
                    f"- `{metric_name}`: `{metric_value}`"
                    for metric_name, metric_value in ragas_metrics["metrics"].items()
                ],
            ],
        )
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(summary_lines) + "\n")


def parse_bool_label(value: Any) -> int | None:
    """Normalize optional human labels into 0/1."""

    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return 1 if float(value) >= 0.5 else 0
    except (TypeError, ValueError):
        return None


def load_eval_input(
    path: Path,
    *,
    sample_size: int,
    random_seed: int,
    allow_fallback: bool,
) -> tuple[list[EvalRow], bool, str]:
    """Load JSONL/CSV/Parquet input with a deterministic fallback sample."""

    rows: list[dict[str, Any]]
    dataset_path_used = str(path.resolve())
    dataset_fallback_used = False
    if not path.exists():
        if not allow_fallback:
            raise FileNotFoundError(f"Evaluation input not found and fallback is disabled: {path}")
        rows = list(DEFAULT_SAMPLE_ROWS)
        dataset_fallback_used = True
        dataset_path_used = "embedded_smoke_fixture"
    elif path.suffix.lower() == ".jsonl":
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    elif path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    elif path.suffix.lower() == ".parquet":
        try:
            import pandas as pd
        except Exception as exc:  # pragma: no cover - env-dependent
            raise RuntimeError("Parquet input requires pandas + pyarrow/fastparquet") from exc
        rows = pd.read_parquet(path).to_dict(orient="records")
    else:
        raise ValueError("Unsupported evaluation input format. Use .jsonl, .csv, or .parquet.")

    normalized_rows: list[EvalRow] = []
    for index, row in enumerate(rows, start=1):
        query_text = str(row.get("query_text", "")).strip()
        if not query_text:
            continue
        normalized_rows.append(
            EvalRow(
                query_id=str(row.get("query_id") or f"row_{index:04d}"),
                query_text=query_text,
                gold_doc_ids=_json_or_list(row.get("gold_doc_ids")),
                gold_answer=str(row.get("gold_answer") or ""),
                expected_claims=_json_or_list(row.get("expected_claims")),
                evidence_quotes=_json_or_list(row.get("evidence_quotes")),
                user_tier=str(row.get("user_tier") or "PRO"),
                subject_id=coerce_subject_id(row.get("subject_id")),
                human_label_if_any=parse_bool_label(row.get("human_label_if_any")),
            ),
        )

    ordered_rows = sorted(
        normalized_rows,
        key=lambda row: stable_hash(
            [random_seed, row.query_id, row.query_text],
        ),
    )
    limited_rows = ordered_rows[:sample_size]
    return limited_rows, dataset_fallback_used, dataset_path_used


def build_config(args: argparse.Namespace) -> EvalConfig:
    """Resolve config from CLI args and env vars."""

    project_root = _resolve_path(
        args.project_root or os.getenv("PULSEPLATE_REPO_ROOT", REPO_ROOT),
    )
    if not project_root.is_dir():
        raise ValueError(f"project_root must exist and be a directory: {project_root}")
    input_path = _resolve_path(
        args.input_path or os.getenv("PULSEPLATE_RAG_EVAL_INPUT", DEFAULT_INPUT_PATH),
    )
    artifact_root = _resolve_path(
        args.artifact_root or os.getenv("PULSEPLATE_RAG_EVAL_ARTIFACT_ROOT", DEFAULT_ARTIFACT_ROOT),
    )
    notebook_path = _resolve_path(args.notebook_path or DEFAULT_NOTEBOOK_PATH)
    companion_metrics_json_raw = getattr(args, "companion_metrics_json", None) or os.getenv(
        "PULSEPLATE_RAG_COMPANION_METRICS_JSON"
    )
    companion_metrics_json = (
        _resolve_path(companion_metrics_json_raw) if companion_metrics_json_raw else None
    )
    experiment_id = sanitize_experiment_id(
        args.experiment_id
        or os.getenv(
            "EXPERIMENT_ID",
            f"rag_eval_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        )
    )
    _ensure_within(input_path, project_root, label="input_path")
    _ensure_within(artifact_root, project_root / "artifacts", label="artifact_root")
    if companion_metrics_json is not None:
        _ensure_within(
            companion_metrics_json,
            project_root / "artifacts" / "rag_eval",
            label="companion_metrics_json",
        )
    sample_size = _require_positive_int(
        _safe_int(
            args.sample_size or os.getenv("PULSEPLATE_RAG_EVAL_SAMPLE_SIZE", "500"),
            default=500,
        ),
        label="sample_size",
    )
    top_k = _require_positive_int(
        _safe_int(
            args.top_k or os.getenv("PULSEPLATE_RAG_EVAL_TOP_K", "50"),
            default=50,
        ),
        label="top_k",
    )
    return EvalConfig(
        project_root=project_root,
        input_path=input_path,
        artifact_root=artifact_root,
        experiment_id=experiment_id,
        sample_size=sample_size,
        top_k=top_k,
        random_seed=_safe_int(
            args.random_seed or os.getenv("PULSEPLATE_RAG_EVAL_RANDOM_SEED", "42"),
            default=42,
        ),
        retriever_mode=(args.retriever_mode or os.getenv("RETRIEVER_MODE", "local_tfidf"))
        .strip()
        .lower(),
        generator_mode=(args.generator_mode or os.getenv("GENERATOR_MODE", "extractive_stub"))
        .strip()
        .lower(),
        enable_nli_model=(args.enable_nli_model or _truthy_env(os.getenv("ENABLE_NLI_MODEL"))),
        nli_model_name=(
            args.nli_model_name or os.getenv("NLI_MODEL_NAME", "roberta-large-mnli")
        ).strip(),
        notebook_path=notebook_path,
        companion_metrics_json=companion_metrics_json,
        require_pass=bool(args.require_pass),
        allow_dataset_fallback=not bool(args.disallow_dataset_fallback),
        allow_runtime_fallbacks=not bool(args.disallow_runtime_fallbacks),
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(
        description="Run PulsePlate RAG release gates deterministically.",
    )
    parser.add_argument("--project-root")
    parser.add_argument("--input-path")
    parser.add_argument("--artifact-root")
    parser.add_argument("--experiment-id")
    parser.add_argument("--sample-size")
    parser.add_argument("--top-k")
    parser.add_argument("--random-seed")
    parser.add_argument(
        "--retriever-mode",
        choices=("local_tfidf", "pulseplate"),
    )
    parser.add_argument(
        "--generator-mode",
        choices=("extractive_stub", "pulseplate_runtime"),
    )
    parser.add_argument("--enable-nli-model", action="store_true")
    parser.add_argument("--nli-model-name")
    parser.add_argument("--notebook-path")
    parser.add_argument(
        "--companion-metrics-json",
        help="Optional informational companion metrics JSON emitted by evals/ragas.",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Exit non-zero when the release decision is NO-GO.",
    )
    parser.add_argument(
        "--disallow-dataset-fallback",
        action="store_true",
        help="Fail when the requested dataset is missing instead of using the embedded smoke fixture.",
    )
    parser.add_argument(
        "--disallow-runtime-fallbacks",
        action="store_true",
        help="Mark runtime retriever/generator degradations as strict violations.",
    )
    return parser


async def async_main(args: argparse.Namespace) -> int:
    """Execute the release-gates run."""

    config = build_config(args)
    companion_metrics = _load_companion_metrics(
        config.companion_metrics_json,
        project_root=config.project_root,
    )
    imports = load_pulseplate_imports()
    state = EvalRuntimeState(config=config, pulseplate_imports=imports)
    rows, dataset_fallback_used, dataset_path_used = load_eval_input(
        config.input_path,
        sample_size=config.sample_size,
        random_seed=config.random_seed,
        allow_fallback=config.allow_dataset_fallback,
    )
    traces = await run_evaluation(state, rows)
    calibration_metrics = apply_calibration(traces)
    metrics_summary, _, release_decision = build_metrics_summary(
        state,
        traces,
        calibration_metrics,
        dataset_fallback_used=dataset_fallback_used,
        dataset_path_used=dataset_path_used,
        companion_metrics=companion_metrics,
    )
    run_dir = config.artifact_root / config.experiment_id
    artifacts = write_artifacts(
        run_dir,
        traces,
        metrics_summary,
        template_notebook_path=config.notebook_path,
    )

    # Validity sidecar: informational measurement artifacts.
    # Does NOT change threshold_results or PASS/NO-GO release decision.
    try:
        from scripts.evals.rag_release_gate_validity import write_validity_sidecar

        validity_sidecar = write_validity_sidecar(run_dir, traces)
        artifacts.update(validity_sidecar)
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: validity sidecar generation failed: {exc}")

    _write_github_step_summary(metrics_summary, artifacts)

    print("PulsePlate import status:", json.dumps(imports.status, indent=2))
    if imports.import_errors:
        print("PulsePlate import errors:", json.dumps(imports.import_errors, indent=2))
    print("Artifacts:")
    for name, value in artifacts.items():
        print(f"  {name}: {value}")
    print("Release decision:", release_decision)

    if config.require_pass and release_decision != "PASS":
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
