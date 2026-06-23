from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.orchestration import creative_code_contract
from scripts.orchestration.creative_code_contract import (
    AUTHORITY_FALSE_KEYS,
    CreativeCodeContractError,
    read_creative_code_candidate_packet,
    validate_creative_code_candidate_packet,
)
from scripts.orchestration.experiment_contract import validate_mutable_candidate_surface

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = REPO_ROOT / "docs/orchestration/contracts/creative_code_candidate.v1.json"
SCHEMA = REPO_ROOT / "docs/orchestration/contracts/creative_code_candidate.v1.schema.json"


def _reference_packet() -> dict[str, object]:
    return read_creative_code_candidate_packet(REFERENCE)


def _valid_packet() -> dict[str, object]:
    return deepcopy(_reference_packet())


def test_reference_packet_and_schema_are_valid() -> None:
    packet = _reference_packet()
    normalized = validate_creative_code_candidate_packet(packet)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert normalized["schema_version"] == "1.0"
    assert normalized["gate_status"] == "closed"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["authority"]["additionalProperties"] is False
    assert schema["properties"]["source_creative_research"]["additionalProperties"] is False
    assert (
        schema["properties"]["authority"]["properties"]["generate_candidate_patch"]["const"]
        is False
    )
    assert schema["properties"]["authority"]["properties"]["open_draft_pr"]["const"] is False
    assert schema["properties"]["variant_count"]["minimum"] == 3
    assert schema["properties"]["variant_count"]["maximum"] == 5


