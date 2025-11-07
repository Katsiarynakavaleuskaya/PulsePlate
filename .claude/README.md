# Claude Code Role Configuration

## 📋 Использование роли

Файл `.claude/role.md` содержит полное описание роли команды PulsePlate AI Team.

### Варианты использования:

#### 1. Автоматическая загрузка (рекомендуется)
Claude Code автоматически читает файлы из `.claude/` директории при запуске в проекте.

#### 2. Явное указание через system prompt
```bash
claude --system-prompt "$(cat .claude/role.md)" "ваш запрос"
```

#### 3. Использование в интерактивной сессии
В интерактивной сессии Claude Code можно упомянуть файл:
```
@.claude/role.md помоги мне с задачей...
```

#### 4. Через append-system-prompt
```bash
claude --append-system-prompt "$(cat .claude/role.md)" "ваш запрос"
```

## 🎯 Что включает роль

- **Multi-domain специалисты**: Backend, Frontend, ML, QA, Security, Marketing
- **PulsePlate-специфичные правила**: Health/nutrition domain, VIP features, Bayesian diagnostics
- **Формат ответов**: Summary → Plan → Code → Tests → Security → Marketing → Decision Log → Next Actions
- **Wellness-специфичные рекомендации**: ASO/SEO, Product Hunt, ниши без лицензий

## 📝 Обновление роли

При необходимости обновите `.claude/role.md` - изменения будут автоматически применяться.
