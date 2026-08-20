from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import re
import stat
from types import SimpleNamespace
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_lifecycle_bayesian_shadow as shadow_cli
from scripts.orchestration import (
    creative_code_lifecycle_bayesian_shadow_contract as shadow_contract,
)
from scripts.orchestration import creative_code_lifecycle_transition_analytics as analytics_cli
from scripts.orchestration import creative_code_patch_builder
from scripts.orchestration import creative_code_patch_generation as generation_cli
from scripts.orchestration.creative_code_lifecycle_bayesian_shadow_contract import (
    AUTHORITY_KEYS,
    FAMILY_IDS,
    FORECAST_KEYS,
    SCORE_KEYS,
    START_KEYS,
    CreativeCodeLifecycleBayesianShadowError,
    assert_no_shadow_slot,
    build_lifecycle_forecast,
    build_lifecycle_forecast_score,
    build_target_start,
    canonical_shadow_bytes,
    normalize_rfc3339,
    publish_shadow_artifact,
    publish_target_start_from_forecast,
    read_shadow_json,
    round_half_up_ratio,
    validate_lifecycle_forecast,
    validate_lifecycle_forecast_score,
    validate_target_start,
    validate_target_start_binding,
)
from scripts.orchestration.creative_code_lifecycle_transition_analytics_contract import (
    build_creative_code_lifecycle_transition_analytics,
)
from scripts.orchestration.creative_code_telemetry_contract import (
    build_creative_code_telemetry_rollup_v2,
)
from scripts.orchestration.creative_code_lifecycle_bayesian_shadow import (
    _target_outcomes,
)
from tests.test_creative_code_lifecycle_transition_analytics import (
    _full_chain,
    _legacy_event,
    _terminal_event,
)
from tests.test_creative_code_patch_generation import (
    _mock_successful_builder_edges,
    _patch_modules_to_repo,
    _prepare_admission,
    _write_gate,
)
from tests.test_creative_spec_patch_admission import _init_patch_repo


def _analytics() -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    rollup = build_creative_code_telemetry_rollup_v2(
        events,
        input_roots=["patch_runs", "promotions", "spec_runs", "terminal_outcomes"],
    )
    return build_creative_code_lifecycle_transition_analytics(
        events,
        telemetry_rollup=rollup,
    )


def _gate() -> dict[str, Any]:
    return {
        "gate_id": "evidence:creative_code_patch_generation_gate:control_plane:1.0:aaaaaaaaaaaaaaaaaaaaaaaa",
        "admission_id": "admission-one",
        "admission_fingerprint": "sha256:" + "1" * 64,
        "admission_ref": "artifacts/orchestration/creative_code/patch_admission/one/admission.json",
        "request_id": "request-one",
        "request_fingerprint": "sha256:" + "2" * 64,
        "request_ref": "artifacts/orchestration/creative_code/patch_admission/one/request.json",
        "source_bundle_id": "bundle-one",
        "source_bundle_fingerprint": "sha256:" + "3" * 64,
        "source_bundle_ref": "artifacts/orchestration/creative_code/spec_runs/one/bundle.json",
        "selected_variant_id": "variant-one",
        "selected_variant_fingerprint": "sha256:" + "4" * 64,
        "base_commit_sha": "a" * 40,
        "run_id": "run-one",
        "state_fingerprint": "sha256:" + "5" * 64,
    }


def _forecast(
    *,
    analytics: dict[str, Any] | None = None,
    produced_at: str = "2026-08-17T10:00:00+00:00",
) -> dict[str, Any]:
    analytics = _analytics() if analytics is None else analytics
    gate = _gate()
    return build_lifecycle_forecast(
        analytics=analytics,
        analytics_ref=(
            "artifacts/orchestration/creative_code/lifecycle_transition_analytics/"
            f"{analytics['analytics_id']}/analytics.json"
        ),
        telemetry_dir_ref="artifacts/orchestration/creative_code/telemetry/baseline-one",
        gate=gate,
        gate_ref=(
            "artifacts/orchestration/creative_code/patch_generation/run-one/" "generation_gate.json"
        ),
        produced_at=produced_at,
    )


def _empty_observation(analytics: dict[str, Any] | None = None) -> dict[str, Any]:
    analytics = _analytics() if analytics is None else analytics
    return {
        "analytics_id": analytics["analytics_id"],
        "analytics_fingerprint": fingerprint_payload(analytics),
        "analytics_ref": (
            "artifacts/orchestration/creative_code/lifecycle_transition_analytics/"
            f"{analytics['analytics_id']}/analytics.json"
        ),
        "telemetry_dir_ref": "artifacts/orchestration/creative_code/telemetry/outcome-one",
        "events_fingerprint": analytics["corpus"]["events_fingerprint"],
        "rollup_fingerprint": analytics["corpus"]["rollup_fingerprint"],
        "event_count": analytics["corpus"]["event_count"],
        "target_event_fingerprints": [],
        "generation_receipt_ref": None,
        "generation_receipt_fingerprint": None,
        "result_id": None,
        "result_fingerprint": None,
        "promotion_id": None,
    }


