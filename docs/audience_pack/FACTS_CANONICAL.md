# FACTS_CANONICAL

Дата фиксации фактов: 19 февраля 2026 года (`America/New_York`)

## 1) Что Это За Проект
PulsePlate — wellness-платформа про питание и повседневные привычки. Продукт соединяет:
- расчет и интерпретацию метрик тела,
- персональные рекомендации,
- практику на каждый день (план, shopping list, экспорт),
- web и iOS клиенты на едином backend API.

## 2) Ключевые Модули И Связи

### Backend
- `app/main.py` — канонический вход FastAPI, реэкспорт приложения из `legacy_app.py`, регистрация метрик и pro-контрактов.
- `legacy_app.py` — слой совместимости и основной runtime-контур для многих legacy endpoint-ов.
- `app/routers/*.py` — сегментированные роуты (`bmi`, `pro`, `vip`, `shoplist`, `users`, `catalog`, `export`).
- `app/middleware/api_tiers.py` — контроль доступов по подписке (`FREE`, `PRO`, `VIP`) и API keys.

### Domain/Core
- `core/bmi/engine.py` — единый канонический BMI engine.
- `core/bmi/risk.py` — каноничные пороги риска (waist/WHR/BMI).
- `core/menu_engine.py`, `core/plate.py`, `core/recommendations.py` — логика меню/тарелки/рекомендаций.
- `core/food_sources/*` + `core/food_merge.py` — data-pipeline для food базы (USDA/OFF).

### Security
- `app/security/rate_limit.py` — rate limiting и OpenAPI-контракты для 429.
- `app/security/llm_monthly_quota.py` — месячная hard quota для LLM endpoint-ов до provider call.

### Clients
- `frontend/` (React + TypeScript + Vite): thin HTTP adapter, OpenAPI-generated types, guard against business logic drift.
- `ios/` (SwiftUI): thin client policy, запрет BMI-вычислений на клиенте, transport-only networking через API/HTTP client.

### QA/CI
- `tests/` — guard tests и функциональные тесты.
- `Makefile` — единые quality gates (`make verify`).
- `pre-commit` — локальные хуки до push.

## 3) Продуктовая Модель
- `FREE` — базовые функции и onboarding-value.
- `PRO` — расширенная персонализация и pro-endpoint-ы.
- `VIP` — премиальные endpoint-ы и самые ресурсоемкие сценарии.

Схема роста ценности: `ориентир -> персонализация -> ежедневная операционная поддержка`.

## 4) Архитектурная Карта (Упрощенно)
```text
Web (React)        iOS (SwiftUI)
      |                 |
      +------ HTTP / /api/v1 ------+
                                    |
                          FastAPI app (app/main.py)
                                    |
            +-----------------------+----------------------+
            |                                              |
      Routers / Middleware                          Security Layer
  (bmi/pro/vip/export/users...)       (tier checks, rate limits, quota)
            |                                              |
            +-----------------------+----------------------+
                                    |
                                core/* domain
                     (BMI engine, risk, menu, plate, food db)
                                    |
                              DB + external datasets
                           (SQLite/Postgres, USDA/OFF)
```

## 5) Используемые Программы/Технологии
- Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic.
- React, TypeScript, Vite (web).
- SwiftUI/Xcode (iOS).
- Pytest, Ruff, MyPy, pre-commit.
- Docker/GitHub Actions.
- SlowAPI (rate limiting when enabled).

## 6) Безопасность И Ограничения
- Tier-доступы через `X-API-Key` и middleware-проверки.
- Rate limits на дорогие endpoint-ы (LLM/exports).
- LLM monthly quota enforced server-side до provider call.
- Privacy-подход: псевдонимизация client key для лимитов, ограничение чувствительных логов.
- `/health` и `/ready` семантически разделены: liveness vs readiness.

## 7) Инварианты Проекта (High-Level)
- Нельзя дублировать BMI-математику вне `core/bmi/*`.
- Клиенты web/iOS должны быть thin adapters (без доменной бизнес-логики).
- `legacy_app.py` — compatibility layer; новые инфраструктурные регистрации должны быть в bootstrap/app entrypoints.
- PR readiness не объявляется без прохода локальных quality gates.

## 8) Для Кого Этот Файл
Используйте этот файл как "единый факт-слой" перед подготовкой:
- investor deck,
- PRD/roadmap,
- onboarding,
- контент-маркетинга,
- sales scripts,
- технической документации.

## Security Notes
- Запрещены external claims, которые выходят за wellness-позиционирование.
- Все публичные обещания должны быть проверяемы через текущую реализацию в repo.
- Любые новые дорогие endpoint-ы должны сразу включать лимиты и тесты на 429.

## Marketing & GTM
- Сообщение для рынка должно опираться на реальные модульные возможности из этого файла.
- Для вывода в канал используйте правило: capability -> user value -> proof artifact.
- Не выводите в промо материалы функции, которые есть только в планах.
