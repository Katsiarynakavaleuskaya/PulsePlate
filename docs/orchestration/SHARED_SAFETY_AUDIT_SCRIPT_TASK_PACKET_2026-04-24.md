# Shared Safety Audit Script Task Packet - 2026-04-24

Status: Active PR-8 slice in the Docker / CI / Security discipline series

## Summary

After signed Docker provenance landed in `PR #1503`, this slice extracts the
duplicated Safety multi-manifest dependency-audit loop from the canonical CI and
Security workflows into one shared helper under `scripts/ci/`.

## Branch / worktree

- Branch: `codex/shared-safety-audit-script`
- Worktree: `worktrees/shared-safety-audit-pr8`
- Draft PR: `#1515`

## Mandatory role order

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `backend-engineer`
5. `dev-operator`
6. post-open `qa-engineer-agent`
7. post-open `bug-hunter`

No ad hoc role stack may replace this order.

## Scope

- add `scripts/ci/run_safety_audit.py` as the canonical Safety audit helper
- auto-discover `requirements.txt` plus optional Docker runtime and RAG vector manifests
- prefer `safety-policy.yaml` over `safety-policy.toml`
- emit deterministic `safety-<stem>.json`, `safety-<stem>.txt`, and `safety-<stem>.log`
- fail closed on missing reports, invalid JSON, execution errors, and
  HIGH/CRITICAL/UNKNOWN findings
- keep LOW/MEDIUM findings as warnings
- delegate both `.github/workflows/ci.yml` and `.github/workflows/security.yml`
  to the shared helper
- keep `.github/scripts/parse-safety-report.py` only as a thin compatibility wrapper

## Non-goals

- no Docker build-path consolidation or digest reuse
- no Docker base-image change
- no requirements-profile split
- no Dagger/control-plane work
- no SBOM/VEX signed security-artifact expansion

## Acceptance criteria

- `ci.yml` and `security.yml` both call `python3 scripts/ci/run_safety_audit.py`
- duplicated shell Safety loops are removed from both workflows
- workflow artifact upload still includes `safety-*.json`, `safety-*.txt`, and `safety-*.log`
- helper tests cover manifest discovery, artifact names, policy precedence,
  fail-closed parsing, and severity aggregation
- workflow-contract tests prove both workflows delegate to the shared helper

## Validation plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py`
- `pre-commit run --all-files`
- current-head GitHub checks for draft PR `#1515`
- strict merge wrapper before any merge claim

## Follow-ups

- Docker workflow build-path consolidation / image digest reuse remains a
  separate follow-up candidate from the analyst report.
- Dagger remains deferred until Docker baseline/provenance work stays stable.
- SBOM/VEX signed security artifacts remain blocked by release-truth criteria.
