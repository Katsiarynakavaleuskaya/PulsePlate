# PR 1711 Fixed Mapping - Production GnuTLS Alert Surface

## Summary

PR #1711 follows PATH A for GitHub Security code-scanning alerts
`security/code-scanning/591`, `security/code-scanning/592`, and
`security/code-scanning/593`: remove the production-only Debian
package-manager/GnuTLS surface from the final `production` image instead of
adding Trivy suppressions.

Primary implementation commit:

- `4b5a20080` - `fix(container): prune production gnutls surface`

## Scope

- Remove `apt`, `gpgv`, and `libgnutls30` from the final `production` stage.
- Keep `runtime-base` usable for development workflows that need `apt`.
- Fail closed in the Dockerfile if blocked Debian packages remain installed.
- Extend `scripts/ci/check_docker_runtime_dependency_surface.py` to support exact
  Debian package blocklists.
- Wire `build.yml` and `trivy.yml` to block `apt`, `gpgv`, and `libgnutls30`.
- Add per-CVE documentation with upstream/Debian/OSV source links and alert
  disposition rules.

## Role Order

Declared role order:

1. `agent-coordinator`
2. `security-auditor`
3. `architecture-specialist`
4. `dev-operator`
5. `qa-engineer-agent`
6. `bug-hunter`

Coordinator packets:

- Pre-open: `605b7deca02e`
- Post-open: `d0002eb4bac5`

Mandatory post-open pass:

- `qa-engineer-agent`: pending final response at artifact creation time.
- `bug-hunter`: pending, must run after `qa-engineer-agent`.

## Security Alert Disposition

Do not resolve or mark these alerts fixed until current-head Docker/Trivy
evidence proves the final `production` image no longer contains
`libgnutls30`.

- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/591`
  - CVE: `CVE-2026-3833`
  - Advisory: `GNUTLS-SA-2026-04-29-5`
  - Disposition: `PENDING FIXED EVIDENCE`
  - Implementation commit: `4b5a20080`
  - Required evidence before `FIXED`: final production image `dpkg-query -W
    libgnutls30` absence evidence, production smoke evidence, and current-head
    Trivy/code-scanning pass.
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/592`
  - CVE: `CVE-2026-42010`
  - Advisory: `GNUTLS-SA-2026-04-29-4`
  - Disposition: `PENDING FIXED EVIDENCE`
  - Implementation commit: `4b5a20080`
  - Required evidence before `FIXED`: final production image `dpkg-query -W
    libgnutls30` absence evidence, production smoke evidence, and current-head
    Trivy/code-scanning pass.
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/593`
  - CVE: `CVE-2026-42011`
  - Advisory: `GNUTLS-SA-2026-04-29-6`
  - Disposition: `PENDING FIXED EVIDENCE`
  - Implementation commit: `4b5a20080`
  - Required evidence before `FIXED`: final production image `dpkg-query -W
    libgnutls30` absence evidence, production smoke evidence, and current-head
    Trivy/code-scanning pass.

## Premortem Summary

- Risk: production hardening could remove Debian-essential package-manager
  packages in a way that leaves config-only dpkg records. Disposition:
  `FIXED` by checking installed status (`ii`) rather than package-name
  presence alone; scanner closure still depends on final Trivy evidence.
- Risk: production hardening could break Python TLS. Disposition: `FIXED` by
  Dockerfile `import ssl` fail-closed assertion.
- Risk: staging inherits production and may lose `apt`. Disposition:
  `NOT-A-BUG`; `docs/deploy/DOCKER.md` documents that staging currently extends
  production and inherits this hardening.
- Risk: local Docker validation is machine-heavy on the operator host.
  Disposition: `DEFERRED`; PR body and this artifact require current-head
  Docker/Trivy CI evidence before any fixed claim.

## Validation

Local bounded validation:

- `python3 scripts/orchestration/check_preflight.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/ci/check_trivy_ignore_policy_expiry.py` - PASS
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-3833-gnutls.md docs/security/CVE-2026-42010-gnutls.md docs/security/CVE-2026-42011-gnutls.md docs/deploy/DOCKER.md` - PASS
- `. .venv/bin/activate && python -m pytest -q tests/test_docker_runtime_dependency_surface.py tests/test_python_supply_chain_controls.py::test_production_target_docker_workflows_run_runtime_surface_guard tests/test_docker_workflow_build_path_contract.py::test_production_dockerfile_prunes_package_manager_surface` - PASS (`17 passed`)
- `make validate-changed` - PASS; branch selector reported no committed Python
  files before the first commit, so focused pytest is the Python guard evidence.
- `pre-commit run --files ...` for changed files - PASS
- Commit hook - PASS
- Push hook - PASS, including `mypy (type-check, changed files)`,
  `pip-audit`, `backend tests (pytest, pre-push)`, `bandit (pre-push, full
  repo)`, and `docker build test`.

Deferred local validation:

- Full local `make verify` deferred under the operator-approved machine-heavy
  exception.
- Full local `pre-commit run --all-files` attempted but stopped after
  `check-added-large-files` hung on a full-repo file list; scoped pre-commit,
  commit hook, and push hook passed.
- Local production Docker smoke and final-image `dpkg-query` evidence deferred
  after operator CPU-safety stop.

Required current-head evidence before merge readiness:

- `docker build --pull --target production ...` PASS
- `/health` smoke PASS
- `/openapi.json` smoke PASS
- `/api/v1/bodyfat` smoke PASS or expected non-404 contract response
- `dpkg-query -W libgnutls30` fails in the final production image
- Trivy/code-scanning no longer reports the three GnuTLS alerts for the final
  production image

## Merge Readiness

- [ ] Current-head required CI is green.
- [ ] Current-head Docker/Trivy evidence proves `libgnutls30` absent.
- [ ] CodeRabbit no-actionables.
- [ ] Sourcery no-actionables.
- [ ] Cubic no-actionables.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass complete.
- [ ] Strict merge-readiness wrapper passes with auth.
