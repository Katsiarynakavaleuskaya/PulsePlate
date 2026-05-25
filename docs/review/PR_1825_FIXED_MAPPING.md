# PR #1825 - Fixed in Commit Mapping

## PR
- URL: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1825
- Branch: `codex/deps-rag-vector-1805-1806-private-index`
- Base: `main`
- Opening dependency head: `ecb2983751c1c2029acf2bd4a24c9899a082f88d`
- Mapping artifact head before post-open fixes:
  `985351389c35345f8738e528831a3ce809ad2980`
- First post-open review fix commit:
  `ff1927e50` (`fix(deps): address rag-vector review evidence`)

## Summary
Human-owned consolidation for Dependabot #1805 and #1806. The lane aligns the
optional RAG/vector profiles on `transformers==5.9.0` and
`sentence-transformers==5.5.1` while preserving exact, SHA256-pinned,
time-boxed emergency wheel fallback behavior.

## Scope
- `requirements-rag-vector.in`
- `requirements-rag-vector.txt`
- `requirements-rag-vector-cpu.in`
- `requirements-rag-vector-cpu.txt`
- `scripts/ci/emergency_python_wheels.json`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `.secrets.baseline`

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/d7c46569fe56.json`
- Pre-open task packet: `artifacts/orchestration/task_packets/d7c46569fe56.json`
- Experiment Runner packet:
  `artifacts/orchestration/experiments/artifacts/orchestration/experiments/pr1805-1806-rag-vector-oracle-packet.json`
- Experiment Runner result:
  `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/pr1805-1806-rag-vector-oracle-result.json`

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1825#discussion_r3297251985 -> ff1927e50
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1825#pullrequestreview-4355626428 -> ff1927e50
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1825#pullrequestreview-4355606034 -> ff1927e50
Disposition: FIXED
Commit: ff1927e50
Evidence: `scripts/ci/emergency_python_wheels.json:204`, `scripts/ci/emergency_python_wheels.json:219`, `docs/roadmap/BACKLOG_LEDGER.md:577`, `requirements-rag-vector.in:7`, and `requirements-rag-vector-cpu.in:13`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1825#discussion_r3297276710 -> ff1927e50
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1825#pullrequestreview-4355655537 -> ff1927e50
Disposition: FIXED
Commit: ff1927e50
Evidence: PM-DEPS rows below now include post-comment proof metadata; no stray trailing `114` line exists in this artifact.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open bot/human review pass completed.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`.

## Premortem Risk Fix Matrix
| Risk ID | Failure mode | Fix | Evidence | Disposition |
| --- | --- | --- | --- | --- |
| PM-DEPS-001 | Source constraints and compiled locks drift. | Updated RAG/vector `.in` and `.txt` direct pins together. | Focused supply-chain tests and source/lock diff audit. | FIXED - `ff1927e50:requirements-rag-vector.in:7`; `ff1927e50:requirements-rag-vector-cpu.in:13` |
| PM-DEPS-002 | Private Python index cannot serve the new pinned wheel. | Verified direct private-index wheel downloads for both pins. | Private-index `pip download --only-binary=:all: --no-deps` probe. | FIXED - `ff1927e50:scripts/ci/emergency_python_wheels.json:202`; `ff1927e50:scripts/ci/emergency_python_wheels.json:217` |
| PM-DEPS-003 | Emergency wheel manifest becomes stale for newly pinned versions. | Updated exact wheel URLs, SHA256 digests, and `expires_at=2026-06-15`. | `tests/test_install_locked_python_requirements.py`. | FIXED - `ff1927e50:scripts/ci/emergency_python_wheels.json:204`; `ff1927e50:scripts/ci/emergency_python_wheels.json:219` |
| PM-DEPS-004 | PR silently widens profile surface. | Limited diff to RAG/vector profiles, manifest, ledger, and hook-generated baseline. | `git diff --name-status origin/main..HEAD`. | FIXED - `ff1927e50:docs/roadmap/BACKLOG_LEDGER.md:577`; `ff1927e50:requirements-rag-vector.in:7` |
| PM-DEPS-005 | Local `.venv` and CI diverge. | Ran repo `.venv` focused tests and installer preflight; documented heavy local ML limits. | `.venv/bin/python -m pytest -q ...`. | FIXED - `ff1927e50:requirements-rag-vector-cpu.in:13`; `ff1927e50:scripts/ci/emergency_python_wheels.json:204` |
| PM-DEPS-006 | Dependency update breaks import/runtime smoke. | Merge readiness blocks on current-head CI for optional heavy ML closure. | Post-open CI and RAG release gates. | DEFERRED with block before merge readiness |
| PM-DEPS-007 | Dependabot PR conflicts after another dependency PR lands. | Rebased human branch onto `origin/main` after #1824. | Head `985351389c35345f8738e528831a3ce809ad2980` over base `fb754a1e5c4be687a3828506218993154e076793`. | FIXED - `ff1927e50:docs/review/PR_1825_FIXED_MAPPING.md:7`; `ff1927e50:docs/roadmap/BACKLOG_LEDGER.md:577` |
| PM-DEPS-008 | Unsafe package pin appears unintentionally. | No `pip==` unsafe pin introduced in RAG/vector locks. | `rg -n "^pip==" requirements-rag-vector*.txt scripts/ci/emergency_python_wheels.json`. | FIXED - `ff1927e50:requirements-rag-vector.in:9`; `ff1927e50:requirements-rag-vector-cpu.in:15` |
| PM-DEPS-009 | Full `make verify` deferred without sufficient bounded evidence. | Used operator-approved machine-heavy exception with focused gates, pre-commit, Experiment Runner, and CI block. | `pre-commit run --all-files`; current-head CI required before merge. | FIXED - `ff1927e50:docs/review/PR_1825_FIXED_MAPPING.md:96`; `ff1927e50:requirements-rag-vector.in:7` |

