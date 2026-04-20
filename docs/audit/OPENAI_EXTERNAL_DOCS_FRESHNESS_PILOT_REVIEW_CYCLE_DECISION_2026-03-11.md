# OpenAI External Docs Freshness Pilot — Review Cycle Decision

**Date:** 11 March 2026 (`America/New_York`)
**Status:** Follow-up decision (`keep narrow`)
**Scope:** Dev-agent docs freshness only; no CI/runtime/product changes

---

## 1. Executive Summary

**Decision:** close the pilot lifecycle as **keep narrow**.

That means:

- repo-native context remains canonical: `scripts/orchestration/context_pack.py:14`
- `openai-docs` remains the canonical external-docs lane for OpenAI tasks:
  `docs/dev/CODEX_SKILLS.md:69`
- `Context7` remains an optional MCP lane documented for local sessions only:
  `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:55`
- `Context Hub` remains an OSS comparator, not repo memory:
  `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:65`

This follow-up closes the lifecycle item opened by
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-openai-docs-freshness-pilot`.

---

## 2. Evidence Basis

This close-out intentionally uses the completed review cycle around PR `#1100`,
not a fresh provider benchmark.

Canonical repo evidence:

- Original pilot decision and exit criteria:
  `docs/audit/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT_DECISION_2026-03-10.md:41`
- Review-thread and merge-governance record for the rollout PR:
  `docs/review/PR_1100_FIXED_MAPPING.md:3`
- KPP promotion rule:
  `docs/memory/kpp_knowledge_promotion_pipeline.md:32`

Reproducible command evidence:

Command:

```bash
gh pr view 1100 --json number,title,state,mergedAt,mergeCommit,url,headRefName,baseRefName
```

Raw stdout excerpt:

```text
{"baseRefName":"main","headRefName":"docs/openai-freshness-pilot","mergeCommit":{"oid":"6fa78202..."},"mergedAt":"2026-03-11T09:07:13Z","number":1100,"state":"MERGED","title":"docs: add OpenAI docs freshness pilot","url":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1100"}
```

Exit code: `0`

Command:

```bash
gh pr checks 1100
```

Raw stdout excerpt:

```text
PR Body Phase2 gates    pass
Merge readiness gate    pass
OpenAPI sync (backend -> frontend artifacts)    pass
test-pr (3.13.6)    pass
coverage-pr    pass
CodeRabbit    pass
cubic · AI code reviewer    pass
```

Exit code: `0`

Interpretation:

- the pilot rollout completed a full governed PR cycle
- the rollout merged cleanly to `main`
- no follow-up evidence suggests pressure to expand this lane into CI/runtime

---

## 3. Review-Cycle Outcome

The pilot stays in place, but only as a **narrow optional lane**.

Why `keep narrow` is the correct close-out:

- the canonical baseline already exists in deterministic repo context and skill
  routing: `scripts/orchestration/task_bootstrap.py:69`,
  `docs/dev/CODEX_SKILLS.md:67`
- the runbook remained aligned with the initial repo-fit decision after one
  review cycle: `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:45`
- no CI/runtime/production integration was introduced by the pilot rollout:
  `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:23`

Why this is **not** a graduation into default behavior:

- official OpenAI docs still carry the truth contract for OpenAI behavior
- external retrieval lanes remain advisory only
- provider surfaces can drift faster than repo governance should

---

## 4. KPP Classification

### 4.1 Durable insight promoted into repo memory

The durable insight is:

- for OpenAI work in PulsePlate, keep repo-native context + official OpenAI docs
  as the canonical baseline, and keep optional external retrieval lanes strictly
  subordinate to that baseline

This is now promoted through:

- `docs/dev/CODEX_SKILLS.md:67`
- `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:30`
- this review-cycle decision artifact

### 4.2 Explicitly non-canonical operational details

The following remain non-canonical and must be revalidated at use time against
provider docs:

- provider auth header names in MCP examples:
  `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:100`
- hosted auth flow details and header wiring examples:
  `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:146`,
  `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:158`
- terminal comparator invocation details for `chub`:
  `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:175`

Reason:

- these are operational examples, not project policy
- they can drift independently from PulsePlate's canonical SoT

---

## 5. Closure Decision

Close the pilot lifecycle item as follows:

- keep repo-native context canonical
- keep `openai-docs` canonical for OpenAI tasks
- keep `Context7` as an optional local MCP lane
- keep `Context Hub` as an optional OSS comparator
- keep all external-doc tooling out of CI, runtime app paths, OpenAPI
  generation, and production endpoints

If provider guidance drifts later, update the runbook or open a new ledger item.
That does **not** reopen this lifecycle decision by default.

---

## 6. Security Notes

- Treat external docs retrieval as untrusted input.
- Do not promote local annotations, MCP responses, or copied skills into repo
  policy without a KPP promotion step.
- Revalidate provider auth details at use time before relying on them in local
  setups.

---

## 7. Marketing & GTM

- This remains an internal developer-enablement pattern only.
- Success is correctness and reduced OpenAI integration drift, not end-user
  feature output.
- No product or growth messaging should imply that external-doc tools are part
  of the PulsePlate runtime stack.
