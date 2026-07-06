# CreativeCodeArtifactInventory Contract

Status: local read-only lifecycle guard for creative-code artifacts. No product
runtime impact.

This guard inventories gitignored creative-code artifacts under:

```text
artifacts/orchestration/creative_code/
```

It does not create, restore, mutate, delete, promote, branch, push, open PRs,
resolve review threads, edit fixed mappings, call providers, call GitHub, call
product runtime, modify workflows, or claim merge readiness.

## CLI

```bash
python -m scripts.orchestration.creative_code_artifact_inventory status --format text
python -m scripts.orchestration.creative_code_artifact_inventory status --format json
python -m scripts.orchestration.creative_code_artifact_inventory assert-ready-for-promotion \
  --patch-run-id <run-id>
python -m scripts.orchestration.creative_code_artifact_inventory assert-ready-for-cleanup
```

`status` is diagnostic and exits 0 when the scan itself completes. Lifecycle
blockers are reported as stable reason codes. The `assert-*` commands exit
non-zero when their guard condition is false.

## Report Contract

The closed schema is:

- `creative_code_artifact_inventory_report.v1.schema.json`

The report may contain only sanitized metadata: safe IDs, counts, booleans,
fingerprints, lifecycle states, reason codes, and repo-relative refs under
`artifacts/orchestration/creative_code/**`.

The report must not contain raw patches, prompts, provider payloads, oracle
stdout/stderr, PR bodies, review bodies, secrets, token values, local absolute
paths, or exception text.

## Lifecycle Rules

Cache cleanup is allowed for ordinary local caches such as `.pytest_cache`,
`.mypy_cache`, `.ruff_cache`, and similar derived tool caches.

Cleanup of `artifacts/orchestration/creative_code/**` requires
`assert-ready-for-cleanup` to pass first. The guard fails closed when accepted
unpromoted PR-2 patch runs, partial/in-progress PR-3 promotion artifacts, or
artifact read/validation errors are present. The guard never deletes files.

PR-3 promotion planning must run only after
`assert-ready-for-promotion --patch-run-id <run-id>` passes. That assertion
requires canonical PR-2 sidecars, `status=accepted`, `failure_class=null`,
workspace cleanup proof, current local `origin/main` base match, and no
existing promotion receipt for the same `source_result_id`. A
`generation_receipt.json`, when present, must validate and bind to the same
run sidecars, but older accepted PR-2 runs are not rejected only because the
generation receipt is absent.

This guard is lifecycle evidence only. It is not fixed-mapping evidence, review
disposition evidence, merge-readiness evidence, or canonical product behavior.
