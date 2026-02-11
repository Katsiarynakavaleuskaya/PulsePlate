# PR Audit — CVE-2026-26007 (`cryptography`) remediation + prevention

**Date:** 2026-02-11
**Scope:** security remediation (dependency manifests) + deterministic prevention guard + documentation/backlog updates
**PR:** #716 (`security/cve-2026-26007-cryptography-46-0-5`)

---

## Summary

This PR remediates five open GitHub security alerts tied to the same dependency vulnerability:

- Dependabot alerts: #27, #28, #29
- Code scanning alerts: #538, #539

Root issue: `cryptography` was below the fixed floor in runtime/dev/lock manifests (`46.0.3`).

Implemented fix:

- `cryptography==46.0.5` in pinned manifests (`requirements.txt`, `requirements-dev.txt`, `requirements-lock.txt`)
- `cryptography>=46.0.5` floor in source constraints (`requirements.in`, `constraints.txt`)

Preventive hardening:

- Added deterministic guard test `tests/test_dependency_security_guard.py`
- Documented guard in `tests/AGENTS.md`
- Added CVE record doc `docs/security/CVE-2026-26007-cryptography.md`
- Tracked follow-ups in `docs/roadmap/BACKLOG_LEDGER.md`

---

## Evidence (commands + raw output + exit code)

### 1) Pinned manifests now use non-vulnerable `cryptography`

Command:

```bash
rg -n "^cryptography(==|>=)" requirements*.txt
```

Observed stdout (excerpt):

- `requirements-lock.txt:30:cryptography==46.0.5`
- `requirements-dev.txt:59:cryptography==46.0.5`
- `requirements.txt:30:cryptography==46.0.5`

Exit code: `0`

### 2) Source constraints enforce non-vulnerable floor

Command:

```bash
rg -n "^cryptography>=" constraints.txt requirements.in
```

Observed stdout (excerpt):

- `constraints.txt:51:cryptography>=46.0.5`
- `requirements.in:25:cryptography>=46.0.5,<47.0.0`

Exit code: `0`

### 3) New deterministic dependency guard passes

Command:

```bash
pytest -q tests/test_dependency_security_guard.py
```

Observed stdout (excerpt):

- `..                                                                       [100%]`

Exit code: `0`

### 4) Runtime dependency audit is clean

Command:

```bash
. .venv/bin/activate && pip-audit -r requirements.txt
```

Observed stdout (excerpt):

- `No known vulnerabilities found`

Exit code: `0`

---

## Security brainstorming synthesis (agent-driven)

Coordinator and specialist brainstorming converged on these practical controls:

1. Deterministic floor/deny guard tests for critical packages
2. CI gate that fails on high/critical SCA findings for changed manifests
3. Lockfile integrity check to prevent drift/manual edits
4. PR dependency-diff summary with security impact notes

This PR implements (1) immediately and records (2)-(4) as follow-up hardening in backlog.

---

## Insights (root causes of bot comments)

1. **Traceability drift in docs**
   - Placeholder metadata (`PR: TBD`) survived into review stage.
   - Prevention: treat audit headers as release checklist items before PR ready-for-review.

2. **Evidence claims without file:line anchors**
   - Remediation/prevention statements were correct but not instantly verifiable.
   - Prevention: for every "implemented" claim, attach direct `file:line` pointers in the same paragraph.

3. **Markdown list/code-fence structure fragility**
   - Mixed list nesting + fenced code block placement triggered markdownlint style violations.
   - Prevention: keep fenced blocks indented under their parent list item and run `pre-commit` before push.

4. **Parser strictness feedback loop**
   - Guard logic initially matched one declaration shape; reviewers pushed for multi-declaration robustness.
   - Prevention: prefer requirement-aware parsing and "check all matches" policy in dependency guards.

---

## DoD mapping

- [x] Vulnerable dependency versions removed from all relevant manifests
- [x] Deterministic local guard added and passing
- [x] Security documentation updated with CVE-specific remediation note
- [x] Backlog ledger updated with follow-up prevention tasks
- [ ] GitHub alerts #27/#28/#29/#538/#539 auto-close after post-merge scans refresh

---

## Non-goals

- No distro-level suppression changes (`trivy/ignore-policy.rego` unchanged)
- No runtime business-logic modifications
- No broad dependency refresh unrelated to CVE-2026-26007
