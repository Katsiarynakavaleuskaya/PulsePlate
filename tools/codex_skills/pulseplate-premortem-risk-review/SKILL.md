---
name: pulseplate-premortem-risk-review
description: Run a PulsePlate-governed premortem risk analysis on a PR plan, epic lane, launch decision, security decision, CI/CD change, AI/RAG rollout, App Store release step, monetization decision, or design-system plan. Advisory only; does not replace coordinator, review gates, or merge-readiness authority.
---

# PulsePlate Premortem Risk Review

## When to use

Use this skill when the user or task says:

- `premortem this`
- `run a premortem`
- `what could kill this`
- `future-proof this`
- `stress test this plan`
- `what am I missing here`
- `find the blind spots`
- `what could go wrong`
- `poke holes in this`
- `where will this break`
- `devil's advocate this`

Also use it when a PulsePlate task has high downside if wrong:

- App Store release readiness decision
- security suppression or remediation decision
- CI/CD workflow change
- Docker/SBOM/provenance gate change
- product-tier, paywall, or StoreKit decision
- HealthKit, AI consent, or privacy decision
- RAG/LLM/evaluation rollout
- design-system automation plan
- production deploy or infrastructure change
- epic lane plan or multi-PR series

## Non-triggers

Do not use this skill for:

- simple factual questions
- ordinary code review without a plan
- typo fixes
- small docs-only edits with no risk
- Dependabot patch bumps unless CI/security blast radius is unclear
- tasks where the decision is already irreversible

## Inputs required

- The plan, decision, or PR scope being assessed in this premortem.
- Changed file list or candidate paths (if PR-scoped).
- Active coordinator packet or task packet path (if available).
- Target mode: `pr-premortem`, `epic-premortem`, `launch-premortem`, or `decision-premortem`.

## Coordinator start

1. Start with repo gates and coordinator bootstrap:

   ```bash
   python3 scripts/orchestration/check_preflight.py
   python3 scripts/orchestration/check_agent_consistency.py
   python3 scripts/orchestration/task_bootstrap.py --goal "<goal>" --task-class "<actual-task-class>" --pr-phase "<phase>"
   ```

   Allowed `--pr-phase` values: `pre_open`, `post_open`, `pre_merge`. Choose based on premortem target:
   - `pre_open` — PR-scoped premortem before opening
   - `post_open` — review-cycle premortem on an open PR
   - `pre_merge` — final risk sweep before merge

2. Preserve the coordinator-declared role order. This skill is advisory and must not invent a parallel decision authority.
3. Treat `recommended_skills` and `skill_routing` from the packet as additive context, not execution permission.

## Role order

Use this default order unless the active packet declares a narrower compatible sequence:

1. `agent-coordinator`: scope lock, role assignment, premortem frame, synthesis, DoD.
2. `architecture-specialist`: structural risk, ownership boundaries, contract drift, layering violations.
3. `security-auditor`: auth, quota, secrets, subprocess safety, guard weakening, suppression hygiene.
4. Surface owners as applicable: `backend-engineer`, `frontend-engineer`, `app-store-release-agent`, `wellness-analyst-agent`, `creative-designer`.
5. `qa-engineer-agent`: test plan risk, missing negative cases, gate coverage gaps.
6. `bug-hunter`: edge cases, false-green risks, historical reviewer-pattern gaps.

## Minimum context threshold

Before running a premortem, identify three things:

1. **What is the plan?** A clear understanding of the thing being premortemed.
2. **Who does it affect?** The audience, users, team, or systems involved.
3. **What does success look like?** The outcome the plan is trying to achieve.

If any of the three are missing, ask one focused question. Do not ask a questionnaire. Infer from repo context when possible.

## Procedure

### 1. Set the premortem frame

After gathering sufficient context, set the frame explicitly:

> It is 6 months from now. This plan failed. We are looking backward to understand why.

For urgent CI/main-red work, compress the timeframe:

> It is 48 hours from now. This hotfix made things worse. We are looking backward to understand why.

### 2. Generate raw failure modes

List every genuine failure mode. Each must be:

