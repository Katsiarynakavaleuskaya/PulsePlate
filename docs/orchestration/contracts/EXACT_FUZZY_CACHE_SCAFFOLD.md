# Exact/Fuzzy Cache Scaffold Contract

## Purpose

SC-G2 defines a deterministic exact/fuzzy cache scaffold for future product AI
runtime review. It does not open the semantic-cache gate. It does not enable
runtime caching. It does not serve cached output.

The semantic-cache gate remains closed:

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Dedicated gate-open PR required: true.

## Scope

SC-G2 is deterministic exact/fuzzy only. It creates derived scaffold records,
normalization keys, lineage identifiers, and non-serving lookup decisions.

Allowed:

- stdlib only;
- NFKC lexical normalization;
- deterministic exact key equality;
- deterministic fuzzy reordered-token comparison;
- deterministic fuzzy near-duplicate comparison;
- integer basis-point scoring;
- Evidence Graph lineage required;
- admission linkage required;
- replay linkage required;
- non-serving fallback/miss decisions.

Blocked:

- embeddings;
- semantic similarity;
- vector search;
- Redis;
- GPTCache;
- provider changes;
- provider calls;
- runtime wiring;
- FastAPI or OpenAPI changes;
- DB writes or storage backend;
- raw prompts;
- raw model responses;
- advisory wiki product cache source;
- cache serving before SC-G3 observability and false-hit harness.

## Normalization Contract

The scaffold normalizes query text with:

1. `unicodedata.normalize("NFKC", text)`.
2. `casefold()`.
3. Unicode punctuation and symbol characters replaced with spaces.
4. Whitespace collapsed to one space.
5. Leading and trailing whitespace stripped.
6. `token_sort_key` derived from sorted lexical tokens.

No stemming, synonym table, transliteration, locale-specific heuristic, spell
correction, embedding, vector lookup, model call, or semantic proxy is allowed.
No semantic proxy models are allowed.

## Partition Contract

A candidate record may be considered only when all partition fields exactly
match the lookup request:

- surface;
- context fingerprint;
- source fingerprints;
- policy version;
- provider key;
- model key;
- user tier;
- transparency notice id.

Any mismatch is a hard miss. This prevents cross-user, cross-tier,
cross-policy, stale-source, model-version, and transparency-notice leakage.

## Match Modes

Match modes are ranked in this order:

1. `exact`: same partition and same normalized query.
2. `fuzzy_reordered_tokens`: same partition and same token sort key with a
   different normalized query.
3. `fuzzy_near_duplicate`: same partition, token Jaccard basis points at or
   above policy threshold, sequence-ratio basis points at or above policy
   threshold, and token-count delta within policy limit.

Tie-break order is deterministic:

1. higher integer basis-point score;
2. lexicographically smaller normalized query;
3. lexicographically smaller record id.

Public result contracts use integer basis points only. No public float scores
are allowed.

## Evidence Graph Linkage

Every scaffold record must carry derived, non-sensitive lineage references:

- source fingerprints;
- policy version;
- admission decision ID when available;
- eval event IDs when available;
- promotion IDs when available;
- replay entry IDs when available;
- provider key;
- model key;
- transparency notice id;
- safety flags.

SC-G2 reuses Evidence Graph lineage/admission/replay identifiers. It does not
create a parallel evidence plane.

## Serving Boundary

SC-G2 output is advisory eligibility metadata only. It cannot serve cached
answers, persist response payloads, bypass safety checks, bypass quota checks,
bypass admission, or mutate runtime state.

The first future bounded runtime experiment remains SC-G4 on a repetitive
`/insight`-style product AI surface. That future experiment must be
feature-flagged, off by default, and easy to disable.

## Blocked Surfaces

SC-G2 must not cache or derive product-cache authority from:

- advisory wiki;
- workforce memory;
- billing/auth/entitlement;
- legal/compliance outputs;
- account truth;
- HealthKit-derived sensitive payloads;
- raw prompts;
- raw model responses;
- secrets or credentials;
- highly personalized coaching state.

## Follow-up Gates

SC-G3 observability and false-hit harness is still required before any
semantic-cache serving. SC-G4 bounded `/insight` semantic-cache experiment
remains a future gated PR. SC-G5 backend selection, including Redis or GPTCache,
remains blocked until measured safety evidence and rollback proof exist.