def _start_for_forecast(forecast: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    forecast_ref = (
        "artifacts/orchestration/creative_code/bayesian_shadow/"
        f"{forecast['forecast_id']}/forecast.json"
    )
    return forecast_ref, build_target_start(
        forecast=forecast,
        forecast_ref=forecast_ref,
        gate=_gate(),
        gate_ref=forecast["target"]["generation_gate_ref"],
        started_at="2026-08-17T10:01:00Z",
    )


def _write_frozen_snapshot(directory: Path, events: list[dict[str, Any]]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    event_lines = [json.dumps(event, sort_keys=True) for event in events]
    (directory / analytics_cli.EVENTS_FILE).write_text(
        "\n".join(event_lines) + ("\n" if event_lines else ""),
        encoding="utf-8",
    )
    rollup = build_creative_code_telemetry_rollup_v2(
        events,
        input_roots=["patch_runs", "promotions", "spec_runs", "terminal_outcomes"],
    )
    (directory / analytics_cli.ROLLUP_FILE).write_text(
        json.dumps(rollup, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _prepare_generation_forecast(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    run_id: str,
) -> tuple[Path, Path, dict[str, Any], dict[str, Any], Path, Path]:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    _resolved_gate, gate = generation_cli.load_stored_generation_gate(gate_path)
    analytics = _analytics()
    gate_ref = gate_path.relative_to(repo).as_posix()
    forecast = build_lifecycle_forecast(
        analytics=analytics,
        analytics_ref=(
            "artifacts/orchestration/creative_code/lifecycle_transition_analytics/"
            f"{analytics['analytics_id']}/analytics.json"
        ),
        telemetry_dir_ref="artifacts/orchestration/creative_code/telemetry/baseline-one",
        gate=gate,
        gate_ref=gate_ref,
        produced_at="2026-08-17T10:00:00Z",
    )
    shadow_root = repo / "artifacts" / "orchestration" / "creative_code" / "bayesian_shadow"
    forecast_path, replayed = publish_shadow_artifact(
        shadow_root=shadow_root,
        forecast_id=forecast["forecast_id"],
        filename="forecast.json",
        content=canonical_shadow_bytes(forecast),
        recheck_sources=lambda: None,
    )
    assert replayed is False
    return repo, gate_path, gate, forecast, forecast_path, shadow_root


def test_zero_corpus_forecast_is_fixed_prior_only_for_three_families() -> None:
    forecast = validate_lifecycle_forecast(_forecast())

    assert tuple(row["family_id"] for row in forecast["families"]) == FAMILY_IDS
    assert len(forecast["families"]) == 3
    for row in forecast["families"]:
        assert row["positive_outcome_count"] == 0
        assert row["negative_outcome_count"] == 0
        assert row["effective_observation_count"] == 0
        assert row["posterior_alpha"] == 1
        assert row["posterior_beta"] == 1
        assert row["posterior_predictive_bps"] == 5000
        assert row["observation_state"] == "prior_only"
    assert forecast["calibration_state"] == "not_assessed"
    assert forecast["chronology_claim"] == "local_dependency_order_only"
    assert forecast["authority"]["decision_authority"] is False
    assert forecast["authority"]["writes_local_artifacts"] is True
    assert forecast["authority"]["writes_repo_tracked_state"] is False


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [(1, 2, 1), (1, 3, 0), (2, 3, 1), (5_000, 10_000, 1)],
)
def test_round_half_up_ratio_is_integer_only(
    numerator: int,
    denominator: int,
    expected: int,
) -> None:
    assert round_half_up_ratio(numerator, denominator) == expected


def test_start_and_score_are_exactly_bound_without_cross_family_aggregate() -> None:
    forecast = _forecast()
    gate = _gate()
    forecast_ref = (
        "artifacts/orchestration/creative_code/bayesian_shadow/"
        f"{forecast['forecast_id']}/forecast.json"
    )
    gate_ref = forecast["target"]["generation_gate_ref"]
    start = build_target_start(
        forecast=forecast,
        forecast_ref=forecast_ref,
        gate=gate,
        gate_ref=gate_ref,
        started_at="2026-08-17T10:01:00Z",
    )
    assert validate_target_start(start) == start

    score = build_lifecycle_forecast_score(
        forecast=forecast,
        forecast_ref=forecast_ref,
        start=start,
        start_ref=(
            "artifacts/orchestration/creative_code/bayesian_shadow/"
            f"{forecast['forecast_id']}/start.json"
        ),
        outcomes={
            FAMILY_IDS[0]: "observed_positive",
            FAMILY_IDS[1]: "not_reached",
            FAMILY_IDS[2]: "not_reached",
        },
        observation={
            "analytics_id": _analytics()["analytics_id"],
            "analytics_fingerprint": fingerprint_payload(_analytics()),
            "analytics_ref": (
                "artifacts/orchestration/creative_code/lifecycle_transition_analytics/"
                f"{_analytics()['analytics_id']}/analytics.json"
            ),
            "telemetry_dir_ref": ("artifacts/orchestration/creative_code/telemetry/outcome-one"),
            "events_fingerprint": "sha256:" + "6" * 64,
            "rollup_fingerprint": "sha256:" + "7" * 64,
            "event_count": 1,
            "target_event_fingerprints": ["sha256:" + "8" * 64],
            "generation_receipt_ref": (
                "artifacts/orchestration/creative_code/patch_generation/run-one/"
                "generation_receipt.json"
            ),
            "generation_receipt_fingerprint": "sha256:" + "9" * 64,
            "result_id": ("evidence:creative_code_patch_result:control_plane:1.0:" + "c" * 24),
            "result_fingerprint": "sha256:" + "b" * 64,
            "promotion_id": None,
        },
        scored_at="2026-08-17T10:02:00Z",
        terminal_stop_observed=True,
    )
    normalized = validate_lifecycle_forecast_score(score)
    assert normalized["score_state"] == "partially_scored"
    assert normalized["families"][0]["realized_brier_loss_ppm"] == 250_000
    assert normalized["families"][0]["actual_bps"] == 10_000
    assert "overall_score" not in normalized
    assert "mean_brier_loss_ppm" not in normalized


def test_identity_and_time_tampering_fail_closed() -> None:
    forecast = _forecast()
    tampered = deepcopy(forecast)
    tampered["families"][0]["posterior_predictive_bps"] = 5001
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError):
        validate_lifecycle_forecast(tampered)

    gate = _gate()
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="started_at"):
        build_target_start(
            forecast=forecast,
            forecast_ref=(
                "artifacts/orchestration/creative_code/bayesian_shadow/"
                f"{forecast['forecast_id']}/forecast.json"
            ),
            gate=gate,
            gate_ref=forecast["target"]["generation_gate_ref"],
            started_at="2026-08-17T09:59:59Z",
        )

    assert forecast["baseline"]["analytics_fingerprint"] == fingerprint_payload(_analytics())


@pytest.mark.parametrize(
    "value",
    [
        "2026-08-17 10:00:00Z",
        "20260817T100000Z",
        "2026-08-17T10:00:00,1Z",
        "2026-08-17T10:00:00-00:00",
        "2026-08-17T10:00:00.1234567Z",
    ],
)
@pytest.mark.parametrize("label", ["produced_at", "started_at", "scored_at"])
def test_shadow_timestamps_require_strict_extended_ascii_rfc3339(
    value: str,
    label: str,
) -> None:
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="RFC3339"):
        normalize_rfc3339(value, label=label)


def test_shadow_timestamp_normalizes_known_offset_and_wraps_utc_or_cutoff_overflow() -> None:
    assert (
        normalize_rfc3339("2026-08-17T12:30:00.123400+02:30", label="produced_at")
        == "2026-08-17T10:00:00.1234Z"
    )
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="valid RFC3339"):
        normalize_rfc3339("0001-01-01T00:00:00+14:00", label="produced_at")
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="cutoff"):
        _forecast(produced_at="9999-12-31T23:59:59Z")


def test_family_counts_keep_censoring_and_unmatched_rows_out_of_posterior() -> None:
    analytics = _analytics()
    analytics["transition_counts"] = [
        {
            "from_stage": "specification",
            "from_status": "accepted",
            "to_stage": "patch_evaluation",
            "to_status": "accepted",
            "count": 2,
        },
        {
            "from_stage": "specification",
            "from_status": "accepted",
            "to_stage": "patch_evaluation",
            "to_status": "rejected",
            "count": 1,
        },
        {
            "from_stage": "promotion_approval",
            "from_status": "accepted",
            "to_stage": "pr_open",
            "to_status": "opened",
            "count": 1,
        },
        {
            "from_stage": "promotion_approval",
            "from_status": "accepted",
            "to_stage": "pr_open",
            "to_status": "blocked",
            "count": 3,
        },
        {
            "from_stage": "pr_open",
            "from_status": "opened",
            "to_stage": "pr_terminal",
            "to_status": "merged",
            "count": 0,
        },
        {
            "from_stage": "pr_open",
            "from_status": "opened",
            "to_stage": "pr_terminal",
            "to_status": "closed_unmerged",
            "count": 2,
        },
    ]
    lineage = analytics["lineage_accounting"]
    lineage["unobserved_successors_by_stage"].update(
        {"specification": 11, "promotion_approval": 12, "pr_open": 13}
    )
    lineage["unobserved_predecessors_by_stage"].update(
        {"patch_evaluation": 21, "pr_open": 22, "pr_terminal": 23}
    )

    rows = _forecast(analytics=analytics)["families"]

    assert [
        (
            row["positive_outcome_count"],
            row["negative_outcome_count"],
            row["effective_observation_count"],
            row["censored_eligible_count"],
            row["unmatched_destination_count"],
            row["posterior_alpha"],
            row["posterior_beta"],
            row["posterior_predictive_bps"],
        )
        for row in rows
    ] == [
        (2, 1, 3, 11, 21, 3, 2, 6000),
        (1, 3, 4, 12, 22, 2, 4, 3333),
        (0, 2, 2, 13, 23, 1, 3, 2500),
    ]


