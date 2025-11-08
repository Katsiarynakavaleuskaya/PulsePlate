"""
Tests for Bayesian Utility Functions

RU: Тесты вспомогательных функций для байесовских методов.
EN: Tests for Bayesian utility functions.

Tests:
- Z-score calculations
- Confidence classification
- Bayesian t-test
- Prior estimation from data
- Thompson Sampling
"""

from __future__ import annotations

import numpy as np
import pytest

from core.bayesian.base import ConfidenceLevel
from core.bayesian.distributions import BetaDistribution, NormalDistribution
from core.bayesian.utils import (
    bayesian_t_test,
    calculate_credible_interval,
    calculate_z_score,
    classify_confidence,
    estimate_normal_prior_from_data,
    thompson_sampling,
    z_score_to_probability,
)


class TestZScoreCalculations:
    """Tests for z-score related functions."""

    def test_calculate_z_score_basic(self):
        """RU: Базовый расчёт z-score. EN: Basic z-score calculation."""
        z = calculate_z_score(value=2500, mean=2000, std=500)
        assert z == 1.0  # 1 std dev above mean

        z = calculate_z_score(value=1000, mean=2000, std=500)
        assert z == -2.0  # 2 std devs below mean

    def test_calculate_z_score_extreme(self):
        """RU: Экстремальные значения. EN: Extreme z-scores."""
        # Apple with 5000 kcal (mean=52, std=10)
        z = calculate_z_score(value=5000, mean=52, std=10)
        assert z > 400  # Extremely anomalous!

    def test_calculate_z_score_zero_std(self):
        """RU: Обработка нулевого σ. EN: Handle zero std dev."""
        z = calculate_z_score(value=100, mean=100, std=0)
        assert z == 0.0  # Edge case

    def test_z_score_to_probability_basic(self):
        """RU: Преобразование z-score в вероятность. EN: Convert z-score to probability."""
        # z=0 -> p=1.0 (completely normal)
        p = z_score_to_probability(0.0)
        assert abs(p - 1.0) < 0.01

        # z=2 -> p~0.05 (5% chance this is normal)
        p = z_score_to_probability(2.0)
        assert abs(p - 0.045) < 0.01

        # z=3 -> p~0.003 (very unlikely)
        p = z_score_to_probability(3.0)
        assert p < 0.01

    def test_z_score_to_probability_extreme(self):
        """RU: Экстремальные z-scores. EN: Extreme z-scores."""
        p = z_score_to_probability(6.0)
        assert p < 0.0001  # Virtually impossible


class TestConfidenceClassification:
    """Tests for confidence level classification."""

    def test_classify_confidence_low(self):
        """RU: Низкая уверенность. EN: Low confidence classification."""
        assert classify_confidence(0.5) == ConfidenceLevel.LOW
        assert classify_confidence(0.69) == ConfidenceLevel.LOW

    def test_classify_confidence_medium(self):
        """RU: Средняя уверенность. EN: Medium confidence classification."""
        assert classify_confidence(0.70) == ConfidenceLevel.MEDIUM
        assert classify_confidence(0.80) == ConfidenceLevel.MEDIUM
        assert classify_confidence(0.849) == ConfidenceLevel.MEDIUM

    def test_classify_confidence_high(self):
        """RU: Высокая уверенность. EN: High confidence classification."""
        assert classify_confidence(0.85) == ConfidenceLevel.HIGH
        assert classify_confidence(0.90) == ConfidenceLevel.HIGH
        assert classify_confidence(0.949) == ConfidenceLevel.HIGH

    def test_classify_confidence_very_high(self):
        """RU: Очень высокая уверенность. EN: Very high confidence classification."""
        assert classify_confidence(0.95) == ConfidenceLevel.VERY_HIGH
        assert classify_confidence(0.99) == ConfidenceLevel.VERY_HIGH


