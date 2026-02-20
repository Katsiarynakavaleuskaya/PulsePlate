#!/usr/bin/env python3
"""Compute deterministic silhouette hash and density metrics for icon rasters.

Contract intent:
- Convert image to grayscale.
- Binarize with locked threshold.
- Normalize to 1-bit mask semantics (0/1 bytes).
- Hash raw mask bytes using SHA-256.

This is designed for L4 icon drift control in design governance docs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

LOCKED_THRESHOLD = 10
WARNING_DELTA_PERCENT = 1.0
HARD_FAIL_DELTA_PERCENT = 3.0


def compute_mask(path: Path, threshold: int = LOCKED_THRESHOLD) -> tuple[bytes, int, int]:
    """Return mask bytes, white pixel count, and total pixels."""
    image = Image.open(path).convert("L")
    pixels = image.tobytes()
    mask = bytearray(len(pixels))

    white = 0
    for idx, px in enumerate(pixels):
        is_white = 1 if px > threshold else 0
        mask[idx] = is_white
        white += is_white

    return bytes(mask), white, len(mask)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pct(part: int, total: int) -> float:
    return (part / total) * 100.0 if total else 0.0


def classify_density_delta(delta_percent: float) -> str:
    return (
        "hard_fail"
        if delta_percent > HARD_FAIL_DELTA_PERCENT
        else "warning" if delta_percent > WARNING_DELTA_PERCENT else "ok"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic silhouette hash tool.")
    parser.add_argument("image_path", type=Path, help="Path to PNG image.")
    parser.add_argument(
        "--threshold",
        type=int,
        default=LOCKED_THRESHOLD,
        help=f"Binarization threshold (default: {LOCKED_THRESHOLD}).",
    )
    parser.add_argument(
        "--baseline-white-ratio",
        type=float,
        default=None,
        help="Optional baseline white ratio percent for drift classification.",
    )
    parser.add_argument(
        "--baseline-black-ratio",
        type=float,
        default=None,
        help="Optional baseline black ratio percent for drift classification.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output.",
    )
    args = parser.parse_args()

    if args.threshold != LOCKED_THRESHOLD:
        raise SystemExit(
            f"Threshold mismatch: got {args.threshold}, expected locked {LOCKED_THRESHOLD}. "
            "Threshold change requires version bump."
        )

    mask_bytes, white, total = compute_mask(args.image_path, threshold=args.threshold)
    black = total - white
    white_ratio = pct(white, total)
    black_ratio = pct(black, total)
    digest = sha256_hex(mask_bytes)

    payload: dict[str, str | int | float | None] = {
        "image_path": str(args.image_path),
        "threshold": args.threshold,
        "silhouette_mask_sha256": digest,
        "white_pixels": white,
        "black_pixels": black,
        "total_pixels": total,
        "white_pixel_ratio_percent": round(white_ratio, 6),
        "black_pixel_ratio_percent": round(black_ratio, 6),
        "density_delta_percent": None,
        "density_status": None,
        "black_density_delta_percent": None,
        "black_density_status": None,
    }

    if args.baseline_white_ratio is not None:
        delta = abs(white_ratio - args.baseline_white_ratio)
        payload["density_delta_percent"] = round(delta, 6)
        payload["density_status"] = classify_density_delta(delta)
    if args.baseline_black_ratio is not None:
        black_delta = abs(black_ratio - args.baseline_black_ratio)
        payload["black_density_delta_percent"] = round(black_delta, 6)
        payload["black_density_status"] = classify_density_delta(black_delta)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print(f"image_path={payload['image_path']}")
    print(f"threshold={payload['threshold']}")
    print(f"silhouette_mask_sha256={payload['silhouette_mask_sha256']}")
    print(f"white_pixel_ratio_percent={payload['white_pixel_ratio_percent']}")
    print(f"black_pixel_ratio_percent={payload['black_pixel_ratio_percent']}")
    if payload["density_delta_percent"] is not None:
        print(f"density_delta_percent={payload['density_delta_percent']}")
        print(f"density_status={payload['density_status']}")
    if payload["black_density_delta_percent"] is not None:
        print(f"black_density_delta_percent={payload['black_density_delta_percent']}")
        print(f"black_density_status={payload['black_density_status']}")


if __name__ == "__main__":
    main()
