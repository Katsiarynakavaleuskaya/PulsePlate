# Creative Code Candidate Contract

<!-- markdownlint-disable MD013 -->

**Status:** PR-0 closed gate. Contract/specification handoff only.

`CreativeCodeCandidatePacket` is the typed handoff from promoted `creative_research` output into a future creative-code implementation lane. It does not generate code, apply patches, write a shared worktree, create branches, push, open pull requests, mark ready for review, resolve review threads, merge, release, or expand Slack/GitHub authority.

Canonical artifacts:

- Schema: `docs/orchestration/contracts/creative_code_candidate.v1.schema.json`
- Reference packet: `docs/orchestration/contracts/creative_code_candidate.v1.json`
- Validator: `scripts/orchestration/creative_code_contract.py`

Validation command:

```bash
python -m scripts.orchestration.creative_code_contract --validate docs/orchestration/contracts/creative_code_candidate.v1.json
```

Expected success output:

```text
PASS: creative-code candidate contract valid
```

---

## Packet Rules

A valid packet must:

- use `schema_version="1.0"` and `packet_type="creative_code_candidate"`;
- set `gate_status="closed"` and `authority_class="code-specification"`;
- reference a promoted `creative_research` source with `promotion_decision="promote"`;
- set `variant_count` to 3, 4, or 5;
- set `sandbox_required=true` and `human_review_required=true`;
- include a non-empty `fallback` for rejection or non-promotion;
- keep target surfaces repo-relative and inside the existing mutable candidate allowlist;
- keep immutable oracles repo-relative and disjoint from target surfaces;
- keep every repository-write, provider, runtime, semantic-cache, PR, review-thread, merge, release, and Slack/GitHub authority flag false.

Unknown fields are invalid. Duplicate JSON keys are invalid. Bool-like strings such as `"false"` are invalid.

---

## Non-Authority

This packet is not merge-readiness evidence, fixed-mapping evidence, CodeRabbit/Sourcery/Cubic disposition evidence, a production release signal, or a public scientific discovery claim. Future implementation requires separate PR governance, focused tests, current-head CI, post-open review gates, and human approval.
