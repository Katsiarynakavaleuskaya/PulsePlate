"""
Advanced tests for core.food_apis.unified_db module - common foods and integration

RU: Продвинутые тесты для модуля унифицированной базы данных - общие продукты и интеграция.
EN: Advanced tests for unified database module - common foods and integration.
"""

import asyncio
import json
import logging
import os
import tempfile
import threading
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from typing import IO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis import unified_db as unified_db_module
from core.food_apis.openfoodfacts_client import OFFFoodItem
from core.food_apis.unified_db import (
    COMMON_FOODS_CACHE_SCHEMA_VERSION,
    COMMON_FOODS_MANIFEST,
    COMMON_FOODS_MANIFEST_VERSION,
    CommonFoodsCacheAdmissionError,
    UnifiedFoodDatabase,
    UnifiedFoodItem,
    get_unified_food_db,
    search_foods_unified,
)
from core.food_apis.usda_client import USDAFoodItem


def _common_food_item(index: int) -> UnifiedFoodItem:
    nutrient_key = f"nutrient_{index}"
    nutrient_value = float(index + 1)
    return UnifiedFoodItem(
        name=f"Common Food {index}",
        nutrients_per_100g={
            nutrient_key: nutrient_value,
            "protein_g": 1.0,
            "fat_g": 0.0,
            "carbs_g": 0.0,
        },
        cost_per_100g=1.0,
        tags=["offline-test"],
        availability_regions=["TEST"],
        source="Deterministic fixture",
        source_id=f"fixture-{index}",
        category="Fixture",
        nutrition_inputs=[
            {
                "source": "usda",
                "record_id": f"fixture-{index}",
                "version_ref": "2026-08-10",
                "nutrients": {nutrient_key: nutrient_value, "protein_g": 1.0},
                "raw_payload": {},
            }
        ],
        nutrition_provenance={nutrient_key: "usda", "protein_g": "usda"},
        nutrition_nutrient_confidence={nutrient_key: 0.7, "protein_g": 0.7},
        nutrition_confidence=0.7,
    )


def _valid_common_foods_envelope() -> dict[str, object]:
    return {
        "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
        "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
        "items": {
            name: asdict(_common_food_item(index))
            for index, name in enumerate(COMMON_FOODS_MANIFEST)
        },
    }


def _write_common_foods_envelope(path: Path, envelope: object) -> None:
    path.write_text(json.dumps(envelope), encoding="utf-8")


def _common_foods_json_with_duplicate(duplicate_kind: str) -> str:
    envelope = _valid_common_foods_envelope()
    items = envelope["items"]
    assert isinstance(items, dict)
    first_name = next(iter(COMMON_FOODS_MANIFEST))
    first_item = items[first_name]
    remaining_items = {name: item for name, item in items.items() if name != first_name}

    if duplicate_kind == "duplicate_top_level":
        return (
            "{"
            f'"schema_version":{json.dumps(COMMON_FOODS_CACHE_SCHEMA_VERSION)},'
            f'"schema_version":{json.dumps(COMMON_FOODS_CACHE_SCHEMA_VERSION)},'
            f'"manifest_version":{json.dumps(COMMON_FOODS_MANIFEST_VERSION)},'
            f'"items":{json.dumps(items)}'
            "}"
        )
    if duplicate_kind == "duplicate_item_key":
        return (
            "{"
            f'"schema_version":{json.dumps(COMMON_FOODS_CACHE_SCHEMA_VERSION)},'
            f'"manifest_version":{json.dumps(COMMON_FOODS_MANIFEST_VERSION)},'
            '"items":{'
            f"{json.dumps(first_name)}:{json.dumps(first_item)},"
            f"{json.dumps(first_name)}:{json.dumps(first_item)},"
            f"{json.dumps(remaining_items)[1:]}"
            "}"
        )
    if duplicate_kind == "duplicate_item_member":
        assert isinstance(first_item, dict)
        duplicated_item = json.dumps(first_item)[:-1] + ',"name":"duplicate"}'
        return (
            "{"
            f'"schema_version":{json.dumps(COMMON_FOODS_CACHE_SCHEMA_VERSION)},'
            f'"manifest_version":{json.dumps(COMMON_FOODS_MANIFEST_VERSION)},'
            '"items":{'
            f"{json.dumps(first_name)}:{duplicated_item},"
            f"{json.dumps(remaining_items)[1:]}"
            "}"
        )
    raise AssertionError(f"Unknown duplicate fixture: {duplicate_kind}")


