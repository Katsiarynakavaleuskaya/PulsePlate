# Privacy Policy

**Status:** Canonical legal document
**Last updated:** 2026-03-08
**Policy version:** `2026-03-08.eu-first.v1`
**Scope:** All product tiers (FREE / PRO / VIP)
**Markets:** CIS / EU / US
**Positioning:** Consumer wellness product, not a clinical system

---

## 🇷🇺 RU Version

### Какие данные мы собираем

**Данные аккаунта и доступа:**

- Email и связанные данные аккаунта, если функция аккаунтов включена
- Технические идентификаторы доступа, связанные с API-ключами и entitlement-проверками

**Псевдонимные идентификаторы безопасности:**

- Хешированные и усечённые client fingerprints для rate limiting, abuse prevention и request correlation
- Эти идентификаторы рассматриваются как псевдонимные данные и не используются как публичный user profile

**Wellness и AI-артефакты:**

- Wellness-профиль и вычисления могут обрабатываться в request scope
- Некоторые прямые user-bound артефакты могут сохраняться в минимизированном виде:
  - feedback on AI/RAG responses
  - user knowledge/personalization artifacts
  - signed audit metadata for privileged AI actions

### Что мы не обещаем

- Мы **не обещаем**, что весь продукт работает без хранения данных
- Мы **не позиционируем** продукт как HIPAA-ready, clinical-grade или Part 2 compliant
- Мы **не используем** текущий wellness runtime для клинических записей, crisis workflows или SUD records

### AI / Automated Analysis

Некоторые поверхности выполняют **automated wellness analysis**:

- BMI / body-fat / nutrition-target calculations
- nutrition planning and weekly-plan generation
- AI insight surfaces (`/insight`, `/api/v1/insight`, `/api/v1/pro/cbt/insight`)

Для таких поверхностей действуют общие правила:

- результат носит wellness / educational характер
- не предназначен для emergency use
- не должен использоваться как единственное основание для treatment decisions
- при признаках клинического риска нужен переход к qualified professional support

### Внешние и self-hosted processors

При включении AI-функций запрос может обрабатываться:

- локальным/runtime processing PulsePlate
- self-hosted provider (например, Ollama-compatible)
- external provider family (например, xAI/Grok, OpenAI-compatible, Anthropic-compatible, Pico)

Конкретный processor зависит от deployment configuration. Retention и downstream processing у внешних processors регулируются их собственными условиями и настройками развертывания.

### Хранение и удаление

- Псевдонимные security identifiers удаляются по retention policy
- Direct-user SQL artifacts могут быть экспортированы или удалены через внутренний support-led DSAR workflow
- Audit envelopes и indirect security artifacts не считаются public self-service artifacts и живут по retention/security policy

### Ваши права

Если на вас распространяется GDPR или аналогичные режимы, вы можете запросить:

- доступ к direct-user artifacts
- удаление direct-user artifacts, где это технически и юридически поддерживается
- исправление неточных account records
- прекращение использования AI surfaces для новых automated-analysis requests

### Связанные документы

