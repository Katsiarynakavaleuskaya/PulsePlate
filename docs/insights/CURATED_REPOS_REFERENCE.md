# Curated Repositories Reference — Mapping to PulsePlate Vision & Stack

**Date:** 2026-01-28
**Status:** Reference (learning, architecture, and feature alignment)
**Purpose:** Map a curated list of Frontend/UI, AI/LLM, RAG, Multimodal, MCP, ML/CV, and Generative AI repos to our project strategy, insights, and scientific innovations.

---

## 1. Executive Summary

**Use:** Bookmark set for frontend polish, RAG/LLM architecture, multimodal (FitChef, food recognition), MCP tooling, and ML/CV foundations. Entries below map each repo to PulsePlate docs (LLM_RAG_AI_ASSISTANT_ANALYSIS, CV_ML_GAMIFICATION_PLAN, creative_scientific_innovations, RECURSIVE_METHODS_LLM_RAG, COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS) and to backlog/insights where relevant.

**Backlog:** P2 Optional — use curated repos as learning and reference when implementing RAG upgrade, multimodal pipeline, or frontend components (see BACKLOG_LEDGER).

---

## 2. Frontend / UI

| Repo | URL | PulsePlate relevance |
|------|-----|----------------------|
| **Flexbox Froggy** | [thomaspark/flexboxfroggy](https://github.com/thomaspark/flexboxfroggy) | Learning: layout for web client; aligns with frontend AGENTS.md and responsive UI. |
| **shadcn/ui** | [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | Top-tier React UI components; frontend stack (Vite/React) can adopt for BMI/plan/settings screens; design consistency. |
| **50 Projects in 50 Days** | [bradtraversy/50projects50days](https://github.com/bradtraversy/50projects50days) | Practice source for frontend patterns; no direct code dependency. |
| **Awesome React Components** | [brillout/awesome-react-components](https://github.com/brillout/awesome-react-components) | Discovery for forms, charts, accessibility; aligns with FREE_PRO_CONTRACT and form handling rules. |
| **Awesome CSS** | [awesome-css-group/awesome-css](https://github.com/awesome-css-group/awesome-css) | Patterns and ideas for styling; supports minimalism and Apple HIG–inspired UI. |

---

## 3. AI / Multimodal / LLM

| Repo | URL | PulsePlate relevance |
|------|-----|----------------------|
| **LLaVA** | [haotian-liu/LLaVA](https://github.com/haotian-liu/LLaVA) | Large Language and Vision Assistant; reference for multimodal (image + text) in FitChef/food explanation (creative_scientific_innovations, CV_ML_GAMIFICATION_PLAN). |
| **CLIP** | [openai/CLIP](https://github.com/openai/CLIP) | Contrastive text–image learning; potential backbone or reference for food recognition / embedding alignment (CV_ML_GAMIFICATION_PLAN, Food-Vision-101 integration). |
| **Transformers** | [huggingface/transformers](https://github.com/huggingface/transformers) | SOTA NLP/Multimodal; we already reference for Food-Vision-101 (CV_ML_GAMIFICATION_PLAN); use for any new vision/NLP models. |
| **Awesome Multimodal ML** | [pliang279/awesome-multimodal-ml](https://github.com/pliang279/awesome-multimodal-ml) | Papers + repos; reference for FitChef multi-modal pipeline and RAG+vision (creative_scientific_innovations, LLM_RAG_AI_ASSISTANT_ANALYSIS). |
| **RAG from Scratch** | [langchain-ai/rag-from-scratch](https://github.com/langchain-ai/rag-from-scratch) | Step-by-step RAG; we have basic RAG (keyword), no vector embeddings yet (LLM_RAG_AI_ASSISTANT_ANALYSIS); use to design vector RAG and avoid lock-in. |
| **Awesome LLM Apps** | [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | Production-ready LLM apps; patterns for insight endpoint, rate limiting, cost control (RECURSIVE_METHODS_LLM_RAG cost section, P0 hardening). |
| **LLM Engineer Handbook** | [PacktPublishing/LLM-Engineers-Handbook](https://github.com/PacktPublishing/LLM-Engineers-Handbook) | Profession guide; supports architecture and reliability (PHILOSOPHICAL_LOGIC_LLM_RELIABILITY, COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS). |

---

## 4. Agents / Tools

| Repo | URL | PulsePlate relevance |
|------|-----|----------------------|
| **MCP Python SDK** | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | Official Model Context Protocol SDK; we use MCP (mcp-config.json, cursor-ide-browser, etc.); reference for tools and protocol evolution. |

---

## 5. ML / CV Collections

| Repo | URL | PulsePlate relevance |
|------|-----|----------------------|
| **Awesome Machine Learning** | [josephmisiti/awesome-machine-learning](https://github.com/josephmisiti/awesome-machine-learning) | Curated ML frameworks; discovery for Bayesian personalization, adherence, uncertainty (creative_scientific_innovations, COMPREHENSIVE). |
| **Awesome Computer Vision** | [jbhuang0604/awesome-computer-vision](https://github.com/jbhuang0604/awesome-computer-vision) | CV reference; food recognition, calorie estimation (CV_ML_GAMIFICATION_PLAN, Food-Vision-101, Bayesian Food Vision). |
| **ZenML (AI Engineering Hub)** | [zenml-io/zenml](https://github.com/zenml-io/zenml) | MLOps; optional reference for training/eval pipelines if we add custom CV/NLP models (CV_ML_GAMIFICATION_PLAN). |

---

## 6. Qwen Ecosystem

| Repo | URL | PulsePlate relevance |
|------|-----|----------------------|
| **Qwen (Official)** | [QwenLM/Qwen](https://github.com/QwenLM/Qwen) | Alternative LLM backend; we use Grok/Ollama (providers); optional local/cloud model for insight or FitChef. |
| **Qwen Fine-Tuning Examples** | [QwenLM/Qwen-Finetuning](https://github.com/QwenLM/Qwen-Finetuning) | Fine-tuning patterns; relevant if we fine-tune for wellness/coaching tone (NUTRITION_COACHING_DESIGN, FitChef personality). |

---

## 7. Reinforcement Learning

| Repo | URL | PulsePlate relevance |
|------|-----|----------------------|
| **Spinning Up in Deep RL** | [openai/spinningup](https://github.com/openai/spinningup) | Deep RL learning; long-term research for adaptive coaching or gamification policies (creative_scientific_innovations, gamification). |
| **Reinforcement Learning: An Introduction** | [ShangtongZhang/reinforcement-learning-an-introduction](https://github.com/ShangtongZhang/reinforcement-learning-an-introduction) | Sutton & Barto; theory for RL-based personalization or motivation (optional research track). |

---

## 8. Core DL / Generative AI

| Repo | URL | PulsePlate relevance |
|------|-----|----------------------|
| **PyTorch** | [pytorch/pytorch](https://github.com/pytorch/pytorch) | Core DL; we reference PyTorch in CV_ML_GAMIFICATION_PLAN and creative_scientific_innovations (Bayesian Food Vision, variance heads). |
| **Awesome Generative AI Guide** | [steven2358/awesome-generative-ai](https://github.com/steven2358/awesome-generative-ai) | Generative AI overview; recipe generation, FitChef text (creative_scientific_innovations, recipe_synth). |

---

## 9. Mapping to Project Documents

| Document | Curated repos most relevant |
|----------|-----------------------------|
| **docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md** | RAG from Scratch, Awesome LLM Apps, Transformers, LLM Engineer Handbook |
| **docs/analysis/CV_ML_GAMIFICATION_PLAN.md** | LLaVA, CLIP, Transformers, Awesome CV, Food-Vision-101 (in doc), PyTorch |
| **core/insight/creative_scientific_innovations.md** | LLaVA, Awesome Multimodal ML, RAG from Scratch, Qwen Fine-Tuning, PyTorch, Awesome Generative AI |
| **docs/insights/RECURSIVE_METHODS_LLM_RAG.md** | Awesome LLM Apps, RAG from Scratch (cost and depth) |
| **docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md** | LLM Engineer Handbook, Awesome ML (Bayesian), PyTorch |
| **Frontend (AGENTS.md, form handling)** | shadcn/ui, Awesome React Components, Flexbox Froggy |
| **MCP / tooling** | MCP Python SDK |

---

## 10. Recommendations

- **Backlog:** P2 Optional — "Use curated repos as learning and reference when implementing RAG upgrade, multimodal pipeline, or frontend components" (see BACKLOG_LEDGER).
- **Insights:** This doc is the single reference for the 22-repo set; link from creative_scientific_innovations and analysis_insights where useful.
- **No mandatory code dependency:** These are bookmarks for understanding and design; adopt patterns or libraries only via normal PR/backlog process.

---

**References**

- Internal: `docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md`, `docs/analysis/CV_ML_GAMIFICATION_PLAN.md`, `core/insight/creative_scientific_innovations.md`, `docs/insights/RECURSIVE_METHODS_LLM_RAG.md`, `docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md`, `docs/roadmap/BACKLOG_LEDGER.md`, `AGENTS.md`
