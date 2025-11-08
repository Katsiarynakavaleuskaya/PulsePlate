#!/usr/bin/env python3
"""
Integrated Bayesian analyzer combining technical and business aspects.
Analyzes tests from the perspectives of code, nutrition, safety, and system philosophy.
"""

from typing import Dict, List, Any
import re
from dataclasses import dataclass
from enum import Enum

from core.bayesian_test_analyzer import BayesianTestAnalyzer
from core.nutrition_bayesian_analyzer import (
    NutritionBayesianAnalyzer,
)

from core.bayesian_technical_utils import analyze_technical_aspects_common


class SystemPhilosophy(Enum):
    """PulsePlate system philosophy."""

    HEALTH_FIRST = "health_first"
    USER_SAFETY = "user_safety"
    DATA_PRIVACY = "data_privacy"
    SCIENTIFIC_ACCURACY = "scientific_accuracy"
    ACCESSIBILITY = "accessibility"
    SUSTAINABILITY = "sustainability"
    PERSONALIZATION = "personalization"
    TRANSPARENCY = "transparency"


@dataclass
class IntegratedTestResult:
    """Integrated result of a test analysis."""

    test_name: str
    success: bool
    technical_issues: List[str]
    nutrition_issues: List[str]
    safety_issues: List[str]
    philosophy_violations: List[str]
    business_impact: str
    overall_risk_level: str  # low, medium, high, critical
    recommendations: List[str]


