# Dependabot Alerts 110-113 Remediation Task Packet

## Summary

- **Date:** 16 April 2026
- **Stable starting branch:** `main`
- **Bundled alerts:** `#110`, `#111`, `#112`, `#113`
- **Packages:**
  - `python-multipart` (`GHSA-mj87-hwqh-73pj`, `CVE-2026-40347`)
  - `dompurify` (`GHSA-39q2-94rc-95cp`)
- **Patched floors:**
  - `python-multipart >= 0.0.26`
  - `dompurify >= 3.4.0`
- **Lane mode:** single coordinator-owned remediation PR with explicit post-open regression review

This packet governs the combined remediation lane for the four currently open
Dependabot alerts that map to two independent dependency families:
`python-multipart` across the Python requirement surfaces and `dompurify` in the
frontend npm lock tree. The lane is intentionally narrow: dependency floors,
lock regeneration, security evidence, regression verification, and merge
governance only.

## Current-Head Truth

- GitHub Dependabot currently reports:
  - `#110` — `python-multipart` in `requirements-lock.txt`
  - `#111` — `python-multipart` in `requirements.txt`
  - `#112` — `python-multipart` in `requirements-ci-lite.txt`
  - `#113` — `dompurify` in `frontend/package-lock.json`
- Current repo evidence before remediation:
  - `requirements.in:18` — `python-multipart>=0.0.20,<1.0.0`
  - `requirements.txt:195` — `python-multipart==0.0.22`
  - `requirements-lock.txt:441` — `python-multipart==0.0.22`
  - `requirements-ci-lite.in:23` — `python-multipart>=0.0.20,<1.0.0`
  - `requirements-ci-lite.txt:301` — `python-multipart==0.0.22`
  - `constraints.txt:43` — `python-multipart>=0.0.20`
  - `frontend/package.json:89` — `overrides.dompurify = 3.3.2`
  - `frontend/package-lock.json:5885` — `node_modules/dompurify`
  - `frontend/package-lock.json:5887` — resolved tarball `dompurify-3.3.2.tgz`
- Existing guard/evidence surfaces already cover both ecosystems:
  - `tests/test_dependency_security_guard.py`
  - `tests/test_frontend_dependency_guards.py`

## Mandatory Role Order

1. `agent-coordinator`
2. `backend-engineer`
3. `frontend-engineer`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`

Rules:

- This order is mandatory for the lane.
- `qa-engineer-agent -> bug-hunter` remains the required post-open review pass.
- No unrelated runtime, OpenAPI, design, or release-surface work may piggyback
  on this PR.

## Scope Lock

### In scope

- Raise the `python-multipart` security floor to `0.0.26` across the repo's
  Python dependency source and lock surfaces
- Raise the frontend `dompurify` override/lock resolution to `3.4.0`
- Update deterministic dependency guards where the new floors become policy
- Add/update security evidence docs for the two alert families
- Run targeted checks plus canonical quality gates
- Open a PR, run the post-open review lane, and prepare merge-readiness artifacts

### Out of scope

- Unrelated package upgrades
- OpenAPI regeneration
- Backend or frontend behavior changes unrelated to dependency remediation
- Broad recurring-drift or ecosystem-policy refactors

## Acceptance Criteria

- All four alerts have a concrete remediation path in committed manifests/locks
- `python-multipart` is at `>=0.0.26` in source surfaces and pinned to `0.0.26`
  in regenerated locks
- `dompurify` resolves to `3.4.0` from the npm registry in the frontend lockfile
- Python and frontend dependency guards reflect the patched floors
- Security notes include `file:line` evidence and validation commands
- Post-open review completes in mandatory order `qa-engineer-agent -> bug-hunter`
- Merge-readiness uses current-head truth only

## Evidence Requirements

- Live alert queries:
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/110`
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/111`
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/112`
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/113`
- Python repo evidence:
  - `requirements.in:18`
  - `requirements.txt:195`
  - `requirements-lock.txt:441`
  - `requirements-ci-lite.in:23`
  - `requirements-ci-lite.txt:301`
  - `constraints.txt:43`
- Frontend repo evidence:
  - `frontend/package.json:89`
  - `frontend/package-lock.json:5885`
  - `frontend/package-lock.json:5887`
- Guard evidence:
  - `tests/test_dependency_security_guard.py`
  - `tests/test_frontend_dependency_guards.py`

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
pytest -q tests/test_dependency_security_guard.py
pytest -q tests/test_frontend_dependency_guards.py
pre-commit run --all-files
make verify
```

## Merge / Post-Merge Rule

- Do not call the lane merge-ready until:
  - local gates are green,
  - post-open `qa-engineer-agent -> bug-hunter` review is complete,
  - current-head required checks are green,
  - the canonical review artifact and PR body mirror are synced.
- After merge:
  - `git fetch --prune origin`
  - remove merged local/remote branch
  - remove merged worktree if one exists
  - `git worktree prune`
  - confirm no tracked local artifacts or stale `worktrees/` paths remain
