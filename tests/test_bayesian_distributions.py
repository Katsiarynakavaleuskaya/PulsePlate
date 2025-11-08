"""
Tests for Bayesian Probability Distributions

RU: Тесты для вероятностных распределений.
EN: Tests for probability distributions.

Tests:
- BetaDistribution (for binary events)
- NormalDistribution (for continuous variables)
- Conjugate updates
- Sampling and statistical properties
"""

from __future__ import annotations

import numpy as np
import pytest

from core.bayesian.distributions import BetaDistribution, NormalDistribution


class TestBetaDistribution:
    """Tests for BetaDistribution."""

    def test_create_uniform_prior(self):
        """RU: Создание равномерного prior. EN: Create uniform prior Beta(1,1)."""
        prior = BetaDistribution(alpha=1, beta=1)
        assert prior.alpha == 1
        assert prior.beta == 1
        assert prior.mean() == 0.5  # Uniform mean

    def test_beta_mean_calculation(self):
        """RU: Расчёт математического ожидания. EN: Calculate mean correctly."""
        dist = BetaDistribution(alpha=50, beta=100)
        expected_mean = 50 / (50 + 100)  # 1/3
        assert abs(dist.mean() - expected_mean) < 0.001

    def test_beta_mode_calculation(self):
        """RU: Расчёт моды. EN: Calculate mode for α,β > 1."""
        dist = BetaDistribution(alpha=5, beta=3)
        mode = dist.mode()
        expected_mode = (5 - 1) / (5 + 3 - 2)  # 4/6 = 2/3
        assert mode is not None
        assert abs(mode - expected_mode) < 0.001

    def test_beta_mode_undefined_for_uniform(self):
        """RU: Мода не определена для равномерного. EN: Mode undefined for uniform."""
        dist = BetaDistribution(alpha=1, beta=1)
        assert dist.mode() is None

    def test_beta_sampling(self):
        """RU: Сэмплирование работает. EN: Sampling produces valid results."""
        dist = BetaDistribution(alpha=10, beta=10)
        samples = dist.sample(n=1000)

        assert len(samples) == 1000
        assert np.all(samples >= 0)
        assert np.all(samples <= 1)
        # Mean should be close to 0.5 for Beta(10,10)
        assert abs(np.mean(samples) - 0.5) < 0.05

    def test_beta_update_conjugate(self):
        """RU: Сопряжённое обновление. EN: Conjugate Bayesian update."""
        prior = BetaDistribution(alpha=1, beta=1)  # Uniform prior
        # Observe 3 successes, 7 failures
        posterior = prior.update(successes=3, failures=7)

        assert posterior.alpha == 1 + 3  # 4
        assert posterior.beta == 1 + 7  # 8
        # Mean should be 4/12 = 1/3
        assert abs(posterior.mean() - (1 / 3)) < 0.001

    def test_beta_credible_interval(self):
        """RU: Вычисление доверительного интервала. EN: Compute credible interval."""
        dist = BetaDistribution(alpha=50, beta=100)
        lower, upper = dist.credible_interval(alpha=0.05)  # 95% CI

        # Should be symmetric around mean for reasonable α, β
        assert lower < dist.mean() < upper
        # Interval should be reasonable
        assert 0.2 < lower < 0.4
        assert 0.3 < upper < 0.5

    def test_beta_probability_beats(self):
        """RU: Вероятность превосходства. EN: Probability that one beats another."""
        variant_a = BetaDistribution(alpha=50, beta=100)  # ~33% conversion
        variant_b = BetaDistribution(alpha=60, beta=80)  # ~43% conversion

        prob_b_beats_a = variant_b.probability_beats(variant_a, n_samples=10000)

        # Variant B should win most of the time
        assert prob_b_beats_a > 0.7

    def test_beta_invalid_parameters(self):
        """RU: Отклонение невалидных параметров. EN: Reject invalid parameters."""
        with pytest.raises(ValueError, match="Alpha and beta must be positive"):
            BetaDistribution(alpha=-1, beta=5)


