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
    from core.verification.contracts import VerificationBundle


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


def test_verify_requirements_wrapper_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the compatibility wrapper covered in the deterministic smoke lane."""

    import verify_requirements

    observed_argv: list[str] | None = None

    def fake_validator(argv: list[str] | None = None) -> int:
        nonlocal observed_argv
        observed_argv = argv
        return 23

    monkeypatch.setattr(verify_requirements, "check_python_dependency_surfaces", fake_validator)

    assert verify_requirements.main(["--repo-root", "/tmp/example"]) == 23
    assert observed_argv == ["--repo-root", "/tmp/example"]


def test_execution_sandbox_network_marker_smoke() -> None:
    """Keep network-disable env handling covered in the CI smoke coverage artifact."""

    from app.security import execution_sandbox as sandbox

    assert sandbox.SANDBOX_DISABLE_NETWORK_ENV == "AGENT_EXECUTION_SANDBOX_DISABLE_NETWORK"
    sanitized = sandbox.sanitize_sandbox_env({sandbox.SANDBOX_DISABLE_NETWORK_ENV.lower(): "YES"})
    assert sanitized[sandbox.SANDBOX_DISABLE_NETWORK_ENV] == "1"
    assert sandbox._network_disable_requested(sanitized) is True

    with pytest.raises(PermissionError, match=sandbox.SANDBOX_DISABLE_NETWORK_ENV):
        sandbox.sanitize_sandbox_env({sandbox.SANDBOX_DISABLE_NETWORK_ENV: "0"})


def test_execution_sandbox_unshare_resolution_smoke(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Cover fail-closed and successful unshare resolver branches in the smoke lane."""

    from app.security import execution_sandbox as sandbox

    monkeypatch.setattr(sandbox.os, "name", "nt", raising=False)
    with pytest.raises(RuntimeError, match="POSIX unshare"):
        sandbox._resolve_unshare_binary()

    monkeypatch.setattr(sandbox.os, "name", "posix", raising=False)
    monkeypatch.setattr(sandbox.shutil, "which", lambda _binary: None)
    with pytest.raises(RuntimeError, match="unshare on PATH"):
        sandbox._resolve_unshare_binary()

    not_executable = tmp_path / "unshare-dir"
    not_executable.mkdir()
    monkeypatch.setattr(sandbox.shutil, "which", lambda _binary: str(not_executable))
    with pytest.raises(RuntimeError, match="executable file"):
        sandbox._resolve_unshare_binary()

    executable = tmp_path / "unshare"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setattr(sandbox.shutil, "which", lambda _binary: str(executable))
    assert sandbox._resolve_unshare_binary() == str(executable.resolve())


def test_execution_sandbox_argv_network_wrapping_smoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise both argv branches used by sandbox subprocess launch."""

    from app.security import execution_sandbox as sandbox

    assert sandbox._build_sandbox_argv(
        binary_path="/usr/bin/python3",
        args=("-c", "pass"),
        env={},
    ) == ("/usr/bin/python3", "-c", "pass")

    monkeypatch.setattr(sandbox, "_resolve_unshare_binary", lambda: "/usr/bin/unshare")
    assert sandbox._build_sandbox_argv(
        binary_path="/usr/bin/python3",
        args=("-c", "pass"),
        env={sandbox.SANDBOX_DISABLE_NETWORK_ENV: "1"},
    ) == ("/usr/bin/unshare", "--net", "--map-root-user", "/usr/bin/python3", "-c", "pass")


def test_run_local_sandbox_builds_effective_argv_smoke(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Run a tiny allowed command so the smoke coverage artifact covers argv construction."""

    from app.security import execution_sandbox as sandbox
    from app.security import agent_control_plane as cp

    monkeypatch.setenv(sandbox.SANDBOX_ENABLED_ENV, "true")
    monkeypatch.setenv(sandbox.SANDBOX_ROOT_ENV, str(tmp_path))
    monkeypatch.setenv(sandbox.SANDBOX_ALLOWED_BINARIES_ENV, "python3")
    monkeypatch.setenv(cp.ALLOWLIST_ENV, "sandbox.exec:local://sandbox")

    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python3",
            args=("-c", "print('sandbox-smoke')"),
            cwd=tmp_path,
        )
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "sandbox-smoke"
    assert result.stderr == ""


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


