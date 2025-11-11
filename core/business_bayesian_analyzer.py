#!/usr/bin/env python3
"""
Bayesian analyzer for business logic, monetization, and cost optimization.

RU: Байесовский анализатор для бизнес-логики, монетизации и экономии средств.
EN: Analyzes tests from the perspective of business model, revenue, and cost optimization.
"""

import ast
import math
import re
import tokenize
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Any


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

    def __init__(
        self,
        low_price_threshold: float | None = None,
        high_price_threshold: float | None = None,
        domain: str = "nutrition",
        business_knowledge: dict[str, Any] | None = None,
        monetization_strategies: dict[str, Any] | None = None,
        cost_optimization_rules: dict[str, Any] | None = None,
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
        """
        self.test_results: list[BusinessTestResult] = []
        # Load business knowledge: injected config takes priority over file loading
        self.business_knowledge_base = (
            business_knowledge
            if business_knowledge is not None
            else self._load_business_knowledge()
        )
        self.monetization_strategies = (
            monetization_strategies
            if monetization_strategies is not None
            else self._load_monetization_strategies()
        )
        self.cost_optimization_rules = (
            cost_optimization_rules
            if cost_optimization_rules is not None
            else self._load_cost_optimization_rules()
        )

        # Configure price thresholds
        if low_price_threshold is not None:
            self.low_price_threshold = low_price_threshold
        elif domain in ("nutrition", "health"):
            self.low_price_threshold = self.NUTRITION_LOW_PRICE_THRESHOLD
        else:
            self.low_price_threshold = self.DEFAULT_LOW_PRICE_THRESHOLD

        if high_price_threshold is not None:
            self.high_price_threshold = high_price_threshold
        elif domain in ("nutrition", "health"):
            self.high_price_threshold = self.NUTRITION_HIGH_PRICE_THRESHOLD
        else:
            self.high_price_threshold = self.DEFAULT_HIGH_PRICE_THRESHOLD

    def analyze(self, test_code: str, test_name: str) -> list[BusinessTestResult]:
        """Public entry point for business logic analysis.
        Публичная точка входа для анализа бизнес-логики.
        """
        return self.analyze_business_logic(test_code, test_name)

    def _load_business_knowledge(self) -> dict[str, Any]:
        """Load business knowledge base from config file or return defaults.

        RU: Загружает базу знаний о бизнесе из конфигурационного файла или возвращает значения по умолчанию.
        EN: Loads business knowledge base from config/business_knowledge.yaml or returns hardcoded defaults.

        Note: Return type annotation already present (-> dict[str, Any]).
        """
        config_path = Path(__file__).parent.parent / "config" / "business_knowledge.yaml"
        if config_path.exists():
            try:
                try:
                    import yaml  # type: ignore[import-untyped]

                    yaml_available = True
                except ImportError:
                    # PyYAML not installed, fallback to defaults
                    yaml_available = False
                if yaml_available:
                    with open(config_path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
            except Exception:  # nosec B110 - intentional fallback to defaults
                # Fallback to defaults on any error (file not found, parse error, etc.)
                pass

        # Fallback defaults (same as original hardcoded values)
        return {
            "revenue_streams": {
                "subscription": {
                    "monthly": {"price_range": [5, 50], "conversion_rate": 0.02},
                    "yearly": {"price_range": [50, 500], "conversion_rate": 0.05},
                    "lifetime": {"price_range": [100, 1000], "conversion_rate": 0.01},
                },
                "freemium": {
                    "free_tier": {"conversion_rate": 0.15},
                    "premium_tier": {"price_range": [10, 100], "conversion_rate": 0.08},
                },
                "usage_based": {
                    "per_request": {"price_range": [0.01, 1.0], "conversion_rate": 0.1},
                    "per_storage": {"price_range": [0.1, 10.0], "conversion_rate": 0.05},
                },
            },
            "customer_segments": {
                "individual": {"ltv": 200, "churn_rate": 0.05},
                "professional": {"ltv": 1000, "churn_rate": 0.02},
                "enterprise": {"ltv": 10000, "churn_rate": 0.01},
            },
            "cost_centers": {
                "infrastructure": {"aws": 0.3, "gcp": 0.25, "azure": 0.2},
                "development": {"salaries": 0.4, "tools": 0.1},
                "marketing": {"ads": 0.2, "content": 0.1},
                "operations": {"support": 0.15, "legal": 0.05},
            },
        }

    def _load_monetization_strategies(self) -> dict[str, Any]:
        """Load monetization strategies from config file or return defaults.

        RU: Загружает стратегии монетизации из конфигурационного файла или возвращает значения по умолчанию.
        EN: Loads monetization strategies from config/monetization_strategies.yaml or returns hardcoded defaults.
        """
        config_path = Path(__file__).parent.parent / "config" / "monetization_strategies.yaml"
        if config_path.exists():
            try:
                try:
                    import yaml

                    yaml_available = True
                except ImportError:
                    # PyYAML not installed, fallback to defaults
                    yaml_available = False
                if yaml_available:
                    with open(config_path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
            except Exception:  # nosec B110 - intentional fallback to defaults
                # Fallback to defaults on any error
                pass

        # Fallback defaults (same as original hardcoded values)
        return {
            "pricing_models": {
                "tiered": "Многоуровневая модель с разными функциями",
                "freemium": "Бесплатный базовый + платный премиум",
                "usage_based": "Оплата по использованию",
                "subscription": "Подписочная модель",
                "one_time": "Единоразовая покупка",
            },
            "conversion_tactics": {
                "trial_period": "Бесплатный пробный период",
                "discount_codes": "Скидочные коды",
                "referral_program": "Реферальная программа",
                "bundling": "Пакетные предложения",
                "upselling": "Продажа дополнительных услуг",
            },
            "retention_strategies": {
                "onboarding": "Улучшенная адаптация новых пользователей",
                "feature_usage": "Анализ использования функций",
                "engagement": "Повышение вовлеченности",
                "support": "Качественная поддержка",
                "feedback": "Обратная связь с пользователями",
            },
        }

    def _load_cost_optimization_rules(self) -> dict[str, Any]:
        """Load cost optimization rules from config file or return defaults.

        RU: Загружает правила оптимизации затрат из конфигурационного файла или возвращает значения по умолчанию.
        EN: Loads cost optimization rules from config/cost_optimization_rules.yaml or returns hardcoded defaults.
        """
        config_path = Path(__file__).parent.parent / "config" / "cost_optimization_rules.yaml"
        if config_path.exists():
            try:
                try:
                    import yaml

                    yaml_available = True
                except ImportError:
                    # PyYAML not installed, fallback to defaults
                    yaml_available = False
                if yaml_available:
                    with open(config_path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
            except Exception:  # nosec B110 - intentional fallback to defaults
                # Fallback to defaults on any error
                pass

        # Fallback defaults (same as original hardcoded values)
        return {
            "infrastructure": {
                "auto_scaling": "Автоматическое масштабирование ресурсов",
                "spot_instances": "Использование spot-инстансов для некритичных задач",
                "reserved_instances": "Резервирование инстансов для долгосрочного использования",
                "cdn_optimization": "Оптимизация CDN для снижения трафика",
                "caching": "Кэширование для снижения нагрузки на БД",
            },
            "development": {
                "code_reuse": "Переиспользование кода",
                "automation": "Автоматизация процессов",
                "testing": "Эффективное тестирование",
                "monitoring": "Проактивный мониторинг",
                "documentation": "Хорошая документация",
            },
            "operations": {
                "process_automation": "Автоматизация операционных процессов",
                "outsourcing": "Аутсорсинг некритичных функций",
                "lean_operations": "Бережливые операции",
                "vendor_negotiation": "Переговоры с поставщиками",
                "resource_sharing": "Совместное использование ресурсов",
            },
        }

    def analyze_business_logic(self, test_code: str, test_name: str) -> list[BusinessTestResult]:
        """Анализирует бизнес-логику в тестах."""
        results: list[BusinessTestResult] = []

        # Анализ монетизации
        monetization_issues = self._analyze_monetization(test_code, test_name)
        results.extend(monetization_issues)

        # Анализ привлечения клиентов
        acquisition_issues = self._analyze_customer_acquisition(test_code, test_name)
        results.extend(acquisition_issues)

        # Анализ оптимизации затрат
        cost_issues = self._analyze_cost_optimization(test_code, test_name)
        results.extend(cost_issues)

        # Анализ роста доходов
        revenue_issues = self._analyze_revenue_growth(test_code, test_name)
        results.extend(revenue_issues)

        # Анализ удержания клиентов
        retention_issues = self._analyze_customer_retention(test_code, test_name)
        results.extend(retention_issues)

        # Persist results for downstream diagnostics
        self.test_results.extend(results)
        return results

    def _remove_comments(self, code: str) -> str:
        """Remove inline comments while preserving '#' inside string literals."""
        try:
            tokens = []
            for token in tokenize.generate_tokens(StringIO(code).readline):
                if token.type != tokenize.COMMENT:
                    tokens.append(token)
            result = tokenize.untokenize(tokens)
            # tokenize.untokenize returns bytes in some Python versions, ensure str
            return result.decode("utf-8") if isinstance(result, bytes) else str(result)
        except (tokenize.TokenError, SyntaxError):
            # Fallback to simple regex if tokenization fails (e.g., incomplete code)
            # Only strip comments that start a line or are preceded by whitespace
            return re.sub(r"(^|\s)#.*", r"\1", code, flags=re.MULTILINE)

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
            matches = re.finditer(pattern, code, re.IGNORECASE)
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
                                    f"${self.low_price_threshold:.2f} приводит к потере дохода"
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
        if (
            "payment" in code_no_comments.lower() or "billing" in code_no_comments.lower()
        ) and not any(
            keyword in code_no_comments.lower()
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
            if not any(
                keyword in code.lower() for keyword in ["validate", "check", "verify", "email"]
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
            if not any(
                keyword in code.lower() for keyword in ["onboard", "tutorial", "guide", "welcome"]
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
            # AST-based detection: check for real nested For loops
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    # Check if this for loop contains nested for loops in its body
                    nested_loops = [child for child in node.body if isinstance(child, ast.For)]
                    for inner in nested_loops:
                        # Extract source of inner loop
                        loop_body_src = ast.get_source_segment(code, inner) or ""
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
        else:
            # Fallback to regex for broken code (keeps existing behavior)
            nested_loop_pattern = (
                r"for\s+(\w+)\s+in\s+[^:]+:\s*(?:[^\n]*\n)*?\s*for\s+(\w+)\s+in\s+[^:]+:"
            )
            nested_matches = re.finditer(nested_loop_pattern, code, re.MULTILINE)
            for match in nested_matches:
                loop_start = match.end()
                lines_after = code[loop_start:].split("\n")[:20]
                loop_body = "\n".join(lines_after)
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

        # 2. SELECT *: only flag when not in test/fixture context
        select_star_pattern = r"SELECT\s+\*\s+FROM"
        if re.search(select_star_pattern, code, re.IGNORECASE):
            # Skip if test_name starts with "test_" or code contains "fixture"
            if not test_name.lower().startswith("test_") and "fixture" not in code.lower():
                results.append(
                    BusinessTestResult(
                        test_name=test_name,
                        success=False,
                        business_category=BusinessCategory.COST_OPTIMIZATION,
                        error_type=BusinessErrorType.OPERATIONAL_WASTE,
                        error_message="SELECT * запрос без контекста теста/фикстуры",
                        cost_impact="Избыточная загрузка данных",
                        optimization_potential="Указать конкретные колонки вместо SELECT *",
                    )
                )

        # 3. while True: only flag when no break/return in loop body
        while_true_pattern = r"while\s+True\s*:"
        while_matches = re.finditer(while_true_pattern, code, re.IGNORECASE)
        for match in while_matches:
            # Extract loop body using DOTALL to match across lines
            loop_start = match.end()
            # Find the body (next 50 lines or until dedent)
            remaining_code = code[loop_start:]
            lines_after = remaining_code.split("\n")[:50]
            loop_body = "\n".join(lines_after)
            # Check if there's a break or return in the loop body
            if not re.search(r"\b(break|return)\b", loop_body, re.DOTALL):
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
        # Match sleep( with any argument, but skip common retry patterns
        sleep_pattern = r"sleep\s*\([^)]+\)"
        sleep_matches = re.finditer(sleep_pattern, code, re.IGNORECASE)
        for match in sleep_matches:
            # Check context: skip if it's part of retry/backoff logic
            context_start = max(0, match.start() - 100)
            context_end = min(len(code), match.end() + 100)
            context = code[context_start:context_end].lower()
            # Skip common retry/backoff patterns
            retry_keywords = ["retry", "backoff", "exponential", "jitter", "wait", "delay"]
            if not any(keyword in context for keyword in retry_keywords):
                results.append(
                    BusinessTestResult(
                        test_name=test_name,
                        success=False,
                        business_category=BusinessCategory.COST_OPTIMIZATION,
                        error_type=BusinessErrorType.OPERATIONAL_WASTE,
                        error_message=f"Использование sleep() без контекста retry/backoff: {match.group(0)}",
                        cost_impact="Блокирующие задержки",
                        optimization_potential="Использовать асинхронные операции или retry-логику",
                    )
                )

        # Проверка на отсутствие кэширования
        if any(
            keyword in code.lower() for keyword in ["database", "api", "request", "fetch"]
        ) and not any(
            keyword in code.lower() for keyword in ["cache", "memoize", "redis", "memory"]
        ):
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

        # Поиск упоминаний аналитики и метрик
        analytics_keywords = ["analytics", "metrics", "tracking", "conversion", "revenue"]
        analytics_mentions = [kw for kw in analytics_keywords if kw in code.lower()]

        if analytics_mentions and not any(
            keyword in code.lower() for keyword in ["ab_test", "experiment", "variant", "control"]
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
            "user" in code.lower()
            and "personal" in code.lower()
            and not any(
                keyword in code.lower()
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

        if communication_mentions and not any(
            keyword in code.lower() for keyword in ["segment", "group", "cohort", "tier"]
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
        if ("feedback" in code.lower() or "review" in code.lower()) and not any(
            keyword in code.lower() for keyword in ["analyze", "process", "respond", "action"]
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

        # Вычисляем вероятности
        probabilities = {}
        for category, count in category_counts.items():
            probabilities[category] = count / total_issues if total_issues > 0 else 0.0

        return probabilities

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
        # В реальном сценарии здесь можно использовать исторические данные проекта
        for result in self.test_results:
            if not result.success:
                category_key = result.business_category.value
                # Оцениваем benefit/cost на основе типа ошибки
                # Это упрощенная модель; в реальности нужны фактические метрики
                if category_key not in category_data:
                    category_data[category_key] = []
                # Примерная оценка: используем консервативные значения
                category_data[category_key].append(0.1)  # Минимальный ROI для проблемы

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
        invalid_data = [x for x in data if x <= -1]
        if invalid_data:
            raise ValueError(
                f"Invalid data values for category '{category}': {invalid_data}. "
                f"All ROI values must be > -1 (ROI > -100%) to allow log transformation."
            )

        # Epsilon for guarding against zero/near-zero standard deviations
        EPSILON = 1e-12

        # Преобразуем ROI в log-returns для нормального распределения
        # ROI = (benefit - cost) / cost, поэтому log_return = log(1 + ROI)
        try:
            prior_log_mean = math.log(1 + prior_mean)
        except ValueError as e:
            raise ValueError(
                f"Math domain error computing log(1 + prior_mean) for category '{category}': "
                f"prior_mean={prior_mean}. This should not occur after validation."
            ) from e

        # First-order delta-method approximation: prior_log_std ≈ prior_std / (1 + prior_mean)
        # This is valid only for small relative variance (prior_std << 1 + prior_mean).
        # For large std, this approximation may be inaccurate. For higher accuracy, consider:
        # - Exact propagation: var_log ≈ var / (1 + mean)**2 (delta-method variance formula)
        # - Numerical transformation: transform sample draws to log-space and compute mean/variance
        prior_log_std = prior_std / (1 + prior_mean)
        # Guard against zero/near-zero std before computing precision
        if prior_log_std <= 0:
            prior_log_std = EPSILON

        # Если есть данные, обновляем апостериорное распределение
        if data:
            # Вычисляем выборочное среднее и стандартное отклонение
            sample_mean = sum(data) / len(data) if data else prior_mean
            try:
                sample_log_mean = math.log(1 + sample_mean)
            except ValueError as e:
                raise ValueError(
                    f"Math domain error computing log(1 + sample_mean) for category '{category}': "
                    f"sample_mean={sample_mean}. This should not occur after validation."
                ) from e

            # Calculate sample standard deviation
            if len(data) > 1:
                sample_variance = sum((x - sample_mean) ** 2 for x in data) / (len(data) - 1)
                # Ensure sample_variance is non-negative before sqrt
                if sample_variance < 0:
                    raise ValueError(
                        f"Invalid sample_variance for category '{category}': {sample_variance}. "
                        f"Variance must be non-negative."
                    )
                try:
                    sample_std = math.sqrt(sample_variance)
                except ValueError as e:
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
                    sample_log_std = EPSILON
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
            if total_precision <= 0:
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
        except OverflowError as e:
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
        except OverflowError as e:
            raise ValueError(
                f"Overflow error computing credible interval for category '{category}': "
                f"lower_log={lower_log}, upper_log={upper_log}. Values too large."
            ) from e

        return ROIEstimate(
            category=category,
            expected_roi=expected_roi,
            credible_interval_lower=credible_interval_lower,
            credible_interval_upper=credible_interval_upper,
            time_horizon_months=time_horizon_months,
            assumptions=assumptions,
        )