def test_closed_schemas_match_python_contract_keys_and_family_order() -> None:
    contracts = Path(__file__).resolve().parents[1] / "docs" / "orchestration" / "contracts"
    schemas = {
        "forecast": json.loads(
            (contracts / "creative_code_lifecycle_bayesian_forecast.v1.schema.json").read_text(
                encoding="utf-8"
            )
        ),
        "start": json.loads(
            (contracts / "creative_code_lifecycle_bayesian_target_start.v1.schema.json").read_text(
                encoding="utf-8"
            )
        ),
        "score": json.loads(
            (contracts / "creative_code_lifecycle_bayesian_score.v1.schema.json").read_text(
                encoding="utf-8"
            )
        ),
    }

    for schema in schemas.values():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        assert set(schema["$defs"]["authority"]["const"]) == AUTHORITY_KEYS
    assert set(schemas["forecast"]["required"]) == FORECAST_KEYS
    assert set(schemas["start"]["required"]) == START_KEYS
    assert set(schemas["score"]["required"]) == SCORE_KEYS
    assert [
        schemas["forecast"]["$defs"][name]["allOf"][1]["properties"]["family_id"]["const"]
        for name in ("patch_family", "open_family", "terminal_family")
    ] == list(FAMILY_IDS)
    assert [
        schemas["score"]["$defs"][name]["allOf"][1]["properties"]["family_id"]["const"]
        for name in ("patch_score", "open_score", "terminal_score")
    ] == list(FAMILY_IDS)


def test_private_publication_is_no_replace_canonical_and_source_rechecked(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bayesian_shadow"
    forecast = _forecast()
    content = canonical_shadow_bytes(forecast)
    rechecks: list[str] = []
    forecast_path, replayed = publish_shadow_artifact(
        shadow_root=root,
        forecast_id=forecast["forecast_id"],
        filename="forecast.json",
        content=content,
        recheck_sources=lambda: rechecks.append("forecast"),
    )
    assert replayed is False
    assert rechecks == ["forecast", "forecast", "forecast"]
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(forecast_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(forecast_path.stat().st_mode) == 0o600
    assert forecast_path.read_bytes() == content

    gate_rechecks: list[str] = []
    start_path, start_replayed, start = publish_target_start_from_forecast(
        forecast_path,
        gate=_gate(),
        gate_ref=forecast["target"]["generation_gate_ref"],
        started_at="2026-08-17T10:01:00Z",
        shadow_root=root,
        recheck_gate_sources=lambda: gate_rechecks.append("gate"),
    )
    assert start_replayed is False
    assert len(gate_rechecks) == 3
    before = start_path.stat()

    replay_path, replayed, replay = publish_target_start_from_forecast(
        forecast_path,
        gate=_gate(),
        gate_ref=forecast["target"]["generation_gate_ref"],
        started_at="2026-08-17T10:01:00Z",
        shadow_root=root,
        recheck_gate_sources=lambda: gate_rechecks.append("gate"),
    )
    after = start_path.stat()
    assert replay_path == start_path
    assert replayed is True
    assert replay == start
    assert (after.st_ino, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_ino,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="unbound generation"):
        assert_no_shadow_slot(
            _gate(),
            gate_ref=forecast["target"]["generation_gate_ref"],
            shadow_root=root,
        )
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="divergent_replay"):
        publish_target_start_from_forecast(
            forecast_path,
            gate=_gate(),
            gate_ref=forecast["target"]["generation_gate_ref"],
            started_at="2026-08-17T10:02:00Z",
            shadow_root=root,
            recheck_gate_sources=lambda: None,
        )
    assert start_path.read_bytes() == canonical_shadow_bytes(start)


def test_publication_rolls_back_installed_artifact_when_final_recheck_fails(
    tmp_path: Path,
) -> None:
    forecast = _forecast()
    root = tmp_path / "bayesian_shadow"
    calls = 0

    def fail_after_install() -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("injected source drift")

    with pytest.raises(RuntimeError, match="injected source drift"):
        publish_shadow_artifact(
            shadow_root=root,
            forecast_id=forecast["forecast_id"],
            filename="forecast.json",
            content=canonical_shadow_bytes(forecast),
            recheck_sources=fail_after_install,
        )
    assert not (root / forecast["forecast_id"] / "forecast.json").exists()


@pytest.mark.parametrize(
    ("filename", "content_factory"),
    [
        ("forecast.json", lambda forecast: b"{}\n"),
        ("start.json", lambda forecast: canonical_shadow_bytes(forecast)),
        ("score.json", lambda forecast: canonical_shadow_bytes(forecast)),
        (
            "forecast.json",
            lambda forecast: (json.dumps(forecast, indent=2, sort_keys=True) + "\n").encode(),
        ),
    ],
)
def test_publisher_validates_matching_contract_and_canonical_bytes_before_root_creation(
    tmp_path: Path,
    filename: str,
    content_factory: Any,
) -> None:
    forecast = _forecast()
    root = tmp_path / "bayesian_shadow"
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError):
        publish_shadow_artifact(
            shadow_root=root,
            forecast_id=forecast["forecast_id"],
            filename=filename,
            content=content_factory(forecast),
            recheck_sources=lambda: None,
        )
    assert not root.exists()


def test_publisher_rejects_content_forecast_id_mismatch_before_root_creation(
    tmp_path: Path,
) -> None:
    forecast = _forecast()
    root = tmp_path / "bayesian_shadow"
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="forecast_id"):
        publish_shadow_artifact(
            shadow_root=root,
            forecast_id=(
                "evidence:creative_code_lifecycle_bayesian_forecast:control_plane:1.0:" + "f" * 24
            ),
            filename="forecast.json",
            content=canonical_shadow_bytes(forecast),
            recheck_sources=lambda: None,
        )
    assert not root.exists()


def test_failed_publication_removes_only_its_owned_empty_namespace(tmp_path: Path) -> None:
    forecast = _forecast()
    content = canonical_shadow_bytes(forecast)
    root = tmp_path / "bayesian_shadow"
    namespace = root / forecast["forecast_id"]

    with pytest.raises(RuntimeError, match="source drift"):
        publish_shadow_artifact(
            shadow_root=root,
            forecast_id=forecast["forecast_id"],
            filename="forecast.json",
            content=content,
            recheck_sources=lambda: (_ for _ in ()).throw(RuntimeError("source drift")),
        )
    assert not namespace.exists()

    namespace.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    namespace.chmod(0o700)
    original_identity = (namespace.stat().st_dev, namespace.stat().st_ino)
    with pytest.raises(RuntimeError, match="source drift"):
        publish_shadow_artifact(
            shadow_root=root,
            forecast_id=forecast["forecast_id"],
            filename="forecast.json",
            content=content,
            recheck_sources=lambda: (_ for _ in ()).throw(RuntimeError("source drift")),
        )
    assert (namespace.stat().st_dev, namespace.stat().st_ino) == original_identity


def test_final_readback_failure_rolls_back_only_the_installed_inode_and_owned_namespace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    forecast = _forecast()
    content = canonical_shadow_bytes(forecast)
    root = tmp_path / "bayesian_shadow"
    target = root / forecast["forecast_id"] / "forecast.json"

    def fail_readback(*_args: Any, **_kwargs: Any) -> bytes:
        raise CreativeCodeLifecycleBayesianShadowError("injected final readback failure")

    monkeypatch.setattr(shadow_contract, "_read_existing_bytes", fail_readback)
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="final readback"):
        publish_shadow_artifact(
            shadow_root=root,
            forecast_id=forecast["forecast_id"],
            filename="forecast.json",
            content=content,
            recheck_sources=lambda: None,
        )
    assert not target.exists()
    assert not target.parent.exists()


