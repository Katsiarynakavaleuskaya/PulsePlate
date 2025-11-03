# 📋 TON Platform Integration - RFC

**Статус:** 🔬 R&D / Исследование
**Приоритет:** Низкий (не блокер релиза)
**Ответственный:** Solo developer

## 🎯 Цель исследования

Оценить возможность интеграции с TON (The Open Network) платформой для:
- Децентрализованного хостинга веб-приложений
- Хранилища данных (TON Storage)
- Децентрализованных доменов (TON Sites/Domains)

**⚠️ Scope Clarification:** TON Payments **не включены** в этот RFC. Интеграция ограничена только инфраструктурой (хостинг, хранилище, домены). Платежи будут обрабатываться через существующие платформы (App Store, Google Play).

## 🎯 Strategic Alignment

### Alignment with Product Objectives

**Primary Goals:**
- **Cost Optimization:** Reduce infrastructure costs from ~$5-20/month to ~$0.1-1/month (90%+ savings), enabling longer runway for solo developer
- **User Acquisition:** Access TON ecosystem (~500M+ users) as new distribution channel for health/nutrition features
- **Infrastructure Decentralization:** Reduce dependency on single hosting provider through decentralized infrastructure

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
- ✅ **Legal/Compliance:** Review regulatory risks (health data storage, GDPR/HIPAA compliance on decentralized infrastructure)
- ✅ **Engineering:** Confirm 2-week timebox is acceptable given current sprint commitments

## 📊 Текущий статус (2025)

### Что доступно сейчас:

1. **TON Blockchain** — стабильная сеть для смарт-контрактов
2. **TON Storage** — децентрализованное хранилище (в разработке)

### Что в разработке:

1. **TON Sites** — хостинг статических сайтов
2. **TON Domains** — децентрализованные домены (.ton)
3. **TON Cloud** — полноценная платформа для деплоя приложений (анонсирована, но детали уточняются)

## 💰 Ожидаемая стоимость

- **TON Sites** (статика): бесплатно или минимальная плата (~$0.01-0.1/месяц)
- **TON Storage** (данные): ~$0.01-0.05 за GB/месяц
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

### 🚫 Health Data Compliance (Phase 0 Blocker):

**TON Storage is explicitly marked as a Phase 0 blocker for identifiable health data** due to fundamental privacy and compliance concerns that require comprehensive research before any Phase 1 scoping.

**Critical Research Tasks (Required before Phase 1):**

1. **End-to-End Encryption & Off-Chain Storage Evaluation**
   - Evaluate feasibility and cost of implementing end-to-end encryption (E2EE) for all personal/health data flows using TON Storage
   - Assess architecture options for off-chain storage of encrypted health data (user metrics, nutrition logs, BMI history, body fat data)
   - Cost analysis: Compare E2EE + off-chain storage overhead vs. traditional encrypted database solutions
   - Technical feasibility: Validate that TON Storage can support E2EE key management and encrypted blob storage patterns
   - Deliverable: Technical feasibility report with cost estimates and architecture recommendations

2. **Transactional Requirements Validation**
   - Validate ACID transaction requirements (Atomicity, Consistency, Isolation, Durability) for health data operations
   - Assess multi-row atomicity needs (e.g., logging meal entry with multiple nutrients must be atomic)
   - Evaluate isolation levels required for concurrent user data updates
   - Determine rollback capabilities for failed transactions (critical for data integrity)
   - **Decision point:** Determine if a traditional DB layer (PostgreSQL/SQLite) is required alongside TON Storage for transactional health data
   - Deliverable: Transactional requirements analysis with recommendation on hybrid architecture vs. TON Storage-only approach