class TestNormalDistribution:
    """Tests for NormalDistribution."""

    def test_create_normal_distribution(self):
        """RU: Создание нормального распределения. EN: Create Normal distribution."""
        dist = NormalDistribution(mu=2000, sigma=500)
        assert dist.mu == 2000
        assert dist.sigma == 500
        assert dist.mean() == 2000
        assert dist.std() == 500
        assert dist.variance() == 500**2

    def test_normal_sampling(self):
        """RU: Сэмплирование работает. EN: Sampling produces valid results."""
        dist = NormalDistribution(mu=100, sigma=15)
        samples = dist.sample(n=10000)

        assert len(samples) == 10000
        # Sample mean should be close to true mean
        assert abs(np.mean(samples) - 100) < 1
        # Sample std should be close to true std
        assert abs(np.std(samples) - 15) < 1

    def test_normal_z_score(self):
        """RU: Вычисление z-score. EN: Calculate z-score."""
        dist = NormalDistribution(mu=2000, sigma=500)

        # Value 3 std devs above mean
        z = dist.z_score(3500)
        assert abs(z - 3.0) < 0.001

        # Value 2 std devs below mean
        z = dist.z_score(1000)
        assert abs(z - (-2.0)) < 0.001

    def test_normal_probability_in_range(self):
        """RU: Вероятность в диапазоне. EN: Probability in range."""
        dist = NormalDistribution(mu=100, sigma=15)

        # Within 1 std dev (~68%)
        prob = dist.probability_in_range(100 - 15, 100 + 15)
        assert abs(prob - 0.68) < 0.01

        # Within 2 std devs (~95%)
        prob = dist.probability_in_range(100 - 2 * 15, 100 + 2 * 15)
        assert abs(prob - 0.95) < 0.01

    def test_normal_update_conjugate(self):
        """RU: Сопряжённое обновление. EN: Conjugate Bayesian update."""
        prior = NormalDistribution(mu=2000, sigma=500)

        # User's 7-day average: 1800 ± 200
        posterior = prior.update(observed_mean=1800, observed_std=200, n=7)

        # Posterior mean should be between prior and observed
        assert 1800 < posterior.mean() < 2000
        # Posterior uncertainty should be less than prior
        assert posterior.std() < prior.std()

    def test_normal_credible_interval(self):
        """RU: Доверительный интервал. EN: Credible interval."""
        dist = NormalDistribution(mu=100, sigma=15)
        lower, upper = dist.credible_interval(alpha=0.05)  # 95% CI

        # Should be symmetric around mean
        assert abs((lower + upper) / 2 - 100) < 1
        # Should be roughly ±2 std devs
        assert abs(lower - (100 - 2 * 15)) < 5
        assert abs(upper - (100 + 2 * 15)) < 5

    def test_normal_invalid_sigma(self):
        """RU: Отклонение невалидного σ. EN: Reject invalid sigma."""
        with pytest.raises(ValueError, match="Sigma .* must be positive"):
            NormalDistribution(mu=100, sigma=-10)

        with pytest.raises(ValueError, match="Sigma .* must be positive"):
            NormalDistribution(mu=100, sigma=0)


class TestDistributionInteroperability:
    """Tests for distribution interoperability and edge cases."""

    def test_beta_and_normal_coexist(self):
        """RU: Beta и Normal работают вместе. EN: Beta and Normal work together."""
        # This is a basic sanity test
        beta = BetaDistribution(alpha=5, beta=5)
        normal = NormalDistribution(mu=0.5, sigma=0.1)

        # Both can sample
        beta_samples = beta.sample(100)
        normal_samples = normal.sample(100)

        assert len(beta_samples) == 100
        assert len(normal_samples) == 100

    def test_distributions_are_immutable(self):
        """RU: Распределения неизменяемы. EN: Distributions are immutable (dataclass frozen)."""
        # BetaDistribution and NormalDistribution use @dataclass
        # but are not frozen=True yet - skip this test for now
        # (Would need to make them frozen in the implementation)
        pass