def test_final_readback_rollback_preserves_a_concurrent_replacement_inode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    forecast = _forecast()
    content = canonical_shadow_bytes(forecast)
    root = tmp_path / "bayesian_shadow"
    target = root / forecast["forecast_id"] / "forecast.json"
    replacement_identity: tuple[int, int] | None = None

    def replace_then_fail(path: Path, **_kwargs: Any) -> bytes:
        nonlocal replacement_identity
        path.unlink()
        path.write_bytes(content)
        path.chmod(0o600)
        info = path.stat()
        replacement_identity = (info.st_dev, info.st_ino)
        raise CreativeCodeLifecycleBayesianShadowError("injected final readback failure")

    monkeypatch.setattr(shadow_contract, "_read_existing_bytes", replace_then_fail)
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="final readback"):
        publish_shadow_artifact(
            shadow_root=root,
            forecast_id=forecast["forecast_id"],
            filename="forecast.json",
            content=content,
            recheck_sources=lambda: None,
        )
    assert replacement_identity is not None
    current = target.stat()
    assert (current.st_dev, current.st_ino) == replacement_identity


def test_shadow_reader_rejects_noncanonical_symlink_and_hardlink_inputs(
    tmp_path: Path,
) -> None:
    forecast = _forecast()

    noncanonical_root = tmp_path / "noncanonical"
    noncanonical = noncanonical_root / forecast["forecast_id"] / "forecast.json"
    noncanonical.parent.mkdir(parents=True, mode=0o700)
    noncanonical_root.chmod(0o700)
    noncanonical.parent.chmod(0o700)
    noncanonical.write_text(json.dumps(forecast, indent=2) + "\n", encoding="utf-8")
    noncanonical.chmod(0o600)
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="canonical JSON"):
        read_shadow_json(
            noncanonical,
            shadow_root=noncanonical_root,
            label="noncanonical forecast",
        )

    hardlink_root = tmp_path / "hardlink"
    canonical, _ = publish_shadow_artifact(
        shadow_root=hardlink_root,
        forecast_id=forecast["forecast_id"],
        filename="forecast.json",
        content=canonical_shadow_bytes(forecast),
        recheck_sources=lambda: None,
    )
    duplicate_link = canonical.parent / "duplicate.json"
    duplicate_link.hardlink_to(canonical)
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="single-link"):
        read_shadow_json(canonical, shadow_root=hardlink_root, label="hardlinked forecast")

    symlink_root = tmp_path / "symlink"
    symlink_root.mkdir(mode=0o700)
    symlink = symlink_root / "forecast.json"
    symlink.symlink_to(canonical)
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="symlink"):
        read_shadow_json(symlink, shadow_root=symlink_root, label="symlinked forecast")


def test_target_lineage_uses_exact_tuple_and_closed_conditional_branches() -> None:
    target = _forecast()["target"]
    chain = _full_chain("one")
    unrelated = _full_chain("other", number=2201)

    outcomes, target_events, promotion_id, terminal = _target_outcomes(
        events=chain + unrelated,
        target=target,
    )
    assert outcomes == {family_id: "observed_positive" for family_id in FAMILY_IDS}
    assert promotion_id == "promotion-one"
    assert terminal is True
    assert len(target_events) == 6

    same_request_wrong_tuple = _legacy_event(
        "patch_evaluation",
        status="accepted",
        source_bundle_id="bundle-other",
        selected_variant_id="variant-other",
        request_id="request-one",
        result_id="result-other",
    )
    outcomes, target_events, _promotion_id, terminal = _target_outcomes(
        events=[same_request_wrong_tuple],
        target=target,
    )
    assert outcomes == {
        FAMILY_IDS[0]: "right_censored",
        FAMILY_IDS[1]: "not_reached",
        FAMILY_IDS[2]: "not_reached",
    }
    assert target_events == []
    assert terminal is False

    blocked = chain[1:5] + [
        _legacy_event(
            "pr_open",
            status="blocked",
            result_id="result-one",
            promotion_id="promotion-one",
        )
    ]
    outcomes, _events, _promotion_id, terminal = _target_outcomes(
        events=blocked,
        target=target,
    )
    assert outcomes == {
        FAMILY_IDS[0]: "observed_positive",
        FAMILY_IDS[1]: "observed_negative",
        FAMILY_IDS[2]: "not_reached",
    }
    assert terminal is True

    rejected = [
        _legacy_event(
            "patch_evaluation",
            status="rejected",
            source_bundle_id="bundle-one",
            selected_variant_id="variant-one",
            request_id="request-one",
            result_id="result-one",
        )
    ]
    outcomes, _events, _promotion_id, terminal = _target_outcomes(
        events=rejected,
        target=target,
    )
    assert outcomes == {
        FAMILY_IDS[0]: "observed_negative",
        FAMILY_IDS[1]: "not_reached",
        FAMILY_IDS[2]: "not_reached",
    }
    assert terminal is True


def test_duplicate_target_patch_or_plan_is_measurement_invalid() -> None:
    target = _forecast()["target"]
    chain = _full_chain("one")
    second_patch = _legacy_event(
        "patch_evaluation",
        status="accepted",
        source_bundle_id="bundle-one",
        selected_variant_id="variant-one",
        request_id="request-one",
        result_id="result-two",
    )
    outcomes, _events, _promotion_id, _terminal = _target_outcomes(
        events=[chain[1], second_patch],
        target=target,
    )
    assert outcomes == {family_id: "measurement_invalid" for family_id in FAMILY_IDS}

    second_plan = _legacy_event(
        "promotion_plan",
        status="accepted",
        source_bundle_id="bundle-one",
        selected_variant_id="variant-one",
        request_id="request-one",
        result_id="result-one",
        promotion_id="promotion-two",
    )
    outcomes, _events, _promotion_id, _terminal = _target_outcomes(
        events=[chain[1], chain[2], second_plan],
        target=target,
    )
    assert outcomes == {
        FAMILY_IDS[0]: "observed_positive",
        FAMILY_IDS[1]: "measurement_invalid",
        FAMILY_IDS[2]: "measurement_invalid",
    }


def _receipt_result() -> dict[str, Any]:
    return {
        "result_id": ("evidence:creative_code_patch_result:control_plane:1.0:" + "c" * 24),
        "result_fingerprint": "sha256:" + "d" * 64,
    }


def _patch_receipt_row(*, result_id: str, result_fingerprint: str) -> dict[str, Any]:
    return {
        "lane_stage": "patch_evaluation",
        "candidate_ids": {"result_id": result_id},
        "source_fingerprint": result_fingerprint,
    }


def test_nonempty_patch_rows_require_validated_generation_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "run-one" / "generation_gate.json"
    gate_path.parent.mkdir()
    receipt = _receipt_result()
    rows = [
        _patch_receipt_row(
            result_id=receipt["result_id"],
            result_fingerprint=receipt["result_fingerprint"],
        ),
        _patch_receipt_row(
            result_id="conflicting-result",
            result_fingerprint="sha256:" + "e" * 64,
        ),
    ]

    def missing_receipt(**_kwargs: Any) -> Any:
        raise generation_cli.CreativeCodePatchGenerationError("receipt missing")

    monkeypatch.setattr(
        generation_cli,
        "load_validated_generation_receipt_context",
        missing_receipt,
    )
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="validated.*receipt"):
        shadow_cli._validated_generation_receipt_projection(
            gate_path=gate_path,
            gate=_gate(),
            patch_rows=rows,
        )


