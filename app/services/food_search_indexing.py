"""Deterministic helpers for diff-based food search indexing."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


def canonicalize_food_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return stable document shape before hashing or indexing."""

    canonical: dict[str, Any] = {}
    for key in sorted(document):
        if key == "content_hash":
            continue
        value = document[key]
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            canonical[key] = sorted(value)
            continue
        canonical[key] = value
    return canonical


def stable_food_document_dump(document: Mapping[str, Any]) -> str:
    """Return stable JSON dump for hashing."""

    return json.dumps(
        canonicalize_food_document(document),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def content_hash(document: Mapping[str, Any]) -> str:
    """Return stable content hash for indexing diff decisions."""

    return hashlib.sha256(stable_food_document_dump(document).encode("utf-8")).hexdigest()


def diff_emit(
    documents: Sequence[Mapping[str, Any]],
    cache: Mapping[str, str],
    *,
    id_field: str = "id",
) -> list[dict[str, Any]]:
    """Emit only materially changed documents with attached content hashes."""

    changed: list[dict[str, Any]] = []
    for document in documents:
        if id_field not in document:
            raise ValueError(f"Document missing required field '{id_field}': {document}")
        doc_id = str(document[id_field])
        doc_hash = content_hash(document)
        if cache.get(doc_id) == doc_hash:
            continue
        enriched_document = dict(canonicalize_food_document(document))
        enriched_document["content_hash"] = doc_hash
        changed.append(enriched_document)
    return changed


def build_swap_indexes_payload(
    index_pairs: Sequence[tuple[str, str]],
) -> list[dict[str, list[str]]]:
    """Return Meilisearch swap-indexes payload."""

    return [{"indexes": [current, candidate]} for current, candidate in index_pairs]
