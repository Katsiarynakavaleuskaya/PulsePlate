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
8. Experimentation and optimization tasks must follow `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`; skills do not bypass mutable-surface or promotion rules.

---

## 2. Coordinator Selection Order

1. Always start with `pulseplate-workflow`.
2. Resolve domain via `docs/orchestration/AGENT_ROUTING_GRAPH.md`.
3. Add repo-tracked PulsePlate skills for the selected domain.
4. Add global installed skills only when the task explicitly matches their scope.
5. Exclude low-fit or high-risk skills even if installed.
6. If the user explicitly requests agent slugs, preserve them in the task packet and apply the corresponding default skill bundles after canonical routing resolves.

Boundary note:
- `docs/orchestration/AGENT_ROUTING_GRAPH.md` remains the canonical source of truth for agent/domain routing.
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` and `scripts/orchestration/skill_router.py` are the canonical skill-selection layer that runs after domain routing resolves.

`scripts/orchestration/task_bootstrap.py:45` is the deterministic bootstrap entrypoint for generic coordinator task packets.
`scripts/orchestration/experiment_bootstrap.py` is the deterministic bootstrap entrypoint for governed experimentation packets.
Deterministic coverage lives in `tests/test_task_bootstrap.py` and `tests/test_experiment_bootstrap.py`.

The bootstrap packet should expose:

- `recommended_skills` for execution order
- `skill_routing` for compact evidence and blocked-pattern metadata

This keeps routing explainable without relying on hidden reasoning.

For experimentation tasks, the bootstrap packet should also reference:

- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
- `docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md` and
  `docs/orchestration/CV_EXPERIMENT_PACKET_TEMPLATE.md` when the task is a CV-oriented offline evaluation
- lexical intents such as `experiment`, `benchmark`, `eval`, `optimization`, `reliability`, and `cv`

CV routing note:

- PR13 promotes `cv` to a first-class coordinator routing domain inside cluster `ml`.
- Generic coordinator task packets should emit `domain: "cv"` for CV-first work.
- Governed experimentation packets remain backward-compatible under `domain: "ml"` until the experiment packet contract is migrated explicitly.
- `cv-agent` is graph-primary for routed CV tasks; runtime/client ownership still stays out of scope here and is tracked separately.

---

## 3. Project-Fit Skill Lanes

| Lane | Default Skills | Conditional Skills |
|------|----------------|--------------------|
| Orchestration / agent workflow | `pulseplate-workflow`, `docs-sync`, `agents-md`, `pulseplate-gates` | `pulseplate-guards`, `code-review-expert`, `create-pr` |
| Experimentation / eval / optimization | `pulseplate-workflow`, `docs-sync`, `pulseplate-gates` | `bug-triage`, `code-review-expert`, `openai-docs` |
| Backend / API / contracts | `pulseplate-backend-endpoints`, `pulseplate-openapi-sync`, `pulseplate-gates` | `bug-triage`, `security-best-practices`, `openai-docs` |
| Frontend / web UX | `pulseplate-frontend-ui`, `pulseplate-gates` | `pulseplate-playwright-e2e`, `playwright`, `figma`, `figma-implement-design`, `vercel-react-best-practices` |
| Docs / runbooks / policy | `docs-sync` | `agents-md`, `release-notes`, `code-review-expert` |
| QA / CI / remediation | `bug-triage`, `pulseplate-gates` | `ci-fix`, `gh-fix-ci`, `gh-address-comments`, `code-review-expert` |
| Reports / wellness / GTM research | `pulseplate-ai-reports`, `docs-sync` | `notion-research-documentation`, `notion-knowledge-capture`, `linear`, `openai-docs` |
| Design / media / launch assets | `figma`, `docs-sync` | `figma-implement-design`, `pulseplate-frontend-ui`, `playwright`, `notion-research-documentation`, `notion-knowledge-capture`, `sora`, `imagegen`, `speech`, `screenshot`, `app-store-release-agent` companion workflows; `Airweave` and `Penpot` stay Phase 1 runbook-only lanes and are not skill-routed yet |

---

## 3a. Requested-Agent Default Bundles

When a task packet includes explicit `requested_agents`, coordinator should keep canonical
domain routing first and then apply these **default helper bundles**:

| Requested agent | Default helper bundle |
|-----------------|-----------------------|
| `agent-coordinator` | `docs-sync`, `agents-md`, `pulseplate-gates` |
| `bug-hunter` | `bug-triage`, `pulseplate-gates`, `pulseplate-guards` |
| `security-auditor` | Auto-routed: `security-best-practices`, `security-threat-model`, `pulseplate-guards`; companion/manual-only: `cybersecurity-skills` (~734 skills, approximate; see `tools/cybersecurity_skills/index.json`) |
| `backend-engineer` | `pulseplate-backend-endpoints`, `pulseplate-openapi-sync`, `pulseplate-gates` |
| `qa-engineer-agent` | `bug-triage`, `pulseplate-gates`, `code-review-expert` |
| `frontend-engineer` | `pulseplate-frontend-ui`, `pulseplate-gates`, `vercel-react-best-practices` |
| `ml-engineer-agent` | `pulseplate-gates`, `docs-sync`, `openai-docs` |
| `data-scientist-agent` | `docs-sync`, `pulseplate-gates`, `pulseplate-ai-reports` |
| `web-research-agent` | `docs-sync`, `pulseplate-ai-reports`, `notion-research-documentation` |

These bundles are bootstrapping helpers, not authority overrides. They do not bypass
`AGENT_ROUTING_GRAPH.md` or reviewer requirements.

Companion note:

- `cybersecurity-skills` is intentionally companion/manual-only guidance for `security-auditor`.
- It must not be emitted as a deterministic `recommended_skills` slug by `scripts/orchestration/skill_router.py`.
- If a security review needs one of those specialized playbooks, the coordinator or reviewer may invoke it deliberately after routing resolves.

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
- `cybersecurity-skills` as companion/manual follow-up for `security-auditor` only (maps to `tools/cybersecurity_skills/skills/` or `$CODEX_HOME/skills` when installed; ~734 skills, approximate; see `tools/cybersecurity_skills/index.json`; installed by default via `scripts/install_codex_skills.sh`)
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

## 4a. Privileged Surface Trigger

The following touched paths must automatically boost security-oriented skills and review:

- `.github/workflows/**`
- `ios/fastlane/**`
- `scripts/orchestration/**`
- merge-governance scripts under `scripts/ci/**`
- merge-governance docs under `docs/orchestration/**` and `docs/review/**`

Expected behavior:

- add `security-best-practices` and/or `pulseplate-guards` when the task packet touches these paths;
- keep `security-auditor` in the review path even if the dominant domain is docs, release, or orchestration;
- security-auditor may reference `cybersecurity-skills` bundle (repo path: `tools/cybersecurity_skills/`; index: `tools/cybersecurity_skills/index.json`) for subdomain-specific procedures (API Security, DevSecOps, Web App Sec, Container Security).

---

## 5. Data Collection Policy For PulsePlate

### 5a. Design Tool Source Precedence

For design-system, prototype, and visual implementation tasks, use the
canonical source precedence defined in
`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`.

Default order:

1. `Figma`
2. `Notion`
3. `Airweave`
4. `Penpot`

Interpretation:

- `Figma` is the canonical design-to-code lane.
- `Notion` is structured memory only.
- `Airweave` is research ingestion only.
- `Penpot` is a secondary design lane only.
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
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
- `.cursor/agents/agent-coordinator.md`
