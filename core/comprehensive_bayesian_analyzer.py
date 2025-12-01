#!/usr/bin/env python3
"""
Комплексный байесовский анализатор, объединяющий все аспекты системы PulsePlate:
- Технические аспекты
- Питание и здоровье
- Бизнес-логика и монетизация
- Создание базы клиентов
- Экономия средств
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from core.bayesian_test_analyzer import BayesianTestAnalyzer
from core.business_bayesian_analyzer import BusinessBayesianAnalyzer
from core.nutrition_bayesian_analyzer import NutritionBayesianAnalyzer


class ComprehensiveCategory(Enum):
    """Комплексные категории анализа."""

    TECHNICAL_EXCELLENCE = "technical_excellence"
    HEALTH_SAFETY = "health_safety"
    BUSINESS_GROWTH = "business_growth"
    COST_EFFICIENCY = "cost_efficiency"
    CUSTOMER_SUCCESS = "customer_success"
    REVENUE_OPTIMIZATION = "revenue_optimization"
    DATA_MONETIZATION = "data_monetization"
    MARKET_EXPANSION = "market_expansion"
    OPERATIONAL_EXCELLENCE = "operational_excellence"
    INNOVATION_POTENTIAL = "innovation_potential"


@dataclass
class ComprehensiveTestResult:
    """Комплексный результат анализа теста."""

    test_name: str
    success: bool
    technical_score: float
    nutrition_score: float
    business_score: float
    overall_score: float
    revenue_impact: str
    cost_impact: str
    customer_impact: str
    health_impact: str
    risk_level: str  # low, medium, high, critical
    priority: str  # low, medium, high, urgent
    critical_issues: List[str] = field(default_factory=list)
    optimization_opportunities: List[str] = field(default_factory=list)


class ComprehensiveBayesianAnalyzer:
    """Комплексный байесовский анализатор для всех аспектов системы."""

    # Technical score penalty constants
    # RU: Константы штрафов для технического балла
    # EN: Penalty values for technical score calculation
    CRITICAL_PENALTY = 0.3  # Penalty for critical technical issues (AsyncMock, exceptions)
    MAJOR_PENALTY = 0.2  # Penalty for major technical issues (typing, await)
    MINOR_PENALTY = 0.1  # Penalty for minor technical issues

    # Business score penalty constants
    # RU: Константы штрафов для бизнес-балла
    # EN: Penalty values for business score calculation
    BUSINESS_PENALTY_CRITICAL = 0.4  # Penalty for critical business issues (revenue)
    BUSINESS_PENALTY_IMPORTANT = 0.3  # Penalty for important business issues (customer)
    BUSINESS_PENALTY_NORMAL = 0.2  # Penalty for normal business issues

    # Scoring thresholds
    # RU: Пороги для оценки успешности тестов
    # EN: Thresholds for test success scoring
    SUCCESS_SCORE_THRESHOLD = 0.8  # Minimum overall score for test success
    NUTRITION_MIN_CONTRIBUTION = 1.0  # Minimum contribution when no nutrition checks are run

    # Risk level calculation thresholds
    # RU: Пороги для расчета уровня риска
    # EN: Thresholds for risk level calculation
    CRITICAL_ISSUE_COUNT_THRESHOLD = 5  # Number of critical issues for critical risk level
    HIGH_ISSUE_COUNT_THRESHOLD = 3  # Number of critical issues for high risk level
    MEDIUM_ISSUE_COUNT_THRESHOLD = 1  # Number of critical issues for medium risk level
    CRITICAL_SCORE_THRESHOLD = 0.3  # Score threshold for critical risk level
    HIGH_SCORE_THRESHOLD = 0.5  # Score threshold for high risk level
    MEDIUM_SCORE_THRESHOLD = 0.7  # Score threshold for medium risk level

    # System health calculation thresholds
    # RU: Пороги для расчета здоровья системы
    # EN: Thresholds for system health calculation
    EXCELLENT_SCORE_THRESHOLD = 0.9  # Score threshold for excellent system health
    GOOD_SCORE_THRESHOLD = 0.8  # Score threshold for good system health
    FAIR_SCORE_THRESHOLD = 0.6  # Score threshold for fair system health
    EXCELLENT_HIGH_RISK_COUNT_THRESHOLD = 1  # Maximum high-risk count for excellent health
    GOOD_HIGH_RISK_COUNT_THRESHOLD = 3  # Maximum high-risk count for good health
    FAIR_CRITICAL_RISK_COUNT_THRESHOLD = 1  # Maximum critical-risk count for fair health

    # Action plan limits
    # RU: Лимиты для плана действий
    # EN: Limits for action plan recommendations
    ACTION_PLAN_RECOMMENDATION_LIMIT = 5  # Maximum number of recommendations per category
    ACTION_PLAN_CRITICAL_TESTS_DISPLAY_LIMIT = (
        3  # Maximum number of critical tests to display in immediate actions
    )

    # Impact assessment thresholds
    # RU: Пороги для оценки влияния на различные аспекты
    # EN: Thresholds for impact assessment (revenue, cost, customer, health)
    MINIMAL_IMPACT_THRESHOLD = 2  # Maximum issue count for minimal impact
    MEDIUM_IMPACT_THRESHOLD = 5  # Maximum issue count for medium impact

    # Priority calculation thresholds
    # RU: Пороги для расчета приоритета
    # EN: Thresholds for priority calculation
    URGENT_PRIORITY_ISSUE_COUNT = 3  # Minimum critical issues for urgent priority
    HIGH_PRIORITY_ISSUE_COUNT = 1  # Minimum critical issues for high priority

    # Configurable keywords for critical nutrition issues detection
    # RU: Ключевые слова для обнаружения критических проблем питания
    CRITICAL_NUTRITION_KEYWORDS = (
        "калорий",
        "calorie",
        "bmi",
        "dangerous",
        "опасно",
    )

    # Technical issue severity keywords (bilingual: Russian and English)
    # RU: Ключевые слова для определения серьезности технических проблем
    # EN: Used in _calculate_technical_score and _identify_critical_issues for consistent scoring
    CRITICAL_TECHNICAL_KEYWORDS = (
        "asyncmock",
        "исключен",
        "exception",
        "исключение",
        "безопасность",
        "security",
    )
    MAJOR_TECHNICAL_KEYWORDS = ("типизац", "typing", "type", "await")

    # Business issue severity keywords (bilingual: Russian and English)
    # RU: Ключевые слова для определения серьезности бизнес-проблем
    # EN: Used in _calculate_business_score and _identify_critical_issues for consistent scoring

    # Revenue-related critical keywords
    CRITICAL_REVENUE_KEYWORDS = ("доход", "revenue", "income")
    # Customer-related important keywords
    IMPORTANT_CUSTOMER_KEYWORDS = ("клиент", "customer", "client")
    # Combined for backward compatibility and critical issues identification
    CRITICAL_BUSINESS_KEYWORDS = CRITICAL_REVENUE_KEYWORDS + IMPORTANT_CUSTOMER_KEYWORDS

    # Standardized business marker prefix for critical business issues
    # RU: Стандартизированный префикс маркера для критических бизнес-проблем
    BUSINESS_MARKER_PREFIX = "business:"

    def __init__(self) -> None:
        self.technical_analyzer = BayesianTestAnalyzer()
        self.nutrition_analyzer = NutritionBayesianAnalyzer()
        self.business_analyzer = BusinessBayesianAnalyzer()
        self.comprehensive_results: List[ComprehensiveTestResult] = []
        self.system_vision = self._load_system_vision()

    def _has_critical_nutrition_issues(self, issues: List[str]) -> bool:
        """
        Проверяет наличие критических проблем питания в списке проблем.

        Args:
            issues: Список строк с описанием проблем

        Returns:
            True, если обнаружены критические проблемы питания, иначе False

        EN: Checks for critical nutrition issues in the list of issues.
        Uses configurable keywords (Russian and English) with case-insensitive matching.
        """
        if not issues:
            return False

        # Convert all keywords to lowercase for case-insensitive matching
        # RU: Преобразуем все ключевые слова в нижний регистр для регистронезависимого поиска
        keywords_lower = [keyword.lower() for keyword in self.CRITICAL_NUTRITION_KEYWORDS]

        # Nested any loop: check if any issue contains any keyword
        # RU: Вложенный цикл any: проверяем, содержит ли какая-либо проблема какое-либо ключевое слово
        return any(any(keyword in issue.lower() for keyword in keywords_lower) for issue in issues)

    def _has_critical_business_issues(self, issues: List[str]) -> bool:
        """
        Проверяет наличие критических бизнес-проблем в списке проблем.

        Args:
            issues: Список строк с описанием проблем

        Returns:
            True, если обнаружены критические бизнес-проблемы, иначе False

        EN: Checks for critical business issues using a standardized marker prefix.
        Uses case-insensitive startswith matching for the normalized prefix.
        """
        if not issues:
            return False

        # Normalize prefix to lowercase for case-insensitive matching
        # RU: Нормализуем префикс в нижний регистр для регистронезависимого поиска
        normalized_prefix = self.BUSINESS_MARKER_PREFIX.lower()

        # Check if any issue starts with the normalized business marker prefix
        # RU: Проверяем, начинается ли какая-либо проблема с нормализованного префикса бизнес-маркера
        return any(issue.lower().startswith(normalized_prefix) for issue in issues)

    def _load_system_vision(self) -> Dict[str, Any]:
        """Загружает видение системы PulsePlate."""
        return {
            "mission": "Сделать здоровое питание доступным и персонализированным для каждого",
            "vision": "Стать ведущей платформой для здорового образа жизни с 10M+ пользователей",
            "values": [
                "Здоровье превыше прибыли",
                "Научная точность",
                "Персонализация",
                "Доступность",
                "Прозрачность",
                "Устойчивость",
            ],
            "business_goals": {
                "revenue_target": 10000000,  # $10M ARR
                "user_target": 1000000,  # 1M активных пользователей
                "retention_target": 0.85,  # 85% retention rate
                "ltv_target": 500,  # $500 LTV
                "cac_target": 50,  # $50 CAC
                "mrr_target": 500000,  # $500K MRR
            },
            "technical_goals": {
                "coverage_target": 0.97,  # 97% test coverage
                "uptime_target": 0.999,  # 99.9% uptime
                "response_time_target": 200,  # 200ms response time
                "security_score": 0.95,  # 95% security score
            },
            "health_goals": {
                "safety_score": 0.99,  # 99% safety score
                "accuracy_score": 0.95,  # 95% nutrition accuracy
                "compliance_score": 0.98,  # 98% medical compliance
            },
        }

    def analyze_comprehensively(
        self, test_code: str, test_name: str, file_path: str
    ) -> ComprehensiveTestResult:
        """Комплексный анализ теста по всем аспектам."""

        # Технический анализ
        technical_issues = self.technical_analyzer.analyze_technical_aspects(test_code, test_name)
        technical_score = self._calculate_technical_score(technical_issues)

        # Анализ питания
        nutrition_results = self.nutrition_analyzer.analyze_nutrition_safety(test_code, test_name)
        nutrition_issues = [
            r.error_message
            for r in nutrition_results
            if not r.success and r.error_message is not None
        ]
        # Compute per-test nutrition score from results (not cumulative state)
        # RU: Вычисляем балл питания для этого теста на основе результатов (не накопительный)
        if nutrition_results:
            successful_checks = sum(r.success for r in nutrition_results)
            total_checks = len(nutrition_results)
            nutrition_score = successful_checks / total_checks
        else:
            # No checks performed → perfect score by default
            nutrition_score = 1.0

        # Бизнес-анализ
        business_results = self.business_analyzer.analyze_business_logic(test_code, test_name)
        business_issues = [
            r.error_message
            for r in business_results
            if not r.success and r.error_message is not None
        ]
        business_score = self._calculate_business_score(business_issues)

        # Общий балл
        # Health First policy: nutrition issues should appropriately reduce overall score
        # Use raw nutrition_score when nutrition checks were performed; otherwise treat as
        # fully satisfied (minimum contribution = 1.0) to match historical behavior / tests.
        nutrition_effective = (
            nutrition_score if nutrition_results else self.NUTRITION_MIN_CONTRIBUTION
        )
        overall_score = (technical_score + nutrition_effective + business_score) / 3

        # Критические проблемы
        critical_issues = self._identify_critical_issues(
            technical_issues, nutrition_issues, business_issues, test_name
        )

        # Health First policy: critical nutrition issues force failure
        # Check for critical nutrition issues (very low calories, dangerous BMI, etc.)
        # RU: Проверка критических проблем питания через централизованный метод
        has_critical_nutrition_issues = self._has_critical_nutrition_issues(nutrition_issues)

        # Apply heavy penalty for critical nutrition issues
        # Note: This sets overall_score to 0.0, which will fail the threshold check below
        if has_critical_nutrition_issues:
            overall_score = 0.0

        # Возможности оптимизации
        optimization_opportunities = self._identify_optimization_opportunities(
            technical_issues, nutrition_issues, business_issues
        )

        # Влияние на различные аспекты
        revenue_impact = self._assess_revenue_impact(
            technical_issues, nutrition_issues, business_issues
        )
        cost_impact = self._assess_cost_impact(technical_issues, nutrition_issues, business_issues)
        customer_impact = self._assess_customer_impact(
            technical_issues, nutrition_issues, business_issues
        )
        health_impact = self._assess_health_impact(nutrition_issues)

        # Уровень риска и приоритет
        risk_level = self._calculate_risk_level(critical_issues, overall_score)
        priority = self._calculate_priority(critical_issues, revenue_impact, health_impact)

        # Determine success: must pass threshold
        # EN: overall_score is set to 0.0 when critical nutrition issues exist (see penalty above),
        # so the threshold check alone is sufficient. Critical business issues are handled
        # through the overall_score calculation and threshold check.
        # RU: при наличии критических проблем питания overall_score принудительно устанавливается в 0.0,
        # поэтому проверка порога достаточна. Критические бизнес-проблемы обрабатываются
        # через расчет overall_score и проверку порога.
        success = overall_score >= self.SUCCESS_SCORE_THRESHOLD

        result = ComprehensiveTestResult(
            test_name=test_name,
            success=success,
            technical_score=technical_score,
            nutrition_score=nutrition_score,
            business_score=business_score,
            overall_score=overall_score,
            critical_issues=critical_issues,
            optimization_opportunities=optimization_opportunities,
            revenue_impact=revenue_impact,
            cost_impact=cost_impact,
            customer_impact=customer_impact,
            health_impact=health_impact,
            risk_level=risk_level,
            priority=priority,
        )

        self.comprehensive_results.append(result)
        return result

    def _calculate_technical_score(self, issues: List[str]) -> float:
        """Вычисляет технический балл."""
        if not issues:
            return 1.0

        # Use centralized keyword constants for consistent scoring
        # RU: Используем централизованные константы ключевых слов для согласованной оценки
        penalty = 0.0
        for issue in issues:
            issue_lower = issue.lower()
            if any(keyword in issue_lower for keyword in self.CRITICAL_TECHNICAL_KEYWORDS):
                penalty += self.CRITICAL_PENALTY  # Критические проблемы
            elif any(keyword in issue_lower for keyword in self.MAJOR_TECHNICAL_KEYWORDS):
                penalty += self.MAJOR_PENALTY  # Важные проблемы
            else:
                penalty += self.MINOR_PENALTY  # Обычные проблемы

        return max(0.0, 1.0 - penalty)

    def _calculate_business_score(self, issues: List[str]) -> float:
        """Вычисляет бизнес-балл."""
        if not issues:
            return 1.0

        # Use centralized keyword constants for consistent scoring
        # RU: Используем централизованные константы ключевых слов для согласованной оценки
        penalty = 0.0
        for issue in issues:
            issue_lower = issue.lower()
            if any(keyword in issue_lower for keyword in self.CRITICAL_REVENUE_KEYWORDS):
                penalty += self.BUSINESS_PENALTY_CRITICAL  # Критические бизнес-проблемы
            elif any(keyword in issue_lower for keyword in self.IMPORTANT_CUSTOMER_KEYWORDS):
                penalty += self.BUSINESS_PENALTY_IMPORTANT  # Важные проблемы
            else:
                penalty += self.BUSINESS_PENALTY_NORMAL  # Обычные проблемы

        return max(0.0, 1.0 - penalty)

    def _identify_critical_issues(
        self, technical: List[str], nutrition: List[str], business: List[str], test_name: str = ""
    ) -> List[str]:
        """Идентифицирует критические проблемы.

        Leverages structured nutrition severity metadata (safety_level='dangerous')
        instead of substring matching for health-first logic.

        Args:
            technical: List of technical issues
            nutrition: List of nutrition issues
            business: List of business issues
            test_name: Current test name to filter nutrition results (optional)
        """
        critical = []

        # Критические технические проблемы - use centralized keywords
        # RU: Используем централизованные ключевые слова из CRITICAL_TECHNICAL_KEYWORDS
        for issue in technical:
            if any(keyword in issue.lower() for keyword in self.CRITICAL_TECHNICAL_KEYWORDS):
                critical.append(f"TECH: {issue}")

        # Критические проблемы питания - prioritize structured metadata from NutritionBayesianAnalyzer
        # RU: Приоритет структурированным метаданным от NutritionBayesianAnalyzer
        health_added = False

        if hasattr(self, "nutrition_analyzer") and hasattr(self.nutrition_analyzer, "test_results"):
            # Use structured safety_level from NutritionTestResult for precision
            # Filter to current test if test_name provided to prevent leakage from past tests
            for result in self.nutrition_analyzer.test_results:
                # Only consider dangerous results for current test to avoid past-test contamination
                if (
                    not result.success
                    and result.safety_level == "dangerous"
                    and (not test_name or result.test_name == test_name)
                ):
                    critical.append(f"HEALTH: {result.error_message}")
                    health_added = True
        # Fallback to substring matching if structured data unavailable OR no structured hits found
        if not health_added:
            for issue in nutrition:
                if any(
                    keyword in issue.lower()
                    for keyword in ["опасно", "dangerous", "критично", "critical", "риск", "risk"]
                ):
                    critical.append(f"HEALTH: {issue}")
                    health_added = True

        # Критические бизнес-проблемы - use centralized keywords
        # RU: Помечаем критические бизнес-проблемы стандартным префиксом для дальнейшей фильтрации
        # EN: Tag critical business issues with marker prefix for downstream filtering via _has_critical_business_issues()
        for issue in business:
            if any(keyword in issue.lower() for keyword in self.CRITICAL_BUSINESS_KEYWORDS):
                # Prefix ensures _has_critical_business_issues() can detect these issues
                # No space after colon to match the startswith check in _has_critical_business_issues()
                critical.append(f"{self.BUSINESS_MARKER_PREFIX}{issue}")

        return critical

    def _identify_optimization_opportunities(
        self, technical: List[str], nutrition: List[str], business: List[str]
    ) -> List[str]:
        """Идентифицирует возможности оптимизации."""
        opportunities = []

        # Технические возможности
        if any("кэш" in issue.lower() or "cache" in issue.lower() for issue in technical):
            opportunities.append("Добавить кэширование для повышения производительности")

        if any("async" in issue.lower() for issue in technical):
            opportunities.append("Оптимизировать асинхронные операции")

        # Возможности питания
        if any("аллерген" in issue.lower() or "allergen" in issue.lower() for issue in nutrition):
            opportunities.append("Улучшить систему проверки аллергенов")

        if any("bmi" in issue.lower() for issue in nutrition):
            opportunities.append("Добавить расширенную аналитику BMI")

        # Бизнес-возможности
        if any("цена" in issue.lower() or "price" in issue.lower() for issue in business):
            opportunities.append("Оптимизировать стратегию ценообразования")

        if any("клиент" in issue.lower() or "customer" in issue.lower() for issue in business):
            opportunities.append("Улучшить процесс привлечения клиентов")

        return opportunities

    def _assess_revenue_impact(
        self, technical: List[str], nutrition: List[str], business: List[str]
    ) -> str:
        """Оценивает влияние на доходы."""
        revenue_issues = 0

        # Технические проблемы, влияющие на доходы
        revenue_issues += sum("производительность" in issue.lower() for issue in technical)

        # Проблемы питания, влияющие на доходы
        revenue_issues += sum("безопасность" in issue.lower() for issue in nutrition)

        # Бизнес-проблемы, влияющие на доходы
        revenue_issues += sum(
            "доход" in issue.lower() or "revenue" in issue.lower() for issue in business
        )

        if revenue_issues == 0:
            return "Нет влияния на доходы"
        elif revenue_issues <= self.MINIMAL_IMPACT_THRESHOLD:
            return "Минимальное влияние на доходы"
        elif revenue_issues <= self.MEDIUM_IMPACT_THRESHOLD:
            return "Среднее влияние на доходы"
        else:
            return "Критическое влияние на доходы"

    def _assess_cost_impact(
        self,
        technical: List[str],
        _nutrition: List[str],  # noqa: ARG002
        business: List[str],
    ) -> str:
        """Оценивает влияние на затраты."""
        cost_issues = 0

        # Технические проблемы, влияющие на затраты
        cost_issues += sum("неэффектив" in issue.lower() for issue in technical)

        # Бизнес-проблемы, влияющие на затраты
        cost_issues += sum(
            "затрат" in issue.lower() or "cost" in issue.lower() for issue in business
        )

        if cost_issues == 0:
            return "Нет влияния на затраты"
        elif cost_issues <= self.MINIMAL_IMPACT_THRESHOLD:
            return "Минимальное влияние на затраты"
        elif cost_issues <= self.MEDIUM_IMPACT_THRESHOLD:
            return "Среднее влияние на затраты"
        else:
            return "Критическое влияние на затраты"

    def _assess_customer_impact(
        self, technical: List[str], nutrition: List[str], business: List[str]
    ) -> str:
        """Оценивает влияние на клиентов."""
        customer_issues = 0

        # Технические проблемы, влияющие на клиентов
        customer_issues += sum("пользователь" in issue.lower() for issue in technical)

        # Проблемы питания, влияющие на клиентов
        customer_issues += sum("здоровье" in issue.lower() for issue in nutrition)

        # Бизнес-проблемы, влияющие на клиентов
        customer_issues += sum(
            "клиент" in issue.lower() or "customer" in issue.lower() for issue in business
        )

        if customer_issues == 0:
            return "Нет влияния на клиентов"
        elif customer_issues <= self.MINIMAL_IMPACT_THRESHOLD:
            return "Минимальное влияние на клиентов"
        elif customer_issues <= self.MEDIUM_IMPACT_THRESHOLD:
            return "Среднее влияние на клиентов"
        else:
            return "Критическое влияние на клиентов"

    def _assess_health_impact(self, nutrition_issues: List[str]) -> str:
        """Оценивает влияние на здоровье."""
        health_issues = sum(
            "опасно" in issue.lower() or "dangerous" in issue.lower() for issue in nutrition_issues
        )

        if health_issues == 0:
            return "Нет влияния на здоровье"
        elif health_issues <= self.MINIMAL_IMPACT_THRESHOLD:
            return "Минимальное влияние на здоровье"
        elif health_issues <= self.MEDIUM_IMPACT_THRESHOLD:
            return "Среднее влияние на здоровье"
        else:
            return "Критическое влияние на здоровье"

    def _calculate_risk_level(self, critical_issues: List[str], overall_score: float) -> str:
        """Вычисляет уровень риска."""
        if (
            len(critical_issues) >= self.CRITICAL_ISSUE_COUNT_THRESHOLD
            or overall_score < self.CRITICAL_SCORE_THRESHOLD
        ):
            return "critical"
        elif (
            len(critical_issues) >= self.HIGH_ISSUE_COUNT_THRESHOLD
            or overall_score < self.HIGH_SCORE_THRESHOLD
        ):
            return "high"
        elif (
            len(critical_issues) >= self.MEDIUM_ISSUE_COUNT_THRESHOLD
            or overall_score < self.MEDIUM_SCORE_THRESHOLD
        ):
            return "medium"
        else:
            return "low"

    def _calculate_priority(
        self, critical_issues: List[str], revenue_impact: str, health_impact: str
    ) -> str:
        """Вычисляет приоритет."""
        if (
            len(critical_issues) >= self.URGENT_PRIORITY_ISSUE_COUNT
            or "критическое" in health_impact.lower()
        ):
            return "urgent"
        elif (
            len(critical_issues) >= self.HIGH_PRIORITY_ISSUE_COUNT
            or "критическое" in revenue_impact.lower()
        ):
            return "high"
        elif "среднее" in revenue_impact.lower() or "среднее" in health_impact.lower():
            return "medium"
        else:
            return "low"

    def get_comprehensive_diagnosis(self) -> Dict[str, Any]:
        """Получает комплексный диагноз системы."""
        if not self.comprehensive_results:
            return {"status": "no_data"}

        # Общая статистика
        total_tests = len(self.comprehensive_results)
        successful_tests = sum(r.success for r in self.comprehensive_results)

        # Средние баллы
        avg_technical = sum(r.technical_score for r in self.comprehensive_results) / total_tests
        avg_nutrition = sum(r.nutrition_score for r in self.comprehensive_results) / total_tests
        avg_business = sum(r.business_score for r in self.comprehensive_results) / total_tests
        avg_overall = sum(r.overall_score for r in self.comprehensive_results) / total_tests

        # Анализ рисков
        risk_distribution: Dict[str, int] = {}
        for result in self.comprehensive_results:
            risk = result.risk_level
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1

        # Критические тесты
        critical_tests = [
            r.test_name for r in self.comprehensive_results if r.risk_level == "critical"
        ]

        # Возможности оптимизации
        all_opportunities = []
        for result in self.comprehensive_results:
            all_opportunities.extend(result.optimization_opportunities)

        # Рекомендации по экономии
        cost_savings = self.business_analyzer.generate_cost_savings_recommendations()

        # Рекомендации по росту доходов
        revenue_optimization = (
            self.business_analyzer.generate_revenue_optimization_recommendations()
        )

        return {
            "status": "analyzed",
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "average_scores": {
                "technical": avg_technical,
                "nutrition": avg_nutrition,
                "business": avg_business,
                "overall": avg_overall,
            },
            "risk_distribution": risk_distribution,
            "critical_tests": critical_tests,
            "optimization_opportunities": list(set(all_opportunities)),
            "cost_savings_recommendations": cost_savings,
            "revenue_optimization_recommendations": revenue_optimization,
            "system_health": self._calculate_system_health(avg_overall, risk_distribution),
        }

    def _calculate_system_health(
        self, overall_score: float, risk_distribution: Dict[str, int]
    ) -> str:
        """Вычисляет общее здоровье системы."""
        critical_count = risk_distribution.get("critical", 0)
        high_count = risk_distribution.get("high", 0)

        if (
            overall_score >= self.EXCELLENT_SCORE_THRESHOLD
            and critical_count == 0
            and high_count <= self.EXCELLENT_HIGH_RISK_COUNT_THRESHOLD
        ):
            return "excellent"
        elif (
            overall_score >= self.GOOD_SCORE_THRESHOLD
            and critical_count == 0
            and high_count <= self.GOOD_HIGH_RISK_COUNT_THRESHOLD
        ):
            return "good"
        elif (
            overall_score >= self.FAIR_SCORE_THRESHOLD
            and critical_count <= self.FAIR_CRITICAL_RISK_COUNT_THRESHOLD
        ):
            return "fair"
        else:
            return "poor"

    def generate_action_plan(self) -> Dict[str, List[str]]:
        """Генерирует план действий на основе анализа."""
        diagnosis = self.get_comprehensive_diagnosis()

        # Handle no_data case to prevent KeyError
        if diagnosis.get("status") == "no_data":
            return {
                "immediate_actions": [],
                "short_term_actions": [],
                "long_term_actions": [],
                "cost_optimization": [],
                "revenue_growth": [],
            }

        action_plan: Dict[str, List[str]] = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_actions": [],
            "cost_optimization": [],
            "revenue_growth": [],
        }

        # Немедленные действия для критических проблем
        if diagnosis["critical_tests"]:
            action_plan["immediate_actions"].extend(
                [
                    f"Исправить критические тесты: {', '.join(diagnosis['critical_tests'][: self.ACTION_PLAN_CRITICAL_TESTS_DISPLAY_LIMIT])}",
                    "Провести экстренный аудит безопасности",
                    "Временно отключить проблемные функции",
                ]
            )

        # Краткосрочные действия
        if diagnosis["average_scores"]["overall"] < self.SUCCESS_SCORE_THRESHOLD:
            action_plan["short_term_actions"].extend(
                [
                    "Повысить общий балл системы до 80%+",
                    "Реализовать топ-3 возможности оптимизации",
                    "Улучшить покрытие тестами до 97%",
                ]
            )

        # Долгосрочные действия
        action_plan["long_term_actions"].extend(
            [
                "Внедрить комплексную систему мониторинга",
                "Разработать стратегию масштабирования",
                "Создать культуру качества и безопасности",
            ]
        )

        # Оптимизация затрат
        action_plan["cost_optimization"] = diagnosis["cost_savings_recommendations"][
            : self.ACTION_PLAN_RECOMMENDATION_LIMIT
        ]

        # Рост доходов
        action_plan["revenue_growth"] = diagnosis["revenue_optimization_recommendations"][
            : self.ACTION_PLAN_RECOMMENDATION_LIMIT
        ]

        return action_plan
