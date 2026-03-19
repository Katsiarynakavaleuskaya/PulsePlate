# PR 1191 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: cfa08e46
Evidence: `docs/security/CVE-2026-0540-dompurify.md:9`, `docs/security/CVE-2026-0540-dompurify.md:22`, `docs/security/CVE-2026-0540-dompurify.md:51`
Reason: Replaced brittle line-number evidence anchors with path/key-based dependency truth and clarified that `dompurify` is resolved transitively via `jspdf` with no direct `frontend/src` import.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1191#pullrequestreview-3974789912 -> cfa08e46

Disposition: FIXED
Commit: eec9151b
Evidence: `docs/security/CVE-2026-0540-dompurify.md:78`, `docs/security/CVE-2026-0540-dompurify.md:79`, `docs/security/CVE-2026-0540-dompurify.md:80`
Reason: Clarified that the repo still keeps an active `overrides.dompurify = 3.3.2` safeguard in `frontend/package.json`, so the document no longer implies a pure upstream-resolution path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1191#discussion_r2959777481 -> eec9151b

Disposition: FIXED
Commit: see mapping entries below
Evidence: `docs/security/CVE-2026-0540-dompurify.md:56`, `docs/security/CVE-2026-0540-dompurify.md:57`, `docs/security/CVE-2026-0540-dompurify.md:58`
Reason: Corrected the evidence anchors to point at the actual `package-lock.json` version lines and the `optionalDependencies.dompurify` path, matching the current resolved dependency tree.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1191#pullrequestreview-3974906249 -> 50fc3a7e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1191#discussion_r2959855353 -> 50fc3a7e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1191#pullrequestreview-3974911784 -> 50fc3a7e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1191#discussion_r2959861000 -> 50fc3a7e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1191#discussion_r2959861008 -> 50fc3a7e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1191#discussion_r2959861012 -> 50fc3a7e

## Merge Readiness

- Status: actionables addressed in docs; waiting for current-head CI, thread resolution sync, and the next bot/review wave
- Local validation:
  - `python3 scripts/orchestration/check_preflight.py`
  - `pre-commit run --files docs/security/CVE-2026-0540-dompurify.md`
  - `cd frontend && npm ls jspdf dompurify`
