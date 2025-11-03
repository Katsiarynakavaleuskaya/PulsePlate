# 📋 TON Platform Integration - RFC

**Статус:** 🔬 R&D / Исследование
**Приоритет:** Низкий (не блокер релиза)
**Ответственный:** Solo developer

## 🎯 Цель исследования

Оценить возможность интеграции с TON (The Open Network) платформой для:
- Децентрализованного хостинга веб-приложений
- Платежей через TON (подписки/премиум функции)
- Хранилища данных (TON Storage)
- Децентрализованных доменов (TON Sites/Domains)

## 🎯 Strategic Alignment

### Alignment with Product Objectives

**Primary Goals:**
- **Cost Optimization:** Reduce infrastructure costs from ~$5-20/month to ~$0.1-1/month (90%+ savings), enabling longer runway for solo developer
- **User Acquisition:** Access TON ecosystem (~500M+ users) as new distribution channel for health/nutrition features
- **Payment Diversification:** Alternative payment method (TON) alongside existing subscription platforms to reduce platform dependency

**Mapped to User Outcomes:**
- **Lower pricing potential:** Cost savings could enable lower subscription prices or extended free tiers
- **Global accessibility:** Decentralized hosting could improve availability in regions with restricted access
- **Privacy-conscious users:** Decentralized infrastructure appeals to privacy-focused health app users

### Trade-offs & Deprioritization

**If TON research is pursued, the following core health features would be deprioritized/delayed:**

1. **Advanced Nutrition Analytics** (Q1-Q2 2025)
   - ML-powered meal recommendations based on user history
   - Personalized micronutrient gap analysis
   - Meal timing optimization algorithms

2. **Health Integrations Expansion** (Q1 2025)
   - Additional HealthKit data sync improvements
   - Wearables integration (Fitbit, Garmin)
   - Lab results import/analysis

3. **Community Features** (Q2 2025)
   - User meal sharing and recipe library
   - Progress tracking with social features
   - Nutritionist consultation marketplace

**Rationale:** TON research requires ~2-4 person-weeks of dedicated engineering time that would otherwise be allocated to core health features. This trade-off is only justified if TON integration can materially improve user acquisition or significantly reduce operational costs.

### Strategic Recommendation

**Proposed Approach:** Narrow scope to a **timeboxed research spike** (2 weeks max) with clear go/no-go criteria before Phase 1 commitment. This minimizes disruption to core roadmap while validating TON feasibility.

**Stakeholder Sign-off Required:**
- ✅ **Product Owner:** Approve deprioritization of health features listed above
- ✅ **Legal/Compliance:** Review regulatory risks (crypto payments, KYC/AML requirements)
- ✅ **Engineering:** Confirm 2-week timebox is acceptable given current sprint commitments

## 📊 Текущий статус (2025)

### Что доступно сейчас:

1. **TON Blockchain** — стабильная сеть для смарт-контрактов
2. **TON Payments** — интеграция платежей (SDK доступен)
3. **TON Storage** — децентрализованное хранилище (в разработке)

### Что в разработке:

1. **TON Sites** — хостинг статических сайтов
2. **TON Domains** — децентрализованные домены (.ton)
3. **TON Cloud** — полноценная платформа для деплоя приложений (анонсирована, но детали уточняются)

## 💰 Ожидаемая стоимость

- **TON Sites** (статика): бесплатно или минимальная плата (~$0.01-0.1/месяц)
- **TON Storage** (данные): ~$0.01-0.05 за GB/месяц
- **TON Payments**: комиссия ~0.5-1% от транзакции
- **TON Domains**: регистрация ~$10-50 (единоразово)

**Сравнение с текущим решением:**
- Cloudflare + VPS: ~$7/год (домен) + $5-20/месяц (хостинг)
- TON (если доступен): ~$0.1-1/месяц (децентрализованный хостинг)

## 🔍 Риски и ограничения

### Технические:

1. **Зрелость SDK:** TON SDK для веб-приложений может быть в ранней стадии
2. **FastAPI compatibility:** Неясно, поддерживается ли Python/FastAPI напрямую
3. **Database:** SQLite/PostgreSQL может потребовать адаптацию для TON Storage
4. **WebSockets:** Необходимо проверить поддержку для real-time функций

### Регуляторные:

1. **Криптовалюты:** Могут быть ограничения в некоторых юрисдикциях
2. **Платежи:** Нужны лицензии для приёма платежей в некоторых странах
3. **KYC/AML:** Для приёма платежей может потребоваться compliance

### Пользовательский опыт:

1. **Онбординг:** Пользователям нужно будет создать TON кошелёк (дополнительный барьер)
2. **Образовательный контент:** Нужны туториалы по TON кошелькам
3. **Криптовалюта:** Не все пользователи знакомы с TON/crypto

## 📅 План исследования

### Phase 0: Research Spike (Timeboxed: 2 person-weeks)

