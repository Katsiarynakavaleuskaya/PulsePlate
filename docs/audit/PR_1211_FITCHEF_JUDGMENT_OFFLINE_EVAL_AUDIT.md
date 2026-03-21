# PR 1211 — FitChef Judgment Offline Eval Audit

## Scope

This audit covers the PR-B closeout slice for deterministic FitChef judgment replay evaluation only. The change remains internal-first and additive:

- continuity-only replay fields stay inside the offline evaluator and fixtures
- no public API or schema changes were introduced
- no runtime FitChef route behavior changed
- no provider, network, realtime, or hidden-memory behavior was added

## Evidence

- `core/judgment_eval.py:41` introduces continuity-only replay records for turns, context snapshots, and continuity checks.
- `core/judgment_eval.py:164` validates optional replay continuity inputs fail-closed, including canonical replay roles.
- `core/judgment_eval.py:269` strips only a trailing current-user prompt from visible history, preserving assistant echoes in replay history.
- `core/judgment_eval.py:449` enforces continuity cases to start with a user turn and to include at least one prior user turn before continuity markers are accepted.
- `core/judgment_eval.py:524` keeps the direct-call fail-closed guard for ungrounded context references, while `core/judgment_eval.py:668` emits `continuity_report` as internal eval metadata only.
- `scripts/orchestration/judgment_eval.py:26` scopes offline runner artifacts under `artifacts/orchestration/judgment/evals`, and `scripts/orchestration/judgment_eval.py:72` fails fast on unexpected replay decisions or write errors.
- `scripts/orchestration/judgment_eval_contract.py:12` re-exports the additive continuity contract surface for orchestration callers.
- `tests/fixtures/orchestration/fitchef_judgment_replay/replay_cases.json:1` freezes top-level `bundle_id` and `scenario_family` on the primary replay pack.
- `tests/fixtures/orchestration/fitchef_judgment_replay/replay_continuity_cases.json:1` adds bounded 3-5 turn continuity fixtures for carry-forward, safe degradation, and fabricated-memory blocking, including a grounded prior-user history for the fabricated-memory case at `tests/fixtures/orchestration/fitchef_judgment_replay/replay_continuity_cases.json:156`.
- `tests/test_judgment_eval_contract.py:62` covers validation failures and continuity-specific evaluator branches, including leading-user and trailing-assistant history edge cases at `tests/test_judgment_eval_contract.py:230`.
- `tests/test_fitchef_judgment_replay.py:22` locks the primary replay pack decisions and exact hard-fail reason sets.
- `tests/test_fitchef_judgment_continuity_replay.py:26` locks the continuity replay pack decisions, uncertainty labels, and continuity reports.
- `tests/test_judgment_eval.py:21` covers offline runner artifact writes, malformed/non-object JSON rejection, output-path escaping, unknown decision rejection, and write-failure handling.
- `docs/orchestration/contracts/JUDGMENT_EVAL_CONTRACT.md:16` documents the additive replay bundle fields and continuity report semantics.

## Validation

- `pre-commit run --all-files`
- `make lint`
- `make typecheck`
- `make test-fast`
- `make diff-cov`
- `pytest -q tests/test_judgment_eval_contract.py tests/test_fitchef_judgment_replay.py tests/test_fitchef_judgment_continuity_replay.py tests/test_judgment_eval.py`

## Security Notes

The new continuity lane uses synthetic replay fixtures only and does not persist user memory. Fabricated-memory detection is evaluated offline through explicit markers, and output artifacts remain under the gitignored `artifacts/` tree.

## Decision

PR 1211 is a bounded offline-eval extension of the existing FitChef judgment seam. It is suitable for review as an internal-only judgment quality gate ahead of any later hidden pilot or runtime rollout.