@pytest.mark.parametrize("matching_rows", [0, 2])
def test_generation_receipt_requires_exactly_one_matching_patch_row(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    matching_rows: int,
) -> None:
    gate_path = tmp_path / "run-one" / "generation_gate.json"
    gate_path.parent.mkdir()
    receipt = _receipt_result()
    rows = [
        _patch_receipt_row(
            result_id=receipt["result_id"],
            result_fingerprint=receipt["result_fingerprint"],
        )
        for _index in range(matching_rows)
    ]
    if matching_rows == 0:
        rows.append(
            _patch_receipt_row(
                result_id="conflicting-result",
                result_fingerprint="sha256:" + "e" * 64,
            )
        )
    monkeypatch.setattr(
        generation_cli,
        "load_validated_generation_receipt_context",
        lambda **_kwargs: (_gate(), receipt),
    )
    monkeypatch.setattr(
        shadow_cli,
        "_repo_ref",
        lambda _path, *, label: (
            "artifacts/orchestration/creative_code/patch_generation/run-one/"
            "generation_receipt.json"
        ),
    )

    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="exactly one"):
        shadow_cli._validated_generation_receipt_projection(
            gate_path=gate_path,
            gate=_gate(),
            patch_rows=rows,
        )


def test_conflicting_patch_row_retains_validated_generation_receipt_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "run-one" / "generation_gate.json"
    gate_path.parent.mkdir()
    gate = _gate()
    receipt = _receipt_result()
    rows = [
        _patch_receipt_row(
            result_id=receipt["result_id"],
            result_fingerprint=receipt["result_fingerprint"],
        ),
        _patch_receipt_row(
            result_id="conflicting-result",
            result_fingerprint="sha256:" + "e" * 64,
        ),
    ]
    receipt_ref = (
        "artifacts/orchestration/creative_code/patch_generation/run-one/" "generation_receipt.json"
    )
    monkeypatch.setattr(
        generation_cli,
        "load_validated_generation_receipt_context",
        lambda **_kwargs: (gate, receipt),
    )
    monkeypatch.setattr(
        shadow_cli,
        "_repo_ref",
        lambda _path, *, label: receipt_ref,
    )

    projection, validated_receipt = shadow_cli._validated_generation_receipt_projection(
        gate_path=gate_path,
        gate=gate,
        patch_rows=rows,
    )

    assert validated_receipt == receipt
    assert projection == {
        "generation_receipt_ref": receipt_ref,
        "generation_receipt_fingerprint": fingerprint_payload(receipt),
        "result_id": receipt["result_id"],
        "result_fingerprint": receipt["result_fingerprint"],
    }


def test_zero_patch_rows_reject_existing_generation_receipt(tmp_path: Path) -> None:
    gate_path = tmp_path / "run-one" / "generation_gate.json"
    gate_path.parent.mkdir()
    (gate_path.parent / generation_cli.RECEIPT_FILENAME).touch()

    with pytest.raises(
        CreativeCodeLifecycleBayesianShadowError,
        match="receipt exists without target patch telemetry",
    ):
        shadow_cli._validated_generation_receipt_projection(
            gate_path=gate_path,
            gate=_gate(),
            patch_rows=[],
        )


@pytest.mark.parametrize(
    ("states", "terminal_stop", "scored_at", "expected_state"),
    [
        (
            ("observed_positive", "observed_positive", "observed_positive"),
            True,
            "2026-08-17T10:02:00Z",
            "fully_scored",
        ),
        (
            ("observed_positive", "observed_negative", "not_reached"),
            True,
            "2026-08-17T10:02:00Z",
            "partially_scored",
        ),
        (
            ("right_censored", "not_reached", "not_reached"),
            False,
            "2026-08-31T10:00:00Z",
            "valid_but_unscored",
        ),
        (
            ("measurement_invalid", "measurement_invalid", "measurement_invalid"),
            False,
            "2026-08-31T10:00:00Z",
            "measurement_invalid",
        ),
    ],
)
def test_score_top_level_states_have_no_cross_family_aggregate(
    states: tuple[str, str, str],
    terminal_stop: bool,
    scored_at: str,
    expected_state: str,
) -> None:
    forecast = _forecast()
    forecast_ref = (
        "artifacts/orchestration/creative_code/bayesian_shadow/"
        f"{forecast['forecast_id']}/forecast.json"
    )
    start = build_target_start(
        forecast=forecast,
        forecast_ref=forecast_ref,
        gate=_gate(),
        gate_ref=forecast["target"]["generation_gate_ref"],
        started_at="2026-08-17T10:01:00Z",
    )
    analytics = _analytics()
    score = build_lifecycle_forecast_score(
        forecast=forecast,
        forecast_ref=forecast_ref,
        start=start,
        start_ref=(
            "artifacts/orchestration/creative_code/bayesian_shadow/"
            f"{forecast['forecast_id']}/start.json"
        ),
        outcomes=dict(zip(FAMILY_IDS, states, strict=True)),
        observation={
            "analytics_id": analytics["analytics_id"],
            "analytics_fingerprint": fingerprint_payload(analytics),
            "analytics_ref": (
                "artifacts/orchestration/creative_code/lifecycle_transition_analytics/"
                f"{analytics['analytics_id']}/analytics.json"
            ),
            "telemetry_dir_ref": ("artifacts/orchestration/creative_code/telemetry/outcome-one"),
            "events_fingerprint": analytics["corpus"]["events_fingerprint"],
            "rollup_fingerprint": analytics["corpus"]["rollup_fingerprint"],
            "event_count": analytics["corpus"]["event_count"],
            "target_event_fingerprints": [],
            "generation_receipt_ref": None,
            "generation_receipt_fingerprint": None,
            "result_id": None,
            "result_fingerprint": None,
            "promotion_id": None,
        },
        scored_at=scored_at,
        terminal_stop_observed=terminal_stop,
    )

    assert score["score_state"] == expected_state
    assert "overall_score" not in score
    assert "mean_brier_loss_ppm" not in score
    for row, state in zip(score["families"], states, strict=True):
        if state in {"observed_positive", "observed_negative"}:
            assert row["realized_brier_loss_ppm"] == 250_000
        else:
            assert row["realized_brier_loss_ppm"] is None


@pytest.mark.parametrize(
    "scored_at",
    ["2026-08-17T10:02:00Z", "2026-08-31T10:00:01Z"],
)
def test_nonterminal_measurement_invalid_score_requires_exact_cutoff(
    scored_at: str,
) -> None:
    forecast = _forecast()
    forecast_ref, start = _start_for_forecast(forecast)

    with pytest.raises(
        CreativeCodeLifecycleBayesianShadowError,
        match="exact observation cutoff",
    ):
        build_lifecycle_forecast_score(
            forecast=forecast,
            forecast_ref=forecast_ref,
            start=start,
            start_ref=(
                "artifacts/orchestration/creative_code/bayesian_shadow/"
                f"{forecast['forecast_id']}/start.json"
            ),
            outcomes={family_id: "measurement_invalid" for family_id in FAMILY_IDS},
            observation=_empty_observation(),
            scored_at=scored_at,
            terminal_stop_observed=False,
        )


def test_terminal_score_must_not_extend_the_fixed_observation_horizon() -> None:
    forecast = _forecast()
    forecast_ref, start = _start_for_forecast(forecast)

    with pytest.raises(
        CreativeCodeLifecycleBayesianShadowError,
        match="must not be after observation cutoff",
    ):
        build_lifecycle_forecast_score(
            forecast=forecast,
            forecast_ref=forecast_ref,
            start=start,
            start_ref=(
                "artifacts/orchestration/creative_code/bayesian_shadow/"
                f"{forecast['forecast_id']}/start.json"
            ),
            outcomes={family_id: "observed_positive" for family_id in FAMILY_IDS},
            observation=_empty_observation(),
            scored_at="2026-08-31T10:00:01Z",
            terminal_stop_observed=True,
        )