**Scope:** Validate technical feasibility before committing to full Phase 1.

**Tasks:**
- [ ] Review TON Developer Docs (2 days)
- [ ] Evaluate TON SDK for Python/FastAPI compatibility (3 days)
- [ ] Assess TON Sites/Cloud deployment capabilities (2 days)
- [ ] Test TON Payments SDK integration (2 days)
- [ ] Legal/compliance preliminary review (1 day)

**Success Criteria (Go):**
- ✅ TON SDK supports Python/FastAPI deployment architecture
- ✅ TON Sites/Cloud can host FastAPI backend (or clear migration path exists)
- ✅ TON Payments SDK has stable API for subscription payments
- ✅ No blocking legal/compliance issues identified
- ✅ Estimated engineering effort for Phase 1 < 4 person-weeks

**Failure Criteria (No-Go):**
- ❌ FastAPI deployment not supported (static sites only)
- ❌ TON Payments incompatible with subscription model
- ❌ Legal/compliance blockers (crypto payment restrictions)
- ❌ Estimated Phase 1 effort > 6 person-weeks

**Deliverable:** Research spike report with go/no-go recommendation and effort estimates.

### Фаза 1: Исследование (Q1 2025) - **Conditional on Phase 0 Go Decision**

**Estimated Effort:** 3-4 person-weeks

- [ ] Setup TON development environment (2 days)
- [ ] Deploy minimal FastAPI app to TON infrastructure (5 days)
- [ ] Implement TON Payments integration prototype (5 days)
- [ ] End-to-end testing: payment → subscription activation (3 days)
- [ ] Performance benchmarking vs. current Cloudflare solution (2 days)

**Success Criteria:**
- ✅ Базовый FastAPI endpoint работает на TON инфраструктуре с <200ms response time (p95)
- ✅ TON Payments успешно обрабатывает тестовую подписку (success rate >99%)
- ✅ Subscription activation происходит автоматически после payment confirmation
- ✅ Uptime >99.5% в течение 1 недели тестирования
- ✅ Engineering effort не превысил 4 person-weeks

**Failure Criteria:**
- ❌ Response time >500ms (p95) или downtime >1%
- ❌ Payment failure rate >5% или subscription activation delays >30s
- ❌ Engineering effort превысил 6 person-weeks
- ❌ Critical bugs, требующие архитектурных изменений

**Go/No-Go Decision Gate:** После Phase 1 требуется review с оценкой:
- Product KPIs: пользовательская конверсия в платежах, onboarding success rate
- Legal: финальный compliance review для production deployment
- Engineering: техническая готовность к Phase 2 (production-grade stability)

### Фаза 2: Пилот (Q2 2025, если Phase 1 успешна)

**Estimated Effort:** 4-6 person-weeks

- [ ] Production-grade staging deployment на TON (5 days)
- [ ] Полная интеграция TON Payments для premium функций (7 days)
- [ ] User onboarding flow с TON wallet creation guide (5 days)
- [ ] Beta testing с ограниченной группой пользователей (2 weeks monitoring)
- [ ] Analytics dashboard для отслеживания TON metrics (3 days)

**Success Criteria:**
- ✅ Staging deployment работает стабильно (uptime >99.9%, response time <200ms p95)
- ✅ TON Payments обрабатываются без ошибок (failure rate <1%)
- ✅ Пользователи успешно проходят онбординг (конверсия >50%, completion time <5 min)
- ✅ Beta users дают положительную обратную связь (NPS >40)
- ✅ Product KPIs: >10% пользователей выбирают TON payment option

**Failure Criteria:**
- ❌ Uptime <99% или критичные performance issues
- ❌ Payment failure rate >3% или frequent transaction delays
- ❌ Onboarding конверсия <30% или user complaints >20%
- ❌ Legal/compliance issues обнаружены в production
- ❌ Adoption rate TON payments <5% (insufficient ROI)

**Product KPI Thresholds for Go:**
- User acquisition: +15% new users from TON ecosystem
- Payment conversion: TON payments adoption rate >10% of total payments
- User satisfaction: NPS не снижается vs. baseline
- Cost savings: инфраструктурные расходы снижены на >70%

### Фаза 3: Production (Q3 2025+, если Phase 2 успешна)

**Estimated Effort:** 6-8 person-weeks

- [ ] Миграция production на TON (или гибрид TON + Cloudflare) (10 days)
- [ ] Полный переход на TON Payments (или dual payment system) (7 days)
- [ ] Маркетинг в TON комьюнити (ongoing)
- [ ] Monitoring, alerting, incident response setup (5 days)

**Success Criteria:**
- ✅ Production migration завершена без downtime
- ✅ All critical metrics meet or exceed Phase 2 baselines
- ✅ Positive ROI: cost savings + user acquisition gains > engineering investment

## 🎯 Ожидаемые выгоды