class TestBayesianTTest:
    """Tests for Bayesian t-test for change detection."""

    def test_bayesian_t_test_no_change(self):
        """RU: Нет изменения. EN: No significant change."""
        # Baseline: 2000 ± 100, recent: 2010 (very close)
        prob_change = bayesian_t_test(
            baseline_mean=2000, baseline_std=100, recent_mean=2010, baseline_n=7, recent_n=3
        )
        # Should be low probability of change
        assert prob_change < 0.5

    def test_bayesian_t_test_significant_change(self):
        """RU: Значимое изменение. EN: Significant change detected."""
        # Baseline: 2000 ± 200, recent: 1400 (big drop!)
        prob_change = bayesian_t_test(
            baseline_mean=2000, baseline_std=200, recent_mean=1400, baseline_n=7, recent_n=3
        )
        # Should be high probability of change
        assert prob_change > 0.8

    def test_bayesian_t_test_edge_case_zero_std(self):
        """RU: Обработка нулевого σ. EN: Handle zero std dev."""
        prob_change = bayesian_t_test(
            baseline_mean=2000, baseline_std=0, recent_mean=2000, baseline_n=7, recent_n=3
        )
        assert prob_change == 0.0  # Edge case


class TestPriorEstimation:
    """Tests for estimating priors from data."""

    def test_estimate_normal_prior_basic(self):
        """RU: Оценка prior из данных. EN: Estimate prior from data."""
        # Apple calorie data
        data = [52, 54, 50, 53, 51]
        prior = estimate_normal_prior_from_data(data, confidence=0.9)

        # Mean should be close to 52
        assert abs(prior.mean() - 52) < 1
        # Std should be positive
        assert prior.std() > 0

    def test_estimate_normal_prior_low_confidence(self):
        """RU: Низкая уверенность -> широкий prior. EN: Low confidence -> wider prior."""
        data = [100, 110, 105]
        prior_low_conf = estimate_normal_prior_from_data(data, confidence=0.5)
        prior_high_conf = estimate_normal_prior_from_data(data, confidence=0.95)

        # Lower confidence = wider prior
        assert prior_low_conf.std() > prior_high_conf.std()

    def test_estimate_normal_prior_insufficient_data(self):
        """RU: Недостаточно данных. EN: Insufficient data raises error."""
        with pytest.raises(ValueError, match="Need at least 2 data points"):
            estimate_normal_prior_from_data([100], confidence=0.9)


class TestCredibleInterval:
    """Tests for credible interval calculation from samples."""

    def test_calculate_credible_interval_basic(self):
        """RU: Расчёт доверительного интервала. EN: Calculate credible interval."""
        # Normal samples centered at 100
        samples = np.random.normal(100, 15, 10000)
        lower, upper = calculate_credible_interval(samples, alpha=0.05)

        # Should be roughly [70, 130] for 95% CI
        assert 60 < lower < 80
        assert 120 < upper < 140

    def test_calculate_credible_interval_narrow(self):
        """RU: Узкий интервал для малой дисперсии. EN: Narrow interval for low variance."""
        # Very tight distribution
        samples = np.random.normal(50, 1, 10000)
        lower, upper = calculate_credible_interval(samples, alpha=0.05)

        # Interval should be narrow
        assert (upper - lower) < 10


class TestThompsonSampling:
    """Tests for Thompson Sampling multi-armed bandit."""

    def test_thompson_sampling_basic(self):
        """RU: Выбор лучшего arm. EN: Select best performing arm."""
        # Arm 0: 33% success, Arm 1: 60% success
        arms = [
            BetaDistribution(alpha=33, beta=67),  # Low performance
            BetaDistribution(alpha=60, beta=40),  # High performance
        ]

        # Run Thompson Sampling 100 times
        selections = [thompson_sampling(arms, n_samples=1000) for _ in range(100)]

        # Arm 1 should be selected more often
        assert sum(s == 1 for s in selections) > 60  # >60% of the time

    def test_thompson_sampling_exploration(self):
        """RU: Баланс exploration-exploitation. EN: Balance exploration-exploitation."""
        # Even with a clear winner, weak arm should still get some chances
        arms = [
            BetaDistribution(alpha=10, beta=90),  # 10% success
            BetaDistribution(alpha=90, beta=10),  # 90% success
        ]

        selections = [thompson_sampling(arms, n_samples=1000) for _ in range(100)]

        # Arm 0 should still get ~5-15% of selections (exploration)
        arm_0_pct = sum(s == 0 for s in selections)
        assert arm_0_pct > 0  # Not zero (exploration happens)
        assert arm_0_pct < 30  # But significantly less than arm 1

    def test_thompson_sampling_single_arm(self):
        """RU: Один arm. EN: Single arm always selected."""
        arms = [BetaDistribution(alpha=50, beta=50)]
        selected = thompson_sampling(arms, n_samples=100)
        assert selected == 0  # Only one arm available