## Agent Execution Log
| Agent | Result | Evidence |
| --- | --- | --- |
| agent-coordinator | PASS | Confirmed lane scope, private-index/emergency-wheel constraints, and machine-heavy local exception. |
| architecture-specialist | PASS | Confirmed optional RAG/vector profile isolation. |
| security-auditor | PASS | Confirmed no public-index fallback, no unsafe generic emergency fallback, and no runtime/CI scope drift. |
| dev-operator | PASS | Confirmed private-index wheel download, installer preflight, and staging evidence. |
| qa-engineer-agent | PASS | Re-ran after rebase onto `origin/main` and confirmed focused checks. |
| bug-hunter | PASS | Confirmed prior baseline/ledger blockers were fixed before open. |

Post-open required pass:
- [x] agent-coordinator
- [x] qa-engineer-agent
- [x] bug-hunter
- [x] security-auditor
- [x] architecture-specialist

Post-open findings:
- Coordinator: PASS for scope/order; requested mapping/body cleanup.
- QA: BLOCK until bot comments, mapping/body drift, and CI terminal state are
  resolved.
- Bug-hunter: BLOCK until TTL alignment, proof metadata, PR body, and Sourcery
  feedback are fixed/disposed.
- Security-auditor: BLOCK until supply-chain governance evidence and bot
  comments are fixed/disposed.
- Architecture-specialist: BLOCK until EN/RU ledger drift and governance cleanup
  are resolved; architecture boundaries otherwise PASS.

## Skill Execution Log
- `pulseplate-premortem-risk-review`: risks closed or blocked before merge readiness.
- `pulseplate-pr-review`: pre-open review completed through role-agent passes.
- `pulseplate-gates`: bounded local gate bundle passed.
- `pulseplate-ledger`: active emergency manifest ledger row updated.
- `codex-security:security-scan`: threat model, finding discovery, validation, attack-path analysis, and final report completed with no blocking finding.

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/pr1805-1806-rag-vector-oracle-result.json`
- Status: accepted
- Mode: oracle-only governance reviewer
- `coauthor_required=true`
- Commit trailer present on `ecb2983751c1c2029acf2bd4a24c9899a082f88d`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Gate Evidence
- `python3 scripts/orchestration/check_preflight.py`: PASS
- `python3 scripts/orchestration/check_agent_consistency.py`: PASS
- `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py`: PASS
- `make validate-changed`: PASS with expected no-op signal for no changed Python files
- `python scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md`: PASS
- `pre-commit run --all-files`: PASS
- Pre-push hooks: PASS

## Deferred / Follow-ups
- Full local `make verify` is deferred under the operator-approved machine-heavy
  optional ML dependency exception. Current-head CI, post-open role-agent pass,
  bot dispositions, Phase2 gates, strict merge-readiness wrapper, and wait-window
  remain blocking before merge.

## Merge Readiness
Not merge-ready at artifact creation time.

Required before merge:
- [ ] Current-head CI terminal/pass.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass.
- [ ] Actionable CodeRabbit, Sourcery, Cubic, and human comments disposed.
- [ ] PR Body Phase2 gates pass.
- [ ] Strict merge-readiness wrapper passes with auth.
- [ ] Final wait-window completed.

## Rollback
Revert this PR to restore `sentence-transformers==5.5.0`,
`transformers==5.8.1`, the prior emergency wheel manifest entries, and the
associated `.secrets.baseline` fingerprints.
