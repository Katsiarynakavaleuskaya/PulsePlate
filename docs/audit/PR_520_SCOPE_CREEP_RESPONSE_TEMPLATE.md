# PR-520 Scope Creep Response Template

**Purpose:** Short, firm, and polite template for responding to scope-creep suggestions during PR review.

---

## Template (Copy/Paste)

> Thanks for the suggestion! This is a good improvement, but it's out of scope for PR-520 (contract alignment only). I'll create a separate PR for [guard alignment / weekly refactor / etc.] after this one merges.
>
> **Rationale:** PR-520 follows the "one logical change" principle to keep review focused and prevent regression risk. See `docs/audit/PR_520_INSIGHTS.md` for enforcement checklist.

---

## Common Scenarios

### 1. "Let's also align guards while we're at it"

**Response:**
> Guard alignment is a separate product/infra decision (see `docs/audit/PR_519_AUDIT.md` section "Guard Divergence"). PR-520 focuses on contract parity only. I'll defer guard alignment to a follow-up PR after explicit product decision.

### 2. "Can we refactor weekly endpoint too?"

**Response:**
> Weekly endpoint (`/api/v1/premium/plan/week`) has contract mismatch (VIP-dependent, different response model). Per PR-519 audit, this is deferred; sanctioned bridge is `week-flexible`. Refactoring weekly is out of scope for PR-520.

### 3. "Why not fix OpenAPI visibility now?"

**Response:**
> OpenAPI visibility gates (hiding deprecated aliases) are planned for PR-521 (frontend migration). PR-520 stabilizes contracts first; visibility changes require frontend coordination.

### 4. "Let's extract legacy_app logic too"

**Response:**
> Legacy extraction is planned for PR-511A/511B (per PR-510 audit). PR-520 keeps legacy dependencies to minimize risk. Extraction will follow after contract stabilization.

---

**Last updated:** 2026-01-12
