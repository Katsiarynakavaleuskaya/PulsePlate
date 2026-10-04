"""Behavioral contract for the CAB-06 family-specific CI simulator selector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci import select_ios_simulator as selector

IPHONE_UDID = "11111111-1111-4111-8111-111111111111"
IPAD_UDID = "22222222-2222-4222-8222-222222222222"
OTHER_IPHONE_UDID = "33333333-3333-4333-8333-333333333333"
IPHONE_TYPE = "com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro"
IPAD_TYPE = "com.apple.CoreSimulator.SimDeviceType.iPad-Air"


def _inventories() -> tuple[dict[str, object], dict[str, object]]:
    devices: dict[str, object] = {
        "devices": {
            selector.IOS_27_RUNTIME: [
                {
                    "name": "iPad Air",
                    "udid": IPAD_UDID,
                    "isAvailable": True,
                    "deviceTypeIdentifier": IPAD_TYPE,
                },
                {
                    "name": "iPhone 18 Pro",
                    "udid": IPHONE_UDID,
                    "isAvailable": True,
                    "deviceTypeIdentifier": IPHONE_TYPE,
                },
                {
                    "name": "iPhone Other",
                    "udid": OTHER_IPHONE_UDID,
                    "isAvailable": True,
                    "deviceTypeIdentifier": IPHONE_TYPE,
                },
            ]
        }
    }
    types: dict[str, object] = {
        "devicetypes": [
            {"identifier": IPHONE_TYPE, "productFamily": "iPhone"},
            {"identifier": IPAD_TYPE, "productFamily": "iPad"},
        ]
    }
    return devices, types


@pytest.mark.parametrize(
    ("family", "expected_udid"),
    [("iphone", IPHONE_UDID), ("ipad", IPAD_UDID)],
)
def test_selects_exact_requested_family(family: str, expected_udid: str) -> None:
    devices, types = _inventories()

    selected = selector.select_simulator(devices, types, family=family)

    assert selected == {
        "family": family,
        "ios_runtime_id": selector.IOS_27_RUNTIME,
        "device_name": "iPhone 18 Pro" if family == "iphone" else "iPad Air",
        "udid": expected_udid,
        "destination": f"platform=iOS Simulator,id={expected_udid}",
    }


def test_preference_and_fallback_stay_in_requested_family() -> None:
    devices, types = _inventories()
    selected = selector.select_simulator(
        devices, types, family="iphone", preferred_names=("iPad Air", "iPhone Other")
    )
    assert selected["udid"] == OTHER_IPHONE_UDID

    selected = selector.select_simulator(
        devices, types, family="iphone", preferred_names=("iPad Air",)
    )
    assert selected["udid"] == IPHONE_UDID


def test_product_family_wins_over_device_name() -> None:
    devices, types = _inventories()
    device_map = devices["devices"]
    assert isinstance(device_map, dict)
    device_list = device_map[selector.IOS_27_RUNTIME]
    assert isinstance(device_list, list)
    device = device_list[1]
    assert isinstance(device, dict)
    device["name"] = "iPad deceptive name"

    selected = selector.select_simulator(
        devices, types, family="iphone", preferred_names=("iPad deceptive name",)
    )
    assert selected["udid"] == IPHONE_UDID


def test_unknown_product_family_rejects_inventory_even_with_valid_candidates() -> None:
    devices, types = _inventories()
    device_types = types["devicetypes"]
    assert isinstance(device_types, list)
    ipad_type = device_types[1]
    assert isinstance(ipad_type, dict)
    ipad_type["productFamily"] = "Unknown"

    with pytest.raises(selector.SelectionError, match="Unknown iOS device productFamily"):
        selector.select_simulator(devices, types, family="iphone")


def test_inventory_order_does_not_change_selection() -> None:
    devices, types = _inventories()
    before = selector.select_simulator(devices, types, family="iphone", preferred_names=())
    device_map = devices["devices"]
    assert isinstance(device_map, dict)
    device_list = device_map[selector.IOS_27_RUNTIME]
    assert isinstance(device_list, list)
    device_list.reverse()
    type_list = types["devicetypes"]
    assert isinstance(type_list, list)
    type_list.reverse()
    after = selector.select_simulator(devices, types, family="iphone", preferred_names=())
    assert before == after


@pytest.mark.parametrize("family", ["iphone", "ipad"])
def test_missing_family_fails_instead_of_crossing_to_other_family(family: str) -> None:
    devices, types = _inventories()
    device_map = devices["devices"]
    assert isinstance(device_map, dict)
    device_list = device_map[selector.IOS_27_RUNTIME]
    assert isinstance(device_list, list)
    device_list[:] = [
        item
        for item in device_list
        if isinstance(item, dict)
        and item["deviceTypeIdentifier"] != (IPHONE_TYPE if family == "iphone" else IPAD_TYPE)
    ]

    with pytest.raises(selector.SelectionError, match="No available"):
        selector.select_simulator(devices, types, family=family)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("family", "Unsupported simulator family"),
        ("devices_map", "no devices map"),
        ("runtime_devices", "must be a list"),
        ("types_list", "no devicetypes list"),
        ("type_entry", "type entry must be an object"),
        ("duplicate_udid", "Duplicate simulator UDID"),
    ],
)
def test_incomplete_inventory_and_duplicate_identity_fail(mutation: str, message: str) -> None:
    devices, types = _inventories()
    family = "iphone"
    if mutation == "family":
        family = "mac"
    elif mutation == "devices_map":
        devices["devices"] = []
    elif mutation == "runtime_devices":
        devices["devices"] = {selector.IOS_27_RUNTIME: None}
    elif mutation == "types_list":
        types["devicetypes"] = {}
    elif mutation == "type_entry":
        types["devicetypes"] = [None]
    else:
        device_map = devices["devices"]
        assert isinstance(device_map, dict)
        device_list = device_map[selector.IOS_27_RUNTIME]
        assert isinstance(device_list, list)
        second_iphone = device_list[2]
        assert isinstance(second_iphone, dict)
        second_iphone["udid"] = IPHONE_UDID

    with pytest.raises(selector.SelectionError, match=message):
        selector.select_simulator(devices, types, family=family)


def test_unavailable_preferred_device_is_not_selected() -> None:
    devices, types = _inventories()
    device_map = devices["devices"]
    assert isinstance(device_map, dict)
    device_list = device_map[selector.IOS_27_RUNTIME]
    assert isinstance(device_list, list)
    preferred = device_list[1]
    assert isinstance(preferred, dict)
    preferred["isAvailable"] = False

    assert selector.select_simulator(devices, types, family="iphone")["udid"] == OTHER_IPHONE_UDID


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("wrong_runtime", "Exactly one iOS 27.0"),
        ("malformed_runtime", "invalid runtime key"),
        ("unknown_type", "Unknown device type"),
        ("invalid_udid", "Invalid simulator UDID"),
        ("control_name", "unsafe characters"),
        ("unicode_separator_name", "unsafe characters"),
        ("markdown_name", "unsafe characters"),
        ("invalid_availability", "invalid availability"),
        ("duplicate_type", "Duplicate device type"),
    ],
)
def test_malformed_or_unproven_inventory_fails(mutation: str, message: str) -> None:
    devices, types = _inventories()
    device_map = devices["devices"]
    assert isinstance(device_map, dict)
    device_list = device_map[selector.IOS_27_RUNTIME]
    assert isinstance(device_list, list)
    device = device_list[1]
    assert isinstance(device, dict)
    if mutation == "wrong_runtime":
        device_map["com.apple.CoreSimulator.SimRuntime.iOS-27-1"] = device_map.pop(
            selector.IOS_27_RUNTIME
        )
    elif mutation == "malformed_runtime":
        device_map["com.apple.CoreSimulator.SimRuntime.iOS-27-0-extra"] = []
    elif mutation == "unknown_type":
        device["deviceTypeIdentifier"] = "com.apple.CoreSimulator.SimDeviceType.Unknown"
    elif mutation == "invalid_udid":
        device["udid"] = "not-a-uuid"
    elif mutation == "control_name":
        device["name"] = "iPhone\noutput=unsafe"
    elif mutation == "unicode_separator_name":
        device["name"] = "iPhone\u2028output=unsafe"
    elif mutation == "markdown_name":
        device["name"] = "iPhone`unsafe`"
    elif mutation == "invalid_availability":
        device["isAvailable"] = "true"
    else:
        type_list = types["devicetypes"]
        assert isinstance(type_list, list)
        type_list.append({"identifier": IPHONE_TYPE, "productFamily": "iPhone"})

    with pytest.raises(selector.SelectionError, match=message):
        selector.select_simulator(devices, types, family="iphone")


def test_cli_writes_family_and_udid_only_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    devices, types = _inventories()
    output_path = tmp_path / "github-output"
    summary_path = tmp_path / "summary"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setattr(selector.shutil, "which", lambda name: "/usr/bin/xcrun")
    monkeypatch.setattr(
        selector,
        "_native_inventory",
        lambda _xcrun, *args: devices if args[0] == "devices" else types,
    )
    monkeypatch.setattr(selector.sys, "argv", ["select_ios_simulator.py", "--family", "ipad"])

    assert selector.main() == 0
    output = output_path.read_text()
    assert "family=ipad\n" in output
    assert f"destination=platform=iOS Simulator,id={IPAD_UDID}\n" in output
    assert "ios_runtime_id=com.apple.CoreSimulator.SimRuntime.iOS-27-0" in output
    assert "### iOS Destination Selection" in summary_path.read_text()


def test_cli_failure_does_not_publish_a_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    devices, types = _inventories()
    output_path = tmp_path / "github-output"
    summary_path = tmp_path / "summary"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setattr(selector.shutil, "which", lambda name: "/usr/bin/xcrun")
    monkeypatch.setattr(
        selector,
        "_native_inventory",
        lambda _xcrun, *args: devices if args[0] == "devices" else types,
    )
    monkeypatch.setattr(selector.sys, "argv", ["select_ios_simulator.py", "--family", "ipad"])
    device_map = devices["devices"]
    assert isinstance(device_map, dict)
    device_map[selector.IOS_27_RUNTIME] = []

    assert selector.main() == 1
    assert not output_path.exists()
    assert not summary_path.exists()


@pytest.mark.parametrize("missing", ["xcrun", "github_output", "invalid_json"])
def test_cli_missing_prerequisite_fails_before_outputs(
    missing: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    devices, types = _inventories()
    output_path = tmp_path / "github-output"
    summary_path = tmp_path / "summary"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setattr(selector.sys, "argv", ["select_ios_simulator.py", "--family", "iphone"])
    monkeypatch.setattr(
        selector.shutil, "which", lambda name: None if missing == "xcrun" else "/usr/bin/xcrun"
    )
    if missing == "invalid_json":
        monkeypatch.setattr(
            selector.subprocess,
            "run",
            lambda argv, **kwargs: selector.subprocess.CompletedProcess(argv, 0, stdout="{"),
        )
    else:
        monkeypatch.setattr(
            selector,
            "_native_inventory",
            lambda _xcrun, *args: devices if args[0] == "devices" else types,
        )
    if missing == "github_output":
        monkeypatch.delenv("GITHUB_OUTPUT")

    assert selector.main() == 1
    assert not output_path.exists()
    assert not summary_path.exists()


def test_cli_summary_is_optional(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    devices, types = _inventories()
    output_path = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(selector.shutil, "which", lambda name: "/usr/bin/xcrun")
    monkeypatch.setattr(
        selector,
        "_native_inventory",
        lambda _xcrun, *args: devices if args[0] == "devices" else types,
    )
    monkeypatch.setattr(selector.sys, "argv", ["select_ios_simulator.py", "--family", "iphone"])

    assert selector.main() == 0
    assert f"udid={IPHONE_UDID}\n" in output_path.read_text()


def test_native_inventory_uses_resolved_xcrun_with_exact_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> object:
        calls.append(args)
        return type("Result", (), {"stdout": json.dumps({"devices": {}})})()

    monkeypatch.setattr(selector.subprocess, "run", fake_run)
    assert selector._native_inventory("/usr/bin/xcrun", "devices", "available") == {"devices": {}}
    assert calls == [["/usr/bin/xcrun", "simctl", "list", "devices", "available", "-j"]]