3. **GDPR Compliance Assessment**
   - **Immutability vs. Right to Erasure:** Evaluate conflict between blockchain immutability and GDPR Article 17 (Right to Erasure). TON Storage immutability may prevent complete data deletion required by GDPR
   - **Data Controller/Processor Roles:** Assess whether TON Storage architecture requires reclassification of data controller/processor roles under GDPR Article 24-28
   - **Mandatory DPIA:** Conduct Data Protection Impact Assessment (DPIA) as required by GDPR Article 35 for high-risk processing of health data
   - **Legal Review:** Mandate legal counsel review of TON Storage architecture from GDPR, CCPA, and HIPAA (if applicable) perspectives
   - Deliverable: GDPR/Privacy compliance report with DPIA documentation and legal recommendations

4. **Decision Gate Recommendation**
   - Recommend a formal decision gate that **prevents Phase 1 scoping** until:
     - All research findings from tasks 1-3 are documented and reviewed
     - A mitigation plan is approved (which may include: hybrid architecture with traditional DB for health data, migration away from TON Storage for personal data, or explicit no-go decision)
     - Legal/Compliance approval is obtained for the proposed architecture
   - Define escalation path if research findings indicate TON Storage is unsuitable for health data
   - Deliverable: Decision gate criteria document with approval checklist

**Research Timeline:** These health data compliance research tasks are estimated at 5-7 additional person-days, extending Phase 0 timeline to **2.5-3 person-weeks**.

### Регуляторные:

**⚠️ BLOCKING: Required decisions before Phase 0 research spike**

The following regulatory decisions must be made and documented before Phase 0 can begin:

#### 1. Health Data (PHI) Storage on TON Infrastructure

**Decision Required:** Will the app store Protected Health Information (PHI) or health data on TON Storage?

- **Option A: No PHI on TON Storage**
  - Only non-identifiable, aggregated, or public data stored on TON Storage
  - Health/nutrition data stored on traditional compliant infrastructure (HIPAA/GDPR compliant)
  - TON Storage used only for static assets, public data, or encrypted backups without keys

- **Option B: PHI Stored on TON Storage**
  - Personal health/nutrition data stored on TON Storage (even if encrypted)
  - Requires comprehensive compliance assessment for decentralized storage

**Current Proposal:** **[DECISION PENDING]** — Recommended: **Option A (No PHI on TON Storage)** to minimize HIPAA/GDPR compliance risks and reduce regulatory complexity. TON Storage would be used only for non-health data (static assets, public content).

#### 2. Target Jurisdictions

**Decision Required:** List all jurisdictions where the app will operate and where data may be stored:

- **Primary Markets:**
  - **[DECISION PENDING]** United States (specify states: all 50 states, or exclude certain states?)
  - **[DECISION PENDING]** European Union (all 27 member states, or specific countries?)
  - **[DECISION PENDING]** Other jurisdictions (UK, Canada, Australia, etc.)

- **Regulatory Impact by Jurisdiction:**
  - **United States:**
    - HIPAA compliance (if PHI collected/stored, regardless of storage location)
    - State privacy laws (CCPA, VCDPA, etc.)
    - Federal data protection requirements

  - **European Union:**
    - GDPR compliance (mandatory for EU data subjects)
    - Data localization requirements (if applicable)
    - Cross-border data transfer mechanisms

  - **Other Jurisdictions:**
    - **[DECISION PENDING]** Specific requirements for each target country (e.g., PIPEDA for Canada)

**Current Proposal:** **[DECISION PENDING]** — Target jurisdictions must be finalized and legal review completed before Phase 0.

#### 3. Required Regulatory Controls (Conditional on Decisions Above)

**Based on data storage model and jurisdictions selected, the following controls may be required:**

**Privacy & Health Data Compliance:**
- [ ] **[IF PHI STORED + US]** HIPAA compliance program (Business Associate Agreements, security controls, breach notification procedures)
- [ ] **[IF EU DATA SUBJECTS]** GDPR compliance (data processing agreements, privacy notices, data subject rights procedures)
- [ ] **[IF US STATES]** State privacy law compliance (CCPA, VCDPA, etc.)
- [ ] **[IF OTHER JURISDICTIONS]** Country-specific privacy law compliance

**Data Security Controls:**
- [ ] End-to-end encryption for all health data (if stored on TON)
- [ ] Access controls and audit logging
- [ ] Data retention and deletion policies
- [ ] Breach notification procedures

