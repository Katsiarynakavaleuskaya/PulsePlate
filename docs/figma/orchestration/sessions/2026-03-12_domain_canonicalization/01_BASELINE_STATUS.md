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
4. Public operator-assist diagnostic baseline on March 12, 2026:
   - `python3 scripts/check_domain_tls.py --domain pulseplate.app` returned `FAIL`
   - Diagnostic snapshot:
     - apex `A`: `172.67.75.178`, `104.26.9.193`, `104.26.8.193`
     - apex `AAAA`: `(none)`
     - `www` `A`: `104.26.8.193`, `104.26.9.193`, `172.67.75.178`
     - `www` `AAAA`: `(none)`
     - `www` `CNAME`: `(none)` under Cloudflare proxy, which is acceptable by itself
     - apex HTTPS: `405`
     - `www` HTTPS: `525`
   - Finding: public-side topology drift still exists specifically on `www` TLS, while the root apex remains repo-backed
5. Figma custom-domain UI baseline from the task screenshot:
   - Connected domain: `pulseplate.app`
   - Status: `Pending`
   - Warning: conflicting apex `AAAA` record must be removed to continue
   - Requested Figma records shown in UI: apex `A`, `_figma_sites_verify` TXT, `www` CNAME to `sites.figma.net`
6. Figma MCP baseline on March 12, 2026:
   - `whoami` reported `Full` seat on `pro`
   - `get_design_context(fileKey="<redacted-make-file-key>", nodeId="0:1")` succeeded for the Make file referenced by the task context
   - Code Connect remains blocked by seat/plan requirements tracked in `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:20`

## Decision

- `pulseplate.app` and `www.pulseplate.app` remain repo-canonical production hosts.
- Figma Make remains a design/source lane only.
- Any Figma-hosted preview must move to a dedicated preview subdomain instead of competing for the production root domain.

## Next Actions

1. Keep production Caddy responsible for apex + `www` TLS and redirect behavior.
2. Use `python3 scripts/check_domain_tls.py --domain pulseplate.app` as the canonical public-side SoT before any origin-side debugging.
3. Remove external DNS/TLS drift:
   - keep apex without conflicting `AAAA`
   - ensure `www` points to the repo-backed production origin
   - keep Cloudflare SSL mode on `Full (strict)`
   - verify the origin certificate covers both apex and `www`
4. Run `bash scripts/diagnose_production.sh` on the origin only after public-side drift is reconfirmed.
5. Do not attempt Code Connect activation as a substitute for domain ownership remediation.

## PR-2 Follow-up Evidence

1. Repo-side diagnostic SoT added for public-side checks:
   - `scripts/check_domain_tls.py:1`
   - `tests/test_check_domain_tls.py:1`
2. Public-side follow-up probe on March 12, 2026 using the new diagnostic:
   - `python3 scripts/check_domain_tls.py --domain pulseplate.app`
   - Result: apex `A` records still resolve through Cloudflare, apex `AAAA` remains absent, apex HTTPS returned `405`, and `www` still returned `525`
3. Follow-up decision for this PR cycle:
   - repo now contains the canonical read-only diagnostic for apex/`www` ownership drift
   - live acceptance remains blocked until Cloudflare/origin remediation makes `www` redirect cleanly to apex
   - Figma remains detached from production-root ownership; any preview must use a dedicated preview subdomain
