# AI Assistant Personalization Protocol (Wellness-safe, deterministic)

**Purpose:** Define how the assistant may personalize outputs in a **wellness** app without drifting into unsafe,
non-deterministic, or privacy-violating behavior.

**Status:** Canonical (dev-only). This is a *product + safety* protocol; runtime implementations must follow it and
ship with deterministic tests in separate runtime PRs.

---

## Non-goals (explicit)

- This protocol does **not** authorize storing sensitive personal data by default.
- This protocol does **not** define medical advice. The assistant must remain in wellness territory.
- This protocol does **not** change runtime behavior by itself (docs-only).

---

## Inputs (allowed sources of personalization)

Personalization may use only **explicitly provided** or **explicitly configured** signals, such as:

- user preferences: language, units, dietary preferences, cuisine dislikes
- goals: weight maintenance / fat loss / muscle gain (wellness framing)
- constraints: budget, time, cooking equipment
- accessibility needs: font size, reduced motion, voice-over hints (clients)

If a signal is not present, the system must degrade gracefully to defaults.

---

## Privacy + data boundaries (minimum)

1. **Minimize**: store only what is required for the UX feature to work.
2. **Separate**: do not mix personalization memory with provider prompts unless required.
3. **Delete**: user must be able to clear personalization state.
4. **No silent inference**: do not infer sensitive attributes (medical conditions, pregnancy, diagnoses).

---

## Determinism contract (required)

Any personalization feature MUST define:

- canonical input schema (what fields exist)
- canonical output schema (what fields are affected)
- fallback defaults (when inputs are missing)
- deterministic tests for: default path + personalized path + cleared state

If personalization touches AI outputs, require:

- explicit **uncertainty/degrade** behaviors (e.g., “insufficient info”)
- bounded budgets (calls, tokens, recursion) where applicable

---

## Safety language (wellness)

Personalized outputs must:

- avoid medical diagnosis/treatment claims
- communicate uncertainty when inputs are incomplete
- prefer “options + trade-offs” over prescriptions

---

## Promotion rules (artifact-based)

When a personalization rule becomes durable, promote it as a repo artifact:

- protocol update (this file) OR an ADR (architecture decision) — pick one SoT
- tests/guards in the runtime PR that implements it
- backlog ledger items for deferred work
