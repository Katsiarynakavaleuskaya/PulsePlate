# Dependabot Alert Inventory - 2026-06-22

This inventory is the PR #2008 source of truth for the seven open Dependabot
alerts observed on 2026-06-22. It intentionally keeps raw Dependabot branches
out of the merge path when they overlap lock/profile surfaces or cannot prove
the current repo-owned dependency path.

## Current Open Alerts

| Alert | Advisory / CVE | Package | Manifest | Dependency type | Install profile | Production exposure | Fixed version | Proxy availability | Owner PR | Disposition | Evidence | Recheck date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| #227 | GHSA-6v7p-g79w-8964 | msgpack | requirements-lock.txt | runtime | combined lock | Potential only if the combined lock is installed in runtime; no product msgpack import proven | 1.2.1 | Available through configured Python package resolution; broad resolver churn avoided | PR #2008 | FIXED in PR #2008 by pinning msgpack 1.2.1 and blocking <1.2.1 | requirements-lock.txt:210, tests/fixtures/dependency_security_schema.json:16, docs/security/GHSA-6v7p-g79w-8964-msgpack.md | After PR #2008 merge and GitHub dependency graph refresh |
| #226 | GHSA-6v7p-g79w-8964 | msgpack | requirements-dev.txt | development | dev tooling | Dev tooling exposure through CacheControl / pip-audit graph | 1.2.1 | Available through configured Python package resolution; broad resolver churn avoided | PR #2008 | FIXED in PR #2008 by adding the dev floor and pinning msgpack 1.2.1 | requirements-dev.in:27, requirements-dev.txt:108, tests/fixtures/dependency_security_schema.json:16, docs/security/GHSA-6v7p-g79w-8964-msgpack.md | After PR #2008 merge and GitHub dependency graph refresh |
| #225 | GHSA-6v7p-g79w-8964 | msgpack | requirements-ci-lite.txt | runtime | ci-lite | Not reproduced from current repo manifests; ci-lite has no direct cachecontrol or msgpack entry | 1.2.1 | Available, but do not add unused ci-lite packages without proving the dependency path | PR #2008 inventory, future recheck lane if it persists | DEFERRED recheck after PR #2008 refresh | docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-msgpack-ci-lite-alert-recheck, requirements-ci-lite.in, requirements-ci-lite.txt | 2026-06-29 |
| #224 | GHSA-98m9-hrrm-r99r / CVE-2026-54297 | faraday | ios/Gemfile.lock | runtime | iOS Fastlane release tooling | Release tooling graph, not application runtime | >= 2.14.3 | RubyGems fixed version exists, but Fastlane still constrains faraday 1.x | Future Fastlane/faraday remediation lane | DEFERRED until Fastlane permits faraday >=2.14.3 or release tooling path changes | docs/security/CVE-2026-54297-faraday-fastlane.md, docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-faraday-cve-2026-54297 | 2026-07-17 |
| #162 | GHSA-rrmf-rvhw-rf47 / CVE-2025-3000 | torch | requirements-ci-lite.txt | runtime | ci-lite | Not reproduced from current ci-lite manifests; no direct torch pin | No GHSA fixed version | No fixed GHSA version published; monitor Safety/GHSA/PyTorch/private index | Future torch advisory lane | DEFERRED / monitored | docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md, docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile | 2026-07-17 |
| #161 | GHSA-rrmf-rvhw-rf47 / CVE-2025-3000 | torch | requirements-rag-vector-cpu.txt | runtime | optional RAG/vector CPU | Optional vector profile; no default application install exposure proven | No GHSA fixed version | No fixed GHSA version published; monitor Safety/GHSA/PyTorch/private index | Future torch advisory lane | DEFERRED / monitored | docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md, docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile | 2026-07-17 |
| #160 | GHSA-rrmf-rvhw-rf47 / CVE-2025-3000 | torch | requirements-rag-vector.txt | runtime | optional RAG/vector | Optional vector profile; no default application install exposure proven | No GHSA fixed version | No fixed GHSA version published; monitor Safety/GHSA/PyTorch/private index | Future torch advisory lane | DEFERRED / monitored | docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md, docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile | 2026-07-17 |

## Raw Dependabot PR No-Go

Do not merge raw Dependabot PRs #2000 through #2004 from this lane:

- #2000 updates msgpack but is Dependabot-owned and does not carry the repo
  guard/backlog/inventory evidence required for this security lane.
- #2001, #2002, #2003, and #2004 touch broader testing, quality, and vector
  profile surfaces. Those overlap active lock/profile governance and must remain
  outside the PR #2008 remediation.

## Future Owner Lanes

1. PR #2008 owns the msgpack remediation for the repo-owned dev/full-lock pins
   and the current seven-alert inventory.
2. The `requirements-ci-lite.txt` msgpack alert #225 is a recheck lane only
   unless GitHub's refreshed dependency graph proves a current repo-owned
   ci-lite path.
3. Faraday remains a Fastlane/release-tooling lane, blocked on a compatible
   Fastlane path or a release-tooling migration.
4. Torch remains an optional RAG/vector advisory lane until advisory metadata and
   available package indexes expose a fixed version.
5. The broader Python dependency surface contract is tracked separately in
   `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-python-dependency-surface-contract`.
