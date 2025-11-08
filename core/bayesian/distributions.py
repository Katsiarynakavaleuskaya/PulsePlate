"""
Probability Distributions for Bayesian Methods

RU: Реализации вероятностных распределений для байесовских методов.
EN: Concrete probability distribution implementations.

Provides:
- BetaDistribution: For binary events (clicks, conversions, success/failure)
- NormalDistribution: For continuous variables (calories, weight, nutrients)
- Both support prior/posterior usage with conjugate updates
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import stats

from .base import Posterior, Prior


@dataclass
class BetaDistribution(Prior[float], Posterior[float]):
    """
    RU: Бета-распределение для бинарных событий.
    EN: Beta distribution for binary events (success/failure).

    Conjugate prior for Bernoulli/Binomial likelihoods.
    Commonly used for:
    - Click-through rates
    - Conversion probabilities
    - Thompson Sampling in multi-armed bandits

    Parameters:
        alpha: Number of successes + 1 (shape parameter)
        beta: Number of failures + 1 (shape parameter)

    Examples:
        >>> # Uniform prior (no prior knowledge)
        >>> prior = BetaDistribution(alpha=1, beta=1)
        >>> # After observing 3 successes and 7 failures
        >>> posterior = prior.update(successes=3, failures=7)
        >>> posterior.mean()  # ~0.3
    """

    alpha: float = 1.0
    beta: float = 1.0

    def __post_init__(self):
        """Validate parameters."""
        if self.alpha <= 0 or self.beta <= 0:
            raise ValueError("Alpha and beta must be positive")

    def sample(self, n: int = 1) -> np.ndarray:
        """
        RU: Сэмплировать из бета-распределения.
        EN: Draw random samples from Beta(alpha, beta).
        """
        return np.random.beta(self.alpha, self.beta, size=n)

    def pdf(self, x: float) -> float:
        """
        RU: Плотность вероятности в точке x.
        EN: Probability density at x ∈ [0, 1].
        """
        if not (0 <= x <= 1):
            return 0.0
        return stats.beta.pdf(x, self.alpha, self.beta)

    def mean(self) -> float:
        """
        RU: Математическое ожидание: E[X] = α / (α + β).
        EN: Expected value: E[X] = α / (α + β).
        """
        return self.alpha / (self.alpha + self.beta)

    def mode(self) -> Optional[float]:
        """
        RU: Мода распределения (наиболее вероятное значение).
        EN: Mode (most probable value).

        Returns:
            Mode if α,β > 1, else None (undefined for uniform/U-shaped)
        """
        if self.alpha > 1 and self.beta > 1:
            return (self.alpha - 1) / (self.alpha + self.beta - 2)
        return None

    def std(self) -> float:
        """
        RU: Стандартное отклонение.
        EN: Standard deviation.
        """
        return np.sqrt(self.variance())

    def variance(self) -> float:
        """
        RU: Дисперсия: Var[X] = αβ / [(α+β)²(α+β+1)].
        EN: Variance: Var[X] = αβ / [(α+β)²(α+β+1)].
        """
        alpha_beta_sum = self.alpha + self.beta
        return (self.alpha * self.beta) / (
            alpha_beta_sum**2 * (alpha_beta_sum + 1)
        )

    def credible_interval(self, alpha: float = 0.05) -> tuple[float, float]:
        """
        RU: Вычислить байесовский доверительный интервал.
        EN: Compute (1-alpha)% credible interval.

        Args:
            alpha: Significance level (default 0.05 for 95% CI)

        Returns:
            (lower, upper) bounds such that P(lower < θ < upper) = 1-alpha
        """
        lower = stats.beta.ppf(alpha / 2, self.alpha, self.beta)
        upper = stats.beta.ppf(1 - alpha / 2, self.alpha, self.beta)
        return (lower, upper)

    def update(
        self, successes: int = 0, failures: int = 0
    ) -> BetaDistribution:
        """
        RU: Байесовское обновление с новыми наблюдениями.
        EN: Bayesian update with new observations (conjugate update).

        Args:
            successes: Number of successes observed
            failures: Number of failures observed

        Returns:
            New BetaDistribution with updated parameters

        Note:
            Posterior: Beta(α + successes, β + failures)
        """
        return BetaDistribution(
            alpha=self.alpha + successes, beta=self.beta + failures
        )

    def probability_beats(self, other: BetaDistribution, n_samples: int = 10000) -> float:
        """
        RU: Вероятность что это распределение "лучше" другого.
        EN: Probability that this distribution beats another (for A/B testing).

        Args:
            other: Another Beta distribution to compare against
            n_samples: Number of Monte Carlo samples

        Returns:
            P(this > other) estimated via sampling

        Example:
            >>> variant_a = BetaDistribution(alpha=50, beta=100)
            >>> variant_b = BetaDistribution(alpha=60, beta=90)
            >>> variant_b.probability_beats(variant_a)  # ~0.75
        """
        samples_this = self.sample(n_samples)
        samples_other = other.sample(n_samples)
        return np.mean(samples_this > samples_other)


@dataclass
class NormalDistribution(Prior[float], Posterior[float]):
    """
    RU: Нормальное распределение для непрерывных переменных.
    EN: Normal (Gaussian) distribution for continuous variables.

    Commonly used for:
    - Calorie intake modeling
    - Weight tracking
    - Nutrient levels
    - General continuous metrics

    Parameters:
        mu: Mean (location parameter)
        sigma: Standard deviation (scale parameter, must be > 0)

    Examples:
        >>> # Prior: average person consumes 2000±500 kcal
        >>> prior = NormalDistribution(mu=2000, sigma=500)
        >>> # User's data suggests 1800 kcal with uncertainty 200
        >>> posterior = prior.update(observed_mean=1800, observed_std=200, n=7)
    """

    mu: float  # Mean
    sigma: float  # Standard deviation

    def __post_init__(self):
        """Validate parameters."""
        if self.sigma <= 0:
            raise ValueError("Sigma (std dev) must be positive")

    def sample(self, n: int = 1) -> np.ndarray:
        """
        RU: Сэмплировать из нормального распределения.
        EN: Draw random samples from N(μ, σ²).
        """
        return np.random.normal(self.mu, self.sigma, size=n)

    def pdf(self, x: float) -> float:
        """
        RU: Плотность вероятности в точке x.
        EN: Probability density at x.
        """
        return stats.norm.pdf(x, self.mu, self.sigma)

    def mean(self) -> float:
        """
        RU: Математическое ожидание: E[X] = μ.
        EN: Expected value: E[X] = μ.
        """
        return self.mu

    def std(self) -> float:
        """
        RU: Стандартное отклонение: σ.
        EN: Standard deviation: σ.
        """
        return self.sigma

    def variance(self) -> float:
        """
        RU: Дисперсия: Var[X] = σ².
        EN: Variance: Var[X] = σ².
        """
        return self.sigma**2

    def credible_interval(self, alpha: float = 0.05) -> tuple[float, float]:
        """
        RU: Вычислить доверительный интервал.
        EN: Compute (1-alpha)% credible interval.
        """
        lower = stats.norm.ppf(alpha / 2, self.mu, self.sigma)
        upper = stats.norm.ppf(1 - alpha / 2, self.mu, self.sigma)
        return (lower, upper)

    def z_score(self, x: float) -> float:
        """
        RU: Вычислить z-score (стандартизированное отклонение).
        EN: Compute z-score: (x - μ) / σ.

        Returns:
            Number of standard deviations x is from the mean
        """
        return (x - self.mu) / self.sigma

    def probability_in_range(self, lower: float, upper: float) -> float:
        """
        RU: Вероятность что значение попадёт в диапазон [lower, upper].
        EN: P(lower ≤ X ≤ upper).
        """
        return stats.norm.cdf(upper, self.mu, self.sigma) - stats.norm.cdf(
            lower, self.mu, self.sigma
        )

    def update(
        self,
        observed_mean: float,
        observed_std: float,
        n: int,
        prior_precision_weight: float = 1.0,
    ) -> NormalDistribution:
        """
        RU: Байесовское обновление с новыми наблюдениями (conjugate update).
        EN: Bayesian update assuming Normal likelihood with known variance.

        Args:
            observed_mean: Mean of observed data
            observed_std: Standard deviation of observed data
            n: Number of observations
            prior_precision_weight: Relative weight of prior vs data (default 1.0)

        Returns:
            New NormalDistribution with updated parameters

        Note:
            Uses precision-weighted average of prior and likelihood.
            Higher prior_precision_weight = stronger prior belief.
        """
        # Precision = 1 / variance
        prior_precision = prior_precision_weight / (self.sigma**2)
        data_precision = n / (observed_std**2)
        posterior_precision = prior_precision + data_precision

        # Precision-weighted mean
        posterior_mean = (
            prior_precision * self.mu + data_precision * observed_mean
        ) / posterior_precision

        posterior_std = np.sqrt(1 / posterior_precision)

        return NormalDistribution(mu=posterior_mean, sigma=posterior_std)


__all__ = [
    "BetaDistribution",
    "NormalDistribution",
]
