# PR 1851 Fixed in Commit Mapping

## Disposition summary

All pre-open and post-open agent findings are dispositioned below.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Agent findings

| Finding | Role | Disposition | Evidence |
|---------|------|-------------|----------|
| Missing live-dispatch approval path tests | architecture-specialist | FIXED | Commit `c969c1978` — added `test_execute_mode_with_matching_live_approval_dispatches_dry_run_false`, `test_execute_mode_with_mismatched_live_approval_rejects_dispatch` |
| Missing audit schema assertions | architecture-specialist | FIXED | Commit `c969c1978` — added `test_live_approval_audit_contains_truncated_hash_for_live_dispatch`, `test_dry_run_audit_contains_none_approval_hash` |
| Missing reply formatting tests | architecture-specialist | FIXED | Commit `c969c1978` — added `test_live_dispatch_reply_shows_dry_run_false_and_approval_hash` |
| Approval digest leak risk | security-auditor | NOT-A-BUG | `scripts/orchestration/experiment_slack_socket_bridge.py` — audit stores 16-char prefix only; Slack reply shows 16-char prefix; error message is generic; workflow masks via `::add-mask::` |
| Workflow validation only checks format | security-auditor | NOT-A-BUG | `.github/workflows/experiment-runner-dispatch.yml:78-86` — semantic binding (branch+hypothesis digest match) is enforced by bridge in `_github_dispatch_inputs` before dispatch; workflow step validates SHA256 hex shape as defense-in-depth. Documented in runbook known limitations. |
| Missing `--validate-live-approval` CLI tests | qa-engineer-agent | FIXED | Commit `c969c1978` — added `test_validate_live_approval_cli_passes_for_valid_digest` |
| Missing live-dispatch integration tests | qa-engineer-agent | FIXED | Commit `c969c1978` — added approval match/mismatch/reply/audit tests |
| Missing unsafe input tests for live path | qa-engineer-agent | FIXED | Commit `c969c1978` — added `test_live_dispatch_path_rejects_unsafe_inputs_via_existing_parser` |
| `approval_hash` leaks into non-dispatch commands | bug-hunter | FIXED | Commit `d2194cbd5` — `_audit_payload` and `BridgeDecision` now gate `approval_hash` on `command.kind == "run-experiment"`; test `test_non_dispatch_command_does_not_carry_approval_hash` proves fix |
| Case-sensitivity mismatch | bug-hunter | FIXED | Commit `d2194cbd5` — `_live_approval_sha256` normalizes to lowercase via `.lower()`; test `test_live_approval_sha256_normalizes_uppercase_to_lowercase` proves fix |
| `"none"` sentinel crashes bridge | bug-hunter | FIXED | Commit `d2194cbd5` — `_live_approval_sha256` treats `"none"` / `"NONE"` as `None`; test `test_live_approval_sha256_returns_none_for_absent_and_none_sentinel` proves fix |
| Crash-safety gap (dispatch vs audit write) | bug-hunter | DEFERRED | Backlog: `docs/roadmap/BACKLOG_LEDGER.md` — Slack bridge crash-safety gap between GitHub dispatch transport return and final audit write. Orphaned dispatches require GitHub Actions UI monitoring. Target PR: future bounded reliability PR. |
| Premortem "both workflows" inaccuracy | cursor-specialist-agent | FIXED | Commit `d2194cbd5` — changed to "the dispatch workflow" |
| Premortem duplicate explanations | cursor-specialist-agent | FIXED | Commit `d2194cbd5` — removed duplicate digest computation from revised plan; references runbook instead |
| Premortem not linked from runbook | cursor-specialist-agent | FIXED | Commit `d2194cbd5` — added "See also" link to premortem from runbook Live-Dispatch Approval Gate section |
| `SlackSocketConfigError` leak in `--validate-live-approval` CLI | sourcery-ai | FIXED | Commit `dae9fd3af` — wrapped `_live_approval_sha256()` in `try/except SlackSocketConfigError` in `main()` |
| Duplicated `approval_hash` prefix logic | sourcery-ai | FIXED | Commit `dae9fd3af` — extracted `_approval_prefix(config, command)` helper used by `_audit_payload` and `process_operator_event` |
| Missing `approval_ref` default assertion in contract test | sourcery-ai | FIXED | Commit `dae9fd3af` — added `monkeypatch.delenv(LIVE_APPROVAL_SHA256_ENV)` and `assert dispatch_inputs["approval_ref"] == "none"` |
| Missing "## Discussion Thread Pass" section | coderabbitai | FIXED | Commit `dae9fd3af` — added required section with two checked checkboxes |
| Prematurely checked merge-readiness checkboxes | coderabbitai | FIXED | Commit `dae9fd3af` — unchecked all merge-readiness items until final merge cycle |

### Merge readiness

- [ ] Pre-open agents: agent-coordinator, cursor-specialist-agent, security-auditor, architecture-specialist
- [ ] Post-open agents: qa-engineer-agent, bug-hunter
- [ ] `make validate-changed` passed
- [ ] `make test-fast` passed
- [ ] `pre-commit run --all-files` passed
- [ ] `python3 scripts/orchestration/check_preflight.py` passed
- [ ] `python3 scripts/orchestration/check_agent_consistency.py` passed
- [ ] PR review dry-run report generated (`/tmp/pulseplate_pr_review_context.json`)
- [ ] Full `make verify` — operator-approved machine-heavy PR deferral (focused checks used)

### Experiment Runner evidence

- Co-authored-by trailer included in commits.
- No runner-mutated paths in this PR (operator-authored bridge/test/docs changes only).

---
