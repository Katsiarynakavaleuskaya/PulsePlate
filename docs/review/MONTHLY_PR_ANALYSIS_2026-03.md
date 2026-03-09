# Monthly PR Analysis for PulsePlate (February–March 2026)

**Snapshot date:** 9 March 2026
**Window covered:** 4 February 2026 to 9 March 2026 (inclusive)
**Method:** agent-orchestrated repo review + merged PR scan + backlog/top-20 cross-check
**Primary sources:** `gh pr list`, `git log`, `docs/roadmap/BACKLOG_LEDGER.md`, `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md`, `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`

**Important:** this document is a synthesis artifact for monthly review. Canonical truth for deferred work and closure status remains `docs/roadmap/BACKLOG_LEDGER.md`. GitHub search returns **387 merged PRs** in the raw calendar window (verification: run the raw merged-window query below to reproduce); this report intentionally focuses on the later-wave slice centered on merged PRs in the `#963-#1048` range and the adjacent backlog items they moved.

**Repro queries used for this snapshot:**
- Raw merged-window scan: `gh pr list --state merged --search "merged:>=2026-02-04 merged:<=2026-03-09" --limit 500`
- Curated late-wave slice review: merged PRs in the `#963-#1048` band cross-checked against `gh pr view <N>`, `git log`, `BACKLOG_LEDGER`, and the Top-20 / phase-fit artifacts above
- Reviewed PR IDs (fixed slice): `#963` through `#1048` inclusive; adjacent pre-wave context references used explicitly in section 1.5 are `#942`, `#950`, `#951`, and `#952`

---

## Summary

| Metric | Snapshot |
|--------|----------|
| Raw merged PR volume in the calendar window | `387` merged PRs from GitHub search |
| Core review band used in this report | curated later-wave slice centered on merged PRs in the `#963-#1048` range, plus adjacent early-February references where relevant |
| Dominant themes | security, orchestration, design tooling, payments baseline, AI/RAG reliability, frontend parity |
| P0 items clearly closed in code + ledger follow-through | RAG input sanitizer (`#1044`, `#1045`), users surface hardening (`#1014`, `#1038`, `#1043`) |
| P0/P1 items materially advanced but not fully finished | session/auth transport (`#995`, `#1003`, `#1030`), export signing (`#1005`, `#1035`), EU compliance control plane foundation (`#1046`) |
| Highest-signal open items | insight fallback chain, iOS Keychain conformance, payments runtime W1, iOS SubscriptionManager, diet-flags sync, legal policy publish |

## 1. What Landed in This Window

### 1.1 Security

| PR | Theme | Why it mattered | What changed |
|----|-------|-----------------|--------------|
| `#989` | CodeQL weak hashing fix | Closed a static-analysis finding in fingerprint/payment-adjacent flows | moved away from weak hashing primitives in the affected path |
| `#992` | Fingerprint hashing hardening | Follow-through after `#989` | strengthened secret/fingerprint handling |
| `#977` | DOMPurify CVE initial fix + evidence | Frontend XSS/dependency hygiene plus proof | initial override plus security evidence doc for the same alert path |
| `#987` | DOMPurify alert follow-through | Follow-up on the same alert family | later Dependabot/alert resolution cleanup for the DOMPurify path |
| `#1005` | Export signing hardening | Reduced risk of forged signed export links | secret requirement, path allowlist, TTL contract |
| `#1035` | Export signing follow-through | Tightened the same export-signing path | additional hardening around secret access and contract clarity |
| `#1014` | Users CRUD API-key guard | Closed unauthenticated CRUD exposure | API-key protection for `/api/v1/users/*` |
| `#1038` | Users surface internalization | Reduced public attack surface | removed `/users/*` from public OpenAPI and aligned visibility |
| `#1018` | Agent input guard | Blocked malicious instruction shapes earlier | fail-closed screening for AI/MCP inputs |
| `#1013` | Local execution sandbox | Reduced command-execution blast radius | sandbox baseline for agent workflows |
| `#1041` | Sandbox stream budget | Prevented unbounded streamed output | output-budget enforcement in sandbox lane |
| `#1044` | RAG input sanitizer | Closed prompt-injection/vector ingestion risk | sanitization before RAG indexing/retrieval |
| `#1046` | EU compliance control plane | Established a compliance/runtime baseline | privacy, transparency, minimization, DSAR support map; follow-through remains open in backlog |
| `#995`, `#1003`, `#1030` | Session/auth transport | Moved browser auth toward safer transport | HttpOnly session-cookie path plus web/session alignment and legacy cleanup |
| `#978` | GDPR log retention cleanup | Retention/compliance hygiene | safer log-retention handling |

**Pattern:** most security work followed the same posture: fail-closed defaults, explicit evidence artifacts, tighter surface visibility, and runtime hardening before growth work.

### 1.2 Payments