### Если успешно:

1. **Экономия:** Значительно дешевле традиционного хостинга
2. **Децентрализация:** Независимость от одного провайдера
3. **Новая аудитория:** TON комьюнити (миллионы пользователей)
4. **Инновации:** Первые в health/nutrition на TON

### Если не успешно:

- Остаёмся на Cloudflare + VPS (проверенное решение)
- Минимальные потери времени на исследование

## 📚 Ресурсы

- **TON Docs**: <https://docs.ton.org>
- **TON Developer Portal**: <https://tondev.io>
- **TON SDK Python**: <https://github.com/toncenter/pytonlib>
- **TON Payments**: <https://docs.ton.org/develop/dapps/ton-payments>

## 🚦 Risk-Adjusted Go/No-Go Decision Gate

### Decision Framework

**After each phase, evaluate using this decision matrix:**

| Criteria | Weight | Phase 0 | Phase 1 | Phase 2 |
|----------|--------|---------|---------|---------|
| **Technical Feasibility** | 30% | ✅/❌ | ✅/❌ | ✅/❌ |
| **Legal/Compliance** | 25% | ✅/❌ | ✅/❌ | ✅/❌ |
| **Product KPIs** | 25% | N/A | ✅/❌ | ✅/❌ |
| **Engineering Effort** | 20% | ✅/❌ | ✅/❌ | ✅/❌ |

**Go Decision Requirements:**
- All critical criteria (weighted score >80%) must be ✅
- Legal/compliance review must be ✅ (no blocking issues)
- Product KPIs must meet thresholds (if applicable for phase)
- Engineering effort must be within budgeted person-weeks

**No-Go Triggers:**
- Any critical blocker (legal, technical, or compliance)
- Product KPIs fail to meet thresholds (Phase 1+)
- Engineering effort exceeds budget by >25%
- Risk-adjusted ROI projection is negative

### Legal/Compliance Review Checklist

**Required before Phase 1:**
- [ ] **Regulatory Assessment:** Crypto payment acceptance legality in target markets (US, EU, etc.)
- [ ] **KYC/AML Requirements:** Determine if TON payments require KYC/AML compliance
- [ ] **Tax Implications:** Crypto payment reporting requirements
- [ ] **Platform Policies:** Review App Store/Google Play policies on crypto payments
- [ ] **Data Privacy:** TON Storage compliance with GDPR/CCPA

**Required before Phase 2 (Production):**
- [ ] **Legal Opinion:** Written assessment from legal counsel
- [ ] **Compliance Framework:** KYC/AML procedures documented (if required)
- [ ] **Terms of Service:** Updated TOS to include TON payment terms
- [ ] **Privacy Policy:** Updated to reflect TON storage/decentralized infrastructure

**Legal Sign-off Required:** Legal/compliance owner must approve before proceeding to Phase 2.

### Product KPI Thresholds

**Phase 1 (Research):**
- Technical feasibility validated
- No product KPIs (research phase)

**Phase 2 (Pilot):**
- User onboarding conversion: **>50%** (vs. baseline)
- TON payment adoption: **>10%** of total payments
- User satisfaction (NPS): **>40** (no decline vs. baseline)
- Infrastructure cost savings: **>70%**

**Phase 3 (Production):**
- User acquisition: **+15%** new users from TON ecosystem
- Payment conversion: **>15%** TON payments adoption
- ROI: Cost savings + acquisition gains > total engineering investment
- User satisfaction: NPS maintained or improved

### Escalation Path

**If No-Go decision is made:**
1. Document learnings in spike report
2. Re-evaluate in 6 months (TON platform maturity)
3. Consider alternative approaches (e.g., hybrid model)
4. Return engineering resources to core health features roadmap

**If Go decision is made:**
1. Update product roadmap with TON integration timeline
2. Communicate deprioritization of health features to stakeholders
3. Allocate engineering resources as per phase estimates
4. Set up monitoring and review cadence (bi-weekly during active phases)

## ✅ Decision Log

```text
**Текущее решение:**
- Основная инфраструктура: **Cloudflare + VPS** (стабильно, работает)
- TON: **Phase 0 Research Spike** (timeboxed 2 weeks, pending stakeholder sign-off)
- Переход на TON: **Conditional on Phase 0 Go decision, earliest Q2 2025** (после успешного пилота)

**Stakeholder Sign-off Status:**
- [ ] Product Owner: Approval for health features deprioritization
- [ ] Legal/Compliance: Preliminary regulatory review completed
- [ ] Engineering: 2-week timebox approved for Phase 0

**Обновление:**
- RFC обновлён с чётким strategic alignment, критериями успеха и decision gates
- Предложен narrowed scope (timeboxed spike) для минимизации рисков
- Добавлены effort estimates и KPI thresholds для каждой фазы
- Решения будут пересматриваться после Phase 0 research spike с обязательным stakeholder review
```
