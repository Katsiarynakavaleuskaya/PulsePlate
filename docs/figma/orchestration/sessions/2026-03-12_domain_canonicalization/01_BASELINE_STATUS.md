# Domain Canonicalization Baseline (2026-03-12)

**Date:** March 12, 2026
**Scope:** `pulseplate.app` production ownership, `www` TLS health, and Figma custom-domain drift

## Evidence

1. Repo-backed production contract still points to the application runtime:
   - `deploy/docker-compose.production.yaml:1`
   - `deploy/Caddyfile.production:1`
   - `app/main.py:1`
2. Public DNS baseline on March 12, 2026:
   - `dig +short A pulseplate.app` returned Cloudflare IPs `104.26.8.193`, `104.26.9.193`, `172.67.75.178`
   - `dig +short A www.pulseplate.app` returned the same Cloudflare IPs
   - `dig +short AAAA www.pulseplate.app` returned no value
3. Public HTTP/TLS baseline on March 12, 2026:
   - `curl -I -L https://pulseplate.app` returned `405` with `allow: GET`, which confirms the app runtime is still answering behind Cloudflare
   - `curl -I -L https://www.pulseplate.app` returned `525`, which confirms broken TLS or host ownership drift for `www`
4. Figma custom-domain UI baseline from the task screenshot:
   - Connected domain: `pulseplate.app`
   - Status: `Pending`
   - Warning: conflicting apex `AAAA` record must be removed to continue
   - Requested Figma records shown in UI: apex `A`, `_figma_sites_verify` TXT, `www` CNAME to `sites.figma.net`
5. Figma MCP baseline on March 12, 2026:
   - `whoami` reported `Full` seat on `pro`
   - `get_design_context(fileKey="<redacted-make-file-key>", nodeId="0:1")` succeeded for the Make file referenced by the task context
   - Code Connect remains blocked by seat/plan requirements tracked in `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:20`

## Decision

- `pulseplate.app` and `www.pulseplate.app` remain repo-canonical production hosts.
- Figma Make remains a design/source lane only.
- Any Figma-hosted preview must move to a dedicated preview subdomain instead of competing for the production root domain.

## Next Actions

1. Keep production Caddy responsible for apex + `www` TLS and redirect behavior.
2. Remove external DNS drift:
   - delete the conflicting apex `AAAA` record from the production DNS zone
   - ensure `www` points to the repo-backed production origin
3. Do not attempt Code Connect activation as a substitute for domain ownership remediation.
