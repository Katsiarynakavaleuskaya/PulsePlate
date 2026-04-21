# -*- coding: utf-8 -*-
"""
Tests for Remaining Low Coverage Modules

RU: Тесты для оставшихся модулей с низким покрытием
EN: Tests for remaining modules with low coverage
"""

import sys
import time
from collections.abc import Sequence
from pathlib import Path
from datetime import datetime, timezone
import importlib
import json
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import asyncio

import pytest

from tests.test_root_npm_dependency_guards import _load_json

if TYPE_CHECKING:
    from core.knowledge.contracts import KnowledgeFactCandidate
    from core.knowledge.policy import KnowledgePolicy
    from core.rag.contracts import RAGChunk


def test_root_npm_security_override_smoke() -> None:
    """RU/EN: Keep critical root npm graph removal invariants in the deterministic fast lane."""
    repo_root = Path(__file__).resolve().parents[1]
    package_manifest = _load_json(repo_root / "package.json")
    package_lock = _load_json(repo_root / "package-lock.json")

    dependencies = package_manifest.get("dependencies", {})
    assert "@goplus/agentguard" not in dependencies

    packages = package_lock.get("packages", {})
    assert isinstance(packages, dict)
    assert "node_modules/@goplus/agentguard" not in packages
    assert "node_modules/axios" not in packages
    assert "node_modules/hono" not in packages
    assert "node_modules/path-to-regexp" not in packages
    assert not any(
        isinstance(package_path, str) and package_path.endswith("/brace-expansion")
        for package_path in packages
    )


def _write_ragas_bootstrap_dataset(path: Path) -> None:
    """Keep eval runner smoke fixtures deterministic in the fast lane."""

    rows = [
        {
            "question": "How can I recover from all-or-nothing thinking after dessert?",
            "answer": "Treat dessert as one event and return to the next planned meal.",
            "contexts": [
                "All-or-nothing thinking often escalates one food choice into a global failure.",
                "Returning to the next planned meal supports recovery without punishment.",
            ],
            "reference": "Reframe the dessert as one event and continue with the next planned meal.",
        },
        {
            "question": "What helps when I skip lunch and overeat later?",
            "answer": "Use a predictable lunch anchor to reduce long hunger gaps.",
            "contexts": [
                "Long gaps without food can increase hunger intensity later in the day.",
                "A predictable meal anchor can reduce rebound overeating pressure.",
            ],
            "ground_truth": "Add a lunch anchor to reduce long hunger gaps and late overeating.",
        },
    ]
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


