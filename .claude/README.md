# Claude Code Role Configuration

## 📋 Использование роли

Роль команды PulsePlate AI Team разделена на несколько файлов для оптимизации контекста:

- **`.claude/role.md`** — основное описание роли (core mission, критичные правила)
- **`.claude/role-technical.md`** — технические правила кодирования
- **`.claude/role-product.md`** — продуктовые рекомендации
- **`.claude/role-security.md`** — руководство по безопасности
- **`.claude/role-marketing.md`** — маркетинг и GTM стратегии
- **`.claude/role-optional.md`** — опциональные разделы (AI reports, wellness ideas)

### Варианты использования

#### 1. Автоматическая загрузка (рекомендуется)

Claude Code автоматически читает файлы из `.claude/` директории при запуске в проекте. Основной файл `.claude/role.md` содержит ссылки на специализированные файлы.

#### 2. Явное указание через system prompt

```bash
claude --system-prompt "$(cat .claude/role.md .claude/role-technical.md)" "ваш запрос"
```

#### 3. Использование в интерактивной сессии

В интерактивной сессии Claude Code можно упомянуть файлы:

```bash
@.claude/role.md @.claude/role-technical.md помоги мне с задачей...
```

#### 4. Через append-system-prompt

```bash
claude --append-system-prompt "$(cat .claude/role.md)" "ваш запрос"
```

## 🎯 Что включает роль

### Основной файл (`.claude/role.md`)

- **Multi-domain специалисты**: Backend, Frontend, ML, QA, Security, Marketing
- **Формат ответов**: Summary → Plan → Code → Tests → Security → Marketing → Decision Log → Next Actions
- **Критичные правила**: Health/nutrition domain, VIP conversion, Bayesian diagnostics, thin slices

### Специализированные файлы

- **Technical** (`.claude/role-technical.md`): Python/Swift правила, тестирование, архитектура, Bayesian diagnostics
- **Product** (`.claude/role-product.md`): VIP features, health data handling, продуктовые принципы
- **Security** (`.claude/role-security.md`): HIPAA, data privacy, API security, compliance
- **Marketing** (`.claude/role-marketing.md`): ASO/SEO, VIP conversion, wellness niche, launch strategy
- **Optional** (`.claude/role-optional.md`): AI reports format, wellness recommendations, easy entry ideas

## 📝 Обновление роли

При необходимости обновите соответствующий файл:

- Технические изменения → `.claude/role-technical.md`
- Продуктовые изменения → `.claude/role-product.md`
- Безопасность → `.claude/role-security.md`
- Маркетинг → `.claude/role-marketing.md`
- Опциональные разделы → `.claude/role-optional.md`
- Критичные правила → `.claude/role.md`

Изменения будут автоматически применяться при следующем запуске Claude Code.
