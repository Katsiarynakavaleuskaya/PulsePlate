"""
Shared test constants for Bayesian analyzer tests.

RU: Общие константы порогов для тестов байесовских анализаторов.
EN: Shared threshold constants for Bayesian analyzer tests.
"""

from typing import Final

# Test threshold constants for risk and health assessment
# RU: Константы порогов для оценки рисков и здоровья
# EN: Score thresholds for risk and health assessment

MEDIUM_SCORE_THRESHOLD: Final[float] = 0.6  # Score threshold for medium-severity issues
HIGH_SCORE_THRESHOLD: Final[float] = 0.95  # Score threshold for high-quality systems
EXCELLENT_HEALTH_THRESHOLD: Final[float] = 0.85  # Score for excellent system health
GOOD_HEALTH_THRESHOLD: Final[float] = 0.65  # Score for good/fair system health

# Issue count thresholds
# RU: Пороги количества проблем для определения приоритета
# EN: Issue count thresholds for priority determination

CRITICAL_ISSUES_COUNT: Final[int] = 3  # Number of critical issues triggering urgent priority
HIGH_ISSUES_COUNT: Final[int] = 2  # Number of issues for high-quality threshold
LOW_ISSUES_COUNT: Final[int] = 1  # Minimum issue count for fair health status
