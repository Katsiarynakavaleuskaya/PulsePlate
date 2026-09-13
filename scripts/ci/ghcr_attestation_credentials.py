"""Scoped GHCR-only native SDK credential placement and owned-directory cleanup.

No token decoding, registry discovery, HOME replacement or subprocess gateway.
Native Docker creates the inline auth; the pinned SDK reads the fixed home path.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Any
from scripts.ci.check_pgvector_attestations import loads

PREFIXES = (
    "pulseplate-pgvector-docker-config.",
    "pulseplate-attestation-probe-auth.",
    "pulseplate-staging-native-auth.",
)
OWNER = ".native-owned.json"
SDK = ".ghcr-sdk-restore.json"
HOLDER = ".pulseplate-ghcr-sdk"


def identity(path: Path, directory: bool = False, *, role: str = "invocation_object") -> dict:
    info = path.lstat()
    if (
        not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        or info.st_uid != os.getuid()
        or info.st_gid != os.getgid()
        or (not directory and info.st_nlink != 1)
        or stat.S_IMODE(info.st_mode) & 0o022
    ):
        observed = {
            "object_role": role,
            "expected_directory": directory,
            "expected_uid": os.getuid(),
            "expected_gid": os.getgid(),
            "type_mode": stat.S_IFMT(info.st_mode),
            "uid": info.st_uid,
            "gid": info.st_gid,
            "mode": oct(stat.S_IMODE(info.st_mode)),
            "links": info.st_nlink,
            "device": info.st_dev,
            "inode": info.st_ino,
        }
        raise ValueError(
            "Native credential object ownership/type/links/permissions changed: "
            + json.dumps(observed, sort_keys=True)
        )
    value: dict[str, Any] = {
        "dev": info.st_dev,
        "ino": info.st_ino,
        "uid": info.st_uid,
        "gid": info.st_gid,
        "mode": stat.S_IMODE(info.st_mode),
        "type": stat.S_IFMT(info.st_mode),
    }
    if not directory:
        value["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return value


def read(path: Path, *, role: str = "invocation_receipt") -> dict:
    if identity(path, role=role)["mode"] != 0o600:
        raise ValueError("Native credential or recovery record must have mode0600")
    value = loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Native credential receipt must be an object")
    return value


def write(path: Path, value: dict) -> None:
    data = json.dumps(value, sort_keys=True).encode()
    if path.exists() or path.is_symlink():
        if identity(path)["mode"] != 0o600:
            raise ValueError("Native recovery record must remain mode0600 before replacement")
    temporary = path.with_name(path.name + ".next")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    created = os.fstat(fd)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    except BaseException:
        try:
            observed = temporary.lstat()
            if (observed.st_dev, observed.st_ino) == (created.st_dev, created.st_ino):
                temporary.unlink()
            else:
                print("Native journal temporary changed; retained", file=sys.stderr)
        except FileNotFoundError:
            pass
        except OSError:
            print("Native journal temporary cleanup failed; retained", file=sys.stderr)
        raise


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def directory_entry(path: Path) -> dict | None:
    """Observe an opaque directory entry without opening any of its children."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Native Docker directory entry must be an ordinary directory")
    return {
        "dev": info.st_dev,
        "ino": info.st_ino,
        "uid": info.st_uid,
        "gid": info.st_gid,
        "mode": stat.S_IMODE(info.st_mode),
        "type": stat.S_IFMT(info.st_mode),
    }


def move_directory(source: Path, destination: Path) -> None:
    """Use the supported kernel no-replace operation; never fall back to overwrite/copy."""
    if sys.platform == "darwin":
        symbol, flag = "renameatx_np", 4
    elif sys.platform.startswith("linux"):
        symbol, flag = "renameat2", 1
    else:
        raise ValueError("Native no-replace directory move is unsupported")
    try:
        operation = getattr(ctypes.CDLL(None, use_errno=True), symbol)
    except (AttributeError, OSError) as error:
        raise ValueError("Native no-replace directory move is unavailable") from error
    operation.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    operation.restype = ctypes.c_int
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    source_fd = os.open(source.parent, flags)
    try:
        destination_fd = os.open(destination.parent, flags)
        try:
            ctypes.set_errno(0)
            result = operation(
                source_fd,
                os.fsencode(source.name),
                destination_fd,
                os.fsencode(destination.name),
                flag,
            )
            if result != 0:
                raise OSError(ctypes.get_errno(), "Native no-replace directory move rejected")
            os.fsync(source_fd)
            os.fsync(destination_fd)
        finally:
            os.close(destination_fd)
    finally:
        os.close(source_fd)