def test_cli_valid_reference_packet_outputs_exact_pass(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = creative_code_contract.main(["--validate", str(REFERENCE)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "PASS: creative-code candidate contract valid"
    assert captured.err == ""


def test_cli_reports_one_fail_line_for_duplicate_json_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    duplicate_key_packet = tmp_path / "creative-code.json"
    duplicate_key_packet.write_text(
        '{"schema_version":"1.0","schema_version":"1.0"}',
        encoding="utf-8",
    )

    exit_code = creative_code_contract.main(["--validate", str(duplicate_key_packet)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.count("\n") == 1
    assert captured.err.startswith(
        "FAIL: creative-code candidate contract has duplicate JSON key: schema_version"
    )


@pytest.mark.parametrize(
    "packet_path",
    [
        Path("missing.json"),
        Path("nested") / "missing.json",
    ],
)
def test_cli_reports_missing_file_failures_on_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    packet_path: Path,
) -> None:
    exit_code = creative_code_contract.main(["--validate", str(tmp_path / packet_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "FAIL: Unable to read creative-code candidate contract JSON.\n"


def test_cli_reports_malformed_json_failures_on_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    malformed_packet = tmp_path / "malformed.json"
    malformed_packet.write_text('{"schema_version": ', encoding="utf-8")

    exit_code = creative_code_contract.main(["--validate", str(malformed_packet)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "FAIL: Unable to read creative-code candidate contract JSON.\n"


def test_source_must_be_promoted_creative_research() -> None:
    packet = _valid_packet()
    source = packet["source_creative_research"]
    assert isinstance(source, dict)
    source["promotion_decision"] = "defer"

    with pytest.raises(
        CreativeCodeContractError,
        match="source_creative_research.promotion_decision must equal 'promote'",
    ):
        validate_creative_code_candidate_packet(packet)


@pytest.mark.parametrize("promotion_decision", ["PROMOTE", "Promote", " promote "])
def test_source_promotion_decision_must_match_schema_exactly(
    promotion_decision: str,
) -> None:
    packet = _valid_packet()
    source = packet["source_creative_research"]
    assert isinstance(source, dict)
    source["promotion_decision"] = promotion_decision

    with pytest.raises(
        CreativeCodeContractError,
        match="source_creative_research.promotion_decision must equal 'promote'",
    ):
        validate_creative_code_candidate_packet(packet)


@pytest.mark.parametrize("variant_count", [3, 4, 5])
def test_variant_count_accepts_only_three_to_five(variant_count: int) -> None:
    packet = _valid_packet()
    packet["variant_count"] = variant_count

    normalized = validate_creative_code_candidate_packet(packet)

    assert normalized["variant_count"] == variant_count


@pytest.mark.parametrize("variant_count", [2, 6])
def test_variant_count_bounds_fail_closed(variant_count: int) -> None:
    packet = _valid_packet()
    packet["variant_count"] = variant_count

    with pytest.raises(CreativeCodeContractError, match="variant_count must be between 3 and 5"):
        validate_creative_code_candidate_packet(packet)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sandbox_required", False, "sandbox_required must be true"),
        ("human_review_required", False, "human_review_required must be true"),
    ],
)
def test_sandbox_and_human_review_are_required(field: str, value: bool, message: str) -> None:
    packet = _valid_packet()
    packet[field] = value

    with pytest.raises(CreativeCodeContractError, match=message):
        validate_creative_code_candidate_packet(packet)


def test_mutable_surface_validator_is_reused(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def recorder(paths: list[str] | tuple[str, ...]) -> list[str]:
        calls.append(tuple(paths))
        return validate_mutable_candidate_surface(paths)

    monkeypatch.setattr(creative_code_contract, "validate_mutable_candidate_surface", recorder)

    validate_creative_code_candidate_packet(_valid_packet())

    assert calls == [("core/rag/orchestration.py",)]


@pytest.mark.parametrize("authority_key", AUTHORITY_FALSE_KEYS)
def test_authority_flags_fail_closed(authority_key: str) -> None:
    packet = _valid_packet()
    authority = packet["authority"]
    assert isinstance(authority, dict)
    authority[authority_key] = True

    with pytest.raises(
        CreativeCodeContractError,
        match=f"authority.{authority_key} must remain false in PR-0",
    ):
        validate_creative_code_candidate_packet(packet)


def test_generate_specifications_must_remain_true() -> None:
    packet = _valid_packet()
    authority = packet["authority"]
    assert isinstance(authority, dict)
    authority["generate_specifications"] = False

    with pytest.raises(
        CreativeCodeContractError,
        match="authority.generate_specifications must remain true in PR-0",
    ):
        validate_creative_code_candidate_packet(packet)


def test_bool_like_strings_do_not_satisfy_authority_flags() -> None:
    packet = _valid_packet()
    authority = packet["authority"]
    assert isinstance(authority, dict)
    authority["write_shared_worktree"] = "false"

    with pytest.raises(
        CreativeCodeContractError,
        match="authority.write_shared_worktree must remain false in PR-0",
    ):
        validate_creative_code_candidate_packet(packet)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("target_surface", ["/tmp/candidate.py"], "must be repo-relative"),
        ("target_surface", ["../core/rag/orchestration.py"], "must not contain traversal"),
        ("immutable_oracles", ["https://example.invalid/oracle.json"], "must not be a URL"),
        ("immutable_oracles", ["artifacts/orchestration/result.json"], "forbidden local surface"),
    ],
)
def test_path_guards_fail_closed(field: str, value: list[str], message: str) -> None:
    packet = _valid_packet()
    packet[field] = value

    with pytest.raises(CreativeCodeContractError, match=message):
        validate_creative_code_candidate_packet(packet)


def test_target_surface_must_not_overlap_oracles() -> None:
    packet = _valid_packet()
    packet["immutable_oracles"] = ["core/rag/orchestration.py"]

    with pytest.raises(
        CreativeCodeContractError,
        match="target_surface must not overlap immutable_oracles",
    ):
        validate_creative_code_candidate_packet(packet)


def test_unknown_fields_fail_closed() -> None:
    packet = _valid_packet()
    packet["unexpected"] = "authority-expansion"

    with pytest.raises(CreativeCodeContractError, match="unsupported fields: unexpected"):
        validate_creative_code_candidate_packet(packet)


def test_nested_unknown_fields_fail_closed() -> None:
    packet = _valid_packet()
    source = packet["source_creative_research"]
    assert isinstance(source, dict)
    source["unexpected"] = "verified-discovery"

    with pytest.raises(CreativeCodeContractError, match="unsupported fields: unexpected"):
        validate_creative_code_candidate_packet(packet)


def test_missing_fallback_fails_closed() -> None:
    packet = _valid_packet()
    packet.pop("fallback")

    with pytest.raises(CreativeCodeContractError, match="missing required fields: fallback"):
        validate_creative_code_candidate_packet(packet)


def test_verified_discovery_overclaim_is_rejected() -> None:
    packet = _valid_packet()
    packet["scientific_claim_status"] = "verified_discovery"

    with pytest.raises(
        CreativeCodeContractError,
        match="scientific_claim_status must not overclaim verified discovery",
    ):
        validate_creative_code_candidate_packet(packet)


def test_future_telemetry_is_defined_but_not_emitted_before_pr1() -> None:
    packet = _valid_packet()
    telemetry = packet["future_telemetry_contract"]
    assert isinstance(telemetry, dict)

    normalized = validate_creative_code_candidate_packet(packet)

    assert normalized["future_telemetry_contract"]["emit_no_earlier_than"] == "PR-1"
    assert set(normalized["future_telemetry_contract"]["minimum_fields"]) == set(
        creative_code_contract.FUTURE_TELEMETRY_FIELDS
    )