**Documentation & Procedures:**
- [ ] Written privacy and data protection policies
- [ ] Risk assessment documentation
- [ ] Data processing impact assessments (if GDPR applies)
- [ ] Training programs for relevant staff (if any)
- [ ] Audit and monitoring procedures

#### 4. Legal/Compliance Sign-off Required

**Before Phase 0 Research Spike:**
- [ ] Legal counsel review of data storage model decision (PHI on TON vs. traditional infrastructure)
- [ ] Legal counsel review of target jurisdictions
- [ ] Preliminary regulatory assessment (HIPAA/GDPR obligations for decentralized storage)
- [ ] Estimated compliance costs and timeline

**Failure to obtain these decisions before Phase 0 will result in research scope being limited to technical feasibility only, with health data storage excluded from testing until regulatory decisions are finalized.**

### Пользовательский опыт:

1. **Прозрачность:** Пользователи не заметят разницы — TON используется только для бэкенд-инфраструктуры
2. **Доступность:** Децентрализованный хостинг может улучшить доступность в регионах с ограниченным доступом
3. **Надежность:** Снижение зависимости от одного провайдера хостинга

## 📅 План исследования

### Phase 0: Research Spike (Timeboxed: 2.5-3 person-weeks)

**Scope:** Validate technical feasibility before committing to full Phase 1. **Health data compliance research is mandatory and blocks Phase 1 scoping until completion.**

**Tasks:**
- [ ] Review TON Developer Docs (2 days)
- [ ] Evaluate TON SDK for Python/FastAPI compatibility (3 days)
- [ ] Assess TON Sites/Cloud deployment capabilities (2 days)
- [ ] Test TON Storage integration (if applicable) (2 days)
- [ ] Legal/compliance preliminary review (1 day)
- [ ] **Health Data Compliance Research (5-7 days - Phase 0 Blocker):**
  - [ ] Task 1: End-to-End Encryption & Off-Chain Storage Evaluation (2 days)
  - [ ] Task 2: Transactional Requirements Validation (ACID, multi-row atomicity, isolation, rollback) (2 days)
  - [ ] Task 3: GDPR Compliance Assessment (DPIA, immutability vs. erasure, controller/processor roles) (2 days)
  - [ ] Task 4: Decision Gate Documentation (preventing Phase 1 until mitigation plan approved) (1 day)

**Success Criteria (Go):**
- ✅ TON SDK supports Python/FastAPI deployment architecture
- ✅ TON Sites/Cloud can host FastAPI backend (or clear migration path exists)
- ✅ TON Storage integration is feasible (if applicable) and meets requirements
- ✅ **Health Data Compliance: All 4 research tasks completed with documented findings**
- ✅ **Health Data Compliance: Mitigation plan approved (hybrid DB architecture or migration plan)**
- ✅ **Health Data Compliance: Legal/Compliance approval obtained for proposed architecture**
- ✅ **Health Data Compliance: DPIA completed and reviewed**
- ✅ No blocking legal/compliance issues identified
- ✅ Estimated engineering effort for Phase 1 < 4 person-weeks

**Failure Criteria (No-Go):**
- ❌ FastAPI deployment not supported (static sites only)
- ❌ TON Storage integration not feasible or incompatible with requirements
- ❌ Legal/compliance blockers (data storage/privacy restrictions)
- ❌ **Health Data Compliance: TON Storage determined unsuitable for health data with no viable mitigation**
- ❌ **Health Data Compliance: GDPR/Privacy compliance cannot be achieved with proposed architecture**
- ❌ **Health Data Compliance: Legal review rejects TON Storage for personal/health data**
- ❌ Estimated Phase 1 effort > 6 person-weeks

**Deliverable:** Research spike report with go/no-go recommendation and effort estimates.

### Фаза 1: Исследование (Q1 2025) - **Conditional on Phase 0 Go Decision + Health Data Compliance Approval**

