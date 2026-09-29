"""Select one exact iOS 27.0 simulator from a requested device family."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404: bounded native simctl inventory reads require a subprocess (remove-by: 2026-10-31, ref: PR-CAB-06)
import sys
from typing import Any
import unicodedata
from uuid import UUID

IOS_27_RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
FAMILIES = {"iphone": "iPhone", "ipad": "iPad"}
PREFERRED_NAMES = {
    "iphone": ("iPhone 18 Pro Max", "iPhone 18 Pro", "iPhone 17e", "iPhone 17"),
    "ipad": (
        "iPad Pro 13-inch (M5)",
        "iPad Pro 11-inch (M5)",
        "iPad Air 13-inch (M4)",
        "iPad Air 11-inch (M4)",
    ),
}
UDID_RE = re.compile(r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\Z")
IOS_RUNTIME_RE = re.compile(r"com\.apple\.CoreSimulator\.SimRuntime\.iOS-\d+-\d+\Z")


class SelectionError(ValueError):
    """The native simulator inventory cannot prove a valid family destination."""


def _safe_text(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(
            unicodedata.category(char).startswith("C") or char in "\u2028\u2029`" for char in value
        )
    ):
        raise SelectionError(f"{label} must be nonempty text without unsafe characters")
    return value


def select_simulator(
    devices_inventory: Any,
    types_inventory: Any,
    *,
    family: str,
    preferred_names: tuple[str, ...] | None = None,
) -> dict[str, str]:
    """Use simctl productFamily as the sole family recognizer; never cross families."""
    if family not in FAMILIES:
        raise SelectionError(f"Unsupported simulator family: {family}")
    if not isinstance(devices_inventory, dict) or not isinstance(
        devices_inventory.get("devices"), dict
    ):
        raise SelectionError("simctl devices inventory has no devices map")
    devices = devices_inventory["devices"]
    for key in devices:
        if not isinstance(key, str) or (
            key.startswith("com.apple.CoreSimulator.SimRuntime.iOS-")
            and not IOS_RUNTIME_RE.fullmatch(key)
        ):
            raise SelectionError("simctl devices inventory has an invalid runtime key")
    ios_runtimes = [
        key for key in devices if isinstance(key, str) and IOS_RUNTIME_RE.fullmatch(key)
    ]
    if ios_runtimes.count(IOS_27_RUNTIME) != 1:
        raise SelectionError("Exactly one iOS 27.0 simulator runtime is required")
    runtime_devices = devices[IOS_27_RUNTIME]
    if not isinstance(runtime_devices, list):
        raise SelectionError("iOS 27.0 devices inventory must be a list")
    if not isinstance(types_inventory, dict) or not isinstance(
        types_inventory.get("devicetypes"), list
    ):
        raise SelectionError("simctl device types inventory has no devicetypes list")

    families_by_type: dict[str, str] = {}
    for item in types_inventory["devicetypes"]:
        if not isinstance(item, dict):
            raise SelectionError("simctl device type entry must be an object")
        identifier = _safe_text(item.get("identifier"), label="device type identifier")
        product_family = _safe_text(item.get("productFamily"), label="productFamily")
        if identifier in families_by_type:
            raise SelectionError(f"Duplicate device type identifier: {identifier}")
        families_by_type[identifier] = product_family

    candidates: list[dict[str, str]] = []
    seen_udids: set[str] = set()
    for item in runtime_devices:
        if not isinstance(item, dict) or not isinstance(item.get("isAvailable"), bool):
            raise SelectionError("iOS 27.0 device entry has invalid availability")
        if not item["isAvailable"]:
            continue
        name = _safe_text(item.get("name"), label="device name")
        type_id = _safe_text(item.get("deviceTypeIdentifier"), label="device type identifier")
        if type_id not in families_by_type:
            raise SelectionError(f"Unknown device type identifier: {type_id}")
        udid = _safe_text(item.get("udid"), label="UDID")
        if not UDID_RE.fullmatch(udid):
            raise SelectionError(f"Invalid simulator UDID for {name}")
        if str(UUID(udid)).casefold() in seen_udids:
            raise SelectionError(f"Duplicate simulator UDID for {name}")
        seen_udids.add(str(UUID(udid)).casefold())
        if families_by_type[type_id] == FAMILIES[family]:
            candidates.append({"device_name": name, "udid": udid})

    if not candidates:
        raise SelectionError(f"No available {FAMILIES[family]} simulator on iOS 27.0")
    preferred = PREFERRED_NAMES[family] if preferred_names is None else preferred_names
    order = {name: index for index, name in enumerate(preferred)}
    candidates.sort(
        key=lambda item: (
            order.get(item["device_name"], len(order)),
            item["device_name"],
            item["udid"],
        )
    )
    selected = candidates[0]
    return {
        "family": family,
        "ios_runtime_id": IOS_27_RUNTIME,
        "device_name": selected["device_name"],
        "udid": selected["udid"],
        "destination": f"platform=iOS Simulator,id={selected['udid']}",
    }


def _native_inventory(xcrun: str, *args: str) -> Any:
    result = subprocess.run(  # nosec B603: resolved absolute xcrun, fixed simctl argv, no shell (remove-by: 2026-10-31, ref: PR-CAB-06)
        [xcrun, "simctl", "list", *args, "-j"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, choices=tuple(FAMILIES))
    args = parser.parse_args()
    try:
        xcrun = shutil.which("xcrun")
        if not xcrun or not Path(xcrun).is_absolute():
            raise SelectionError("xcrun is unavailable as an absolute executable")
        result = select_simulator(
            _native_inventory(xcrun, "devices", "available"),
            _native_inventory(xcrun, "devicetypes"),
            family=args.family,
        )
        output_path = os.environ.get("GITHUB_OUTPUT")
        if not output_path:
            raise SelectionError("GITHUB_OUTPUT is required")
        with open(output_path, "a", encoding="utf-8") as output:
            for key, value in result.items():
                print(f"{key}={value}", file=output)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as summary:
                print("### iOS Destination Selection", file=summary)
                for key, value in result.items():
                    print(f"- {key}: `{value.replace('`', '')}`", file=summary)
        for key, value in result.items():
            print(f"{key}={value}")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, SelectionError) as exc:
        print(f"::error::iOS simulator selection failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
