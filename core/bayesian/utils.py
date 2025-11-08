"""
Utility Functions for Bayesian Inference

RU: Вспомогательные функции для байесовских вычислений.
EN: Helper functions for Bayesian computations.

Provides:
- Anomaly scoring (z-score, probability-based)
- Confidence level classification
- Statistical testing utilities
- Prior generation from data
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from scipy import stats

from .base import ConfidenceLevel
from .distributions import NormalDistribution


def calculate_z_score(value: float, mean: float, std: float) -> float:
    """
    RU: Вычислить z-score (стандартизированное отклонение).
    EN: Calculate z-score: (value - mean) / std.

    Args:
        value: Observed value
        mean: Population/prior mean
        std: Population/prior standard deviation

    Returns:
        Number of standard deviations from mean

    Example:
        >>> calculate_z_score(5000, 2000, 500)  # Apple with 5000 kcal
        6.0  # 6 standard deviations away!
    """
    if std == 0:
        return 0.0
    return (value - mean) / std


def z_score_to_probability(z_score: float) -> float:
    """
    RU: Преобразовать z-score в вероятность аномалии.
    EN: Convert z-score to anomaly probability.

    Uses two-tailed test: P(|Z| > |z_score|)

    Args:
        z_score: Standardized deviation

    Returns:
        Probability that value is anomalous (0-1)

    Example:
        >>> z_score_to_probability(3.0)  # 3 std devs away
        0.0027  # ~0.3% chance this is normal
    """
    # Two-tailed test: probability in both tails
    return 2 * (1 - stats.norm.cdf(abs(z_score)))


def classify_confidence(probability: float) -> ConfidenceLevel:
    """
    RU: Классифицировать вероятность в уровень уверенности.
    EN: Classify probability into confidence level category.

    Args:
        probability: Confidence probability (0-1)

    Returns:
        ConfidenceLevel enum

    Thresholds:
        - < 0.7: LOW
        - 0.7-0.85: MEDIUM
        - 0.85-0.95: HIGH
        - > 0.95: VERY_HIGH
    """
    if probability < 0.7:
        return ConfidenceLevel.LOW
    elif probability < 0.85:
        return ConfidenceLevel.MEDIUM
    elif probability < 0.95:
        return ConfidenceLevel.HIGH
    else:
        return ConfidenceLevel.VERY_HIGH


def bayesian_t_test(
    baseline_mean: float,
    baseline_std: float,
    recent_mean: float,
    baseline_n: int = 7,
    recent_n: int = 3,
) -> float:
    """
    RU: Байесовский t-тест для обнаружения изменений.
    EN: Bayesian t-test for change detection.

    Tests whether recent data differs significantly from baseline.

    Args:
        baseline_mean: Mean of baseline period
        baseline_std: Std dev of baseline period
        recent_mean: Mean of recent period
        baseline_n: Number of baseline observations
        recent_n: Number of recent observations

    Returns:
        Probability that a significant change occurred (0-1)

    Example:
        >>> # User ate 2000 kcal/day for a week, then 1400 for 3 days
        >>> bayesian_t_test(2000, 200, 1400, baseline_n=7, recent_n=3)
        0.95  # 95% probability of significant change
    """
    # Estimate variance assuming equal variance
    pooled_std = baseline_std  # Simplified assumption

    # Standard error of difference
    se_diff = pooled_std * np.sqrt(1 / baseline_n + 1 / recent_n)

    if se_diff == 0:
        return 0.0

    # t-statistic
    t_stat = abs(baseline_mean - recent_mean) / se_diff

    # Degrees of freedom
    df = baseline_n + recent_n - 2

    # Two-tailed p-value
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))

    # Convert p-value to "probability of change"
    # Lower p-value = higher probability of change
    return 1 - p_value


def estimate_normal_prior_from_data(
    data: List[float], confidence: float = 0.9
) -> NormalDistribution:
    """
    RU: Оценить нормальный prior из данных.
    EN: Estimate Normal prior from data.

    Uses sample mean and std with uncertainty adjustment.

    Args:
        data: List of observations
        confidence: Confidence in the estimates (0-1)
            Lower confidence = wider prior

    Returns:
        NormalDistribution representing prior belief

    Example:
        >>> # Historical calorie data for apples
        >>> apple_data = [52, 54, 50, 53, 51]
        >>> prior = estimate_normal_prior_from_data(apple_data)
        >>> prior.mean()  # ~52
        >>> prior.std()   # ~1.5
    """
    if len(data) < 2:
        raise ValueError("Need at least 2 data points to estimate prior")

    data_array = np.array(data)
    sample_mean = float(np.mean(data_array))
    sample_std = float(np.std(data_array, ddof=1))

    # Adjust std based on confidence and sample size
    # Less confidence or fewer samples = wider prior
    n = len(data)
    adjustment_factor = 1 / np.sqrt(confidence * n)
    adjusted_std = sample_std * (1 + adjustment_factor)

    return NormalDistribution(mu=sample_mean, sigma=adjusted_std)


def calculate_credible_interval(
    samples: np.ndarray, alpha: float = 0.05
) -> Tuple[float, float]:
    """
    RU: Вычислить байесовский доверительный интервал из сэмплов.
    EN: Calculate Bayesian credible interval from samples.

    Args:
        samples: Array of samples from posterior distribution
        alpha: Significance level (default 0.05 for 95% CI)

    Returns:
        (lower, upper) bounds of credible interval

    Example:
        >>> samples = np.random.normal(100, 10, 10000)
        >>> lower, upper = calculate_credible_interval(samples)
        >>> # ~(80, 120) for 95% CI
    """
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    lower = float(np.percentile(samples, lower_percentile))
    upper = float(np.percentile(samples, upper_percentile))

    return (lower, upper)


def effective_sample_size(
    prior_std: float, likelihood_std: float, n_observations: int
) -> float:
    """
    RU: Вычислить эффективный размер выборки для байесовского обновления.
    EN: Calculate effective sample size for Bayesian update.

    Quantifies how much the prior shrinks after observing data.

    Args:
        prior_std: Prior standard deviation
        likelihood_std: Likelihood standard deviation
        n_observations: Number of observations

    Returns:
        Effective number of observations (including prior as pseudo-observations)

    Higher value = more influence from data vs. prior
    """
    prior_precision = 1 / (prior_std**2)
    data_precision = n_observations / (likelihood_std**2)
    return prior_precision + data_precision


def thompson_sampling(distributions: List, n_samples: int = 1000) -> int:
    """
    RU: Thompson Sampling для multi-armed bandits.
    EN: Thompson Sampling for multi-armed bandit problems.

    Randomly selects an arm based on its probability of being optimal.

    Args:
        distributions: List of probability distributions (e.g., BetaDistributions)
        n_samples: Number of samples to draw per arm

    Returns:
        Index of selected arm (0-indexed)

    Example:
        >>> from .distributions import BetaDistribution
        >>> arms = [
        ...     BetaDistribution(alpha=50, beta=100),  # ~33% success rate
        ...     BetaDistribution(alpha=60, beta=80),   # ~43% success rate
        ... ]
        >>> selected_arm = thompson_sampling(arms)
        >>> # More likely to select arm 1, but arm 0 still has a chance
    """
    samples = [dist.sample(n_samples).mean() for dist in distributions]
    return int(np.argmax(samples))


__all__ = [
    "calculate_z_score",
    "z_score_to_probability",
    "classify_confidence",
    "bayesian_t_test",
    "estimate_normal_prior_from_data",
    "calculate_credible_interval",
    "effective_sample_size",
    "thompson_sampling",
]