| PR | Theme | Why it mattered | What changed |
|----|-------|-----------------|--------------|
| `#983` | RU/BY + iOS payment contract | Established the contract before runtime expansion | documented canonical rails and iOS-first baseline |
| `#986` | PRO activation baseline | Billing activation groundwork | activation endpoints, idempotency, issuer-scoped reads |
| `#999` | Pro payment baseline | Revenue path foundation | Apple verify-receipt + RU/BY manual-intent baseline + reconcile path |

**Pattern:** payments stayed contract-first and additive. The repo now has a baseline, but the runtime W1 wave is still open.

### 1.3 Orchestration and Governance

| PR | Theme | Why it mattered | What changed |
|----|-------|-----------------|--------------|
| `#1000` | Agent Orchestration 2.0 | Canonicalized coordinator-first execution | routing/workflow governance |
| `#996` | PR orchestration contract matrix | One SoT for PR governance | fixed the rule surface for merge/readiness/disposition |
| `#998` | Fixed mapping SoT | Prevented PR-body drift | `docs/review/PR_<N>_FIXED_MAPPING.md` became canonical |
| `#1007` | Merge-check entrypoint | Centralized merge-readiness checks | `check_pr_merge_readiness.py` |
| `#1009` | Local vs CI auth semantics | Removed auth ambiguity around `gh`/GraphQL checks | clearer local-vs-CI auth contract |
| `#1016` | Agent clusters validation | Reduced routing/doc drift | consistency validation across agent docs |
| `#1022` | Skill routing | Deterministic skill selection | routing policy + router implementation |
| `#985`, `#990` | Review-proof governance | Stopped weak review resolution patterns | strict dispositions + ban on trigger-only FIXED proof |
| `#966`, `#1004` | Preflight contract | Made task start deterministic | required preflight and locked CLI contract |
| `#963`, `#973`, `#975`, `#980`, `#981`, `#984`, `#994` | Orchestration support lane | Built the supporting governance mesh | worktree isolation, telemetry, routing graph, consistency guards, tier dependency inventory |

**Pattern:** a large portion of the window was spent not on product endpoints, but on making future PRs reviewable, merge-safe, and reproducible.

### 1.4 Design Tooling

| PR | Theme | Why it mattered | What changed |
|----|-------|-----------------|--------------|
| `#997` | Storybook-first design surface | Created a stable review surface for UI work | Storybook + tokenized component review |
| `#1001` | Penpot + Storybook handoff | Canonicalized a design-to-code bridge | handoff rules and docs |
| `#1006` | Penpot CTA review packet pilot | Added a secondary design-review lane | packetized review flow |
| `#1040` | Codex GPT-5.4 design tooling governance | Defined design-tool routing | operating model for the design lane |
| `#1047` | Token pipeline foundation | Removed manual token mirroring drift | `/tokens`, Style Dictionary, generated web/iOS mirrors |
| `#1048` | Ledger follow-up for token pipeline | Closed traceability gap after `#1047` | backlog recording and follow-through |
| `#1042` | FitChef phase 2 sandbox contract | Scoped mascot/design experimentation | explicit sandbox contract |

**Pattern:** design moved from ad hoc artifacts to governed review lanes and generated token infrastructure.

### 1.5 AI / RAG / Reliability

| PR | Theme | Why it mattered | What changed |
|----|-------|-----------------|--------------|
| `#972` | Philosophy validator | Deterministic LLM-output validation | rule-based wellness/logic guardrails |
| `#974` | Recursive RAG W1 | Reliability iteration on retrieval | recursive retrieval baseline |
| `#1002` | Vector RAG tenant scope | Reduced retrieval cross-talk | subject/tenant scoping |
| `#1024` | Philosophical runtime foundation | Strengthened insight reasoning layer | runtime foundation under `core/insight/*` |
| `#942`, `#950`, `#951`, `#952` | Earlier RAG/philosophy groundwork referenced by this wave | Provide context for what March built on | established the pre-March RAG/philosophy stack that the newer work hardened |

**Pattern:** March work leaned more toward deterministic wrappers and bounded reliability than toward broader AI-surface expansion.

### 1.6 Frontend and Client Parity

| PR | Theme | Why it mattered | What changed |
|----|-------|-----------------|--------------|
| `#995`, `#1003`, `#1030` | Web session/auth alignment | Brought browser behavior closer to secure server transport | session UI/path cleanup and hardening |
| `#1012` | CTA parity coverage | Raised confidence in key user paths | added frontend parity tests |
| `#1021` | Frontend + iOS AI insight parity W1 | Reduced client drift around insight contracts | aligned UI/client contract with backend confidence fields |
| `#997`, `#1006` | Frontend design review lanes | Supported UI consistency | Storybook and CTA packet review |

## 2. What Did Not Land Yet

### 2.1 Top-20 Recovery Queue Snapshot

This section reflects the queue state from `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md` and the phase-fit checklist. It separates fully closed items from partial progress and avoids treating “implementation landed” as identical to “backlog canonically closed”.