- Specific to this plan (not generic advice that applies to anything).
- Grounded in actual details from the plan and repo context.
- A genuine threat (not a minor inconvenience or extremely unlikely edge case).

Do not pad with weak risks. Do not stop early if there are more. The number should be whatever is real for this specific plan.

### 3. Deep-dive each failure mode

For each major failure mode, include:

- **Failure story:** 2-3 paragraph narrative of how it played out. Use details from the plan.
- **Underlying assumption:** The one thing being taken for granted that made this failure possible.
- **Early warning signs:** 1-2 concrete, observable signals that this failure mode is starting to play out.
- **Containment action:** What to do if the warning signs appear.

### 4. Synthesize

Produce the synthesis with the following sections:

#### Summary

State the plan in one sentence and the failure frame in one sentence.

#### Most likely failure

Which failure scenario is most probable given what you know? Why?

#### Most dangerous failure

Which failure scenario would cause the most damage if it happened, even if less likely?

#### Hidden assumption

The single biggest assumption that has not been questioned.

#### Revised plan

Concrete changes that would make the plan more resilient. Each revision must map directly to a specific failure mode.

#### Pre-merge or pre-launch checklist

3-7 checks that can be performed before merge or launch.

#### Decision

Use one of:

- `proceed` -- plan is sound.
- `proceed with changes` -- plan is sound after specific revisions.
- `block until fixed` -- plan has critical issues that must be resolved first.
- `split PR` -- plan scope is too large and should be decomposed.
- `close as premature` -- plan needs more context or prerequisite work.
- `convert to different PR type` -- plan is misclassified.

### 5. Run PulsePlate-specific checklists

Apply domain-specific checks based on what the plan touches:

#### PR governance

- Does the plan preserve `AGENTS.md` authority?
- Does it preserve `docs/orchestration/AGENT_ROUTING_GRAPH.md`?
- Does it preserve `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md`?
- Does it preserve Phase2 PR body gates?
- Does it preserve review mapping artifacts?
- Does it preserve CI required checks?

#### Security

- Does the plan weaken a guard?
- Does it add allowlist/suppression without removal condition?
- Does it hide a real alert?
- Does it make a fail-closed gate advisory?
- Does it leak secrets or local paths?

#### CI/CD

- First failing step versus misleading downstream symptom?
- `always()` usage?
- Missing step outcome gates?
- `continue-on-error` or `|| true`?
- Artifact/evidence upload behavior?
- Branch/tag trigger differences?
- Staging versus production duplication?

#### App Store / wellness

- No medical/diagnosis/treatment/therapy/crisis claims?
- HealthKit read-only posture preserved?
- AI consent before free-text request?
- Reviewer notes match runtime truth?
- Screenshot claims match implemented feature access?
- StoreKit/App Store Connect remains pricing truth?

#### RAG / LLM / eval

- Offline fixtures before runtime rollout?
- No provider calls in offline evals?
- No unverifiable claims?
- No leakage of private data into eval corpora?
- Clear promotion criteria?
- Failure thresholds and rollback?

#### Design / Figma

- Repo remains source of truth?
- No Figma write without operator approval?
- No screenshots unless explicitly scoped?
- No fake UI labels?
- No design claims unsupported by runtime?
- No MCP dependency if task says no MCP?

## Output format

- **Format:** Markdown only. No HTML reports by default.
- **Artifact placement:** If a written artifact is needed, place it under `docs/review/` or `docs/orchestration/`.
- **Chat summary:** After the full report, provide a 3-sentence summary: most likely failure, hidden assumption, and the single most important revision.

## Guardrails

- Do not replace `agent-coordinator`, `scripts/orchestration/task_bootstrap.py`, `make verify`, `check_merge_ready.py`, or fixed-mapping governance.
- Do not auto-merge, auto-resolve review threads, or bypass PR gates.
- Do not create HTML reports by default.
- Do not require MCP, Figma, or screenshot dependencies.
- Do not invent repo state or use fake citations.
- Do not reveal hidden chain-of-thought.
- Do not recommend weakening guards as the first fix.
- Do not mark a risky PR merge-ready just because it is small.
- Do not use broad scraping or external data collection.
- This skill is advisory. It does not have execution authority.

## SoT links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
