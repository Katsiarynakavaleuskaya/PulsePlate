#!/usr/bin/env python3
"""
Bayesian analyzer for business logic, monetization, and cost optimization.

RU: Байесовский анализатор для бизнес-логики, монетизации и экономии средств.
EN: Analyzes tests from the perspective of business model, revenue, and cost optimization.
"""

from __future__ import annotations

import ast
import logging
import math
import re
import tokenize
from pathlib import Path
from types import ModuleType
from typing import Any
from dataclasses import dataclass
from enum import Enum
from io import StringIO

from core import i18n

logger = logging.getLogger(__name__)


class BusinessCategory(Enum):
    """Business problem categories.

    RU: Категории бизнес-проблем.
    EN: Categories of business issues and opportunities.
    """

    MONETIZATION = "monetization"
    CUSTOMER_ACQUISITION = "customer_acquisition"
    COST_OPTIMIZATION = "cost_optimization"
    REVENUE_GROWTH = "revenue_growth"
    USER_RETENTION = "user_retention"
    PRICING_STRATEGY = "pricing_strategy"
    MARKET_EXPANSION = "market_expansion"
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    DATA_MONETIZATION = "data_monetization"
    PARTNERSHIP_OPPORTUNITIES = "partnership_opportunities"


class BusinessErrorType(Enum):
    """Business error types.

    RU: Типы бизнес-ошибок.
    EN: Types of business errors and inefficiencies.
    """

    REVENUE_LEAK = "revenue_leak"
    COST_OVERSPEND = "cost_overspend"
    CUSTOMER_CHURN = "customer_churn"
    PRICING_INEFFICIENCY = "pricing_inefficiency"
    MARKET_MISSED = "market_missed"
    OPERATIONAL_WASTE = "operational_waste"
    DATA_UNDERUTILIZED = "data_underutilized"
    PARTNERSHIP_MISSED = "partnership_missed"
    SCALING_BLOCKED = "scaling_blocked"
    COMPETITIVE_DISADVANTAGE = "competitive_disadvantage"


@dataclass
class BusinessTestResult:
    """Test result from business perspective.

    RU: Результат теста с точки зрения бизнеса.
    EN: Result of test analysis from business and monetization perspective.
    """

    test_name: str
    success: bool
    business_category: BusinessCategory
    error_type: BusinessErrorType | None = None
    error_message: str = ""
    execution_time: float = 0.0
    file_path: str = ""
    revenue_impact: str = ""  # Описание влияния на доходы
    cost_impact: str = ""  # Описание влияния на затраты
    customer_impact: str = ""  # Описание влияния на клиентов
    optimization_potential: str = ""  # Потенциал оптимизации


@dataclass
class ROIEstimate:
    """Байесовская оценка ROI для категории оптимизации."""

    category: str
    expected_roi: float  # Posterior mean (expected ROI)
    credible_interval_lower: float  # 95% credible interval lower bound
    credible_interval_upper: float  # 95% credible interval upper bound
    time_horizon_months: int  # Time horizon for ROI calculation
    assumptions: str  # Key assumptions for the estimate