| Target PR | Domain | Snapshot status |
|-----------|--------|-----------------|
| `PR-TBD-SESSION-COOKIE-HARDENING-W1` | security | materially advanced by `#995`, `#1003`, `#1030`, but not represented as fully complete in the recovery queue |
| `PR-TBD-INSIGHT-FALLBACK-CHAIN` | ml | still open |
| `PR-TBD-RAG-INPUT-SANITIZER` | security | closed by `#1044`, with ledger close-out recorded in `#1045` |
| `PR-TBD-IOS-KEYCHAIN-CONFORMANCE` | ios | still open; guard coverage landed separately in `#1011` |
| `PR-TBD-PAYMENTS-RU_BY-IOS-BASELINE-RUNTIME-W1` | backend | baseline contract/runtime groundwork landed, W1 runtime still open |
| `PR-TBD-BILLING-APPLE-VERIFY` | backend | still open |
| `PR-TBD-IOS-SUBSCRIPTION-MANAGER` | ios | still open |
| `PR-TBD-DIET-FLAGS-CONTRACT-SYNC` | frontend | still open |
| `PR-TBD-LEGAL-POLICY-PUBLISH` | docs | still open |
| `PR-TBD-EXPORT-SIGNING-HARDENING` | security | materially advanced by `#1005` and `#1035`; queue follow-through still worth treating as partially complete rather than silently closed |
| `PR-TBD-USERS-SURFACE-HARDENING` | security | closed by `#1014` and `#1038`, with ledger close-out recorded in `#1043` |

### 2.2 High-Signal Open Backlog Themes

- **P0:** EU compliance follow-through, insight fallback chain, payments RU/BY + iOS runtime follow-through.
- **P1:** iOS/mobile secret conformance, diet-flags contract sync, legal policy publish, API-key toggle guard, worker proxy hardening.
- **P2:** semantic RAG upgrade remains deferred behind P1 stability, plus ongoing docs/governance/reporting cleanup.
- **Platform sequencing:** Android billing/keystore work remains deferred under the iOS-first policy.

### 2.3 Why These Stayed Open

1. **Security-first sequencing:** release safety and transport hardening were prioritized before growth or broader platform scope.
2. **Baseline-before-runtime pattern:** payments and compliance first received contract/control-plane foundations, with runtime follow-through deferred into explicit next PRs.
3. **Governance overhead was intentional:** merge-readiness, disposition discipline, and ledger sync consumed real throughput, but they also reduced long-term PR entropy.
4. **Thin-scope discipline:** several larger ideas were kept split into baseline vs runtime vs follow-up, which lowered immediate risk at the cost of more docs/ledger work.

## 3. Planning Signals From the Window

### 3.1 Now Bucket

1. Session/auth transport hardening follow-through after `#995`, `#1003`, `#1030`.
2. Insight reliability: deterministic fallback chain plus VIP/echo visibility.
3. Payments runtime W1 for `ios_app_store`, `erip_qr`, and `swift_manual`.
4. Access-control parity: iOS Keychain conformance and diet-flags sync.
5. Legal baseline publication: Privacy Policy plus Terms alignment.

### 3.2 Next Bucket

- `PR-TBD-BILLING-APPLE-VERIFY`
- `PR-TBD-IOS-SUBSCRIPTION-MANAGER`
- `PR-TBD-DIET-FLAGS-CONTRACT-SYNC`
- `PR-TBD-LEGAL-POLICY-PUBLISH`
- `PR-TBD-IOS-STOREKIT-PRODUCTS`
- PostgreSQL cutover and legacy `/premium/*` cleanup remain secondary follow-through items

### 3.3 Later / Deferred

- Semantic RAG upgrade after P1 reliability waves stabilize
- Android monetization and Android secret-storage lanes
- web checkout/global expansion
- growth channels such as Product Hunt, SEO landing pages, and short-form content engine

### 3.4 Sequencing Rules Reconfirmed by the Window

1. Wave-1 security and release blockers come before public growth pushes.
2. Payments runtime W1 should land before Apple verify / iOS SubscriptionManager follow-through.
3. `PR-TBD-AI-BOUNDED-CONTEXT` remains gated behind `PR-TBD-INSIGHT-FALLBACK-CHAIN`.
4. Governance cleanup is valuable, but it should not pre-empt active release/security blockers unless it directly affects merge truth.

## 4. Classification Snapshot

- **Bugfix / hardening:** CodeQL hashing fixes, DOMPurify CVE handling, export signing, RAG sanitizer, users surface security, session transport work.
- **Tech debt / governance:** orchestration 2.0, fixed-mapping SoT, review dispositions, agent consistency, preflight, routing graph, merge-readiness consolidation.
- **Net-new foundation:** token pipeline, EU compliance control plane, payments baseline, philosophy validator/runtime layers, execution sandbox.

## 5. Canonical Artifacts Referenced by This Review

- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md`
- `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
- `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`

---

*Generated on 9 March 2026 from repo-local sources and merged PR history. This review summarizes momentum and gaps; it does not replace canonical backlog or merge-governance artifacts.*