def test_pr_open_requires_exact_promotion_and_target_result_identity() -> None:
    target = _forecast()["target"]
    chain = _full_chain("one")
    wrong_result_open = _legacy_event(
        "pr_open",
        status="opened",
        result_id="result-conflict",
        promotion_id="promotion-one",
    )

    outcomes, target_events, promotion_id, terminal = _target_outcomes(
        events=[*chain[1:5], wrong_result_open],
        target=target,
    )

    assert outcomes == {
        FAMILY_IDS[0]: "observed_positive",
        FAMILY_IDS[1]: "measurement_invalid",
        FAMILY_IDS[2]: "measurement_invalid",
    }
    assert wrong_result_open in target_events
    assert promotion_id == "promotion-one"
    assert terminal is False


@pytest.mark.parametrize(
    "upstream_stage", ["promotion_plan", "promotion_validation", "promotion_approval"]
)
def test_nonaccepted_upstream_with_downstream_target_evidence_is_invalid(
    upstream_stage: str,
) -> None:
    target = _forecast()["target"]
    chain = _full_chain("one")
    indexes = {"promotion_plan": 2, "promotion_validation": 3, "promotion_approval": 4}
    conflicting = deepcopy(chain[indexes[upstream_stage]])
    conflicting["status"] = "rejected"
    events = [chain[1], chain[2], chain[3], chain[4], chain[5]]
    events[indexes[upstream_stage] - 1] = conflicting

    outcomes, _target_events, promotion_id, terminal = _target_outcomes(
        events=events,
        target=target,
    )

    assert outcomes == {
        FAMILY_IDS[0]: "observed_positive",
        FAMILY_IDS[1]: "measurement_invalid",
        FAMILY_IDS[2]: "measurement_invalid",
    }
    assert promotion_id == "promotion-one"
    assert terminal is False


def test_missing_validation_with_approval_and_open_is_measurement_invalid() -> None:
    target = _forecast()["target"]
    chain = _full_chain("one")

    outcomes, _target_events, promotion_id, terminal = _target_outcomes(
        events=[chain[1], chain[2], chain[4], chain[5]],
        target=target,
    )

    assert outcomes == {
        FAMILY_IDS[0]: "observed_positive",
        FAMILY_IDS[1]: "measurement_invalid",
        FAMILY_IDS[2]: "measurement_invalid",
    }
    assert promotion_id == "promotion-one"
    assert terminal is False


def test_maximum_count_allows_the_distinct_maximum_posterior_parameter() -> None:
    max_count = getattr(shadow_contract, "MAX_COUNT")
    max_parameter = getattr(shadow_contract, "MAX_POSTERIOR_PARAMETER")
    assert max_count == 1_000_000_000_000
    assert max_parameter == max_count + 1
    analytics = _analytics()
    analytics["transition_counts"] = [
        {
            "from_stage": "specification",
            "from_status": "accepted",
            "to_stage": "patch_evaluation",
            "to_status": "accepted",
            "count": max_count,
        }
    ]

    row = _forecast(analytics=analytics)["families"][0]

    assert row["positive_outcome_count"] == max_count
    assert row["posterior_alpha"] == max_parameter
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "orchestration"
            / "contracts"
            / "creative_code_lifecycle_bayesian_forecast.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["$defs"]["count"]["maximum"] == max_count
    assert schema["$defs"]["posterior_parameter"]["maximum"] == max_parameter
    assert schema["$defs"]["family_base"]["properties"]["posterior_alpha"] == {
        "$ref": "#/$defs/posterior_parameter"
    }


def test_schema_file_and_directory_ref_languages_match_python_validator() -> None:
    contracts = Path(__file__).resolve().parents[1] / "docs" / "orchestration" / "contracts"
    schemas = [
        json.loads((contracts / filename).read_text(encoding="utf-8"))
        for filename in (
            "creative_code_lifecycle_bayesian_forecast.v1.schema.json",
            "creative_code_lifecycle_bayesian_target_start.v1.schema.json",
            "creative_code_lifecycle_bayesian_score.v1.schema.json",
        )
    ]
    file_patterns = {schema["$defs"]["json_file_ref"]["pattern"] for schema in schemas}
    directory_patterns = {schema["$defs"]["directory_ref"]["pattern"] for schema in schemas}
    assert len(file_patterns) == 1
    assert len(directory_patterns) == 1
    file_pattern = file_patterns.pop()
    directory_pattern = directory_patterns.pop()
    candidates = [
        ("artifacts/orchestration/creative_code/one/a.json", ".json", True),
        ("artifacts/orchestration/creative_code/a:b/c_d-1.json", ".json", True),
        ("artifacts/orchestration/creative_code/telemetry/baseline-one", "", True),
        ("artifacts/orchestration/creative_code/telemetry/name.json", "", True),
        ("artifacts/orchestration/creative_code/one/no-extension", ".json", False),
        ("artifacts/orchestration/creative_code//a.json", ".json", False),
        ("artifacts/orchestration/creative_code/./a.json", ".json", False),
        ("artifacts/orchestration/creative_code/../a.json", ".json", False),
        ("artifacts/orchestration/creative_code/a b.json", ".json", False),
        ("artifacts/orchestration/creative_code/a\\b.json", ".json", False),
        ("artifacts/orchestration/other/a.json", ".json", False),
    ]
    for value, suffix, expected in candidates:
        try:
            shadow_contract._repo_ref(value, label="test ref", suffix=suffix)
        except CreativeCodeLifecycleBayesianShadowError:
            python_accepts = False
        else:
            python_accepts = True
        pattern = file_pattern if suffix else directory_pattern
        schema_accepts = re.fullmatch(pattern, value) is not None
        assert python_accepts is expected
        assert schema_accepts is expected


def test_shadow_read_requires_private_exact_root_and_namespace_only(tmp_path: Path) -> None:
    outer = tmp_path / "shared-parent"
    outer.mkdir(mode=0o755)
    root = outer / "bayesian_shadow"
    forecast = _forecast()
    path, _replayed = publish_shadow_artifact(
        shadow_root=root,
        forecast_id=forecast["forecast_id"],
        filename="forecast.json",
        content=canonical_shadow_bytes(forecast),
        recheck_sources=lambda: None,
    )
    assert read_shadow_json(path, shadow_root=root, label="forecast")[0] == forecast

    root.chmod(0o755)
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="shadow root.*0700"):
        read_shadow_json(path, shadow_root=root, label="forecast")
    root.chmod(0o700)

    path.parent.chmod(0o755)
    with pytest.raises(CreativeCodeLifecycleBayesianShadowError, match="namespace.*0700"):
        read_shadow_json(path, shadow_root=root, label="forecast")


def test_shadow_root_resolver_is_centralized_in_leaf_contract(tmp_path: Path) -> None:
    resolver = getattr(shadow_contract, "canonical_shadow_root")
    expected = tmp_path / "artifacts" / "orchestration" / "creative_code" / "bayesian_shadow"
    assert resolver(tmp_path) == expected
    assert shadow_cli.BAYESIAN_SHADOW_ROOT == resolver(shadow_cli.REPO_ROOT)