class BusinessBayesianAnalyzer:
    """Bayesian analyzer for business logic.

    RU: Байесовский анализатор для бизнес-логики.
    EN: Analyzes tests from business, monetization, and cost optimization perspectives.
    """

    # Generic price thresholds (fallback defaults)
    DEFAULT_LOW_PRICE_THRESHOLD: float = 1.0
    DEFAULT_HIGH_PRICE_THRESHOLD: float = 1000.0

    # Domain-specific thresholds for nutrition/health apps
    NUTRITION_LOW_PRICE_THRESHOLD: float = 5.0
    NUTRITION_HIGH_PRICE_THRESHOLD: float = 50.0

    # Epsilon: Numerical stability guard for Bayesian ROI calculations
    # RU: Epsilon: защита численной стабильности для байесовских расчетов ROI
    # EN: Guards against zero/near-zero standard deviations in delta-method approximations.
    #     Value: 1e-12 (small positive constant chosen for numerical stability)
    #     Usage: Prevents division by zero when computing precision (1 / variance) in
    #            posterior distribution updates during Bayesian ROI estimation.
    #     Reference: Numerical Recipes (Press et al.) - "Avoiding Floating-Point Pitfalls"
    EPSILON: float = 1e-12

    # Delta-method approximation thresholds for ROI estimation
    # RU: Пороги аппроксимации дельта-метода для оценки ROI
    # EN: These thresholds determine when to switch from first-order to variance-formula
    #     approximation in log-space transformations for ROI distributions.
    #     - RELATIVE_VARIANCE_THRESHOLD: When std/mean ratio > 10%, first-order breaks down
    #     - VAR_RATIO_THRESHOLD: When (σ²/μ²) > 1%, variance formula needed for accuracy
    #     Reference: Delta method approximation for log transformation (Casella & Berger, 2002)
    RELATIVE_VARIANCE_THRESHOLD: float = 0.1
    VAR_RATIO_THRESHOLD: float = 0.01

    # Maximum credible upper bound for ROI estimates
    # RU: Максимальная верхняя граница доверительного интервала для оценок ROI
    # EN: Prevents astronomically large/misleading upper bounds due to high posterior variance.
    #     Value: 10.0 (1000% ROI) - reasonable upper limit for business projections
    #     Rationale: ROI > 1000% is unrealistic for most business optimizations and likely
    #     indicates high uncertainty rather than genuine potential.
    #     This constant is configurable for domains expecting higher returns.
    MAX_CREDIBLE_UPPER_ROI: float = 10.0

    # Severity to ROI mapping for failed tests
    # Maps error severity levels to ROI impact (benefit/cost ratio)
    # Lower severity = lower ROI (less urgent), higher severity = higher ROI (more urgent)
    # TODO: Replace with actual metrics from telemetry/analytics once available
    SEVERITY_TO_ROI: dict[str, float] = {
        "critical": 0.5,  # High-impact failures (50% ROI)
        "high": 0.3,  # Significant failures (30% ROI)
        "medium": 0.2,  # Moderate failures (20% ROI)
        "low": 0.1,  # Minor failures (10% ROI)
    }
    DEFAULT_FAILURE_ROI: float = 0.1  # Fallback ROI for unknown severity

    def __init__(
        self,
        low_price_threshold: float | None = None,
        high_price_threshold: float | None = None,
        domain: str = "nutrition",
        business_knowledge: dict[str, Any] | None = None,
        monetization_strategies: dict[str, Any] | None = None,
        cost_optimization_rules: dict[str, Any] | None = None,
        locale: str | None = None,
    ) -> None:
        """
        Initialize business logic analyzer.

        RU: Инициализирует анализатор бизнес-логики.
        EN: Initializes the business logic analyzer with optional configuration injection.

        Args:
            low_price_threshold: Lower price threshold (if None, uses domain-specific config)
            high_price_threshold: Upper price threshold (if None, uses domain-specific config)
            domain: Application domain ("nutrition", "health", or "generic")
            business_knowledge: Optional injected business knowledge dict
                (overrides file loading)
            monetization_strategies: Optional injected monetization strategies dict
                (overrides file loading)
            cost_optimization_rules: Optional injected cost optimization rules dict (overrides file loading)
            locale: Optional locale code (e.g., 'en', 'ru', 'es') for loading localized configs.
                Falls back to 'en' if not provided or invalid.
        """
        self.test_results: list[BusinessTestResult] = []
        # Persist normalized locale for downstream diagnostics and tests
        self.locale: str = i18n.normalize_lang(locale)
        # Load business knowledge: injected config takes priority over file loading
        self.business_knowledge_base = (
            business_knowledge
            if business_knowledge is not None
            else self._load_business_knowledge()
        )
        # Load monetization strategies
        if monetization_strategies is not None:
            self.monetization_strategies = monetization_strategies
        else:
            self.monetization_strategies = self._load_monetization_strategies(locale=locale)

        # Load cost optimization rules
        if cost_optimization_rules is not None:
            self.cost_optimization_rules = cost_optimization_rules
        else:
            self.cost_optimization_rules = self._load_cost_optimization_rules()

        # Configure price thresholds
        if low_price_threshold is not None:
            self.low_price_threshold = low_price_threshold
        elif domain in {"nutrition", "health"}:
            self.low_price_threshold = self.NUTRITION_LOW_PRICE_THRESHOLD
        else:
            self.low_price_threshold = self.DEFAULT_LOW_PRICE_THRESHOLD

        if high_price_threshold is not None:
            self.high_price_threshold = high_price_threshold
        elif domain in {"nutrition", "health"}:
            self.high_price_threshold = self.NUTRITION_HIGH_PRICE_THRESHOLD
        else:
            self.high_price_threshold = self.DEFAULT_HIGH_PRICE_THRESHOLD

    @staticmethod
    def _import_yaml_module() -> ModuleType | None:
        """Attempt to import PyYAML, returning None if unavailable."""
        try:
            import yaml

            return yaml
        except (ModuleNotFoundError, ImportError):
            return None
        # Let other exceptions (version conflicts, corrupt installs) propagate

    def _config_dir(self) -> Path:
        """Return the config directory adjacent to this module, with fallback to parent."""
        module_path = Path(__file__).resolve()
        candidates = [
            module_path.parent / "config",
            module_path.parent.parent / "config",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _load_business_knowledge(self) -> dict[str, Any]:
        """Load business knowledge base from YAML or return defaults."""
        yaml_mod = self._import_yaml_module()
        config_path = self._config_dir() / "business_knowledge.yaml"
        if yaml_mod and config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as fh:
                    data = yaml_mod.safe_load(fh) or {}
                    if isinstance(data, dict):
                        if "revenue_streams" in data:
                            return data
                        # If YAML missing expected keys, fall back to defaults
            except Exception:
                logging.debug("Failed to load business_knowledge.yaml", exc_info=True)

        # Fallback defaults
        return {
            "revenue_streams": {
                "subscription": {"price_range": [5, 50]},
                "subscriptions": {"price_range": [5, 50]},
                "ads": {"price_range": [0.01, 5]},
            },
            "pricing_models": {"freemium": True, "payg": True},
        }

    def _load_monetization_strategies(self, locale: str | None = None) -> dict[str, Any]:
        """Load monetization strategies by locale, with fallbacks."""
        yaml_mod = self._import_yaml_module()
        lang = i18n.normalize_lang(locale)
        base_dir = self._config_dir()
        localized = base_dir / f"monetization_strategies.{lang}.yaml"
        default_path = base_dir / "monetization_strategies.yaml"

        for path in (localized, default_path):
            if yaml_mod and path.exists():
                try:
                    with path.open("r", encoding="utf-8") as fh:
                        data = yaml_mod.safe_load(fh) or {}
                        if isinstance(data, dict):
                            return data
                except Exception:
                    logging.debug("Failed to load %s", path, exc_info=True)

        return {
            "pricing_models": {
                "tiered": ["basic", "pro", "enterprise"],
                "usage_based": True,
                "discounts": ["annual", "student"],
            },
            "upsell": {"bundle": True, "premium_support": True},
        }

    def _load_cost_optimization_rules(self) -> dict[str, Any]:
        """Load cost optimization rules from YAML or return defaults."""
        yaml_mod = self._import_yaml_module()
        config_path = self._config_dir() / "cost_optimization_rules.yaml"
        if yaml_mod and config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as fh:
                    data = yaml_mod.safe_load(fh) or {}
                    if isinstance(data, dict):
                        return data
            except Exception:
                logging.debug("Failed to load cost_optimization_rules.yaml", exc_info=True)

        return {
            "infrastructure": {"auto_scaling": True, "capacity_planning": True},
            "development": {"testing": True, "ci_cd": True},
            "operations": {"support": True, "monitoring": True},
        }

    def analyze(self, test_code: str | list[str], test_name: str) -> list[BusinessTestResult]:
        """Public entry point for business logic analysis.
        Публичная точка входа для анализа бизнес-логики.
        """
        return self.analyze_business_logic(test_code, test_name)

    def analyze_business_logic(
        self, test_code: str | list[str], test_name: str
    ) -> list[BusinessTestResult]:
        """Analyze business logic aspects of test code.

        Args:
            test_code (str | list[str]): The test code to analyze.
            test_name (str): The name of the test.

        Returns:
            list[BusinessTestResult]: The results of business logic analysis.
        """
        business_logic_results: list[BusinessTestResult] = []
        normalized_code: str = self._normalize_code_input(test_code)

        # Анализ монетизации (Monetization Analysis)
        monetization_analysis_results: list[BusinessTestResult] = self._analyze_monetization(
            normalized_code, test_name
        )
        business_logic_results.extend(monetization_analysis_results)

        customer_acquisition_results: list[BusinessTestResult] = self._analyze_customer_acquisition(
            normalized_code, test_name
        )
        business_logic_results.extend(customer_acquisition_results)

        # Анализ оптимизации затрат
        cost_issues: list[BusinessTestResult] = self._analyze_cost_optimization(
            normalized_code, test_name
        )
        business_logic_results.extend(cost_issues)

        # Анализ роста доходов
        revenue_issues = self._analyze_revenue_growth(normalized_code, test_name)
        business_logic_results.extend(revenue_issues)

        # Анализ удержания клиентов
        retention_issues = self._analyze_customer_retention(normalized_code, test_name)
        business_logic_results.extend(retention_issues)

        # Persist results for downstream diagnostics
        self.test_results.extend(business_logic_results)
        return business_logic_results

    def _normalize_code_input(self, code: str | list[str] | tuple[str, ...]) -> str:
        """Convert test code input (str, list, or tuple) to a single string."""
        if isinstance(code, (list, tuple)):
            return "\n".join(str(line) for line in code)
        return str(code)

    def _remove_comments(self, code: str | list[str]) -> str:
        """Remove inline comments while preserving '#' inside string literals."""
        code_str = self._normalize_code_input(code)

        try:
            tokens: list[tokenize.TokenInfo] = []
            tokens.extend(
                token
                for token in tokenize.generate_tokens(StringIO(code_str).readline)
                if token.type != tokenize.COMMENT
            )
            # tokenize.untokenize always returns str in Python 3
            return str(tokenize.untokenize(tokens))
        except tokenize.TokenError:
            # Fallback: character-level parsing that tracks string literals across lines
            return self._remove_comments_fallback(code_str)

    def _remove_comments_fallback(self, code_str: str) -> str:
        """Remove comments while preserving '#' inside string literals across multiple lines.

        Maintains state between lines to properly handle multiline strings.
        """
        in_single_quote = False
        in_double_quote = False
        in_triple_single = False
        in_triple_double = False
        cleaned_lines = []

        for line in code_str.splitlines():
            cleaned_line = ""
            i = 0

            while i < len(line):
                # Check for triple quotes first (longer match)
                if i + 2 < len(line):
                    three_chars = line[i : i + 3]

                    # Triple single quotes
                    if three_chars == "'''" and not in_double_quote and not in_triple_double:
                        in_triple_single = not in_triple_single
                        cleaned_line += three_chars
                        i += 3
                        continue

                    # Triple double quotes
                    if three_chars == '"""' and not in_single_quote and not in_triple_single:
                        in_triple_double = not in_triple_double
                        cleaned_line += three_chars
                        i += 3
                        continue

                char = line[i]

                # Check for escape sequences
                if char == "\\" and i + 1 < len(line):
                    # Skip escaped character (including escaped quotes)
                    cleaned_line += line[i : i + 2]
                    i += 2
                    continue

                # Check for single quote (only if not in any other quote type)
                if (
                    char == "'"
                    and not in_double_quote
                    and not in_triple_single
                    and not in_triple_double
                ):
                    in_single_quote = not in_single_quote
                    cleaned_line += char
                    i += 1
                    continue

                # Check for double quote (only if not in any other quote type)
                if (
                    char == '"'
                    and not in_single_quote
                    and not in_triple_single
                    and not in_triple_double
                ):
                    in_double_quote = not in_double_quote
                    cleaned_line += char
                    i += 1
                    continue

                # Check for comment start (only if not in any string)
                if (
                    char == "#"
                    and not in_single_quote
                    and not in_double_quote
                    and not in_triple_single
                    and not in_triple_double
                ):
                    # Found comment start - stop processing this line
                    break

                cleaned_line += char
                i += 1

            # Add the cleaned line (without trailing whitespace)
            cleaned_lines.append(cleaned_line.rstrip())

        return "\n".join(cleaned_lines)

    def _analyze_monetization(self, code: str, test_name: str) -> list[BusinessTestResult]:
        """Анализирует стратегии монетизации."""
        results = []
        # Ignore inline comments when scanning for strategy keywords to avoid false negatives
        # Use tokenize to properly remove comments while preserving '#' inside string literals
        code_no_comments = self._remove_comments(code)

        # Поиск упоминаний цен и платежей
        pricing_patterns = [
            r"price\s*[=:]\s*(\d+(?:\.\d+)?)",
            r"cost\s*[=:]\s*(\d+(?:\.\d+)?)",
            r"fee\s*[=:]\s*(\d+(?:\.\d+)?)",
            r"subscription\s*[=:]\s*(\d+(?:\.\d+)?)",
        ]

        for pattern in pricing_patterns:
            matches = re.finditer(pattern, code_no_comments, re.IGNORECASE)
            for match in matches:
                try:
                    price = float(match.group(1))

                    # Проверка на разумность цены с использованием конфигурируемых порогов
                    if price < self.low_price_threshold:
                        results.append(
                            BusinessTestResult(
                                test_name=test_name,
                                success=False,
                                business_category=BusinessCategory.MONETIZATION,
                                error_type=BusinessErrorType.PRICING_INEFFICIENCY,
                                error_message=(
                                    f"Слишком низкая цена (${price:.2f}) ниже порога "
                                    f"${self.low_price_threshold:.2f} "
                                    "приводит к потере дохода"
                                ),
                                revenue_impact="Потеря потенциального дохода",
                                cost_impact="Не покрывает операционные расходы",
                                optimization_potential=(
                                    f"Увеличить цену до рыночного уровня "
                                    f"(минимум ${self.low_price_threshold:.2f})"
                                ),
                            )
                        )
                    elif price > self.high_price_threshold:
                        results.append(
                            BusinessTestResult(
                                test_name=test_name,
                                success=False,
                                business_category=BusinessCategory.MONETIZATION,
                                error_type=BusinessErrorType.PRICING_INEFFICIENCY,
                                error_message=(
                                    f"Слишком высокая цена: ${price:.2f} превышает порог "
                                    f"${self.high_price_threshold:.2f}"
                                ),
                                revenue_impact="Снижение конверсии",
                                customer_impact="Отпугивание клиентов",
                                optimization_potential=(
                                    f"Снизить цену до разумного уровня "
                                    f"(максимум ${self.high_price_threshold:.2f}) "
                                    "или добавить ценностное предложение"
                                ),
                            )
                        )
                except ValueError:
                    continue

        # Проверка на отсутствие стратегии монетизации
        if ("payment" in code_no_comments.lower() or "billing" in code_no_comments.lower()) and all(
            keyword not in code_no_comments.lower()
            for keyword in ["subscription", "tier", "plan", "upgrade"]
        ):
            results.append(
                BusinessTestResult(
                    test_name=test_name,
                    success=False,
                    business_category=BusinessCategory.MONETIZATION,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                    error_message="Обнаружены платежи без стратегии монетизации",
                    revenue_impact="Неэффективная монетизация",
                    optimization_potential="Реализовать многоуровневую модель ценообразования",
                )
            )

        return results

    def _analyze_customer_acquisition(self, code: str, test_name: str) -> list[BusinessTestResult]:
        """Анализирует привлечение клиентов."""
        results = []

        # Поиск упоминаний регистрации и привлечения
        acquisition_keywords = ["register", "signup", "sign_up", "create_account", "new_user"]
        acquisition_mentions = [kw for kw in acquisition_keywords if kw in code.lower()]

        if acquisition_mentions:
            # Проверка на отсутствие валидации
            if all(
                keyword not in code.lower() for keyword in ["validate", "check", "verify", "email"]
            ):
                results.append(
                    BusinessTestResult(
                        test_name=test_name,
                        success=False,
                        business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                        error_type=BusinessErrorType.CUSTOMER_CHURN,
                        error_message="Регистрация без валидации данных",
                        customer_impact="Низкое качество лидов",
                        optimization_potential="Добавить валидацию email и проверку данных",
                    )
                )

            # Проверка на отсутствие онбординга
            if all(
                keyword not in code.lower()
                for keyword in ["onboard", "tutorial", "guide", "welcome"]
            ):
                results.append(
                    BusinessTestResult(
                        test_name=test_name,
                        success=False,
                        business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                        error_type=BusinessErrorType.CUSTOMER_CHURN,
                        error_message="Отсутствует процесс онбординга",
                        customer_impact="Высокий отток новых пользователей",
                        optimization_potential="Добавить пошаговый онбординг",
                    )
                )

        return results

    def _analyze_cost_optimization(self, code: str, test_name: str) -> list[BusinessTestResult]:
        """Анализирует возможности оптимизации затрат."""
        results = []
        code_for_regex = code[:10240]

        # 1. Nested loops: Use AST for accurate detection, fallback to regex for broken code
        # Heavy operation indicators (used by both AST and regex paths)
        heavy_indicators = [
            r"\.append\(",
            r"\.extend\(",
            r"\.insert\(",
            r"database",
            r"query",
            r"api",
            r"request",
        ]

        # Try AST-based detection first (accurate indentation-aware)
        try:
            tree = ast.parse(code)
        except SyntaxError:
            tree = None

        if tree is not None:
            # AST-based detection: check for nested (sync/async) for-loops at any depth
            # AsyncFor available in Python 3.5+ for async for loops
            # This catches patterns like:
            #   for ...: if ...: for ...:
            #   async for ...: for ...:
            #   for ...: while ...: for ...:
            #   for ...: try: for ...:
            async_for = getattr(ast, "AsyncFor", None)
            loop_node_types = (ast.For, async_for) if async_for is not None else (ast.For,)
            for node in ast.walk(tree):
                if isinstance(node, loop_node_types):
                    # Walk the entire subtree of this for loop to find ANY nested for loops
                    # (not just direct children)
                    for descendant in ast.walk(node):
                        # Skip the node itself
                        if descendant is node or not isinstance(descendant, loop_node_types):
                            continue
                        # Found a nested for loop
                        loop_body_src = ast.get_source_segment(code, descendant) or ""
                        # Check if inner loop lacks break/return and has heavy operations
                        if not re.search(r"\b(break|return)\b", loop_body_src) and any(
                            re.search(pattern, loop_body_src, re.IGNORECASE)
                            for pattern in heavy_indicators
                        ):
                            results.append(
                                BusinessTestResult(
                                    test_name=test_name,
                                    success=False,
                                    business_category=BusinessCategory.COST_OPTIMIZATION,
                                    error_type=BusinessErrorType.OPERATIONAL_WASTE,
                                    error_message="Вложенные циклы без break/return",
                                    cost_impact="Повышенное потребление ресурсов",
                                    optimization_potential="Оптимизировать алгоритм или добавить ранний выход",
                                )
                            )
                            # Only report once per outer loop
                            break
        else:
            # Fallback heuristic without heavy regex to avoid ReDoS risk
            lines = code_for_regex.splitlines()
            for idx, line in enumerate(lines):
                line_stripped = line.lstrip()
                if not (
                    line_stripped.startswith("for ")
                    and " in " in line_stripped
                    and ":" in line_stripped
                ):
                    continue
                lookahead = lines[idx + 1 : idx + 11]
                for inner in lookahead:
                    inner_stripped = inner.lstrip()
                    if not (
                        inner_stripped.startswith("for ")
                        and " in " in inner_stripped
                        and ":" in inner_stripped
                    ):
                        continue

                    # Found nested for loop - check for heavy operations
                    loop_body = "\n".join(lookahead)
                    if not re.search(r"\b(break|return)\b", loop_body) and any(
                        re.search(pattern, loop_body, re.IGNORECASE) for pattern in heavy_indicators
                    ):
                        results.append(
                            BusinessTestResult(
                                test_name=test_name,
                                success=False,
                                business_category=BusinessCategory.COST_OPTIMIZATION,
                                error_type=BusinessErrorType.OPERATIONAL_WASTE,
                                error_message="Вложенные циклы без break/return",
                                cost_impact="Повышенное потребление ресурсов",
                                optimization_potential="Оптимизировать алгоритм или добавить ранний выход",
                            )
                        )
                    break

        # 2. SELECT *: flag when not in test/fixture context
        select_star_pattern = r"SELECT\s+\*\s+FROM"
        if re.search(select_star_pattern, code_for_regex, re.IGNORECASE):
            is_test_or_fixture = (
                test_name.lower().startswith("test_") or "fixture" in code_for_regex.lower()
            )
            if not is_test_or_fixture:
                results.append(
                    BusinessTestResult(
                        test_name=test_name,
                        success=False,
                        business_category=BusinessCategory.COST_OPTIMIZATION,
                        error_type=BusinessErrorType.OPERATIONAL_WASTE,
                        error_message=("SELECT * запрос без контекста теста/фикстуры"),
                        cost_impact="Избыточная загрузка данных",
                        optimization_potential="Указать конкретные колонки вместо SELECT *",
                    )
                )

        # 3. while True: only flag when no break/return in loop body
        while_true_pattern = r"while\s+True\s*:"
        while_matches = re.finditer(while_true_pattern, code_for_regex, re.IGNORECASE)
        for match in while_matches:
            # Extract loop body using DOTALL to match across lines
            loop_start = match.end()
            # Find the body (next 50 lines or until dedent)
            remaining_code = code_for_regex[loop_start:]
            lines_after = remaining_code.split("\n")[:50]
            loop_body = "\n".join(lines_after)
            # Check if there's a break or return in the loop body
            # Removed re.DOTALL to avoid ReDoS vulnerability
            if not re.search(r"\b(break|return)\b", loop_body):
                results.append(
                    BusinessTestResult(
                        test_name=test_name,
                        success=False,
                        business_category=BusinessCategory.COST_OPTIMIZATION,
                        error_type=BusinessErrorType.OPERATIONAL_WASTE,
                        error_message="while True без break/return в теле цикла",
                        cost_impact="Риск бесконечного цикла",
                        optimization_potential="Добавить условие выхода или break/return",
                    )
                )

        # 4. sleep(): broaden detection but avoid retry/backoff patterns
        # Match sleep( with bounded argument length to avoid expensive backtracking
        sleep_pattern = r"sleep\s*\(\s*[^)\n]{0,80}\)"
        sleep_matches = re.finditer(sleep_pattern, code_for_regex, re.IGNORECASE)
        for match in sleep_matches:
            # Check context: skip if it's part of retry/backoff logic
            context_start = max(0, match.start() - 100)
            context_end = min(len(code_for_regex), match.end() + 100)
            context = code_for_regex[context_start:context_end].lower()
            # Skip common retry/backoff patterns
            retry_keywords = ["retry", "backoff", "exponential", "jitter", "wait", "delay"]
            if all(keyword not in context for keyword in retry_keywords):
                results.append(
                    BusinessTestResult(
                        test_name=test_name,
                        success=False,
                        business_category=BusinessCategory.COST_OPTIMIZATION,
                        error_type=BusinessErrorType.OPERATIONAL_WASTE,
                        error_message=(
                            f"Использование sleep() без контекста retry/backoff: {match.group(0)}"
                        ),
                        cost_impact="Блокирующие задержки",
                        optimization_potential="Использовать асинхронные операции или retry-логику",
                    )
                )

        # Проверка на отсутствие кэширования
        code_lower = code_for_regex.lower()
        if any(
            keyword in code_lower for keyword in ["database", "api", "request", "fetch"]
        ) and all(keyword not in code_lower for keyword in ["cache", "memoize", "redis", "memory"]):
            results.append(
                BusinessTestResult(
                    test_name=test_name,
                    success=False,
                    business_category=BusinessCategory.COST_OPTIMIZATION,
                    error_type=BusinessErrorType.OPERATIONAL_WASTE,
                    error_message="Отсутствует кэширование для частых запросов",
                    cost_impact="Избыточные затраты на инфраструктуру",
                    optimization_potential="Добавить кэширование для снижения нагрузки",
                )
            )

        return results

    def _analyze_revenue_growth(self, code: str, test_name: str) -> list[BusinessTestResult]:
        """Анализирует возможности роста доходов."""
        results = []
        code_for_regex = code[:10240]
        code_lower = code_for_regex.lower()

        # Обнаружение явных утечек дохода (отрицательные платежи) без рискованного regex
        if "process_payment" in code_lower and "amount" in code_lower and "-" in code_lower:
            for line in code_for_regex.splitlines():
                line_lower = line.lower()
                if "process_payment" not in line_lower or "amount" not in line_lower:
                    continue
                if "amount" in line_lower and "=-" in line_lower.replace(" ", ""):
                    results.append(
                        BusinessTestResult(
                            test_name=test_name,
                            success=False,
                            business_category=BusinessCategory.REVENUE_GROWTH,
                            error_type=BusinessErrorType.REVENUE_LEAK,
                            error_message="Обнаружена утечка дохода: отрицательная сумма платежа",
                            revenue_impact="Непосредственная потеря дохода",
                            optimization_potential="Валидировать суммы платежей и отклонять отрицательные значения",
                        )
                    )
                    break

        # Поиск упоминаний аналитики и метрик
        analytics_keywords = ["analytics", "metrics", "tracking", "conversion", "revenue"]
        analytics_mentions = [kw for kw in analytics_keywords if kw in code_lower]

        if analytics_mentions and all(
            keyword not in code_lower for keyword in ["ab_test", "experiment", "variant", "control"]
        ):
            results.append(
                BusinessTestResult(
                    test_name=test_name,
                    success=False,
                    business_category=BusinessCategory.REVENUE_GROWTH,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                    error_message="Аналитика без A/B тестирования",
                    revenue_impact="Упущенные возможности оптимизации",
                    optimization_potential="Добавить A/B тестирование для роста конверсии",
                )
            )

        # Проверка на отсутствие персонализации
        if (
            "user" in code_lower
            and "personal" in code_lower
            and all(
                keyword not in code_lower
                for keyword in ["recommend", "suggest", "customize", "tailor"]
            )
        ):
            results.append(
                BusinessTestResult(
                    test_name=test_name,
                    success=False,
                    business_category=BusinessCategory.REVENUE_GROWTH,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                    error_message="Персонализация без рекомендаций",
                    revenue_impact="Снижение вовлеченности и LTV",
                    optimization_potential="Добавить систему рекомендаций",
                )
            )

        return results

    def _analyze_customer_retention(self, code: str, test_name: str) -> list[BusinessTestResult]:
        """Анализирует удержание клиентов."""
        results = []

        # Поиск упоминаний уведомлений и коммуникации
        communication_keywords = ["notification", "email", "message", "alert", "reminder"]
        communication_mentions = [kw for kw in communication_keywords if kw in code.lower()]

        if communication_mentions and all(
            keyword not in code.lower() for keyword in ["segment", "group", "cohort", "tier"]
        ):
            results.append(
                BusinessTestResult(
                    test_name=test_name,
                    success=False,
                    business_category=BusinessCategory.USER_RETENTION,
                    error_type=BusinessErrorType.CUSTOMER_CHURN,
                    error_message="Коммуникация без сегментации",
                    customer_impact="Низкая релевантность сообщений",
                    optimization_potential="Добавить сегментацию пользователей",
                )
            )

        # Проверка на отсутствие обратной связи
        if ("feedback" in code.lower() or "review" in code.lower()) and all(
            keyword not in code.lower() for keyword in ["analyze", "process", "respond", "action"]
        ):
            results.append(
                BusinessTestResult(
                    test_name=test_name,
                    success=False,
                    business_category=BusinessCategory.USER_RETENTION,
                    error_type=BusinessErrorType.CUSTOMER_CHURN,
                    error_message="Сбор обратной связи без обработки",
                    customer_impact="Неудовлетворенность клиентов",
                    optimization_potential="Добавить обработку и реагирование на обратную связь",
                )
            )

        return results

    def generate_cost_savings_recommendations(self) -> list[str]:
        """Генерирует рекомендации по экономии средств."""
        recommendations = []

        # Анализируем проблемы
        issues = self.diagnose_business_issues()

        # Рекомендации по инфраструктуре
        if BusinessCategory.COST_OPTIMIZATION in issues:
            recommendations.extend(
                [
                    "Использовать spot-инстансы для некритичных задач (экономия до 70%)",
                    "Реализовать автоматическое масштабирование (снижение затрат на 30%)",
                    "Добавить кэширование для снижения нагрузки на БД (экономия 40%)",
                    "Оптимизировать CDN для снижения трафика (экономия 25%)",
                ]
            )

        # Рекомендации по разработке
        if BusinessCategory.OPERATIONAL_EFFICIENCY in issues:
            recommendations.extend(
                [
                    "Автоматизировать тестирование (снижение времени разработки на 50%)",
                    "Использовать переиспользование кода (снижение затрат на разработку на 30%)",
                    "Добавить мониторинг для проактивного решения проблем (снижение downtime на 60%)",
                ]
            )

        # Рекомендации по монетизации
        if BusinessCategory.MONETIZATION in issues:
            recommendations.extend(
                [
                    "Реализовать многоуровневую модель ценообразования (рост ARPU на 40%)",
                    "Добавить реферальную программу (снижение CAC на 25%)",
                    "Внедрить A/B тестирование цен (рост конверсии на 20%)",
                ]
            )

        return recommendations

    def generate_revenue_optimization_recommendations(self) -> list[str]:
        """Генерирует рекомендации по оптимизации доходов."""
        recommendations = []

        # Анализируем проблемы
        issues = self.diagnose_business_issues()

        # Рекомендации по привлечению клиентов
        if BusinessCategory.CUSTOMER_ACQUISITION in issues:
            recommendations.extend(
                [
                    "Улучшить процесс онбординга (рост конверсии на 35%)",
                    "Добавить социальные доказательства (рост доверия на 50%)",
                    "Реализовать бесплатный пробный период (рост подписок на 60%)",
                ]
            )

        # Рекомендации по удержанию
        if BusinessCategory.USER_RETENTION in issues:
            recommendations.extend(
                [
                    "Добавить персонализированные рекомендации (рост LTV на 45%)",
                    "Реализовать программу лояльности (снижение churn на 30%)",
                    "Улучшить поддержку клиентов (рост NPS на 40%)",
                ]
            )

        # Рекомендации по монетизации данных
        if BusinessCategory.DATA_MONETIZATION in issues:
            recommendations.extend(
                [
                    "Создать анонимизированные аналитические отчеты (новый поток доходов)",
                    "Предложить API для партнеров (B2B монетизация)",
                    "Разработать премиум аналитику (увеличение ARPU на 25%)",
                ]
            )

        return recommendations

    def diagnose_business_issues(self) -> dict[BusinessCategory, float]:
        """Диагностирует бизнес-проблемы."""
        if not self.test_results:
            return {}

        # Подсчитываем проблемы по категориям
        category_counts: dict[BusinessCategory, int] = {}
        total_issues = 0

        for result in self.test_results:
            if not result.success:
                category = result.business_category
                category_counts[category] = category_counts.get(category, 0) + 1
                total_issues += 1

        return {
            category: count / total_issues if total_issues > 0 else 0.0
            for category, count in category_counts.items()
        }

    def calculate_roi_potential(self) -> list[ROIEstimate]:
        """
        Вычисляет потенциал ROI для различных оптимизаций с использованием байесовского подхода.

        Returns:
            list[ROIEstimate]: Список байесовских оценок ROI для каждой категории оптимизации.
        """
        issues = self.diagnose_business_issues()
        roi_estimates: list[ROIEstimate] = []

        # Собираем данные из результатов тестов для обновления априорных распределений
        category_data = self._collect_category_data()

        # Потенциал ROI для каждой категории с байесовской оценкой
        if BusinessCategory.COST_OPTIMIZATION in issues:
            estimate = self._calculate_bayesian_roi(
                category="cost_optimization",
                prior_mean=0.25,  # Априорное ожидание 25% экономии
                prior_std=0.15,  # Неопределенность априорного распределения
                data=category_data.get("cost_optimization", []),
                time_horizon_months=12,
                assumptions="Экономия затрат на инфраструктуру и операции",
            )
            roi_estimates.append(estimate)

        if BusinessCategory.MONETIZATION in issues:
            estimate = self._calculate_bayesian_roi(
                category="monetization",
                prior_mean=0.35,  # Априорное ожидание 35% роста доходов
                prior_std=0.20,
                data=category_data.get("monetization", []),
                time_horizon_months=6,
                assumptions="Рост доходов через улучшенную монетизацию",
            )
            roi_estimates.append(estimate)

        if BusinessCategory.CUSTOMER_ACQUISITION in issues:
            estimate = self._calculate_bayesian_roi(
                category="customer_acquisition",
                prior_mean=0.20,  # Априорное ожидание 20% роста конверсии
                prior_std=0.12,
                data=category_data.get("customer_acquisition", []),
                time_horizon_months=3,
                assumptions="Улучшение конверсии через оптимизацию онбординга",
            )
            roi_estimates.append(estimate)

        if BusinessCategory.USER_RETENTION in issues:
            estimate = self._calculate_bayesian_roi(
                category="user_retention",
                prior_mean=0.30,  # Априорное ожидание 30% роста LTV
                prior_std=0.18,
                data=category_data.get("user_retention", []),
                time_horizon_months=12,
                assumptions="Рост LTV через улучшение удержания клиентов",
            )
            roi_estimates.append(estimate)

        return roi_estimates

    def _collect_category_data(self) -> dict[str, list[float]]:
        """
        Собирает исторические данные по категориям из результатов тестов.

        Returns:
            dict[str, list[float]]: Данные по категориям (benefit/cost ratios).
        """
        category_data: dict[str, list[float]] = {}

        # Извлекаем информацию из результатов тестов
        # ROI оценивается на основе severity/impact (если доступно) или категории ошибки
        # TODO: Integrate actual telemetry/metrics once available (e.g., error frequency, fix time)
        for result in self.test_results:
            if not result.success:
                category_key = result.business_category.value
                if category_key not in category_data:
                    category_data[category_key] = []

                # Determine ROI based on error severity/impact if available
                # Try to extract severity from error message or use error_type mapping
                roi = self.DEFAULT_FAILURE_ROI  # Start with fallback

                # Check if error_message contains severity indicators
                error_msg = (result.error_message or "").lower()
                if "critical" in error_msg or "high impact" in error_msg:
                    roi = self.SEVERITY_TO_ROI.get("critical", roi)
                elif "high" in error_msg or "important" in error_msg:
                    roi = self.SEVERITY_TO_ROI.get("high", roi)
                elif "medium" in error_msg or "moderate" in error_msg:
                    roi = self.SEVERITY_TO_ROI.get("medium", roi)
                elif "low" in error_msg or "minor" in error_msg:
                    roi = self.SEVERITY_TO_ROI.get("low", roi)
                # else: use DEFAULT_FAILURE_ROI

                category_data[category_key].append(roi)

        return category_data

    def _calculate_bayesian_roi(
        self,
        category: str,
        prior_mean: float,
        prior_std: float,
        data: list[float],
        time_horizon_months: int,
        assumptions: str,
    ) -> ROIEstimate:
        """
        Вычисляет байесовскую оценку ROI используя нормальное распределение на log-returns.

        Args:
            category: Название категории оптимизации
            prior_mean: Априорное среднее значение ROI (must be > -1, ROI > -100%)
            prior_std: Априорное стандартное отклонение (must be >= 0)
            data: Исторические данные (benefit/cost ratios, all values must be > -1)
            time_horizon_months: Горизонт времени в месяцах
            assumptions: Ключевые предположения

        Returns:
            ROIEstimate: Байесовская оценка ROI с 95% доверительным интервалом

        Raises:
            ValueError: If input validation fails (invalid prior_mean, prior_std, or data values)
        """
        # Input validation: ROI must be > -1 (ROI > -100%)
        if prior_mean <= -1:
            raise ValueError(
                f"Invalid prior_mean for category '{category}': {prior_mean}. "
                f"ROI must be > -1 (prior_mean > -1) to allow log transformation."
            )
        if prior_std < 0:
            raise ValueError(
                f"Invalid prior_std for category '{category}': {prior_std}. "
                f"Standard deviation must be >= 0."
            )

        # Validate all data values are > -1
        if invalid_data := [x for x in data if x <= -1]:
            raise ValueError(
                f"Invalid data values for category '{category}': {invalid_data}. "
                f"All ROI values must be > -1 (ROI > -100%) to allow log transformation."
            )

        # Преобразуем ROI в log-returns для нормального распределения
        # ROI = (benefit - cost) / cost, поэтому log_return = log(1 + ROI)
        try:
            prior_log_mean = math.log(1 + prior_mean)
        except ValueError as e:  # pragma: no cover - defensive guard after validation
            raise ValueError(
                f"Math domain error computing log(1 + prior_mean) for category '{category}': "
                f"prior_mean={prior_mean}. This should not occur after validation."
            ) from e

        # First-order delta-method approximation: prior_log_std ≈ prior_std / (1 + prior_mean)
        # This is valid only for small relative variance (prior_std << 1 + prior_mean).
        # For large std, this approximation may be inaccurate. For higher accuracy, consider:
        # - Exact propagation: var_log ≈ var / (1 + mean)**2 (delta-method variance formula)
        # - Numerical transformation: transform sample draws to log-space and compute mean/variance

        # Check if the small-relative-variance assumption holds
        # RU: Проверяем, выполняется ли предположение о малой относительной дисперсии
        # EN: Delta-method approximation validity check using class-level thresholds
        relative_variance = prior_std / (1 + prior_mean) if prior_mean > -1 else float("inf")
        var_ratio = (prior_std**2) / ((1 + prior_mean) ** 2) if prior_mean > -1 else float("inf")

        # Apply thresholds: switch to variance formula when approximation assumptions violated
        if (
            relative_variance > self.RELATIVE_VARIANCE_THRESHOLD
            or var_ratio > self.VAR_RATIO_THRESHOLD
        ):
            # Assumption violated: use more accurate delta-method variance formula
            logger.warning(
                f"Delta-method approximation assumption violated for category '{category}': "
                f"relative_variance={relative_variance:.6f}, var_ratio={var_ratio:.6f}, "
                f"prior_mean={prior_mean:.6f}, prior_std={prior_std:.6f}. "
                f"Switching to delta-method variance formula for improved accuracy."
            )
            # Use delta-method variance formula: var_log ≈ prior_std**2 / (1 + prior_mean)**2
            var_log = var_ratio
            prior_log_std = math.sqrt(var_log) if var_log > 0 else self.EPSILON
        else:
            # Assumption holds: use first-order approximation
            prior_log_std = prior_std / (1 + prior_mean)

        # Guard against zero/near-zero std before computing precision
        if prior_log_std <= 0:
            prior_log_std = self.EPSILON

        # Если есть данные, обновляем апостериорное распределение
        if data:
            # Вычисляем выборочное среднее (data is guaranteed non-empty here)
            sample_mean = sum(data) / len(data)
            try:
                sample_log_mean = math.log(1 + sample_mean)
            except ValueError as e:  # pragma: no cover - defensive guard after validation
                raise ValueError(
                    f"Math domain error computing log(1 + sample_mean) for category '{category}': "
                    f"sample_mean={sample_mean}. This should not occur after validation."
                ) from e

            # Calculate sample standard deviation
            if len(data) > 1:
                sample_variance = sum((x - sample_mean) ** 2 for x in data) / (len(data) - 1)
                # Ensure sample_variance is non-negative before sqrt
                if sample_variance < 0:  # pragma: no cover - variance cannot be negative after calc
                    raise ValueError(
                        f"Invalid sample_variance for category '{category}': {sample_variance}. "
                        f"Variance must be non-negative."
                    )
                try:
                    sample_std = math.sqrt(sample_variance)
                except ValueError as e:  # pragma: no cover - defensive guard
                    raise ValueError(
                        f"Math domain error computing sqrt(sample_variance) for category '{category}': "
                        f"sample_variance={sample_variance}. This should not occur after validation."
                    ) from e

                # First-order delta-method approximation: sample_log_std ≈ sample_std / (1 + sample_mean)
                # This is valid only for small relative variance (sample_std << 1 + sample_mean).
                # For large std, this approximation may be inaccurate. For higher accuracy, consider:
                # - Exact propagation: var_log ≈ var / (1 + mean)**2 (delta-method variance formula)
                # - Numerical transformation: transform sample draws to log-space and compute mean/variance
                sample_log_std = sample_std / (1 + sample_mean)
                # Guard against zero/near-zero std before computing precision
                if sample_log_std <= 0:
                    sample_log_std = self.EPSILON
            else:
                sample_log_std = prior_log_std

            # Байесовское обновление (упрощенная модель)
            # Используем взвешенное среднее априорного и выборочного среднего
            n = len(data)
            # Precision (обратная дисперсия)
            # prior_log_std and sample_log_std are already guarded against zero (>= EPSILON)
            prior_precision = 1 / (prior_log_std**2)
            sample_precision = n / (sample_log_std**2)

            # Guard against division by zero (should not occur after epsilon guards)
            total_precision = prior_precision + sample_precision
            if total_precision <= 0:  # pragma: no cover - guarded by epsilon above
                raise ValueError(
                    f"Invalid total precision for category '{category}': {total_precision}. "
                    f"This should not occur after epsilon guards."
                )

            # Апостериорное среднее (взвешенное среднее)
            posterior_log_mean = (
                prior_precision * prior_log_mean + sample_precision * sample_log_mean
            ) / total_precision
            # Апостериорное стандартное отклонение
            try:
                posterior_log_std = math.sqrt(1 / total_precision)
            except ValueError as e:
                raise ValueError(
                    f"Math domain error computing sqrt(1/total_precision) for category '{category}': "
                    f"total_precision={total_precision}. This should not occur after validation."
                ) from e
        else:
            # Используем априорное распределение, если данных нет
            posterior_log_mean = prior_log_mean
            posterior_log_std = prior_log_std

        # Преобразуем обратно в ROI
        try:
            expected_roi = math.exp(posterior_log_mean) - 1
        except OverflowError as e:  # pragma: no cover - defensive guard
            raise ValueError(
                f"Overflow error computing exp(posterior_log_mean) for category '{category}': "
                f"posterior_log_mean={posterior_log_mean}. Value too large."
            ) from e

        # Вычисляем 95% доверительный интервал (2 стандартных отклонения)
        z_score = 1.96  # 95% доверительный интервал
        lower_log = posterior_log_mean - z_score * posterior_log_std
        upper_log = posterior_log_mean + z_score * posterior_log_std

        try:
            credible_interval_lower = max(-1.0, math.exp(lower_log) - 1)  # ROI может быть до -100%
            credible_interval_upper = math.exp(upper_log) - 1
        except OverflowError:  # pragma: no cover - defensive guard for extreme values
            # On overflow, use clamped maximum to avoid misleading infinite ROI
            credible_interval_lower = (
                max(-1.0, math.exp(lower_log) - 1) if lower_log < 100 else -1.0
            )
            credible_interval_upper = self.MAX_CREDIBLE_UPPER_ROI
            logger.warning(
                f"Overflow computing credible interval for category '{category}': "
                f"upper_log={upper_log:.2f}. Clamping upper bound to {self.MAX_CREDIBLE_UPPER_ROI}."
            )

        # Clamp both bounds to avoid misleading astronomically large values and ensure ordering
        credible_interval_lower = max(
            -1.0, min(credible_interval_lower, self.MAX_CREDIBLE_UPPER_ROI)
        )
        credible_interval_upper = max(
            credible_interval_lower,
            min(credible_interval_upper, self.MAX_CREDIBLE_UPPER_ROI),
        )

        return ROIEstimate(
            category=category,
            expected_roi=expected_roi,
            credible_interval_lower=credible_interval_lower,
            credible_interval_upper=credible_interval_upper,
            time_horizon_months=time_horizon_months,
            assumptions=assumptions,
        )
