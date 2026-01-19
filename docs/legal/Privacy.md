# Privacy Policy

**Status:** Canonical legal document
**Last updated:** 2026-01-19
**Scope:** All product tiers (FREE / PRO / VIP)
**Markets:** CIS / EU / US
**GDPR Compliance:** Yes (Article 4(5) pseudonymous data)

---

## 🇷🇺 RU Version

### Какие данные мы собираем

**Данные аккаунта:**

- Email-адрес (для регистрации и связи)

**Псевдонимные идентификаторы:**

- Хешированные и усечённые IP-адреса (для безопасности и аналитики)
- Эти идентификаторы **не могут** напрямую идентифицировать пользователя
- Классификация: псевдонимные данные (GDPR Article 4(5))

**Аналитика использования:**

- Агрегированные метрики использования (без персональной идентификации)

### Какие данные мы НЕ храним

**Мы НЕ храним постоянно:**

- Показатели здоровья (рост, вес, BMI и другие метрики)
- Персональные медицинские данные
- Платежные данные карт (обрабатываются сторонними провайдерами)

Расчёты выполняются локально и временно.

### Обработка данных

**Локальная обработка:**

- Большинство расчётов выполняются локально без передачи внешним сервисам

**Обработка с использованием AI/LLM:**

- Некоторые эндпоинты (`/insight`, `/api/v1/insight`) могут передавать предоставленный пользователем текст внешним AI-провайдерам для генерации персонализированных рекомендаций
- Провайдеры могут включать OpenAI, Anthropic или другие сервисы
- Данные у провайдеров обычно хранятся до 30 дней для мониторинга злоупотреблений, затем удаляются
- **Отказ:** Не используйте эндпоинты `/insight` или `/api/v1/insight`, если не хотите, чтобы ваш текст обрабатывался внешними AI-провайдерами

**Рекомендация:** Избегайте отправки личной идентифицирующей информации (PII) или чувствительных медицинских данных в эндпоинты insight.

### Хранение и удаление

**Псевдонимные идентификаторы:**

- Хранятся в течение установленного периода (настраивается администратором)
- Автоматически удаляются по истечении периода хранения

**Данные аккаунта:**

- Хранятся до удаления аккаунта
- Могут быть удалены по запросу пользователя

**Данные у внешних провайдеров:**

- Подчиняются политикам хранения провайдеров (обычно 30 дней)

### Ваши права (GDPR)

Если вы находитесь в ЕС, вы имеете право:

- Запросить доступ к вашим данным
- Запросить исправление неточных данных
- Запросить удаление ваших данных
- Отозвать согласие на обработку

### Контакты

По вопросам конфиденциальности обращайтесь к администратору приложения.

**API endpoint:** `GET /privacy` (JSON response с детальной информацией)

---

## 🇬🇧 EN Version

### What Data We Collect

**Account Data:**

- Email address (for registration and communication)

**Pseudonymous Identifiers:**

- Hashed and truncated IP addresses (for security and analytics)
- These identifiers **cannot** directly identify individual users
- Classification: pseudonymous data (GDPR Article 4(5))

**Usage Analytics:**

- Aggregated usage metrics (without personal identification)

### What Data We Do NOT Store

**We do NOT store permanently:**

- Health metrics (height, weight, BMI, and other measurements)
- Personal health information
- Payment card data (handled by third-party providers)

Calculations are performed locally and temporarily.

### Data Processing

**Local Processing:**

- Most calculations are performed locally without external transmission

**AI/LLM Processing:**

- Certain endpoints (`/insight`, `/api/v1/insight`) may transmit user-provided text to external AI providers for generating personalized insights
- Providers may include OpenAI, Anthropic, or other services
- Data at providers is typically retained for 30 days for abuse monitoring, then deleted
- **Opt-out:** Do not use `/insight` or `/api/v1/insight` endpoints if you do not wish your text to be processed by external AI providers

**Recommendation:** Avoid submitting personally identifiable information (PII) or sensitive health data to insight endpoints.

### Retention & Deletion

**Pseudonymous Identifiers:**

- Retained for a configured period (set by administrator)
- Automatically deleted after retention period expires

**Account Data:**

- Retained until account deletion
- Can be deleted upon user request

**Data at External Providers:**

- Subject to provider retention policies (typically 30 days)

### Your Rights (GDPR)

If you are in the EU, you have the right to:

- Request access to your data
- Request correction of inaccurate data
- Request deletion of your data
- Withdraw consent for processing

### Contact

For privacy concerns, please contact the application administrator.

**API endpoint:** `GET /privacy` (JSON response with detailed information)

---

## 🇪🇸 ES Version

### Qué Datos Recopilamos

**Datos de Cuenta:**

- Dirección de correo electrónico (para registro y comunicación)

**Identificadores Seudónimos:**

- Direcciones IP hasheadas y truncadas (para seguridad y análisis)
- Estos identificadores **no pueden** identificar directamente a usuarios individuales
- Clasificación: datos seudónimos (GDPR Artículo 4(5))

**Análisis de Uso:**

- Métricas de uso agregadas (sin identificación personal)

### Qué Datos NO Almacenamos

**NO almacenamos permanentemente:**

- Métricas de salud (altura, peso, BMI y otras mediciones)
- Información de salud personal
- Datos de tarjetas de pago (manejados por proveedores externos)

Los cálculos se realizan localmente y temporalmente.

### Procesamiento de Datos

**Procesamiento Local:**

- La mayoría de los cálculos se realizan localmente sin transmisión externa

**Procesamiento con AI/LLM:**

- Ciertos endpoints (`/insight`, `/api/v1/insight`) pueden transmitir texto proporcionado por el usuario a proveedores de AI externos para generar recomendaciones personalizadas
- Los proveedores pueden incluir OpenAI, Anthropic u otros servicios
- Los datos en los proveedores generalmente se retienen durante 30 días para monitoreo de abuso, luego se eliminan
- **Opt-out:** No use los endpoints `/insight` o `/api/v1/insight` si no desea que su texto sea procesado por proveedores de AI externos

**Recomendación:** Evite enviar información de identificación personal (PII) o datos de salud sensibles a los endpoints de insight.

### Retención y Eliminación

**Identificadores Seudónimos:**

- Retenidos por un período configurado (establecido por el administrador)
- Eliminados automáticamente después de que expire el período de retención

**Datos de Cuenta:**

- Retenidos hasta la eliminación de la cuenta
- Pueden eliminarse a solicitud del usuario

**Datos en Proveedores Externos:**

- Sujetos a políticas de retención del proveedor (típicamente 30 días)

### Sus Derechos (GDPR)

Si está en la UE, tiene derecho a:

- Solicitar acceso a sus datos
- Solicitar corrección de datos inexactos
- Solicitar eliminación de sus datos
- Retirar el consentimiento para el procesamiento

### Contacto

Para consultas sobre privacidad, póngase en contacto con el administrador de la aplicación.

**API endpoint:** `GET /privacy` (respuesta JSON con información detallada)

---

## 📍 Legal Compliance

This privacy policy is designed to comply with:

- **GDPR (EU):** Pseudonymous data classification (Article 4(5)), data subject rights
- **CIS markets:** Local data protection requirements
- **US:** General privacy principles (no HIPAA triggers for wellness apps)

---

**See also:**

- `GET /privacy` API endpoint — Detailed JSON response with current data collection practices
- `docs/legal/Disclaimer.md` — Medical and wellness disclaimers
- `docs/legal/Terms.md` — Terms of Service