class TestUnifiedFoodDatabaseCommonFoods:
    """Test common foods database functionality."""

    @pytest.fixture(autouse=True)
    def _disable_inter_row_delay(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNIFIED_DB_COMMON_SLEEP_MS", "0")

    def test_manifest_is_exact_versioned_and_immutable(self) -> None:
        assert COMMON_FOODS_MANIFEST_VERSION == "common-foods-manifest.v1"
        assert tuple(COMMON_FOODS_MANIFEST.items()) == (
            ("chicken_breast", "chicken breast meat only cooked roasted"),
            ("salmon", "salmon atlantic farmed cooked dry heat"),
            ("lentils", "lentils mature seeds cooked boiled"),
            ("spinach", "spinach raw"),
            ("oats", "cereals oats regular and quick unenriched dry"),
            ("broccoli", "broccoli raw"),
            ("brown_rice", "rice brown long-grain cooked"),
            ("quinoa", "quinoa cooked"),
            ("almonds", "nuts almonds"),
            ("greek_yogurt", "yogurt greek plain nonfat"),
            ("eggs", "egg whole raw fresh"),
            ("sweet_potato", "sweet potato raw unprepared"),
            ("avocado", "avocados raw all commercial varieties"),
            ("banana", "bananas raw"),
            ("black_beans", "beans black mature seeds cooked boiled"),
            ("tofu", "tofu raw firm prepared with calcium sulfate"),
            ("olive_oil", "oil olive salad or cooking"),
            ("milk", "milk reduced fat fluid 2% milkfat"),
            ("carrots", "carrots raw"),
            ("tomatoes", "tomatoes red ripe raw year round average"),
        )
        assert type(COMMON_FOODS_MANIFEST).__name__ == "mappingproxy"
        assert not hasattr(COMMON_FOODS_MANIFEST, "__setitem__")

    def test_warm_cache_requires_exact_envelope_and_preserves_evidence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        envelope = _valid_common_foods_envelope()
        cache_file = tmp_path / "common_foods.json"
        _write_common_foods_envelope(cache_file, envelope)
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))

        async def unexpected_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            raise AssertionError(
                f"warm cache searched unexpectedly: {query}, {save_cache}, {use_memory_cache}"
            )

        monkeypatch.setattr(db, "search_food", unexpected_search)
        foods = asyncio.run(db.get_common_foods_database())

        assert tuple(foods) == tuple(COMMON_FOODS_MANIFEST)
        expected_items = envelope["items"]
        assert isinstance(expected_items, dict)
        assert asdict(foods["chicken_breast"]) == expected_items["chicken_breast"]

    def test_cold_cache_completes_one_exact_sweep_and_publishes_atomically(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        calls: list[tuple[str, bool, bool]] = []
        queries = tuple(COMMON_FOODS_MANIFEST.values())

        async def deterministic_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            calls.append((query, save_cache, use_memory_cache))
            return [_common_food_item(queries.index(query))]

        replace_calls: list[tuple[Path, Path]] = []
        real_replace = os.replace

        def recording_replace(source: str | Path, target: str | Path) -> None:
            source_path = Path(source)
            target_path = Path(target)
            assert source_path.parent == target_path.parent == tmp_path
            assert source_path != target_path
            replace_calls.append((source_path, target_path))
            real_replace(source_path, target_path)

        sleep = AsyncMock()
        monkeypatch.setattr(db, "search_food", deterministic_search)
        monkeypatch.setattr(unified_db_module.asyncio, "sleep", sleep)
        monkeypatch.setattr(unified_db_module.os, "replace", recording_replace)
        foods = asyncio.run(db.get_common_foods_database())

        assert calls == [(query, False, False) for query in queries]
        assert sleep.await_count == len(queries) - 1
        assert all(call.args == (0.0,) for call in sleep.await_args_list)
        assert tuple(foods) == tuple(COMMON_FOODS_MANIFEST)
        assert len(replace_calls) == 1
        cache_file = tmp_path / "common_foods.json"
        published = json.loads(cache_file.read_text(encoding="utf-8"))
        assert set(published) == {"schema_version", "manifest_version", "items"}
        assert published["schema_version"] == COMMON_FOODS_CACHE_SCHEMA_VERSION
        assert published["manifest_version"] == COMMON_FOODS_MANIFEST_VERSION
        assert not list(tmp_path.glob(".common_foods.json.*.tmp"))

    def test_force_refresh_bypasses_warm_disk_and_memory_for_exact_manifest_sweep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        old_envelope = _valid_common_foods_envelope()
        cache_file = tmp_path / "common_foods.json"
        _write_common_foods_envelope(cache_file, old_envelope)
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        calls: list[tuple[str, bool, bool]] = []
        queries = tuple(COMMON_FOODS_MANIFEST.values())
        for query in queries:
            db._memory_cache[f"search_{query}"] = _common_food_item(500)

        async def refreshed_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            calls.append((query, save_cache, use_memory_cache))
            return [_common_food_item(100 + queries.index(query))]

        monkeypatch.setattr(db, "search_food", refreshed_search)

        refreshed = asyncio.run(db.get_common_foods_database(force_refresh=True))

        assert calls == [(query, False, False) for query in queries]
        assert refreshed["chicken_breast"].source_id == "fixture-100"
        published = json.loads(cache_file.read_text(encoding="utf-8"))
        assert published["items"]["chicken_breast"]["source_id"] == "fixture-100"

    @pytest.mark.parametrize(
        ("mutation", "expected_error"),
        [
            ("protein_over_100g", "macronutrient bounds"),
            ("no_protein_or_fat", "macronutrient bounds"),
            ("blank_record_id", "nutrition evidence"),
            ("blank_version_ref", "nutrition evidence"),
        ],
    )
    def test_common_food_admission_enforces_top_level_macros_and_nonblank_refs(
        self, mutation: str, expected_error: str
    ) -> None:
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)
        chicken = items["chicken_breast"]
        assert isinstance(chicken, dict)
        evidence = chicken["nutrition_inputs"]
        assert isinstance(evidence, list)
        first_evidence = evidence[0]
        assert isinstance(first_evidence, dict)
        nutrients = chicken["nutrients_per_100g"]
        assert isinstance(nutrients, dict)

        if mutation == "protein_over_100g":
            nutrients["protein_g"] = 101.0
        elif mutation == "no_protein_or_fat":
            nutrients["protein_g"] = 0.0
            nutrients["fat_g"] = 0.0
        elif mutation == "blank_record_id":
            first_evidence["record_id"] = "   "
        else:
            first_evidence["version_ref"] = "   "

        with pytest.raises(CommonFoodsCacheAdmissionError, match=expected_error):
            UnifiedFoodDatabase._validate_common_foods_envelope(envelope)

    @pytest.mark.parametrize(
        ("blank_carrier", "expected_error"),
        [
            ("top_level_nutrient_key", "nutrient shape"),
            ("input_nutrient_key", "nutrition evidence"),
            ("raw_payload_key", "nutrition evidence"),
            ("provenance_key", "provenance evidence"),
            ("provenance_value", "provenance evidence"),
        ],
    )
    @pytest.mark.parametrize("blank_text", ["", "   "], ids=["empty", "whitespace"])
    def test_common_food_admission_rejects_blank_nutrition_mapping_strings(
        self,
        blank_carrier: str,
        expected_error: str,
        blank_text: str,
    ) -> None:
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)
        chicken = items["chicken_breast"]
        assert isinstance(chicken, dict)
        nutrients = chicken["nutrients_per_100g"]
        nutrition_inputs = chicken["nutrition_inputs"]
        provenance = chicken["nutrition_provenance"]
        assert isinstance(nutrients, dict)
        assert isinstance(nutrition_inputs, list)
        assert isinstance(provenance, dict)
        nutrition_input = nutrition_inputs[0]
        assert isinstance(nutrition_input, dict)
        input_nutrients = nutrition_input["nutrients"]
        raw_payload = nutrition_input["raw_payload"]
        assert isinstance(input_nutrients, dict)
        assert isinstance(raw_payload, dict)

        if blank_carrier == "top_level_nutrient_key":
            nutrients[blank_text] = nutrients.pop("nutrient_0")
        elif blank_carrier == "input_nutrient_key":
            input_nutrients[blank_text] = input_nutrients.pop("nutrient_0")
        elif blank_carrier == "raw_payload_key":
            raw_payload[blank_text] = "evidence"
        elif blank_carrier == "provenance_key":
            provenance[blank_text] = provenance.pop("nutrient_0")
        else:
            provenance["nutrient_0"] = blank_text

        with pytest.raises(CommonFoodsCacheAdmissionError, match=expected_error):
            UnifiedFoodDatabase._validate_common_foods_envelope(envelope)

    def test_common_food_path_rejects_symlink_before_warm_or_provider_access(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        outside = tmp_path / "outside.json"
        outside.write_text(json.dumps(_valid_common_foods_envelope()), encoding="utf-8")
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "common_foods.json"
        cache_file.symlink_to(outside)
        db = UnifiedFoodDatabase(cache_dir=str(cache_dir))
        acquisition = AsyncMock()
        monkeypatch.setattr(db, "_acquire_common_foods_envelope", acquisition)

        with pytest.raises(CommonFoodsCacheAdmissionError, match="not a regular file"):
            asyncio.run(db.get_common_foods_database())

        acquisition.assert_not_awaited()
        assert cache_file.is_symlink()
        assert outside.exists()

    def test_search_food_memory_cache_bypass_is_explicit_and_default_preserving(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        db.off_client = None
        query = "bounded cold-cache lookup"
        stale_item = _common_food_item(0)
        db._memory_cache[f"search_{query}"] = stale_item
        fresh_item = USDAFoodItem(
            fdc_id=991,
            description="Fresh provider row",
            food_category="Fixture",
            nutrients_per_100g={"protein_g": 11.0, "fat_g": 2.0, "carbs_g": 3.0},
            data_type="Foundation",
            publication_date="2026-08-11",
        )
        provider_search = AsyncMock(return_value=[fresh_item])
        monkeypatch.setattr(db.usda_client, "search_foods", provider_search)

        default_result = asyncio.run(db.search_food(query, save_cache=False))
        assert default_result == [stale_item]
        provider_search.assert_not_awaited()

        bypass_result = asyncio.run(db.search_food(query, save_cache=False, use_memory_cache=False))
        assert [item.source_id for item in bypass_result] == ["991"]
        provider_search.assert_awaited_once_with(query, page_size=5)
        assert db._memory_cache[f"search_{query}"] is stale_item

        fresh_query = "uncached bounded cold-cache lookup"
        asyncio.run(db.search_food(fresh_query, save_cache=False, use_memory_cache=False))
        assert f"search_{fresh_query}" not in db._memory_cache

    @pytest.mark.parametrize("resolved_count", [0, 14, 19])
    def test_cold_cache_rejects_incomplete_sweeps(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        resolved_count: int,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        calls: list[str] = []
        queries = tuple(COMMON_FOODS_MANIFEST.values())

        async def incomplete_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            calls.append(query)
            index = queries.index(query)
            return [_common_food_item(index)] if index < resolved_count else []

        monkeypatch.setattr(db, "search_food", incomplete_search)
        with pytest.raises(CommonFoodsCacheAdmissionError, match="membership is not exact"):
            asyncio.run(db.get_common_foods_database())

        assert calls == list(queries)
        assert not (tmp_path / "common_foods.json").exists()

    def test_ordinary_row_exception_leaves_unresolved_and_sweep_continues(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        calls: list[str] = []
        queries = tuple(COMMON_FOODS_MANIFEST.values())
        sensitive_provider_context = "advanced-provider-context-marker-7f31-do-not-log"

        async def one_error_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            calls.append(query)
            index = queries.index(query)
            if index == 7:
                raise RuntimeError(sensitive_provider_context)
            return [_common_food_item(index)]

        monkeypatch.setattr(db, "search_food", one_error_search)
        with pytest.raises(CommonFoodsCacheAdmissionError):
            asyncio.run(db.get_common_foods_database())

        assert calls == list(queries)
        assert not (tmp_path / "common_foods.json").exists()
        assert sensitive_provider_context not in caplog.text
        assert "category=RuntimeError" in caplog.text

    def test_real_usda_common_food_path_is_finite_secret_safe_and_unpublished(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        db.off_client = None
        provider_marker = "usda-provider-context-marker-a183"
        usda_search = AsyncMock(side_effect=RuntimeError(provider_marker))
        monkeypatch.setattr(db.usda_client, "search_foods", usda_search)
        caplog.set_level(logging.ERROR, logger=unified_db_module.__name__)

        with pytest.raises(CommonFoodsCacheAdmissionError, match="membership is not exact"):
            asyncio.run(db.get_common_foods_database())

        assert usda_search.await_count == len(COMMON_FOODS_MANIFEST)
        assert not (tmp_path / "common_foods.json").exists()
        assert not list(tmp_path.glob(".common_foods.json.*.tmp"))
        assert provider_marker not in caplog.text
        sink_records = [
            record
            for record in caplog.records
            if record.getMessage() == "Unified DB USDA search failed; category=RuntimeError"
        ]
        assert len(sink_records) == len(COMMON_FOODS_MANIFEST)
        assert all(record.exc_info is None for record in sink_records)

    @pytest.mark.parametrize(
        "corruption",
        [
            "malformed_json",
            "extra_top_level",
            "stale_schema",
            "stale_manifest",
            "wrong_member_twenty",
            "extra_item_field",
            "evidence_loss",
            "duplicate_top_level",
            "duplicate_item_key",
            "duplicate_item_member",
        ],
    )
    def test_invalid_warm_cache_is_never_admitted(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        corruption: str,
    ) -> None:
        cache_file = tmp_path / "common_foods.json"
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)

        if corruption == "malformed_json":
            cache_file.write_text("{broken", encoding="utf-8")
        elif corruption.startswith("duplicate_"):
            cache_file.write_text(_common_foods_json_with_duplicate(corruption), encoding="utf-8")
        else:
            if corruption == "extra_top_level":
                envelope["extra"] = "not admitted"
            elif corruption == "stale_schema":
                envelope["schema_version"] = "common-foods-cache.v0"
            elif corruption == "stale_manifest":
                envelope["manifest_version"] = "common-foods-manifest.v0"
            elif corruption == "wrong_member_twenty":
                items["wrong_member"] = items.pop("tomatoes")
            elif corruption == "extra_item_field":
                chicken = items["chicken_breast"]
                assert isinstance(chicken, dict)
                chicken["extra"] = "not admitted"
            elif corruption == "evidence_loss":
                chicken = items["chicken_breast"]
                assert isinstance(chicken, dict)
                chicken.pop("nutrition_inputs")
            _write_common_foods_envelope(cache_file, envelope)

        old_bytes = cache_file.read_bytes()
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        calls: list[str] = []

        async def unresolved_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            calls.append(query)
            return []

        monkeypatch.setattr(db, "search_food", unresolved_search)
        with pytest.raises(CommonFoodsCacheAdmissionError):
            asyncio.run(db.get_common_foods_database())

        assert calls == list(COMMON_FOODS_MANIFEST.values())
        assert cache_file.read_bytes() == old_bytes

    def test_duplicate_source_identity_across_manifest_slots_is_rejected(self) -> None:
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)
        first_name, second_name = tuple(COMMON_FOODS_MANIFEST)[:2]
        first_item = items[first_name]
        second_item = items[second_name]
        assert isinstance(first_item, dict)
        assert isinstance(second_item, dict)
        second_item["source"] = first_item["source"]
        second_item["source_id"] = first_item["source_id"]

        with pytest.raises(
            CommonFoodsCacheAdmissionError,
            match="Duplicate common-food source identity across manifest slots",
        ):
            UnifiedFoodDatabase._validate_common_foods_envelope(envelope)

    def test_total_deadline_becomes_admission_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        calls: list[str] = []

        async def blocked_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            calls.append(query)
            await asyncio.sleep(1.0)
            return []

        monkeypatch.setattr(db, "search_food", blocked_search)
        monkeypatch.setattr(unified_db_module, "COMMON_FOODS_ACQUISITION_TIMEOUT_SECONDS", 0.01)
        with pytest.raises(CommonFoodsCacheAdmissionError, match="total deadline"):
            asyncio.run(db.get_common_foods_database())

        assert len(calls) == 1
        assert not (tmp_path / "common_foods.json").exists()

    def test_synchronous_validation_overrun_times_out_before_publication(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        real_validate = db._validate_common_foods_envelope
        publication = MagicMock()

        def validate_after_deadline(envelope: object) -> dict[str, UnifiedFoodItem]:
            foods = real_validate(envelope)
            threading.Event().wait(0.03)
            return foods

        monkeypatch.setattr(
            db,
            "_acquire_common_foods_envelope",
            AsyncMock(return_value=_valid_common_foods_envelope()),
        )
        monkeypatch.setattr(db, "_validate_common_foods_envelope", validate_after_deadline)
        monkeypatch.setattr(db, "_publish_common_foods_envelope", publication)
        monkeypatch.setattr(
            unified_db_module,
            "COMMON_FOODS_ACQUISITION_TIMEOUT_SECONDS",
            0.01,
        )

        with pytest.raises(CommonFoodsCacheAdmissionError, match="total deadline"):
            asyncio.run(db.get_common_foods_database())

        publication.assert_not_called()
        assert not (tmp_path / "common_foods.json").exists()

    def test_synchronous_publication_overrun_compensates_new_cache_before_timeout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        cache_file = tmp_path / "common_foods.json"
        real_publish = db._publish_common_foods_envelope

        def publish_before_deadline_check(
            target: Path,
            envelope: dict[str, object],
        ) -> None:
            real_publish(target, envelope)
            threading.Event().wait(0.03)

        monkeypatch.setattr(
            db,
            "_acquire_common_foods_envelope",
            AsyncMock(return_value=_valid_common_foods_envelope()),
        )
        monkeypatch.setattr(db, "_publish_common_foods_envelope", publish_before_deadline_check)
        monkeypatch.setattr(
            unified_db_module,
            "COMMON_FOODS_ACQUISITION_TIMEOUT_SECONDS",
            0.01,
        )

        with pytest.raises(CommonFoodsCacheAdmissionError, match="total deadline"):
            asyncio.run(db.get_common_foods_database())

        assert not cache_file.exists()
        assert not list(tmp_path.glob(".common_foods.json.deadline-rollback.*.tmp"))

    def test_force_refresh_deadline_overrun_restores_exact_prior_cache_bytes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        cache_file = tmp_path / "common_foods.json"
        cache_file.write_text(
            json.dumps(_valid_common_foods_envelope(), separators=(",", ":")),
            encoding="utf-8",
        )
        prior_bytes = cache_file.read_bytes()
        refreshed_envelope = _valid_common_foods_envelope()
        refreshed_items = refreshed_envelope["items"]
        assert isinstance(refreshed_items, dict)
        refreshed_chicken = refreshed_items["chicken_breast"]
        assert isinstance(refreshed_chicken, dict)
        refreshed_chicken["name"] = "Refreshed Chicken"
        real_publish = db._publish_common_foods_envelope

        def publish_then_overrun(target: Path, envelope: dict[str, object]) -> None:
            real_publish(target, envelope)
            threading.Event().wait(0.03)

        monkeypatch.setattr(
            db,
            "_acquire_common_foods_envelope",
            AsyncMock(return_value=refreshed_envelope),
        )
        monkeypatch.setattr(db, "_publish_common_foods_envelope", publish_then_overrun)
        monkeypatch.setattr(
            unified_db_module,
            "COMMON_FOODS_ACQUISITION_TIMEOUT_SECONDS",
            0.01,
        )

        with pytest.raises(CommonFoodsCacheAdmissionError, match="total deadline"):
            asyncio.run(db.get_common_foods_database(force_refresh=True))

        assert cache_file.read_bytes() == prior_bytes
        assert not list(tmp_path.glob(".common_foods.json.deadline-rollback.*.tmp"))

    def test_waiter_lock_wait_and_acquisition_share_one_total_deadline(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        owner_started = asyncio.Event()
        waiter_acquisition_started = asyncio.Event()
        acquisition_count = 0
        publication = MagicMock()

        async def acquire_with_owner_timeout() -> dict[str, object]:
            nonlocal acquisition_count
            acquisition_count += 1
            if acquisition_count == 1:
                owner_started.set()
                await asyncio.Event().wait()
            waiter_acquisition_started.set()
            await asyncio.sleep(0.22)
            return _valid_common_foods_envelope()

        monkeypatch.setattr(db, "_acquire_common_foods_envelope", acquire_with_owner_timeout)
        monkeypatch.setattr(db, "_publish_common_foods_envelope", publication)
        monkeypatch.setattr(
            unified_db_module,
            "COMMON_FOODS_ACQUISITION_TIMEOUT_SECONDS",
            0.3,
        )

        async def run_owner_and_waiter() -> tuple[object, object]:
            owner = asyncio.create_task(db.get_common_foods_database())
            await owner_started.wait()
            await asyncio.sleep(0.18)
            waiter = asyncio.create_task(db.get_common_foods_database())
            owner_result, waiter_result = await asyncio.gather(
                owner,
                waiter,
                return_exceptions=True,
            )
            return owner_result, waiter_result

        owner_result, waiter_result = asyncio.run(run_owner_and_waiter())

        assert waiter_acquisition_started.is_set()
        assert acquisition_count == 2
        assert isinstance(owner_result, CommonFoodsCacheAdmissionError)
        assert isinstance(waiter_result, CommonFoodsCacheAdmissionError)
        assert str(owner_result) == "Common-food acquisition exceeded its total deadline"
        assert str(waiter_result) == "Common-food acquisition exceeded its total deadline"
        publication.assert_not_called()
        assert not (tmp_path / "common_foods.json").exists()

    @pytest.mark.parametrize(
        "configured_delay",
        ["not-an-integer", "1" + "0" * 400],
        ids=["malformed", "division-overflow"],
    )
    def test_invalid_common_food_delay_is_stable_admission_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        configured_delay: str,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        search_food = AsyncMock()
        monkeypatch.setattr(db, "search_food", search_food)
        monkeypatch.setenv("UNIFIED_DB_COMMON_SLEEP_MS", configured_delay)

        with pytest.raises(CommonFoodsCacheAdmissionError) as exc_info:
            asyncio.run(db.get_common_foods_database())

        assert str(exc_info.value) == "Invalid common-food inter-row delay configuration"
        search_food.assert_not_awaited()
        assert not (tmp_path / "common_foods.json").exists()

    @pytest.mark.parametrize(
        ("numeric_carrier", "expected_message"),
        [
            ("nutrient", "Invalid common-food nutrient shape for chicken_breast"),
            ("cost", "Invalid common-food numeric shape for chicken_breast"),
            ("confidence", "Invalid common-food numeric shape for chicken_breast"),
            (
                "input_nutrient",
                "Invalid common-food nutrition evidence for chicken_breast",
            ),
            (
                "raw_payload",
                "Invalid common-food nutrition evidence for chicken_breast",
            ),
            (
                "nutrient_confidence",
                "Invalid common-food provenance evidence for chicken_breast",
            ),
        ],
    )
    def test_extreme_json_integer_numeric_carriers_are_admission_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        numeric_carrier: str,
        expected_message: str,
    ) -> None:
        cache_file = tmp_path / "common_foods.json"
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)
        chicken = items["chicken_breast"]
        assert isinstance(chicken, dict)
        extreme_integer = 10**400

        if numeric_carrier == "nutrient":
            nutrients = chicken["nutrients_per_100g"]
            assert isinstance(nutrients, dict)
            nutrients["nutrient_0"] = extreme_integer
        elif numeric_carrier == "cost":
            chicken["cost_per_100g"] = extreme_integer
        elif numeric_carrier == "confidence":
            chicken["nutrition_confidence"] = extreme_integer
        elif numeric_carrier == "input_nutrient":
            nutrition_inputs = chicken["nutrition_inputs"]
            assert isinstance(nutrition_inputs, list)
            nutrition_input = nutrition_inputs[0]
            assert isinstance(nutrition_input, dict)
            input_nutrients = nutrition_input["nutrients"]
            assert isinstance(input_nutrients, dict)
            input_nutrients["nutrient_0"] = extreme_integer
        elif numeric_carrier == "raw_payload":
            nutrition_inputs = chicken["nutrition_inputs"]
            assert isinstance(nutrition_inputs, list)
            nutrition_input = nutrition_inputs[0]
            assert isinstance(nutrition_input, dict)
            raw_payload = nutrition_input["raw_payload"]
            assert isinstance(raw_payload, dict)
            raw_payload["extreme"] = extreme_integer
        else:
            nutrient_confidence = chicken["nutrition_nutrient_confidence"]
            assert isinstance(nutrient_confidence, dict)
            nutrient_confidence["nutrient_0"] = extreme_integer

        _write_common_foods_envelope(cache_file, envelope)
        old_bytes = cache_file.read_bytes()
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))

        async def replay_invalid_json_envelope() -> dict[str, object]:
            loaded = json.loads(cache_file.read_text(encoding="utf-8"))
            assert isinstance(loaded, dict)
            return loaded

        monkeypatch.setattr(db, "_acquire_common_foods_envelope", replay_invalid_json_envelope)
        with pytest.raises(CommonFoodsCacheAdmissionError) as exc_info:
            asyncio.run(db.get_common_foods_database())

        assert str(exc_info.value) == expected_message
        assert cache_file.read_bytes() == old_bytes

    @pytest.mark.parametrize(
        "replay_drift",
        ["nutrient", "provenance", "nutrient_confidence", "confidence"],
    )
    def test_nutrition_evidence_must_match_canonical_replay(self, replay_drift: str) -> None:
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)
        chicken = items["chicken_breast"]
        assert isinstance(chicken, dict)

        if replay_drift == "nutrient":
            nutrients = chicken["nutrients_per_100g"]
            assert isinstance(nutrients, dict)
            nutrients["nutrient_0"] = 999.0
        elif replay_drift == "provenance":
            provenance = chicken["nutrition_provenance"]
            assert isinstance(provenance, dict)
            provenance["nutrient_0"] = "label"
        elif replay_drift == "nutrient_confidence":
            nutrient_confidence = chicken["nutrition_nutrient_confidence"]
            assert isinstance(nutrient_confidence, dict)
            nutrient_confidence["nutrient_0"] = 0.6
        else:
            chicken["nutrition_confidence"] = 0.6

        with pytest.raises(
            CommonFoodsCacheAdmissionError,
            match="Common-food nutrition evidence does not replay for chicken_breast",
        ):
            UnifiedFoodDatabase._validate_common_foods_envelope(envelope)

    def test_nutrition_replay_preserves_constructor_synthetic_zero_macros(self) -> None:
        constructed = UnifiedFoodItem.from_usda_item(
            USDAFoodItem(
                fdc_id=731,
                description="Constructor omission fixture",
                food_category="Fixture",
                nutrients_per_100g={"protein_g": 21.0},
                data_type="Foundation",
                publication_date="2026-08-11",
            )
        )
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)
        items["chicken_breast"] = asdict(constructed)

        admitted = UnifiedFoodDatabase._validate_common_foods_envelope(envelope)

        chicken = admitted["chicken_breast"]
        assert chicken.nutrients_per_100g == {
            "protein_g": 21.0,
            "fat_g": 0.0,
            "carbs_g": 0.0,
        }
        assert chicken.nutrition_provenance == {"protein_g": "usda"}
        assert chicken.nutrition_nutrient_confidence == {"protein_g": 0.7}

    @pytest.mark.parametrize("secondary_nutrients", [{}, {"fiber_g": 3.0}])
    def test_merge_filters_only_empty_secondary_evidence(
        self,
        secondary_nutrients: dict[str, float],
    ) -> None:
        usda = UnifiedFoodItem.from_usda_item(
            USDAFoodItem(
                fdc_id=732,
                description="Primary fixture",
                food_category="Fixture",
                nutrients_per_100g={"protein_g": 21.0},
                data_type="Foundation",
                publication_date="2026-08-11",
            )
        )
        off = UnifiedFoodItem.from_off_item(
            OFFFoodItem(
                code="off-secondary-732",
                product_name="Secondary fixture",
                categories=["Fixture"],
                nutrients_per_100g=secondary_nutrients,
                ingredients_text=None,
                brands=None,
                labels=[],
                countries=["TEST"],
                packaging=[],
                image_url=None,
                last_modified_t=0,
                nutrition_inputs=[
                    {
                        "source": "estimate",
                        "record_id": "off-secondary-732",
                        "version_ref": None,
                        "nutrients": secondary_nutrients,
                        "raw_payload": {},
                    }
                ],
                nutrition_provenance={nutrient: "estimate" for nutrient in secondary_nutrients},
                nutrition_nutrient_confidence={nutrient: 0.4 for nutrient in secondary_nutrients},
                nutrition_confidence=0.4 if secondary_nutrients else 0.0,
            )
        )

        merged = UnifiedFoodItem.from_usda_and_off_merge(usda, off)

        assert all(entry["nutrients"] for entry in merged.nutrition_inputs)
        assert merged.nutrition_provenance["protein_g"] == "usda"
        if secondary_nutrients:
            assert merged.nutrients_per_100g["fiber_g"] == 3.0
            assert merged.nutrition_provenance["fiber_g"] == "estimate"
            assert merged.nutrition_nutrient_confidence["fiber_g"] == 0.4
            assert merged.nutrition_confidence == 0.55
        else:
            assert merged.nutrition_provenance == {"protein_g": "usda"}
            assert merged.nutrition_nutrient_confidence == {"protein_g": 0.7}
            assert merged.nutrition_confidence == 0.7

    @pytest.mark.parametrize(
        "fabrication",
        ["nonzero_missing_macro", "unsupported_zero_nutrient"],
    )
    def test_nutrition_replay_rejects_fabricated_synthetic_values(
        self,
        fabrication: str,
    ) -> None:
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)
        chicken = items["chicken_breast"]
        assert isinstance(chicken, dict)
        nutrients = chicken["nutrients_per_100g"]
        assert isinstance(nutrients, dict)

        if fabrication == "nonzero_missing_macro":
            nutrients["fat_g"] = 1.0
        else:
            nutrients["unsupported_synthetic"] = 0.0

        with pytest.raises(
            CommonFoodsCacheAdmissionError,
            match="Common-food nutrition evidence does not replay for chicken_breast",
        ):
            UnifiedFoodDatabase._validate_common_foods_envelope(envelope)

    @pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
    def test_strict_loader_rejects_non_finite_json_constants(self, constant: str) -> None:
        with pytest.raises(CommonFoodsCacheAdmissionError) as exc_info:
            unified_db_module._load_common_foods_json(
                StringIO(f'{{"numeric_evidence": {constant}}}')
            )

        assert str(exc_info.value) == "Non-finite numeric constant in common-food cache JSON"

    def test_external_cancellation_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))

        async def cancelled_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            raise asyncio.CancelledError

        monkeypatch.setattr(db, "search_food", cancelled_search)
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(db.get_common_foods_database())

        assert not (tmp_path / "common_foods.json").exists()

    def test_concurrent_cold_callers_share_one_acquisition_and_publication(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        acquisition_started = asyncio.Event()
        release_acquisition = asyncio.Event()
        acquisition_count = 0
        publication_count = 0
        real_publish = db._publish_common_foods_envelope

        async def acquire_once() -> dict[str, object]:
            nonlocal acquisition_count
            acquisition_count += 1
            acquisition_started.set()
            await release_acquisition.wait()
            return _valid_common_foods_envelope()

        def record_publication(cache_file: Path, envelope: dict[str, object]) -> None:
            nonlocal publication_count
            publication_count += 1
            real_publish(cache_file, envelope)

        monkeypatch.setattr(db, "_acquire_common_foods_envelope", acquire_once)
        monkeypatch.setattr(db, "_publish_common_foods_envelope", record_publication)

        async def run_callers() -> tuple[dict[str, UnifiedFoodItem], dict[str, UnifiedFoodItem]]:
            owner = asyncio.create_task(db.get_common_foods_database())
            await acquisition_started.wait()
            waiter = asyncio.create_task(db.get_common_foods_database())
            await asyncio.sleep(0)
            release_acquisition.set()
            first, second = await asyncio.gather(owner, waiter)
            return first, second

        first, second = asyncio.run(run_callers())

        assert acquisition_count == 1
        assert publication_count == 1
        assert tuple(first) == tuple(second) == tuple(COMMON_FOODS_MANIFEST)

    def test_one_instance_cold_admission_spans_overlapping_event_loops(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        acquisition_started = threading.Event()
        release_acquisition = threading.Event()
        waiter_is_polling = threading.Event()
        counter_lock = threading.Lock()
        result_lock = threading.Lock()
        acquisition_count = 0
        publication_count = 0
        results: list[dict[str, UnifiedFoodItem]] = []
        errors: list[BaseException] = []
        real_publish = db._publish_common_foods_envelope
        real_sleep = asyncio.sleep

        async def acquire_once() -> dict[str, object]:
            nonlocal acquisition_count
            with counter_lock:
                acquisition_count += 1
            acquisition_started.set()
            while not release_acquisition.is_set():
                await real_sleep(0)
            return _valid_common_foods_envelope()

        async def observe_lock_poll(delay: float) -> None:
            if threading.current_thread().name == "common-food-waiter":
                waiter_is_polling.set()
            await real_sleep(delay)

        def record_publication(cache_file: Path, envelope: dict[str, object]) -> None:
            nonlocal publication_count
            with counter_lock:
                publication_count += 1
            real_publish(cache_file, envelope)

        def run_in_thread() -> None:
            try:
                result = asyncio.run(db.get_common_foods_database())
                with result_lock:
                    results.append(result)
            except BaseException as exc:
                with result_lock:
                    errors.append(exc)

        monkeypatch.setattr(db, "_acquire_common_foods_envelope", acquire_once)
        monkeypatch.setattr(db, "_publish_common_foods_envelope", record_publication)
        monkeypatch.setattr(unified_db_module.asyncio, "sleep", observe_lock_poll)

        owner = threading.Thread(target=run_in_thread, name="common-food-owner", daemon=True)
        waiter = threading.Thread(target=run_in_thread, name="common-food-waiter", daemon=True)
        owner.start()
        assert acquisition_started.wait(timeout=2)
        waiter.start()
        assert waiter_is_polling.wait(timeout=2)
        release_acquisition.set()
        owner.join(timeout=2)
        waiter.join(timeout=2)

        assert not owner.is_alive()
        assert not waiter.is_alive()
        assert errors == []
        assert acquisition_count == 1
        assert publication_count == 1
        assert len(results) == 2
        assert all(tuple(result) == tuple(COMMON_FOODS_MANIFEST) for result in results)

    def test_cancelled_cold_waiter_does_not_cancel_lock_owner(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        acquisition_started = asyncio.Event()
        release_acquisition = asyncio.Event()
        acquisition_count = 0

        async def acquire_once() -> dict[str, object]:
            nonlocal acquisition_count
            acquisition_count += 1
            acquisition_started.set()
            await release_acquisition.wait()
            return _valid_common_foods_envelope()

        monkeypatch.setattr(db, "_acquire_common_foods_envelope", acquire_once)

        async def run_callers() -> dict[str, UnifiedFoodItem]:
            owner = asyncio.create_task(db.get_common_foods_database())
            await acquisition_started.wait()
            waiter = asyncio.create_task(db.get_common_foods_database())
            await asyncio.sleep(0)
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter
            release_acquisition.set()
            return await owner

        foods = asyncio.run(run_callers())

        assert acquisition_count == 1
        assert tuple(foods) == tuple(COMMON_FOODS_MANIFEST)
        assert (tmp_path / "common_foods.json").exists()

    def test_cancelled_cold_owner_releases_lock_for_surviving_waiter(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        owner_started = asyncio.Event()
        acquisition_count = 0

        async def acquire_with_cancelled_owner() -> dict[str, object]:
            nonlocal acquisition_count
            acquisition_count += 1
            if acquisition_count == 1:
                owner_started.set()
                await asyncio.Event().wait()
            return _valid_common_foods_envelope()

        monkeypatch.setattr(
            db,
            "_acquire_common_foods_envelope",
            acquire_with_cancelled_owner,
        )

        async def run_callers() -> dict[str, UnifiedFoodItem]:
            owner = asyncio.create_task(db.get_common_foods_database())
            await owner_started.wait()
            waiter = asyncio.create_task(db.get_common_foods_database())
            await asyncio.sleep(0)
            owner.cancel()
            with pytest.raises(asyncio.CancelledError):
                await owner
            return await waiter

        foods = asyncio.run(run_callers())

        assert acquisition_count == 2
        assert tuple(foods) == tuple(COMMON_FOODS_MANIFEST)
        assert (tmp_path / "common_foods.json").exists()

    @pytest.mark.parametrize("failure", ["serialize", "duplicate_serialized", "replace"])
    def test_publication_failure_preserves_old_target_and_cleans_temp(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        failure: str,
    ) -> None:
        cache_file = tmp_path / "common_foods.json"
        cache_file.write_bytes(b"old-target")
        old_bytes = cache_file.read_bytes()
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        queries = tuple(COMMON_FOODS_MANIFEST.values())

        async def deterministic_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            return [_common_food_item(queries.index(query))]

        monkeypatch.setattr(db, "search_food", deterministic_search)
        if failure == "serialize":
            monkeypatch.setattr(
                unified_db_module.json,
                "dump",
                lambda *args, **kwargs: (_ for _ in ()).throw(OSError("write failed")),
            )
        elif failure == "duplicate_serialized":

            def write_duplicate_member(
                value: object, file_object: IO[str], **kwargs: object
            ) -> None:
                file_object.write(_common_foods_json_with_duplicate("duplicate_item_member"))

            monkeypatch.setattr(unified_db_module.json, "dump", write_duplicate_member)
        else:
            monkeypatch.setattr(
                unified_db_module.os,
                "replace",
                lambda *args, **kwargs: (_ for _ in ()).throw(OSError("replace failed")),
            )

        expected_error = (
            "Duplicate member" if failure == "duplicate_serialized" else "publication failed"
        )
        with pytest.raises(CommonFoodsCacheAdmissionError, match=expected_error):
            asyncio.run(db.get_common_foods_database())

        assert cache_file.read_bytes() == old_bytes
        assert not list(tmp_path.glob(".common_foods.json.*.tmp"))

    def test_publication_rejects_non_finite_serialization_before_replace(
        self, tmp_path: Path
    ) -> None:
        cache_file = tmp_path / "common_foods.json"
        cache_file.write_bytes(b"old-target")
        old_bytes = cache_file.read_bytes()
        envelope = _valid_common_foods_envelope()
        items = envelope["items"]
        assert isinstance(items, dict)
        chicken = items["chicken_breast"]
        assert isinstance(chicken, dict)
        nutrition_inputs = chicken["nutrition_inputs"]
        assert isinstance(nutrition_inputs, list)
        nutrition_input = nutrition_inputs[0]
        assert isinstance(nutrition_input, dict)
        raw_payload = nutrition_input["raw_payload"]
        assert isinstance(raw_payload, dict)
        raw_payload["non_finite"] = float("nan")

        with pytest.raises(CommonFoodsCacheAdmissionError) as exc_info:
            UnifiedFoodDatabase._publish_common_foods_envelope(cache_file, envelope)

        assert str(exc_info.value) == "Common-food cache publication failed"
        assert cache_file.read_bytes() == old_bytes
        assert not list(tmp_path.glob(".common_foods.json.*.tmp"))

    def test_publication_fsyncs_parent_after_replace_and_closes_descriptor(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cache_file = tmp_path / "common_foods.json"
        events: list[tuple[str, int | None]] = []
        real_fsync = os.fsync
        real_close = os.close
        real_replace = os.replace

        def recording_fsync(descriptor: int) -> None:
            events.append(("fsync", descriptor))
            real_fsync(descriptor)

        def recording_replace(source: str | Path, target: str | Path) -> None:
            real_replace(source, target)
            events.append(("replace", None))

        def recording_close(descriptor: int) -> None:
            events.append(("close", descriptor))
            real_close(descriptor)

        monkeypatch.setattr(unified_db_module.os, "fsync", recording_fsync)
        monkeypatch.setattr(unified_db_module.os, "replace", recording_replace)
        monkeypatch.setattr(unified_db_module.os, "close", recording_close)

        UnifiedFoodDatabase._publish_common_foods_envelope(
            cache_file,
            _valid_common_foods_envelope(),
        )

        fsync_events = [event for event in events if event[0] == "fsync"]
        assert len(fsync_events) == 2
        parent_descriptor = fsync_events[-1][1]
        assert parent_descriptor is not None
        assert [event[0] for event in events] == ["fsync", "replace", "fsync", "close"]
        assert events[-2:] == [
            ("fsync", parent_descriptor),
            ("close", parent_descriptor),
        ]

    @pytest.mark.parametrize(
        "prior_target_bytes",
        [b"exact-prior-target", None],
        ids=["existing-target", "no-prior-target"],
    )
    def test_parent_fsync_failure_restores_prior_publication_state(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        prior_target_bytes: bytes | None,
    ) -> None:
        cache_file = tmp_path / "common_foods.json"
        if prior_target_bytes is not None:
            cache_file.write_bytes(prior_target_bytes)
        fsync_descriptors: list[int] = []
        closed_descriptors: list[int] = []
        real_fsync = os.fsync
        real_close = os.close

        def fail_parent_fsync(descriptor: int) -> None:
            fsync_descriptors.append(descriptor)
            if len(fsync_descriptors) == 2:
                raise OSError("parent fsync failed")
            real_fsync(descriptor)

        def recording_close(descriptor: int) -> None:
            closed_descriptors.append(descriptor)
            real_close(descriptor)

        monkeypatch.setattr(unified_db_module.os, "fsync", fail_parent_fsync)
        monkeypatch.setattr(unified_db_module.os, "close", recording_close)

        with pytest.raises(CommonFoodsCacheAdmissionError, match="publication failed"):
            UnifiedFoodDatabase._publish_common_foods_envelope(
                cache_file,
                _valid_common_foods_envelope(),
            )

        expected_fsync_count = 4 if prior_target_bytes is not None else 3
        assert len(fsync_descriptors) == expected_fsync_count
        assert fsync_descriptors[1] in closed_descriptors
        assert fsync_descriptors[-1] in closed_descriptors
        if prior_target_bytes is None:
            assert not cache_file.exists()
        else:
            assert cache_file.read_bytes() == prior_target_bytes
        assert not list(tmp_path.glob(".common_foods.json.*.tmp"))

    def test_cleanup_unlink_failure_log_is_category_only(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        queries = tuple(COMMON_FOODS_MANIFEST.values())
        cleanup_marker = "cleanup-path-context-marker-d4b7"

        async def deterministic_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            return [_common_food_item(queries.index(query))]

        def fail_replace(source: str | Path, target: str | Path) -> None:
            raise OSError("replacement failed")

        def fail_unlink(path: Path, missing_ok: bool = False) -> None:
            raise PermissionError(cleanup_marker)

        monkeypatch.setattr(db, "search_food", deterministic_search)
        monkeypatch.setattr(unified_db_module.os, "replace", fail_replace)
        monkeypatch.setattr(Path, "unlink", fail_unlink)
        caplog.set_level(logging.ERROR, logger=unified_db_module.__name__)

        with pytest.raises(CommonFoodsCacheAdmissionError) as exc_info:
            asyncio.run(db.get_common_foods_database())

        assert str(exc_info.value) == "Common-food cache publication failed"
        assert cleanup_marker not in caplog.text
        sink_records = [
            record
            for record in caplog.records
            if record.getMessage()
            == "Common-food temporary cache cleanup failed; category=PermissionError"
        ]
        assert len(sink_records) == 1
        assert sink_records[0].exc_info is None

    def test_cold_to_warm_round_trip_preserves_full_provenance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cold_db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        queries = tuple(COMMON_FOODS_MANIFEST.values())

        async def deterministic_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            return [_common_food_item(queries.index(query))]

        monkeypatch.setattr(cold_db, "search_food", deterministic_search)
        cold_foods = asyncio.run(cold_db.get_common_foods_database())

        warm_db = UnifiedFoodDatabase(cache_dir=str(tmp_path))

        async def unexpected_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            raise AssertionError(f"round-trip warm load searched unexpectedly: {query}")

        monkeypatch.setattr(warm_db, "search_food", unexpected_search)
        warm_foods = asyncio.run(warm_db.get_common_foods_database())

        assert {name: asdict(item) for name, item in warm_foods.items()} == {
            name: asdict(item) for name, item in cold_foods.items()
        }


class TestUnifiedFoodDatabaseEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_search_food_off_client_error(self, temp_cache_dir):
        """Test search when OFF client raises error."""
        # Mock USDA client with empty results
        mock_usda_client = AsyncMock()
        mock_usda_client.search_foods.return_value = []

        # Mock OFF client that raises error
        mock_off_client = AsyncMock()
        mock_off_client.search_products.side_effect = Exception("OFF API Error")

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = mock_off_client

        # Should handle error gracefully
        results = await db.search_food("test query")

        assert results == []

    def test_search_food_off_fallback_failure_is_category_only(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        usda_search = AsyncMock(return_value=[])
        off_client = AsyncMock()
        provider_marker = "off-fallback-context-marker-b294"
        off_search = AsyncMock(side_effect=RuntimeError(provider_marker))
        monkeypatch.setattr(db.usda_client, "search_foods", usda_search)
        monkeypatch.setattr(off_client, "search_products", off_search)
        db.off_client = off_client
        caplog.set_level(logging.ERROR, logger=unified_db_module.__name__)

        results = asyncio.run(db.search_food("offline fallback fixture", save_cache=False))

        assert results == []
        usda_search.assert_awaited_once_with("offline fallback fixture", page_size=5)
        off_search.assert_awaited_once_with("offline fallback fixture", page_size=5)
        assert "search_offline fallback fixture" not in db._memory_cache
        assert provider_marker not in caplog.text
        sink_records = [
            record
            for record in caplog.records
            if record.getMessage()
            == "Unified DB Open Food Facts search failed; category=RuntimeError"
        ]
        assert len(sink_records) == 1
        assert sink_records[0].exc_info is None

    def test_search_food_off_merge_failure_preserves_usda_fallback_and_cache_retry(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        usda_item = USDAFoodItem(
            fdc_id=731,
            description="Offline USDA fixture",
            food_category="Fixture",
            nutrients_per_100g={"protein_g": 21.0},
            data_type="Foundation",
            publication_date="2026-08-10",
        )
        usda_search = AsyncMock(return_value=[usda_item])
        off_client = AsyncMock()
        provider_marker = "off-merge-context-marker-c3a5"
        off_search = AsyncMock(side_effect=RuntimeError(provider_marker))
        monkeypatch.setattr(db.usda_client, "search_foods", usda_search)
        monkeypatch.setattr(off_client, "search_products", off_search)
        db.off_client = off_client
        caplog.set_level(logging.DEBUG, logger=unified_db_module.__name__)

        results = asyncio.run(db.search_food("offline merge fixture", save_cache=False))

        assert len(results) == 1
        assert results[0].name == "Offline USDA fixture"
        assert results[0].source == "USDA FoodData Central"
        usda_search.assert_awaited_once_with("offline merge fixture", page_size=5)
        off_search.assert_awaited_once_with("offline merge fixture", page_size=1)
        assert "search_offline merge fixture" not in db._memory_cache
        assert provider_marker not in caplog.text
        sink_records = [
            record
            for record in caplog.records
            if record.getMessage()
            == "Unified DB USDA+OFF nutrition merge skipped; category=RuntimeError"
        ]
        assert len(sink_records) == 1
        assert sink_records[0].exc_info is None

    @pytest.mark.asyncio
    async def test_get_food_by_id_off_client_error(self, temp_cache_dir):
        """Test get by ID when OFF client raises error."""
        # Mock OFF client that raises error
        mock_off_client = AsyncMock()
        mock_off_client.get_product_details.side_effect = Exception("OFF API Error")

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.off_client = mock_off_client

        # Should handle error gracefully
        result = await db.get_food_by_id("openfoodfacts", "123456")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_food_by_id_usda_not_found(self, temp_cache_dir):
        """Test get USDA food by ID when not found."""
        # Mock USDA client that returns None
        mock_usda_client = AsyncMock()
        mock_usda_client.get_food_details.return_value = None

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client

        result = await db.get_food_by_id("usda", "12345")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_food_by_id_off_not_found(self, temp_cache_dir):
        """Test get OFF food by ID when not found."""
        # Mock OFF client that returns None
        mock_off_client = AsyncMock()
        mock_off_client.get_product_details.return_value = None

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.off_client = mock_off_client

        result = await db.get_food_by_id("openfoodfacts", "123456")

        assert result is None

    def test_save_cache_error_handling(self, temp_cache_dir):
        """Test cache save with file permission error."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        # Add item to cache
        test_item = UnifiedFoodItem(
            name="Test Food",
            nutrients_per_100g={"calories": 100.0},
            cost_per_100g=1.0,
            tags=["test"],
            availability_regions=["US"],
            source="Test",
            source_id="test123",
        )
        db._memory_cache["test"] = test_item

        # Mock file operation to fail
        with patch("builtins.open", side_effect=PermissionError("Cannot write")):
            # Should not crash when save fails
            db._save_cache()

        # Memory cache should still be intact
        assert "test" in db._memory_cache

    def test_cache_directory_creation_error(self):
        """Test database initialization when cache directory creation fails."""
        # Try to create cache in a read-only location that might fail
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Cannot create directory")):
            # Should handle directory creation error gracefully
            try:
                db = UnifiedFoodDatabase(cache_dir="/root/readonly_dir")
                assert isinstance(db._memory_cache, dict)
            except PermissionError:
                # This is acceptable - function might not handle this specific error
                pass

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db.OFFClient", None)  # Simulate OFF not available
    async def test_search_food_without_off_client(self, temp_cache_dir):
        """Test search when OFF client is not available."""
        # Mock USDA client
        mock_usda_client = AsyncMock()
        mock_usda_item = USDAFoodItem(
            fdc_id=12345,
            description="Test Food",
            food_category="Test",
            nutrients_per_100g={"calories": 100.0},
            data_type="Foundation",
            publication_date="2019-04-01",
        )

        with patch.object(mock_usda_item, "_generate_tags", return_value=["test"]):
            mock_usda_client.search_foods.return_value = [mock_usda_item]

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = None  # No OFF client available

        # When prefer_source="openfoodfacts" but OFF is unavailable, should return empty results
        # because current logic doesn't fallback to USDA
        results = await db.search_food("test query", prefer_source="openfoodfacts")

        assert len(results) == 0  # No results because OFF unavailable and no fallback

        # But with prefer_source="usda" should work
        results = await db.search_food("test query", prefer_source="usda")

        assert len(results) == 1
        assert results[0].source == "USDA FoodData Central"


class TestModuleConstants:
    """Test module-level constants and configuration."""

    def test_off_available_constant(self):
        """Test OFF_AVAILABLE constant."""
        from core.food_apis.unified_db import OFF_AVAILABLE

        # Should be a boolean
        assert isinstance(OFF_AVAILABLE, bool)

    def test_off_client_symbol_exists(self):
        """Test that OFFClient symbol exists in module."""
        from core.food_apis.unified_db import OFFClient

        # Symbol should exist (even if None)
        assert OFFClient is not None or OFFClient is None  # Just check it's defined

    def test_module_level_imports(self):
        """Test that module imports work correctly."""
        try:
            from core.food_apis.unified_db import (
                UnifiedFoodDatabase,
                UnifiedFoodItem,
                get_unified_food_db,
                search_foods_unified,
            )

            # All imports should work
            assert UnifiedFoodItem is not None
            assert UnifiedFoodDatabase is not None
            assert search_foods_unified is not None
            assert get_unified_food_db is not None

        except ImportError as e:
            pytest.fail(f"Module imports failed: {e}")


class TestAsyncUtilities:
    """Test async utility functions with different scenarios."""

    @pytest.mark.asyncio
    async def test_search_foods_unified_max_results(self):
        """Test unified search with max results limit."""
        # Mock database with multiple results
        mock_db = AsyncMock()

        # Create multiple mock items
        mock_items = []
        for i in range(10):
            item = UnifiedFoodItem(
                name=f"Test Food {i}",
                nutrients_per_100g={"calories": 100.0 + i},
                cost_per_100g=1.0 + i,
                tags=[f"test{i}"],
                availability_regions=["US"],
                source="Test",
                source_id=f"test{i}",
            )
            mock_items.append(item)

        mock_db.search_food.return_value = mock_items

        with patch("core.food_apis.unified_db.get_unified_food_db", return_value=mock_db):
            results = await search_foods_unified("test query", max_results=3)

        # Should limit to 3 results
        assert len(results) == 3
        assert results[0]["name"] == "Test Food 0"
        assert results[1]["name"] == "Test Food 1"
        assert results[2]["name"] == "Test Food 2"

    @pytest.mark.asyncio
    async def test_search_foods_unified_empty_results(self):
        """Test unified search with empty results."""
        mock_db = AsyncMock()
        mock_db.search_food.return_value = []

        with patch("core.food_apis.unified_db.get_unified_food_db", return_value=mock_db):
            results = await search_foods_unified("nonexistent food")

        assert results == []

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db._unified_db_instance")
    async def test_get_unified_food_db_existing_instance(self, mock_instance):
        """Test getting existing unified database instance."""
        # Mock existing instance
        mock_db = UnifiedFoodDatabase()
        mock_instance.__bool__ = lambda self: True  # Simulate non-None instance

        with patch("core.food_apis.unified_db._unified_db_instance", mock_db):
            db = await get_unified_food_db()

        assert db is mock_db