- `GET /privacy` — runtime JSON contract
- `GET /terms` — runtime legal publication for service scope and acceptable use
- `docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`
- `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
- `docs/compliance/DSAR_AND_DELETION_MAP.md`
- `docs/legal/Disclaimer.md`

---

## 🇬🇧 EN Version

### What Data We Collect

**Account and access data:**

- Email and account-linked data when account functionality is enabled
- Access-control and entitlement data associated with API keys and subscription checks

**Pseudonymous security identifiers:**

- Hashed and truncated client fingerprints used for rate limiting, abuse prevention, and request correlation
- These identifiers are treated as pseudonymous data and are not presented as a public user profile

**Wellness and AI artifacts:**

- Wellness-profile inputs may be processed within request scope
- Some direct-user artifacts may be persisted in minimized form:
  - feedback on AI/RAG responses
  - user knowledge/personalization artifacts
  - signed audit metadata for privileged AI actions

### What We Do Not Promise

- We do **not** promise that the entire product is zero-storage or purely local-only
- We do **not** position the current product as HIPAA-ready, clinical-grade, or 42 CFR Part 2 compliant
- We do **not** use the current wellness runtime for clinical records, crisis workflows, or substance-use-disorder records

### AI / Automated Analysis

Some surfaces perform **automated wellness analysis**, including:

- BMI, body-fat, and nutrition-target calculations
- nutrition planning and weekly-plan generation
- AI insight surfaces (`/insight`, `/api/v1/insight`, `/api/v1/pro/cbt/insight`)

For these surfaces:

- outputs are intended for wellness and educational use
- they are not for emergency use
- they must not be used as the sole basis for treatment decisions
- signs of clinical risk require escalation to qualified professional support

### External and Self-Hosted Processors

When AI features are enabled, requests may be processed by:

- PulsePlate local/runtime processing
- a self-hosted provider family (for example, Ollama-compatible deployments)
- an external provider family (for example, xAI/Grok, OpenAI-compatible, Anthropic-compatible, or Pico)

The active processor depends on deployment configuration. Retention and downstream processing at external processors are governed by the selected provider or deployment terms.

### Retention and Deletion

- Pseudonymous security identifiers are cleaned up through retention policy
- Direct-user SQL artifacts can be exported or deleted through an internal support-led DSAR workflow
- Audit envelopes and indirect security artifacts are retention-managed and are not treated as public self-service artifacts

### Your Rights

Where GDPR or a similar regime applies, you may request:

- access to direct-user artifacts
- deletion of direct-user artifacts where technically and legally supported
- correction of inaccurate account records
- discontinuation of new automated-analysis requests by avoiding or disabling AI surfaces

### Related Documents

- `GET /privacy` runtime JSON contract
- `GET /terms` runtime legal publication for service scope and acceptable use
- `docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`
- `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
- `docs/compliance/DSAR_AND_DELETION_MAP.md`
- `docs/legal/Disclaimer.md`

---

## 🇪🇸 ES Version

### Qué Datos Recopilamos

- Datos de cuenta y acceso cuando la funcionalidad de cuenta está habilitada
- Identificadores de seguridad seudónimos para rate limiting, prevención de abuso y correlación de solicitudes
- Artefactos minimizados vinculados al usuario para feedback de AI/RAG, personalización y metadatos de auditoría firmada

### Qué No Prometemos

- No prometemos un producto completamente sin almacenamiento o solo local
- No posicionamos el producto actual como HIPAA-ready, clinical-grade o 42 CFR Part 2 compliant
- No usamos el runtime de wellness para registros clínicos, workflows de crisis o registros de trastorno por uso de sustancias

### AI / Análisis Automatizado

Algunas superficies realizan análisis automatizado de wellness:

- cálculos de BMI, body-fat y nutrition targets
- planificación nutricional y weekly-plan generation
- superficies AI insight (`/insight`, `/api/v1/insight`, `/api/v1/pro/cbt/insight`)

Estos resultados son para wellness y educación, no para emergencias ni decisiones de tratamiento.

### Procesadores Externos y Self-Hosted

Cuando las funciones de AI están habilitadas, las solicitudes pueden ser procesadas por:

- PulsePlate runtime local
- una familia self-hosted (por ejemplo, Ollama-compatible)
- una familia externa (por ejemplo, xAI/Grok, OpenAI-compatible, Anthropic-compatible o Pico)

### Retención y Eliminación

- Los identificadores de seguridad seudónimos siguen la política de retención
- Los artefactos SQL vinculados directamente al usuario pueden exportarse o eliminarse mediante un flujo interno DSAR
- Los audit envelopes y artefactos indirectos de seguridad se gestionan por retención y no son artefactos públicos self-service

---

## 📍 Legal Compliance

This privacy policy is designed to align with:

- **EU / GDPR-style expectations:** transparency, minimization, retention, and data-subject request readiness
- **CIS markets:** wellness positioning and baseline privacy governance
- **US wellness posture:** general privacy principles without claiming clinical compliance

**See also:**

- `GET /privacy` API endpoint — runtime JSON response with current processing disclosures
- `GET /terms` API endpoint — runtime service-scope and acceptable-use disclosures
- `docs/compliance/PROVIDER_INVENTORY.md`
- `docs/compliance/US_REGULATED_LANE_RFC_42_CFR_PART_2.md`
