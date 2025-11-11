#!/usr/bin/env python3
"""
Integrated Bayesian analyzer combining technical and business aspects.
Analyzes tests from the perspectives of code, nutrition, safety, and system philosophy.
"""

import ast
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Set

from core.bayesian_technical_utils import analyze_technical_aspects_common
from core.bayesian_test_analyzer import BayesianTestAnalyzer
from core.nutrition_bayesian_analyzer import NutritionBayesianAnalyzer, NutritionTestResult


class NormalizedIssueType(Enum):
    """Language-agnostic normalized issue types for risk assessment."""

    INJECTION = "injection"
    PASSWORD_LEAK = "passwordLeak"  # nosec B105 - enum value, not hardcoded password
    DANGEROUS_INSTRUCTION = "dangerousInstruction"
    EXCEPTION_HANDLING = "exceptionHandling"
    ASYNC_ERROR = "asyncError"
    HEALTH_VIOLATION = "healthViolation"
    SAFETY_VIOLATION = "safetyViolation"


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

    # Risk level calculation thresholds
    # RU: Пороги для расчета уровня риска
    # EN: Thresholds for risk level calculation
    RISK_THRESHOLD_CRITICAL = 3  # Minimum critical issue types for critical risk level
    RISK_THRESHOLD_HIGH = 2  # Minimum critical issue types for high risk level
    RISK_THRESHOLD_MEDIUM = 1  # Minimum critical issue types for medium risk level

    # Recommendation trigger thresholds
    # RU: Пороги для генерации рекомендаций
    # EN: Thresholds for generating recommendations based on issue frequency
    TECHNICAL_THRESHOLD = (
        0.5  # Minimum fraction of tests with technical issues to trigger recommendation
    )
    NUTRITION_THRESHOLD = (
        0.3  # Minimum fraction of tests with nutrition issues to trigger recommendation
    )
    SAFETY_THRESHOLD = 0.2  # Minimum fraction of tests with safety issues to trigger recommendation
    PHILOSOPHY_THRESHOLD = (
        0.4  # Minimum fraction of tests with philosophy violations to trigger recommendation
    )

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
        nutrition_results: List[NutritionTestResult] = (
            self.nutrition_analyzer.analyze_nutrition_safety(test_code, test_name)
        )
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
            success=not technical_issues
            and not nutrition_issues
            and not safety_issues
            and not philosophy_violations,
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

    def _is_in_test_or_mock_context(self, code: str) -> bool:
        """Check if code is in a test or mock context."""
        test_markers = [
            "@pytest.fixture",
            "def test_",
            "class Test",
            "Mock(",
            "unittest.mock",
            "@mock",
        ]
        code_lower = code.lower()
        return any(marker.lower() in code_lower for marker in test_markers)

    def _check_unsafe_file_opens(self, code: str) -> bool:
        """
        Check for unsafe file opens using AST analysis.

        Returns True if unsafe open() calls are found (not in with statement
        and not wrapped by contextlib.closing).
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # If code cannot be parsed, fall back to safe assumption
            return False

        class UnsafeOpenChecker(ast.NodeVisitor):
            """Visitor to check for unsafe open() calls."""

            def __init__(self) -> None:
                self.unsafe_opens: List[ast.Call] = []
                self.parent_stack: List[ast.AST] = []
                self.in_with_context = False

            def visit(self, node: ast.AST) -> None:
                """Override visit to track parent nodes."""
                self.parent_stack.append(node)
                method = f"visit_{node.__class__.__name__}"
                visitor = getattr(self, method, self.generic_visit)
                visitor(node)
                self.parent_stack.pop()

            def visit_With(self, node: ast.With) -> None:
                """Track With nodes and their contents."""
                # Mark that we're entering a with context
                # All code inside the with body is considered safe
                old_in_with = self.in_with_context
                self.in_with_context = True
                self.generic_visit(node)
                self.in_with_context = old_in_with

            def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
                """Track AsyncWith nodes and their contents."""
                # Mark that we're entering an async with context
                # All code inside the async with body is considered safe
                old_in_with = self.in_with_context
                self.in_with_context = True
                self.generic_visit(node)
                self.in_with_context = old_in_with

            def visit_Call(self, node: ast.Call) -> None:
                """Check if this is an unsafe open() call."""
                # Check if this is a call to open()
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "open"
                    and not self.in_with_context
                    and not self._is_context_expression(node)
                    and not self._is_wrapped_by_closing(node)
                ):
                    self.unsafe_opens.append(node)
                self.generic_visit(node)

            def _is_context_expression(self, node: ast.Call) -> bool:
                """Check if open() is used directly as a context expression."""
                # Check parent nodes in the stack
                for parent in self.parent_stack:
                    if isinstance(parent, (ast.With, ast.AsyncWith)):
                        # Check if this node is the context_expr
                        for item in parent.items:
                            if item.context_expr is node:
                                return True
                return False

            def _is_closing_call(self, node: ast.Call) -> bool:
                """Check if this is a call to contextlib.closing."""
                if isinstance(node.func, ast.Attribute):
                    return (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "contextlib"
                        and node.func.attr == "closing"
                    )
                if isinstance(node.func, ast.Name) and node.func.id == "closing":
                    # Could be from "from contextlib import closing"
                    return True
                return False

            def _is_wrapped_by_closing(self, node: ast.Call) -> bool:
                """Check if open() is wrapped by contextlib.closing()."""
                # Check parent nodes in the stack
                for parent in self.parent_stack:
                    # Check if node is an argument to a closing() call
                    if (
                        isinstance(parent, ast.Call)
                        and self._is_closing_call(parent)
                        and any(arg is node for arg in parent.args)
                    ):
                        return True
                return False

        checker = UnsafeOpenChecker()
        checker.visit(tree)
        return bool(checker.unsafe_opens)

    def _check_sensitive_data_logging(self, code: str) -> bool:
        """
        Check if sensitive data is being logged using AST parsing.

        Parses code to find logger method calls (logger.info, logger.debug, etc.)
        and checks if their arguments contain sensitive identifiers or strings.

        Args:
            code: Source code to analyze

        Returns:
            True if sensitive data appears to be logged, False otherwise
        """
        # Sensitive keywords to detect
        sensitive_keywords = ["password", "token", "key", "secret", "api_key", "auth"]

        try:
            tree = ast.parse(code)
        except (SyntaxError, ValueError):
            # Fallback to simple regex if AST parsing fails
            if "logger" in code.lower():
                code_lower = code.lower()
                return any(keyword in code_lower for keyword in sensitive_keywords)
            return False

        class SensitiveLoggingChecker(ast.NodeVisitor):
            """Visitor to check for sensitive data in logger calls."""

            def __init__(self) -> None:
                self.found_sensitive_logging = False
                self.sensitive_keywords = sensitive_keywords

            def visit_Call(self, node: ast.Call) -> None:
                """Check if this is a logger call with sensitive data."""
                # Check if this is a logger method call (logger.info, logger.debug, etc.)
                if isinstance(node.func, ast.Attribute):
                    # Check if target is a logger-like variable
                    if isinstance(node.func.value, ast.Name):
                        logger_name = node.func.value.id.lower()
                        if logger_name in ["logger", "log"]:
                            # Check method name (info, debug, error, warning, etc.)
                            method_name = node.func.attr.lower()
                            if method_name in [
                                "info",
                                "debug",
                                "error",
                                "warning",
                                "critical",
                                "exception",
                            ]:
                                # Check arguments for sensitive data
                                for arg in node.args:
                                    if self._contains_sensitive_data(arg):
                                        self.found_sensitive_logging = True
                                        return

                self.generic_visit(node)

            def _contains_sensitive_data(self, node: ast.AST) -> bool:
                """Check if AST node contains sensitive data."""
                # Check for Name nodes (variable names)
                if isinstance(node, ast.Name):
                    name_lower = node.id.lower()
                    return any(keyword in name_lower for keyword in self.sensitive_keywords)

                # Check for Constant nodes (string literals)
                if isinstance(node, ast.Constant):
                    if isinstance(node.value, str):
                        value_lower = node.value.lower()
                        return any(keyword in value_lower for keyword in self.sensitive_keywords)

                # Check for FormattedValue nodes (f-string parts)
                if isinstance(node, ast.FormattedValue):
                    if isinstance(node.value, ast.Name):
                        name_lower = node.value.id.lower()
                        return any(keyword in name_lower for keyword in self.sensitive_keywords)

                # Check for JoinedStr nodes (f-strings)
                if isinstance(node, ast.JoinedStr):
                    for part in node.values:
                        if self._contains_sensitive_data(part):
                            return True

                return False

        checker = SensitiveLoggingChecker()
        checker.visit(tree)
        return checker.found_sensitive_logging

    def _analyze_safety_aspects(self, code: str, test_name: str) -> List[str]:
        """Analyze safety aspects."""
        issues = []

        # Hardcoded password check (context-aware: skip test fixtures and mocks)
        password_match = re.search(r'password\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE)
        if password_match and not self._is_in_test_or_mock_context(code):
            issues.append("Hardcoded password in code")

        # SQL injection check (comprehensive detection of unsafe SQL construction)
        # Patterns cover: string concatenation, f-strings, .format(), multiline queries,
        # and various SQL verbs (SELECT, INSERT, UPDATE, DELETE)
        sql_concat_patterns = [
            # String concatenation with + operator and SQL keywords
            r'["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\'].*\+',
            r'\+.*["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\']',
            # f-strings with SQL keywords
            r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{[^}]*\}',
            r'f["\'].*\{[^}]*\}.*(?:SELECT|INSERT|UPDATE|DELETE)',
            # .format() calls with SQL keywords
            r'["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\']\.format\(',
            # Multiline queries with concatenation
            r'["\'].*(?:SELECT|INSERT|UPDATE|DELETE)[\s\S]*?["\'].*\+',
            r'\+.*["\'].*(?:SELECT|INSERT|UPDATE|DELETE)[\s\S]*?["\']',
            # Triple-quoted strings with SQL and concatenation
            r'["\']{3}.*(?:SELECT|INSERT|UPDATE|DELETE)[\s\S]*?["\']{3}.*\+',
            r'\+.*["\']{3}.*(?:SELECT|INSERT|UPDATE|DELETE)[\s\S]*?["\']{3}',
        ]
        if any(
            re.search(pattern, code, re.IGNORECASE | re.DOTALL) for pattern in sql_concat_patterns
        ):
            issues.append("Potential SQL injection vulnerability")

        # Unsafe file handling - AST-based check for precise detection
        if self._check_unsafe_file_opens(code):
            issues.append("Unsafe file open without context manager")

        # Sensitive data logging - AST-based detection to avoid false positives
        if self._check_sensitive_data_logging(code):
            issues.append("Logging sensitive data")

        return issues

    def _analyze_philosophy_compliance(self, code: str, test_name: str) -> List[str]:
        """Analyze compliance with system philosophy."""
        violations = []

        # Health orientation check
        if "health" in test_name.lower() and all(
            metric not in code.lower() for metric in ["bmi", "calorie"]
        ):
            violations.append("Health test does not verify key metrics")

        # Scientific accuracy check
        if "nutrition" in test_name.lower() and all(
            metric not in code.lower() for metric in ["protein", "fat", "carbs", "vitamin"]
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

    def _normalize_issue_type(self, issue: str) -> Set[NormalizedIssueType]:
        """
        Normalize issue string to language-agnostic issue types.

        Maps issue descriptions to normalized types regardless of language.
        Returns a set of normalized types found in the issue.
        """
        issue_lower = issue.lower()
        normalized_types: Set[NormalizedIssueType] = set()

        # Injection detection (SQL injection, code injection, etc.)
        injection_keywords = [
            "injection",
            "инъекция",
            "sql injection",
            "sql инъекция",
            "code injection",
            "инъекция кода",
            "vulnerability",
            "уязвимость",
        ]
        if any(keyword in issue_lower for keyword in injection_keywords):
            normalized_types.add(NormalizedIssueType.INJECTION)

        # Password leak detection
        password_keywords = [
            "password",
            "парол",
            "hardcoded password",
            "хардкод парол",
            "password leak",
            "утечка парол",
            "sensitive",
            "чувствительн",
        ]
        if any(keyword in issue_lower for keyword in password_keywords):
            normalized_types.add(NormalizedIssueType.PASSWORD_LEAK)

        # Dangerous instruction detection
        dangerous_keywords = [
            "dangerous",
            "опасно",
            "unsafe",
            "небезопасн",
            "risk",
            "риск",
            "critical",
            "критичн",
            "severe",
            "серьезн",
        ]
        if any(keyword in issue_lower for keyword in dangerous_keywords):
            normalized_types.add(NormalizedIssueType.DANGEROUS_INSTRUCTION)

        # Exception handling issues
        exception_keywords = [
            "exception",
            "исключен",
            "error handling",
            "обработка ошибок",
            "asyncmock",
            "mock error",
            "ошибка мок",
        ]
        if any(keyword in issue_lower for keyword in exception_keywords):
            normalized_types.add(NormalizedIssueType.EXCEPTION_HANDLING)

        # Async error detection
        async_keywords = ["asyncmock", "async error", "асинхронн ошибк", "await", "async"]
        if any(keyword in issue_lower for keyword in async_keywords):
            normalized_types.add(NormalizedIssueType.ASYNC_ERROR)

        # Health violation detection
        health_keywords = ["health", "здоровье", "nutrition", "питание", "bmi", "calorie", "калори"]
        if any(keyword in issue_lower for keyword in health_keywords):
            normalized_types.add(NormalizedIssueType.HEALTH_VIOLATION)

        # Safety violation detection
        safety_keywords = ["safety", "безопас", "security", "безопасност", "privacy", "приватност"]
        if any(keyword in issue_lower for keyword in safety_keywords):
            normalized_types.add(NormalizedIssueType.SAFETY_VIOLATION)

        return normalized_types

    def _calculate_risk_level(
        self, technical: List[str], nutrition: List[str], safety: List[str], philosophy: List[str]
    ) -> str:
        """Calculate overall risk level using language-agnostic normalized issue types."""
        critical_issue_types: Set[NormalizedIssueType] = set()

        # Normalize all issues and collect critical types
        all_issues = technical + nutrition + safety + philosophy
        for issue in all_issues:
            normalized = self._normalize_issue_type(issue)
            # Critical types: injection, password leak, dangerous instruction
            critical_types = {
                NormalizedIssueType.INJECTION,
                NormalizedIssueType.PASSWORD_LEAK,
                NormalizedIssueType.DANGEROUS_INSTRUCTION,
            }
            critical_issue_types.update(normalized & critical_types)

        # Count unique critical issue types
        critical_count = len(critical_issue_types)

        if critical_count >= self.RISK_THRESHOLD_CRITICAL:
            return "critical"
        elif critical_count >= self.RISK_THRESHOLD_HIGH:
            return "high"
        elif critical_count >= self.RISK_THRESHOLD_MEDIUM:
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
        successful_tests = sum(r.success for r in self.integrated_results)

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
        if len(all_technical) > len(self.integrated_results) * self.TECHNICAL_THRESHOLD:
            recommendations.append("Провести технический рефакторинг тестов")

        if len(all_nutrition) > len(self.integrated_results) * self.NUTRITION_THRESHOLD:
            recommendations.append("Усилить проверки безопасности питания")

        if len(all_safety) > len(self.integrated_results) * self.SAFETY_THRESHOLD:
            recommendations.append("Провести аудит безопасности данных")

        if len(all_philosophy) > len(self.integrated_results) * self.PHILOSOPHY_THRESHOLD:
            recommendations.append("Обновить тесты в соответствии с философией системы")

        return recommendations
