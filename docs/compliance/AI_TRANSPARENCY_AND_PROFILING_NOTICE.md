# AI Transparency and Profiling Notice

**Status:** Canonical
**Last updated:** 2026-03-08

PulsePlate treats health-adjacent AI features as **automated wellness analysis**.

## Surfaces Covered

### BMI wellness screening

- Surface ids: `bmi_wellness_screening`
- Endpoints: `/bmi`, `/api/v1/bmi`, `/api/v1/pro/bmi/calculate`
- Analysis type: formula-based automated analysis
- Boundary: wellness-only, not a medical diagnosis or treatment recommendation

### Body-fat estimation

- Surface id: `bodyfat_estimation`
- Endpoint: `/api/v1/bodyfat`
- Analysis type: formula-based wellness estimation
- Boundary: estimate-only, not a clinical body-composition assessment

### Nutrition targets and planning

- Surface id: `nutrition_targets_and_weekly_plan`
- Endpoints: `/api/v1/pro/nutrition/daily`, `/api/v1/pro/meal/weekly`, `/api/v1/premium/plate`
- Analysis type: rule-based automated wellness guidance
- Boundary: wellness planning only, not personalized medical nutrition therapy

### AI-generated insight

- Surface id: `ai_generated_insight`
- Endpoints: `/insight`, `/api/v1/insight`, `/api/v1/pro/cbt/insight`
- Analysis type: automated AI-assisted analysis
- Boundary: wellness coaching only, not therapy, diagnosis, or clinical decision support
- Runtime tracing: prompt and completion payloads are fingerprinted with HMAC and exported without raw text in v1

## User Notice Contract

Every covered surface is governed by these baseline statements:

- This feature performs automated wellness analysis.
- It is not for emergency use.
- It must not be used as the sole basis for treatment or medication decisions.
- Users should seek qualified professional help when clinical risk or urgent care is involved.

## Blocked Regulated Lane

The following cases are **not allowed** inside the current wellness runtime:

- clinical diagnosis or treatment recommendations
- crisis or self-harm intervention workflows
- substance-use-disorder records or 42 CFR Part 2 data
- provider/EHR ingestion and redisclosure workflows

These require a separate regulated lane with:

- separate consent workflow
- separate storage segregation
- redisclosure controls
- explicit legal/compliance approval
