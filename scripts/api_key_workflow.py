#!/usr/bin/env python3
"""Automate end-to-end API key workflow checks.

This helper script exercises the enhanced ``update_api_key`` module without
requiring manual environment fiddling. It can:

* create an isolated (temporary) ``HOME`` directory and write sample keys there;
* populate both premium and free profiles (or a subset) using supplied keys;
* run the diagnostics routine to confirm encryption, metadata, and .env entries;
* optionally keep the sandbox around for inspection.

By default the script operates against a temporary directory and uses demo keys
that satisfy validation rules. Supply ``--home`` + real keys to operate on an
explicit directory.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from secure_config import ENCRYPTION_AVAILABLE
from update_api_key import PROFILE_CONFIG, run_diagnostics, update_api_key

try:
    from unittest.mock import patch
except ImportError as exc:  # pragma: no cover - Python always ships mock
    raise SystemExit(f"unittest.mock is required: {exc}") from exc

if not ENCRYPTION_AVAILABLE:
    raise SystemExit(
        "cryptography library not available. Install with `pip install cryptography` before running this script."
    )

DEMO_PREMIUM_KEY = "sk-premium-demo-aaaaaaaaaaaaaaaaaaaa"
DEMO_FREE_KEY = "sk-free-demo-bbbbbbbbbbbbbbbbbbbbbb"


@contextlib.contextmanager
def sandbox_home(target_home: Path):
    """Temporarily redirect Path.home()/HOME to ``target_home``."""

    target_home = target_home.expanduser().resolve()
    target_home.mkdir(parents=True, exist_ok=True)
    # stash originals
    original_env_home = os.environ.get("HOME")

    patches = [
        patch("pathlib.Path.home", return_value=target_home),
        patch("update_api_key.Path.home", return_value=target_home),
        patch("secure_config.Path.home", return_value=target_home),
    ]

    with contextlib.ExitStack() as stack:
        for patcher in patches:
            stack.enter_context(patcher)
        os.environ["HOME"] = str(target_home)
        try:
            yield target_home
        finally:
            if original_env_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = original_env_home


def ensure_permissions(paths: Iterable[Path]) -> None:
    """Best-effort chmod 600 on provided paths."""

    for path in paths:
        try:
            if path.exists():
                os.chmod(path, 0o600)
        except OSError:
            pass  # leave warnings to diagnostics


def store_keys(
    home: Path, premium: Optional[str], free: Optional[str], source: str
) -> tuple[List[str], bool]:
    """Store keys for the requested profiles and return touched profiles + success flag."""

    touched: List[str] = []
    all_ok = True
    cursor_dir = home / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    env_file = cursor_dir / ".env"
    env_file.touch(exist_ok=True)
    mcp_file = cursor_dir / "mcp.json"
    if not mcp_file.exists():
        mcp_file.write_text(json.dumps({"mcpServers": {}}, indent=2))
    settings_file = cursor_dir / "settings.json"
    if not settings_file.exists():
        settings_file.write_text(json.dumps({}, indent=2))

    with sandbox_home(home):
        if premium:
            result = update_api_key(premium, profile="premium", source=source)
            all_ok = all_ok and result
            if result:
                touched.append("premium")
        if free:
            result = update_api_key(free, profile="free", source=source)
            all_ok = all_ok and result
            if result:
                touched.append("free")

        ensure_permissions(
            [
                env_file,
                cursor_dir / "key.meta.json",
                cursor_dir / ".key",
                mcp_file,
                settings_file,
            ]
        )

    return touched, all_ok


def run_verify(home: Path, profiles: Iterable[str], stale_days: int) -> bool:
    profiles = list(profiles)
    if not profiles:
        profiles = list(PROFILE_CONFIG.keys())

    with sandbox_home(home):
        return run_diagnostics(profiles=profiles, threshold_days=stale_days)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate PulsePlate API key setup + diagnostics")
    parser.add_argument(
        "--home", type=Path, help="Directory to treat as HOME/.cursor (defaults to temp sandbox)"
    )
    parser.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="Keep temporary sandbox directory instead of cleaning it up",
    )
    parser.add_argument("--premium", help="Premium API key value to store")
    parser.add_argument("--free", help="Free-tier API key value to store")
    parser.add_argument("--skip-premium", action="store_true", help="Skip premium profile updates")
    parser.add_argument("--skip-free", action="store_true", help="Skip free profile updates")
    parser.add_argument("--source", default="automation-script", help="Metadata/audit source label")
    parser.add_argument(
        "--stale-days",
        type=int,
        default=30,
        help="Pass-through to diagnostics stale key warning threshold",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only run diagnostics (no key updates). Requires --home when skipping updates.",
    )
    return parser.parse_args(argv)


def resolve_keys(
    args: argparse.Namespace, using_temp_home: bool
) -> tuple[Optional[str], Optional[str]]:
    premium_key: Optional[str] = None
    free_key: Optional[str] = None

    if not args.skip_premium:
        if args.premium:
            premium_key = args.premium
        elif using_temp_home:
            premium_key = DEMO_PREMIUM_KEY
        elif not args.verify_only:
            raise SystemExit("--premium is required when targeting a real home directory")

    if not args.skip_free:
        if args.free:
            free_key = args.free
        elif using_temp_home:
            free_key = DEMO_FREE_KEY
        elif not args.verify_only:
            raise SystemExit("--free is required when targeting a real home directory")

    return premium_key, free_key


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    if args.home is None:
        if args.keep_sandbox:
            sandbox_root = Path(tempfile.mkdtemp(prefix="pulseplate-api-key-"))
            using_temp_home = True
        else:
            sandbox_manager = tempfile.TemporaryDirectory(prefix="pulseplate-api-key-")
            sandbox_root = Path(sandbox_manager.name)
            using_temp_home = True
    else:
        sandbox_root = args.home.expanduser().resolve()
        sandbox_root.mkdir(parents=True, exist_ok=True)
        sandbox_manager = None
        using_temp_home = False

    premium_key, free_key = resolve_keys(args, using_temp_home)

    touched_profiles: List[str] = []
    store_success = True

    if not args.verify_only:
        touched_profiles, store_success = store_keys(
            sandbox_root, premium=premium_key, free=free_key, source=args.source
        )
        if touched_profiles:
            print("Stored profiles:", ", ".join(touched_profiles))
        else:
            print("No profiles updated (nothing to do).")

    profiles_to_check = touched_profiles or [
        p for p in PROFILE_CONFIG if not getattr(args, f"skip_{p}", False)
    ]
    ok = run_verify(sandbox_root, profiles=profiles_to_check, stale_days=args.stale_days)
    final_ok = store_success and ok
    if not store_success:
        print("One or more profiles failed to update.")
    print("Diagnostics status:", "OK" if final_ok else "Issues detected")
    print("Sandbox HOME:", sandbox_root)

    if args.keep_sandbox:
        print("Sandbox preserved for inspection.")
    elif args.home is None and not args.keep_sandbox:
        # TemporaryDirectory automatically cleans up on GC; keep reference until after run
        try:
            sandbox_manager.cleanup()
        except Exception:
            pass

    return 0 if final_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
