# Top-20 PR Recovery Task Packets (2026-03-08)

Canonical execution artifact for the normalized recovery queue.

Mandatory entry gates before any listed PR starts:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/route_with_telemetry.py --domain <domain> --task-type "<task type>"
```

Coordinator-first rule still applies. If agent connectivity is degraded, use the same routing manually and record the decision in the PR artifact / ledger.

## Active Queue

| # | Target PR | Wave | Domain | Primary | Secondary | Reviewer | Minimum DoD |
|---|---|---|---|---|---|---|---|
| 1 | `PR-TBD-SESSION-COOKIE-HARDENING-W1` | 1 | security | `security-auditor` | `architecture-specialist` | `agent-coordinator` | Remove browser-stored auth secrets; use canonical `/api/v1/pro/session/*` cookie flow; add auth regression tests |
| 2 | `PR-TBD-INSIGHT-FALLBACK-CHAIN` | 3 | ml | `ai-innovation-specialist` | `rag-systems-agent` | `architecture-specialist` | Deterministic provider fallback order; `/ready` reports fallback/echo state safely; response contract remains additive |
| 3 | `PR-TBD-RAG-INPUT-SANITIZER` | 1 | security | `security-auditor` | `architecture-specialist` | `agent-coordinator` | Sanitizer runs before RAG indexing/retrieval; prompt-injection regressions added |
| 4 | `PR-TBD-IOS-KEYCHAIN-CONFORMANCE` | 2 | ios | `frontend-engineer` | `creative-designer` | `qa-engineer-agent` | Keychain-only secret storage verified; no insecure release fallback |
| 5 | `PR-TBD-PAYMENTS-RU_BY-IOS-BASELINE-RUNTIME-W1` | 2 | backend | `architecture-specialist` | `backend-engineer` | `security-auditor` | Runtime billing flow for `ios_app_store`, `erip_qr`, `swift_manual`; activation contract tested |
| 6 | `PR-TBD-BILLING-APPLE-VERIFY` | 2 | backend | `architecture-specialist` | `backend-engineer` | `security-auditor` | Server-side Apple receipt verification normalizes into billing activation |
| 7 | `PR-TBD-IOS-SUBSCRIPTION-MANAGER` | 2 | ios | `frontend-engineer` | `creative-designer` | `qa-engineer-agent` | Dedicated iOS subscription orchestration stays thin and backend-driven |
| 8 | `PR-TBD-DIET-FLAGS-CONTRACT-SYNC` | 3 | frontend | `frontend-engineer` | `creative-designer` | `qa-engineer-agent` | One canonical enum/normalization table across schemas, UI, and generated types |
| 9 | `PR-TBD-LEGAL-POLICY-PUBLISH` | 1 | docs | `web-research-agent` | `cursor-specialist-agent` | `qa-engineer-agent` | Canonical privacy/terms publication paths exist and client links are aligned |
| 10 | `PR-TBD-EXPORT-SIGNING-HARDENING` | 1 | security | `security-auditor` | `architecture-specialist` | `agent-coordinator` | Default secret fails closed; signable export paths are allowlisted |
| 11 | `PR-TBD-USERS-SURFACE-HARDENING` | 1 | security | `security-auditor` | `architecture-specialist` | `agent-coordinator` | `/api/v1/users` is authenticated, internalized, or retired explicitly |
| 12 | `PR-TBD-API-KEY-TOGGLE-GUARD` | 1 | security | `security-auditor` | `architecture-specialist` | `agent-coordinator` | Production/staging fail closed on anonymous or dev API-key toggles |
| 13 | `PR-TBD-WORKER-PROXY-HARDENING` | 1 | security | `security-auditor` | `architecture-specialist` | `agent-coordinator` | Worker path scope, CORS, and forwarded headers are bounded |
| 14 | `PR-TBD (fix/orch-ban-trigger-commit-mapping)` | 4 | orchestration | `cursor-specialist-agent` | `dev-operator` | `architecture-specialist` | Trigger-only commits cannot satisfy FIXED proof mapping |
| 15 | `PR-TBD (required-check truth)` | 4 | orchestration | `cursor-specialist-agent` | `dev-operator` | `architecture-specialist` | Merge truth is current-HEAD required checks only |
| 16 | `PR-TBD (CI hard/soft/external)` | 4 | orchestration | `cursor-specialist-agent` | `dev-operator` | `architecture-specialist` | CI check classes documented and aligned with merge-readiness rules |
| 17 | `PR-TBD-STAGING-SEAM-REMOVAL` | 4 | infra | `dev-operator` | `architecture-specialist` | `security-auditor` | Temporary staging TLS fallback removed only after direct staging runtime is primary |
| 18 | `PR-TBD-NOSEC-ALLOWLIST-PHASE2` | 4 | security | `security-auditor` | `architecture-specialist` | `agent-coordinator` | Legacy allowlist entries removed or converted to fully compliant inline suppressions |
| 19 | `PR-TBD-AI-BOUNDED-CONTEXT` | 3 | ml | `ai-innovation-specialist` | `rag-systems-agent` | `architecture-specialist` | AI runtime extracted after fallback-chain behavior is locked |
| 20 | `PR-TBD-IOS-STOREKIT-PRODUCTS` | 2 | release | `app-store-release-agent` | `marketing-strategist` | `qa-engineer-agent` | Canonical StoreKit product contract and setup checklist are versioned |

## Sequencing Rules

1. Wave 1 security/release blockers land before public growth or store-release pushes.
2. In Wave 2, implement `PR-TBD-PAYMENTS-RU_BY-IOS-BASELINE-RUNTIME-W1` before Apple verify or iOS SubscriptionManager work.
3. `PR-TBD-IOS-STOREKIT-PRODUCTS` may run in parallel with `PR-TBD-IOS-SUBSCRIPTION-MANAGER` only after the billing baseline contract is runtime-backed.
4. `PR-TBD-AI-BOUNDED-CONTEXT` must not start before `PR-TBD-INSIGHT-FALLBACK-CHAIN` is behaviorally complete.
5. Governance cleanup PRs in Wave 4 must not block active release/security remediation unless they directly affect merge-readiness policy.
