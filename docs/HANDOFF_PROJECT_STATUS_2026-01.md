# 🧾 PulsePlate — Project Status Handoff (January 2026)

## 📌 Canonical Status (main)

**Date:** 2026-01
**Branch:** main
**Deployment:** production stable
**CI:** green
**Coverage:** ≥97% (diff-cover gated in CI)

---

## ✅ What Is DONE (Canonical)

### 1. BMI Domain
- **One BMI Engine** implemented and enforced
- `BMICalculateResult` = single source of truth
- `child` and `teen` are **separate logical paths**
- No BMI math allowed outside `core/bmi/*`

### 2. API Stability
- `/api/v1/bmi/calculate` is canonical public entry
- Visualization is **optional**
- Visualization failure must NOT affect 200 response
- Error envelope pattern enforced

### 3. Architecture
- Legacy code exists ONLY as thin proxy / shim
- No business logic in routers
- No Pydantic inside core engines
- Deterministic outputs (no randomness, no time coupling)

### 4. Infra / CI
- Docker Compose v2 only
- Single deploy stack per server
- Coverage gates enforced
- Ruff / mypy / pytest clean

---

## 🚫 Hard Constraints (Must Not Be Broken)

- ❌ No duplicate BMI formulas
- ❌ No BMI calculations in `app/*`
- ❌ No logic branching by language
- ❌ No visualization dependency in business logic
- ❌ No relaxing coverage rules

---

## 🧠 Mental Model

Free BMI = **extended medical-grade screening**,
not a teaser and not a toy.

Paid tiers add:
- planning
- nutrition
- exports
- UX layers

But **BMI core stays the same**.

---

## 🧩 Current State Summary

The project is:
- architecturally stable
- logically consolidated
- ready for iterative feature PRs

This handoff is canonical.