def capture(directory: Path, runner_temp: Path) -> None:
    parent = runner_temp.resolve(strict=True)
    if (
        runner_temp != parent
        or directory.parent != parent
        or not directory.name.startswith(PREFIXES)
    ):
        raise ValueError("Native private directory must be a physical direct RUNNER_TEMP child")
    owned = identity(directory, True)
    if owned["mode"] != 0o700:
        raise ValueError("Native private directory must have mode0700")
    if (directory / OWNER).exists():
        raise ValueError("Native private directory already captured")
    write(directory / OWNER, {"root": owned, "runner_temp": str(parent)})


def owned(directory: Path) -> dict:
    receipt = read(directory / OWNER)
    if (
        directory.parent != Path(receipt["runner_temp"])
        or directory.parent.resolve(strict=True) != directory.parent
        or identity(directory, True, role="invocation_root") != receipt["root"]
    ):
        raise ValueError("Invocation-owned native directory identity changed")
    return receipt


def ghcr_directory(directory: Path) -> Path:
    owned(directory)
    return Path(tempfile.mkdtemp(prefix="ghcr-only-", dir=directory))


def install(directory: Path, generated: Path, default: Path) -> None:
    owned(directory)
    if generated.parent.parent != directory or generated.parent.is_symlink():
        raise ValueError("GHCR config must come from the invocation private login subdirectory")
    if identity(generated.parent, True, role="generated_ghcr_directory")["mode"] != 0o700:
        raise ValueError("Native GHCR login subdirectory must remain private")
    config = read(generated, role="generated_ghcr_config")
    auths = config.get("auths")
    if (
        not isinstance(auths, dict)
        or set(auths) != {"ghcr.io"}
        or not isinstance(auths["ghcr.io"], dict)
        or not isinstance(auths["ghcr.io"].get("auth"), str)
        or not auths["ghcr.io"]["auth"]
    ):
        raise ValueError("Native login must generate exactly one inline GHCR auth")
    if (directory / SDK).exists() or (directory / SDK).is_symlink():
        raise ValueError("Native SDK credential placement already active")
    home = default.parent
    if default.name != ".docker" or home != home.resolve(strict=True):
        raise ValueError("Native SDK default must use its physical home directory")
    parent = directory_entry(home)
    if parent is None or parent["uid"] != os.getuid() or parent["mode"] & 0o022:
        raise ValueError("Native SDK home must be owned and not group/world writable")
    holder = home / HOLDER
    if holder.exists() or holder.is_symlink():
        raise ValueError("Native SDK holder already exists; overlapping placement is unsupported")
    original = directory_entry(default)
    if original is not None and original["dev"] != parent["dev"]:
        raise ValueError("Native SDK original must remain on the home filesystem")
    state: dict[str, Any] = {
        "home": str(home),
        "home_identity": parent,
        "default": str(default),
        "original": original,
        "holder_identity": None,
        "authored": None,
        "config": None,
        "restored": False,
    }
    # Intent precedes allocations: an interrupted, unrecorded inode is HOLD, not guessed ownership.
    write(directory / SDK, state)
    holder.mkdir(mode=0o700)
    state["holder_identity"] = identity(holder, True, role="sdk_holder")
    if state["holder_identity"]["mode"] != 0o700:
        raise ValueError("Native SDK holder must be private")
    write(directory / SDK, state)
    fresh = holder / "sdk"
    fresh.mkdir(mode=0o700)
    state["authored"] = identity(fresh, True, role="authored_sdk_directory")
    if state["authored"]["mode"] != 0o700:
        raise ValueError("Native SDK directory must be private")
    write(directory / SDK, state)
    target = fresh / "config.json"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(json.dumps({"auths": auths}, sort_keys=True).encode())
        output.flush()
        os.fsync(output.fileno())
    sync_directory(fresh)
    state["config"] = identity(target, role="authored_sdk_config")
    if state["config"]["mode"] != 0o600:
        raise ValueError("Native SDK config must be private")
    # This complete record can recover either side of every following namespace move.
    write(directory / SDK, state)
    if directory_entry(home) != parent or directory_entry(default) != original:
        raise ValueError("Native SDK original or home changed before placement")
    if original is not None:
        move_directory(default, holder / "original")
        if directory_entry(holder / "original") != original:
            raise ValueError("Native SDK original changed during preservation")
    move_directory(fresh, default)
    if identity(default, True) != state["authored"]:
        raise ValueError("Native SDK authored directory changed during placement")


def _state_paths(state: dict) -> tuple[Path, Path, Path]:
    if set(state) != {
        "home",
        "home_identity",
        "default",
        "original",
        "holder_identity",
        "authored",
        "config",
        "restored",
    } or not isinstance(state["restored"], bool):
        raise ValueError("Native SDK recovery record has an unknown shape")
    if not isinstance(state["home"], str) or not isinstance(state["default"], str):
        raise ValueError("Native SDK recovery paths are invalid")
    home = Path(state["home"])
    default = Path(state["default"])
    if home != home.resolve(strict=True) or default != home / ".docker":
        raise ValueError("Native SDK recovery paths changed")
    if directory_entry(home) != state["home_identity"]:
        raise ValueError("Native SDK physical home identity changed")
    return home, default, home / HOLDER


