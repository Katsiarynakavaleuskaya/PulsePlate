# Wave 6 A1b PRO Quota Reconciliation Task Packet

**Date:** 17 April 2026
**Scope:** docs/backlog/governance only
**Mode:** pre-open packet for the next canonical Wave 6 slice

## Purpose

Freeze `PR-A1b` as the next user-owned Wave 6 lane after merged `PR-S0`
(`PR #1433`) and merged `A1` (`PR #1379`).

This packet exists to:

- reconcile the roadmap/backlog wording with already-landed PRO/VIP quota truth
  on live `main`;
- keep `A1b` docs-only and governance-only;
- preserve the canonical `A1b -> A5` runtime sequence;
- prevent semantic-cache or plugin/control-plane work from widening this lane;
- encode the mandatory late-rebase rule because open PRs `#1440` and `#1441`
  also touch `docs/roadmap/BACKLOG_LEDGER.md`.

## Current-Head Preconditions

- `PR #1388` is merged and no longer blocks the next Wave 6 lane.
- `PR #1433` is merged and `PR-S0` is already closed.
- `PR #1379` is merged and is the canonical already-landed runtime evidence for
  the `A1` fallback/readiness spine.
- `origin/main` is green on current-head `CI`.
- Open PRs `#1440` and `#1441` still modify
  `docs/roadmap/BACKLOG_LEDGER.md`, so this lane may open in draft but may not
  claim merge-readiness before a late rebase onto fresh `origin/main`.

## Hard Boundaries

- No runtime/product code changes
- No OpenAPI or public contract mutation
- No semantic cache implementation or semantic-cache gate change
- No Redis / GPTCache rollout
- No provider/auth/billing behavior changes
- No plugin/control-plane implementation work for GitHub / Cloudflare / Figma /
  Hugging Face / Linear / Computer Use / Remotion / Life Science Research
- No widening into `A2-A5`
- No review artifact creation before the PR actually exists

## Canonical Scope

### In scope

- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- this packet
- `docs/review/PR_<N>_FIXED_MAPPING.md` only after PR open
- optional cross-link-only touch to
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`

### Out of scope

- `core/rag/*`
- `llm.py`
- `app/services/*`
- `legacy_app.py`
- quota runtime logic
- provider fallback logic
- auth/entitlement/billing runtime surfaces
- Rail B1 workforce/wiki implementation
- Rail B2 plugin/control-plane implementation

## Required Content Changes

### `docs/roadmap/BACKLOG_LEDGER.md`

- update `ledger-p1-pro-monthly-quota-ledger-reconciliation`
- move the item from the stale `PR #1388` target to canonical `PR-A1b`
- anchor already-landed evidence to merged `PR #1379` using a minimum evidence
  bundle:
  - merge truth: `PR #1379` plus merge commit
    `1ddf8c6778ca1f13c2bfce2e052db5409e8d06ba`
  - runtime truth: `file:line` pointers to tier-aware quota enforcement and
    startup validation
  - verification truth: `file:line` pointers to deterministic tests and
    optional runtime/test artifact links when available
  - acceptance floor: PR + merge SHA and `file:line` pointers are mandatory;
    runtime/test artifact links are optional
- keep the item as reconciliation-only, not runtime reimplementation
- if real residual debt is found, create a narrow follow-up item instead of
  widening `A1b`
- do not close or mutate:
  - `ledger-p1-rag-hardening-followthrough`
  - `ledger-p1-ai-bounded-context-packet`
  - `ledger-p1-ai-bounded-context-extraction`
  - `ledger-p1-llm-reliability-security-gates`
- do not create or reopen any semantic-cache item

### `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`

- preserve `PR-A1b` as a docs reconciliation slice
- strengthen the evidence wording so `A1b` clearly follows already-landed
  `PR #1379`
- preserve sequence `A1b -> A2 -> A3 -> A4 -> A5`
- keep semantic cache deferred and outside `A1b`

### `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`

- optional backlink only if needed for evidence symmetry
- hard gate must remain unchanged

## Required Role-Agent Order

1. `agent-coordinator`
2. `backend-engineer`
3. `architecture-specialist`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`

Rules:

- this order is the lane SoT even if `task_bootstrap.py` suggests a different
  routed primary;
- no assigned role agent may be skipped without an explicit packet update;
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains
  mandatory.

## PR Lifecycle Contract

### PR title

`docs(roadmap): reconcile landed PRO quota truth for Wave 6 A1b`

### Required PR body sections

- `Scope`
- `Files`
- `DoD`
- `Deferred / Follow-ups`
- `Discussion Thread Pass`
- `Fixed in Commit Mapping`
- `Merge Readiness`

### Post-open actions

1. create `docs/review/PR_<N>_FIXED_MAPPING.md`
2. run the mandatory `post_open_review` lane
3. iterate on current-head checks and actionable review comments
4. refresh the PR body mirror whenever the canonical review artifact changes

## Mandatory Late-Rebase Rule

Because open PRs `#1440` and `#1441` both touch
`docs/roadmap/BACKLOG_LEDGER.md`, this lane follows a strict overlap policy:

- the PR may open in draft immediately;
- merge-readiness is forbidden before a late rebase onto fresh `origin/main`;
- during that rebase, resolve only the `A1b`-owned ledger lines;
- if the rebase reveals true overlap on the same anchors with still-open
  `#1440` / `#1441`, stop the lane and replan instead of force-resolving or
  silently rewriting another lane's scope.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- grep verification that:
  - `PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md` preserves `A1b -> A5`
    ```bash
    rg -n '^- `PR-A1b`|^- `PR-A2`|^- `PR-A3`|^- `PR-A4`|^- `PR-A5`' \
      docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md
    ```
  - semantic cache remains deferred-only
    ```bash
    rg -n 'A1b|semantic cache|blocked until the `A1b -> A5` runtime sequence is closed' \
      docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md \
      docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md
    ```
  - `ledger-p1-pro-monthly-quota-ledger-reconciliation` points to already-landed
    `PR #1379` evidence rather than a new runtime implementation claim
    ```bash
    rg -n 'ledger-p1-pro-monthly-quota-ledger-reconciliation|PR #1379|1ddf8c6778ca1f13c2bfce2e052db5409e8d06ba' \
      docs/roadmap/BACKLOG_LEDGER.md
    ```
  - Rail B2 families do not become runtime truth
    ```bash
    rg -n 'Rail B2|advisory only|product runtime truth|semantic cache' \
      docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md
    ```

## Merge-Ready Gate

Before calling this lane merge-ready:

1. late rebase onto fresh `origin/main`
2. rerun `pre-commit run --all-files`
3. rerun `make verify`
4. refresh `docs/review/PR_<N>_FIXED_MAPPING.md` against reachable head commits
5. confirm current-head PR checks are green
6. run the strict wrapper:

```bash
python3 scripts/orchestration/check_merge_ready.py \
  --pr-number <N> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```

## Next Lane After Merge

After merge and safe cleanup, the next canonical slice is:

- `PR-A2` — RAG hardening follow-through

It is explicitly **not** semantic cache.
