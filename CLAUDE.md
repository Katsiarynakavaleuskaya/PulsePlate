# Claude Role Configuration

## Overview

This file references the PulsePlate AI Team role configuration for Claude Code. The role is split across multiple focused files for context optimization:

- **`.claude/role.md`** — Core mission and critical rules (~50 lines)
- **`.claude/role-technical.md`** — Technical coding guidelines
- **`.claude/role-product.md`** — Product guidance
- **`.claude/role-security.md`** — Security guidelines
- **`.claude/role-marketing.md`** — Marketing and GTM strategies
- **`.claude/role-optional.md`** — Optional sections (AI reports, wellness ideas)

The main role file (`.claude/role.md`) defines a multi-domain specialist team that provides coordinated technical, business, and marketing guidance specifically tailored to the PulsePlate health/nutrition application.

## Intended Audience

- **New contributors** unfamiliar with PulsePlate's development practices
- **Developers** working on backend (FastAPI), frontend (iOS SwiftUI), or ML components
- **Team members** needing context-aware AI assistance aligned with project standards
- **Anyone** seeking domain-specific guidance for health/nutrition applications

## Required Configuration

The role configuration is automatically loaded when Claude Code runs in this project directory. No manual setup is required—Claude Code automatically reads files from the `.claude/` directory.

**Note:** If automatic loading doesn't work, you can explicitly reference the role files using:

```text
@.claude/role.md - используй эту роль для всех последующих ответов
```

For specific guidance, you can reference individual files:
- `@.claude/role-technical.md` - для технических вопросов
- `@.claude/role-product.md` - для продуктовых вопросов
- `@.claude/role-security.md` - для вопросов безопасности
- `@.claude/role-marketing.md` - для маркетинговых вопросов

## Common Use Cases

1. **Code Development**: Get AI assistance that follows PulsePlate's coding standards (PEP 8, type hints, 97% test coverage requirement)
2. **Domain Expertise**: Receive health/nutrition-specific guidance, including USDA/OFF data integration and HIPAA considerations
3. **Multi-Domain Support**: Access coordinated advice from backend, frontend, ML, QA, security, and marketing specialists
4. **Test Analysis**: Use Bayesian diagnostics for test quality analysis and coverage improvements
5. **Wellness Product Strategy**: Get recommendations for wellness products, ASO/SEO strategies, and low-barrier market entry ideas

## Usage Example

When starting a conversation with Claude Code in this project, you can explicitly activate the role:

```text
@.claude/role.md - используй эту роль для всех последующих ответов

Помоги мне добавить новую endpoint для расчета BMR с учетом активности пользователя.
```

The role will then provide responses following PulsePlate's structured format:

- Summary → Plan → Code → Tests → Security → Marketing → Decision Log → Next Actions

## What the Role Includes

### Main Role File (`.claude/role.md`)
- **Multi-domain specialists**: Backend, Frontend, ML, QA, Security, Marketing expertise
- **Response format**: Summary → Plan → Code → Tests → Security → Marketing → Decision Log → Next Actions
- **Critical rules**: Health/nutrition domain, VIP conversion, Bayesian diagnostics, thin slices

### Specialized Files
- **Technical** (`.claude/role-technical.md`): Python/Swift coding rules, testing (97% coverage), architecture, Bayesian diagnostics
- **Product** (`.claude/role-product.md`): VIP features, health data handling, product principles
- **Security** (`.claude/role-security.md`): HIPAA considerations, data privacy, API security, compliance
- **Marketing** (`.claude/role-marketing.md`): ASO/SEO, VIP conversion, wellness niche, launch strategies
- **Optional** (`.claude/role-optional.md`): AI reports format, wellness recommendations, easy entry ideas

## Full Documentation

For complete details on role configuration, usage options, and advanced features, see **[`.claude/README.md`](.claude/README.md)**.

---

**Quick Reference**: `@.claude/role.md` - используй эту роль для всех последующих ответов