def _authored(directory: Path, state: dict, *, removing: bool = False) -> None:
    if identity(directory, True, role="authored_sdk_directory") != state["authored"]:
        raise ValueError("Native SDK authored directory identity changed")
    if {child.name for child in directory.iterdir()} - {"config.json"}:
        raise ValueError("Native SDK authored directory contains unknown children")
    config = directory / "config.json"
    if config.exists() or config.is_symlink():
        if identity(config, role="authored_sdk_config") != state["config"]:
            raise ValueError("Native SDK authored config identity changed")
    elif state["config"] is not None and not removing:
        raise ValueError("Native SDK authored config disappeared")


def restore(directory: Path) -> None:
    owned(directory)
    if not (directory / SDK).exists() and not (directory / SDK).is_symlink():
        return
    state = read(directory / SDK)
    home, default, holder = _state_paths(state)
    original = state["original"]
    current = directory_entry(default)
    held = directory_entry(holder)
    if held is None:
        if current != original or (state["holder_identity"] is not None and not state["restored"]):
            raise ValueError("Native SDK holder disappeared before proven restoration")
        (directory / SDK).unlink()
        sync_directory(directory)
        return
    if identity(holder, True, role="sdk_holder") != state["holder_identity"]:
        raise ValueError("Native SDK holder identity is unknown or changed")
    if {child.name for child in holder.iterdir()} - {"original", "sdk"}:
        raise ValueError("Native SDK holder contains unknown children; original retained")
    backup = holder / "original"
    fresh = holder / "sdk"
    saved = directory_entry(backup)  # Only the original entry, never its children.
    staged = directory_entry(fresh)
    authored = state["authored"]
    if saved is not None and saved != original:
        raise ValueError("Native SDK saved original identity changed")
    if staged is not None:
        _authored(fresh, state, removing=state["restored"])
    if state["restored"]:
        if current != original or saved is not None:
            raise ValueError("Native SDK original restoration postcondition changed")
    else:
        if current is not None and current == authored:
            if staged is not None or saved != original or state["config"] is None:
                raise ValueError("Native SDK active topology is inconsistent")
            _authored(default, state)
            move_directory(default, fresh)
            current = directory_entry(default)
            staged = directory_entry(fresh)
            if current is not None or staged != authored:
                raise ValueError("Native SDK authored return changed identity")
        elif current != original and current is not None:
            raise ValueError("Native SDK default changed externally; original retained")
        if original is not None:
            if current is None and saved == original:
                move_directory(backup, default)
            elif current != original or saved is not None:
                raise ValueError("Native SDK original recovery topology is ambiguous")
        elif current is not None or saved is not None:
            raise ValueError("Native SDK originally absent default changed externally")
        if directory_entry(default) != original or directory_entry(backup) is not None:
            raise ValueError("Native SDK original restoration is unproven")
        if staged is None and authored is not None:
            raise ValueError("Native SDK authored state disappeared before cleanup")
        state["restored"] = True
        write(directory / SDK, state)
    # Restore O first; only then replay deletion of the finite authored config/empty dirs.
    if staged is not None:
        _authored(fresh, state, removing=True)
        config = fresh / "config.json"
        if config.exists():
            config.unlink()
            sync_directory(fresh)
        fresh.rmdir()
        sync_directory(holder)
    holder.rmdir()  # Never recurse into the original holder or any unknown child.
    sync_directory(home)
    (directory / SDK).unlink()
    sync_directory(directory)


def cleanup(directory: Path) -> None:
    owned(directory)
    restore(directory)  # Never delete the saved original before successful restoration.
    owned(directory)
    shutil.rmtree(directory)  # Python unlinks interior symlinks; root was identity-checked.


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "ghcr-directory", "install", "cleanup"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ghcr-config", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "capture":
            capture(args.directory, Path(os.environ["RUNNER_TEMP"]))
        elif args.mode == "ghcr-directory":
            print(ghcr_directory(args.directory))
        elif args.mode == "install":
            if args.ghcr_config is None:
                raise ValueError("Native SDK placement requires --ghcr-config")
            install(args.directory, args.ghcr_config, Path.home() / ".docker")
        else:
            cleanup(args.directory)
        return 0
    except OSError as error:
        print(
            "Native GHCR credential placement/cleanup HOLD: filesystem operation failed; "
            + json.dumps({"errno": error.errno}),
            file=sys.stderr,
        )
        return 1
    except (ValueError, KeyError) as error:
        print("Native GHCR credential placement/cleanup HOLD: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
