# PyTorch `torch.jit.script` CVE-2025-3000 advisory

## Summary

Safety flags `torch` in the optional RAG/vector manifests for
`SFTY-20250331-30014` / `CVE-2025-3000`. The advisory concerns
`torch.jit.script` memory corruption. PulsePlate keeps `torch` out of the
default production, CI-lite, Docker runtime, and full lock manifests; the
finding is limited to the optional vector profile.

## Governance

- **Owner:** @katsiaryna_kavaleuskaya
- **Remove-by:** 2026-07-17
- **Backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile`
- **Safety policy:** `safety-policy.yaml`
- **Last checked:** 2026-06-18

## Current Repo State

- `requirements.txt`: no direct `torch` pin.
- `requirements-ci-lite.txt`: no direct `torch` pin; any GitHub alert on this
  file is treated as dependency-graph lag unless a future diff reintroduces
  torch here.
- `requirements-docker-runtime.txt`: no direct `torch` pin.
- `requirements-lock.txt`: no direct `torch` pin.
- `requirements-rag-vector.txt`: Safety flags `torch==2.11.0`.
- `requirements-rag-vector-cpu.txt`: Safety flags `torch==2.11.0+cpu`.
- GitHub Advisory `GHSA-rrmf-rvhw-rf47`: affected `torch <= 2.12.0`.
  Patched versions: none.
- PyPI latest `torch` release observed on 2026-06-18: `2.12.1`, but the
  GitHub Advisory Database still reports patched versions as none for
  `GHSA-rrmf-rvhw-rf47`. Do not treat a newer release as fixed until advisory
  and private-index evidence agree.
- Safety `SFTY-20250331-30014`: affected versions `<=2.12.0`.

## Evidence Anchors

- `requirements-rag-vector.txt:162`
- `requirements-rag-vector-cpu.txt:119`
- `safety-policy.yaml:16`
- `docs/roadmap/BACKLOG_LEDGER.md:709`

## Exposure Assessment

The vulnerable surface is tied to PyTorch TorchScript (`torch.jit.script`) in an
optional vector/RAG dependency profile. It is not installed by the default
production or Docker runtime manifests. Reassess immediately if product runtime
starts loading the vector profile by default, accepts untrusted TorchScript
artifacts, or routes user-controlled data into TorchScript compilation.

## Remediation

1. Prefer a fixed `torch` release when Safety, OSV, GitHub Advisory Database, or
   PyTorch upstream publishes one that satisfies the private package index.
2. If no fixed release exists by the remove-by date, decide between extending
   this waiver with fresh evidence, replacing the vector backend, or removing
   TorchScript-dependent capability from the optional profile.
3. Remove `SFTY-20250331-30014` from `safety-policy.yaml` in the same PR that
   closes the backlog item.

## References

- CVE: `https://www.cve.org/CVERecord?id=CVE-2025-3000`
- NVD: `https://nvd.nist.gov/vuln/detail/CVE-2025-3000`
- GitHub Advisory Database: `https://github.com/advisories/GHSA-rrmf-rvhw-rf47`
- Safety entry: `https://getsafety.com/vulnerabilities/SFTY-20250331-30014`
- PyPI torch: `https://pypi.org/project/torch/`
