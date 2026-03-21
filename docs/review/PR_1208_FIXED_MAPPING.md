# PR 1208 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 34fff143
Evidence: `core/judgment.py:291-294` now normalizes float-like coercion failures to a deterministic `ValueError`, and `core/judgment_eval.py:351-365` keeps low-marker retrieval/evidence confidence tied to `support_ratio` instead of collapsing to a constant.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969313278 -> 34fff143
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969313279 -> 34fff143
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319612 -> 34fff143

Disposition: FIXED
Commit: 2fa6e95e
Evidence: `core/creative_research.py:250-268` rejects non-string scientific fields, `core/creative_research.py:431-445` validates optional scientific-structure strings, `core/creative_research.py:503-517` now safety-screens scientific-structure text, `app/services/creative_research_runtime.py:161-203` fail-closes non-string provider values, `core/judgment.py:239-240` and `core/judgment.py:319-320` hard-reject malformed sequence/scalar payloads, `core/judgment.py:393-396` exports `CalibratedDecision`, `core/judgment_eval.py:104-107`, `core/judgment_eval.py:121`, `core/judgment_eval.py:228-239`, and `core/judgment_eval.py:334-335` tighten replay-pack validation/scoring, `core/insight/philosophy_validator.py:37-42` and `core/insight/philosophy_validator.py:69-72` broaden hard-fail language detection, `core/__init__.py:1-33` keeps the offline eval shim import-light, `tests/test_judgment_eval_contract.py:61-72`, `tests/test_judgment_eval_contract.py:126-145`, `tests/test_judgment_eval_contract.py:190-221`, `tests/test_judgment_core.py:402-537`, `tests/test_fitchef_judgment_replay.py:26-46`, `tests/test_creative_research_eval_contract.py:60-67`, `tests/test_creative_research_runtime_helpers.py:35-63`, and `tests/fixtures/orchestration/creative_research/bundle_negative_controls.json:12-74` lock the regressions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969315172 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969315173 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969315175 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319587 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319590 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319592 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319593 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319594 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319608 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319609 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319611 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319614 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319615 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319616 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#discussion_r2969319617 -> 2fa6e95e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#pullrequestreview-3985876233 -> 2fa6e95e

Disposition: NOT-A-BUG
Evidence: `core/judgment.py:291-294` and `core/judgment_eval.py:351-365`.
Reason: Review `3985794972` is an aggregate shell; its concrete actionable threads are mapped individually above (`2969313278`, `2969313279`) and do not require a separate shell-specific code change.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#pullrequestreview-3985794972

Disposition: NOT-A-BUG
Evidence: `core/creative_research.py:250-268`, `core/creative_research.py:503-517`, `core/judgment_eval.py:228-239`, and `tests/fixtures/orchestration/creative_research/bundle_negative_controls.json:12-74`.
Reason: Review `3985799340` is an aggregate CodeRabbit summary; every actionable item from that review is mapped individually above and resolved by `2fa6e95e`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#pullrequestreview-3985799340

Disposition: NOT-A-BUG
Evidence: `tests/test_judgment_core.py:402-537`, `core/judgment.py:319-320`, `core/judgment_eval.py:104-107`, `core/judgment_eval.py:121`, `core/judgment_eval.py:334-335`, and `core/insight/philosophy_validator.py:69-72`.
Reason: Review `3985799356` is an aggregate Cubic shell; the actionable inline threads from the same review are mapped individually (`34fff143` / `2fa6e95e`) and do not require a separate shell-only fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1208#pullrequestreview-3985799356

## Merge Readiness

- Status: ready for review / not ready to merge.
- Current packet commits:
  - `cd3a3752` — `feat: add fitchef judgment offline eval`
  - `0e28d2ae` — `docs(pr): scaffold pr 1208 governance`
  - `34fff143` — `fix: address sourcery judgment review`
  - `2fa6e95e` — `fix: address bot review follow-ups`
- Current scope discipline:
  - offline eval contract, deterministic evaluator, fixture pack, and safety-validator hardening only
  - no public FitChef route changes
  - no provider, embeddings, or network behavior in the new eval layer
  - backlog anchor: `ledger-p1-fitchef-judgment-offline-eval`
- Required before merge:
  - record every actionable review disposition in this artifact
  - resolve review threads only after disposition evidence exists
  - confirm current-head required checks are green with no pending required jobs
  - confirm no actionable bot comments remain
  - re-run `make verify`
- PR-local validation executed on this lane:
  - `pytest tests/test_creative_research_eval_contract.py tests/test_creative_research_runtime_helpers.py tests/test_fitchef_judgment_replay.py tests/test_judgment_core.py tests/test_judgment_eval_contract.py tests/test_philosophy_validator.py -q`
  - `. .venv/bin/activate && mypy --no-incremental --cache-dir=/dev/null app core`
  - `python -m compileall core app/services tests/test_judgment_core.py tests/test_judgment_eval_contract.py tests/test_philosophy_validator.py tests/test_creative_research_eval_contract.py tests/test_creative_research_runtime_helpers.py tests/test_fitchef_judgment_replay.py`
  - `make verify`
  - `pre-commit run --all-files`
