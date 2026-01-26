# Model Selection Rationale Blocks (Ready-to-Insert)

**Purpose:** Copy-paste-ready rationale blocks for each agent file.

**Placement:** Insert after frontmatter (after `---`), before main content.

**Format:** 2-5 bullets, no thresholds, no duplication of canonical docs.

---

## agent-coordinator.md

```diff
 ---

+## Model Selection Rationale
+
+- **Model:** `auto`
+- **Why auto:** Coordinator performs routing and synthesis only, not heavy reasoning. Flexibility benefits from latest model capabilities without manual updates.
+- **Work type:** Task triage → agent assignment → result synthesis → next actions. Process-driven, not model-driven.
+- **Determinism:** Repeatability ensured by canonical process (Audit → Plan → DoD) and links to canonical docs, not fixed model.
+- **Escalation:** If coordinator starts drifting in style/quality, fix model only via separate PR with rationale in `docs/agents/model_policy.md`.
+
 You are the **Master Agent Coordinator** for the PulsePlate project.
```

---

## ai-innovation-specialist.md

```diff
 ---

+## Model Selection Rationale
+
+- **Model:** `auto` (currently `gpt-5.2`; can be auto for flexibility)
+- **Why auto:** R&D and experimental design benefit from model variety and strong reasoning capabilities. Latest models often improve on previous versions.
+- **Work type:** Research-backed proposals, prototypes, impact/effort assessment, cutting-edge technique evaluation.
+- **Determinism:** Results fixed by artifacts (audit/ADR/PoC), not identical text. Innovation requires exploration, not repetition.
+- **Escalation:** For benchmarks/replication studies, temporarily fix model for experiment duration.
+
 You are a senior AI research engineer and innovation specialist with deep expertise in:
```

---

## architecture-specialist.md

```diff
 ---

+## Model Selection Rationale
+
+- **Model:** `auto` (currently `gpt-5.2`; can be auto for flexibility)
+- **Why auto:** Architecture tasks require contextual repo analysis and trade-offs. Auto typically provides better design reasoning and adapts to codebase context.
+- **Work type:** Layer boundaries, invariants, minimal diffs, PR planning, pattern design.
+- **Determinism:** Ensured by guard-policy + audit docs + DoD, not fixed model. Architecture decisions documented, not repeated verbatim.
+- **Escalation:** If strictly repeatable text needed for ADR, fix model pointwise for specific task only.
+
 You are a senior software architect specializing in the PulsePlate codebase architecture.
```

---

## bug-hunter.md

```diff
 ---

+## Model Selection Rationale
+
+- **Model:** `auto` (currently `gpt-5.2-codex`; can be auto for flexibility)
+- **Why auto:** Bug diagnosis and root cause analysis benefit from stronger reasoning and context adaptation. Latest models often improve on debugging capabilities.
+- **Work type:** CI triage, minimal reproducible cases, pinpoint code locations, test failure analysis.
+- **Determinism:** Achieved through reproducible steps (commands/logs/tests), not identical text. Bug reports are artifacts, not model outputs.
+- **Escalation:** If stable test matrix/table reports needed, can fix model for reporting only.
+
 You are a senior bug hunter and quality assurance specialist for the PulsePlate project.
```

---

## security-auditor.md

```diff
 ---

+## Model Selection Rationale
+
+- **Model:** `auto` (currently `claude-4.5-opus-high-thinking`; can be auto with option to fix later for repeatable reports)
+- **Why auto:** Security analysis requires coverage of new attack surfaces and change context. Auto typically stronger in comprehensive threat analysis.
+- **Work type:** Threat modeling, diff review, hardening checks, "what can go wrong" analysis.
+- **Determinism:** Checklists and artifacts (RUNBOOK/guards) more important than identical formulations. Security findings are documented, not repeated.
+- **Escalation:** For regulatory/template reports, can fix model for consistency. For exploratory audits, auto preferred.
+
 You are a senior security auditor and penetration testing specialist for the PulsePlate project.
```

---

## marketing-strategist.md

```diff
 ---

+## Model Selection Rationale
+
+- **Model:** `auto` (currently `gpt-5.2`; can be auto for flexibility)
+- **Why auto:** Marketing requires copy variation, positioning flexibility, and rapid iteration across channels. Auto enables experimentation and adaptation.
+- **Work type:** ASO/SEO, messaging, growth experiments, competitive analysis, conversion optimization.
+- **Determinism:** Results fixed by specific deliverables (copy pack, screenshot plan), not identical responses. Marketing is iterative, not repetitive.
+- **Escalation:** If strict tone-of-voice needed per brand guide, can fix model for package preparation period only.
+
 You are a senior marketing strategist and business growth expert specializing in wellness/health mobile applications.
```

---

## creative-designer.md

```diff
 ---

+## Model Selection Rationale
+
+- **Model:** `auto` (currently `gemini-3-flash`; can be auto for flexibility)
+- **Why auto:** Design and creative work benefit from wide variant generation and rapid divergence. Latest models often improve on visual/creative capabilities.
+- **Work type:** UI/UX ideas, visual concepts, storyboards, asset/promo structures, brand consistency.
+- **Determinism:** Controlled by Brand/Style Guide and review, not model. Design deliverables are artifacts, not model outputs.
+- **Escalation:** If uniform "standard" spec format needed, can fix model for documentation only. For ideation, auto preferred.
+
 You are a senior creative designer and visual identity specialist for **PulsePlate** wellness app.
```

---

## Summary

All agents use `auto` (or can migrate to `auto`) for:
- **Flexibility:** Latest models often improve capabilities
- **Context adaptation:** Better reasoning for specific tasks
- **No drift risk:** Determinism ensured by process/artifacts, not model

Fixed models only when:
- Repeatable reports needed (regulatory/template)
- Benchmarks/replication studies
- Auto becomes unstable for specific task

**Policy reference:** See `docs/agents/model_policy.md` for canonical policy.
