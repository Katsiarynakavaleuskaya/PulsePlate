# Agent instructions (scope: tests/evals/ and subdirectories)

## Purpose
- Keep eval-lane tests deterministic and offline-only.
- Preserve the bootstrap contract without widening request-path runtime scope.

## Hard rules
- Runner import tests must succeed even when eval extras are forced unavailable
- Prefer `monkeypatch` for optional-dependency and filesystem behavior
- Keep dataset and runner assertions deterministic; avoid live provider or network calls
- Bootstrap eval tests must not introduce CI fail thresholds or PASS/NO-GO semantics
