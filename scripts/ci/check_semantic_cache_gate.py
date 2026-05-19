#!/usr/bin/env python3
"""Fail-closed guard for the PulsePlate semantic-cache gate document."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOC = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
DEFAULT_CONTRACT = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "SEMANTIC_CACHE_ROLLOUT_GATE.md"
)
DEFAULT_SCAFFOLD_CONTRACT = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "EXACT_FUZZY_CACHE_SCAFFOLD.md"
)
DEFAULT_OBSERVABILITY_CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md"
)
DEFAULT_BOUNDED_INSIGHT_CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md"
)
DEFAULT_BACKEND_SELECTION_CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
)
DEFAULT_BACKEND_SELECTION_SCHEMA = DEFAULT_BACKEND_SELECTION_CONTRACT.with_suffix(".schema.json")
DEFAULT_PHILOSOPHY_ADMISSION_CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md"
)
DEFAULT_PHILOSOPHY_ADMISSION_SCHEMA = DEFAULT_PHILOSOPHY_ADMISSION_CONTRACT.with_suffix(
    ".schema.json"
)

REQUIRED_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

REQUIRED_PHRASES = (
    "gate-closed",
    "reviewed gate-open PR",
    "product AI runtime rail",
    "not advisory wiki",
    "not workforce memory",
    "not a second source of truth",
    "not billing/auth/entitlement truth",
    "not a compliance/legal output cache",
    "not user-account truth surfaces",
)

ROLLOUT_ORDER = (
    "SC-G1 rollout gate contract",
    "SC-G2 exact/fuzzy cache scaffold",
    "SC-G3 observability and false-hit harness",
    "SC-G4 bounded `/insight` semantic-cache experiment",
    "SC-G5 backend selection",
)

FORBIDDEN_CLAIM_PATTERNS = (
    (
        "semantic cache live claim",
        re.compile(
            r"(?<!philosophical )\bsemantic\s+cache\s+"
            r"(?:(?:is|has\s+been)\s+)?(?:now\s+)?"
            r"(?:implemented|active|enabled|open|approved|ready|live)\b"
        ),
    ),
    (
        "semantic-cache live claim",
        re.compile(
            r"(?<!philosophical )\bsemantic-cache\s+"
            r"(?:(?:is|has\s+been)\s+)?(?:now\s+)?"
            r"(?:implemented|active|enabled|open|approved|ready|live)\b"
        ),
    ),
    (
        "semantic cache prerequisites satisfied",
        re.compile(r"\bsemantic\s+cache\s+prerequisites\s+(?:are\s+)?satisfied\b"),
    ),
    (
        "E1-E5 unlock semantic cache",
        re.compile(
            r"\be1\s*(?:-|through|to)\s*e5\s+(?:automatically\s+)?unlock(?:s)?\s+semantic\s+cache\b"
        ),
    ),
    (
        "E1-E5 satisfy semantic cache prerequisites",
        re.compile(
            r"\be1\s*(?:-|through|to)\s*e5\s+satisf(?:y|ies)\s+semantic\s+cache\s+prerequisites\b"
        ),
    ),
    (
        "Evidence Graph unlocks semantic cache",
        re.compile(r"\bevidence\s+graph\s+(?:automatically\s+)?unlock(?:s)?\s+semantic\s+cache\b"),
    ),
    (
        "advisory wiki feeds product cache",
        re.compile(r"\badvisory\s+wiki\s+(?:feeds|can\s+seed|seeds)\s+product\s+cache\b"),
    ),
    ("wiki pages are cache truth", re.compile(r"\bwiki\s+pages\s+are\s+cache\s+truth\b")),
    ("GraphRAG rollout approved", re.compile(r"\bgraphrag\s+rollout\s+(?:is\s+)?approved\b")),
    ("GPTCache rollout approved", re.compile(r"\bgptcache\s+rollout\s+(?:is\s+)?approved\b")),
    (
        "Redis semantic cache approved",
        re.compile(r"\bredis\s+semantic\s+cache\s+(?:is\s+)?approved\b"),
    ),
    ("cache raw prompt", re.compile(r"\bcache\s+raw\s+(?:model\s+)?prompts?\b")),
    ("cache raw response", re.compile(r"\bcache\s+raw\s+(?:model\s+)?responses?\b")),
    ("cache secrets", re.compile(r"\bcache\s+secrets?\b")),
    ("cache user health data", re.compile(r"\bcache\s+user\s+health\s+data\b")),
    ("cache account truth", re.compile(r"\bcache\s+account\s+truth\b")),
    (
        "advisory evidence seeds product cache",
        re.compile(r"\badvisory\s+evidence\s+seeds\s+product\s+cache\b"),
    ),
    (
        "semantic cache serving live claim",
        re.compile(
            r"\bsemantic\s+cache\s+serving\s+"
            r"(?:(?:is|has\s+been)\s+)?(?:available|enabled|active|ready)\b"
        ),
    ),
    (
        "semantic-cache serving live claim",
        re.compile(
            r"\bsemantic-cache\s+serving\s+"
            r"(?:(?:is|has\s+been)\s+)?(?:available|enabled|active|ready)\b"
        ),
    ),
    (
        "semantic cache production ready",
        re.compile(r"\bsemantic\s+cache\s+(?:is\s+)?production-ready\b"),
    ),
)

CONTRACT_REQUIRED_ANCHORS = (
    ("gate does not open", re.compile(r"\bdoes not open (?:the )?semantic-cache gate\b")),
    ("no cache implementation", re.compile(r"\bdoes not implement semantic cache\b")),
    ("gate remains closed", re.compile(r"\bgate remains closed\b")),
    ("product AI runtime rail only", re.compile(r"\bproduct ai runtime rail only\b")),
    ("feature flag", re.compile(r"\bfeature-flagged\b")),
    ("off by default", re.compile(r"\boff by default\b")),
    ("SC-G1 rollout gate contract", re.compile(r"\bsc-g1 rollout gate contract\b")),
    ("SC-G2 exact/fuzzy cache scaffold", re.compile(r"\bsc-g2 exact/fuzzy cache scaffold\b")),
    (
        "SC-G3 observability and false-hit harness",
        re.compile(r"\bsc-g3 observability and false-hit harness\b"),
    ),
    (
        "SC-G4 bounded insight semantic-cache experiment",
        re.compile(r"\bsc-g4 bounded /insight semantic-cache experiment\b"),
    ),
    ("SC-G5 backend selection", re.compile(r"\bsc-g5 backend selection\b")),
    ("exact duplicate hit", re.compile(r"\bexact duplicate hit\b")),
    ("normalized fuzzy hit", re.compile(r"\bnormalized fuzzy hit\b")),
    ("semantic false positive", re.compile(r"\bsemantic false positive\b")),
    ("stale-source hit", re.compile(r"\bstale-source hit\b")),
    ("policy-version mismatch hit", re.compile(r"\bpolicy-version mismatch hit\b")),
    ("model-version mismatch hit", re.compile(r"\bmodel-version mismatch hit\b")),
    ("user-context leakage hit", re.compile(r"\buser-context leakage hit\b")),
    ("eligible_hit_rate", re.compile(r"\beligible_hit_rate\b")),
    ("served_hit_rate", re.compile(r"\bserved_hit_rate\b")),
    ("false_hit_rate", re.compile(r"\bfalse_hit_rate\b")),
    ("cache_precision_proxy", re.compile(r"\bcache_precision_proxy\b")),
    ("stale_answer_rate", re.compile(r"\bstale_answer_rate\b")),
    ("fallback_rate", re.compile(r"\bfallback_rate\b")),
    ("p50/p95 latency_saved", re.compile(r"\bp50/p95 latency_saved\b")),
    ("provider_calls_avoided", re.compile(r"\bprovider_calls_avoided\b")),
    ("cost_saved", re.compile(r"\bcost_saved\b")),
    ("quota_consumption_delta", re.compile(r"\bquota_consumption_delta\b")),
    ("kill switch", re.compile(r"\bkill switch\b")),
    ("no-cache fallback path", re.compile(r"\bno-cache fallback path\b")),
    ("purge/invalidation path", re.compile(r"\bpurge/invalidation path\b")),
    ("blocked cache surfaces", re.compile(r"\bblocked cache surfaces\b")),
    ("advisory wiki product truth block", re.compile(r"\badvisory wiki pages as product truth\b")),
    ("billing/auth/entitlement block", re.compile(r"\bbilling/auth/entitlement\b")),
    ("legal/compliance outputs block", re.compile(r"\blegal/compliance outputs\b")),
    ("user-account truth block", re.compile(r"\buser-account truth\b")),
    ("raw prompts block", re.compile(r"\braw prompts\b")),
    ("raw model responses block", re.compile(r"\braw model responses\b")),
    ("Evidence Graph linkage", re.compile(r"\bevidence graph linkage\b")),
    ("admission decision IDs", re.compile(r"\badmission decision ids\b")),
    ("promotion/replay lineage", re.compile(r"\bpromotion/replay lineage\b")),
)

SCAFFOLD_REQUIRED_ANCHORS = (
    (
        "SC-G2 does not open semantic-cache gate",
        re.compile(r"\bsc-g2 defines .*\bdoes not open (?:the )?semantic-cache gate\b"),
    ),
    (
        "SC-G2 does not enable runtime caching",
        re.compile(r"\bdoes not enable runtime caching\b"),
    ),
    ("deterministic exact/fuzzy only", re.compile(r"\bdeterministic exact/fuzzy only\b")),
    ("stdlib only", re.compile(r"\bstdlib only\b")),
    ("no embeddings", re.compile(r"\bblocked:\s+- embeddings\b")),
    ("no semantic similarity", re.compile(r"\bblocked:.*-\s+semantic similarity\b")),
    ("no Redis", re.compile(r"\bblocked:.*-\s+redis\b")),
    ("no GPTCache", re.compile(r"\bblocked:.*-\s+gptcache\b")),
    ("no vector search", re.compile(r"\bblocked:.*-\s+vector search\b")),
    ("no provider changes", re.compile(r"\bblocked:.*-\s+provider changes\b")),
    ("no runtime wiring", re.compile(r"\bblocked:.*-\s+runtime wiring\b")),
    ("no raw prompts", re.compile(r"\bblocked:.*-\s+raw prompts\b")),
    ("no raw model responses", re.compile(r"\bblocked:.*-\s+raw model responses\b")),
    ("Evidence Graph lineage required", re.compile(r"\bevidence graph lineage required\b")),
    ("admission linkage required", re.compile(r"\badmission linkage required\b")),
    ("replay linkage required", re.compile(r"\breplay linkage required\b")),
    (
        "partition surface",
        re.compile(r"\bpartition fields exactly match.*-\s+surface\b"),
    ),
    (
        "partition context fingerprint",
        re.compile(r"\bpartition fields exactly match.*-\s+context fingerprint\b"),
    ),
    (
        "partition source fingerprints",
        re.compile(r"\bpartition fields exactly match.*-\s+source fingerprints\b"),
    ),
    (
        "partition policy version",
        re.compile(r"\bpartition fields exactly match.*-\s+policy version\b"),
    ),
    (
        "partition provider key",
        re.compile(r"\bpartition fields exactly match.*-\s+provider key\b"),
    ),
    (
        "partition model key",
        re.compile(r"\bpartition fields exactly match.*-\s+model key\b"),
    ),
    (
        "partition user tier",
        re.compile(r"\bpartition fields exactly match.*-\s+user tier\b"),
    ),
    (
        "partition transparency notice id",
        re.compile(r"\bpartition fields exactly match.*-\s+transparency notice id\b"),
    ),
    ("integer basis-point scoring", re.compile(r"\binteger basis-point scoring\b")),
    (
        "SC-G3 required",
        re.compile(r"\bsc-g3 observability and false-hit harness is still required\b"),
    ),
    ("SC-G4 future", re.compile(r"\bsc-g4 bounded /insight semantic-cache experiment\b")),
)

SCAFFOLD_FORBIDDEN_PATTERNS = (
    (
        "SC-G2 permits embeddings",
        re.compile(
            r"\b(?:sc-g2\s+)?(?:permits|allows|enables|supports|approves)\s+embeddings\b"
            r"|\bsc-g2\s+can\s+use\s+embeddings\b"
            r"|\bembeddings\s+(?:are\s+)?(?:allowed|enabled|supported|available|approved)\s+"
            r"(?:for|in)\s+sc-g2\b"
        ),
    ),
    (
        "SC-G2 permits semantic similarity",
        re.compile(
            r"\b(?:sc-g2\s+)?(?:permits|allows|enables|supports|approves)\s+semantic\s+similarity\b"
            r"|\bsc-g2\s+can\s+use\s+semantic\s+similarity\b"
            r"|\bsemantic\s+similarity\s+(?:is\s+)?"
            r"(?:allowed|enabled|supported|available|approved)\s+(?:for|in)\s+sc-g2\b"
        ),
    ),
    (
        "SC-G2 permits vector search",
        re.compile(
            r"\b(?:sc-g2\s+)?(?:permits|allows|enables|supports|approves)\s+vector\s+search\b"
            r"|\bsc-g2\s+can\s+use\s+vector\s+search\b"
            r"|\bvector\s+search\s+(?:is\s+)?"
            r"(?:allowed|enabled|supported|available|approved)\s+(?:for|in)\s+sc-g2\b"
        ),
    ),
    (
        "SC-G2 permits Redis",
        re.compile(
            r"\b(?:sc-g2\s+)?(?:permits|allows|enables|supports|approves)\s+redis\b"
            r"|\bsc-g2\s+can\s+use\s+redis\b"
            r"|\bredis\s+(?:is\s+)?(?:allowed|enabled|supported|available|approved)\s+"
            r"(?:for|in)\s+sc-g2\b"
        ),
    ),
    (
        "SC-G2 permits GPTCache",
        re.compile(
            r"\b(?:sc-g2\s+)?(?:permits|allows|enables|supports|approves)\s+gptcache\b"
            r"|\bsc-g2\s+can\s+use\s+gptcache\b"
            r"|\bgptcache\s+(?:is\s+)?(?:allowed|enabled|supported|available|approved)\s+"
            r"(?:for|in)\s+sc-g2\b"
        ),
    ),
    (
        "SC-G2 bypasses SC-G3",
        re.compile(r"\bsc-g2\s+(?:bypasses|skips)\s+sc-g3\b"),
    ),
)

OBSERVABILITY_REQUIRED_ANCHORS = (
    ("offline only", re.compile(r"\boffline only\b")),
    ("non-serving", re.compile(r"\bnon-serving\b")),
    ("audit event", re.compile(r"\baudit event\b")),
    ("false hit", re.compile(r"\bfalse hit\b")),
    ("negative controls", re.compile(r"\bnegative controls\b")),
    ("stop rules", re.compile(r"\bstop rules\b")),
    ("rollback thresholds", re.compile(r"\brollback thresholds\b")),
    ("kill switch snapshot", re.compile(r"\bkill switch snapshot\b")),
    ("stale source", re.compile(r"\bstale source\b")),
    ("policy mismatch", re.compile(r"\bpolicy mismatch\b")),
    ("model mismatch", re.compile(r"\bmodel mismatch\b")),
    ("context leakage", re.compile(r"\bcontext leakage\b")),
    ("admission blocked hit", re.compile(r"\badmission blocked hit\b")),
    ("blocked surfaces", re.compile(r"\bblocked surfaces\b")),
    (
        "no raw prompts",
        re.compile(r"\b(?:blocked:\s*-\s*|no\s+|must not contain\s+)raw prompts\b"),
    ),
    (
        "no raw model responses",
        re.compile(r"\b(?:blocked:\s*-\s*|no\s+|must not contain\s+)raw model responses\b"),
    ),
    (
        "no embeddings",
        re.compile(r"\b(?:blocked:\s*-\s*|no\s+|must not contain\s+)embeddings\b"),
    ),
    ("no Redis", re.compile(r"\b(?:blocked:\s*-\s*|no\s+|must not contain\s+)redis\b")),
    (
        "no GPTCache",
        re.compile(r"\b(?:blocked:\s*-\s*|no\s+|must not contain\s+)gptcache\b"),
    ),
    (
        "no provider calls",
        re.compile(r"\b(?:blocked:\s*-\s*|no\s+|must not contain\s+)provider calls\b"),
    ),
    ("gate remains closed", re.compile(r"\bgate remains closed\b")),
    (
        "SC-G4 remains future bounded insight experiment",
        re.compile(r"\bsc-g4 remains a future bounded /insight experiment\b"),
    ),
    ("eligible_request_count", re.compile(r"\beligible_request_count\b")),
    ("false_hit_rate_bps", re.compile(r"\bfalse_hit_rate_bps\b")),
    ("cache_precision_proxy_bps", re.compile(r"\bcache_precision_proxy_bps\b")),
    (
        "semantic false positive label only",
        re.compile(r"\bsemantic_false_positive\b.*\blabel only\b"),
    ),
)

OBSERVABILITY_FORBIDDEN_PATTERNS = (
    (
        "semantic cache active",
        re.compile(r"\bsemantic\s+cache\s+(?:is\s+)?(?:active|enabled|open)\b"),
    ),
    (
        "semantic cache serving enabled",
        re.compile(r"\bsemantic\s+cache\s+serving\s+(?:is\s+)?enabled\b"),
    ),
    ("SC-G3 opens gate", re.compile(r"\bsc-g3\s+opens\s+(?:the\s+)?gate\b")),
    (
        "SC-G3 enables insight serving",
        re.compile(r"\bsc-g3\s+enables\s+/insight\s+serving\b"),
    ),
    (
        "SC-G3 allows embeddings",
        re.compile(r"\bsc-g3\s+(?:allows|approves|enables)\s+embeddings\b"),
    ),
    (
        "SC-G3 approves Redis/GPTCache",
        re.compile(
            r"\bsc-g3\s+(?:permits|allows|enables|supports|approves)\s+"
            r"(?:redis|gptcache|redis/gptcache)\b"
        ),
    ),
    (
        "SC-G3 allows semantic similarity",
        re.compile(r"\bsc-g3\s+(?:allows|approves|enables|permits)\s+semantic\s+similarity\b"),
    ),
    (
        "SC-G3 allows vector search",
        re.compile(r"\bsc-g3\s+(?:allows|approves|enables|permits)\s+vector\s+search\b"),
    ),
    (
        "SC-G3 allows provider calls",
        re.compile(r"\bsc-g3\s+(?:allows|approves|enables|permits)\s+provider\s+calls\b"),
    ),
    (
        "SC-G3 allows runtime serving",
        re.compile(r"\bsc-g3\s+(?:allows|approves|enables|permits)\s+runtime\s+serving\b"),
    ),
    (
        "SC-G3 allows Redis",
        re.compile(r"\bsc-g3\s+(?:allows|enables|permits)\s+redis\b"),
    ),
    (
        "SC-G3 allows GPTCache",
        re.compile(r"\bsc-g3\s+(?:allows|enables|permits)\s+gptcache\b"),
    ),
    ("cache raw prompts", re.compile(r"\bcache\s+raw\s+prompts?\b")),
    ("cache raw responses", re.compile(r"\bcache\s+raw\s+(?:model\s+)?responses?\b")),
)

BOUNDED_INSIGHT_REQUIRED_ANCHORS = (
    ("SC-G4 bounded insight", re.compile(r"\bsc-g4 bounded /insight semantic-cache experiment\b")),
    ("does not open gate", re.compile(r"\bdoes not open (?:the )?semantic-cache gate\b")),
    ("does not enable runtime caching", re.compile(r"\bdoes not enable runtime caching\b")),
    ("does not enable insight serving", re.compile(r"\bdoes not enable /insight serving\b")),
    ("gate remains closed", re.compile(r"\bgate remains closed\b")),
    ("runtime allowed false", re.compile(r"\bruntime allowed:\s*false\b")),
    ("implementation allowed false", re.compile(r"\bimplementation allowed:\s*false\b")),
    ("off by default", re.compile(r"\boff by default\b")),
    ("environment flag", re.compile(r"\benvironment flag\b")),
    ("runtime flag snapshot", re.compile(r"\bruntime flag snapshot\b")),
    ("explicit request opt-in", re.compile(r"\bexplicit request opt-in\b")),
    ("request disable", re.compile(r"\brequest disable\b")),
    ("kill switch snapshot", re.compile(r"\bkill switch snapshot\b")),
    ("fallback", re.compile(r"\bfallback\b")),
    ("source fingerprints", re.compile(r"\bsource fingerprints\b")),
    ("eval event IDs", re.compile(r"\beval event ids\b")),
    ("admission decision ID", re.compile(r"\badmission decision id\b")),
    ("promotion IDs", re.compile(r"\bpromotion ids\b")),
    ("replay entry IDs", re.compile(r"\breplay entry ids\b")),
    ("policy version", re.compile(r"\bpolicy version\b")),
    ("provider key", re.compile(r"\bprovider key\b")),
    ("model key", re.compile(r"\bmodel key\b")),
    ("context fingerprint", re.compile(r"\bcontext fingerprint\b")),
    ("user tier", re.compile(r"\buser tier\b")),
    ("transparency notice id", re.compile(r"\btransparency notice id\b")),
    ("response fingerprint", re.compile(r"\bresponse fingerprint\b")),
    (
        "no raw prompts",
        re.compile(r"\b(?:must not contain or persist|blocked payload fields).*raw prompts\b"),
    ),
    (
        "no raw queries",
        re.compile(r"\b(?:must not contain or persist|blocked payload fields).*raw queries\b"),
    ),
    (
        "no raw model responses",
        re.compile(
            r"\b(?:must not contain or persist|blocked payload fields).*raw model responses\b"
        ),
    ),
    (
        "no raw answers",
        re.compile(r"\b(?:must not contain or persist|blocked payload fields).*raw answers\b"),
    ),
    ("advisory wiki blocked", re.compile(r"\badvisory wiki\b")),
    ("no Redis", re.compile(r"\bsc-g4 blocks:.*redis\b")),
    ("no GPTCache", re.compile(r"\bsc-g4 blocks:.*gptcache\b")),
    ("no embeddings", re.compile(r"\bsc-g4 blocks:.*embeddings\b")),
    ("no vector search", re.compile(r"\bsc-g4 blocks:.*vector search\b")),
    ("no provider calls", re.compile(r"\bsc-g4 blocks:.*provider calls\b")),
    ("SC-G5 remains future", re.compile(r"\bsc-g5 backend selection remains future\b")),
)

BOUNDED_INSIGHT_FORBIDDEN_PATTERNS = (
    (
        "semantic cache active",
        re.compile(r"\bsemantic\s+cache\s+(?:is\s+)?(?:active|enabled|open)\b"),
    ),
    (
        "semantic cache can serve insight",
        re.compile(r"\bsemantic\s+cache\s+can\s+serve\s+/insight\s+responses\b"),
    ),
    ("SC-G4 opens gate", re.compile(r"\bsc-g4\s+opens\s+(?:the\s+)?gate\b")),
    (
        "SC-G4 enables insight serving",
        re.compile(r"\bsc-g4\s+enables\s+/insight\s+serving\b"),
    ),
    (
        "SC-G4 allows embeddings",
        re.compile(r"\bsc-g4\s+(?:allows|approves|enables|permits)\s+embeddings\b"),
    ),
    (
        "SC-G4 allows vector search",
        re.compile(r"\bsc-g4\s+(?:allows|approves|enables|permits)\s+vector\s+search\b"),
    ),
    (
        "SC-G4 approves Redis/GPTCache",
        re.compile(
            r"\bsc-g4\s+(?:allows|approves|enables|permits|supports)\s+"
            r"(?:redis|gptcache|redis/gptcache)\b"
        ),
    ),
    ("SC-G4 allows Redis", re.compile(r"\bsc-g4\s+(?:allows|enables|permits)\s+redis\b")),
    ("SC-G4 allows GPTCache", re.compile(r"\bsc-g4\s+(?:allows|enables|permits)\s+gptcache\b")),
    (
        "Redis allowed",
        re.compile(r"\bredis\s+(?:is\s+)?(?:allowed|approved|enabled|supported)\b"),
    ),
    (
        "GPTCache supported",
        re.compile(r"\bgptcache\s+(?:is\s+)?(?:allowed|approved|enabled|supported)\b"),
    ),
    (
        "SC-G4 allows provider calls",
        re.compile(r"\bsc-g4\s+(?:allows|approves|enables|permits)\s+provider\s+calls\b"),
    ),
    (
        "default-on experiment",
        re.compile(r"\b(?:default on|default-on|on by default)\b"),
    ),
    ("cache raw prompts", re.compile(r"\bcache(?:s)?\s+raw\s+prompts?\b")),
    ("cache raw queries", re.compile(r"\bcache(?:s)?\s+raw\s+quer(?:y|ies)\b")),
    ("cache raw responses", re.compile(r"\bcache(?:s)?\s+raw\s+(?:model\s+)?responses?\b")),
    ("cache raw answers", re.compile(r"\bcache(?:s)?\s+raw\s+answers?\b")),
    (
        "raw payload allowed",
        re.compile(
            r"\braw\s+(?:prompts?|quer(?:y|ies)|(?:model\s+)?responses?|answers?)\s+"
            r"(?:are\s+)?(?:allowed|approved|enabled|supported|stored|persisted)\b"
        ),
    ),
    (
        "SC-G4 may store raw payloads",
        re.compile(
            r"\bsc-g4\s+(?:may|can)\s+(?:store|persist|cache)\s+raw\s+"
            r"(?:prompts?|quer(?:y|ies)|(?:model\s+)?responses?|answers?)\b"
        ),
    ),
    (
        "provider payloads for replay",
        re.compile(r"\bprovider\s+payloads?\s+(?:for|in|to)\s+replay\b"),
    ),
    (
        "advisory wiki seeds product cache",
        re.compile(r"\badvisory\s+wiki\s+(?:may\s+seed|can\s+seed|seeds)\s+product\s+cache\b"),
    ),
)

BACKEND_SELECTION_REQUIRED_ANCHORS = (
    ("SC-G5 backend selection", re.compile(r"\bsc-g5 backend selection\b")),
    ("does not open gate", re.compile(r"\bdoes not open (?:the )?semantic-cache gate\b")),
    ("gate remains closed", re.compile(r"\bgate remains closed\b")),
    ("runtime allowed false", re.compile(r"\bruntime allowed:\s*false\b")),
    ("implementation allowed false", re.compile(r"\bimplementation allowed:\s*false\b")),
    ("default activation none", re.compile(r"\bdefault activation:\s*none\b")),
    ("recommendation-only metadata", re.compile(r"\brecommendation-only metadata\b")),
    ("candidate backend labels only", re.compile(r"\bcandidate backend labels only\b")),
    ("redis label", re.compile(r"\bredis_label\b")),
    ("gptcache label", re.compile(r"\bgptcache_label\b")),
    ("SC-G2 evidence", re.compile(r"\bsc-g2 contract and lineage evidence\b")),
    (
        "SC-G3 evidence",
        re.compile(
            r"\bsc-g3 audit, negative-control, metric, stop-rule, and kill-switch evidence\b"
        ),
    ),
    (
        "SC-G4 evidence",
        re.compile(r"\bsc-g4 bounded /insight metadata-only decision evidence\b"),
    ),
    ("safety hard gate", re.compile(r"\bsafety is a hard gate\b")),
    ("false hit rate", re.compile(r"\bfalse_hit_rate_bps\b")),
    ("stale answer rate", re.compile(r"\bstale_answer_rate_bps\b")),
    ("current-head CI", re.compile(r"\bcurrent-head ci governance proof\b")),
    ("human approval", re.compile(r"\bhuman approval record\b")),
    ("kill switch proof", re.compile(r"\bkill switch proof\b")),
    ("purge invalidation proof", re.compile(r"\bpurge/invalidation proof\b")),
    ("no runtime serving", re.compile(r"\bsc-g5 blocks:.*runtime serving\b")),
    ("no FastAPI", re.compile(r"\bsc-g5 blocks:.*fastapi\b")),
    ("no OpenAPI", re.compile(r"\bsc-g5 blocks:.*openapi\b")),
    ("no DB writes", re.compile(r"\bsc-g5 blocks:.*db writes\b")),
    ("no provider calls", re.compile(r"\bsc-g5 blocks:.*provider calls\b")),
    ("no Redis imports", re.compile(r"\bsc-g5 blocks:.*redis imports or clients\b")),
    ("no GPTCache imports", re.compile(r"\bsc-g5 blocks:.*gptcache imports or clients\b")),
    ("no connection strings", re.compile(r"\bsc-g5 blocks:.*connection strings\b")),
    ("no vector search", re.compile(r"\bsc-g5 blocks:.*vector search\b")),
    ("no embeddings", re.compile(r"\bsc-g5 blocks:.*embeddings\b")),
    ("no raw prompts", re.compile(r"\bmust not contain, persist, rank, or emit:.*raw prompts\b")),
    (
        "no raw model responses",
        re.compile(r"\bmust not contain, persist, rank, or emit:.*raw model responses\b"),
    ),
    (
        "no provider payloads",
        re.compile(r"\bmust not contain, persist, rank, or emit:.*provider payloads\b"),
    ),
    (
        "advisory wiki blocked",
        re.compile(
            r"\bmust not use advisory wiki\b|\bblocked_truth_sources\b[^\]]*\badvisory wiki\b"
        ),
    ),
    (
        "workforce memory blocked",
        re.compile(
            r"\bmust not use\b[^.]*\bworkforce memory\b|"
            r"\bblocked_truth_sources\b[^\]]*\bworkforce memory\b"
        ),
    ),
)

BACKEND_SELECTION_FORBIDDEN_PATTERNS = (
    ("SC-G5 opens gate", re.compile(r"\bsc-g5\s+opens\s+(?:the\s+)?gate\b")),
    (
        "backend selected for serving",
        re.compile(
            r"\bbackend\s+(?:is\s+)?selected\s+for\s+serving\b"
            r"|\bbackend selection (?:is )?(?:authorized|approved|allowed) for serving\b"
            r"|\bserving backend selection (?:is )?(?:authorized|approved|allowed)\b"
            r"|\bselected backend (?:is )?(?:authorized|approved|allowed) for serving\b"
        ),
    ),
    (
        "backend active",
        re.compile(r"\bbackend\s+(?:is\s+)?(?:active|enabled|live|ready)\b"),
    ),
    (
        "semantic cache serving ready",
        re.compile(
            r"\bsemantic(?:-| )cache\s+serving\s+(?:is\s+)?"
            r"(?:ready|active|enabled|live|authorized|allowed|approved|permitted)\b"
        ),
    ),
    (
        "Redis approved",
        re.compile(r"\bredis\s+(?:is\s+)?(?:approved|enabled|supported|allowed|active)\b"),
    ),
    (
        "GPTCache approved",
        re.compile(r"\bgptcache\s+(?:is\s+)?(?:approved|enabled|supported|allowed|active)\b"),
    ),
    (
        "Redis/GPTCache approved",
        re.compile(
            r"\bredis\s*(?:/|and)\s*gptcache\s+(?:are\s+)?"
            r"(?:approved|enabled|supported|allowed|active)\b"
        ),
    ),
    (
        "SC-G5 approves Redis",
        re.compile(r"\bsc-g5\s+(?:approves|enables|supports|allows)\s+redis\b"),
    ),
    (
        "SC-G5 approves GPTCache",
        re.compile(r"\bsc-g5\s+(?:approves|enables|supports|allows)\s+gptcache\b"),
    ),
    ("Redis URL", re.compile(r"\bredis://|\bredis_url\b")),
    ("GPTCache env", re.compile(r"\bgptcache_(?:url|backend|config|enabled)\b")),
    ("cache raw prompts", re.compile(r"\bcache(?:s)?\s+raw\s+prompts?\b")),
    ("cache raw responses", re.compile(r"\bcache(?:s)?\s+raw\s+(?:model\s+)?responses?\b")),
    (
        "provider-backed cache",
        re.compile(r"\bprovider-backed\s+cache\b|\bprovider\s+cache\s+backend\b"),
    ),
)

# --- Philosophy Admission Contract Constants ---
PHILOSOPHY_ADMISSION_CLASSES = frozenset(
    {
        "runtime_only",
        "blocked_from_cache",
        "verification_bundle_required",
        "future_cache_candidate_deferred",
    }
)

PHILOSOPHY_BLOCKED_SURFACES = (
    "billing_auth_entitlement_truth",
    "auth_session_account_identity_truth",
    "medical_or_therapy_routing",
    "compliance_legal_output_cache",
    "raw_user_free_text_cache_keys",
    "advisory_wiki_product_truth",
    "workforce_memory_product_truth",
    "graphrag_product_truth",
    "plugin_control_plane_product_truth",
    "fitchef_cbt_bypassing_validators",
)

PHILOSOPHY_FORBIDDEN_CLAIM_CLASSES = (
    "claim_class_gate_open_equivalence",
    "claim_class_live_philosophy_cache",
    "claim_class_provider_rollout_approved",
    "claim_class_verification_bundle_skipped",
    "claim_class_production_live_cache_key_behavior",
    "claim_class_pdf_design_intake_gate_override",
    "claim_class_runtime_expansion_approved",
)

PHILOSOPHY_RUNTIME_ONLY_SURFACES = (
    "philosophical_runtime_preview_validate_rewrite",
    "offline_logic_philosophy_replay",
    "eval_harness_without_cache_serving",
)

PHILOSOPHY_VERIFICATION_BUNDLE_REQUIRED_SURFACES = (
    "knowledge_promotion_decisions",
    "semantic_cache_admission_decisions",
    "recursive_retrieval_verification_merges",
    "philosophical_outputs_presentation_risk_canonical_facts",
    "write_or_mutate_knowledge_records",
)

PHILOSOPHY_FUTURE_CACHE_CANDIDATE_DEFERRED_SURFACES: tuple[str, ...] = ()

PHILOSOPHY_REFERENCES = (
    "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
    "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md",
    "core/insight/philosophical_runtime.py",
    "core/verification/",
)

PHILOSOPHY_SC_G5_MERGE_SHA = "cb1db8b40"
PHILOSOPHY_SC_G5_CONTRACT_PATH = (
    "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
)

PHILOSOPHY_ADMISSION_ROLLOUT_ORDER = (
    "SC-G1 rollout gate contract",
    "SC-G2 exact/fuzzy cache scaffold",
    "SC-G3 observability and false-hit harness",
    "SC-G4 bounded `/insight` semantic-cache experiment",
    "SC-G5 backend selection",
    "Philosophy admission contract reconciliation",
)

PHILOSOPHY_ADMISSION_REQUIRED_ANCHORS = (
    ("Philosophy PR-1 admission", re.compile(r"\bphilosophy epic v2 pr-1\b")),
    ("does not open gate", re.compile(r"\bdoes not open (?:the )?semantic-cache gate\b")),
    ("gate remains closed", re.compile(r"\bgate remains closed\b")),
    ("runtime allowed false", re.compile(r"\bruntime allowed:\s*false\b")),
    ("implementation allowed false", re.compile(r"\bimplementation allowed:\s*false\b")),
    ("does not duplicate SC-G5", re.compile(r"\bdoes not duplicate\b.*\bsc-g5\b")),
    ("runtime_only class", re.compile(r"\bruntime_only\b")),
    ("blocked_from_cache class", re.compile(r"\bblocked_from_cache\b")),
    (
        "verification_bundle_required class",
        re.compile(r"\bverification_bundle_required\b"),
    ),
    (
        "future_cache_candidate_deferred class",
        re.compile(r"\bfuture_cache_candidate_deferred\b"),
    ),
    ("philosophical_runtime reference", re.compile(r"\bcore/insight/philosophical_runtime\.py\b")),
    ("SC-G5 reference", re.compile(r"\bsemantic_cache_backend_selection_contract\.md\b")),
    ("sc_g5 merge commit", re.compile(r"\bcb1db8b40\b")),
    ("no Redis imports", re.compile(r"\bno redis imports\b")),
    ("no GPTCache imports", re.compile(r"\bno gptcache imports\b")),
    ("no embeddings", re.compile(r"\bno embeddings\b")),
    ("no vector search", re.compile(r"\b(?:no|blocked)\s+vector search\b")),
    ("no connection strings", re.compile(r"\b(?:no|blocked)\s+connection strings\b")),
    ("no cache adapters", re.compile(r"\b(?:no|blocked)\s+cache adapters\b")),
    ("no insight cache wiring", re.compile(r"\bno\b.*(?<!\w)/insight(?!\w).*\bcache wiring\b")),
)

PHILOSOPHY_RUNTIME_ONLY_SECTION_REQUIRED_ANCHORS = (
    ("no Redis imports", re.compile(r"\bno redis imports\b")),
    ("no GPTCache imports", re.compile(r"\bno gptcache imports\b")),
    ("no embeddings", re.compile(r"\bno embeddings\b")),
    ("no vector search", re.compile(r"\b(?:no|blocked)\s+vector search\b")),
    ("no connection strings", re.compile(r"\b(?:no|blocked)\s+connection strings\b")),
    ("no cache adapters", re.compile(r"\b(?:no|blocked)\s+cache adapters\b")),
    ("no insight cache wiring", re.compile(r"\bno\b.*(?<!\w)/insight(?!\w).*\bcache wiring\b")),
)

PHILOSOPHY_FORBIDDEN_CLAIMS_SECTION_POLARITY_RE = re.compile(
    r"\bpr-1 and downstream docs must not claim\s*:"
)
PHILOSOPHY_FORBIDDEN_CLAIMS_SECTION_PERMISSIVE_POLARITY_RE = re.compile(
    r"^pr-1 and downstream docs (?:may|can|should|must)"
    r"(?!\s+(?:not|never)\b)(?:\s+\w+){0,3}\s+claim\s*:"
    r"|^pr-1 and downstream docs "
    r"(?!are\s+(?:not|never)\s+"
    r"(?:allowed|permitted|approved|enabled|authorized|granted|supported|available)\b)"
    r"(?:are\s+)?(?!(?:not|never)\s)"
    r"(?:\w+\s+){0,3}"
    r"(?:allowed|permitted|approved|enabled|authorized|granted|supported|available)"
    r"\s+to\s+claim\s*:"
    r"|^(?:allowed|permitted|approved|enabled|authorized|granted|supported|available)"
    r"(?:\s+(?!to\b)\w+){0,3}\s+claims?(?:\s+\w+){0,3}\s*:"
    r"|^claims?\s+(?!(?:\w+\s+){0,3}(?:not|never|no\s+longer)\s+)"
    r"(?:(?:is|are)\s+)?"
    r"(?:\w+\s+){0,3}"
    r"(?:allowed|permitted|approved|enabled|authorized|granted|supported|available)\s*:"
)
PHILOSOPHY_FORBIDDEN_CLAIMS_SAFE_BULLET_PREFIX_RE = re.compile(
    r"^(?:"
    r"(?:forbidden\s+)?examples?"
    r"|do\s+not\s+claim"
    r"|must\s+not\s+claim"
    r"|the\s+following\s+are\s+forbidden\s+examples?"
    r"|not\s+allowed(?:\s+\w+){0,3}\s+claims?"
    r"|not\s+permitted(?:\s+\w+){0,3}\s+claims?"
    r"|never(?:\s+\w+){0,3}\s+claims?"
    r"|no(?:\s+\w+){0,3}\s+claims?"
    r")\s*(?::|-)?$"
)

PHILOSOPHY_ADMISSION_FORBIDDEN_PATTERNS = (
    (
        "philosophy admission opens gate",
        re.compile(
            r"\b(?:philosophy admission|philosophy pr-1 admission|philosophy pr-1|"
            r"pr-1 admission|pr-1|the admission contract|admission contract) "
            r"(?:(?:will|shall|can|may) "
            r"(?:re[- ]?open|open(?: up)?|unlock|activate|enable)|"
            r"(?:has|had) (?:re[- ]?opened|opened|unlocked|activated|enabled)|"
            r"(?:is|was|has been|had been) "
            r"(?:re[- ]?opening|opening|unlocking|activating|enabling)|"
            r"(?:re[- ]?open(?:s|ed)?|open(?:s|ed)?(?: up)?|unlock(?:s|ed)?|"
            r"activate(?:s|d)?|enable(?:s|d)?)) "
            r"(?:the )?(?:(?:global )?semantic[- ]cache|global) gate\b"
            r"|\bphilosophy admission open(?:s|ed) (?:the )?semantic[- ]cache gate\b"
            r"|\bphilosophy admission unlock(?:s|ed) (?:the )?semantic[- ]cache gate\b"
            r"|\bphilosophy pr-1 admission open(?:s|ed) (?:the )?semantic[- ]cache gate\b"
            r"|\bphilosophy pr-1 admission unlock(?:s|ed) "
            r"(?:the )?semantic[- ]cache gate\b"
            r"|\b(?:philosophy )?pr-1 open(?:s|ed)(?: up)? "
            r"(?:the )?semantic[- ]cache gate\b"
            r"|\b(?:philosophy )?pr-1 open(?:s|ed)(?: up)? "
            r"(?:the )?global semantic[- ]cache gate\b"
            r"|\b(?:philosophy )?pr-1 unlock(?:s|ed) (?:the )?semantic[- ]cache gate\b"
            r"|\b(?:philosophy )?pr-1 (?:has|had) "
            r"(?:opened|unlocked|activated|enabled) "
            r"(?:the )?(?:(?:global )?semantic[- ]cache|global) gate\b"
            r"|\b(?:philosophy )?pr-1 "
            r"(?:(?:is|was|has been) )?(?:opening|unlocking|activating|enabling) "
            r"(?:the )?(?:(?:global )?semantic[- ]cache|global) gate\b"
            r"|\bphilosophy admission open(?:s|ed) (?:the )?global gate\b"
            r"|\bphilosophy admission unlock(?:s|ed) (?:the )?global gate\b"
            r"|\bphilosophy admission activate(?:s|d) (?:the )?"
            r"(?:global|semantic[- ]cache) gate\b"
            r"|\bphilosophy admission enable(?:s|d) (?:the )?"
            r"(?:global|semantic[- ]cache) gate\b"
            r"|\b(?:philosophy )?pr-1(?: admission)? open(?:s|ed) (?:the )?global gate\b"
            r"|\b(?:philosophy )?pr-1(?: admission)? unlock(?:s|ed) (?:the )?global gate\b"
            r"|\b(?:philosophy )?pr-1(?: admission)? activate(?:s|d) (?:the )?"
            r"(?:global|semantic[- ]cache) gate\b"
            r"|\b(?:philosophy )?pr-1(?: admission)? enable(?:s|d) (?:the )?"
            r"(?:global|semantic[- ]cache) gate\b"
            r"|\b(?:philosophy admission|philosophy pr-1 admission|"
            r"philosophy pr-1|pr-1 admission|pr-1) does not "
            r"(?:only|just|merely|simply|solely|exclusively) "
            r"(?:open|unlock|activate|enable) (?:the )?"
            r"(?:global|semantic[- ]cache) gate\b"
            r"|\bphilosophy(?: pr-1)?(?: admission)? "
            r"is equivalent to opening (?:the )?(?:global|semantic[- ]cache) gate\b"
            r"|\b(?:philosophy )?pr-1(?: admission)? "
            r"is equivalent to opening (?:the )?(?:global|semantic[- ]cache) gate\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate (?:is )?(?:now )?open for "
            r"(?:philosophy pr-1|pr-1)\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate is open for philosophy admission\b"
            r"|\b(?:the )?(?:(?:global )?semantic[- ]cache|global) gate "
            r"(?:is|was|has been) (?:now )?open\b"
            r"|\b(?:the )?(?:(?:global )?semantic[- ]cache|global) gate "
            r"(?:(?:is|was|has been) still |(?:still )?remains |"
            r"(?:has|had) remained |remained |(?:has )?stayed |stays |"
            r"(?:continues|continued|has continued) to be )"
            r"(?:open|opened|re[- ]?opened|unlocked|live|enabled|active|approved|ready)\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate "
            r"(?:became|has become) (?:now )?open\b"
            r"|\b(?:the )?(?:(?:global )?semantic[- ]cache|global) gate "
            r"(?:has|had) (?:now )?opened\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate is opened "
            r"for philosophy admission\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate opened for philosophy admission\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate "
            r"(?:is|was|has been|has now been) opened\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate "
            r"(?:is|was|has been|has now been) (?:now )?unlocked"
            r"(?: by (?:philosophy admission|philosophy pr-1|pr-1))?\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate "
            r"(?:is|was|has been|has now been) (?:now )?re[- ]?opened"
            r"(?: by (?:philosophy admission|philosophy pr-1|pr-1))?\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate "
            r"(?:is|was|has been) no longer closed\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate "
            r"(?:is|was|has been) not closed anymore\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate "
            r"(?:is|was|has been) (?:active|enabled|on|turned on|live|approved|ready)\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate "
            r"(?:is|was|has been) opened by "
            r"(?:philosophy admission|philosophy pr-1|pr-1)\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate (?:can|may) be opened "
            r"for philosophy admission\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate (?:can|may) be "
            r"(?:unlocked|activated|enabled) for philosophy admission\b"
            r"|\b(?:the )?(?:global|semantic[- ]cache) gate opens for philosophy admission\b"
            r"|\b(?:the )?(?:(?:global )?semantic[- ]cache|global) gate opens "
            r"(?:in|during|with|by) (?:philosophy )?pr-1\b"
            r"|\b(?:the )?(?:(?:global )?semantic[- ]cache|global) gate "
            r"(?:will|shall) (?:be )?"
            r"(?:open|opened|re[- ]?opened|unlocked|activated|enabled) "
            r"(?:in|during|with|by) (?:philosophy )?pr-1\b"
            r"|\b(?:philosophy )?pr-1(?: admission)? (?:can|may) "
            r"(?:open|unlock|activate|enable) "
            r"(?:the )?(?:global|semantic[- ]cache) gate\b"
            r"|\bphilosophy admission (?:can|may) "
            r"(?:open|unlock|activate|enable) "
            r"(?:the )?(?:global|semantic[- ]cache) gate\b"
        ),
    ),
    (
        "philosophical semantic cache live",
        re.compile(
            r"\bphilosophical semantic[- ]cache "
            r"(?:(?:is|are|was|were|has been|have been) "
            r"(?:not (?:only|just|merely|simply|solely|exclusively) )?|"
            r"(?:isn't|aren't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:live|active|enabled|open)\b"
            r"|\bphilosophical semantic[- ]cache paths? "
            r"(?:(?:is|are|was|were|has been|have been) "
            r"(?:not (?:only|just|merely|simply|solely|exclusively) )?|"
            r"(?:isn't|aren't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:live|active|enabled|open|available|supported)\b"
            r"|\bphilosophical semantic[- ]cache serving "
            r"(?:(?:is|are|was|were|has been|have been) "
            r"(?:not (?:only|just|merely|simply|solely|exclusively) )?|"
            r"(?:isn't|aren't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:live|active|enabled|open|approved)\b"
            r"|\b(?:semantic[- ]cache serving|cache serving|serving) "
            r"(?:(?:is|are|was|were|has been|have been) "
            r"(?:not (?:only|just|merely|simply|solely|exclusively) )?|"
            r"(?:isn't|aren't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:live|active|enabled|open|approved) for philosophy admission\b"
            r"|\bphilosophical semantic[- ]cache paths? "
            r"(?:(?:is|are|was|were|has been|have been) "
            r"(?:not (?:only|just|merely|simply|solely|exclusively) )?|"
            r"(?:isn't|aren't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"approved for serving\b"
        ),
    ),
    (
        "production-live philosophical cache-key behavior",
        re.compile(
            r"\bproduction[- ]live philosophical cache[- ]key behavior\b"
            r"|\bphilosophical cache[- ]key behavior "
            r"(?:is|was|has been) production[- ]live\b"
        ),
    ),
    (
        "redis philosophical cache approved",
        re.compile(
            r"\bredis philosophical cache "
            r"(?:(?:is|was|has been) )?"
            r"(?:allowed|permitted|approved|enabled|authorized|granted|supported|available)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled) redis rollout "
            r"for (?:the )?philosophical (?:semantic[- ]cache|cache) paths?\b"
            r"|\bredis(?: rollout)? "
            r"(?:(?:is|was|has been) |(?:is|was|has been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:isn't|wasn't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|authorized|granted|available|supported) "
            r"for (?:the )?philosophical "
            r"(?:semantic[- ]cache|cache) paths?\b"
            r"|(?<!\bno )(?<!\bnot )(?<!\bnever )"
            r"(?<!\bno currently )(?<!\bnot currently )(?<!\bnever currently )"
            r"(?<!\bno actually )(?<!\bnot actually )(?<!\bnever actually )"
            r"(?<!\bno explicitly )(?<!\bnot explicitly )(?<!\bnever explicitly )"
            r"\b(?:allowed|permitted|approved|enabled) redis rollout "
            r"for (?:the )?philosophical "
            r"(?:semantic[- ]cache|cache) paths?\b"
        ),
    ),
    (
        "gptcache philosophical cache approved",
        re.compile(
            r"\bgptcache philosophical cache "
            r"(?:(?:is|was|has been) )?"
            r"(?:allowed|permitted|approved|enabled|authorized|granted|supported|available)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled) gptcache rollout "
            r"for (?:the )?philosophical (?:semantic[- ]cache|cache) paths?\b"
            r"|\bgptcache(?: rollout)? "
            r"(?:(?:is|was|has been) |(?:is|was|has been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:isn't|wasn't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|authorized|granted|available|supported) "
            r"for (?:the )?philosophical "
            r"(?:semantic[- ]cache|cache) paths?\b"
            r"|(?<!\bno )(?<!\bnot )(?<!\bnever )"
            r"(?<!\bno currently )(?<!\bnot currently )(?<!\bnever currently )"
            r"(?<!\bno actually )(?<!\bnot actually )(?<!\bnever actually )"
            r"(?<!\bno explicitly )(?<!\bnot explicitly )(?<!\bnever explicitly )"
            r"\b(?:allowed|permitted|approved|enabled) gptcache rollout "
            r"for (?:the )?philosophical "
            r"(?:semantic[- ]cache|cache) paths?\b"
        ),
    ),
    (
        "redis imports allowed in pr-1",
        re.compile(
            r"\bredis (?:imports?|clients?|probes?) "
            r"(?:(?:are|is|was|were|has been|have been) |"
            r"(?:are|is|was|were|has been|have been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:aren't|isn't|wasn't|weren't) "
            r"(?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|supported|available) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled|grants|granted) redis (?:imports?|clients?|probes?)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|imports?|uses?|wires?) redis (?:imports?|clients?|probes?)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:has|includes?) redis (?:imports?|clients?|probes?)"
            r"(?: for philosophy admission)?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|imports?|uses?|wires?) redis\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:(?:is|are|was|were|has been|have been) )?"
            r"(?:using|wiring|importing) redis(?: for philosophy admission)?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"enables? redis(?: for philosophy admission)?\b"
        ),
    ),
    (
        "gptcache imports allowed in pr-1",
        re.compile(
            r"\bgptcache (?:imports?|clients?|probes?) "
            r"(?:(?:are|is|was|were|has been|have been) |"
            r"(?:are|is|was|were|has been|have been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:aren't|isn't|wasn't|weren't) "
            r"(?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|supported|available) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled|grants|granted) gptcache "
            r"(?:imports?|clients?|probes?)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|imports?|uses?|wires?) gptcache (?:imports?|clients?|probes?)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:has|had|includes?|included|contains?|contained) "
            r"gptcache (?:imports?|clients?|probes?)(?: for philosophy admission)?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|imports?|uses?|wires?) gptcache\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:(?:is|are|was|were|has been|have been) )?"
            r"(?:using|wiring|importing) gptcache(?: for philosophy admission)?\b"
        ),
    ),
    (
        "embeddings allowed in pr-1",
        re.compile(
            r"\b(?:embeddings?|embedding models?) "
            r"(?:(?:are|is|was|were|has been|have been) |"
            r"(?:are|is|was|were|has been|have been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:aren't|isn't|wasn't|weren't) "
            r"(?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|authorized|granted|available|supported) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled|grants|granted) "
            r"(?:embeddings?|embedding models?)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|uses?|wires?|calls?) (?:embeddings?|embedding models?)\b"
        ),
    ),
    (
        "insight cache wiring allowed in pr-1",
        re.compile(
            r"(?<!\w)/insight cache wiring "
            r"(?:(?:is|was|has been) |"
            r"(?:is|was|has been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:isn't|wasn't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|authorized|granted|available|supported) "
            r"(?:in pr-1|for pr-1|for philosophy admission|"
            r"by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled) (?<!\w)/insight cache wiring\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|uses?|wires?) (?<!\w)/insight cache wiring\b"
        ),
    ),
    (
        "vector search allowed in pr-1",
        re.compile(
            r"\bvector search(?:es)? "
            r"(?:(?:are|is|was|were|has been|have been) |"
            r"(?:are|is|was|were|has been|have been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:aren't|isn't|wasn't|weren't) "
            r"(?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|authorized|granted|available|supported) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled|grants|granted) vector search(?:es)?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|uses?|wires?|performs?) vector search(?:es)?\b"
        ),
    ),
    (
        "connection strings allowed in pr-1",
        re.compile(
            r"\b(?:redis |gptcache )?connection strings? "
            r"(?:(?:are|is|was|were|has been|have been) |"
            r"(?:are|is|was|were|has been|have been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:aren't|isn't|wasn't|weren't) "
            r"(?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|available|supported) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled|grants|granted) "
            r"(?:redis |gptcache )?connection strings?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|uses?|wires?|stores?|persists?|"
            r"(?:has|had) (?:added|used|wired|stored|persisted)) "
            r"(?:redis |gptcache )?connection strings?\b"
            r"|\b(?:redis |gptcache )?connection strings? "
            r"(?:(?:are|is|was|were|has been|have been) )?"
            r"(?:added|used|wired|stored|persisted) "
            r"(?:in pr-1|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
        ),
    ),
    (
        "cache adapters allowed in pr-1",
        re.compile(
            r"\bcache adapt(?:er|or)s? "
            r"(?:(?:are|is|was|were|has been|have been) |"
            r"(?:are|is|was|were|has been|have been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:aren't|isn't|wasn't|weren't) "
            r"(?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|authorized|granted|available|supported) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled|grants|granted) cache adapt(?:er|or)s?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|uses?|wires?|stores?|persists?|"
            r"(?:has|had) (?:added|used|wired|stored|persisted)) "
            r"cache adapt(?:er|or)s?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:has|includes?) cache adapt(?:er|or)s?\b"
            r"|\bcache adapt(?:er|or)s? "
            r"(?:(?:are|is|was|were|has been|have been) )?"
            r"(?:added|used|wired|stored|persisted) "
            r"(?:in pr-1|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
        ),
    ),
    (
        "runtime allowed in pr-1",
        re.compile(
            r"\bruntime(?: behavior|[- ]expansion| paths?| permissions?)? "
            r"(?:(?:are|is|was|were|has been|have been) |"
            r"(?:are|is|was|were|has been|have been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:aren't|isn't) (?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|available|supported) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\bruntime(?: behavior|[- ]expansion| paths?| permissions?)? "
            r"(?:get|gets) (?:allowed|permitted|approved|enabled|supported) "
            r"(?:in pr-1|for philosophy admission)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|authorized|approved|"
            r"allowed|permitted|enabled|grants|granted) runtime(?:[- ]expansion| permissions?)"
            r"(?: for philosophy admission)?\b"
            r"|\b(?:providers?|storage) "
            r"(?:(?:are|is|was|were|has been|have been) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|supported|available) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:provider calls?|semantic[- ]cache storage|cache storage) "
            r"(?:(?:are|is|was|were|has been|have been) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|supported|available) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|grants) "
            r"(?:providers?|provider calls?|storage|semantic[- ]cache storage|cache storage)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|uses?|wires?|calls?|(?:has|had) (?:added|used|wired|called)) "
            r"(?:providers?|provider calls?|storage|semantic[- ]cache storage|cache storage)"
            r"(?: for philosophy admission)?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:calls?|(?:has|had) called) "
            r"(?:openai|anthropic|google|azure|llm|model) providers?"
            r"(?: for philosophy admission)?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:adds?|uses?|wires?|(?:has|had) (?:added|used|wired)) "
            r"(?:openai|anthropic|google|azure|llm|model) providers?"
            r"(?: for philosophy admission)?\b"
        ),
    ),
    (
        "cache IO allowed in pr-1",
        re.compile(
            r"\b(?:semantic[- ]cache |cache )(?:reads?|writes?|admission(?: decisions?)?) "
            r"(?:(?:are|is|was|were|has been|have been) |"
            r"(?:are|is|was|were|has been|have been) not "
            r"(?:only|just|merely|simply|solely|exclusively) |"
            r"(?:aren't|isn't|wasn't|weren't) "
            r"(?:only|just|merely|simply|solely|exclusively) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|available|supported) "
            r"(?:in pr-1|for philosophy admission|by (?:philosophy admission|philosophy pr-1|pr-1))\b"
            r"|\bcache admission (?:(?:is|was|has been) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|available|supported) "
            r"for philosophy admission\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|grants|authorized|approved|"
            r"allowed|permitted|enabled|granted) (?:semantic[- ]cache |cache )?"
            r"(?:reads?|writes?|admission(?: decisions?)?)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:reads? from|writes? to|stores?|"
            r"(?:has|had) (?:read from|written to|stored))"
            r"(?: (?:semantic[- ]cache|cache))?"
            r"(?: entries?)?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:reads?|writes?|(?:has|had) (?:read|written)) "
            r"(?:semantic[- ]cache |cache )?(?:entries?|records?)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"reads? (?:semantic[- ]cache|cache)\b"
        ),
    ),
    (
        "blocked surface cache admission allowed",
        re.compile(
            r"\b(?:billing[/ ]auth entitlement truth|auth[/ ]session[/ ]account identity truth|"
            r"auth[/ ]session account identity truth|auth session account identity truth|"
            r"billing truth|subscription truth|entitlement truth|paywall truth|"
            r"auth truth|session truth|account identity truth|user[- ]account truth|"
            r"medical(?: diagnosis| treatment| medication| therapy)? routing|therapy routing|"
            r"compliance output caches?|legal output caches?|compliance[/ ]legal output caches?|"
            r"raw user free[- ]text (?:cache keys|persistence(?: for cache keys)?)|"
            r"advisory wiki product truth|"
            r"advisory wiki outputs as product truth|"
            r"workforce memory outputs as product truth|graphrag outputs as product truth|"
            r"plugin[/ ]control[- ]plane outputs as product truth|"
            r"workforce memory product truth|graphrag product truth|"
            r"plugin[/ ]control[- ]plane product truth|"
            r"fitchef[/ ]cbt coaching paths? (?:that )?bypass(?:ing)? "
            r"wellness[- ]only validators|fitchef cbt bypassing validators) "
            r"(?:(?:is|are|was|were|has been|have been) )?"
            r"(?:allowed|permitted|approved|enabled|granted|authorized|"
            r"available|supported|cache eligible) "
            r"for (?:semantic[- ]cache|cache) admission(?: in pr-1)?\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|permits|enables|grants) "
            r"(?:billing truth|subscription truth|entitlement truth|paywall truth|"
            r"auth truth|session truth|account identity truth|user[- ]account truth|"
            r"auth[/ ]session[/ ]account identity truth|auth[/ ]session account identity truth|"
            r"medical(?: diagnosis| treatment| medication| therapy)? routing|therapy routing|"
            r"compliance output caches?|legal output caches?|compliance[/ ]legal output caches?|"
            r"raw user free[- ]text (?:cache keys|persistence(?: for cache keys)?)|"
            r"advisory wiki outputs as product truth|"
            r"workforce memory outputs as product truth|graphrag outputs as product truth|"
            r"plugin[/ ]control[- ]plane outputs as product truth|"
            r"fitchef[/ ]cbt coaching paths? (?:that )?bypass(?:ing)? "
            r"wellness[- ]only validators) "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:admits?|adds?|caches?|stores?|writes?|persists?|uses?|wires?) "
            r"(?:billing truth|subscription truth|entitlement truth|paywall truth|"
            r"auth truth|session truth|account identity truth|user[- ]account truth|"
            r"auth[/ ]session[/ ]account identity truth|auth[/ ]session account identity truth|"
            r"medical(?: diagnosis| treatment| medication| therapy)? routing|therapy routing|"
            r"compliance output caches?|legal output caches?|compliance[/ ]legal output caches?|"
            r"raw user free[- ]text (?:cache keys|persistence(?: for cache keys)?)|"
            r"advisory wiki outputs as product truth|"
            r"workforce memory outputs as product truth|graphrag outputs as product truth|"
            r"plugin[/ ]control[- ]plane outputs as product truth|"
            r"advisory wiki product truth|"
            r"workforce memory product truth|graphrag product truth|"
            r"plugin[/ ]control[- ]plane product truth|"
            r"fitchef[/ ]cbt coaching paths? (?:that )?bypass(?:ing)? "
            r"wellness[- ]only validators)"
            r"(?: (?:to|for) (?:semantic[- ]cache|cache) admission)?\b"
        ),
    ),
    (
        "cache admission without verification bundle",
        re.compile(
            r"\b(?:knowledge promotion|semantic[- ]cache admission|"
            r"recursive retrieval verification merges?|"
            r"philosophical outputs? presentation risk canonical facts?|"
            r"write or mutate knowledge records?) "
            r"(?:decisions? )?"
            r"(?:(?:are|is|was|were|has been|have been) )?"
            r"(?:cache eligible|allowed|permitted|approved|enabled) "
            r"without (?:a )?(?:passed )?(?:verification[- ]bundle|bundle)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:(?:will|shall|can|may) "
            r"(?:promote|write|mutate|store|persist)|"
            r"(?:has|have|had) "
            r"(?:promoted|written|mutated|stored|persisted)|"
            r"(?:is|are|was|were|has been|have been) "
            r"(?:promoting|writing|mutating|storing|persisting)|"
            r"(?:promotes?|writes?|mutates?|stores?|persists?)) "
            r"(?:knowledge|knowledge records?|knowledge promotion(?: decisions?)?) "
            r"without (?:a )?(?:passed )?(?:verification[- ]bundles?|bundles?)\b"
        ),
    ),
    (
        "design intake overrides gate markers",
        re.compile(
            r"\b(?:pdf[/ ]design intake|pdf intake|design intake) "
            r"(?:(?:can|may) )?(?:overrides?|bypasses?) repo gate markers\b"
        ),
    ),
    (
        "verification bundle optional",
        re.compile(
            r"\bverification[- ]bundles? (?:(?:is|are) )?optional "
            r"for (?:semantic[- ]cache|cache)(?: admission)?\b"
            r"|\bverification[- ]bundle requirements? (?:is|are) optional "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundle requirements? (?:is|are|may be|can be) skipped "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundles? (?:(?:is|are) )?not required "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundles? (?:(?:is|are) )?not needed "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundles? (?:(?:is|are) )?unnecessary "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\b(?:semantic[- ]cache |cache )?admission "
            r"(?:does not|doesn't|do not|don't) require "
            r"(?:a )?verification[- ]bundles?\b"
            r"|\b(?:semantic[- ]cache |cache )?admission "
            r"(?:does not|doesn't|do not|don't) need "
            r"(?:a )?verification[- ]bundles?\b"
            r"|\b(?:semantic[- ]cache |cache )?admission requires no "
            r"verification[- ]bundles?\b"
            r"|\b(?:semantic[- ]cache |cache )?admission "
            r"(?:can|may) (?:bypass|skip|omit|waive) "
            r"(?:a )?verification[- ]bundles?\b"
            r"|\b(?:semantic[- ]cache |cache )?admission "
            r"bypasses (?:a )?verification[- ]bundles?\b"
            r"|\b(?:semantic[- ]cache |cache )?admission "
            r"skips (?:a )?verification[- ]bundles?\b"
            r"|\b(?:semantic[- ]cache |cache )?admission "
            r"(?:has|had) (?:bypassed|skipped|waived) "
            r"(?:a )?verification[- ]bundles?\b"
            r"|\b(?:semantic[- ]cache |cache )?admission "
            r"(?:(?:is|are|was|were|has been|have been) )?exempt from "
            r"(?:a )?verification[- ]bundles?\b"
            r"|\bverification[- ]bundle requirements? "
            r"(?:(?:is|are|was|were|has been|have been) still |"
            r"(?:still )?remains? |(?:has|have|had) remained |"
            r"remained |(?:has|have|had) stayed |stays? )"
            r"(?:optional|skippable|waivable|omittable|not required) "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundles? (?:(?:may be|can be|is|are) )?omitted "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundle requirements? (?:(?:may be|can be|is|are) )?"
            r"omitted for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundle requirements? "
            r"(?:(?:is|are|was|were|may be|can be) )?"
            r"(?:bypassed|waived|skipped) for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundle requirements? "
            r"(?:has|have|had) been (?:bypassed|waived|skipped) "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\bverification[- ]bundles? "
            r"(?:(?:is|are|was|were|has been|have been|may be|can be) )?"
            r"(?:bypassed|waived|skipped) for (?:semantic[- ]cache|cache) admission\b"
            r"|\bskipped verification[- ]bundles? "
            r"for (?:semantic[- ]cache|cache) admission\b"
            r"|\bskipped verification[- ]bundle requirements? "
            r"for (?:semantic[- ]cache|cache) admission\b"
        ),
    ),
    (
        "backend selection authorized by philosophy admission",
        re.compile(
            r"\bphilosophy admission replaces sc-g2-sc-g5 contracts\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) replaces "
            r"(?:sc-g[2-5]|sc g[2-5]) "
            r"(?:exact[/ ]fuzzy cache scaffold|observability|bounded insight experiment|"
            r"backend[- ]selection|contracts?)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:authorizes|approves|allows|enables|permits|authorized|approved|"
            r"allowed|enabled|permitted|grants|granted) "
            r"(?:backend[- ]selection|semantic[- ]cache backend[- ]selection|serving|"
            r"semantic[- ]cache serving|backend[- ]selection and serving)\b"
            r"|\b(?:semantic[- ]cache )?backend[- ]selections? "
            r"(?:(?:is|are|was|were|has been|have been) |"
            r"(?:can|may|will|shall) be )"
            r"(?:authorized|approved|allowed|enabled|permitted|granted) "
            r"for philosophy admission\b"
            r"|\b(?:(?:semantic[- ]cache )?backend[- ]selections?|semantic[- ]cache serving|serving) "
            r"(?:(?:is|are|was|were|has been|have been) |"
            r"(?:is|are|was|were|has been|have been) still |"
            r"(?:still )?remains? |(?:has|have|had) remained |remained |"
            r"(?:has|have|had) stayed |stays? |(?:can|may|will|shall) be )"
            r"(?:authorized|approved|allowed|enabled|permitted|granted) "
            r"(?:by philosophy admission|for philosophy admission)\b"
            r"|\b(?:semantic[- ]cache serving|cache serving|serving) "
            r"(?:(?:is|are|was|were|has been|have been) |"
            r"(?:is|are|was|were|has been|have been) still |"
            r"(?:still )?remains? |(?:has|have|had) remained |remained |"
            r"(?:has|have|had) stayed |stays? |(?:can|may|will|shall) be )"
            r"(?:authorized|approved|allowed|enabled|permitted|granted) "
            r"by (?:philosophy admission|philosophy pr-1|pr-1)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:performs backend selection|selects (?:a )?backends? for serving)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:selects|selected|has selected|had selected) (?:redis|gptcache) "
            r"(?:as (?:the )?(?:semantic[- ]cache )?backend|"
            r"backend for philosophy admission)\b"
            r"|\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:serves|served|has served|had served|is serving|was serving|"
            r"has been serving|will serve|will be serving) "
            r"(?:(?:philosophical|philosophy) )?(?:semantic[- ]cache|cache) traffic\b"
        ),
    ),
    (
        "SC-G5 matrix duplicated",
        re.compile(
            r"\b(?:philosophy admission|philosophy pr-1|pr-1) "
            r"(?:restates?|duplicates?|copies|includes?|documents?|enumerates?) "
            r"(?:the )?sc-g5 "
            r"(?:ranking rules?|backend[- ](?:evaluation|selection) matrix|candidate labels?)\b"
            r"|\bsc-g5 (?:ranking rules?|backend[- ](?:evaluation|selection) matrix|candidate labels?) "
            r"(?:is|are|was|were|has been|have been) "
            r"(?:restated|duplicated|copied|included|documented|enumerated) "
            r"(?:by|into|in) (?:philosophy admission|philosophy pr-1|pr-1)\b"
        ),
    ),
    (
        "SC-G5 in-memory label duplicated",
        re.compile(
            r"\b(?<!not\s)(?<!no\s)(?<!never\s)(?<!can't\s)(?<!cannot\s)"
            r"(?<!won't\s)(?<!shouldn't\s)(?<!mustn't\s)(?<!doesn't\s)(?<!don't\s)"
            r"(?:lists?|includes?|copies|duplicates?|defines|uses|allows|approves|reuses|"
            r"restates|documents?|names?|enumerates?)"
            r"\s+(?:the\s+)?(?:sc-g5\s+)?in_memory_label\b"
            r"|\bin_memory_label\s+(?:is\s+)?"
            r"(?:listed|included|copied|duplicated|defined|used|allowed|approved|reused|"
            r"restated|documented|named|enumerated)\b"
        ),
    ),
    (
        "SC-G5 redis label duplicated",
        re.compile(
            r"\b(?<!not\s)(?<!no\s)(?<!never\s)(?<!can't\s)(?<!cannot\s)"
            r"(?<!won't\s)(?<!shouldn't\s)(?<!mustn't\s)(?<!doesn't\s)(?<!don't\s)"
            r"(?:lists?|includes?|copies|duplicates?|defines|uses|allows|approves|reuses|"
            r"restates|documents?|names?|enumerates?)"
            r"\s+(?:the\s+)?(?:sc-g5\s+)?redis_label\b"
            r"|\bredis_label\s+(?:is\s+)?"
            r"(?:listed|included|copied|duplicated|defined|used|allowed|approved|reused|"
            r"restated|documented|named|enumerated)\b"
        ),
    ),
    (
        "SC-G5 gptcache label duplicated",
        re.compile(
            r"\b(?<!not\s)(?<!no\s)(?<!never\s)(?<!can't\s)(?<!cannot\s)"
            r"(?<!won't\s)(?<!shouldn't\s)(?<!mustn't\s)(?<!doesn't\s)(?<!don't\s)"
            r"(?:lists?|includes?|copies|duplicates?|defines|uses|allows|approves|reuses|"
            r"restates|documents?|names?|enumerates?)"
            r"\s+(?:the\s+)?(?:sc-g5\s+)?gptcache_label\b"
            r"|\bgptcache_label\s+(?:is\s+)?"
            r"(?:listed|included|copied|duplicated|defined|used|allowed|approved|reused|"
            r"restated|documented|named|enumerated)\b"
        ),
    ),
)

PHILOSOPHY_SC_G5_LABEL_DUPLICATION_PATTERN_LABELS = {
    "SC-G5 in-memory label duplicated",
    "SC-G5 redis label duplicated",
    "SC-G5 gptcache label duplicated",
    "SC-G5 matrix duplicated",
}

PHILOSOPHY_PR1_PERMISSION_PATTERN_LABELS = {
    "redis philosophical cache approved",
    "gptcache philosophical cache approved",
    "redis imports allowed in pr-1",
    "gptcache imports allowed in pr-1",
    "embeddings allowed in pr-1",
    "insight cache wiring allowed in pr-1",
    "vector search allowed in pr-1",
    "connection strings allowed in pr-1",
    "cache adapters allowed in pr-1",
    "runtime allowed in pr-1",
    "cache IO allowed in pr-1",
    "blocked surface cache admission allowed",
}

PHILOSOPHY_NEGATED_GATE_OPEN_PATTERN_LABELS = {
    "philosophy admission opens gate",
}

PHILOSOPHY_NEGATED_DOWNSTREAM_FORBIDDEN_PATTERN_LABELS = {
    "philosophical semantic cache live",
    "production-live philosophical cache-key behavior",
    "verification bundle optional",
    "cache admission without verification bundle",
    "backend selection authorized by philosophy admission",
}

PHILOSOPHY_NEGATED_DUPLICATION_PREFIX_RE = re.compile(
    r"\b(?:no|not|never|can't|cannot|won't|shouldn't|mustn't|doesn't|don't|"
    r"should\s+not|must\s+not|does\s+not|do\s+not)\b"
    r"(?:\s+(?:safely|intentionally|accidentally|ever))?\s*$"
)

PHILOSOPHY_NEGATED_PERMISSION_PREFIX_RE = re.compile(
    r"(?:^|\s)(?:no|not|never|can't|cannot|won't|shouldn't|mustn't|doesn't|don't|"
    r"should\s+not|must\s+not|does\s+not|do\s+not)\b"
    r"(?:\s+(?:currently|yet|formally|actually|explicitly)){0,3}\s*$"
)
PHILOSOPHY_NEGATED_PERMISSION_DOMAIN_RE = re.compile(
    r"\b(?:pr-1|philosophy admission|semantic[- ]cache gate|global gate|redis|"
    r"gptcache|backend[- ]selection|serving|runtime|providers?|storage|cache|"
    r"insight|verification|billing|subscription|entitlement|paywall|medical|"
    r"compliance|raw|advisory|workforce|graphrag|plugin|fitchef|cbt)\b"
)

PHILOSOPHY_FORBIDDEN_CLAIM_PATTERN_LABELS = {
    "claim_class_gate_open_equivalence": ("philosophy admission opens gate",),
    "claim_class_live_philosophy_cache": ("philosophical semantic cache live",),
    "claim_class_provider_rollout_approved": (
        "redis philosophical cache approved",
        "gptcache philosophical cache approved",
        "redis imports allowed in pr-1",
        "gptcache imports allowed in pr-1",
        "embeddings allowed in pr-1",
        "insight cache wiring allowed in pr-1",
        "vector search allowed in pr-1",
        "connection strings allowed in pr-1",
        "cache adapters allowed in pr-1",
    ),
    "claim_class_runtime_expansion_approved": (
        "runtime allowed in pr-1",
        "backend selection authorized by philosophy admission",
        "cache IO allowed in pr-1",
        "blocked surface cache admission allowed",
    ),
    "claim_class_verification_bundle_skipped": (
        "verification bundle optional",
        "cache admission without verification bundle",
    ),
    "claim_class_production_live_cache_key_behavior": (
        "production-live philosophical cache-key behavior",
    ),
    "claim_class_pdf_design_intake_gate_override": ("design intake overrides gate markers",),
}

MARKER_RE = re.compile(r"<!--\s*(?P<key>SEMANTIC_CACHE_[A-Z_]+):\s*(?P<value>.*?)\s*-->")
MACHINE_JSON_RE = re.compile(r"```json\s*(?P<payload>\{.*?\})\s*```", re.DOTALL)
MARKDOWN_BULLET_PREFIX_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
MARKDOWN_TASK_PREFIX_RE = re.compile(r"^\[[ xX]\]\s+")
MARKDOWN_BLOCKQUOTE_PREFIX_RE = re.compile(r"^(?:>\s*)+")
MARKDOWN_HEADING_PREFIX_RE = re.compile(r"^#{1,6}\s+")
MARKDOWN_SECTION_RE = re.compile(r"(?m)^##\s+")


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    text = re.sub(r"[*`]+", "", text)
    text = re.sub(r"[/]+", "/", text)
    return re.sub(r"\s+", " ", text)


def _extract_markers(text: str) -> tuple[dict[str, str], list[str]]:
    markers: dict[str, str] = {}
    duplicates: list[str] = []
    for match in MARKER_RE.finditer(text):
        key = match.group("key")
        if key in markers and key not in duplicates:
            duplicates.append(key)
        markers[key] = match.group("value").strip().lower()
    return markers, duplicates


def _forbidden_claim_errors(text: str) -> list[str]:
    normalized = _normalize_text(text)
    errors: list[str] = []
    for label, pattern in FORBIDDEN_CLAIM_PATTERNS:
        for match in pattern.finditer(normalized):
            if _is_negated_philosophy_permission_claim(normalized, match):
                continue
            errors.append(f"forbidden semantic-cache claim: {label}")
            break
    return errors


def _is_negated_philosophy_duplication_claim(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 80) : match.start()]
    return PHILOSOPHY_NEGATED_DUPLICATION_PREFIX_RE.search(prefix) is not None


def _is_negated_philosophy_permission_claim(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 80) : match.start()]
    if PHILOSOPHY_NEGATED_PERMISSION_PREFIX_RE.search(prefix) is None:
        return False
    token_count = len(prefix.strip().split())
    return token_count <= 3 or PHILOSOPHY_NEGATED_PERMISSION_DOMAIN_RE.search(prefix) is not None


def _philosophy_admission_forbidden_claim_errors(text: str) -> list[str]:
    errors: list[str] = []
    for label, pattern in PHILOSOPHY_ADMISSION_FORBIDDEN_PATTERNS:
        for match in pattern.finditer(text):
            if label in PHILOSOPHY_SC_G5_LABEL_DUPLICATION_PATTERN_LABELS and (
                _is_negated_philosophy_duplication_claim(text, match)
            ):
                continue
            if label in PHILOSOPHY_PR1_PERMISSION_PATTERN_LABELS and (
                _is_negated_philosophy_permission_claim(text, match)
            ):
                continue
            if label in PHILOSOPHY_NEGATED_GATE_OPEN_PATTERN_LABELS and (
                _is_negated_philosophy_permission_claim(text, match)
            ):
                continue
            if label in PHILOSOPHY_NEGATED_DOWNSTREAM_FORBIDDEN_PATTERN_LABELS and (
                _is_negated_philosophy_permission_claim(text, match)
            ):
                continue
            errors.append(f"forbidden philosophy admission contract claim: {label}")
            break
    return errors


def _without_markdown_sections(text: str, headings: set[str]) -> str:
    """Remove named level-two markdown sections before claim scanning."""
    matches = list(MARKDOWN_SECTION_RE.finditer(text))
    if not matches:
        return text

    kept_parts: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        section_start = match.start()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        kept_parts.append(text[cursor:section_start])
        heading_line_end = text.find("\n", match.end())
        if heading_line_end == -1:
            heading_line_end = section_end
        heading = text[match.end() : heading_line_end].strip().lower()
        if heading not in headings:
            kept_parts.append(text[section_start:section_end])
        cursor = section_end
    kept_parts.append(text[cursor:])
    return "".join(kept_parts)


def _markdown_section(text: str, heading: str) -> str:
    heading_pattern = re.compile(rf"(?im)^##\s+{re.escape(heading)}\s*$")
    match = heading_pattern.search(text)
    if match is None:
        return ""
    section = text[match.end() :]
    next_heading = re.search(r"(?m)^##\s+", section)
    if next_heading is not None:
        section = section[: next_heading.start()]
    return section


def _philosophy_admission_assertion_text(text: str) -> str:
    """Keep claim scanning on assertive prose, not forbidden examples or JSON."""
    text_without_json = _without_philosophy_admission_machine_state_json(text)
    return _without_markdown_sections(text_without_json, headings={"forbidden claims"})


def _without_philosophy_admission_machine_state_json(text: str) -> str:
    """Remove only the fenced Philosophy machine-state JSON, not nearby prose."""
    heading = re.search(r"(?im)^##\s+Machine-Readable State\s*$", text)
    if heading is None:
        return text
    section_start = heading.end()
    section = text[section_start:]
    next_heading = re.search(r"(?m)^##\s+", section)
    section_end = section_start + (
        next_heading.start() if next_heading is not None else len(section)
    )
    matches = list(MACHINE_JSON_RE.finditer(text[section_start:section_end]))
    if len(matches) != 1:
        return text
    match = matches[0]
    payload_start = section_start + match.start()
    payload_end = section_start + match.end()
    return text[:payload_start] + "\n" + text[payload_end:]


def _validate_rollout_order(
    normalized: str,
    *,
    missing_prefix: str,
    out_of_order_prefix: str,
    order: tuple[str, ...] | None = None,
) -> list[str]:
    errors: list[str] = []
    positions: dict[str, int] = {}
    phrases = order if order is not None else ROLLOUT_ORDER

    for phrase in phrases:
        normalized_phrase = _normalize_text(phrase)
        index = normalized.find(normalized_phrase)
        if index == -1:
            errors.append(f"{missing_prefix}: {phrase}")
            continue
        positions[phrase] = index

    previous_index = -1
    for phrase in phrases:
        current_index = positions.get(phrase)
        if current_index is None:
            continue
        if current_index <= previous_index:
            errors.append(f"{out_of_order_prefix}: {phrase}")
        previous_index = current_index

    return errors


def validate_semantic_cache_gate(text: str) -> list[str]:
    """Return stable validation errors for unsafe semantic-cache gate docs."""
    errors: list[str] = []
    markers, duplicates = _extract_markers(text)

    for key in duplicates:
        errors.append(f"duplicate marker: {key}")

    for key, expected in REQUIRED_MARKERS.items():
        actual = markers.get(key)
        if actual is None:
            errors.append(f"missing marker: {key}")
        elif actual != expected:
            errors.append(f"invalid marker {key}: expected {expected}, got {actual}")

    normalized = _normalize_text(text)
    for phrase in REQUIRED_PHRASES:
        if _normalize_text(phrase) not in normalized:
            errors.append(f"missing required phrase: {phrase}")

    errors.extend(
        _validate_rollout_order(
            normalized,
            missing_prefix="missing rollout order item",
            out_of_order_prefix="rollout order item out of order",
        )
    )

    errors.extend(_forbidden_claim_errors(text))

    return errors


def validate_semantic_cache_rollout_contract(text: str) -> list[str]:
    """Return stable validation errors for unsafe semantic-cache rollout contracts."""
    errors: list[str] = []
    normalized = _normalize_text(text)

    for label, pattern in CONTRACT_REQUIRED_ANCHORS:
        if not pattern.search(normalized):
            errors.append(f"rollout contract missing anchor: {label}")

    errors.extend(
        _validate_rollout_order(
            normalized,
            missing_prefix="rollout contract missing phase",
            out_of_order_prefix="rollout contract phase out of order",
        )
    )

    errors.extend(_forbidden_claim_errors(text))

    return errors


def validate_exact_fuzzy_scaffold_contract(text: str) -> list[str]:
    """Return stable validation errors for unsafe SC-G2 exact/fuzzy contracts."""
    errors: list[str] = []
    normalized = _normalize_text(text)

    for label, pattern in SCAFFOLD_REQUIRED_ANCHORS:
        if not pattern.search(normalized):
            errors.append(f"exact/fuzzy scaffold contract missing anchor: {label}")

    positions = {
        "SC-G2": normalized.find("sc-g2 is deterministic exact/fuzzy only"),
        "SC-G3": normalized.find("sc-g3 observability and false-hit harness is still required"),
        "SC-G4": normalized.find("sc-g4 bounded /insight semantic-cache experiment"),
    }
    for phase, index in positions.items():
        if index == -1:
            errors.append(f"exact/fuzzy scaffold contract missing phase: {phase}")
    expected_phase_order = ("SC-G2", "SC-G3", "SC-G4")
    previous_position = -1
    for phase in expected_phase_order:
        current_position = positions[phase]
        if current_position == -1:
            continue
        if current_position <= previous_position:
            errors.append(f"exact/fuzzy scaffold phase out of order: {phase}")
        previous_position = current_position
    errors.extend(_forbidden_claim_errors(text))
    errors.extend(
        f"forbidden exact/fuzzy scaffold claim: {label}"
        for label, pattern in SCAFFOLD_FORBIDDEN_PATTERNS
        if pattern.search(normalized)
    )

    return errors


def validate_semantic_cache_observability_contract(text: str) -> list[str]:
    """Return stable validation errors for unsafe SC-G3 observability contracts."""
    errors: list[str] = []
    normalized = _normalize_text(text)

    for label, pattern in OBSERVABILITY_REQUIRED_ANCHORS:
        if not pattern.search(normalized):
            errors.append(f"observability contract missing anchor: {label}")

    errors.extend(
        _validate_rollout_order(
            normalized,
            missing_prefix="observability contract missing phase",
            out_of_order_prefix="observability contract phase out of order",
        )
    )
    errors.extend(_forbidden_claim_errors(text))
    errors.extend(
        f"forbidden observability contract claim: {label}"
        for label, pattern in OBSERVABILITY_FORBIDDEN_PATTERNS
        if pattern.search(normalized)
    )

    return errors


def validate_semantic_cache_bounded_insight_experiment_contract(text: str) -> list[str]:
    """Return stable validation errors for unsafe SC-G4 bounded experiment contracts."""
    errors: list[str] = []
    normalized = _normalize_text(text)

    for label, pattern in BOUNDED_INSIGHT_REQUIRED_ANCHORS:
        if not pattern.search(normalized):
            errors.append(f"bounded insight contract missing anchor: {label}")

    rollout_section_index = normalized.find("required rollout order remains:")
    rollout_section = (
        normalized[rollout_section_index:] if rollout_section_index != -1 else normalized
    )
    errors.extend(
        _validate_rollout_order(
            rollout_section,
            missing_prefix="bounded insight contract missing phase",
            out_of_order_prefix="bounded insight contract phase out of order",
        )
    )
    errors.extend(_forbidden_claim_errors(text))
    errors.extend(
        f"forbidden bounded insight contract claim: {label}"
        for label, pattern in BOUNDED_INSIGHT_FORBIDDEN_PATTERNS
        if pattern.search(normalized)
    )

    return errors


def validate_semantic_cache_backend_selection_contract(text: str) -> list[str]:
    """Return stable validation errors for unsafe SC-G5 backend selection contracts."""
    errors: list[str] = []
    normalized = _normalize_text(text)

    for label, pattern in BACKEND_SELECTION_REQUIRED_ANCHORS:
        if not pattern.search(normalized):
            errors.append(f"backend selection contract missing anchor: {label}")

    rollout_section_index = normalized.find("required rollout order remains:")
    rollout_section = (
        normalized[rollout_section_index:] if rollout_section_index != -1 else normalized
    )
    errors.extend(
        _validate_rollout_order(
            rollout_section,
            missing_prefix="backend selection contract missing phase",
            out_of_order_prefix="backend selection contract phase out of order",
        )
    )
    errors.extend(_forbidden_claim_errors(text))
    errors.extend(
        f"forbidden backend selection contract claim: {label}"
        for label, pattern in BACKEND_SELECTION_FORBIDDEN_PATTERNS
        if pattern.search(normalized)
    )
    errors.extend(_validate_backend_selection_machine_state(text))

    return errors


def _validate_backend_selection_machine_state(text: str) -> list[str]:
    payload_text, state_errors = _backend_selection_machine_state_json(text)
    if state_errors:
        return state_errors
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        return [f"backend selection contract invalid JSON state: {exc.msg}"]
    if not isinstance(payload, dict):
        return ["backend selection contract JSON state must be an object"]

    errors: list[str] = []
    expected_keys = {
        "acceptance_criteria",
        "allowed_backend_labels",
        "blocked_payload_fields",
        "blocked_runtime_dependencies",
        "blocked_truth_sources",
        "candidate_backend_labels",
        "default_activation",
        "forbidden_claims",
        "gate_status",
        "implementation_allowed",
        "label_only_backends",
        "required_evidence",
        "required_rollback_proof",
        "rollout_phase",
        "runtime_allowed",
        "selection_mode",
    }
    actual_keys = set(payload)
    for key in sorted(expected_keys - actual_keys):
        errors.append(f"backend selection contract JSON missing required key: {key}")
    for key in sorted(actual_keys - expected_keys):
        errors.append(f"backend selection contract JSON unexpected key: {key}")
    expected_values = {
        "gate_status": "closed",
        "runtime_allowed": False,
        "implementation_allowed": False,
        "rollout_phase": "SC-G5",
        "selection_mode": "recommendation_only",
        "default_activation": "none",
        "label_only_backends": True,
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            errors.append(
                f"backend selection contract JSON {key}: expected {expected!r}, "
                f"got {payload.get(key)!r}"
            )
    expected_labels = ["in_memory_label", "redis_label", "gptcache_label"]
    for key in ("candidate_backend_labels", "allowed_backend_labels"):
        if payload.get(key) != expected_labels:
            errors.append(f"backend selection contract JSON {key}: expected label-only list")
    required_lists = {
        "acceptance_criteria": (
            "gate remains closed",
            "runtime_allowed remains false",
            "implementation_allowed remains false",
            "backend candidates are labels only",
            "Redis/GPTCache are not approved for rollout",
            "no runtime imports or backend clients",
            "safety hard-gates ranking",
            "rollback proof is required",
        ),
        "blocked_payload_fields": (
            "raw prompts",
            "raw queries",
            "normalized queries",
            "raw model responses",
            "raw answers",
            "provider payloads",
            "secrets",
            "credentials",
            "authorization headers",
            "cookies",
            "API keys",
            "private keys",
            "local paths",
            "HealthKit-derived sensitive payloads",
            "diagnosis-like health data",
            "highly personalized coaching state",
            "user-account truth",
            "billing/auth/entitlement truth",
            "legal/compliance output truth",
        ),
        "blocked_runtime_dependencies": (
            "FastAPI",
            "OpenAPI",
            "DB writes",
            "migrations",
            "provider calls",
            "Redis imports or clients",
            "GPTCache imports or clients",
            "environment reads",
            "network calls",
            "file writes",
            "cache backend adapters",
            "connection strings",
            "availability probes",
            "vector search",
            "embeddings",
            "semantic similarity backends",
            "dependency additions",
        ),
        "blocked_truth_sources": (
            "advisory wiki",
            "workforce memory",
            "local support plane",
            "GraphRAG",
            "knowledge graph runtime output",
            "plugin/control-plane output",
            "second source of truth",
        ),
        "required_evidence": (
            "SC-G2 lineage evidence",
            "SC-G3 false-hit evidence",
            "SC-G4 bounded insight decision evidence",
            "source fingerprints",
            "eval event IDs",
            "admission decision ID",
            "promotion IDs",
            "replay entry IDs",
            "evidence fingerprints",
            "current-head CI governance proof",
            "human approval record",
        ),
        "required_rollback_proof": (
            "kill switch proof",
            "request bypass proof",
            "no-cache fallback proof",
            "purge/invalidation proof",
            "disabled-state test IDs",
            "stop-rule replay IDs",
            "rollback runbook ID",
            "rollback blast radius basis points",
        ),
        "forbidden_claims": (
            "active semantic-cache claim",
            "enabled semantic-cache claim",
            "open semantic-cache claim",
            "approved Redis rollout claim",
            "approved GPTCache rollout claim",
            "serving backend selection claim",
            "production readiness claim",
            "raw prompt caching claim",
            "raw response caching claim",
        ),
    }
    for key, required_items in required_lists.items():
        actual = payload.get(key)
        if not isinstance(actual, list):
            errors.append(f"backend selection contract JSON {key}: expected list")
            continue
        missing = [item for item in required_items if item not in actual]
        for item in missing:
            errors.append(f"backend selection contract JSON {key}: missing {item}")
    return errors


def _backend_selection_machine_state_json(text: str) -> tuple[str, list[str]]:
    heading = re.search(r"(?im)^##\s+Machine-Readable State\s*$", text)
    if heading is None:
        return "", ["backend selection contract missing Machine-Readable State heading"]
    section = text[heading.end() :]
    next_heading = re.search(r"(?m)^##\s+", section)
    if next_heading is not None:
        section = section[: next_heading.start()]
    matches = list(MACHINE_JSON_RE.finditer(section))
    if not matches:
        return "", ["backend selection contract missing machine-readable JSON state"]
    if len(matches) > 1:
        return "", ["backend selection contract has multiple machine-readable JSON states"]
    return matches[0].group("payload"), []


def validate_semantic_cache_backend_selection_schema(
    *,
    schema_text: str,
    contract_text: str,
) -> list[str]:
    """Validate the SC-G5 JSON schema against the contract machine state."""

    errors: list[str] = []
    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError as exc:
        return [f"backend selection schema invalid JSON: {exc.msg}"]
    if not isinstance(schema, dict):
        return ["backend selection schema must be an object"]
    if schema.get("type") != "object":
        errors.append("backend selection schema root type must be object")

    payload_text, state_errors = _backend_selection_machine_state_json(contract_text)
    if state_errors:
        return state_errors
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        return [f"backend selection contract invalid JSON state: {exc.msg}"]
    if not isinstance(payload, dict):
        return ["backend selection contract JSON state must be an object"]

    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict):
        errors.append("backend selection schema properties must be an object")
        properties = {}
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("backend selection schema required must be a string list")
        required = []
    if schema.get("additionalProperties") is not False:
        errors.append("backend selection schema must set additionalProperties false")

    required_set = set(required)
    payload_keys = set(payload)
    property_keys = set(properties)
    for key in sorted(required_set - payload_keys):
        errors.append(f"backend selection schema required key missing from contract JSON: {key}")
    for key in sorted(payload_keys - required_set):
        errors.append(f"backend selection contract JSON key missing from schema required: {key}")
    for key in sorted(payload_keys - property_keys):
        errors.append(f"backend selection contract JSON key missing from schema properties: {key}")
    for key in sorted(required_set - property_keys):
        errors.append(f"backend selection schema required key missing from properties: {key}")
    for key in sorted(property_keys - payload_keys):
        errors.append(f"backend selection schema property missing from contract JSON: {key}")

    closed_state_const_keys = {
        "default_activation",
        "gate_status",
        "implementation_allowed",
        "label_only_backends",
        "rollout_phase",
        "runtime_allowed",
        "selection_mode",
    }

    for key, spec in properties.items():
        if not isinstance(spec, dict) or key not in payload:
            continue
        if key in closed_state_const_keys and "const" not in spec:
            errors.append(f"backend selection schema const missing for {key}")
        if "const" in spec and payload[key] != spec["const"]:
            errors.append(
                f"backend selection schema const mismatch for {key}: "
                f"expected {spec['const']!r}, got {payload[key]!r}"
            )
        items = spec.get("items")
        if isinstance(payload[key], list):
            if spec.get("type") != "array":
                errors.append(f"backend selection schema array type missing for {key}")
            if not isinstance(spec.get("minItems"), int) or spec["minItems"] < 1:
                errors.append(f"backend selection schema minItems missing for {key}")
            if spec.get("uniqueItems") is not True:
                errors.append(f"backend selection schema uniqueItems missing for {key}")
            if not isinstance(items, dict) or items.get("type") != "string":
                errors.append(f"backend selection schema string items missing for {key}")
        if isinstance(items, dict) and "enum" in items:
            enum = items["enum"]
            actual = payload[key]
            if key in {"candidate_backend_labels", "allowed_backend_labels"}:
                if not isinstance(enum, list) or not all(isinstance(item, str) for item in enum):
                    errors.append(f"backend selection schema enum must be a string list for {key}")
                elif isinstance(actual, list) and set(enum) != set(actual):
                    errors.append(f"backend selection schema enum set mismatch for {key}")
            if isinstance(enum, list) and isinstance(actual, list):
                invalid = [item for item in actual if item not in enum]
                for item in invalid:
                    errors.append(f"backend selection schema enum mismatch for {key}: {item!r}")
        elif key in {"candidate_backend_labels", "allowed_backend_labels"}:
            errors.append(f"backend selection schema enum missing for {key}")

    return errors


def _philosophy_admission_machine_state_json(text: str) -> tuple[str, list[str]]:
    headings = list(re.finditer(r"(?im)^##\s+Machine-Readable State\s*$", text))
    if not headings:
        return "", ["philosophy admission contract missing Machine-Readable State heading"]
    if len(headings) > 1:
        return "", ["philosophy admission contract Machine-Readable State section must be unique"]
    heading = headings[0]
    section = text[heading.end() :]
    next_heading = re.search(r"(?m)^##\s+", section)
    if next_heading is not None:
        section = section[: next_heading.start()]
    matches = list(MACHINE_JSON_RE.finditer(section))
    if not matches:
        return "", ["philosophy admission contract missing machine-readable JSON state"]
    if len(matches) > 1:
        return "", ["philosophy admission contract has multiple machine-readable JSON states"]
    return matches[0].group("payload"), []


def _load_philosophy_admission_machine_state(payload_text: str) -> tuple[object, list[str]]:
    duplicate_keys: list[str] = []

    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        parsed: dict[str, object] = {}
        for key, value in pairs:
            if key in parsed and key not in duplicate_keys:
                duplicate_keys.append(key)
            parsed[key] = value
        return parsed

    try:
        payload = json.loads(payload_text, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        return None, [f"philosophy admission contract invalid JSON state: {exc.msg}"]
    if duplicate_keys:
        return payload, [
            f"philosophy admission contract JSON duplicate key: {key}"
            for key in sorted(duplicate_keys)
        ]
    return payload, []


def validate_philosophy_semantic_cache_admission_contract(text: str) -> list[str]:
    """Return stable validation errors for Philosophy PR-1 admission contracts."""
    errors: list[str] = []
    assertion_text = _philosophy_admission_assertion_text(text)
    normalized = _normalize_text(assertion_text)

    forbidden_claims_section_text = _markdown_section(text, "Forbidden Claims")
    forbidden_claims_sections = re.findall(r"(?im)^##\s+Forbidden Claims\s*$", text)
    if len(forbidden_claims_sections) != 1:
        errors.append("philosophy admission contract Forbidden Claims section must be unique")
    forbidden_claims_section = _normalize_text(forbidden_claims_section_text)
    if not PHILOSOPHY_FORBIDDEN_CLAIMS_SECTION_POLARITY_RE.search(forbidden_claims_section):
        errors.append(
            "philosophy admission contract Forbidden Claims section must retain "
            "negative must-not-claim polarity"
        )
    for line in forbidden_claims_section_text.splitlines():
        stripped_line, had_bullet = _strip_forbidden_claims_line_prefixes(line)
        if not stripped_line:
            continue
        normalized_line = _normalize_text(stripped_line)
        if PHILOSOPHY_FORBIDDEN_CLAIMS_SECTION_PERMISSIVE_POLARITY_RE.search(normalized_line):
            errors.append(
                "philosophy admission contract Forbidden Claims section must retain "
                "negative must-not-claim polarity"
            )
            break
        if had_bullet and _has_prefixed_forbidden_claim_assertion(normalized_line):
            errors.append(
                "philosophy admission contract Forbidden Claims section must retain "
                "negative must-not-claim polarity"
            )
            break
        if had_bullet:
            continue
        line_errors = _forbidden_claim_errors(stripped_line)
        line_errors.extend(_philosophy_admission_forbidden_claim_errors(normalized_line))
        if line_errors:
            errors.append(
                "philosophy admission contract Forbidden Claims section must retain "
                "negative must-not-claim polarity"
            )
            break

    for label, pattern in PHILOSOPHY_ADMISSION_REQUIRED_ANCHORS:
        if not pattern.search(normalized):
            errors.append(f"philosophy admission contract missing anchor: {label}")

    runtime_section = _normalize_text(_markdown_section(text, "Runtime-Only Default"))
    for label, pattern in PHILOSOPHY_RUNTIME_ONLY_SECTION_REQUIRED_ANCHORS:
        if not pattern.search(runtime_section):
            errors.append(f"philosophy admission contract runtime section missing anchor: {label}")

    rollout_section_index = normalized.find("required rollout order remains:")
    rollout_section = (
        normalized[rollout_section_index:] if rollout_section_index != -1 else normalized
    )
    errors.extend(
        _validate_rollout_order(
            rollout_section,
            order=PHILOSOPHY_ADMISSION_ROLLOUT_ORDER,
            missing_prefix="philosophy admission contract missing phase",
            out_of_order_prefix="philosophy admission contract phase out of order",
        )
    )
    errors.extend(_forbidden_claim_errors(assertion_text))
    errors.extend(_philosophy_admission_forbidden_claim_errors(normalized))
    errors.extend(_validate_philosophy_admission_machine_state(text))

    return errors


def _strip_forbidden_claims_line_prefixes(line: str) -> tuple[str, bool]:
    """Normalize nested Markdown prefixes while preserving bullet-example status."""
    stripped = line.strip()
    had_bullet = False
    while stripped:
        original = stripped
        blockquote_match = MARKDOWN_BLOCKQUOTE_PREFIX_RE.match(stripped)
        if blockquote_match is not None:
            stripped = stripped[blockquote_match.end() :].strip()
        heading_match = MARKDOWN_HEADING_PREFIX_RE.match(stripped)
        if heading_match is not None:
            stripped = stripped[heading_match.end() :].strip()
        bullet_match = MARKDOWN_BULLET_PREFIX_RE.match(stripped)
        if bullet_match is not None:
            had_bullet = True
            stripped = stripped[bullet_match.end() :].strip()
        task_match = MARKDOWN_TASK_PREFIX_RE.match(stripped)
        if task_match is not None:
            stripped = stripped[task_match.end() :].strip()
        if stripped == original:
            break
    return stripped, had_bullet


def validate_philosophy_semantic_cache_admission_downstream_text(text: str) -> list[str]:
    """Reject Philosophy PR-1 forbidden claims in downstream docs without contract anchors."""
    assertion_text = _philosophy_downstream_assertion_text(text)
    assertion_normalized = _normalize_text(assertion_text)
    errors = _forbidden_claim_errors(assertion_text)
    errors.extend(_philosophy_admission_forbidden_claim_errors(assertion_normalized))
    return errors


def _has_prefixed_forbidden_claim_assertion(normalized_line: str) -> bool:
    """Return true when a bullet wraps a forbidden claim in assertive prose."""
    for _label, pattern in (*FORBIDDEN_CLAIM_PATTERNS, *PHILOSOPHY_ADMISSION_FORBIDDEN_PATTERNS):
        for match in pattern.finditer(normalized_line):
            if match.start() == 0:
                continue
            prefix = normalized_line[: match.start()].strip()
            if (
                not prefix
                or prefix == "any"
                or PHILOSOPHY_FORBIDDEN_CLAIMS_SAFE_BULLET_PREFIX_RE.search(prefix)
            ):
                continue
            return True
    return False


def _has_same_line_forbidden_claim_tail(normalized_tail: str) -> bool:
    """Return true when a negative lead-in hides a second assertive forbidden claim."""
    for _label, pattern in (*FORBIDDEN_CLAIM_PATTERNS, *PHILOSOPHY_ADMISSION_FORBIDDEN_PATTERNS):
        first_match_seen = False
        for match in pattern.finditer(normalized_tail):
            if match.start() == 0 and not first_match_seen:
                first_match_seen = True
                continue
            if match.start() == 0:
                continue
            prefix = normalized_tail[: match.start()].strip()
            if not prefix or PHILOSOPHY_FORBIDDEN_CLAIMS_SAFE_BULLET_PREFIX_RE.search(prefix):
                continue
            return True
    return False


def _philosophy_downstream_assertion_text(text: str) -> str:
    """Keep downstream scans broad while allowing explicitly negative examples."""
    kept_lines: list[str] = []
    in_forbidden_claims_section = False
    negative_example_block = False
    negative_example_fence = False
    for line in text.splitlines():
        heading_match = re.match(r"^(?P<marks>#{2,6})\s+(?P<heading>.+?)\s*$", line.strip())
        if heading_match is not None:
            level = len(heading_match.group("marks"))
            heading = heading_match.group("heading").strip().lower()
            if heading == "forbidden claims":
                in_forbidden_claims_section = True
                negative_example_block = False
                negative_example_fence = False
            elif in_forbidden_claims_section and level > 2:
                normalized_heading = _normalize_text(heading)
                if not PHILOSOPHY_FORBIDDEN_CLAIMS_SAFE_BULLET_PREFIX_RE.search(normalized_heading):
                    negative_example_block = False
                    negative_example_fence = False
            else:
                in_forbidden_claims_section = False
                negative_example_block = False
                negative_example_fence = False
            kept_lines.append(line)
            continue
        if not in_forbidden_claims_section:
            kept_lines.append(line)
            continue

        stripped = line.strip()
        if negative_example_block and negative_example_fence:
            if stripped.startswith(("```", "~~~")):
                negative_example_fence = False
            continue
        if negative_example_block and stripped.startswith(("```", "~~~")):
            negative_example_fence = True
            continue

        stripped_line, had_bullet = _strip_forbidden_claims_line_prefixes(line)
        normalized_line = _normalize_text(stripped_line)
        if re.match(r"^#{3,6}\s+", line.strip()):
            heading_text = re.sub(r"^#{3,6}\s+", "", line.strip())
            normalized_heading = _normalize_text(heading_text)
            if not PHILOSOPHY_FORBIDDEN_CLAIMS_SAFE_BULLET_PREFIX_RE.search(normalized_heading):
                negative_example_block = False
            kept_lines.append(line)
            continue
        negative_polarity_match = PHILOSOPHY_FORBIDDEN_CLAIMS_SECTION_POLARITY_RE.search(
            normalized_line
        )
        if negative_polarity_match is not None:
            tail = normalized_line[negative_polarity_match.end() :].strip()
            if PHILOSOPHY_FORBIDDEN_CLAIMS_SECTION_PERMISSIVE_POLARITY_RE.search(
                tail
            ) or _has_same_line_forbidden_claim_tail(tail):
                kept_lines.append(tail)
                continue
            negative_example_block = True
            continue
        if negative_example_block and normalized_line and not had_bullet:
            if not PHILOSOPHY_FORBIDDEN_CLAIMS_SAFE_BULLET_PREFIX_RE.search(normalized_line):
                negative_example_block = False
        if (
            negative_example_block
            and had_bullet
            and not PHILOSOPHY_FORBIDDEN_CLAIMS_SECTION_PERMISSIVE_POLARITY_RE.search(
                normalized_line
            )
            and not _has_prefixed_forbidden_claim_assertion(normalized_line)
        ):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def _load_philosophy_admission_schema_json(schema_text: str) -> tuple[object, list[str]]:
    duplicate_keys: list[str] = []

    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        parsed: dict[str, object] = {}
        for key, value in pairs:
            if key in parsed and key not in duplicate_keys:
                duplicate_keys.append(key)
            parsed[key] = value
        return parsed

    try:
        schema = json.loads(schema_text, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        return None, [f"philosophy admission schema invalid JSON: {exc.msg}"]
    if duplicate_keys:
        return schema, [
            f"philosophy admission schema duplicate key: {key}" for key in sorted(duplicate_keys)
        ]
    return schema, []


def _validate_philosophy_admission_machine_state(text: str) -> list[str]:
    payload_text, state_errors = _philosophy_admission_machine_state_json(text)
    if state_errors:
        return state_errors
    payload, parse_errors = _load_philosophy_admission_machine_state(payload_text)
    if parse_errors:
        return parse_errors
    if not isinstance(payload, dict):
        return ["philosophy admission contract JSON state must be an object"]

    errors: list[str] = []
    expected_keys = {
        "admission_classes",
        "blocked_surfaces",
        "default_admission_while_gate_closed",
        "does_not_duplicate_sc_g5_backend_selection",
        "forbidden_claims",
        "gate_status",
        "implementation_allowed",
        "references",
        "rollout_phase",
        "runtime_allowed",
        "sc_g5_merge_commit",
        "runtime_only_surfaces",
        "verification_bundle_required_surfaces",
        "future_cache_candidate_deferred_surfaces",
    }
    actual_keys = set(payload)
    for key in sorted(expected_keys - actual_keys):
        errors.append(f"philosophy admission contract JSON missing required key: {key}")
    for key in sorted(actual_keys - expected_keys):
        errors.append(f"philosophy admission contract JSON unexpected key: {key}")

    expected_values = {
        "gate_status": "closed",
        "runtime_allowed": False,
        "implementation_allowed": False,
        "rollout_phase": "PHILOSOPHY-PR1",
        "default_admission_while_gate_closed": "runtime_only",
        "does_not_duplicate_sc_g5_backend_selection": True,
        "sc_g5_merge_commit": PHILOSOPHY_SC_G5_MERGE_SHA,
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            errors.append(
                f"philosophy admission contract JSON {key}: expected {expected!r}, "
                f"got {payload.get(key)!r}"
            )

    admission_classes = payload.get("admission_classes")
    if not isinstance(admission_classes, list) or not all(
        isinstance(item, str) for item in admission_classes
    ):
        errors.append("philosophy admission contract JSON admission_classes must be a string list")
    elif len(admission_classes) != len(set(admission_classes)):
        errors.append("philosophy admission contract JSON admission_classes contains duplicates")
    elif set(admission_classes) != PHILOSOPHY_ADMISSION_CLASSES:
        errors.append("philosophy admission contract JSON admission_classes set mismatch")

    references = payload.get("references")
    if "references" in payload and (
        not isinstance(references, list) or not all(isinstance(item, str) for item in references)
    ):
        errors.append("philosophy admission contract JSON references must be a string list")
    elif isinstance(references, list) and len(references) != len(set(references)):
        errors.append("philosophy admission contract JSON references contains duplicates")
    elif isinstance(references, list):
        missing = [item for item in PHILOSOPHY_REFERENCES if item not in references]
        for item in missing:
            errors.append(f"philosophy admission contract JSON references missing {item}")
        unexpected = [item for item in references if item not in PHILOSOPHY_REFERENCES]
        for item in unexpected:
            errors.append(f"philosophy admission contract JSON references unexpected {item}")

    required_lists = {
        "blocked_surfaces": PHILOSOPHY_BLOCKED_SURFACES,
        "forbidden_claims": PHILOSOPHY_FORBIDDEN_CLAIM_CLASSES,
        "runtime_only_surfaces": PHILOSOPHY_RUNTIME_ONLY_SURFACES,
        "verification_bundle_required_surfaces": PHILOSOPHY_VERIFICATION_BUNDLE_REQUIRED_SURFACES,
    }
    for key, required_items in required_lists.items():
        actual = payload.get(key)
        if not isinstance(actual, list) or not all(isinstance(item, str) for item in actual):
            errors.append(f"philosophy admission contract JSON {key}: expected list")
            continue
        if len(actual) != len(set(actual)):
            errors.append(f"philosophy admission contract JSON {key}: contains duplicates")
        missing = [item for item in required_items if item not in actual]
        for item in missing:
            errors.append(f"philosophy admission contract JSON {key}: missing {item}")
        unexpected = [item for item in actual if item not in required_items]
        for item in unexpected:
            errors.append(f"philosophy admission contract JSON {key}: unexpected {item}")

    forbidden_claims = payload.get("forbidden_claims")
    if isinstance(forbidden_claims, list) and all(
        isinstance(item, str) for item in forbidden_claims
    ):
        active_pattern_labels = {
            label for label, _pattern in PHILOSOPHY_ADMISSION_FORBIDDEN_PATTERNS
        }
        for claim_class in forbidden_claims:
            for pattern_label in PHILOSOPHY_FORBIDDEN_CLAIM_PATTERN_LABELS.get(claim_class, ()):
                if pattern_label not in active_pattern_labels:
                    errors.append(
                        "philosophy admission contract JSON forbidden_claims "
                        f"{claim_class}: missing active detector {pattern_label}"
                    )

    deferred_surfaces = payload.get("future_cache_candidate_deferred_surfaces")
    if not isinstance(deferred_surfaces, list) or not all(
        isinstance(item, str) for item in deferred_surfaces
    ):
        errors.append(
            "philosophy admission contract JSON future_cache_candidate_deferred_surfaces: "
            "expected list"
        )
    elif deferred_surfaces != list(PHILOSOPHY_FUTURE_CACHE_CANDIDATE_DEFERRED_SURFACES):
        errors.append(
            "philosophy admission contract JSON future_cache_candidate_deferred_surfaces: "
            "must stay empty while gate closed"
        )

    return errors


def validate_philosophy_semantic_cache_admission_schema(
    *,
    schema_text: str,
    contract_text: str,
) -> list[str]:
    """Validate the Philosophy PR-1 JSON schema against the contract machine state."""
    errors: list[str] = []
    schema, parse_errors = _load_philosophy_admission_schema_json(schema_text)
    if parse_errors:
        return parse_errors
    if not isinstance(schema, dict):
        return ["philosophy admission schema must be an object"]
    if schema.get("type") != "object":
        errors.append("philosophy admission schema root type must be object")

    payload_text, state_errors = _philosophy_admission_machine_state_json(contract_text)
    if state_errors:
        return state_errors
    payload, parse_errors = _load_philosophy_admission_machine_state(payload_text)
    if parse_errors:
        return parse_errors
    if not isinstance(payload, dict):
        return ["philosophy admission contract JSON state must be an object"]

    root_schema_keys = {
        "$comment",
        "$schema",
        "additionalProperties",
        "default",
        "deprecated",
        "description",
        "examples",
        "properties",
        "readOnly",
        "required",
        "title",
        "type",
        "writeOnly",
    }
    for constraint in sorted(set(schema) - root_schema_keys):
        errors.append(f"philosophy admission schema unsupported root constraint: {constraint}")

    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict):
        errors.append("philosophy admission schema properties must be an object")
        properties = {}
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("philosophy admission schema required must be a string list")
        required = []
    elif len(required) != len(set(required)):
        errors.append("philosophy admission schema required contains duplicates")

    if schema.get("additionalProperties") is not False:
        errors.append("philosophy admission schema must set additionalProperties false")

    required_set = set(required)
    payload_keys = set(payload)
    property_keys = set(properties)
    for key in sorted(required_set - payload_keys):
        errors.append(f"philosophy admission schema required key missing from contract JSON: {key}")
    for key in sorted(payload_keys - required_set):
        errors.append(f"philosophy admission contract JSON key missing from schema required: {key}")
    for key in sorted(payload_keys - property_keys):
        errors.append(
            f"philosophy admission contract JSON key missing from schema properties: {key}"
        )
    for key in sorted(required_set - property_keys):
        errors.append(f"philosophy admission schema required key missing from properties: {key}")
    for key in sorted(property_keys - payload_keys):
        errors.append(f"philosophy admission schema property missing from contract JSON: {key}")

    const_keys = {
        "default_admission_while_gate_closed",
        "does_not_duplicate_sc_g5_backend_selection",
        "gate_status",
        "implementation_allowed",
        "rollout_phase",
        "runtime_allowed",
        "sc_g5_merge_commit",
    }
    schema_annotation_keys = {
        "$comment",
        "default",
        "deprecated",
        "description",
        "examples",
        "readOnly",
        "title",
        "writeOnly",
    }
    scalar_schema_keys = schema_annotation_keys | {"const", "type"}
    array_schema_keys = scalar_schema_keys | {
        "items",
        "maxItems",
        "minItems",
        "uniqueItems",
    }
    array_item_schema_keys = schema_annotation_keys | {"enum", "type"}
    for key, spec in properties.items():
        if key not in payload:
            continue
        if not isinstance(spec, dict):
            errors.append(f"philosophy admission schema property must be an object for {key}")
            continue
        if key in const_keys and "const" not in spec:
            errors.append(f"philosophy admission schema const missing for {key}")
        if "const" in spec and payload[key] != spec["const"]:
            errors.append(
                f"philosophy admission schema const mismatch for {key}: "
                f"expected {spec['const']!r}, got {payload[key]!r}"
            )
        if isinstance(payload[key], bool) and spec.get("type") != "boolean":
            errors.append(f"philosophy admission schema boolean type mismatch for {key}")
        elif isinstance(payload[key], str) and spec.get("type") != "string":
            errors.append(f"philosophy admission schema string type mismatch for {key}")
        if key in const_keys and isinstance(payload[key], (bool, str)):
            unsupported_scalar_constraints = sorted(set(spec) - scalar_schema_keys)
            for constraint in unsupported_scalar_constraints:
                errors.append(
                    "philosophy admission schema unsupported scalar constraint for "
                    f"{key}: {constraint}"
                )
        items = spec.get("items")
        if isinstance(payload[key], list):
            unsupported_array_constraints = sorted(set(spec) - array_schema_keys)
            for constraint in unsupported_array_constraints:
                errors.append(
                    "philosophy admission schema unsupported array constraint for "
                    f"{key}: {constraint}"
                )
            if spec.get("type") != "array":
                errors.append(f"philosophy admission schema array type missing for {key}")
            min_items = spec.get("minItems")
            max_items = spec.get("maxItems")
            enum_backed = isinstance(items, dict) and "enum" in items
            if payload[key] and type(min_items) is not int:
                errors.append(f"philosophy admission schema minItems missing for {key}")
            elif payload[key] and enum_backed and min_items != len(payload[key]):
                errors.append(
                    f"philosophy admission schema minItems mismatch for {key}: "
                    f"expected {len(payload[key])}"
                )
            if payload[key] and enum_backed and max_items != len(payload[key]):
                errors.append(
                    f"philosophy admission schema maxItems mismatch for {key}: "
                    f"expected {len(payload[key])}"
                )
            if key == "future_cache_candidate_deferred_surfaces" and (
                min_items is not None and (type(min_items) is not int or min_items != 0)
            ):
                errors.append(
                    "philosophy admission schema minItems mismatch for "
                    "future_cache_candidate_deferred_surfaces: expected 0"
                )
            if key == "future_cache_candidate_deferred_surfaces" and (
                type(max_items) is not int or max_items != 0
            ):
                errors.append(
                    "philosophy admission schema maxItems mismatch for "
                    "future_cache_candidate_deferred_surfaces: expected 0"
                )
            if spec.get("uniqueItems") is not True:
                errors.append(f"philosophy admission schema uniqueItems missing for {key}")
            if not isinstance(items, dict) or items.get("type") != "string":
                errors.append(f"philosophy admission schema string items missing for {key}")
            if isinstance(items, dict):
                unsupported_item_constraints = sorted(set(items) - array_item_schema_keys)
                for constraint in unsupported_item_constraints:
                    errors.append(
                        "philosophy admission schema unsupported array item constraint for "
                        f"{key}: {constraint}"
                    )
            if key != "future_cache_candidate_deferred_surfaces" and not (
                isinstance(items, dict) and isinstance(items.get("enum"), list)
            ):
                errors.append(f"philosophy admission schema enum missing for {key}")
        if isinstance(items, dict) and "enum" in items and isinstance(payload[key], list):
            enum = items["enum"]
            if not isinstance(enum, list) or not all(isinstance(item, str) for item in enum):
                errors.append(f"philosophy admission schema enum must be a string list for {key}")
            else:
                if len(enum) != len(set(enum)):
                    errors.append(f"philosophy admission schema enum contains duplicates for {key}")
                invalid = [item for item in payload[key] if item not in enum]
                for item in invalid:
                    errors.append(f"philosophy admission schema enum mismatch for {key}: {item!r}")
                missing = [item for item in enum if item not in payload[key]]
                for item in missing:
                    errors.append(
                        f"philosophy admission schema enum missing from contract for {key}: "
                        f"{item!r}"
                    )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check semantic-cache gate markers.")
    parser.add_argument(
        "--doc",
        type=Path,
        default=DEFAULT_DOC,
        help="Semantic-cache gate markdown document to validate.",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT,
        help="Semantic-cache rollout contract markdown document to validate.",
    )
    parser.add_argument(
        "--scaffold-contract",
        type=Path,
        default=DEFAULT_SCAFFOLD_CONTRACT,
        help="SC-G2 exact/fuzzy scaffold markdown document to validate.",
    )
    parser.add_argument(
        "--observability-contract",
        type=Path,
        default=DEFAULT_OBSERVABILITY_CONTRACT,
        help="SC-G3 observability false-hit harness markdown document to validate.",
    )
    parser.add_argument(
        "--bounded-insight-contract",
        type=Path,
        default=DEFAULT_BOUNDED_INSIGHT_CONTRACT,
        help="SC-G4 bounded insight experiment markdown document to validate.",
    )
    parser.add_argument(
        "--backend-selection-contract",
        type=Path,
        default=DEFAULT_BACKEND_SELECTION_CONTRACT,
        help="SC-G5 backend selection markdown document to validate.",
    )
    parser.add_argument(
        "--backend-selection-schema",
        type=Path,
        default=DEFAULT_BACKEND_SELECTION_SCHEMA,
        help="SC-G5 backend selection JSON schema to validate.",
    )
    parser.add_argument(
        "--philosophy-admission-contract",
        type=Path,
        default=DEFAULT_PHILOSOPHY_ADMISSION_CONTRACT,
        help="Philosophy PR-1 admission markdown document to validate.",
    )
    parser.add_argument(
        "--philosophy-admission-schema",
        type=Path,
        default=DEFAULT_PHILOSOPHY_ADMISSION_SCHEMA,
        help="Philosophy PR-1 admission JSON schema to validate.",
    )
    args = parser.parse_args(argv)

    doc = args.doc
    if not doc.exists():
        print(f"ERROR: semantic-cache gate document missing: {doc}", file=sys.stderr)
        return 1

    contract = args.contract
    if not contract.exists():
        print(f"ERROR: semantic-cache rollout contract missing: {contract}", file=sys.stderr)
        return 1

    scaffold_contract = args.scaffold_contract
    if not scaffold_contract.exists():
        print(
            f"ERROR: exact/fuzzy scaffold contract missing: {scaffold_contract}",
            file=sys.stderr,
        )
        return 1

    observability_contract = args.observability_contract
    if not observability_contract.exists():
        print(
            f"ERROR: cache observability contract missing: {observability_contract}",
            file=sys.stderr,
        )
        return 1

    bounded_insight_contract = args.bounded_insight_contract
    if not bounded_insight_contract.exists():
        print(
            f"ERROR: bounded insight experiment contract missing: {bounded_insight_contract}",
            file=sys.stderr,
        )
        return 1

    backend_selection_contract = args.backend_selection_contract
    if not backend_selection_contract.exists():
        print(
            f"ERROR: backend selection contract missing: {backend_selection_contract}",
            file=sys.stderr,
        )
        return 1
    backend_selection_schema = args.backend_selection_schema
    if not backend_selection_schema.exists():
        print(
            f"ERROR: backend selection schema missing: {backend_selection_schema}",
            file=sys.stderr,
        )
        return 1

    philosophy_admission_contract = args.philosophy_admission_contract
    if not philosophy_admission_contract.exists():
        print(
            f"ERROR: philosophy admission contract missing: {philosophy_admission_contract}",
            file=sys.stderr,
        )
        return 1
    philosophy_admission_schema = args.philosophy_admission_schema
    if not philosophy_admission_schema.exists():
        print(
            f"ERROR: philosophy admission schema missing: {philosophy_admission_schema}",
            file=sys.stderr,
        )
        return 1

    errors = validate_semantic_cache_gate(doc.read_text(encoding="utf-8"))
    errors.extend(validate_semantic_cache_rollout_contract(contract.read_text(encoding="utf-8")))
    errors.extend(
        validate_exact_fuzzy_scaffold_contract(scaffold_contract.read_text(encoding="utf-8"))
    )
    errors.extend(
        validate_semantic_cache_observability_contract(
            observability_contract.read_text(encoding="utf-8")
        )
    )
    errors.extend(
        validate_semantic_cache_bounded_insight_experiment_contract(
            bounded_insight_contract.read_text(encoding="utf-8")
        )
    )
    backend_selection_text = backend_selection_contract.read_text(encoding="utf-8")
    errors.extend(validate_semantic_cache_backend_selection_contract(backend_selection_text))
    errors.extend(
        validate_semantic_cache_backend_selection_schema(
            schema_text=backend_selection_schema.read_text(encoding="utf-8"),
            contract_text=backend_selection_text,
        )
    )
    philosophy_admission_text = philosophy_admission_contract.read_text(encoding="utf-8")
    errors.extend(validate_philosophy_semantic_cache_admission_contract(philosophy_admission_text))
    errors.extend(
        validate_philosophy_semantic_cache_admission_schema(
            schema_text=philosophy_admission_schema.read_text(encoding="utf-8"),
            contract_text=philosophy_admission_text,
        )
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"semantic-cache gate closed: {doc}")
    print(f"semantic-cache rollout contract closed: {contract}")
    print(f"exact/fuzzy scaffold contract closed: {scaffold_contract}")
    print(f"cache observability contract closed: {observability_contract}")
    print(f"bounded insight experiment contract closed: {bounded_insight_contract}")
    print(f"backend selection contract closed: {backend_selection_contract}")
    print(f"philosophy admission contract closed: {philosophy_admission_contract}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