def test_real_event_analytics_preserve_patch_fanout_censoring_and_unmatched_counts() -> None:
    events = [
        _legacy_event(
            "specification",
            status="accepted",
            source_packet_id="packet-one",
            source_bundle_id="bundle-one",
            selected_variant_id="variant-one",
        ),
        _legacy_event(
            "patch_evaluation",
            status="accepted",
            source_bundle_id="bundle-one",
            selected_variant_id="variant-one",
            request_id="request-one",
            result_id="result-one",
        ),
        _legacy_event(
            "patch_evaluation",
            status="rejected",
            source_bundle_id="bundle-one",
            selected_variant_id="variant-one",
            request_id="request-two",
            result_id="result-two",
        ),
        _legacy_event(
            "specification",
            status="accepted",
            source_packet_id="packet-censored",
            source_bundle_id="bundle-censored",
            selected_variant_id="variant-censored",
        ),
        _legacy_event(
            "patch_evaluation",
            status="accepted",
            source_bundle_id="bundle-unmatched",
            selected_variant_id="variant-unmatched",
            request_id="request-unmatched",
            result_id="result-unmatched",
        ),
    ]
    rollup = build_creative_code_telemetry_rollup_v2(
        events,
        input_roots=["patch_runs", "promotions", "spec_runs", "terminal_outcomes"],
    )
    analytics = build_creative_code_lifecycle_transition_analytics(
        events,
        telemetry_rollup=rollup,
    )

    row = _forecast(analytics=analytics)["families"][0]

    assert row["positive_outcome_count"] == 1
    assert row["negative_outcome_count"] == 1
    assert row["effective_observation_count"] == 2
    assert row["censored_eligible_count"] == 1
    assert row["unmatched_destination_count"] == 1
    assert row["posterior_alpha"] == 2
    assert row["posterior_beta"] == 2
    assert row["posterior_predictive_bps"] == 5000


def _configure_public_shadow_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, dict[str, Any]]:
    repo = tmp_path / "repo"
    creative_root = repo / "artifacts" / "orchestration" / "creative_code"
    telemetry_root = creative_root / "telemetry"
    analytics_root = creative_root / "lifecycle_transition_analytics"
    shadow_root = creative_root / "bayesian_shadow"
    telemetry_root.mkdir(parents=True)
    monkeypatch.setattr(analytics_cli, "REPO_ROOT", repo)
    monkeypatch.setattr(analytics_cli, "CREATIVE_CODE_ROOT", creative_root)
    monkeypatch.setattr(analytics_cli, "TELEMETRY_ROOT", telemetry_root)
    monkeypatch.setattr(analytics_cli, "ANALYTICS_ROOT", analytics_root)
    monkeypatch.setattr(shadow_cli, "REPO_ROOT", repo)
    monkeypatch.setattr(shadow_cli, "CREATIVE_CODE_ROOT", creative_root)
    monkeypatch.setattr(shadow_cli, "BAYESIAN_SHADOW_ROOT", shadow_root)
    gate = _gate()
    gate_path = creative_root / "patch_generation" / "run-one" / "generation_gate.json"
    gate_path.parent.mkdir(parents=True)
    gate_path.write_text("{}\n", encoding="utf-8")

    def load_gate(path: Path) -> tuple[Path, dict[str, Any]]:
        assert path.resolve(strict=True) == gate_path.resolve(strict=True)
        return gate_path.resolve(strict=True), gate

    monkeypatch.setattr(shadow_cli, "_load_gate_before_generation", load_gate)
    monkeypatch.setattr(shadow_cli, "_load_gate_for_readback", load_gate)
    monkeypatch.setattr(
        shadow_cli,
        "resolve_existing_run_dir",
        lambda run_id: gate_path.parent.resolve(strict=True),
    )
    return repo, telemetry_root, analytics_root, shadow_root, gate


def test_build_forecast_holds_canonical_run_lock_across_sources_and_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gate = _gate()
    resolved_gate = tmp_path / "generation_gate.json"
    run_dir = tmp_path / "patch-run"
    run_dir.mkdir()
    snapshot = SimpleNamespace(analytics=_analytics(), events=())
    lock_active = False
    gate_checks: list[bool] = []
    snapshot_checks: list[bool] = []

    @contextmanager
    def fake_lock(path: Path, *, label: str) -> Any:
        nonlocal lock_active
        assert path == run_dir
        assert label == "creative-code shadow forecast"
        assert lock_active is False
        lock_active = True
        try:
            yield
        finally:
            lock_active = False

    def load_gate(_path: Path) -> tuple[Path, dict[str, Any]]:
        gate_checks.append(lock_active)
        return resolved_gate, gate

    def load_snapshot(*, telemetry_dir: Path) -> Any:
        assert telemetry_dir == tmp_path / "telemetry"
        snapshot_checks.append(lock_active)
        assert lock_active is True
        return snapshot

    def publish(**kwargs: Any) -> tuple[Path, bool]:
        assert lock_active is True
        kwargs["recheck_sources"]()
        return tmp_path / "forecast.json", False

    monkeypatch.setattr(shadow_cli, "_load_gate_before_generation", load_gate)
    monkeypatch.setattr(analytics_cli, "load_validated_snapshot_artifact", load_snapshot)
    monkeypatch.setattr(
        shadow_cli, "resolve_existing_run_dir", lambda run_id: run_dir, raising=False
    )
    monkeypatch.setattr(shadow_cli, "exclusive_patch_run_lock", fake_lock, raising=False)
    monkeypatch.setattr(
        shadow_cli,
        "_analytics_ref",
        lambda _snapshot: "artifacts/orchestration/creative_code/lifecycle_transition_analytics/one/analytics.json",
    )
    monkeypatch.setattr(
        shadow_cli,
        "_repo_ref",
        lambda _path, *, label: (
            "artifacts/orchestration/creative_code/patch_generation/run-one/generation_gate.json"
            if label == "generation gate"
            else "artifacts/orchestration/creative_code/telemetry/baseline-one"
        ),
    )
    monkeypatch.setattr(shadow_cli, "publish_shadow_artifact", publish)

    shadow_cli.build_forecast(
        telemetry_dir=tmp_path / "telemetry",
        gate_path=resolved_gate,
        produced_at="2026-08-17T10:00:00Z",
    )

    assert gate_checks[0] is False
    assert gate_checks[1:] and all(gate_checks[1:])
    assert snapshot_checks and all(snapshot_checks)
    assert lock_active is False


def test_public_cli_frozen_snapshot_forecast_score_readback_and_subset_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, telemetry_root, _analytics_root, shadow_root, gate = _configure_public_shadow_cli(
        monkeypatch,
        tmp_path,
    )
    baseline_events = [
        _legacy_event(
            "specification",
            status="accepted",
            source_packet_id="packet-baseline",
            source_bundle_id="bundle-baseline",
            selected_variant_id="variant-baseline",
        )
    ]
    baseline_dir = telemetry_root / "baseline"
    _write_frozen_snapshot(baseline_dir, baseline_events)
    analytics_cli.build_from_snapshot(telemetry_dir=baseline_dir)
    gate_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_generation"
        / "run-one"
        / "generation_gate.json"
    )

    assert (
        shadow_cli.main(
            [
                "build-forecast",
                "--telemetry-dir",
                str(baseline_dir),
                "--gate",
                str(gate_path),
                "--produced-at",
                "2026-08-17T10:00:00Z",
            ]
        )
        == 0
    )
    forecast_path = next(shadow_root.glob("*/forecast.json"))
    assert shadow_cli.main(["validate-forecast", "--forecast", str(forecast_path)]) == 0
    raw_forecast, _forecast_seal = read_shadow_json(
        forecast_path,
        shadow_root=shadow_root,
        label="forecast",
    )
    forecast = validate_lifecycle_forecast(raw_forecast)
    start_path, _replayed, start = publish_target_start_from_forecast(
        forecast_path,
        gate=gate,
        gate_ref=forecast["target"]["generation_gate_ref"],
        started_at="2026-08-17T10:01:00Z",
        shadow_root=shadow_root,
        recheck_gate_sources=lambda: None,
    )
    assert shadow_cli.main(["validate-start", "--start", str(start_path)]) == 0
    assert validate_target_start(start) == start

    missing_baseline_dir = telemetry_root / "outcome-missing-baseline"
    _write_frozen_snapshot(missing_baseline_dir, [])
    analytics_cli.build_from_snapshot(telemetry_dir=missing_baseline_dir)
    assert (
        shadow_cli.main(
            [
                "score-forecast",
                "--forecast",
                str(forecast_path),
                "--telemetry-dir",
                str(missing_baseline_dir),
                "--scored-at",
                "2026-08-31T10:00:00Z",
            ]
        )
        == 1
    )
    assert "baseline_snapshot_drift" in capsys.readouterr().err
    assert not (forecast_path.parent / "score.json").exists()

    outcome_dir = telemetry_root / "outcome"
    _write_frozen_snapshot(outcome_dir, baseline_events)
    analytics_cli.build_from_snapshot(telemetry_dir=outcome_dir)
    assert (
        shadow_cli.main(
            [
                "score-forecast",
                "--forecast",
                str(forecast_path),
                "--telemetry-dir",
                str(outcome_dir),
                "--scored-at",
                "2026-08-31T10:00:00Z",
            ]
        )
        == 0
    )
    score_path = forecast_path.parent / "score.json"
    assert shadow_cli.main(["validate-score", "--score", str(score_path)]) == 0
    score = validate_lifecycle_forecast_score(
        read_shadow_json(score_path, shadow_root=shadow_root, label="score")[0]
    )
    assert score["score_state"] == "valid_but_unscored"
    assert [row["outcome_state"] for row in score["families"]] == [
        "right_censored",
        "not_reached",
        "not_reached",
    ]


