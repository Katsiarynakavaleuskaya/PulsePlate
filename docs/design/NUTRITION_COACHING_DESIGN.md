# Nutrition Coaching Design (CBT in Nutrition, Weight Loss/Gain)

**Status:** Vision / Research (P2)
**Date:** 2026-01-28
**Owner:** @katsiaryna_kavaleuskaya

---

## Overview

**Concept:** Product differentiation via cognitive-behavioral psychology in nutrition: goals, reflection, habits, support for slips/weight gain. Does not require ML training platform; leverages LLM/RAG and existing user data.

**English summary:** Nutrition coaching using CBT principles — structured scenarios (goal-setting dialogues, weekly reflections, slip analysis). Builds on existing LLM/RAG infrastructure without requiring dedicated ML training platform.

---

## Links to Existing Components

| Component | Connection to Coaching | Implementation Approach |
| --------- | ---------------------- | ----------------------- |
| **VIP / insight** (`/api/v1/insight`, `app/routers`, legacy_app) | Current insight = one-time LLM response. Coaching = structured scenarios (goal dialogue, weekly reflection, slip analysis). | New layer: "coaching flows" on top of same `get_llm_provider` + RAG; separate endpoints or modes (e.g., `/api/v1/vip/insight/coach/reflection`). |
| **Bayes adherence** (`core/bayes/adherence_model.py`, `bayes_adherence` router) | Already has adherence model (meal_logged, slip), slip risk. CBT coaching can use this data for reflection and step formulation. | Read adherence state via existing API; in coaching prompts — "this week had N slips, risk X"; don't change core, only consume. |
| **FitChef / AI companion** (core/insight/creative_scientific_innovations.md) | FitChef as "friendly expert" — natural voice for coaching (support, non-judgmental, educational tips). | Extend persona and scenarios in FitChef: not only nutrition facts, but also goals, reflection, behavioral advice. |
| **RAG** (`core/rag/simple_rag.py`) | RAG provides educational context. For CBT, add content on cognitive distortions, habits, SMART goals. | Separate index/documents for coaching (or tags in existing RAG); same `retrieve()` calls in coaching prompts. |
| **Menus, goals, targets** (VIP menu, `core/targets.py`, nutrition targets) | Calorie/macro goals already exist. Coaching ties behavioral steps to these goals (e.g., "this week focus — breakfasts"). | Read user goals via existing API; in coaching scenarios — reference goal and suggest small steps. |
| **DigitalOcean platform** | LLM inference (Ollama or cloud provider) already planned on DO. Coaching = another consumer of same LLM/RAG; no separate ML training platform needed. | No infrastructure changes; rate limiting and limits for insight/coaching — shared (P0). |

---

## Future Social Network — Links (Perspective)

- **Shared user base and goals:** If social network = separate app, possible shared identity (OAuth/account) and export goals/achievements from PulsePlate to "community profile".
- **Content and moderation:** Educational content and rules (including from RAG and coaching) can be reused for community guides.
- **Not in current scope:** Social network implementation (feed, subscriptions, chats) does not affect current PulsePlate components; recorded as long-term possibility after coaching.

---

## References

- `core/insight/creative_scientific_innovations.md` (FitChef, AI companion)
- `docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md` (insight, RAG)
- `docs/roadmap/BACKLOG_LEDGER.md` (P2 Vision: Nutrition coaching)
