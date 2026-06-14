# PR #1921 Late Post-Open Premortem

Plan: finish MCP example security hardening by closing review findings for safe MCP defaults, exact `npx` pins, governed runbook examples, and PR review-governance evidence.

Frame: it is 48 hours from now and this closeout made the lane worse. We are looking backward to understand why.

## Most Likely Failure

The guard passes locally but still misses a documented unsafe example. This would happen if the test only covered `.cursor` and `.kimi` JSON files while the governed runbook continued to teach unpinned `npx` Context7 usage.

Disposition: FIXED in this lane. The runbook Context7 examples are pinned to `@upstash/context7-mcp@3.1.0`, and `tests/guards/test_mcp_examples_safe_defaults.py` now scans the governed runbook path for unpinned Context7 local examples.

## Most Dangerous Failure

A future MCP example reintroduces unrestricted Playwright filesystem access through environment configuration instead of the CLI flag. That bypass would leave the examples appearing deny-by-default while still allowing broad local file access.

Disposition: FIXED in this lane. The guard now rejects truthy `PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS` values in Playwright `env` mappings as well as the unrestricted filesystem CLI flag.

## Hidden Assumption

The previous guard assumed all `npx` packages worth validating were scoped package names beginning with `@`. That left unscoped packages and malformed version specs as false negatives.

Disposition: FIXED in this lane. The guard now identifies the first non-option `npx` package arg, including unscoped packages, and requires an exact numeric package version parsed with `rsplit("@", 1)`.

## Revised Plan

- Keep the PR docs/test/example-only; do not touch runtime, OpenAPI, frontend, iOS, or database behavior.
- Fix code/docs/tests before fixed mapping or thread resolution.
- Use the implementation commit after review-comment timestamps as FIXED proof.
- Document full local `make verify` deferral as operator-approved and machine-heavy; use focused local gates plus current-head CI instead.

## Pre-Merge Checklist

- Focused guard test passes from repo root.
- Focused guard test passes from an external CWD using an absolute test path.
- Black check passes for `tests/guards/test_mcp_examples_safe_defaults.py`.
- `make validate-changed` passes.
- `pre-commit run --all-files` passes.
- `docs/review/PR_1921_FIXED_MAPPING.md` maps all actionable review URLs with valid dispositions.
- Strict merge-readiness wrapper passes with GitHub auth after current-head CI and review-thread checks.

## Decision

Proceed with changes. The identified failure modes are concrete but addressed by the local patch and must remain tied to focused validation plus fixed-mapping evidence before any readiness claim.
