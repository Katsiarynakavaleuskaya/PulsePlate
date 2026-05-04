"""Tests for the evaluation item metadata registry.

RU: Тесты для реестра метаданных eval-элементов.
EN: Deterministic, offline tests that validate the item metadata
    registry covers all fixture canonical_ids, has no orphan rows,
    matches expected decisions, and contains no forbidden content.

This test file does NOT implement IRT, psychometric scoring, or
adaptive item selection.  It validates registry metadata only.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from scripts.evals.eval_item_registry import (
    DIFFICULTY_BANDS,
    LANES,
    SCORE_BANDS,
    EvalItemMetadataRecord,
    extract_canonical_ids_from_outcome_fixture,
    index_registry_by_canonical_id,
    load_eval_item_registry,
    validate_eval_item_metadata_record,
    validate_registry_coverage,
)

# ---------------------------------------------------------------------------
# Paths (relative to repo root, resolved from this file)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _REPO_ROOT / "data" / "evals" / "eval_item_metadata_registry.jsonl"
_JUDGMENT_FIXTURE = (
    _REPO_ROOT / "data" / "evals" / "pulseplate_judgment_eval_validity_variants.jsonl"
)
_RAG_FIXTURE = _REPO_ROOT / "data" / "evals" / "pulseplate_rag_release_gate_validity_variants.jsonl"
_REGISTRY_MODULE = _REPO_ROOT / "scripts" / "evals" / "eval_item_registry.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture_canonical_rows(path: Path) -> dict[str, dict]:
    """Load canonical rows (variant_family == 'canonical') keyed by canonical_id."""
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            if raw.get("variant_family") == "canonical":
                rows[raw["canonical_id"]] = raw
    return rows


def _load_fixture_variant_families(path: Path) -> dict[str, set[str]]:
    """For each canonical_id, collect the set of variant_family values present."""
    families: dict[str, set[str]] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            cid = raw["canonical_id"]
            families.setdefault(cid, set()).add(raw["variant_family"])
    return families


# ---------------------------------------------------------------------------
# 1. File existence
# ---------------------------------------------------------------------------


class TestRegistryFileExists:
    def test_eval_item_metadata_registry_file_exists(self) -> None:
        assert _REGISTRY_PATH.exists(), f"Registry file not found: {_REGISTRY_PATH}"


# ---------------------------------------------------------------------------
# 2. Parse
# ---------------------------------------------------------------------------


class TestRegistryParses:
    def test_eval_item_metadata_registry_parses(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        assert len(records) > 0, "Registry must not be empty"


# ---------------------------------------------------------------------------
# 3. Validation
# ---------------------------------------------------------------------------


class TestRegistryRecordsValidate:
    def test_eval_item_metadata_registry_records_validate(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        for rec in records:
            assert rec["lane"] in LANES
            assert rec["difficulty_band"] in DIFFICULTY_BANDS
            assert rec["expected_score_band"] in SCORE_BANDS
            assert isinstance(rec["anchor_item"], bool)
            assert isinstance(rec["variant_family_coverage"], list)
            assert isinstance(rec["canonical_id"], str)
            assert isinstance(rec["domain"], str)
            assert isinstance(rec["skill_dimension"], str)
            assert isinstance(rec["expected_decision"], str)
            assert isinstance(rec["source_fixture"], str)
            assert isinstance(rec["notes"], str)


# ---------------------------------------------------------------------------
# 4. Unique canonical_ids
# ---------------------------------------------------------------------------


class TestRegistryUniqueIds:
    def test_eval_item_metadata_registry_has_unique_canonical_ids(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        ids = [rec["canonical_id"] for rec in records]
        assert len(ids) == len(set(ids)), (
            f"Duplicate canonical_ids in registry: "
            f"{sorted(cid for cid in ids if ids.count(cid) > 1)}"
        )


# ---------------------------------------------------------------------------
# 5. Covers all judgment canonical_ids
# ---------------------------------------------------------------------------


class TestRegistryCoversJudgment:
    def test_eval_item_metadata_registry_covers_all_judgment_canonical_ids(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        judgment_ids = extract_canonical_ids_from_outcome_fixture(_JUDGMENT_FIXTURE)
        registry_ids = {rec["canonical_id"] for rec in records}

        missing = judgment_ids - registry_ids
        assert not missing, f"Judgment canonical_ids missing from registry: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 6. Covers all RAG canonical_ids
# ---------------------------------------------------------------------------


class TestRegistryCoversRag:
    def test_eval_item_metadata_registry_covers_all_rag_canonical_ids(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        rag_ids = extract_canonical_ids_from_outcome_fixture(_RAG_FIXTURE)
        registry_ids = {rec["canonical_id"] for rec in records}

        missing = rag_ids - registry_ids
        assert not missing, f"RAG canonical_ids missing from registry: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 7. No orphan items
# ---------------------------------------------------------------------------


class TestRegistryNoOrphans:
    def test_eval_item_metadata_registry_has_no_orphan_items(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        judgment_ids = extract_canonical_ids_from_outcome_fixture(_JUDGMENT_FIXTURE)
        rag_ids = extract_canonical_ids_from_outcome_fixture(_RAG_FIXTURE)
        all_fixture_ids = judgment_ids | rag_ids

        validate_registry_coverage(records, all_fixture_ids)


# ---------------------------------------------------------------------------
# 8. Expected decision matches fixture canonical row
# ---------------------------------------------------------------------------


class TestRegistryExpectedDecisionMatchesFixture:
    def test_eval_item_metadata_registry_expected_decision_matches_fixture_canonical(
        self,
    ) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        index = index_registry_by_canonical_id(records)

        judgment_canonicals = _load_fixture_canonical_rows(_JUDGMENT_FIXTURE)
        rag_canonicals = _load_fixture_canonical_rows(_RAG_FIXTURE)
        overlap = set(judgment_canonicals) & set(rag_canonicals)
        assert not overlap, f"canonical_id overlap between fixtures: {sorted(overlap)}"
        all_canonicals = {**judgment_canonicals, **rag_canonicals}

        for cid, reg_rec in index.items():
            fixture_row = all_canonicals.get(cid)
            assert fixture_row is not None, f"Registry item {cid!r} has no canonical fixture row"
            assert reg_rec["expected_decision"] == fixture_row["decision"], (
                f"Registry expected_decision={reg_rec['expected_decision']!r} "
                f"does not match fixture decision={fixture_row['decision']!r} "
                f"for canonical_id={cid!r}"
            )


# ---------------------------------------------------------------------------
# 9. Variant family coverage matches fixture
# ---------------------------------------------------------------------------


class TestRegistryVariantFamilyCoverage:
    def test_eval_item_metadata_registry_variant_family_coverage_matches_fixture(
        self,
    ) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        index = index_registry_by_canonical_id(records)

        judgment_families = _load_fixture_variant_families(_JUDGMENT_FIXTURE)
        rag_families = _load_fixture_variant_families(_RAG_FIXTURE)
        overlap = set(judgment_families) & set(rag_families)
        assert not overlap, f"canonical_id overlap between fixtures: {sorted(overlap)}"
        all_families = {**judgment_families, **rag_families}

        for cid, reg_rec in index.items():
            fixture_fams = all_families.get(cid)
            assert fixture_fams is not None, f"Registry item {cid!r} has no fixture rows"
            registry_fams = set(reg_rec["variant_family_coverage"])
            assert registry_fams == fixture_fams, (
                f"Variant family coverage mismatch for {cid!r}: "
                f"registry={sorted(registry_fams)}, "
                f"fixture={sorted(fixture_fams)}"
            )


# ---------------------------------------------------------------------------
# 10. Difficulty band is valid
# ---------------------------------------------------------------------------


class TestRegistryDifficultyBand:
    def test_eval_item_metadata_registry_difficulty_band_is_valid(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        for rec in records:
            assert rec["difficulty_band"] in DIFFICULTY_BANDS, (
                f"Invalid difficulty_band={rec['difficulty_band']!r} "
                f"for canonical_id={rec['canonical_id']!r}"
            )


# ---------------------------------------------------------------------------
# 11. Expected score band is valid
# ---------------------------------------------------------------------------


class TestRegistryExpectedScoreBand:
    def test_eval_item_metadata_registry_expected_score_band_is_valid(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        for rec in records:
            assert rec["expected_score_band"] in SCORE_BANDS, (
                f"Invalid expected_score_band={rec['expected_score_band']!r} "
                f"for canonical_id={rec['canonical_id']!r}"
            )


# ---------------------------------------------------------------------------
# 12. Anchor items for each lane
# ---------------------------------------------------------------------------


class TestRegistryAnchorItems:
    def test_eval_item_metadata_registry_has_anchor_items_for_each_lane(self) -> None:
        records = load_eval_item_registry(_REGISTRY_PATH)
        lanes_with_anchors: set[str] = set()
        for rec in records:
            if rec["anchor_item"]:
                lanes_with_anchors.add(rec["lane"])

        for lane in LANES:
            assert lane in lanes_with_anchors, f"No anchor_item=true found for lane={lane!r}"


# ---------------------------------------------------------------------------
# 13. No LLM or provider metadata
# ---------------------------------------------------------------------------


_FORBIDDEN_STRINGS = frozenset(
    {
        "api_key",
        "token",
        "secret",
        "password",
        "openai",
        "anthropic",
        "claude",
        "gpt-",
        "gpt_",
        "model_name",
        "provider",
        "http://",
        "https://",
        "sk-",
        "Bearer ",
    }
)


class TestRegistryNoLlmOrProviderMetadata:
    def test_eval_item_metadata_registry_has_no_llm_or_provider_metadata(self) -> None:
        content = _REGISTRY_PATH.read_text(encoding="utf-8")
        content_lower = content.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert (
                forbidden.lower() not in content_lower
            ), f"Registry contains forbidden string: {forbidden!r}"


# ---------------------------------------------------------------------------
# 14. No network lib imports
# ---------------------------------------------------------------------------


_NETWORK_MODULES = frozenset(
    {
        "requests",
        "httpx",
        "aiohttp",
        "urllib3",
        "urllib.request",
        "socket",
        "http.client",
    }
)


def _is_forbidden_module(module_name: str) -> bool:
    """Check if a module name matches or is a submodule of a forbidden network lib."""
    return any(
        module_name == forbidden or module_name.startswith(f"{forbidden}.")
        for forbidden in _NETWORK_MODULES
    )


class TestRegistryNoNetworkImports:
    def test_eval_item_metadata_registry_does_not_import_network_libs(self) -> None:
        source = _REGISTRY_MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_forbidden_module(
                        alias.name
                    ), f"eval_item_registry.py imports network lib: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    assert not _is_forbidden_module(
                        node.module
                    ), f"eval_item_registry.py imports from network lib: {node.module}"
                    # Also check "from <parent> import <child>" where
                    # "<parent>.<child>" is a forbidden module (e.g.
                    # "from urllib import request" -> "urllib.request").
                    for alias in node.names:
                        qualified = f"{node.module}.{alias.name}"
                        assert not _is_forbidden_module(
                            qualified
                        ), f"eval_item_registry.py imports from network lib: {qualified}"


# ---------------------------------------------------------------------------
# 15. No IRT scoring
# ---------------------------------------------------------------------------

_IRT_PATTERNS = frozenset(
    {
        "item_response_theory",
        "irt_difficulty",
        "irt_discrimination",
        "irt_information",
        "rasch_model",
        "2pl_model",
        "3pl_model",
        "theta_estimate",
        "item_information_function",
        "test_information_function",
        "scipy.optimize",
        "scipy.stats",
        "numpy",
    }
)


class TestRegistryNoIrtScoring:
    def test_eval_item_metadata_registry_does_not_compute_irt_scores(self) -> None:
        source = _REGISTRY_MODULE.read_text(encoding="utf-8")
        source_lower = source.lower()
        for pattern in _IRT_PATTERNS:
            assert (
                pattern.lower() not in source_lower
            ), f"eval_item_registry.py contains IRT pattern: {pattern!r}"


# ---------------------------------------------------------------------------
# 16. Negative validation tests (GAP-1)
# ---------------------------------------------------------------------------

# A valid base record for mutation in negative tests.
_VALID_RAW: dict = {
    "canonical_id": "test_001",
    "lane": "rag",
    "domain": "release_gate",
    "skill_dimension": "retrieval_faithfulness",
    "difficulty_band": "low",
    "expected_decision": "pass",
    "expected_score_band": "pass",
    "variant_family_coverage": ["canonical"],
    "anchor_item": True,
    "source_fixture": "test.jsonl",
    "notes": "Test note.",
}


class TestValidatorRejectsInvalidInput:
    def test_rejects_non_dict_input(self) -> None:
        with pytest.raises(ValueError, match="expects dict"):
            validate_eval_item_metadata_record([1, 2, 3])  # type: ignore[arg-type]

    def test_rejects_missing_key(self) -> None:
        bad = {k: v for k, v in _VALID_RAW.items() if k != "lane"}
        with pytest.raises(ValueError, match="missing keys"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_extra_key(self) -> None:
        bad = {**_VALID_RAW, "extra_field": "oops"}
        with pytest.raises(ValueError, match="unexpected keys"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_invalid_lane(self) -> None:
        bad = {**_VALID_RAW, "lane": "unknown"}
        with pytest.raises(ValueError, match="Invalid lane"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_invalid_difficulty_band(self) -> None:
        bad = {**_VALID_RAW, "difficulty_band": "extreme"}
        with pytest.raises(ValueError, match="Invalid difficulty_band"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_invalid_score_band(self) -> None:
        bad = {**_VALID_RAW, "expected_score_band": "excellent"}
        with pytest.raises(ValueError, match="Invalid expected_score_band"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_non_bool_anchor_item(self) -> None:
        bad = {**_VALID_RAW, "anchor_item": "yes"}
        with pytest.raises(ValueError, match="anchor_item must be bool"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_non_list_variant_family_coverage(self) -> None:
        bad = {**_VALID_RAW, "variant_family_coverage": "canonical"}
        with pytest.raises(ValueError, match="variant_family_coverage must be list"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_empty_variant_family_coverage(self) -> None:
        bad = {**_VALID_RAW, "variant_family_coverage": []}
        with pytest.raises(ValueError, match="variant_family_coverage must not be empty"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_non_string_items_in_variant_family_coverage(self) -> None:
        bad = {**_VALID_RAW, "variant_family_coverage": [123]}
        with pytest.raises(ValueError, match="variant_family_coverage must contain only strings"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_non_string_canonical_id(self) -> None:
        bad = {**_VALID_RAW, "canonical_id": 999}
        with pytest.raises(ValueError, match="canonical_id must be str"):
            validate_eval_item_metadata_record(bad)

    def test_rejects_non_string_domain(self) -> None:
        bad = {**_VALID_RAW, "domain": None}
        with pytest.raises(ValueError, match="domain must be str"):
            validate_eval_item_metadata_record(bad)

    def test_accepts_valid_record(self) -> None:
        result = validate_eval_item_metadata_record(dict(_VALID_RAW))
        assert result["canonical_id"] == "test_001"


# ---------------------------------------------------------------------------
# 17. index_registry_by_canonical_id duplicate detection (GAP-2)
# ---------------------------------------------------------------------------


class TestIndexRegistryDuplicateDetection:
    def test_index_registry_by_canonical_id_rejects_duplicates(self) -> None:
        rec: EvalItemMetadataRecord = validate_eval_item_metadata_record(dict(_VALID_RAW))
        with pytest.raises(ValueError, match="Duplicate canonical_id"):
            index_registry_by_canonical_id([rec, rec])


# ---------------------------------------------------------------------------
# 18. validate_registry_coverage error paths (GAP-3)
# ---------------------------------------------------------------------------


class TestRegistryCoverageErrorPaths:
    def test_coverage_rejects_missing_fixture_ids(self) -> None:
        with pytest.raises(ValueError, match="missing from registry"):
            validate_registry_coverage([], {"missing_001"})

    def test_coverage_rejects_orphan_registry_ids(self) -> None:
        rec: EvalItemMetadataRecord = validate_eval_item_metadata_record(dict(_VALID_RAW))
        with pytest.raises(ValueError, match="Orphan registry"):
            validate_registry_coverage([rec], set())

    def test_coverage_passes_when_both_empty(self) -> None:
        validate_registry_coverage([], set())
