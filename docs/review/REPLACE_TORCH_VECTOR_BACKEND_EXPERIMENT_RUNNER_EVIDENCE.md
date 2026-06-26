# Replace PyTorch Vector Backend - Experiment Runner Evidence

## Purpose

Committed summary for the local Experiment Runner oracle-only governance review
used by this PR. Raw Experiment Runner JSON artifacts remain under gitignored
`artifacts/` by repo policy, so this document records the verifiable fields used
for PR governance without tracking the local runtime artifact.

## Local Result

- Path: `artifacts/orchestration/experiments/results/exp-dd6e071fdff3.json`
- SHA-256: `e5190fef8515830dadb0ac722c9f9b3b6a7110892413d547531ace1bbd0f2c56`
- Experiment ID: `exp-dd6e071fdff3`
- Runner mode: `oracle_only_governance_reviewer`
- Review outcome: `accepted`
- Failure class: `None`
- Shared tree untouched: `true`
- Source diff applied in isolated checkout: `true`
- Source diff path count: `27`
- Mutated paths in raw local result: `[]`

## Oracle Commands

- `git diff --check` - PASS, return code 0.
- `python -m pytest -q tests/test_embeddings_provider.py tests/test_vector_rag.py` - PASS, return code 0.
- `python -m pytest -q tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py tests/test_install_locked_python_requirements.py tests/test_ci_risk_profile.py tests/test_pgvector_embedding_migration.py` - PASS, return code 0.

## Attribution Scope

The raw result marks `coauthor_required=true` with contribution kind
`oracle_review` because the oracle-only governance result shaped the final
validation and commit decision. Commits that include the implementation should
therefore use the canonical trailer:

`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

This summary is not merge-readiness proof. It records local oracle evidence only;
PR current-head CI, post-open role passes, Codex Security review, bot review
dispositions, and merge-readiness checks remain separate gates.
