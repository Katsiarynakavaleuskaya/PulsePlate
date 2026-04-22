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
            verification_bundle=self._verification_bundle(),
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
            verification_bundle=self._verification_bundle(),
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
            verification_bundle=self._verification_bundle(),
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
            verification_bundle=self._verification_bundle(),
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

    def test_runtime_bundle_passthrough_when_runtime_verification_is_disabled(self) -> None:
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
            verification_first_path=True,
            runtime_verification_enabled=False,
        )

        assert merged == rag_bundle

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