**⚠️ Phase 1 cannot proceed until:**
- All Phase 0 health data compliance research tasks (1-4) are completed
- Mitigation plan is documented and approved (hybrid DB architecture or migration away from TON Storage for health data)
- Legal/Compliance approval obtained for proposed architecture
- DPIA completed and reviewed

**Estimated Effort:** 3-4 person-weeks

- [ ] Setup TON development environment (2 days)
- [ ] Deploy minimal FastAPI app to TON infrastructure (5 days)
- [ ] Test TON Storage integration (if applicable) (5 days)
- [ ] End-to-end testing: infrastructure deployment and data flow (3 days)
- [ ] Performance benchmarking vs. current Cloudflare solution (2 days)

**Success Criteria:**
- ✅ Базовый FastAPI endpoint работает на TON инфраструктуре с <200ms response time (p95)
- ✅ TON Storage (если используется) интегрирован и работает стабильно
- ✅ Инфраструктура развернута и функционирует корректно
- ✅ Uptime >99.5% в течение 1 недели тестирования
- ✅ Engineering effort не превысил 4 person-weeks

**Failure Criteria:**
- ❌ Response time >500ms (p95) или downtime >1%
- ❌ Storage/infrastructure failure rate >5% или frequent service interruptions
- ❌ Engineering effort превысил 6 person-weeks
- ❌ Critical bugs, требующие архитектурных изменений

**Go/No-Go Decision Gate:** После Phase 1 требуется review с оценкой:
- Technical KPIs: инфраструктурная стабильность, performance metrics
- Legal: финальный compliance review для production deployment
- Engineering: техническая готовность к Phase 2 (production-grade stability)

### Фаза 2: Пилот (Q2 2025, если Phase 1 успешна)

**Estimated Effort:** 4-6 person-weeks

- [ ] Production-grade staging deployment на TON (5 days)
- [ ] Полная интеграция TON Storage (если применимо) (7 days)
- [ ] Monitoring и alerting setup (5 days)
- [ ] Beta testing с ограниченной группой пользователей (2 weeks monitoring)
- [ ] Analytics dashboard для отслеживания TON infrastructure metrics (3 days)

**Success Criteria:**
- ✅ Staging deployment работает стабильно (uptime >99.9%, response time <200ms p95)
- ✅ TON инфраструктура функционирует без ошибок (failure rate <1%)
- ✅ Пользователи не испытывают проблем с доступностью (no user complaints about downtime)
- ✅ Beta users дают положительную обратную связь (NPS >40)
- ✅ Infrastructure KPIs: uptime и performance соответствуют или превышают текущую инфраструктуру

**Failure Criteria:**
- ❌ Uptime <99% или критичные performance issues
- ❌ Infrastructure failure rate >3% или frequent service interruptions
- ❌ User complaints >20% или significant service degradation
- ❌ Legal/compliance issues обнаружены в production
- ❌ Cost savings <50% или insufficient ROI vs. engineering investment

**Product KPI Thresholds for Go:**
- Infrastructure stability: uptime и performance соответствуют или превышают baseline
- User satisfaction: NPS не снижается vs. baseline
- Cost savings: инфраструктурные расходы снижены на >70%
- No user-facing degradation: все функции работают как прежде

### Фаза 3: Production (Q3 2025+, если Phase 2 успешна)

**Estimated Effort:** 6-8 person-weeks

- [ ] Миграция production на TON (или гибрид TON + Cloudflare) (10 days)
- [ ] Полная интеграция TON Storage (если применимо) (7 days)
- [ ] Monitoring, alerting, incident response setup (5 days)
- [ ] Documentation и runbooks для operations (3 days)

**Success Criteria:**
- ✅ Production migration завершена без downtime
- ✅ All critical metrics meet or exceed Phase 2 baselines
- ✅ Positive ROI: cost savings > engineering investment

## 🎯 Ожидаемые выгоды

### Если успешно:

