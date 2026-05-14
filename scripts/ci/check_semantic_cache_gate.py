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
            r"\bsemantic\s+cache\s+(?:(?:is|has\s+been)\s+)?(?:now\s+)?"
            r"(?:implemented|active|enabled|open|approved|ready)\b"
        ),
    ),
    (
        "semantic-cache live claim",
        re.compile(
            r"\bsemantic-cache\s+(?:(?:is|has\s+been)\s+)?(?:now\s+)?"
            r"(?:implemented|active|enabled|open|approved|ready)\b"
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
        re.compile(r"\bbackend\s+(?:is\s+)?selected\s+for\s+serving\b"),
    ),
    (
        "backend active",
        re.compile(r"\bbackend\s+(?:is\s+)?(?:active|enabled|live|ready)\b"),
    ),
    (
        "semantic cache serving ready",
        re.compile(r"\bsemantic(?:-| )cache\s+serving\s+(?:is\s+)?(?:ready|active|enabled|live)\b"),
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

MARKER_RE = re.compile(r"<!--\s*(?P<key>SEMANTIC_CACHE_[A-Z_]+):\s*(?P<value>.*?)\s*-->")
MACHINE_JSON_RE = re.compile(r"```json\s*(?P<payload>\{.*?\})\s*```", re.DOTALL)


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
    return [
        f"forbidden semantic-cache claim: {label}"
        for label, pattern in FORBIDDEN_CLAIM_PATTERNS
        if pattern.search(normalized)
    ]


def _validate_rollout_order(
    normalized: str,
    *,
    missing_prefix: str,
    out_of_order_prefix: str,
) -> list[str]:
    errors: list[str] = []
    positions: dict[str, int] = {}

    for phrase in ROLLOUT_ORDER:
        normalized_phrase = _normalize_text(phrase)
        index = normalized.find(normalized_phrase)
        if index == -1:
            errors.append(f"{missing_prefix}: {phrase}")
            continue
        positions[phrase] = index

    previous_index = -1
    for phrase in ROLLOUT_ORDER:
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
            "Redis imports or clients",
            "GPTCache imports or clients",
            "provider calls",
            "environment reads",
            "network calls",
            "file writes",
            "connection strings",
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
            "approved Redis rollout claim",
            "approved GPTCache rollout claim",
            "serving backend selection claim",
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
            if isinstance(enum, list) and isinstance(actual, list):
                if key in {"candidate_backend_labels", "allowed_backend_labels"} and set(
                    enum
                ) != set(actual):
                    errors.append(f"backend selection schema enum set mismatch for {key}")
                invalid = [item for item in actual if item not in enum]
                for item in invalid:
                    errors.append(f"backend selection schema enum mismatch for {key}: {item!r}")

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
    errors.extend(
        validate_semantic_cache_backend_selection_contract(
            backend_selection_contract.read_text(encoding="utf-8")
        )
    )
    errors.extend(
        validate_semantic_cache_backend_selection_schema(
            schema_text=backend_selection_schema.read_text(encoding="utf-8"),
            contract_text=backend_selection_contract.read_text(encoding="utf-8"),
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