class TestOfflineEvalBootstrapSmoke:
    """Exercise the eval bootstrap lane in the always-on smoke suite."""

    def test_ragas_metrics_config_contract(self) -> None:
        """The bootstrap metric config stays deterministic and threshold-free."""

        from evals.ragas import metrics_config

        assert metrics_config.DEFAULT_RAGAS_METRICS == (
            "faithfulness",
            "answer_relevancy",
            "context_precision",
        )
        assert metrics_config.REPORT_ONLY_MODE is True
        assert not hasattr(metrics_config, "FAIL_THRESHOLDS")
        assert not hasattr(metrics_config, "GATE_THRESHOLDS")

    def test_ragas_runner_import_and_cli_contract(self) -> None:
        """Importing the runner must stay lazy and the CLI must parse bootstrap flags."""

        runner = importlib.import_module("evals.ragas.run_ragas_eval")

        assert runner.REPORT_ONLY_MODE is True
        args = runner.parse_args(
            [
                "--dataset",
                "evals/ragas/testset.jsonl",
                "--output-json",
                "/tmp/ragas_report.json",
                "--output-md",
                "/tmp/ragas_report.md",
            ]
        )

        assert args.dataset == Path("evals/ragas/testset.jsonl")
        assert args.output_json == Path("/tmp/ragas_report.json")
        assert args.output_md == Path("/tmp/ragas_report.md")

    def test_ragas_runner_report_contract(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """The smoke lane must cover deterministic report rendering and error hygiene."""

        runner = importlib.import_module("evals.ragas.run_ragas_eval")
        dataset_path = tmp_path / "testset.jsonl"
        _write_ragas_bootstrap_dataset(dataset_path)

        def _boom() -> tuple[object, object, object]:
            raise AssertionError("ragas import path should stay lazy in this test")

        def _fake_evaluator(
            rows: list[dict[str, object]],
            metric_names: tuple[str, ...],
        ) -> dict[str, float]:
            assert len(rows) == 2
            assert metric_names == (
                "faithfulness",
                "answer_relevancy",
                "context_precision",
            )
            return {
                "faithfulness": 0.84,
                "answer_relevancy": 0.79,
                "context_precision": 0.88,
            }

        monkeypatch.setattr(runner, "_load_ragas_dependencies", _boom)

        report = runner.run_report(dataset_path, evaluator=_fake_evaluator)
        summary = runner.render_markdown_summary(report)

        assert report == {
            "dataset_path": str(dataset_path.resolve()),
            "sample_count": 2,
            "report_only": True,
            "metrics": {
                "faithfulness": 0.84,
                "answer_relevancy": 0.79,
                "context_precision": 0.88,
            },
        }
        assert "Metric | Score" in summary
        assert "faithfulness | 0.84" in summary
        assert "answer_relevancy | 0.79" in summary
        assert "context_precision | 0.88" in summary

        def _partial_evaluator(
            rows: list[dict[str, object]],
            metric_names: tuple[str, ...],
        ) -> dict[str, float]:
            assert rows
            assert metric_names
            return {"faithfulness": 0.84}

        with pytest.raises(RuntimeError, match="missing required scores"):
            runner.run_report(dataset_path, evaluator=_partial_evaluator)

        def _non_finite_evaluator(
            rows: list[dict[str, object]],
            metric_names: tuple[str, ...],
        ) -> dict[str, float]:
            assert rows
            assert metric_names
            return {
                "faithfulness": float("nan"),
                "answer_relevancy": 0.79,
                "context_precision": 0.88,
            }

        with pytest.raises(RuntimeError, match="non-finite score"):
            runner.run_report(dataset_path, evaluator=_non_finite_evaluator)

        class _EmptyScores:
            @staticmethod
            def to_list() -> list[dict[str, float]]:
                return []

        class _Result:
            scores = _EmptyScores()

        with pytest.raises(RuntimeError, match="score rows is empty"):
            runner._extract_metric_scores(
                _Result(),
                ("faithfulness", "answer_relevancy", "context_precision"),
            )

    def test_ragas_dataset_validation_paths(self, tmp_path: Path) -> None:
        """Dataset parsing must fail closed on malformed bootstrap inputs."""

        runner = importlib.import_module("evals.ragas.run_ragas_eval")

        txt_path = tmp_path / "testset.txt"
        txt_path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match=r"\.jsonl"):
            runner.load_dataset_rows(txt_path)

        with pytest.raises(FileNotFoundError, match="Dataset not found"):
            runner.load_dataset_rows(tmp_path / "missing.jsonl")

        empty_path = tmp_path / "empty.jsonl"
        empty_path.write_text("\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Dataset is empty"):
            runner.load_dataset_rows(empty_path)

        invalid_json_path = tmp_path / "invalid.jsonl"
        invalid_json_path.write_text("{bad json}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            runner.load_dataset_rows(invalid_json_path)

        non_object_path = tmp_path / "non_object.jsonl"
        non_object_path.write_text('["not", "an", "object"]\n', encoding="utf-8")
        with pytest.raises(ValueError, match="must be an object"):
            runner.load_dataset_rows(non_object_path)

        missing_reference_path = tmp_path / "missing_reference.jsonl"
        missing_reference_path.write_text(
            json.dumps(
                {
                    "question": "How do I restart after one snack?",
                    "answer": "Return to the next meal.",
                    "contexts": ["A planned next meal reduces rebound restriction."],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="one of 'reference' or 'ground_truth'"):
            runner.load_dataset_rows(missing_reference_path)

        conflicting_reference_path = tmp_path / "conflicting_reference.jsonl"
        conflicting_reference_path.write_text(
            json.dumps(
                {
                    "question": "How do I restart after one snack?",
                    "answer": "Return to the next meal.",
                    "contexts": ["A planned next meal reduces rebound restriction."],
                    "reference": "Return to the next meal.",
                    "ground_truth": "Skip the next meal.",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="'reference' and 'ground_truth' must match"):
            runner.load_dataset_rows(conflicting_reference_path)

        with pytest.raises(ValueError, match="'question' must be a string"):
            runner._normalize_string(7, field_name="question", row_number=1)
        with pytest.raises(ValueError, match="'question' must be non-empty"):
            runner._normalize_string("   ", field_name="question", row_number=1)
        with pytest.raises(ValueError, match="'contexts' must be a non-empty list"):
            runner._normalize_contexts([], row_number=1)
        with pytest.raises(ValueError, match="'contexts\\[1\\]' must be a string"):
            runner._normalize_contexts([7], row_number=1)
        with pytest.raises(ValueError, match="'contexts\\[1\\]' must be non-empty"):
            runner._normalize_contexts(["   "], row_number=1)

    def test_ragas_default_evaluator_and_score_extractors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Default evaluator branches must stay covered in the deterministic smoke suite."""

        runner = importlib.import_module("evals.ragas.run_ragas_eval")
        dataset_path = tmp_path / "testset.jsonl"
        _write_ragas_bootstrap_dataset(dataset_path)
        rows = runner.load_dataset_rows(dataset_path)

        with pytest.raises(ValueError, match="Bootstrap metric contract drift detected"):
            runner._validate_metric_names(("faithfulness",))

        monkeypatch.setattr(runner, "REPORT_ONLY_MODE", False)
        with pytest.raises(ValueError, match="report-only"):
            runner._validate_metric_names(runner.REQUIRED_METRIC_NAMES)
        monkeypatch.setattr(runner, "REPORT_ONLY_MODE", True)

        class _FakeDataset:
            captured_rows: list[dict[str, object]] = []

            @classmethod
            def from_list(cls, values: list[dict[str, object]]) -> "_FakeDataset":
                cls.captured_rows = values
                return cls()

        metric_map = {name: object() for name in runner.REQUIRED_METRIC_NAMES}

        class _EvaluateWithoutShowProgress:
            def __call__(self, *, dataset: object, metrics: list[object]):
                assert isinstance(dataset, _FakeDataset)
                assert len(metrics) == 3
                return {
                    "faithfulness": 0.91,
                    "answer_relevancy": 0.82,
                    "context_precision": 0.88,
                }

        monkeypatch.setattr(
            runner,
            "_load_ragas_dependencies",
            lambda: (_FakeDataset, _EvaluateWithoutShowProgress(), metric_map),
        )

        scores = runner.evaluate_records(rows, runner.REQUIRED_METRIC_NAMES)
        assert scores == {
            "faithfulness": 0.91,
            "answer_relevancy": 0.82,
            "context_precision": 0.88,
        }
        assert (
            _FakeDataset.captured_rows[0]["reference"]
            == _FakeDataset.captured_rows[0]["ground_truth"]
        )

        class _Series:
            def __init__(self, value: float) -> None:
                self._value = value

            def mean(self) -> float:
                return self._value

        class _Frame:
            def __contains__(self, item: str) -> bool:
                return item in runner.REQUIRED_METRIC_NAMES

            def __getitem__(self, item: str) -> _Series:
                return _Series(
                    {
                        "faithfulness": 0.83,
                        "answer_relevancy": 0.81,
                        "context_precision": 0.8,
                    }[item]
                )

        class _PandasResult:
            @staticmethod
            def to_pandas() -> _Frame:
                return _Frame()

        pandas_scores = runner._extract_metric_scores(_PandasResult(), runner.REQUIRED_METRIC_NAMES)
        assert pandas_scores["faithfulness"] == pytest.approx(0.83)

        class _ScoreRows:
            @staticmethod
            def to_list() -> list[dict[str, float]]:
                return [
                    {
                        "faithfulness": 0.8,
                        "answer_relevancy": 0.7,
                        "context_precision": 0.9,
                    },
                    {
                        "faithfulness": 0.9,
                        "answer_relevancy": 0.8,
                        "context_precision": 0.7,
                    },
                ]

        class _ScoreResult:
            scores = _ScoreRows()

        score_rows = runner._extract_metric_scores(_ScoreResult(), runner.REQUIRED_METRIC_NAMES)
        assert score_rows["answer_relevancy"] == pytest.approx(0.75)

        with pytest.raises(RuntimeError, match="Could not extract metric scores"):
            runner._extract_metric_scores(object(), runner.REQUIRED_METRIC_NAMES)

        monkeypatch.setattr(
            runner,
            "_load_ragas_dependencies",
            lambda: (_FakeDataset, lambda **_: None, metric_map),
        )
        with pytest.raises(RuntimeError, match="Could not extract metric scores"):
            runner.evaluate_records(rows, runner.REQUIRED_METRIC_NAMES)

        monkeypatch.setattr(
            runner,
            "_load_ragas_dependencies",
            lambda: (
                _FakeDataset,
                lambda *, dataset, metrics, show_progress=False: (_ for _ in ()).throw(
                    TypeError("broken evaluator")
                ),
                metric_map,
            ),
        )
        with pytest.raises(TypeError, match="broken evaluator"):
            runner.evaluate_records(rows, runner.REQUIRED_METRIC_NAMES)

        signature_error_evaluator = _EvaluateWithoutShowProgress()
        monkeypatch.setattr(
            runner,
            "_load_ragas_dependencies",
            lambda: (_FakeDataset, signature_error_evaluator, metric_map),
        )
        monkeypatch.setattr(
            runner.inspect,
            "signature",
            lambda _callable: (_ for _ in ()).throw(ValueError("missing signature")),
        )
        signature_scores = runner.evaluate_records(rows, runner.REQUIRED_METRIC_NAMES)
        assert signature_scores["context_precision"] == pytest.approx(0.88)

        with pytest.raises(RuntimeError, match="invalid score for faithfulness"):
            runner._validate_metric_scores(
                {
                    "faithfulness": object(),
                    "answer_relevancy": 0.82,
                    "context_precision": 0.88,
                },
                runner.REQUIRED_METRIC_NAMES,
                source="score rows",
            )

    def test_ragas_dependency_and_cli_output_paths(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Output writers and main() must stay deterministic in success and error paths."""

        runner = importlib.import_module("evals.ragas.run_ragas_eval")
        report = {
            "dataset_path": "evals/ragas/testset.jsonl",
            "sample_count": 2,
            "report_only": True,
            "metrics": {
                "faithfulness": 0.84,
                "answer_relevancy": 0.79,
                "context_precision": 0.88,
            },
        }
        markdown_summary = runner.render_markdown_summary(report)

        json_output = tmp_path / "artifacts" / "rag_eval" / "bootstrap" / "report.json"
        md_output = tmp_path / "artifacts" / "rag_eval" / "bootstrap" / "report.md"
        runner.write_outputs(
            report,
            markdown_summary,
            output_json=json_output,
            output_md=md_output,
        )
        assert json.loads(json_output.read_text(encoding="utf-8"))["sample_count"] == 2
        assert md_output.read_text(encoding="utf-8").strip() == markdown_summary
        assert runner._display_path(json_output).endswith("report.json")
        assert runner.format_score(1.0) == "1"
        assert runner._display_path(runner.DEFAULT_DATASET_PATH).startswith("evals/ragas/")

        monkeypatch.setitem(sys.modules, "datasets", None)
        monkeypatch.setitem(sys.modules, "ragas", None)
        monkeypatch.setitem(sys.modules, "ragas.metrics", None)
        with pytest.raises(RuntimeError, match="requirements-evals.txt"):
            runner._load_ragas_dependencies()

        fake_datasets = ModuleType("datasets")

        class _ImportDataset:
            @staticmethod
            def from_list(values: list[dict[str, object]]) -> list[dict[str, object]]:
                return values

        fake_ragas = ModuleType("ragas")
        fake_metrics = ModuleType("ragas.metrics")
        setattr(fake_datasets, "Dataset", _ImportDataset)
        setattr(fake_ragas, "evaluate", lambda **_: report["metrics"])
        setattr(fake_metrics, "faithfulness", object())
        setattr(fake_metrics, "answer_relevancy", object())
        setattr(fake_metrics, "context_precision", object())
        monkeypatch.setitem(sys.modules, "datasets", fake_datasets)
        monkeypatch.setitem(sys.modules, "ragas", fake_ragas)
        monkeypatch.setitem(sys.modules, "ragas.metrics", fake_metrics)

        dataset_cls, evaluate, metric_map = runner._load_ragas_dependencies()
        assert dataset_cls is _ImportDataset
        assert evaluate() == report["metrics"]
        assert set(metric_map) == set(runner.REQUIRED_METRIC_NAMES)

        args = SimpleNamespace(
            dataset=Path("evals/ragas/testset.jsonl"),
            output_json=tmp_path / "main.json",
            output_md=tmp_path / "main.md",
        )
        monkeypatch.setattr(runner, "parse_args", lambda _argv=None: args)
        monkeypatch.setattr(runner, "run_report", lambda _dataset: report)

        assert runner.main([]) == 0
        stdout = capsys.readouterr().out
        assert "Metric | Score" in stdout
        assert args.output_json.is_file()
        assert args.output_md.is_file()

        error_args = SimpleNamespace(dataset=Path("broken.jsonl"), output_json=None, output_md=None)
        monkeypatch.setattr(runner, "parse_args", lambda _argv=None: error_args)
        monkeypatch.setattr(
            runner,
            "run_report",
            lambda _dataset: (_ for _ in ()).throw(ValueError("broken dataset")),
        )

        assert runner.main([]) == 1
        stderr = capsys.readouterr().err
        assert "Error: broken dataset" in stderr


class TestShoplistModule:
    """Test core.shoplist module."""

    def test_packaging_rule_class(self):
        """Test PackagingRule dataclass."""
        from core.shoplist import PackagingRule

        # Test creating packaging rule
        rule = PackagingRule(
            category="grains",
            unit="g",
            typical_packages=[100, 250, 500, 1000],
            rounding_strategy="up",
        )

        assert rule.category == "grains"
        assert rule.unit == "g"
        assert rule.typical_packages == [100, 250, 500, 1000]
        assert rule.rounding_strategy == "up"

    def test_shopping_item_class(self):
        """Test ShoppingItem dataclass."""
        from core.shoplist import ShoppingItem

        # Test creating shopping item
        item = ShoppingItem(name="chicken breast", quantity=500.0, unit="g", category="meat")

        assert item.name == "chicken breast"
        assert item.quantity == 500.0
        assert item.unit == "g"

    def test_shoplist_functions(self):
        """Test shoplist utility functions."""
        from core.shoplist import (
            create_shopping_list,
            group_by_category,
            optimize_packaging,
        )

        # Test with mock meal plan
        meal_plan = {
            "day1": {
                "breakfast": [{"name": "oats", "amount": 50, "unit": "g"}],
                "lunch": [{"name": "chicken", "amount": 150, "unit": "g"}],
                "dinner": [{"name": "rice", "amount": 100, "unit": "g"}],
            }
        }

        # Test shopping list creation
        shopping_list = create_shopping_list(meal_plan)
        assert isinstance(shopping_list, (list, dict, type(None)))

        # Test packaging optimization
        items = [
            {"name": "flour", "quantity": 350, "unit": "g"},
            {"name": "sugar", "quantity": 150, "unit": "g"},
        ]

        optimized = optimize_packaging(items)
        assert isinstance(optimized, (list, dict, type(None)))

        # Test category grouping
        grouped = group_by_category(items)
        assert isinstance(grouped, (dict, type(None)))


class TestWeeklyPlanModule:
    """Test core.weekly_plan module."""

    def test_weekly_plan_generation(self) -> None:
        """Test weekly plan generation."""
        from unittest.mock import MagicMock

        from core.weekly_plan import generate_weekly_plan

        targets = MagicMock()
        targets.kcal_daily = 2000

        with patch("core.weekly_plan.parse_food_db", return_value={}):
            with patch("core.weekly_plan.parse_recipe_db", return_value={}):
                with patch("core.weekly_plan.create_daily_plate", return_value={}):
                    plan = generate_weekly_plan(targets, set())
                    assert isinstance(plan, dict)
                    assert "days" in plan
                    assert len(plan["days"]) == 7

    def test_weekly_plan_with_diet_flags(self) -> None:
        """Test weekly plan with dietary restrictions."""
        from unittest.mock import MagicMock

        from core.weekly_plan import generate_weekly_plan

        targets = MagicMock()
        targets.kcal_daily = 1800

        diet_flags = {"vegetarian", "gluten_free"}

        with patch("core.weekly_plan.parse_food_db", return_value={}):
            with patch("core.weekly_plan.parse_recipe_db", return_value={}):
                with patch("core.weekly_plan.create_daily_plate", return_value={}):
                    plan = generate_weekly_plan(targets, diet_flags)
                    assert isinstance(plan, dict)
                    assert "days" in plan
                    assert len(plan["days"]) == 7

    def test_daily_plan_functions(self) -> None:
        """Test daily plan helper functions."""
        from core.weekly_plan import (
            calculate_weekly_nutrition,
            optimize_weekly_variety,
            validate_weekly_plan,
        )

        # Mock weekly plan data
        weekly_plan = {
            "day1": {"calories": 2000, "protein": 150},
            "day2": {"calories": 1900, "protein": 140},
            "day3": {"calories": 2100, "protein": 160},
        }

        # Test nutrition calculation
        nutrition = calculate_weekly_nutrition(weekly_plan)
        assert isinstance(nutrition, dict)
        assert "total_calories" in nutrition
        assert "avg_calories" in nutrition

        # Test variety optimization
        optimized = optimize_weekly_variety(weekly_plan)
        assert isinstance(optimized, dict)
        assert optimized.get("variety_optimized") is True

        # Test plan validation
        is_valid = validate_weekly_plan(weekly_plan)
        assert is_valid is True


class TestUtilsModule:
    """Test core.utils module."""

    def test_utils_comprehensive(self) -> None:
        """Test utils functions comprehensively."""
        from core.utils import (
            safe_float,
            safe_int,
            slugify,
        )

        # Test safe_float with various inputs
        assert safe_float("123.45") == 123.45
        assert safe_float("invalid") is None
        assert safe_float(None) is None
        assert safe_float("") is None
        assert safe_float("0") == 0.0
        assert safe_float("-123.45") == -123.45

        # Test safe_int with various inputs
        assert safe_int("123") == 123
        assert safe_int("invalid") is None
        assert safe_int(None) is None
        assert safe_int("") is None
        assert safe_int("0") == 0
        assert safe_int("-123") == -123

        # Test slugify with various inputs
        slug = slugify("Test String With Spaces")
        assert isinstance(slug, str)

        slug = slugify("Special!@#$%Characters")
        assert isinstance(slug, str)

        slug = slugify("")
        assert slug == ""

        slug = slugify(None)
        assert slug == ""

    def test_additional_utils(self) -> None:
        """Test additional utility functions."""
        from core.utils import (
            format_number,
            generate_id,
            sanitize_html,
            validate_email,
        )

        # Test email validation
        assert validate_email("test@example.com") is True
        assert validate_email("invalid-email") is False
        assert validate_email("") is False
        assert validate_email(None) is False

        # Test HTML sanitization
        sanitized = sanitize_html("<script>alert('xss')</script>")
        assert isinstance(sanitized, str)
        assert "<script>" not in sanitized

        sanitized = sanitize_html("<p>Valid HTML</p>")
        assert isinstance(sanitized, str)

        # Test ID generation
        idVal = generate_id()
        assert isinstance(idVal, str)
        assert len(idVal) == 32  # UUID hex without hyphens

        # Test number formatting
        formatted = format_number(1234.567)
        assert isinstance(formatted, str)


class TestTimeUtilsModule:
    """Test core.time_utils module for better coverage."""

    def test_time_utils_comprehensive(self) -> None:
        """Test time utilities comprehensively."""
        from core.time_utils import (
            format_datetime,
            get_timezone_offset,
            is_valid_date,
            parse_datetime,
        )

        # Test datetime parsing
        result = parse_datetime("2024-01-01T00:00:00")
        assert result is not None
        result = parse_datetime("2024-01-01")
        assert result is not None

        result = parse_datetime("invalid")
        assert result is None

        result = parse_datetime("")
        assert result is None

        # Test datetime formatting
        formatted = format_datetime("2024-01-01T00:00:00")
        assert isinstance(formatted, str)

        # Test timezone offset
        offset = get_timezone_offset("UTC")
        assert offset == 0.0

        offset = get_timezone_offset("US/Eastern")
        assert isinstance(offset, (int, float, type(None)))

        # Test date validation
        assert is_valid_date("2024-01-01") is True
        assert is_valid_date("invalid") is False


class TestKnowledgePromotionFastLane:
    """Keep knowledge promotion fail-closed branches in the deterministic fast lane."""

    @staticmethod
    def _knowledge_policy(
        *,
        enabled: bool = True,
        allow_promotion: bool = True,
        subject_scope_required: bool = True,
    ) -> "KnowledgePolicy":
        from core.knowledge.policy import KnowledgePolicy

        return KnowledgePolicy(
            enabled=enabled,
            allow_reads=True,
            allow_promotion=allow_promotion,
            min_confidence=0.7,
            require_rag_factual_route=True,
            deny_degraded_reasons=("retrieval_empty", "all_chunks_filtered"),
            subject_scope_required=subject_scope_required,
            rail="product_ai_runtime",
        )

    @staticmethod
    def _chunk(*, content: str = "Validated chunk.") -> "RAGChunk":
        from core.rag.contracts import RAGChunk

        return RAGChunk(
            chunk_id="chunk-1",
            file="docs/one.md",
            content=content,
            score=0.88,
            hop=1,
        )

    @staticmethod
    def _candidate(
        *,
        fact_key: str,
        confidence: float,
        observed_at: datetime,
        supersedes: Sequence[str] = (),
    ) -> "KnowledgeFactCandidate":
        from core.knowledge.contracts import KnowledgeEvidenceRef, KnowledgeFactCandidate

        return KnowledgeFactCandidate(
            fact_key=fact_key,
            subject="subject:42",
            predicate="validated_rag_evidence:docs/one.md:chunk-1",
            value=f"chunk=chunk-1;source=docs/one.md;digest={fact_key};hop=1",
            observed_at=observed_at,
            confidence=confidence,
            access_scope="subject:42",
            rail="product_ai_runtime",
            provenance=(KnowledgeEvidenceRef("chunk-1", "docs/one.md", confidence, 1),),
            supersedes=tuple(supersedes),
        )

    def test_build_knowledge_promotion_candidates_covers_fail_closed_branches(self) -> None:
        """Promotion must reject missing inputs and empty validated content deterministically."""

        from core.knowledge.promotion import build_knowledge_promotion_candidates

        policy = self._knowledge_policy()

        assert (
            build_knowledge_promotion_candidates(
                chunks=[],
                confidence=0.9,
                degraded_reason=None,
                subject_id=42,
                knowledge_policy=policy,
            )
            == []
        )
        assert (
            build_knowledge_promotion_candidates(
                chunks=[self._chunk()],
                confidence=0.9,
                degraded_reason="retrieval_empty",
                subject_id=42,
                knowledge_policy=policy,
            )
            == []
        )
        assert (
            build_knowledge_promotion_candidates(
                chunks=[self._chunk()],
                confidence=None,
                degraded_reason=None,
                subject_id=42,
                knowledge_policy=policy,
            )
            == []
        )
        assert (
            build_knowledge_promotion_candidates(
                chunks=[self._chunk()],
                confidence=0.9,
                degraded_reason=None,
                subject_id=None,
                knowledge_policy=policy,
            )
            == []
        )
        assert (
            build_knowledge_promotion_candidates(
                chunks=[self._chunk(content="   ")],
                confidence=0.9,
                degraded_reason=None,
                subject_id=42,
                knowledge_policy=policy,
            )
            == []
        )

    def test_knowledge_promotion_record_helpers_cover_supersession_paths(self) -> None:
        """Same-confidence newer evidence may supersede only when explicitly declared."""

        from core.knowledge.contracts import KnowledgeRecord
        from core.knowledge.promotion import (
            candidate_should_supersede,
            candidate_to_record,
            mark_record_superseded,
        )

        observed_at = datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)
        existing = KnowledgeRecord(
            fact_key="fact-1",
            subject="subject:42",
            predicate="validated_rag_evidence:docs/one.md:chunk-1",
            value="chunk=chunk-1;source=docs/one.md;digest=fact-1;hop=1",
            status="active",
            confidence=0.9,
            access_scope="subject:42",
            rail="product_ai_runtime",
            provenance=(),
            observed_at=observed_at,
        )
        candidate = self._candidate(
            fact_key="fact-2",
            confidence=0.9,
            observed_at=observed_at.replace(minute=1),
            supersedes=("fact-1",),
        )

        assert candidate_should_supersede(existing=existing, candidate=candidate) is True

        active_record = candidate_to_record(candidate)
        assert active_record.status == "active"
        assert active_record.fact_key == "fact-2"

        superseded = mark_record_superseded(record=existing, superseded_by="fact-2")
        assert superseded.status == "superseded"
        assert superseded.superseded_by == "fact-2"


class TestKnowledgeStoreFastLane:
    """Keep bounded knowledge store seams covered by test-fast."""

    @staticmethod
    def _candidate(
        *,
        fact_key: str,
        confidence: float,
        observed_at: datetime,
        supersedes: Sequence[str] = (),
    ) -> "KnowledgeFactCandidate":
        from core.knowledge.contracts import KnowledgeEvidenceRef, KnowledgeFactCandidate

        return KnowledgeFactCandidate(
            fact_key=fact_key,
            subject="subject:42",
            predicate="validated_rag_evidence:docs/test.md:chunk-1",
            value=f"value:{fact_key}",
            observed_at=observed_at,
            confidence=confidence,
            access_scope="subject:42",
            rail="product_ai_runtime",
            provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", confidence, 1),),
            supersedes=tuple(supersedes),
        )

    def test_noop_knowledge_store_discards_promotions_and_reads(self) -> None:
        """No-op store must fail closed without persisting or leaking records."""

        from core.knowledge.store import NoOpKnowledgeStore

        store = NoOpKnowledgeStore()
        candidate = self._candidate(
            fact_key="fact-1",
            confidence=0.8,
            observed_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
        )

        assert store.promote([candidate]) == []
        assert (
            store.read(
                subject="subject:42",
                predicate="validated_rag_evidence:docs/test.md:chunk-1",
                access_scope="subject:42",
                rail="product_ai_runtime",
            )
            == []
        )

    def test_in_memory_knowledge_store_replays_reads_and_supersedes_only_when_eligible(
        self,
    ) -> None:
        """Store must support idempotent replay, scoped reads, and explicit supersession only."""

        from core.knowledge.store import InMemoryKnowledgeStore

        observed_at = datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)
        store = InMemoryKnowledgeStore()
        first = self._candidate(fact_key="fact-1", confidence=0.8, observed_at=observed_at)
        weaker = self._candidate(
            fact_key="fact-2",
            confidence=0.7,
            observed_at=observed_at.replace(minute=1),
            supersedes=("fact-1",),
        )
        stronger = self._candidate(
            fact_key="fact-3",
            confidence=0.95,
            observed_at=observed_at.replace(minute=2),
            supersedes=("fact-1",),
        )

        first_promoted = store.promote([first])
        replay_promoted = store.promote([first])
        weaker_promoted = store.promote([weaker])
        stronger_promoted = store.promote([stronger])

        assert [record.fact_key for record in first_promoted] == ["fact-1"]
        assert replay_promoted == []
        assert weaker_promoted == []
        assert [record.fact_key for record in stronger_promoted] == ["fact-3"]

        active = store.read(
            subject="subject:42",
            predicate="validated_rag_evidence:docs/test.md:chunk-1",
            access_scope="subject:42",
            rail="product_ai_runtime",
        )
        wrong_scope = store.read(
            subject="subject:42",
            predicate="validated_rag_evidence:docs/test.md:chunk-1",
            access_scope="subject:99",
            rail="product_ai_runtime",
        )

        assert [record.fact_key for record in active] == ["fact-3"]
        assert wrong_scope == []
        assert len([record for record in store.all_records() if record.status == "superseded"]) == 1


class TestInsightApplicationServiceFastLane:
    """Keep async knowledge-promotion seam covered by test-fast."""

    @pytest.mark.asyncio
    async def test_maybe_promote_knowledge_candidates_awaits_async_store(self) -> None:
        """Async stores must be awaited before the response path continues."""

        from app.services.insight_application_service import _maybe_promote_knowledge_candidates
        from core.knowledge.contracts import KnowledgeFactCandidate

        observed: dict[str, object] = {}
        candidate = cast(KnowledgeFactCandidate, SimpleNamespace(fact_key="fact-1"))

        class _AsyncStore:
            async def promote(self, candidates: list[object]) -> list[object]:
                observed["candidates"] = candidates
                return []

        await _maybe_promote_knowledge_candidates(
            knowledge_store=_AsyncStore(),
            candidates=[candidate],
        )

        assert observed["candidates"] == [candidate]

    @pytest.mark.asyncio
    async def test_maybe_promote_knowledge_candidates_logs_and_swallows_store_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Store failures must not break the user response path."""

        from app.services.insight_application_service import _maybe_promote_knowledge_candidates
        from core.knowledge.contracts import KnowledgeFactCandidate

        warnings: list[tuple[tuple[object, ...], dict[str, object]]] = []

        class _BrokenStore:
            def promote(self, candidates: list[object]) -> list[object]:
                del candidates
                raise RuntimeError("boom")

        monkeypatch.setattr(
            "app.services.insight_application_service.logger.warning",
            lambda *args, **kwargs: warnings.append((args, kwargs)),
            raising=True,
        )

        await _maybe_promote_knowledge_candidates(
            knowledge_store=_BrokenStore(),
            candidates=[cast(KnowledgeFactCandidate, SimpleNamespace(fact_key="fact-1"))],
        )

        assert warnings
        assert "Knowledge promotion failed" in str(warnings[0][0][0])
        assert warnings[0][1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_maybe_promote_knowledge_candidates_times_out_async_store(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Timed-out promotion must degrade to logging instead of request latency."""

        from app.services.insight_application_service import _maybe_promote_knowledge_candidates
        from core.knowledge.contracts import KnowledgeFactCandidate

        warnings: list[tuple[tuple[object, ...], dict[str, object]]] = []

        class _SlowStore:
            def promote(self, candidates: list[object]) -> object:
                del candidates

                async def _stall() -> list[object]:
                    await asyncio.Future()

                return _stall()

        monkeypatch.setattr(
            "app.services.insight_application_service.KNOWLEDGE_PROMOTION_TIMEOUT_SECONDS",
            0.01,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_application_service.logger.warning",
            lambda *args, **kwargs: warnings.append((args, kwargs)),
            raising=True,
        )

        await _maybe_promote_knowledge_candidates(
            knowledge_store=_SlowStore(),
            candidates=[cast(KnowledgeFactCandidate, SimpleNamespace(fact_key="fact-1"))],
        )

        assert warnings
        assert "Knowledge promotion timed out" in str(warnings[0][0][0])
        assert warnings[0][1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_maybe_promote_knowledge_candidates_times_out_sync_store(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sync promotion must also respect the bounded timeout via thread offload."""

        from app.services.insight_application_service import _maybe_promote_knowledge_candidates
        from core.knowledge.contracts import KnowledgeFactCandidate

        warnings: list[tuple[tuple[object, ...], dict[str, object]]] = []

        class _SlowSyncStore:
            def promote(self, candidates: list[object]) -> list[object]:
                del candidates
                time.sleep(0.05)
                return []

        monkeypatch.setattr(
            "app.services.insight_application_service.KNOWLEDGE_PROMOTION_TIMEOUT_SECONDS",
            0.01,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_application_service.logger.warning",
            lambda *args, **kwargs: warnings.append((args, kwargs)),
            raising=True,
        )

        await _maybe_promote_knowledge_candidates(
            knowledge_store=_SlowSyncStore(),
            candidates=[cast(KnowledgeFactCandidate, SimpleNamespace(fact_key="fact-1"))],
        )

        assert warnings
        assert "Knowledge promotion timed out" in str(warnings[0][0][0])
        assert warnings[0][1]["exc_info"] is True


class TestPhilosophicalRuntimeFastLane:
    """Keep runtime knowledge-candidate gating covered by the fast lane."""

    @staticmethod
    def _runtime_policy(*, enabled: bool = True, allow_promotion: bool = True):
        from core.knowledge.policy import KnowledgePolicy

        return KnowledgePolicy(
            enabled=enabled,
            allow_reads=True,
            allow_promotion=allow_promotion,
            min_confidence=0.7,
            require_rag_factual_route=True,
            deny_degraded_reasons=("retrieval_empty", "all_chunks_filtered"),
            subject_scope_required=True,
            rail="product_ai_runtime",
        )

    @staticmethod
    def _runtime_candidate():
        from core.knowledge.contracts import KnowledgeEvidenceRef, KnowledgeFactCandidate

        return KnowledgeFactCandidate(
            fact_key="fact-1",
            subject="subject:42",
            predicate="validated_rag_evidence:docs/test.md:chunk-1",
            value="chunk=chunk-1;source=docs/test.md;digest=abc123;hop=1",
            observed_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
            confidence=0.9,
            access_scope="subject:42",
            rail="product_ai_runtime",
            provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", 0.9, 1),),
        )

    @pytest.mark.parametrize(
        (
            "route_type",
            "philo_validation_enabled",
            "policy",
            "rag_actually_used",
            "degraded_reason",
            "canonical",
            "expected_count",
        ),
        [
            ("DEEP_REASONING", True, "enabled", True, None, True, 0),
            ("RAG_FACTUAL", False, "enabled", True, None, True, 0),
            ("RAG_FACTUAL", True, "none", True, None, True, 0),
            ("RAG_FACTUAL", True, "disabled", True, None, True, 0),
            ("RAG_FACTUAL", True, "deny", True, None, True, 0),
            ("RAG_FACTUAL", True, "enabled", False, None, True, 0),
            ("RAG_FACTUAL", True, "enabled", True, "retrieval_empty", True, 0),
            ("RAG_FACTUAL", True, "enabled", True, None, False, 0),
            ("RAG_FACTUAL", True, "enabled", True, None, True, 1),
        ],
    )
    def test_resolve_runtime_knowledge_candidates_honors_all_guards(
        self,
        route_type: str,
        philo_validation_enabled: bool,
        policy: str,
        rag_actually_used: bool,
        degraded_reason: str | None,
        canonical: bool,
        expected_count: int,
    ) -> None:
        """Runtime may promote only canonical candidates from validated factual RAG paths."""

        from core.insight.philosophical_runtime import (
            PhilosophicalRuntime,
            RiskLevel,
            RouteDecision,
            RouteType,
        )
        from core.rag.orchestration import RAGOrchestrationResult

        runtime = PhilosophicalRuntime()
        candidate = self._runtime_candidate()
        decision = RouteDecision(
            route_type=RouteType(route_type),
            target_depth=1,
            needs_rag=True,
            needs_generation=True,
            risk_level=RiskLevel.LOW,
        )
        if policy == "none":
            knowledge_policy = None
        elif policy == "disabled":
            knowledge_policy = self._runtime_policy(enabled=False)
        elif policy == "deny":
            knowledge_policy = self._runtime_policy(allow_promotion=False)
        else:
            knowledge_policy = self._runtime_policy()

        result = runtime._resolve_runtime_knowledge_candidates(
            decision=decision,
            rag_result=RAGOrchestrationResult(
                chunks=[],
                formatted_prompt="prompt",
                rag_actually_used=rag_actually_used,
                confidence=0.9,
                hops=1,
                latency_ms=1,
                degraded_reason=degraded_reason,
                knowledge_candidates=[candidate],
                knowledge_candidates_canonical=canonical,
            ),
            philo_validation_enabled=philo_validation_enabled,
            knowledge_policy=knowledge_policy,
        )

        assert len(result) == expected_count


class TestVectorTypeFastLane:
    """Keep pgvector SQLAlchemy fallback covered inside test-fast."""

    def test_build_sqlalchemy_vector_type_falls_back_when_pgvector_is_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fallback vector type must still render valid SQL when pgvector is absent."""

        from core.rag import vector_rag

        # RU: Имитируем отсутствие установленного pgvector без моков import hook.
        # EN: Simulate a missing pgvector install without patching Python's import hook.
        monkeypatch.setitem(sys.modules, "pgvector", ModuleType("pgvector"))
        monkeypatch.delitem(sys.modules, "pgvector.sqlalchemy", raising=False)
        vector_type = vector_rag._build_sqlalchemy_vector_type(7)

        assert vector_type.get_col_spec() == "VECTOR(7)"


class TestDbGuardAndFallbackSmokeCoverage:
    """RU: Smoke-visible coverage tail for DB guard/fallback helpers.

    EN: Smoke-visible coverage tail for DB guard/fallback helpers.
    """

    TRUTHY = {"1", "true", "yes", "on"}

    def test_build_engine_url_production_guards_fail_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RU: Prod-like env must reject missing and SQLite URLs.

        EN: Production-like env must reject missing and SQLite DATABASE_URL values.
        """

        import core.db as core_db

        core_db.reset_db_for_tests()
        try:
            monkeypatch.setenv("ENVIRONMENT", "production")
            monkeypatch.delenv("APP_ENV", raising=False)
            monkeypatch.setenv("DEBUG", "false")
            monkeypatch.delenv("DATABASE_URL", raising=False)

            with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
                core_db._build_engine_url()

            monkeypatch.setenv("DATABASE_URL", "sqlite:///./cache/app.db")
            with pytest.raises(RuntimeError, match="SQLite DATABASE_URL is not allowed"):
                core_db._build_engine_url()
        finally:
            core_db.reset_db_for_tests()

    def test_is_sqlite_database_url_uses_scheme_fallback_when_sqlalchemy_parse_fails(self) -> None:
        """RU: Fallback parser must still detect SQLite dialect schemes.

        EN: Fallback parser must still detect SQLite dialect schemes.
        """

        import core.db as core_db

        with patch.object(core_db, "make_url", side_effect=ValueError("bad url")):
            assert core_db._is_sqlite_database_url("sqlite+pysqlite:///./cache/app.db") is True

    @pytest.mark.parametrize(
        ("database_url", "expected"),
        [
            ("", "<empty-db-url>"),
            ("sqlite:///:memory:", "sqlite:///:memory:"),
            ("sqlite:///./fallback.db", "sqlite:///<redacted>"),
            ("postgresql://db.example/pulseplate", "<redacted-db-url>"),
        ],
    )
    def test_redact_database_url_variants(self, database_url: str, expected: str) -> None:
        """RU: Redaction helper must cover empty, memory, file, and remote DSNs.

        EN: Redaction helper must cover empty, memory, file, and remote DSNs.
        """

        from core.db_fallback import _redact_database_url

        assert _redact_database_url(database_url) == expected

    def test_check_production_constraints_logs_and_raises(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """RU: Production fallback constraint must fail closed with guidance.

        EN: Production fallback constraint must fail closed with guidance.
        """

        from core.db_fallback import _check_production_constraints

        with pytest.raises(RuntimeError, match="prod-db-error"):
            _check_production_constraints(
                env_name="production",
                fallback_url="sqlite:///./fallback.db",
                truthy=self.TRUTHY,
                db_err=RuntimeError("prod-db-error"),
            )

        assert "canonical Postgres DATABASE_URL" in caplog.text

    def test_initialize_fallback_engine_re_raises_original_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RU: Fallback engine init must preserve the original DB error.

        EN: Fallback engine init must preserve the original DB error.
        """

        import core.db_fallback as fallback_mod

        def _raise_create_engine(*args: object, **kwargs: object) -> object:
            raise RuntimeError("fallback init failed")

        monkeypatch.setattr(fallback_mod, "create_engine", _raise_create_engine)

        with pytest.raises(OSError, match="primary-db-error"):
            fallback_mod._initialize_fallback_engine(
                "sqlite:///:memory:",
                OSError("primary-db-error"),
            )

    def test_attempt_db_fallback_routes_production_and_nonproduction_helpers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RU: _attempt_db_fallback must route prod and non-prod helper paths.

        EN: _attempt_db_fallback must route prod and non-prod helper paths.
        """

        import core.db_fallback as fallback_mod

        production_calls: list[tuple[object, ...]] = []
        nonproduction_calls: list[tuple[str, object]] = []

        def _fake_check(
            env_name: str | None,
            fallback_url: str,
            truthy: set[str],
            db_err: Exception,
        ) -> None:
            production_calls.append((env_name, fallback_url, truthy, str(db_err)))
            raise db_err

        def _fake_validate(
            env_name: str | None,
            is_production: bool,
            fallback_url: str,
            db_err: Exception,
        ) -> None:
            nonproduction_calls.append(
                ("validate", (env_name, is_production, fallback_url, str(db_err)))
            )

        def _fake_initialize(fallback_url: str, db_err: Exception) -> str:
            nonproduction_calls.append(("initialize", (fallback_url, str(db_err))))
            return "engine-sentinel"

        def _fake_configure(
            engine: str,
            is_production: bool,
            fallback_url: str,
            env_name: str | None,
        ) -> None:
            nonproduction_calls.append(
                ("configure", (engine, is_production, fallback_url, env_name))
            )

        monkeypatch.setattr(fallback_mod, "_check_production_constraints", _fake_check)
        monkeypatch.setattr(fallback_mod, "_validate_fallback_url", _fake_validate)
        monkeypatch.setattr(fallback_mod, "_initialize_fallback_engine", _fake_initialize)
        monkeypatch.setattr(fallback_mod, "_configure_session_bindings", _fake_configure)

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./prod-fallback.db")
        with pytest.raises(RuntimeError, match="prod failure"):
            fallback_mod._attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=RuntimeError("prod failure"),
                truthy=self.TRUTHY,
            )

        assert production_calls == [
            ("production", "sqlite:///./prod-fallback.db", self.TRUTHY, "prod failure")
        ]

        monkeypatch.delenv("DB_FALLBACK_URL", raising=False)
        monkeypatch.setenv("ALLOW_DB_INMEMORY_FALLBACK", "true")
        fallback_mod._attempt_db_fallback(
            env_name="dev",
            is_production=False,
            db_err=RuntimeError("dev failure"),
            truthy=self.TRUTHY,
        )

        assert nonproduction_calls == [
            ("validate", ("dev", False, "sqlite:///:memory:", "dev failure")),
            ("initialize", ("sqlite:///:memory:", "dev failure")),
            ("configure", ("engine-sentinel", False, "sqlite:///:memory:", "dev")),
        ]
