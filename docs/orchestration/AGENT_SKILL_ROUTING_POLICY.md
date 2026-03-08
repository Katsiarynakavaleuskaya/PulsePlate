# Agent Skill Routing Policy

**Purpose:** Define how the coordinator and domain agents select installed skills automatically, without requiring the user to name them manually.

**Status:** Canonical for skill selection in orchestration.

---

## 1. Hard Rules

1. Skills are helpers, not authority. Root `AGENTS.md`, scoped `AGENTS.md`, and business constraints always win.
2. Prefer repo-tracked PulsePlate skills first. Use global installed skills only when they materially improve the task and fit the project architecture.
3. Skill selection must be deterministic and explainable. The coordinator should be able to justify each recommended skill from task class, paths, and goal text.
4. External data collection is research-only unless a future PR explicitly promotes it into a governed product surface.
5. Broad scraping is not an approved default for PulsePlate.
6. Skill routing should use compositional evidence:
   - domain prior,
   - path evidence,
   - lexical cues from task wording,
   - explicit policy blocks for low-fit requests.
7. The routing model should stay explicit and finite-state, not pseudo-semantic magic.
   Practical inspiration is acceptable from formal semantics, relevance weighting,
   and linguistic compositionality, but every output must remain deterministic,
   testable, and inspectable in the task packet.

---

## 2. Coordinator Selection Order

1. Always start with `pulseplate-workflow`.
2. Resolve domain via `docs/orchestration/AGENT_ROUTING_GRAPH.md`.
3. Add repo-tracked PulsePlate skills for the selected domain.
4. Add global installed skills only when the task explicitly matches their scope.
5. Exclude low-fit or high-risk skills even if installed.

Boundary note:
- `docs/orchestration/AGENT_ROUTING_GRAPH.md` remains the canonical source of truth for agent/domain routing.
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` and `scripts/orchestration/skill_router.py` are the canonical skill-selection layer that runs after domain routing resolves.

`scripts/orchestration/task_bootstrap.py:45` is the deterministic bootstrap entrypoint for this selection.
The packet contract is materialized at `scripts/orchestration/task_bootstrap.py:80`,
with routing outputs populated from `scripts/orchestration/task_bootstrap.py:73`.
Deterministic coverage lives in `tests/test_task_bootstrap.py:16` and
`tests/test_task_bootstrap.py:105`.

The bootstrap packet should expose:

- `recommended_skills` for execution order
- `skill_routing` for compact evidence and blocked-pattern metadata

This keeps routing explainable without relying on hidden reasoning.

---

## 3. Project-Fit Skill Lanes

| Lane | Default Skills | Conditional Skills |
|------|----------------|--------------------|
| Orchestration / agent workflow | `pulseplate-workflow`, `docs-sync`, `agents-md`, `pulseplate-gates` | `pulseplate-guards`, `code-review-expert`, `create-pr` |
| Backend / API / contracts | `pulseplate-backend-endpoints`, `pulseplate-openapi-sync`, `pulseplate-gates` | `bug-triage`, `security-best-practices`, `openai-docs` |
| Frontend / web UX | `pulseplate-frontend-ui`, `pulseplate-gates` | `pulseplate-playwright-e2e`, `playwright`, `figma`, `figma-implement-design`, `vercel-react-best-practices` |
| Docs / runbooks / policy | `docs-sync` | `agents-md`, `release-notes`, `code-review-expert` |
| QA / CI / remediation | `bug-triage`, `pulseplate-gates` | `ci-fix`, `gh-fix-ci`, `gh-address-comments`, `code-review-expert` |
| Reports / wellness / GTM research | `pulseplate-ai-reports`, `docs-sync` | `notion-research-documentation`, `notion-knowledge-capture`, `linear`, `openai-docs` |
| Design / media / launch assets | `figma`, `docs-sync` | `figma-implement-design`, `pulseplate-frontend-ui`, `playwright`, `notion-research-documentation`, `notion-knowledge-capture`, `sora`, `imagegen`, `speech`, `screenshot`, `app-store-release-agent` companion workflows |

---

## 4. Installed Skills Policy For This Project

The coordinator may use installed skills when they improve delivery and align with PulsePlate boundaries.

### Preferred by default

- Repo-tracked PulsePlate skills in `tools/codex_skills/`
- `docs-sync`
- `bug-triage`
- `code-review-expert`
- `openai-docs`
- `playwright`
- `figma`
- `linear`
- `notion-research-documentation`

### Conditional by task fit

- `security-best-practices`, `security-threat-model`, `security-ownership-map`
- `create-pr`, `commit-work`, `release-notes`, `gh-address-comments`, `gh-fix-ci`, `ci-fix`
- `sora`, `imagegen`, `speech`
- `vercel-react-best-practices`, `vercel-react-native-skills`
- deployment skills (`vercel-deploy`, `netlify-deploy`, `render-deploy`, `cloudflare-deploy`) only for explicit deploy tasks

### Never auto-invoke by default

- `yeet`
- deployment skills on non-deploy tasks
- screenshot/system capture skills on non-visual tasks
- any broad scraping or “collect everything from the internet” workflow

---

## 5. Data Collection Policy For PulsePlate

### 5a. Design Tool Source Precedence

For design-system, prototype, and visual implementation tasks, use the
canonical source precedence defined in
`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`.
### Approved now

- YouTube transcript / channel monitoring for founder research and trend tracking
- X/Twitter research via official APIs or compliant exports
- Google Trends and search-intent datasets

### Conditional later

- Reddit or forum mining for pain-point discovery
- App Store / Play Store review mining
- Competitor landing page monitoring

### Not approved for current repo

- TikTok scraping
- Google Maps scraping
- universal free-form scrapers for arbitrary sites

Rationale: the current product is a wellness/nutrition platform with strong privacy, quota, and safe-language constraints. These data-collection surfaces are not core runtime dependencies.

---

## 6. PR / Release Discipline

If a task includes PR preparation, release packaging, or review-thread handling:

- use `create-pr`, `commit-work`, `release-notes`, `gh-address-comments`, or `gh-fix-ci` only when the task explicitly enters that stage;
- do not stage or push automatically unless the user asked for it;
- keep merge-readiness rules in `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md` authoritative.

---

## Related Documentation

- `docs/dev/CODEX_SKILLS.md`
- `docs/orchestration/workflow.md`
- `docs/orchestration/AGENT_ROUTING_GRAPH.md`
- `.cursor/agents/agent-coordinator.md`
