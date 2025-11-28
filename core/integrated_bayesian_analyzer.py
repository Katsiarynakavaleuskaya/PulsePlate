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
    # Enum member name contains "password" but it is not a secret value (Bandit B105).
    PASSWORD_LEAK = "passwordLeak"  # nosec B105
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
        self, test_code: str, test_name: str, file_path: str | None = None
    ) -> IntegratedTestResult:
        """Comprehensive analysis of a single test.

        Args:
            test_code: Source code of the test under analysis.
            test_name: Test function name.
            file_path: Optional path of the test file (for logging/telemetry).
        """
        # TODO: Use file_path for logging/telemetry in future implementation
        _ = file_path  # Explicitly mark as intentionally unused for now

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
        return analyze_technical_aspects_common(code)

    def _is_in_test_or_mock_context(self, code: str) -> bool:
        """
        Check if code is in a test or mock context using precise AST-based detection.

        Returns True if code contains test-related patterns:
        - Functions starting with "test_"
        - Classes inheriting from unittest.TestCase
        - pytest.fixture or mock decorators
        - Explicit mock module imports/usage

        Falls back to regex if AST parsing fails.
        """
        try:
            tree = ast.parse(code)
        except (SyntaxError, ValueError):
            # Fallback to regex-based detection with word boundaries
            # Note: re module already imported at module level
            regex_patterns = [
                r"^\s*@pytest\.fixture\b",  # pytest fixture decorator
                r"^\s*@mock\.",  # mock decorators
                r"^\s*def\s+test_[A-Za-z0-9_]+\b",  # test function definitions
                r"^\s*class\s+Test[A-Za-z0-9_]+\b",  # test class definitions
                r"\bunittest\.mock\b",  # unittest.mock usage
                r"\bMock\(",  # Mock instantiation
                r"\bMagicMock\(",  # MagicMock instantiation
            ]
            return any(re.search(pattern, code, re.MULTILINE) for pattern in regex_patterns)

        # AST-based detection for precise matching
        for node in ast.walk(tree):
            # Check for test function definitions (def test_*)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                return True

            # Check for classes inheriting from unittest.TestCase
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    # TestCase or unittest.TestCase
                    if isinstance(base, ast.Attribute):
                        if base.attr == "TestCase":
                            return True
                    elif isinstance(base, ast.Name):
                        if base.id == "TestCase":
                            return True

            # Check for pytest.fixture or mock decorators
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        # @pytest.fixture
                        if (
                            isinstance(decorator.value, ast.Name)
                            and decorator.value.id == "pytest"
                            and decorator.attr == "fixture"
                        ):
                            return True
                        # @mock.patch or @mock.*
                        if isinstance(decorator.value, ast.Name) and decorator.value.id == "mock":
                            return True
                    # @fixture (from pytest import fixture) or @patch (from unittest.mock import patch)
                    elif isinstance(decorator, ast.Name):
                        if decorator.id in {"fixture", "pytest_fixture"}:
                            return True
                        # Narrow check: only @patch is a clear test/mock decorator
                        # Note: "mock" alone is too generic (could be any custom decorator)
                        if decorator.id == "patch":
                            return True

            # Check for Mock/MagicMock instantiation
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in {"Mock", "MagicMock", "AsyncMock"}:
                        return True
                # unittest.mock.Mock or mock.Mock
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in {"Mock", "MagicMock", "AsyncMock"}:
                        return True

            # Check for assignments with fixture/mock/test_data variable names
            # Removed broad ast.Name check to avoid false positives (e.g., test_data usage in production code)
            # Only assignment targets (left-hand side) are checked to detect fixture/mock/test_data definitions
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_lower = target.id.lower()
                        if any(
                            marker in name_lower
                            for marker in ["fixture", "mock", "test_data", "test_"]
                        ):
                            return True

        return False

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
            """Visitor to check for unsafe open() calls.

            Only flags open() calls that are NOT used as context managers or wrapped by closing().
            Removed in_with_context flag to avoid false negatives (e.g., 'with lock: f = open(...)').
            """

            def __init__(self) -> None:
                self.unsafe_opens: List[ast.Call] = []
                self.parent_stack: List[ast.AST] = []

            def visit(self, node: ast.AST) -> None:
                """Override visit to track parent nodes."""
                self.parent_stack.append(node)
                method = f"visit_{node.__class__.__name__}"
                visitor = getattr(self, method, self.generic_visit)
                visitor(node)
                self.parent_stack.pop()

            def visit_Call(self, node: ast.Call) -> None:
                """Check if this is an unsafe open() call."""
                # Check if this is a call to open()
                # Only safe if it's a context expression OR wrapped by closing()
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "open"
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
        sensitive_keywords = [
            "password",
            "token",
            "key",
            "secret",
            "api_key",
            "auth",
            "credential",
            "bearer",
        ]

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
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
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
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    value_lower = node.value.lower()
                    return any(keyword in value_lower for keyword in self.sensitive_keywords)

                # Check for FormattedValue nodes (f-string parts)
                if isinstance(node, ast.FormattedValue) and isinstance(node.value, ast.Name):
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
            # Only flag if not in test/mock context (same as hardcoded password check)
            if not self._is_in_test_or_mock_context(code):
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

        # Health orientation check - relaxed matching for health tests
        if "health" in test_name.lower():
            test_name_lower = test_name.lower()
            code_lower = code.lower()

            # Metric validation keywords that require BMI/calorie checks
            metric_validation_keywords = ["metric", "measure", "calculate", "bmi", "calorie"]
            requires_metric_validation = any(
                keyword in test_name_lower for keyword in metric_validation_keywords
            )

            # Acceptable health indicators (broader context)
            acceptable_health_indicators = [
                "status",
                "endpoint",
                "response",
                "200",
                "201",
                "404",
                "health",
                "bmi",
                "calorie",
                "calories",
                "weight",
                "height",
                "body",
            ]

            # If test name implies metric validation, require BMI/calorie
            if requires_metric_validation:
                has_metric = any(metric in code_lower for metric in ["bmi", "calorie", "calories"])
                if not has_metric:
                    violations.append("Health test does not verify key metrics")
            else:
                # For other health tests, check for any acceptable health indicator
                has_health_indicator = any(
                    indicator in code_lower for indicator in acceptable_health_indicators
                )
                if not has_health_indicator:
                    violations.append("Health test does not verify key metrics")

        # Scientific accuracy check
        if "nutrition" in test_name.lower() and all(
            metric not in code.lower() for metric in ["protein", "fat", "carbs", "vitamin"]
        ):
            violations.append("Nutrition test does not validate macronutrients")

        # Accessibility check - only flag error-oriented tests that lack error handling validation
        # Intent keywords that suggest the test is checking error/edge cases
        error_intent_keywords = [
            "edge",
            "invalid",
            "fail",
            "validation",
            "raises",
            "throws",
            "handles",
            "rejects",
            "bad_input",
            "error",
            "exception",
        ]
        test_name_lower = test_name.lower()
        code_lower = code.lower()

        # Check if test name suggests error/edge case intent
        has_error_intent = any(keyword in test_name_lower for keyword in error_intent_keywords)

        # Check if test body contains error assertion constructs (use generator for lazy evaluation)
        error_assertion_patterns = ["pytest.raises", "assertraises", "expect_error", "with raises"]
        has_error_assertion = any(pattern in code_lower for pattern in error_assertion_patterns)

        # Only flag if:
        # 1. Test name includes "user" AND suggests error/edge case intent
        # 2. BUT lacks both error keywords in code AND error assertion constructs
        if (
            "user" in test_name_lower
            and has_error_intent
            and "error" not in code_lower
            and "exception" not in code_lower
            and not has_error_assertion
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
        """Генерирует системные рекомендации / Generate system-wide recommendations.

        Returns bilingual recommendations (RU / EN) based on issue frequency.
        """
        recommendations = []

        # Count test records with at least one issue of each type
        num_technical_tests = sum(1 for r in self.integrated_results if r.technical_issues)
        num_nutrition_tests = sum(1 for r in self.integrated_results if r.nutrition_issues)
        num_safety_tests = sum(1 for r in self.integrated_results if r.safety_issues)
        num_philosophy_tests = sum(1 for r in self.integrated_results if r.philosophy_violations)

        # Рекомендации на основе частых проблем (bilingual output)
        if num_technical_tests > len(self.integrated_results) * self.TECHNICAL_THRESHOLD:
            recommendations.append(
                "Провести технический рефакторинг тестов / Conduct technical test refactoring"
            )

        if num_nutrition_tests > len(self.integrated_results) * self.NUTRITION_THRESHOLD:
            recommendations.append(
                "Усилить проверки безопасности питания / Strengthen nutrition safety checks"
            )

        if num_safety_tests > len(self.integrated_results) * self.SAFETY_THRESHOLD:
            recommendations.append(
                "Провести аудит безопасности данных / Conduct data security audit"
            )

        if num_philosophy_tests > len(self.integrated_results) * self.PHILOSOPHY_THRESHOLD:
            recommendations.append(
                "Обновить тесты в соответствии с философией системы / "
                "Update tests to align with system philosophy"
            )

        return recommendations