class IntegratedBayesianAnalyzer:
    """Integrated Bayesian analyzer."""

    def __init__(self) -> None:
        self.technical_analyzer = BayesianTestAnalyzer()
        self.nutrition_analyzer = NutritionBayesianAnalyzer()
        self.integrated_results: List[IntegratedTestResult] = []
        self.system_philosophy = self._load_system_philosophy()

    def _load_system_philosophy(self) -> Dict[str, Any]:
        """Load PulsePlate system philosophy."""
        return {
            "core_principles": [
                "Здоровье пользователя превыше всего",
                "Научная точность в расчетах питания",
                "Защита конфиденциальности данных",
                "Доступность для всех пользователей",
                "Устойчивое развитие и экология",
                "Персонализация рекомендаций",
                "Прозрачность алгоритмов",
            ],
            "safety_requirements": [
                "Проверка аллергенов",
                "Медицинские ограничения",
                "Безопасные пределы BMI",
                "Разумные калории",
                "Защита персональных данных",
            ],
            "quality_standards": [
                "97% покрытие тестами",
                "Научная валидация",
                "Медицинская экспертиза",
                "Пользовательское тестирование",
            ],
        }

    def analyze_test_comprehensively(
        self, test_code: str, test_name: str, file_path: str
    ) -> IntegratedTestResult:
        """Comprehensive analysis of a single test."""

        # Technical analysis
        technical_issues = self._analyze_technical_aspects(test_code, test_name)

        # Nutrition analysis
        nutrition_results = self.nutrition_analyzer.analyze_nutrition_safety(test_code, test_name)
        nutrition_issues = [r.error_message for r in nutrition_results if not r.success]

        # Safety analysis
        safety_issues = self._analyze_safety_aspects(test_code, test_name)

        # System philosophy analysis
        philosophy_violations = self._analyze_philosophy_compliance(test_code, test_name)

        # Business impact assessment
        business_impact = self._assess_business_impact(
            technical_issues, nutrition_issues, safety_issues, philosophy_violations
        )

        # Overall risk level
        risk_level = self._calculate_risk_level(
            technical_issues, nutrition_issues, safety_issues, philosophy_violations
        )

        # Generate recommendations
        recommendations = self._generate_integrated_recommendations(
            technical_issues, nutrition_issues, safety_issues, philosophy_violations
        )

        result = IntegratedTestResult(
            test_name=test_name,
            success=len(technical_issues) == 0
            and len(nutrition_issues) == 0
            and len(safety_issues) == 0,
            technical_issues=technical_issues,
            nutrition_issues=nutrition_issues,
            safety_issues=safety_issues,
            philosophy_violations=philosophy_violations,
            business_impact=business_impact,
            overall_risk_level=risk_level,
            recommendations=recommendations,
        )

        self.integrated_results.append(result)
        return result

    def _analyze_technical_aspects(self, code: str, test_name: str) -> List[str]:
        """Analyze technical aspects of the test."""
        return analyze_technical_aspects_common(code, test_name)

    def _analyze_safety_aspects(self, code: str, test_name: str) -> List[str]:
        """Analyze safety aspects."""
        issues = []

        # Hardcoded password check
        if re.search(r'password\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            issues.append("Hardcoded password in code")

        # SQL injection check (string concatenation in SQL queries)
        # Matches string concat with SELECT statements: "SELECT..." + var
        if re.search(r'["\'].*SELECT.*["\'].*\+', code, re.IGNORECASE | re.DOTALL):
            issues.append("Potential SQL injection")

        # Unsafe file handling
        if "open(" in code and "with" not in code:
            issues.append("Unsafe file open without context manager")

        # Sensitive data logging
        if "logger" in code and any(
            sensitive in code.lower() for sensitive in ["password", "token", "key"]
        ):
            issues.append("Logging sensitive data")

        return issues

    def _analyze_philosophy_compliance(self, code: str, test_name: str) -> List[str]:
        """Analyze compliance with system philosophy."""
        violations = []

        # Health orientation check
        if (
            "health" in test_name.lower()
            and "bmi" not in code.lower()
            and "calorie" not in code.lower()
        ):
            violations.append("Health test does not verify key metrics")

        # Scientific accuracy check
        if "nutrition" in test_name.lower() and not any(
            metric in code.lower() for metric in ["protein", "fat", "carbs", "vitamin"]
        ):
            violations.append("Nutrition test does not validate macronutrients")

        # Accessibility check
        if (
            "user" in test_name.lower()
            and "error" not in code.lower()
            and "exception" not in code.lower()
        ):
            violations.append("User-related test does not validate error handling")

        # Personalization check
        if (
            "personal" in test_name.lower()
            and "profile" not in code.lower()
            and "preference" not in code.lower()
        ):
            violations.append("Personalization test does not use user profile/preferences")

        return violations

    def _assess_business_impact(
        self, technical: List[str], nutrition: List[str], safety: List[str], philosophy: List[str]
    ) -> str:
        """Assess business impact."""
        total_issues = len(technical) + len(nutrition) + len(safety) + len(philosophy)

        if total_issues == 0:
            return "No business impact"
        elif total_issues <= 2:
            return "Minimal impact on user experience"
        elif total_issues <= 5:
            return "Moderate impact on product quality"
        elif total_issues <= 10:
            return "High impact on reputation and safety"
        else:
            return "Critical impact on business operations"

    def _calculate_risk_level(
        self, technical: List[str], nutrition: List[str], safety: List[str], philosophy: List[str]
    ) -> str:
        """Calculate overall risk level."""
        critical_issues = 0

        # Critical technical issues
        critical_issues += sum(
            1 for issue in technical if "AsyncMock" in issue or "исключение" in issue
        )

        # Critical nutrition issues
        critical_issues += sum(
            1 for issue in nutrition if "опасно" in issue.lower() or "dangerous" in issue.lower()
        )

        # Critical safety issues
        critical_issues += sum(
            1
            for issue in safety
            if "инъекция" in issue.lower()
            or "injection" in issue.lower()
            or "парол" in issue.lower()
            or "password" in issue.lower()
        )

        # Critical philosophy violations
        critical_issues += sum(
            1
            for issue in philosophy
            if "здоровье" in issue.lower()
            or "health" in issue.lower()
            or "безопас" in issue.lower()
            or "safety" in issue.lower()
        )

        if critical_issues >= 3:
            return "critical"
        elif critical_issues >= 2:
            return "high"
        elif critical_issues >= 1:
            return "medium"
        else:
            return "low"

    def _generate_integrated_recommendations(
        self, technical: List[str], nutrition: List[str], safety: List[str], philosophy: List[str]
    ) -> List[str]:
        """Generate integrated recommendations."""
        recommendations = []

        # Technical recommendations
        if technical:
            recommendations.extend(["Fix technical issues: " + "; ".join(technical[:3])])

        # Nutrition recommendations
        if nutrition:
            recommendations.extend(["Improve nutrition safety: " + "; ".join(nutrition[:3])])

        # Safety recommendations
        if safety:
            recommendations.extend(["Strengthen data safety: " + "; ".join(safety[:3])])

        # Philosophy recommendations
        if philosophy:
            recommendations.extend(["Align with system philosophy: " + "; ".join(philosophy[:3])])

        return recommendations

    def get_comprehensive_diagnosis(self) -> Dict[str, Any]:
        """Get comprehensive system diagnosis."""
        if not self.integrated_results:
            return {"status": "no_data"}

        # Category statistics
        total_tests = len(self.integrated_results)
        successful_tests = sum(1 for r in self.integrated_results if r.success)

        # Risk analysis
        risk_distribution: Dict[str, int] = {}
        for result in self.integrated_results:
            risk = result.overall_risk_level
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1

        # Problem area analysis
        problem_areas = {
            "technical": sum(len(r.technical_issues) for r in self.integrated_results),
            "nutrition": sum(len(r.nutrition_issues) for r in self.integrated_results),
            "safety": sum(len(r.safety_issues) for r in self.integrated_results),
            "philosophy": sum(len(r.philosophy_violations) for r in self.integrated_results),
        }

        return {
            "status": "analyzed",
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "risk_distribution": risk_distribution,
            "problem_areas": problem_areas,
            "critical_tests": [
                r.test_name for r in self.integrated_results if r.overall_risk_level == "critical"
            ],
            "recommendations": self._generate_system_recommendations(),
        }

    def _generate_system_recommendations(self) -> List[str]:
        """Генерирует системные рекомендации."""
        recommendations = []

        # Анализируем общие паттерны проблем
        all_technical = []
        all_nutrition = []
        all_safety = []
        all_philosophy = []

        for result in self.integrated_results:
            all_technical.extend(result.technical_issues)
            all_nutrition.extend(result.nutrition_issues)
            all_safety.extend(result.safety_issues)
            all_philosophy.extend(result.philosophy_violations)

        # Рекомендации на основе частых проблем
        if len(all_technical) > len(self.integrated_results) * 0.5:
            recommendations.append("Провести технический рефакторинг тестов")

        if len(all_nutrition) > len(self.integrated_results) * 0.3:
            recommendations.append("Усилить проверки безопасности питания")

        if len(all_safety) > len(self.integrated_results) * 0.2:
            recommendations.append("Провести аудит безопасности данных")

        if len(all_philosophy) > len(self.integrated_results) * 0.4:
            recommendations.append("Обновить тесты в соответствии с философией системы")

        return recommendations
