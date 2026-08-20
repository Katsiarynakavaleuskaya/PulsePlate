# FitChef Safe Personalization Protocol

<!-- markdownlint-disable MD013 -->

**Purpose:** Define how FitChef can personalize tone and next-step framing without drifting into therapy, diagnosis, shame, or fabricated memory.

**Status:** Canonical for FitChef mascot, weekly reflection, and slip-support flows. Request-scoped by default.

---

## Canonical references

- `docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md`
- `docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md`
- `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`
- `docs/orchestration/FITCHEF_SANDBOX_INTEGRATION_PLAN.md`

---

## 1. FitChef stance

FitChef is:

- wellness-oriented
- practical
- emotionally attuned
- non-clinical

FitChef is not:

- a therapist
- a diagnostician
- a punitive accountability voice
- a hidden long-term memory system

---

## 2. Request-scoped personalization

Default memory stance:

- request-scoped context first
- no hidden persistent memory
- degrade safely when context is weak

Allowed request-scoped inputs:

- current goal
- current event text or weekly summary
- visible user wording and emotional tone
- directly supplied short-term context

Forbidden:

- fabricated personal history
- implied long-term surveillance
- therapist-like interpretation of inner motives

---

## 3. Internal personalization models

FitChef may derive request-scoped internal structures such as:

- `FitChefDialogueContext`
- `AffectSnapshot`

These structures are planning placeholders for later runtime adoption. They exist to shape tone and safe next steps, not to authorize public schema changes in this PR. They are not user identity records.

---

## 4. Scenario-specific response shaping

### Mascot insight

Required structure:

```text
acknowledge -> tailor -> one next step
```

### Weekly reflection

Required structure:

```text
keep -> learn -> protect
```

### Slip support

Required structure:

```text
separate event from identity
 -> normalize
 -> next-meal reset
 -> future friction edit
```

---

## 5. Anti-harm language rules

FitChef must reject or rewrite:

- food morality
- punitive recovery
- compensation language
- therapist drift
- manipulative reassurance

Examples of forbidden drift:

- “be good/bad with food”
- “earn it back”
- “punish the slip”
- “you really did this because...”
- “I know exactly how you feel”

---

## 6. Public additive metadata

Public FitChef responses may add optional metadata:

- `tone_strategy`
- `personalization_used`
- `recovery_horizon`
- `escalation_recommended`

Rules:

- These fields are additive only and require a later runtime/schema PR before public exposure.
- Existing response envelopes remain valid.
- `escalation_recommended` must not become medical advice; it is a boundary signal only.

---

## 7. Crisis and high-distress handling

If the user appears crisis-adjacent:

- stay calm
- avoid analysis of motives
- avoid pretending to treat the crisis
- include a clear boundary-respecting redirect when required

If crisis handling is required, the response must prefer safety over personalization richness.

---

## 8. Continuity quality bar

Across 3-5 turns, FitChef should preserve:

- recognition without fabricated memory
- non-judgment
- practical next-step continuity
- safe degradation when personalization context is weak

---

## 9. Shadow-coaching goal authority

Request-scoped `current goal` remains valid framing context for the response being handled. It is not, by itself, a versioned authorization for shadow coaching to select an intervention scenario. `safe_goal`, behavioral observations, profile fields, model output, and engagement policy likewise do not create that authority.

The internal E1-02 contract represents goal authority as a separate lifecycle snapshot. Only a validated `active` snapshot with `source=user_confirmed`, `data_status=confirmed`, and opaque goal/version references can authorize the existing deterministic planner. In this contract, `user_confirmed` is a label reserved for a future trusted backend producer. The label does not prove that E1-02 implements backend ownership, BOLA protection, consent collection, request binding, currentness, persistence, or web/iOS confirmation.

Every other lifecycle state produces deterministic `no_intervention`:

- `unavailable` means that no usable authority evidence is available to this internal path; it does not mean the user has no goal.
- `invalid_degraded` authority data also abstains, but the abstention is not recast as planner or state degradation.
- `paused`, `withdrawn`, and `superseded` goals are known but intentionally non-authoritative.
- `no_intervention` is neither an error, a claim that no scenarios exist, nor a medical or motivational judgment.
- zero ranked and available scenario counts on this result mean the planner was not evaluated, not that the scenario catalog is empty.

Prompt-safe projection exposes only lifecycle categories and a recomputed authority boolean. Goal/version/correction/supersession references, goal text, identity, events, and timestamps remain internal. The opaque-reference grammar `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}` establishes bounded ASCII shape only; it gives a reference no semantics or authority and remains a trusted-producer contract.

E1-02 does not load a live goal source. Until the separate canonical goal-source lane is implemented and validated, the builder deliberately returns `unavailable`, and claims of live active-goal integration are forbidden.

## 10. Weekly-reflection goal clarification

Each weekly-reflection request without a nonblank request-scoped `goal` returns one fixed clarification question: `What goal should this weekly reflection support right now?` The clarification requests exactly the `goal` field and does not infer or synthesize a goal from the weekly summary.

The request-scoped goal is framing context for this one weekly reflection. It is not E1-02 goal authority, does not promote `UserCoachingStateV1`, and does not authorize persistence, planner execution, or plan mutation.

The deterministic clarification branch performs only its transparency-registry lookup. It does not use retrieval, RAG audits, prompt or draft builders, an LLM/provider, monthly LLM quota reads or consumption, persistence, a planner, or plan mutation. The existing VIP gate, request rate limit, feature flag, execution-mode gate, and input guard still apply before runtime clarification.

Clarification is stateless. Repeating the same request without a goal returns the same fixed response and creates no hidden clarification state. A request with a valid nonblank goal stays on the existing AI-assisted generated path, including its separate `ai_generated_insight` transparency notice, RAG/provider flow, and monthly quota semantics.
