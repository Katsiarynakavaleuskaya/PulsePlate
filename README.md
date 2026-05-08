# PulsePlate

[![CI](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/workflows/ci.yml/badge.svg)](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Katsiarynakavaleuskaya/PulsePlate/graph/badge.svg?token=HE8BHRB709)](https://codecov.io/gh/Katsiarynakavaleuskaya/PulsePlate)

> **PulsePlate turns body-metric check-ins into practical meal decisions.**

It is a planning-first wellness product built around one continuous flow:

**check-in -> targets -> daily plate -> weekly plan -> shopping list**

PulsePlate is designed as a **wellness and meal-planning product**, not as a diagnosis, treatment, therapy, crisis-support, or emergency-care system. BMI and related outputs are informational wellness tools only, and the product should not replace clinician guidance for diagnosed conditions, pregnancy, eating disorders, medically prescribed diets, or emergencies.

PulsePlate is currently in a **private staged rollout**. This repository is a technical and product snapshot of the platform.

## What PulsePlate Does

PulsePlate is built for people who want structured nutrition planning without the guesswork. It takes body-metric check-ins and turns them into actionable meal decisions.

**Core capabilities:**

- **BMI & nutrition targets** — baseline wellness metrics and daily nutrition guidance
- **Meal planning** — daily plate suggestions and weekly plan generation
- **Food database** — merged local catalog built from USDA and Open Food Facts inputs
- **Shopping list** — auto-generated grocery lists from your weekly plan
- **AI-assisted planning** — retrieval-augmented support for consistency checks and planning value, used only where it adds real structure to the flow

**Product tiers:**

| Tier | What you get |
|------|-------------|
| **FREE** | BMI check-ins, baseline wellness metrics |
| **PRO** | Nutrition targets, daily plate, weekly planning |
| **VIP** | Higher-end planning, menu flows, recipes, shopping/export |

**Client surfaces:** web interface and iOS client in development.

## Why PulsePlate Stands Out

- **Planning-first, not logging-first** — structured around execution, not retrospective tracking. The flow is `check-in -> targets -> plate -> weekly plan -> groceries`.
- **Domain logic combined with product workflows** — BMI/nutrition logic is integrated directly into the planning pipeline, not siloed as a separate calculation.
- **Snapshot-first food-data model** — local merged USDA + Open Food Facts catalog, no external API dependency for core food lookups.
- **AI is staged, not decorative** — retrieval-augmented support, consistency and contradiction checks. AI is used only where it increases planning value.

## Current Status

PulsePlate is in a **private staged rollout**.

- **Backend API**: active — FastAPI-based backend with nutrition and BMI logic
- **Food-data pipeline**: active — USDA + Open Food Facts ingestion
- **Web client**: in development
- **iOS client**: in development
- **Monetization / selective rollout**: hardening in progress
- **Full self-hosted setup**: not available publicly

Production components require authorized access.

## Access and Licensing

PulsePlate is **proprietary software**. All rights reserved.

This public repository is a product and technical snapshot for evaluation, collaboration, and licensing discussions. It is **not** a public self-hosting distribution.

Full backend bootstrap, private packages, deployment runbooks, production configuration, internal AI-runtime tooling, and release operations require **explicit written authorization**.

Unauthorized copying, distribution, modification, commercial use, or derivative work creation is prohibited without prior written permission.

For licensing, partnership, or access inquiries: **pulseplate@pm.me**

---

Copyright (c) 2025 Katsiaryna Kavaleuskaya. All rights reserved.
