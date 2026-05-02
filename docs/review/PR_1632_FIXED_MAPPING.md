# PR 1632 Fixed Mapping

## Summary

Evaluation validity substrate PR for deterministic invariance, mutation, and worst-case reporting.

Branch: `evals/evaluation-validity-substrate`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Review Thread Dispositions

### Codex (chatgpt-codex-connector[bot])

1. **r3177263714** — P1: Remove sys.path.insert from eval test modules
   - Disposition: FIXED
   - Commit: 699da4769
   - Evidence: `tests/evals/conftest.py:16` (moved sys.path.insert to allowlisted conftest)

2. **r3177263716** — P1: Reject non-finite scores during outcome validation
   - Disposition: FIXED
   - Commit: 699da4769
   - Evidence: `scripts/evals/eval_validity_contract.py:139` (math.isfinite check)

### Cubic (cubic-dev-ai[bot])

3. **r3177271030** — P1: sys.path.insert forbidden in tests
   - Disposition: FIXED (same fix as #1)
   - Commit: 699da4769
   - Evidence: `tests/evals/conftest.py:16`

4. **r3177271031** — P1: Missing canonical baseline default 0.0
   - Disposition: FIXED
   - Commit: 699da4769
   - Evidence: `scripts/evals/eval_validity_contract.py:226` (raises ValueError instead of defaulting to 0.0)

5. **r3177271033** — P1: Reject non-finite score values
   - Disposition: FIXED (same fix as #2)
   - Commit: 699da4769
   - Evidence: `scripts/evals/eval_validity_contract.py:139`

6. **r3177271034** — P2: Avoid mutating sys.path in test file
   - Disposition: FIXED (same fix as #1)
   - Commit: 699da4769
   - Evidence: `tests/evals/conftest.py:16`

7. **r3177271035** — P2: artifacts/evals/ not in .gitignore
   - Disposition: FIXED
   - Commit: 699da4769
   - Evidence: `.gitignore:242` (added `artifacts/evals/`)

8. **r3177271036** — P2: Boolean score accepted as numeric
   - Disposition: FIXED
   - Commit: 699da4769
   - Evidence: `scripts/evals/eval_validity_contract.py:137` (explicit bool rejection before numeric check)

9. **r3177271038** — P2: Replace placeholder in mapping artifact
   - Disposition: FIXED
   - Commit: 699da4769
   - Evidence: This artifact (canonical mapping content)

10. **r3177271039** — P2: Use canonical Discussion Thread Pass section
    - Disposition: FIXED
    - Commit: 699da4769
    - Evidence: PR body and this artifact updated with canonical format

### CodeRabbit (coderabbitai[bot])

11. **r3177275456** — Minor: Add gitignore for generated validity report artifacts
    - Disposition: FIXED (same fix as #7)
    - Commit: 699da4769
    - Evidence: `.gitignore:242`

12. **r3177275459** — Major: Use canonical fixed-mapping sections and required checkboxes
    - Disposition: FIXED (same fix as #9/#10)
    - Commit: 699da4769
    - Evidence: This artifact

13. **r3177275460** — Minor: Add DoD bullet for generated reports
    - Disposition: DEFERRED
    - Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-evaluation-validity-substrate`
    - Reason: Minor documentation enhancement; DoD for local artifacts is already covered by root AGENTS.md local-only artifacts rule

14. **r3177275462** — Major: Fail-closed validators coerce malformed records (str/list/dict)
    - Disposition: DEFERRED
    - Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-evaluation-validity-substrate`
    - Reason: Bool score fix applied (highest-impact coercion); remaining str/list/dict coercions are lower risk for the deterministic offline contract; follow-up PR

15. **r3177275465** — Major: mutation_drop should not default missing canonical baseline to 0.0
    - Disposition: FIXED (same fix as #4)
    - Commit: 699da4769
    - Evidence: `scripts/evals/eval_validity_contract.py:226`

16. **r3177275468** — Major: Remove sys.path.insert from test module (contract tests)
    - Disposition: FIXED (same fix as #1)
    - Commit: 699da4769
    - Evidence: `tests/evals/conftest.py:16`

17. **r3177275470** — Major: Drop sys.path.insert from test file (runner tests)
    - Disposition: FIXED (same fix as #1)
    - Commit: 699da4769
    - Evidence: `tests/evals/conftest.py:16`

18. **r3177283292** — Minor: Make determinism assertion encoding-explicit
    - Disposition: FIXED
    - Commit: PENDING_SHA
    - Evidence: `tests/evals/test_run_eval_validity.py:75` (added `encoding="utf-8"`)

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177263714 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177263716 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177271030 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177271031 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177271033 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177271034 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177271035 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177271036 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177271038 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177271039 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177275456 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177275459 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177275460
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177275462
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177275465 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177275468 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177275470 -> 699da47691fada67396465b0fa7da9de27f38482
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1632#discussion_r3177283292 -> PENDING_SHA

## Merge Readiness Evidence

Pending current-head CI after second fix commit.