1. **Экономия:** Значительно дешевле традиционного хостинга
2. **Децентрализация:** Независимость от одного провайдера
3. **Надежность:** Улучшенная доступность за счет децентрализованной инфраструктуры
4. **Инновации:** Опыт работы с децентрализованной инфраструктурой

### Если не успешно:

- Остаёмся на Cloudflare + VPS (проверенное решение)
- Минимальные потери времени на исследование

## 📚 Ресурсы

- **TON Docs**: <https://docs.ton.org>
- **TON Developer Portal**: <https://tondev.io>
- **TON SDK Python**: <https://github.com/toncenter/pytonlib>
- **TON Storage**: <https://docs.ton.org/develop/dapps/ton-storage>

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
- **Health Data Compliance:** TON Storage determined unsuitable for health data with no viable mitigation plan
- **Health Data Compliance:** GDPR/Privacy compliance cannot be achieved with proposed architecture
- **Health Data Compliance:** Legal review rejects TON Storage for personal/health data
- Any critical blocker (legal, technical, or compliance)
- Product KPIs fail to meet thresholds (Phase 1+)
- Engineering effort exceeds budget by >25%
- Risk-adjusted ROI projection is negative

### Legal/Compliance Review Checklist

**🚫 REQUIRED BEFORE PHASE 1 (Phase 0 Blocker - Health Data Compliance):**
- [ ] **Health Data Compliance Research Tasks Completed (See Phase 0 tasks):**
  - [ ] Task 1: End-to-End Encryption & Off-Chain Storage Evaluation completed
  - [ ] Task 2: Transactional Requirements Validation completed
  - [ ] Task 3: GDPR Compliance Assessment completed (including DPIA)
  - [ ] Task 4: Decision Gate Documentation completed
- [ ] **GDPR/Privacy Compliance:**
  - [ ] **DPIA (Data Protection Impact Assessment):** Conducted and reviewed as required by GDPR Article 35 for health data processing
  - [ ] **Right to Erasure:** Mitigation plan approved for GDPR Article 17 compliance (TON Storage immutability conflict resolved)
  - [ ] **Data Controller/Processor Roles:** Assessment completed per GDPR Articles 24-28
  - [ ] **Legal Review:** Legal counsel review of TON Storage architecture from GDPR, CCPA, and HIPAA perspectives completed
- [ ] **Mitigation Plan Approved:** Architecture decision documented (hybrid DB for health data OR migration away from TON Storage for personal data)
- [ ] **Health Data Architecture Approval:** Legal/Compliance sign-off obtained for proposed health data storage architecture

**Required before Phase 1 (General Compliance):**
- [ ] **Regulatory Assessment:** Data storage and infrastructure legality in target markets (US, EU, etc.)
- [ ] **Data Privacy (General):** TON Storage compliance with GDPR/CCPA for non-health data
- [ ] **Infrastructure Compliance:** Review of decentralized infrastructure compliance requirements

**Required before Phase 2 (Production):**
- [ ] **Legal Opinion:** Written assessment from legal counsel
- [ ] **Terms of Service:** Updated TOS to reflect TON infrastructure and health data handling
- [ ] **Privacy Policy:** Updated to reflect TON storage/decentralized infrastructure and health data architecture

**Legal Sign-off Required:** Legal/compliance owner must approve **health data compliance research findings and mitigation plan** before proceeding to Phase 1. Legal/compliance owner must also approve before proceeding to Phase 2.

### Product KPI Thresholds

**Phase 1 (Research):**
- Technical feasibility validated
- No product KPIs (research phase)

**Phase 2 (Pilot):**
- Infrastructure stability: uptime и performance соответствуют или превышают baseline
- User satisfaction (NPS): **>40** (no decline vs. baseline)
- Infrastructure cost savings: **>70%**
- No user-facing degradation: все функции работают как прежде

**Phase 3 (Production):**
- Infrastructure stability: uptime и performance соответствуют или превышают Phase 2 baselines
- ROI: Cost savings > total engineering investment
- User satisfaction: NPS maintained or improved
- No service degradation: все функции работают как прежде

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