def test_public_cli_rejects_target_leakage_in_frozen_baseline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, telemetry_root, _analytics_root, shadow_root, _gate_payload = (
        _configure_public_shadow_cli(monkeypatch, tmp_path)
    )
    leaked_dir = telemetry_root / "leaked"
    _write_frozen_snapshot(leaked_dir, [_full_chain("one")[1]])
    analytics_cli.build_from_snapshot(telemetry_dir=leaked_dir)
    gate_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_generation"
        / "run-one"
        / "generation_gate.json"
    )

    assert (
        shadow_cli.main(
            [
                "build-forecast",
                "--telemetry-dir",
                str(leaked_dir),
                "--gate",
                str(gate_path),
                "--produced-at",
                "2026-08-17T10:00:00Z",
            ]
        )
        == 1
    )
    assert "retrospective_forecast_forbidden" in capsys.readouterr().err
    assert not shadow_root.exists()


@pytest.mark.parametrize("single_flag", ["--shadow-forecast", "--started-at"])
def test_generate_candidate_requires_paired_shadow_arguments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    single_flag: str,
) -> None:
    value = (
        str(tmp_path / "forecast.json")
        if single_flag == "--shadow-forecast"
        else ("2026-08-17T10:01:00Z")
    )
    assert (
        generation_cli.main(
            [
                "generate-candidate",
                "--gate",
                str(tmp_path / "missing-gate.json"),
                single_flag,
                value,
            ]
        )
        == 1
    )
    assert "must be supplied together" in capsys.readouterr().err


def test_generate_candidate_publishes_valid_start_before_builder_without_probabilities(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, gate_path, gate, forecast, forecast_path, shadow_root = _prepare_generation_forecast(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        run_id="shadow-integration-success",
    )
    original_generate = creative_code_patch_builder.generate
    observed_calls: list[str] = []

    def observed_generate(*, run_id: str) -> dict[str, Any]:
        observed_calls.append(run_id)
        start_path = forecast_path.parent / "start.json"
        raw, _seal = read_shadow_json(
            start_path,
            shadow_root=shadow_root,
            label="target start before generate",
        )
        validate_target_start_binding(
            start=raw,
            forecast=forecast,
            forecast_ref=forecast_path.relative_to(repo).as_posix(),
            gate=gate,
            gate_ref=gate_path.relative_to(repo).as_posix(),
        )
        return original_generate(run_id=run_id)

    monkeypatch.setattr(creative_code_patch_builder, "generate", observed_generate)

    assert (
        generation_cli.main(
            [
                "generate-candidate",
                "--gate",
                str(gate_path),
                "--shadow-forecast",
                str(forecast_path),
                "--started-at",
                "2026-08-17T10:01:00Z",
            ]
        )
        == 0
    )
    assert observed_calls == [gate["run_id"]]
    assert (forecast_path.parent / "start.json").exists()
    assert (gate_path.parent / generation_cli.RECEIPT_FILENAME).exists()


def test_generation_failure_preserves_start_blocks_unbound_and_allows_identical_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _repo, gate_path, _gate_payload, _forecast_payload, forecast_path, _shadow_root = (
        _prepare_generation_forecast(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            run_id="shadow-integration-retry",
        )
    )
    original_generate = creative_code_patch_builder.generate

    def fail_generation(*, run_id: str) -> dict[str, Any]:
        assert run_id == "shadow-integration-retry"
        assert (forecast_path.parent / "start.json").exists()
        raise creative_code_patch_builder.CreativeCodePatchBuilderError(
            "injected generation failure"
        )

    monkeypatch.setattr(creative_code_patch_builder, "generate", fail_generation)
    forecasted_command = [
        "generate-candidate",
        "--gate",
        str(gate_path),
        "--shadow-forecast",
        str(forecast_path),
        "--started-at",
        "2026-08-17T10:01:00Z",
    ]
    assert generation_cli.main(forecasted_command) == 1
    assert "injected generation failure" in capsys.readouterr().err
    start_path = forecast_path.parent / "start.json"
    start_before = start_path.read_bytes()

    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 1
    assert "unbound generation is forbidden" in capsys.readouterr().err
    assert start_path.read_bytes() == start_before

    monkeypatch.setattr(creative_code_patch_builder, "generate", original_generate)
    assert generation_cli.main(forecasted_command) == 0
    assert start_path.read_bytes() == start_before


def test_legacy_generate_candidate_without_shadow_slot_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "shadow-legacy-no-slot"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    shadow_root = repo / "artifacts" / "orchestration" / "creative_code" / "bayesian_shadow"

    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    assert not shadow_root.exists()
    assert (gate_path.parent / generation_cli.RECEIPT_FILENAME).exists()


def test_duplicate_generate_candidate_is_serialized_by_existing_run_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _repo, gate_path, _gate_payload, _forecast_payload, forecast_path, _shadow_root = (
        _prepare_generation_forecast(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            run_id="shadow-duplicate-lock",
        )
    )
    command = [
        "generate-candidate",
        "--gate",
        str(gate_path),
        "--shadow-forecast",
        str(forecast_path),
        "--started-at",
        "2026-08-17T10:01:00Z",
    ]
    builder_calls = 0

    def probe_duplicate(*, run_id: str) -> dict[str, Any]:
        nonlocal builder_calls
        assert run_id == "shadow-duplicate-lock"
        builder_calls += 1
        if builder_calls == 1:
            assert generation_cli.main(command) == 1
            raise creative_code_patch_builder.CreativeCodePatchBuilderError("outer generation stop")
        raise creative_code_patch_builder.CreativeCodePatchBuilderError("duplicate reached builder")

    monkeypatch.setattr(creative_code_patch_builder, "generate", probe_duplicate)
    capsys.readouterr()

    assert generation_cli.main(command) == 1
    captured = capsys.readouterr()
    assert builder_calls == 1
    assert "already in progress" in captured.err
    assert "duplicate reached builder" not in captured.err
    assert (forecast_path.parent / "start.json").exists()
