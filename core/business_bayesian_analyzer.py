#!/usr/bin/env python3
"""
Байесовский анализатор для бизнес-логики, монетизации и экономии средств.
Анализирует тесты с точки зрения бизнес-модели, доходности и оптимизации затрат.
"""

import re
import tokenize
from io import StringIO
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class BusinessCategory(Enum):
    """Категории бизнес-проблем."""

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
    """Типы бизнес-ошибок."""

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
    """Результат теста с точки зрения бизнеса."""

    test_name: str
    success: bool
    business_category: BusinessCategory
    error_type: Optional[BusinessErrorType] = None
    error_message: str = ""
    execution_time: float = 0.0
    file_path: str = ""
    revenue_impact: str = ""  # Описание влияния на доходы
    cost_impact: str = ""  # Описание влияния на затраты
    customer_impact: str = ""  # Описание влияния на клиентов
    optimization_potential: str = ""  # Потенциал оптимизации


class BusinessBayesianAnalyzer:
    """Байесовский анализатор для бизнес-логики."""

    def __init__(self) -> None:
        self.test_results: List[BusinessTestResult] = []
        self.business_knowledge_base = self._load_business_knowledge()
        self.monetization_strategies = self._load_monetization_strategies()
        self.cost_optimization_rules = self._load_cost_optimization_rules()

    def _load_business_knowledge(self) -> Dict[str, Any]:
        """Загружает базу знаний о бизнесе."""
        return {
            "revenue_streams": {
                "subscription": {
                    "monthly": {"price_range": (5, 50), "conversion_rate": 0.02},
                    "yearly": {"price_range": (50, 500), "conversion_rate": 0.05},
                    "lifetime": {"price_range": (100, 1000), "conversion_rate": 0.01},
                },
                "freemium": {
                    "free_tier": {"conversion_rate": 0.15},
                    "premium_tier": {"price_range": (10, 100), "conversion_rate": 0.08},
                },
                "usage_based": {
                    "per_request": {"price_range": (0.01, 1.0), "conversion_rate": 0.1},
                    "per_storage": {"price_range": (0.1, 10.0), "conversion_rate": 0.05},
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

    def _load_monetization_strategies(self) -> Dict[str, Any]:
        """Загружает стратегии монетизации."""
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

    def _load_cost_optimization_rules(self) -> Dict[str, Any]:
        """Загружает правила оптимизации затрат."""
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

    def analyze_business_logic(self, test_code: str, test_name: str) -> List[BusinessTestResult]:
        """Анализирует бизнес-логику в тестах."""
        results: List[BusinessTestResult] = []

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

    def _analyze_monetization(self, code: str, test_name: str) -> List[BusinessTestResult]:
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

                    # Проверка на разумность цены
                    if price < 1.0:
                        results.append(
                            BusinessTestResult(
                                test_name=test_name,
                                success=False,
                                business_category=BusinessCategory.MONETIZATION,
                                error_type=BusinessErrorType.PRICING_INEFFICIENCY,
                                error_message=f"Слишком низкая цена: ${price}",
                                revenue_impact="Потеря потенциального дохода",
                                cost_impact="Не покрывает операционные расходы",
                                optimization_potential="Увеличить цену до рыночного уровня",
                            )
                        )
                    elif price > 1000.0:
                        results.append(
                            BusinessTestResult(
                                test_name=test_name,
                                success=False,
                                business_category=BusinessCategory.MONETIZATION,
                                error_type=BusinessErrorType.PRICING_INEFFICIENCY,
                                error_message=f"Слишком высокая цена: ${price}",
                                revenue_impact="Снижение конверсии",
                                customer_impact="Отпугивание клиентов",
                                optimization_potential="Снизить цену или добавить ценностное предложение",
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

    def _analyze_customer_acquisition(self, code: str, test_name: str) -> List[BusinessTestResult]:
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

    def _analyze_cost_optimization(self, code: str, test_name: str) -> List[BusinessTestResult]:
        """Анализирует возможности оптимизации затрат."""
        results = []

        # Поиск неэффективных операций
        inefficiency_patterns = [
            r"for\s+.*\s+in\s+.*:\s*for\s+.*\s+in\s+.*:",  # Вложенные циклы
            r"SELECT\s+\*\s+FROM",  # SELECT * запросы
            r"while\s+True:",  # Бесконечные циклы
            r"sleep\([0-9]+\)",  # Длительные задержки
        ]

        for pattern in inefficiency_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                results.append(
                    BusinessTestResult(
                        test_name=test_name,
                        success=False,
                        business_category=BusinessCategory.COST_OPTIMIZATION,
                        error_type=BusinessErrorType.OPERATIONAL_WASTE,
                        error_message="Неэффективная операция обнаружена",
                        cost_impact="Повышенное потребление ресурсов",
                        optimization_potential="Оптимизировать алгоритм или запрос",
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

    def _analyze_revenue_growth(self, code: str, test_name: str) -> List[BusinessTestResult]:
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

    def _analyze_customer_retention(self, code: str, test_name: str) -> List[BusinessTestResult]:
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

    def generate_cost_savings_recommendations(self) -> List[str]:
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

    def generate_revenue_optimization_recommendations(self) -> List[str]:
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

    def diagnose_business_issues(self) -> Dict[BusinessCategory, float]:
        """Диагностирует бизнес-проблемы."""
        if not self.test_results:
            return {}

        # Подсчитываем проблемы по категориям
        category_counts: Dict[BusinessCategory, int] = {}
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

    def calculate_roi_potential(self) -> Dict[str, float]:
        """Вычисляет потенциал ROI для различных оптимизаций."""
        issues = self.diagnose_business_issues()

        roi_potential = {}

        # Потенциал ROI для каждой категории
        if BusinessCategory.COST_OPTIMIZATION in issues:
            roi_potential["cost_optimization"] = 0.3  # 30% экономии затрат

        if BusinessCategory.MONETIZATION in issues:
            roi_potential["monetization"] = 0.4  # 40% роста доходов

        if BusinessCategory.CUSTOMER_ACQUISITION in issues:
            roi_potential["customer_acquisition"] = 0.25  # 25% роста конверсии

        if BusinessCategory.USER_RETENTION in issues:
            roi_potential["user_retention"] = 0.35  # 35% роста LTV

        return roi_potential
