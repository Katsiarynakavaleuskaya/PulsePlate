# PyTorch `torch.jit.script` CVE-2025-3000 advisory

## Summary

`pip-audit` flags `torch` in the optional RAG/vector manifests for
`CVE-2025-3000` / `GHSA-rrmf-rvhw-rf47`. The advisory concerns
`torch.jit.script` memory corruption. PulsePlate keeps `torch` out of the
default production, CI-lite, Docker runtime, and full lock manifests; the
finding is limited to the optional vector profile.

## Governance

- **Owner:** @katsiaryna_kavaleuskaya
- **Remove-by:** 2026-07-17
- **Backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile`
- **pip-audit waiver:** `scripts/ci_pip_audit.sh`
- **Last checked:** 2026-06-24

## Current Repo State

- `requirements.txt`: no direct `torch` pin.
- `requirements-ci-lite.txt`: no direct `torch` pin; any GitHub alert on this
  file is treated as dependency-graph lag unless a future diff reintroduces
  torch here.
- `requirements-docker-runtime.txt`: no direct `torch` pin.
- `requirements-lock.txt`: no direct `torch` pin.
- `requirements-rag-vector.txt`: `pip-audit` flags `torch==2.11.0`.
- `requirements-rag-vector-cpu.txt`: `torch==2.11.0+cpu` remains in the optional
  Linux CPU lock.
- GitHub Advisory `GHSA-rrmf-rvhw-rf47`: affected `torch <= 2.12.0`.
  Patched versions: none.
- PyPI latest `torch` release observed on 2026-06-18: `2.12.1`, but the
  GitHub Advisory Database still reports patched versions as none for
  `GHSA-rrmf-rvhw-rf47`. Do not treat a newer release as fixed until advisory
  and private-index evidence agree.
- `pip-audit` reports `CVE-2025-3000` with no `fix_versions`.

## Evidence Anchors

- `requirements-rag-vector.txt:162`
- `requirements-rag-vector-cpu.txt:119`
- `scripts/ci_pip_audit.sh:40`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile`

## Exposure Assessment

The vulnerable surface is tied to PyTorch TorchScript (`torch.jit.script`) in an
optional vector/RAG dependency profile. It is not installed by the default
production or Docker runtime manifests. Reassess immediately if product runtime
starts loading the vector profile by default, accepts untrusted TorchScript
artifacts, or routes user-controlled data into TorchScript compilation.

## Remediation

1. Prefer a fixed `torch` release when OSV, GitHub Advisory Database, pip-audit, or
   PyTorch upstream publishes one that satisfies the private package index.
2. If no fixed release exists by the remove-by date, decide between extending
   this waiver with fresh evidence, replacing the vector backend, or removing
   TorchScript-dependent capability from the optional profile.
3. Remove the `CVE-2025-3000` pip-audit waiver from `scripts/ci_pip_audit.sh` in
   the same PR that closes the backlog item.

## References

- CVE: `https://www.cve.org/CVERecord?id=CVE-2025-3000`
- NVD: `https://nvd.nist.gov/vuln/detail/CVE-2025-3000`
- GitHub Advisory Database: `https://github.com/advisories/GHSA-rrmf-rvhw-rf47`
- PyPI torch: `https://pypi.org/project/torch/`