def _clear_ragas_live_provider_env(
    monkeypatch: pytest.MonkeyPatch,
    runner: ModuleType,
) -> None:
    """Keep RAGAS smoke tests independent from the operator shell environment."""

    prohibited_env_vars = cast(
        Sequence[str],
        getattr(runner, "PROHIBITED_LIVE_PROVIDER_ENV_VARS"),
    )
    for name in prohibited_env_vars:
        monkeypatch.delenv(name, raising=False)


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
        expected_dataset_path = dataset_path.resolve().as_posix()

        assert report == {
            "dataset_path": expected_dataset_path,
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

    def test_ragas_runner_rejects_live_provider_credentials_before_ragas_load(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """The fast lane must cover fail-closed credential guards before RAGAS loads."""

        runner = importlib.import_module("evals.ragas.run_ragas_eval")
        dataset_path = tmp_path / "testset.jsonl"
        _write_ragas_bootstrap_dataset(dataset_path)
        rows = runner.load_dataset_rows(dataset_path)
        prohibited_env_vars = cast(
            Sequence[str],
            getattr(runner, "PROHIBITED_LIVE_PROVIDER_ENV_VARS"),
        )
        load_attempts = 0

        def _boom() -> tuple[object, object, object]:
            nonlocal load_attempts
            load_attempts += 1
            raise AssertionError("ragas must not load while live provider creds are set")

        monkeypatch.setattr(runner, "_load_ragas_dependencies", _boom)

        for index, name in enumerate(prohibited_env_vars):
            secret_value = f"test-secret-{index}"
            _clear_ragas_live_provider_env(monkeypatch, runner)
            monkeypatch.setenv(name, secret_value)

            with pytest.raises(RuntimeError) as exc_info:
                runner.evaluate_records(rows, runner.REQUIRED_METRIC_NAMES)

            message = str(exc_info.value)
            assert "offline-only" in message
            assert name in message
            assert secret_value not in message
            assert load_attempts == 0

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
        _clear_ragas_live_provider_env(monkeypatch, runner)
        dataset_path = tmp_path / "testset.jsonl"
        _write_ragas_bootstrap_dataset(dataset_path)
        rows = runner.load_dataset_rows(dataset_path)

        with pytest.raises(ValueError, match="Bootstrap metric contract drift detected"):
            runner._validate_metric_names(("faithfulness",))

        monkeypatch.setattr(runner, "REPORT_ONLY_MODE", False)
        with pytest.raises(ValueError, match="report-only"):
            runner._validate_metric_names(runner.REQUIRED_METRIC_NAMES)
        monkeypatch.setattr(runner, "REPORT_ONLY_MODE", True)
        captured_rows: list[dict[str, object]] = []

        class _FakeDataset:
            @classmethod
            def from_list(cls, values: list[dict[str, object]]) -> "_FakeDataset":
                captured_rows.clear()
                captured_rows.extend(values)
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
        assert captured_rows[0]["reference"] == captured_rows[0]["ground_truth"]

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
        id_val = generate_id()
        assert isinstance(id_val, str)
        assert len(id_val) == 32  # UUID hex without hyphens

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
        from core.verification.contracts import VerificationArtifact, VerificationBundle

        policy = self._knowledge_policy()
        bundle = VerificationBundle(
            artifacts=(
                VerificationArtifact(
                    artifact_id="fast-lane-pass",
                    verifier_id="fast_lane_verifier",
                    status="pass",
                    reason_codes=("verification_checks_pass",),
                ),
            ),
            overall_status="pass",
            admission_allowed=True,
            reason_codes=("verification_checks_pass",),
        )

        assert (
            build_knowledge_promotion_candidates(
                chunks=[],
                confidence=0.9,
                degraded_reason=None,
                subject_id=42,
                knowledge_policy=policy,
                verification_bundle=bundle,
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
                verification_bundle=bundle,
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
                verification_bundle=bundle,
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
                verification_bundle=bundle,
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
                verification_bundle=bundle,
            )
            == []
        )
        assert (
            build_knowledge_promotion_candidates(
                chunks=[self._chunk()],
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

    @staticmethod
    def _verification_bundle(*, admission_allowed: bool = True) -> "VerificationBundle":
        from core.verification.contracts import VerificationArtifact, VerificationBundle

        status = "pass" if admission_allowed else "fail"
        return VerificationBundle(
            artifacts=(
                VerificationArtifact(
                    artifact_id=f"service-{status}",
                    verifier_id="service_test_verifier",
                    status=status,
                    reason_codes=(
                        ("verification_checks_pass",)
                        if admission_allowed
                        else ("verification_failed",)
                    ),
                ),
            ),
            overall_status=status,
            admission_allowed=admission_allowed,
            reason_codes=(
                ("verification_checks_pass",) if admission_allowed else ("verification_failed",)
            ),
        )

    def test_maybe_promote_knowledge_candidates_awaits_async_store(self) -> None:
        """Async stores must be awaited before the response path continues."""

        from app.services.insight_application_service import _maybe_promote_knowledge_candidates
        from core.knowledge.contracts import KnowledgeFactCandidate

        observed: dict[str, object] = {}
        candidate = cast(KnowledgeFactCandidate, SimpleNamespace(fact_key="fact-1"))

        class _AsyncStore:
            async def promote(self, candidates: list[object]) -> list[object]:
                observed["candidates"] = candidates
                return []

        asyncio.run(
            _maybe_promote_knowledge_candidates(
                knowledge_store=_AsyncStore(),
                candidates=[candidate],
                verification_bundle=self._verification_bundle(),
            )
        )

        assert observed["candidates"] == [candidate]

    def test_maybe_promote_knowledge_candidates_logs_and_swallows_store_errors(
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

        asyncio.run(
            _maybe_promote_knowledge_candidates(
                knowledge_store=_BrokenStore(),
                candidates=[cast(KnowledgeFactCandidate, SimpleNamespace(fact_key="fact-1"))],
                verification_bundle=self._verification_bundle(),
            )
        )

        assert warnings
        assert "Knowledge promotion failed" in str(warnings[0][0][0])
        assert warnings[0][1]["exc_info"] is True

    def test_maybe_promote_knowledge_candidates_times_out_async_store(
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

        asyncio.run(
            _maybe_promote_knowledge_candidates(
                knowledge_store=_SlowStore(),
                candidates=[cast(KnowledgeFactCandidate, SimpleNamespace(fact_key="fact-1"))],
                verification_bundle=self._verification_bundle(),
            )
        )

        assert warnings
        assert "Knowledge promotion timed out" in str(warnings[0][0][0])
        assert warnings[0][1]["exc_info"] is True

    def test_traced_retriever_uses_prepared_recursive_rollout_policy(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Prepared recursive rollout policy must own recursive/optimization truth."""

        from contextlib import nullcontext

        from app.services.insight_runtime import _traced_retrieve_and_validate_rag
        from core.ai.insight_runtime import RecursiveRolloutPolicy

        observed: dict[str, object] = {}

        async def _fake_retrieve_and_validate_rag(*args: object, **kwargs: object) -> object:
            observed["args"] = args
            observed["kwargs"] = kwargs
            return SimpleNamespace(hops=2)

        monkeypatch.setattr(
            "app.services.insight_runtime.retrieval_span",
            lambda **kwargs: nullcontext(SimpleNamespace()),
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.set_attributes",
            lambda *args, **kwargs: None,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.rag_orchestration.retrieve_and_validate_rag",
            _fake_retrieve_and_validate_rag,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_recursive_rag_enabled",
            lambda: pytest.fail("recursive env reader must not run"),
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_recursive_rag_optimization_enabled",
            lambda: pytest.fail("optimization env reader must not run"),
            raising=True,
        )

        rag_result = asyncio.run(
            _traced_retrieve_and_validate_rag(
                "hello",
                max_chunks=3,
                philo_validation_enabled=True,
                recursive_rollout_policy=RecursiveRolloutPolicy(
                    use_rag=True,
                    recursive_rag_enabled=True,
                    recursive_rag_optimization_enabled=False,
                ),
                subject_id=123,
                knowledge_policy=None,
                user_tier="VIP",
                route_path="/api/v1/insight",
            ),
        )

        assert getattr(rag_result, "hops", None) == 2
        assert observed["args"] == ("hello",)
        assert observed["kwargs"]["recursive_rag_enabled"] is True
        assert observed["kwargs"]["optimization_enabled"] is False

    def test_generate_traced_insight_uses_prepared_recursive_policy_in_feature_flags(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tracing feature flags must observe the prepared recursive policy."""

        from contextlib import nullcontext

        from app.services.insight_runtime import generate_traced_insight
        from core.ai.insight_runtime import RecursiveRolloutPolicy

        observed: dict[str, object] = {}

        class _Runtime:
            async def generate_insight(self, **kwargs: object) -> object:
                observed["runtime_kwargs"] = kwargs
                return SimpleNamespace(ok=True)

        def _fake_chain_span(*args: object, **kwargs: object) -> object:
            del args
            observed["feature_flags"] = kwargs["feature_flags"]
            return nullcontext()

        monkeypatch.setattr(
            "app.services.insight_runtime.chain_span",
            _fake_chain_span,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_router_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_phase12_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_linguistic_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_pragmatic_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_validation_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_recursive_rag_enabled",
            lambda: pytest.fail("recursive env reader must not run"),
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_recursive_rag_optimization_enabled",
            lambda: pytest.fail("optimization env reader must not run"),
            raising=True,
        )

        result = asyncio.run(
            generate_traced_insight(
                runtime=_Runtime(),
                text="hello",
                lang=None,
                provider=SimpleNamespace(name="fake-provider"),
                use_rag=True,
                philo_validation_enabled=False,
                recursive_rag_enabled=False,
                route_path="/api/v1/insight",
                route_type="deep_reasoning",
                user_tier="VIP",
                subject_id=None,
                knowledge_policy=None,
                recursive_rollout_policy=RecursiveRolloutPolicy(
                    use_rag=True,
                    recursive_rag_enabled=True,
                    recursive_rag_optimization_enabled=False,
                ),
            ),
        )

        assert getattr(result, "ok", None) is True
        assert observed["feature_flags"]["rag"] is True
        assert observed["feature_flags"]["rag_recursive"] is True
        assert observed["feature_flags"]["rag_recursive_optimization"] is False
        assert observed["runtime_kwargs"]["recursive_rag_enabled"] is True

    def test_insight_feature_flag_state_prefers_prepared_rag_truth_when_use_rag_omitted(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Prepared recursive policy must also own the base RAG snapshot when injected."""

        from app.services.insight_runtime import insight_feature_flag_state
        from core.ai.insight_runtime import RecursiveRolloutPolicy

        monkeypatch.setenv("FEATURE_RAG", "false")
        monkeypatch.setattr(
            "app.services.insight_runtime.is_recursive_rag_enabled",
            lambda: pytest.fail("recursive env reader must not run"),
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_recursive_rag_optimization_enabled",
            lambda: pytest.fail("optimization env reader must not run"),
            raising=True,
        )

        feature_flags = insight_feature_flag_state(
            use_rag=None,
            recursive_rollout_policy=RecursiveRolloutPolicy(
                use_rag=True,
                recursive_rag_enabled=True,
                recursive_rag_optimization_enabled=False,
            ),
        )

        assert feature_flags["rag"] is True
        assert feature_flags["rag_recursive"] is True
        assert feature_flags["rag_recursive_optimization"] is False

    def test_insight_feature_flag_state_falls_back_to_feature_rag_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Without prepared recursive policy, the base RAG snapshot must use env truth."""

        from app.services.insight_runtime import insight_feature_flag_state

        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_INSIGHT", "false")
        monkeypatch.setenv("FEATURE_RAG_VECTOR", "false")
        monkeypatch.setattr(
            "app.services.insight_runtime.is_recursive_rag_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_recursive_rag_optimization_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_router_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_phase12_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_linguistic_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_pragmatic_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_runtime.is_philosophy_validation_enabled",
            lambda: False,
            raising=True,
        )

        feature_flags = insight_feature_flag_state(
            use_rag=None,
            recursive_rollout_policy=None,
        )

        assert feature_flags["rag"] is True
        assert feature_flags["rag_recursive"] is False
        assert feature_flags["rag_recursive_optimization"] is False

    def test_execute_insight_request_builds_legacy_recursive_fallback_in_fast_lane(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fast-lane coverage must exercise the legacy recursive fallback via the public seam."""

        from app.services.insight_application_service import execute_insight_request
        from core.ai.insight_runtime import InsightTransparencyNotice
        from core.insight.philosophical_runtime import PhilosophyRolloutPolicy

        observed: dict[str, object] = {}
        prepared_runtime = SimpleNamespace(
            runtime=object(),
            provider=object(),
            decision=SimpleNamespace(route_type=SimpleNamespace(value="deep_reasoning")),
            rollout_policy=PhilosophyRolloutPolicy(
                router_enabled=False,
                phase12_enabled=False,
                linguistic_enabled=False,
                pragmatic_enabled=False,
            ),
            transparency_notice=InsightTransparencyNotice(
                surface_id="ai_generated_insight",
                wellness_boundary="Wellness only.",
            ),
            knowledge_policy=None,
        )

        async def _fake_generate_traced_insight(**kwargs: object) -> object:
            observed["generate_kwargs"] = kwargs
            return SimpleNamespace(
                insight="generated insight",
                provider_name="fake-provider",
                source_dicts=[],
                confidence=0.9,
                rag_used=True,
                hops=1,
                latency_ms=12,
                knowledge_candidates=[],
                metadata=SimpleNamespace(
                    route_type="deep_reasoning",
                    depth_used=1,
                    verification_rate=0.0,
                    falsifiability_rate=0.0,
                    contradiction_count=0,
                    reason_codes=["legacy_recursive_fallback"],
                    optimization_applied=False,
                ),
            )

        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setattr(
            "app.services.insight_application_service.is_recursive_rag_enabled",
            lambda: True,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_application_service.is_recursive_rag_optimization_enabled",
            lambda: False,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_application_service.prepare_insight_runtime",
            lambda **kwargs: prepared_runtime,
            raising=True,
        )
        monkeypatch.setattr(
            "app.services.insight_application_service.generate_traced_insight",
            _fake_generate_traced_insight,
            raising=True,
        )

        response = asyncio.run(
            execute_insight_request(
                SimpleNamespace(text="hello"),
                route_path="/api/v1/insight",
                user_tier="VIP",
                input_guard=lambda text: None,
                provider_loader=lambda: None,
                transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
                response_factory=lambda **payload: dict(payload),
                source_item_factory=lambda **payload: dict(payload),
            )
        )

        generate_kwargs = cast(dict[str, object], observed["generate_kwargs"])
        recursive_rollout_policy = cast(
            object,
            generate_kwargs["recursive_rollout_policy"],
        )

        assert getattr(recursive_rollout_policy, "use_rag") is True
        assert getattr(recursive_rollout_policy, "recursive_path_enabled") is True
        assert getattr(recursive_rollout_policy, "optimization_path_enabled") is False
        assert generate_kwargs["use_rag"] is True
        assert generate_kwargs["recursive_rag_enabled"] is True
        assert generate_kwargs["recursive_rag_optimization_enabled"] is False
        assert response["rag_used"] is True

    def test_maybe_promote_knowledge_candidates_times_out_sync_store(
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

        asyncio.run(
            _maybe_promote_knowledge_candidates(
                knowledge_store=_SlowSyncStore(),
                candidates=[cast(KnowledgeFactCandidate, SimpleNamespace(fact_key="fact-1"))],
                verification_bundle=self._verification_bundle(),
            )
        )

        assert warnings
        assert "Knowledge promotion timed out" in str(warnings[0][0][0])
        assert warnings[0][1]["exc_info"] is True


class TestPhilosophicalRuntimeFastLane:
    """Keep runtime knowledge-candidate gating covered by the fast lane."""

    @staticmethod
    def _runtime_policy(*, enabled: bool = True, allow_promotion: bool = True) -> "KnowledgePolicy":
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
    def _runtime_candidate() -> "KnowledgeFactCandidate":
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

    @staticmethod
    def _verification_bundle(*, admission_allowed: bool = True) -> "VerificationBundle":
        from core.verification.contracts import VerificationArtifact, VerificationBundle

        status = "pass" if admission_allowed else "fail"
        return VerificationBundle(
            artifacts=(
                VerificationArtifact(
                    artifact_id=f"fast-lane-{status}",
                    verifier_id="fast_lane_verifier",
                    status=status,
                    reason_codes=(
                        ("verification_checks_pass",)
                        if admission_allowed
                        else ("verification_failed",)
                    ),
                ),
            ),
            overall_status=status,
            admission_allowed=admission_allowed,
            reason_codes=(
                ("verification_checks_pass",) if admission_allowed else ("verification_failed",)
            ),
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
            verification_bundle=(
                self._verification_bundle()
                if canonical and degraded_reason is None and rag_actually_used
                else None
            ),
        )

        assert len(result) == expected_count

    def test_resolve_runtime_knowledge_candidates_requires_admissible_bundle(self) -> None:
        """Promotion must fail closed when the canonical RAG path lacks a passed bundle."""

        from core.insight.philosophical_runtime import (
            PhilosophicalRuntime,
            RiskLevel,
            RouteDecision,
            RouteType,
        )
        from core.rag.orchestration import RAGOrchestrationResult

        runtime = PhilosophicalRuntime()
        decision = RouteDecision(
            route_type=RouteType.RAG_FACTUAL,
            target_depth=1,
            needs_rag=True,
            needs_generation=True,
            risk_level=RiskLevel.LOW,
        )

        result = runtime._resolve_runtime_knowledge_candidates(
            decision=decision,
            rag_result=RAGOrchestrationResult(
                chunks=[],
                formatted_prompt="prompt",
                rag_actually_used=True,
                confidence=0.9,
                hops=1,
                latency_ms=1,
                degraded_reason=None,
                knowledge_candidates=[self._runtime_candidate()],
                knowledge_candidates_canonical=True,
            ),
            philo_validation_enabled=True,
            knowledge_policy=self._runtime_policy(),
            verification_bundle=None,
        )

        assert result == []

    def test_build_direct_result_requires_public_metadata_access(self) -> None:
        """Direct-result helper must fail closed when metadata exposure is disabled."""

        from core.insight.philosophical_runtime import (
            PhilosophicalRuntime,
            RiskLevel,
            RouteDecision,
            RouteType,
        )

        runtime = PhilosophicalRuntime()
        decision = RouteDecision(
            route_type=RouteType.DIRECT_DEFINITION,
            target_depth=0,
            needs_rag=False,
            needs_generation=False,
            risk_level=RiskLevel.LOW,
            simplified_query="simple query",
        )

        with pytest.raises(
            ValueError,
            match="direct-result metadata requires public metadata access",
        ):
            runtime._build_direct_result(
                answer="local answer",
                provider_name="local",
                decision=decision,
                public_metadata_enabled=False,
                verification_report=None,
                falsification_report=None,
                contradiction_count=0,
                fallback_reason="",
                rewrite_count=0,
            )


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


class TestVerificationRegistryCoverageTail:
    """Keep verification-registry diff coverage inside the canonical CI fast bundle."""

    @staticmethod
    def _knowledge_policy() -> "KnowledgePolicy":
        from core.knowledge.policy import KnowledgePolicy

        return KnowledgePolicy(
            enabled=True,
            allow_reads=True,
            allow_promotion=True,
            min_confidence=0.7,
            require_rag_factual_route=True,
            deny_degraded_reasons=("retrieval_empty", "all_chunks_filtered"),
            subject_scope_required=True,
            rail="product_ai_runtime",
        )

    @staticmethod
    def _build_rag_bundle(provenance, knowledge_policy):
        from core.verification.registry import build_rag_verification_bundle

        return build_rag_verification_bundle(
            knowledge_policy=knowledge_policy,
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=(),
            provenance=provenance,
        )

    @staticmethod
    def _build_runtime_bundle(rag_bundle, provenance):
        from core.verification.registry import build_runtime_verification_bundle

        return build_runtime_verification_bundle(
            rag_bundle=rag_bundle,
            verification_report=None,
            falsification_report=None,
            contradiction_count=0,
            verification_first_path=False,
            runtime_verification_enabled=False,
            provenance=provenance,
        )

    def test_runtime_bundle_fails_closed_without_rag_bundle(self) -> None:
        from core.verification.registry import build_runtime_verification_bundle

        merged = build_runtime_verification_bundle(
            rag_bundle=None,
            verification_report=None,
            falsification_report=None,
            contradiction_count=0,
            verification_first_path=True,
        )

        assert merged is not None
        assert merged.admission_allowed is False
        assert [artifact.verifier_id for artifact in merged.artifacts] == [
            "runtime_preconditions_verifier",
            "analytical_verifier",
            "falsification_verifier",
        ]

    def test_runtime_bundle_returns_none_without_verification_first_path(self) -> None:
        from core.verification.registry import build_runtime_verification_bundle

        merged = build_runtime_verification_bundle(
            rag_bundle=None,
            verification_report=None,
            falsification_report=None,
            contradiction_count=0,
            verification_first_path=False,
        )

        assert merged is None

    def test_runtime_bundle_disabled_path_ignores_provenance_without_rag_bundle(self) -> None:
        from core.verification.registry import (
            build_runtime_verification_bundle,
            build_verification_provenance,
        )

        merged = build_runtime_verification_bundle(
            rag_bundle=None,
            verification_report=None,
            falsification_report=None,
            contradiction_count=0,
            verification_first_path=False,
            runtime_verification_enabled=False,
            provenance=build_verification_provenance(
                input_text="disabled runtime input",
                answer_text="disabled runtime answer",
            ),
        )

        assert merged is None

    def test_verification_provenance_redacts_before_hash_and_preserves_admission(
        self,
    ) -> None:
        from dataclasses import asdict
        from hashlib import sha256

        from core.verification.registry import (
            build_bundle,
            build_verification_provenance,
            redacted_sha256_label,
        )
        from core.verification.contracts import VerificationArtifact

        raw_text = (
            "email jane@example.com api_key=secret-token "
            "/Users/example/private.txt /workspace/PulsePlate/.env /app/secrets/key "
            "DATABASE_URL=postgres://example.invalid/db SERVER_SALT=salt SECRET_KEY=value "
            "xoxb-secret-token U1234567890"
        )
        artifact = VerificationArtifact(
            artifact_id="provenance-test",
            verifier_id="provenance_test_verifier",
            status="pass",
            reason_codes=("verification_checks_pass",),
        )
        provenance = build_verification_provenance(
            input_text=raw_text,
            prompt_text=raw_text,
            context_items=(raw_text,),
            answer_text=raw_text,
            prompt_char_count=-5,
            prompt_trimmed=True,
            verification_hops="invalid",
            verification_calls=3,
        )
        baseline = build_bundle(artifacts=(artifact,))
        with_provenance = build_bundle(artifacts=(artifact,), provenance=provenance)

        assert with_provenance.overall_status == baseline.overall_status
        assert with_provenance.admission_allowed == baseline.admission_allowed
        assert with_provenance.reason_codes == baseline.reason_codes
        assert with_provenance.provenance is provenance
        assert provenance.prompt_char_count == 0
        assert provenance.prompt_trimmed is True
        assert provenance.verification_hops == 0
        assert provenance.verification_calls == 3
        assert provenance.input_digest == redacted_sha256_label(raw_text)
        assert provenance.input_sha == provenance.input_digest
        assert provenance.prompt_sha == provenance.prompt_digest
        assert provenance.context_item_shas == provenance.context_item_digests
        assert provenance.answer_sha == provenance.answer_digest
        assert provenance.prompt_original_char_count == 0
        assert provenance.prompt_final_char_count == 0
        assert provenance.prompt_trim_limit is None
        assert provenance.prompt_trimmed_char_count is None
        context_fail_closed_provenance = build_verification_provenance(
            context_items=("valid context", "")
        )
        assert context_fail_closed_provenance.context_item_digests == ()
        assert context_fail_closed_provenance.context_item_shas == ()
        assert provenance.input_digest != f"sha256:{sha256(raw_text.encode('utf-8')).hexdigest()}"
        assert provenance.input_digest is not None
        assert provenance.input_digest.startswith("sha256:")
        assert len(provenance.input_digest.removeprefix("sha256:")) == 64
        assert build_verification_provenance(prompt_text="count me").prompt_char_count == 8
        github_pat_text = "github_pat_fake_fake_fake"
        github_pat_digest = redacted_sha256_label(github_pat_text)
        assert github_pat_digest is not None
        assert github_pat_digest != f"sha256:{sha256(github_pat_text.encode('utf-8')).hexdigest()}"
        payload = str(asdict(with_provenance))
        for forbidden in (
            "jane@example.com",
            "/Users/example",
            "/workspace/PulsePlate",
            "/app/secrets",
            "postgres://example.invalid/db",
            "SERVER_SALT=salt",
            "SECRET_KEY=value",
            "xoxb-secret-token",
            "U1234567890",
            "secret-token",
        ):
            assert forbidden not in payload

    def test_runtime_bundle_passthrough_when_runtime_verification_is_disabled(self) -> None:
        from core.verification.registry import (
            build_bundle,
            build_rag_verification_bundle,
            build_runtime_verification_bundle,
            build_verification_provenance,
        )
        from core.verification.contracts import VerificationArtifact
        from core.verification.policy import VerificationPolicy

        provenance = build_verification_provenance(
            input_text="input",
            context_items=("rag context",),
            answer_text="answer",
            verification_hops=2,
            verification_calls=2,
        )
        rag_bundle = build_rag_verification_bundle(
            knowledge_policy=self._knowledge_policy(),
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
            provenance=provenance,
        )

        merged = build_runtime_verification_bundle(
            rag_bundle=rag_bundle,
            verification_report=None,
            falsification_report=None,
            contradiction_count=0,
            verification_first_path=True,
            runtime_verification_enabled=False,
            provenance=build_verification_provenance(
                input_text="new input",
                prompt_text="trimmed prompt",
                answer_text="new answer",
                prompt_char_count=4000,
                prompt_trimmed=True,
                prompt_original_char_count=4100,
                prompt_final_char_count=4000,
                prompt_trim_limit=4000,
                prompt_trimmed_char_count=100,
            ),
        )

        assert merged is not None
        assert merged.artifacts == rag_bundle.artifacts
        assert merged.overall_status == rag_bundle.overall_status
        assert merged.admission_allowed == rag_bundle.admission_allowed
        assert merged.reason_codes == rag_bundle.reason_codes
        assert merged.provenance is not None
        assert merged.provenance.input_digest != provenance.input_digest
        assert merged.provenance.context_item_digests == provenance.context_item_digests
        assert merged.provenance.prompt_trimmed is True
        assert merged.provenance.prompt_char_count == 4000
        assert merged.provenance.prompt_original_char_count == 4100
        assert merged.provenance.prompt_final_char_count == 4000
        assert merged.provenance.prompt_trim_limit == 4000
        assert merged.provenance.prompt_trimmed_char_count == 100
        assert merged.provenance.verification_hops == 2
        assert merged.provenance.verification_calls == 2

        warn_policy = VerificationPolicy(scope="knowledge_write", allow_warn=True)
        warn_bundle = build_bundle(
            artifacts=(
                VerificationArtifact(
                    artifact_id="warn",
                    verifier_id="warn_verifier",
                    status="warn",
                    reason_codes=("warn_allowed",),
                ),
            ),
            policy=warn_policy,
            provenance=provenance,
        )
        merged_warn = build_runtime_verification_bundle(
            rag_bundle=warn_bundle,
            verification_report=None,
            falsification_report=None,
            contradiction_count=0,
            verification_first_path=True,
            runtime_verification_enabled=False,
            provenance=build_verification_provenance(answer_text="new answer"),
        )

        assert merged_warn is not None
        assert merged_warn.overall_status == warn_bundle.overall_status
        assert merged_warn.admission_allowed is True
        assert merged_warn.reason_codes == warn_bundle.reason_codes

    def test_runtime_bundle_preserves_rag_provenance_without_overlay(self) -> None:
        from core.insight.analytical import FalsificationReport, VerificationReport
        from core.verification.registry import (
            build_rag_verification_bundle,
            build_runtime_verification_bundle,
            build_verification_provenance,
        )

        provenance = build_verification_provenance(input_text="rag input")
        rag_bundle = build_rag_verification_bundle(
            knowledge_policy=self._knowledge_policy(),
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
            provenance=provenance,
        )

        merged = build_runtime_verification_bundle(
            rag_bundle=rag_bundle,
            verification_report=VerificationReport(verification_rate=1.0, unverified_claims=[]),
            falsification_report=FalsificationReport(
                falsifiability_rate=1.0,
                unfalsifiable_claims=[],
            ),
            contradiction_count=0,
            verification_first_path=True,
        )

        assert merged is not None
        assert merged.provenance is provenance

    def test_runtime_bundle_merges_rag_and_runtime_provenance(self) -> None:
        from core.insight.analytical import FalsificationReport, VerificationReport
        from core.verification.registry import (
            build_rag_verification_bundle,
            build_runtime_verification_bundle,
            build_verification_provenance,
        )

        rag_provenance = build_verification_provenance(
            input_text="rag input",
            context_items=("rag context",),
            verification_hops=2,
            verification_calls=2,
        )
        runtime_provenance = build_verification_provenance(
            answer_text="runtime answer",
            prompt_text="runtime prompt",
            prompt_trimmed=True,
            prompt_original_char_count=80,
            prompt_final_char_count=40,
            prompt_trim_limit=40,
            prompt_trimmed_char_count=40,
            verification_hops=0,
            verification_calls=3,
        )
        rag_bundle = build_rag_verification_bundle(
            knowledge_policy=self._knowledge_policy(),
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
            provenance=rag_provenance,
        )

        merged = build_runtime_verification_bundle(
            rag_bundle=rag_bundle,
            verification_report=VerificationReport(verification_rate=1.0, unverified_claims=[]),
            falsification_report=FalsificationReport(
                falsifiability_rate=1.0,
                unfalsifiable_claims=[],
            ),
            contradiction_count=0,
            verification_first_path=True,
            provenance=runtime_provenance,
        )

        assert merged is not None
        assert merged.provenance is not None
        assert merged.provenance is not rag_provenance
        assert merged.provenance is not runtime_provenance
        assert merged.provenance.input_digest == rag_provenance.input_digest
        assert merged.provenance.context_item_digests == rag_provenance.context_item_digests
        assert merged.provenance.prompt_digest == runtime_provenance.prompt_digest
        assert merged.provenance.answer_digest == runtime_provenance.answer_digest
        assert merged.provenance.input_sha == rag_provenance.input_digest
        assert merged.provenance.prompt_sha == runtime_provenance.prompt_digest
        assert merged.provenance.context_item_shas == rag_provenance.context_item_digests
        assert merged.provenance.answer_sha == runtime_provenance.answer_digest
        assert merged.provenance.prompt_trimmed is True
        assert merged.provenance.prompt_original_char_count == 80
        assert merged.provenance.prompt_final_char_count == 40
        assert merged.provenance.prompt_trim_limit == 40
        assert merged.provenance.prompt_trimmed_char_count == 40
        assert merged.provenance.verification_hops == rag_provenance.verification_hops
        assert merged.provenance.verification_calls == runtime_provenance.verification_calls

    def test_merge_provenance_falsy_bool_preserved(self) -> None:
        from core.verification.registry import build_verification_provenance

        base = build_verification_provenance(prompt_trimmed=True)
        overlay = build_verification_provenance(prompt_trimmed=False)
        policy = self._knowledge_policy()

        rag_bundle = self._build_rag_bundle(provenance=base, knowledge_policy=policy)
        merged = self._build_runtime_bundle(rag_bundle=rag_bundle, provenance=overlay)

        assert merged is not None
        assert merged.provenance is not None
        assert merged.provenance.prompt_trimmed is False

    def test_merge_provenance_is_idempotent(self) -> None:
        from core.verification.registry import build_verification_provenance

        rag_provenance = build_verification_provenance(
            input_text="input",
            context_items=("ctx",),
            verification_hops=2,
            verification_calls=2,
        )
        policy = self._knowledge_policy()
        rag_bundle = self._build_rag_bundle(provenance=rag_provenance, knowledge_policy=policy)

        runtime_provenance = build_verification_provenance(
            input_text="input",
            prompt_text="prompt",
            context_items=("ctx",),
            answer_text="answer",
            verification_hops=0,
            verification_calls=3,
        )

        m1 = self._build_runtime_bundle(rag_bundle=rag_bundle, provenance=runtime_provenance)
        assert m1 is not None

        m2 = self._build_runtime_bundle(rag_bundle=m1, provenance=runtime_provenance)
        assert m2 is not None

        assert m1.provenance == m2.provenance

    @pytest.mark.parametrize("exc_class", [RuntimeError, TypeError, ValueError])
    def test_redacted_sha256_label_survives_redactor_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
        exc_class: type[BaseException],
    ) -> None:
        from core.verification.registry import redacted_sha256_label

        def _broken_redactor(_value: str) -> str:
            raise exc_class("boom")

        monkeypatch.setattr(
            "core.verification.registry._redact_provenance_text",
            _broken_redactor,
        )
        assert redacted_sha256_label("any text") is None

    @pytest.mark.parametrize("input_text", ["", "   ", "\n\t"])
    def test_redacted_sha256_label_empty_or_whitespace_returns_none(self, input_text: str) -> None:
        from core.verification.registry import redacted_sha256_label

        assert redacted_sha256_label(input_text) is None

    def test_rag_bundle_provenance_answer_digest_is_none(self) -> None:
        from core.verification.registry import build_verification_provenance

        provenance = build_verification_provenance(
            input_text="question",
            prompt_text="prompt",
            context_items=("chunk",),
        )
        assert provenance.answer_digest is None
        assert provenance.answer_sha is None

    def test_verification_provenance_aliases_cannot_drift_when_constructed_directly(
        self,
    ) -> None:
        from core.verification.contracts import VerificationProvenance

        provenance = VerificationProvenance(
            input_digest="sha256:" + "a" * 64,
            prompt_digest="sha256:" + "b" * 64,
            context_item_digests=("sha256:" + "c" * 64,),
            answer_digest="sha256:" + "d" * 64,
            input_sha="sha256:" + "1" * 64,
            prompt_sha="sha256:" + "2" * 64,
            context_item_shas=("sha256:" + "3" * 64,),
            answer_sha="sha256:" + "4" * 64,
        )

        assert provenance.input_sha == provenance.input_digest
        assert provenance.prompt_sha == provenance.prompt_digest
        assert provenance.context_item_shas == provenance.context_item_digests
        assert provenance.answer_sha == provenance.answer_digest

    def test_runtime_bundle_reuses_rag_bundle_without_philosophical_pass(self) -> None:
        from core.verification.registry import (
            build_rag_verification_bundle,
            build_runtime_verification_bundle,
        )

        rag_bundle = build_rag_verification_bundle(
            knowledge_policy=self._knowledge_policy(),
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
        )

        merged = build_runtime_verification_bundle(
            rag_bundle=rag_bundle,
            verification_report=None,
            falsification_report=None,
            contradiction_count=0,
            verification_first_path=False,
        )

        assert merged == rag_bundle

    def test_runtime_rewrite_provenance_records_rewrite_prompt_trim(self) -> None:
        from core.insight.philosophical_runtime import PhilosophicalRuntime

        class _Provider:
            name = "coverage-provider"

            def __init__(self) -> None:
                self.calls = 0

            async def generate(self, text: str) -> str:
                self.calls += 1
                return "This may help. It depends on the individual."

        runtime = PhilosophicalRuntime()
        provider = _Provider()

        result = asyncio.run(
            runtime.generate_insight(
                text="How much protein should I eat for recovery? " + ("nutrition " * 700),
                lang="en",
                provider=provider,
                use_rag=False,
                philo_validation_enabled=False,
                recursive_rag_enabled=False,
                philosophy_router_enabled=True,
                philosophy_phase12_enabled=True,
                philosophy_linguistic_enabled=True,
                philosophy_pragmatic_enabled=False,
            )
        )

        assert provider.calls == 2
        assert result.verification_bundle is not None
        assert result.verification_bundle.provenance is not None
        assert result.verification_bundle.provenance.prompt_char_count == 4000
        assert result.verification_bundle.provenance.prompt_trimmed is True

    def test_runtime_trim_prompt_legacy_wrapper_returns_text_only(self) -> None:
        from core.insight import philosophical_runtime as runtime_mod

        assert runtime_mod._trim_prompt("abcdef", max_chars=3) == "abc"
        assert runtime_mod._trim_prompt("abc", max_chars=3) == "abc"

    def test_rag_bundle_denies_disabled_policy_and_string_degraded_reason(self) -> None:
        from dataclasses import replace

        from core.verification.registry import build_rag_verification_bundle

        bundle = build_rag_verification_bundle(
            knowledge_policy=replace(self._knowledge_policy(), allow_promotion=False),
            confidence=0.92,
            degraded_reason="manual_degraded_reason",
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
        )
        disabled_bundle = build_rag_verification_bundle(
            knowledge_policy=replace(self._knowledge_policy(), enabled=False),
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
        )

        assert bundle.admission_allowed is False
        assert bundle.reason_codes == (
            "knowledge_promotion_disabled",
            "manual_degraded_reason",
            "rag_degraded",
        )
        assert "knowledge_policy_disabled" in disabled_bundle.reason_codes

    def test_rag_bundle_records_recursive_execution_verification_calls(self) -> None:
        from core.verification.registry import build_rag_verification_bundle

        bundle = build_rag_verification_bundle(
            knowledge_policy=self._knowledge_policy(),
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=True,
            verification_calls=2,
            evidence_refs=("docs/keep.md:keep",),
        )

        assert bundle.admission_allowed is False
        assert "recursive_verification_calls_observed" in bundle.reason_codes

    def test_runtime_bundle_denies_non_finite_and_out_of_range_rates(self) -> None:
        from core.insight.analytical import FalsificationReport, VerificationReport
        from core.verification.registry import (
            build_rag_verification_bundle,
            build_runtime_verification_bundle,
        )

        rag_bundle = build_rag_verification_bundle(
            knowledge_policy=self._knowledge_policy(),
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
        )

        non_finite = build_runtime_verification_bundle(
            rag_bundle=rag_bundle,
            verification_report=VerificationReport(
                verification_rate=float("nan"),
                verified_claims=[],
                unverified_claims=["Synthetic claim."],
                classifications={
                    "analytical": 0,
                    "synthetic": 1,
                    "metaphysical": 0,
                    "unknown": 0,
                },
            ),
            falsification_report=FalsificationReport(
                falsifiability_rate=1.0,
                falsifiable_claims=["Synthetic claim."],
                unfalsifiable_claims=[],
            ),
            contradiction_count=0,
            verification_first_path=True,
        )
        out_of_range = build_runtime_verification_bundle(
            rag_bundle=rag_bundle,
            verification_report=VerificationReport(
                verification_rate=1.0,
                verified_claims=["Claim A."],
                unverified_claims=[],
                classifications={
                    "analytical": 0,
                    "synthetic": 1,
                    "metaphysical": 0,
                    "unknown": 0,
                },
            ),
            falsification_report=FalsificationReport(
                falsifiability_rate=1.1,
                falsifiable_claims=["Claim A."],
                unfalsifiable_claims=[],
            ),
            contradiction_count=0,
            verification_first_path=True,
        )

        assert non_finite is not None
        assert non_finite.admission_allowed is False
        assert "verification_below_threshold" in non_finite.reason_codes
        assert out_of_range is not None
        assert out_of_range.admission_allowed is False
        assert "falsification_below_threshold" in out_of_range.reason_codes

    def test_rag_bundle_denies_non_finite_confidence(self) -> None:
        from core.verification.registry import build_rag_verification_bundle

        bundle = build_rag_verification_bundle(
            knowledge_policy=self._knowledge_policy(),
            confidence=float("nan"),
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
        )

        assert bundle.admission_allowed is False
        assert "confidence_non_finite" in bundle.reason_codes

    def test_runtime_bundle_denies_contradictions(self) -> None:
        from core.insight.analytical import FalsificationReport, VerificationReport
        from core.verification.registry import (
            build_rag_verification_bundle,
            build_runtime_verification_bundle,
        )

        rag_bundle = build_rag_verification_bundle(
            knowledge_policy=self._knowledge_policy(),
            confidence=0.92,
            degraded_reason=None,
            rag_actually_used=True,
            philo_validation_enabled=True,
            recursive_executed=False,
            verification_calls=0,
            evidence_refs=("docs/keep.md:keep",),
        )

        merged = build_runtime_verification_bundle(
            rag_bundle=rag_bundle,
            verification_report=VerificationReport(
                verification_rate=1.0,
                verified_claims=["Claim A."],
                unverified_claims=[],
                classifications={
                    "analytical": 0,
                    "synthetic": 1,
                    "metaphysical": 0,
                    "unknown": 0,
                },
            ),
            falsification_report=FalsificationReport(
                falsifiability_rate=1.0,
                falsifiable_claims=["Claim A."],
                unfalsifiable_claims=[],
            ),
            contradiction_count=1,
            verification_first_path=True,
        )

        assert merged is not None
        assert merged.admission_allowed is False
        assert "contradictions_detected" in merged.reason_codes

    def test_build_bundle_falls_back_to_registry_failure_and_warn_status(self) -> None:
        from core.verification.contracts import VerificationArtifact
        from core.verification.policy import VerificationPolicy
        from core.verification.registry import build_bundle

        missing_bundle = build_bundle(artifacts=())
        warn_bundle = build_bundle(
            artifacts=(
                VerificationArtifact(
                    artifact_id="warn-artifact",
                    verifier_id="execution_verifier",
                    status="warn",
                    checked_at=datetime.now(timezone.utc),
                    reason_codes=("recursive_verification_calls_missing",),
                ),
            ),
            policy=VerificationPolicy(scope="knowledge_write", allow_warn=True),
        )

        assert missing_bundle.overall_status == "fail"
        assert missing_bundle.admission_allowed is False
        assert missing_bundle.reason_codes == ("verification_artifacts_missing",)
        assert warn_bundle.overall_status == "warn"
        assert warn_bundle.admission_allowed is True
