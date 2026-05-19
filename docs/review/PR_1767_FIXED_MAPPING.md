# PR #1767 — Fixed in Commit Mapping

**Supersedes:** <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1760>
**Replacement branch:** `codex/dependabot-pr1760-sentence-transformers-5-5-0`
**Scope:** `sentence-transformers 5.4.1 -> 5.5.0` on optional RAG vector profiles plus exact emergency-wheel fallback alignment.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

Disposition: FIXED
Commit: 7c99fb9e8
Evidence: `requirements-rag-vector.in`, `requirements-rag-vector.txt`, `requirements-rag-vector-cpu.in`, and `requirements-rag-vector-cpu.txt` pin `sentence-transformers==5.5.0`; `scripts/ci/emergency_python_wheels.json` carries the exact `sentence_transformers-5.5.0-py3-none-any.whl` fallback with pinned `sha256`; `tests/test_install_locked_python_requirements.py` guards runtime-effective manifest-to-RAG-profile alignment and avoids treating expired manifest entries as active.

Supersedes Dependabot PR #1760 governance blocker: missing canonical fixed-mapping artifact on the bot PR.

## Role-Agent / Premortem Pass

- `agent-coordinator` initial pass — completed; decision: proceed with changes before commit/push.
- `pulseplate-premortem-risk-review` — completed in `docs/review/PR_1767_PREMORTEM.md`; decision: proceed with changes.
- `cursor-specialist-agent` — completed; stale packet and validation-plan findings FIXED via task packet `artifacts/orchestration/task_packets/4640174232c5.json` and validation-path update.
- `security-auditor` — completed; no supply-chain blocker found, exact sha256 fallback and fail-closed installer contract preserved.
- Codex Security diff-scoped scan — completed through threat-model/discovery; no plausible security candidates found, so validation and attack-path phases were skipped per plugin workflow.
- `qa-engineer-agent` — completed; active-manifest false-green finding FIXED in `tests/test_install_locked_python_requirements.py` and `docs/roadmap/BACKLOG_LEDGER.md`.
- `bug-hunter` — completed; no code-scope blocker, replacement PR/current-head CI remains a post-open requirement.
- `agent-coordinator` final synthesis — completed; decision: proceed to local gates/commit, no readiness claim before replacement PR current-head CI and strict governance.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path requirements-rag-vector-cpu.in --path requirements-rag-vector-cpu.txt --path requirements-rag-vector.in --path requirements-rag-vector.txt --path scripts/ci/emergency_python_wheels.json --path tests/test_install_locked_python_requirements.py --path tests/test_python_supply_chain_controls.py --path docs/roadmap/BACKLOG_LEDGER.md --path docs/review/PR_1767_FIXED_MAPPING.md --path docs/review/PR_1767_PREMORTEM.md` — PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` — PASS.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py` — PASS.
- `. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/activate && make validate-changed` — PASS. Note: the first unactivated `make validate-changed` attempt failed because this isolated worktree has no local `.venv` and `python3` could not import `fastapi`; the activated repo venv rerun passed.
- `pre-commit run --all-files` — PASS after black reformatted `tests/test_install_locked_python_requirements.py` and `.secrets.baseline` was updated for the intentional wheel sha256 fingerprint.
- `git diff --check` — PASS.

## Machine-Heavy Gate Deferral

Full local `make verify` is intentionally deferred under the operator-approved machine-heavy exception for this dependency/governance lane. Merge readiness requires the narrow local gate bundle above plus canonical latest-head CI parity and strict merge-readiness checks.
