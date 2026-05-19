# PR #1767 — Fixed in Commit Mapping

**Supersedes:** <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1760>
**Replacement branch:** `codex/dependabot-pr1760-sentence-transformers-5-5-0`
**Scope:** `sentence-transformers 5.4.1 -> 5.5.0` on optional RAG vector profiles plus exact emergency-wheel fallback alignment.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1767#pullrequestreview-4318257613 -> d23616f72
Disposition: FIXED
Commit: d23616f72
Evidence: Cubic review-level finding is fixed by canonical replacement artifact names, checked required mapping boxes, raw commit proof, and parser-safe implementation evidence placement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1767#discussion_r3265717327 -> d23616f72
Disposition: FIXED
Commit: d23616f72
Evidence: Cubic inline commit-proof finding is fixed by using canonical `docs/review/PR_1767_FIXED_MAPPING.md` and raw parser-safe commit proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1767#discussion_r3265719096 -> d23616f72
Disposition: FIXED
Commit: d23616f72
Evidence: CodeRabbit checkbox finding is fixed by marking the required artifact discussion and fixed-mapping checkboxes complete.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1767#pullrequestreview-4318259512 -> d23616f72
Disposition: FIXED
Commit: d23616f72
Evidence: CodeRabbit review-level actionable is fixed by the same canonical checkbox and mapping artifact correction as the inline finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1767#discussion_r3265735783 -> f747a8aa6
Disposition: FIXED
Commit: f747a8aa6
Evidence: Codex governance finding about non-mapping bullets is fixed by keeping the parser-sensitive mapping section limited to URL/disposition/proof blocks and moving implementation details outside it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1767#discussion_r3265735791 -> f747a8aa6
Disposition: FIXED
Commit: f747a8aa6
Evidence: Codex governance finding about raw SHA proof is fixed by using raw hex commit values in the mapping artifact.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1767#discussion_r3265735797 -> f747a8aa6
Disposition: FIXED
Commit: f747a8aa6
Evidence: Codex governance finding about required mapping checkboxes is fixed by keeping both artifact checkboxes checked.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1767#discussion_r3265735803 -> f747a8aa6
Disposition: FIXED
Commit: f747a8aa6
Evidence: Codex governance finding about replacement PR artifact naming is fixed by using `PR_1767_FIXED_MAPPING.md` and `PR_1767_PREMORTEM.md`.

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
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1767` — PASS after PR body mirror normalization.
- `GH_TOKEN` exported: `python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1767 --require-auth` — PASS for all 6 resolved review threads.
- `GITHUB_TOKEN`/`GH_TOKEN` exported: `python3 scripts/ci/check_pr_merge_readiness.py --pr-number 1767 --repo Katsiarynakavaleuskaya/PulsePlate` — PASS for review governance; current-head CI remains a separate live gate.

## Machine-Heavy Gate Deferral

Full local `make verify` is intentionally deferred under the operator-approved machine-heavy exception for this dependency/governance lane. Merge readiness requires the narrow local gate bundle above plus canonical latest-head CI parity and strict merge-readiness checks.
