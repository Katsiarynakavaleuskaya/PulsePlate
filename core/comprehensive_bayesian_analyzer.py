#!/usr/bin/env python3
"""
Комплексный байесовский анализатор, объединяющий все аспекты системы PulsePlate:
- Технические аспекты
- Питание и здоровье
- Бизнес-логика и монетизация
- Создание базы клиентов
- Экономия средств
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from core.bayesian_test_analyzer import BayesianTestAnalyzer
from core.nutrition_bayesian_analyzer import NutritionBayesianAnalyzer
from core.business_bayesian_analyzer import BusinessBayesianAnalyzer


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

    def __init__(self) -> None:
        self.technical_analyzer = BayesianTestAnalyzer()
        self.nutrition_analyzer = NutritionBayesianAnalyzer()
        self.business_analyzer = BusinessBayesianAnalyzer()
        self.comprehensive_results: List[ComprehensiveTestResult] = []
        self.system_vision = self._load_system_vision()
        # Configurable keywords for critical nutrition issues detection
        # RU: Ключевые слова для обнаружения критических проблем питания
        self._critical_nutrition_keywords = [
            "калорий",
            "calorie",
            "bmi",
            "dangerous",
            "опасно",
        ]
        # Standardized business marker prefix for critical business issues
        # RU: Стандартизированный префикс маркера для критических бизнес-проблем
        self._business_marker_prefix = "business:"

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
        keywords_lower = [keyword.lower() for keyword in self._critical_nutrition_keywords]

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
        normalized_prefix = self._business_marker_prefix.lower()

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
        nutrition_issues = [r.error_message for r in nutrition_results if not r.success]
        nutrition_score = self.nutrition_analyzer.get_safety_score()

        # Бизнес-анализ
        business_results = self.business_analyzer.analyze_business_logic(test_code, test_name)
        business_issues = [r.error_message for r in business_results if not r.success]
        business_score = self._calculate_business_score(business_issues)

        # Общий балл
        # Health First policy: nutrition issues should appropriately reduce overall score
        # Use a minimal floor (0.3) to prevent division by zero, but allow nutrition failures
        # to significantly impact the overall score
        nutrition_effective = max(nutrition_score, 0.3)
        overall_score = (technical_score + nutrition_effective + business_score) / 3

        # Критические проблемы
        critical_issues = self._identify_critical_issues(
            technical_issues, nutrition_issues, business_issues
        )

        # Health First policy: critical nutrition issues force failure
        # Check for critical nutrition issues (very low calories, dangerous BMI, etc.)
        # RU: Проверка критических проблем питания через централизованный метод
        has_critical_nutrition_issues = self._has_critical_nutrition_issues(critical_issues)

        # Check for critical business issues (revenue, customer impact)
        # RU: Проверка критических бизнес-проблем через централизованный метод
        has_critical_business_issues = self._has_critical_business_issues(critical_issues)

        # Apply heavy penalty for critical nutrition issues
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

        # Determine success: must pass threshold AND no critical issues (nutrition or business)
        # EN: overall_score is capped to 0.0 when critical nutrition issues exist (see penalty above),
        # so the 0.8 threshold would suffice; we still keep explicit
        # "not has_critical_nutrition_issues" and "not has_critical_business_issues"
        # for clarity and defensive programming.
        # RU: при наличии критических проблем питания overall_score принудительно устанавливается в 0.0,
        # поэтому одного порога 0.8 было бы достаточно; явные проверки
        # "not has_critical_nutrition_issues" и "not has_critical_business_issues"
        # оставлены ради ясности и защитного программирования.
        success = (
            overall_score >= 0.8
            and not has_critical_nutrition_issues
            and not has_critical_business_issues
        )

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

        # Штрафы за разные типы проблем
        penalty = 0.0
        for issue in issues:
            if "AsyncMock" in issue or "исключение" in issue:
                penalty += 0.3  # Критические проблемы
            elif "типизация" in issue or "await" in issue:
                penalty += 0.2  # Важные проблемы
            else:
                penalty += 0.1  # Обычные проблемы

        return max(0.0, 1.0 - penalty)

    def _calculate_business_score(self, issues: List[str]) -> float:
        """Вычисляет бизнес-балл."""
        if not issues:
            return 1.0

        penalty = 0.0
        for issue in issues:
            if "доход" in issue.lower() or "revenue" in issue.lower():
                penalty += 0.4  # Критические бизнес-проблемы
            elif "клиент" in issue.lower() or "customer" in issue.lower():
                penalty += 0.3  # Важные проблемы
            else:
                penalty += 0.2  # Обычные проблемы

        return max(0.0, 1.0 - penalty)

    def _identify_critical_issues(
        self, technical: List[str], nutrition: List[str], business: List[str]
    ) -> List[str]:
        """Идентифицирует критические проблемы."""
        critical = []

        # Критические технические проблемы
        for issue in technical:
            if any(
                keyword in issue.lower() for keyword in ["asyncmock", "исключение", "безопасность"]
            ):
                critical.append(f"TECH: {issue}")

        # Критические проблемы питания
        for issue in nutrition:
            if any(keyword in issue.lower() for keyword in ["опасно", "dangerous", "критично"]):
                critical.append(f"HEALTH: {issue}")

        # Критические бизнес-проблемы
        for issue in business:
            if any(
                keyword in issue.lower() for keyword in ["доход", "revenue", "клиент", "customer"]
            ):
                critical.append(f"BUSINESS: {issue}")

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
        elif revenue_issues <= 2:
            return "Минимальное влияние на доходы"
        elif revenue_issues <= 5:
            return "Среднее влияние на доходы"
        else:
            return "Критическое влияние на доходы"

    def _assess_cost_impact(
        self, technical: List[str], nutrition: List[str], business: List[str]
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
        elif cost_issues <= 2:
            return "Минимальное влияние на затраты"
        elif cost_issues <= 5:
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
        elif customer_issues <= 2:
            return "Минимальное влияние на клиентов"
        elif customer_issues <= 5:
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
        elif health_issues <= 2:
            return "Минимальное влияние на здоровье"
        elif health_issues <= 5:
            return "Среднее влияние на здоровье"
        else:
            return "Критическое влияние на здоровье"

    def _calculate_risk_level(self, critical_issues: List[str], overall_score: float) -> str:
        """Вычисляет уровень риска."""
        if len(critical_issues) >= 5 or overall_score < 0.3:
            return "critical"
        elif len(critical_issues) >= 3 or overall_score < 0.5:
            return "high"
        elif len(critical_issues) >= 1 or overall_score < 0.7:
            return "medium"
        else:
            return "low"

    def _calculate_priority(
        self, critical_issues: List[str], revenue_impact: str, health_impact: str
    ) -> str:
        """Вычисляет приоритет."""
        if len(critical_issues) >= 3 or "критическое" in health_impact.lower():
            return "urgent"
        elif len(critical_issues) >= 1 or "критическое" in revenue_impact.lower():
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

        if overall_score >= 0.9 and critical_count == 0 and high_count <= 1:
            return "excellent"
        elif overall_score >= 0.8 and critical_count == 0 and high_count <= 3:
            return "good"
        elif overall_score >= 0.6 and critical_count <= 1:
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
                    f"Исправить критические тесты: {', '.join(diagnosis['critical_tests'][:3])}",
                    "Провести экстренный аудит безопасности",
                    "Временно отключить проблемные функции",
                ]
            )

        # Краткосрочные действия
        if diagnosis["average_scores"]["overall"] < 0.8:
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
        action_plan["cost_optimization"] = diagnosis["cost_savings_recommendations"][:5]

        # Рост доходов
        action_plan["revenue_growth"] = diagnosis["revenue_optimization_recommendations"][:5]

        return action_plan
