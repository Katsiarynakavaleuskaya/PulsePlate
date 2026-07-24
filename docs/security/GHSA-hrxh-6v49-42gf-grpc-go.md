# GHSA-hrxh-6v49-42gf: grpc-go remediation

## Security decision

The GitHub advisory marks `google.golang.org/grpc` versions below `1.82.1` as affected and
`1.82.1` as patched. The failed image scan observed `v1.81.0` in the Caddy binary, so the
repository now rebuilds Caddy `v2.11.4` with grpc-go `v1.82.1` while retaining the pinned
builder and runtime images.

Official sources:

- [GitHub Advisory GHSA-hrxh-6v49-42gf](https://github.com/advisories/GHSA-hrxh-6v49-42gf)
- [grpc-go v1.82.1 release](https://github.com/grpc/grpc-go/releases/tag/v1.82.1)
- [grpc-go v1.82.1 module](https://pkg.go.dev/google.golang.org/grpc@v1.82.1)
- [Trivy v0.72.0 release](https://github.com/aquasecurity/trivy/releases/tag/v0.72.0)

## Remediation evidence

- `frontend/Dockerfile.caddy-spa:15` creates a temporary Go module, resolves only the exact
  Caddy and grpc-go versions, verifies the module graph, and builds with `-mod=readonly`.
- `frontend/Dockerfile.caddy-spa:33` and `frontend/Dockerfile.caddy-spa:35` verify the
  embedded Caddy and grpc-go module identities from the completed binary before it can enter
  the runtime image.
- `.github/workflows/cd.yml:324`, `.github/workflows/cd.yml:343`,
  `.github/workflows/build.yml:386`, `.github/workflows/build.yml:592`, and
  `.github/workflows/trivy.yml:206` pin the five active Trivy inputs to `v0.72.0` while the
  action itself remains commit-pinned.
- `tests/test_caddy_deploy_provenance.py:77` rejects unpinned, replacement-based,
  checksum-bypassing, xcaddy, legacy `go install`, and grpc-go `v1.81.0` recipes.
- `tests/test_ci_workflow_pr_size_governance_contract.py:1177` positively enumerates the two
  CD, two build, and one standalone Trivy action contracts, including their exact action SHA,
  runtime version, inputs, environment, and fail-closed behavior.

No vulnerability suppression, ignore-policy expansion, workflow trigger change, permission
change, or SSH/deploy-policy change is part of this remediation. The staged Caddy scan remains
suppression-free through its existing empty `.trivyignore-caddy` contract.
