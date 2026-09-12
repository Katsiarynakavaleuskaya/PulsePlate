"""Scoped GHCR-only native SDK credential placement and owned-directory cleanup.

No token decoding, registry discovery, HOME replacement or subprocess gateway.
Native Docker creates the inline auth; the pinned SDK reads the fixed home path.
"""

from __future__ import annotations

import argparse
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


def identity(path: Path, directory: bool = False) -> dict:
    info = path.lstat()
    if (
        not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        or info.st_uid != os.getuid()
        or info.st_gid != os.getgid()
        or (not directory and info.st_nlink != 1)
        or stat.S_IMODE(info.st_mode) & 0o022
    ):
        raise ValueError("Native credential object ownership/type/links/permissions changed")
    value: dict[str, Any] = {
        "dev": info.st_dev,
        "ino": info.st_ino,
        "uid": info.st_uid,
        "gid": info.st_gid,
        "mode": stat.S_IMODE(info.st_mode),
    }
    if not directory:
        value["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return value


def read(path: Path) -> dict:
    identity(path)
    value = loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Native credential receipt must be an object")
    return value


def write(path: Path, value: dict) -> None:
    data = json.dumps(value, sort_keys=True).encode()
    if path.exists():
        identity(path)
    temporary = path.with_name(path.name + ".next")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
    os.replace(temporary, path)


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
        or identity(directory, True) != receipt["root"]
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
    if identity(generated.parent, True)["mode"] != 0o700:
        raise ValueError("Native GHCR login subdirectory must remain private")
    config = read(generated)
    auths = config.get("auths")
    if (
        not isinstance(auths, dict)
        or set(auths) != {"ghcr.io"}
        or not isinstance(auths["ghcr.io"], dict)
        or not isinstance(auths["ghcr.io"].get("auth"), str)
        or not auths["ghcr.io"]["auth"]
    ):
        raise ValueError("Native login must generate exactly one inline GHCR auth")
    if (directory / SDK).exists():
        raise ValueError("Native SDK credential placement already active")
    created = not default.exists()
    if created:
        default.mkdir(mode=0o700)
    directory_identity = identity(default, True)
    target = default / "config.json"
    original = identity(target) if target.exists() or target.is_symlink() else None
    backup = directory / ".original-docker-config"
    if original is not None:
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(target.read_bytes())
    fd, name = tempfile.mkstemp(prefix=".pulseplate-ghcr-", dir=default)
    temporary = Path(name)
    with os.fdopen(fd, "wb") as output:
        output.write(json.dumps({"auths": auths}, sort_keys=True).encode())
    authored = identity(temporary)
    state = {
        "default": str(default),
        "directory": directory_identity,
        "created": created,
        "original": original,
        "backup": identity(backup) if original else None,
        "authored": authored,
        "temporary": str(temporary),
    }
    write(directory / SDK, state)
    if original is not None and identity(target) != original:
        raise ValueError("Default native credential config changed before installation")
    if original is None and (target.exists() or target.is_symlink()):
        raise ValueError("Default native credential config appeared before installation")
    os.replace(temporary, target)


def restore(directory: Path) -> None:
    owned(directory)
    if not (directory / SDK).exists():
        return
    state = read(directory / SDK)
    default = Path(state["default"])
    if identity(default, True) != state["directory"]:
        raise ValueError("Default native credential directory changed")
    target = default / "config.json"
    present = identity(target) if target.exists() or target.is_symlink() else None
    if "restored" in state:
        if present != state["restored"]:
            raise ValueError("Restored native config changed externally")
    elif present == state["authored"]:
        if state["original"] is None:
            target.unlink()
        else:
            backup = directory / ".original-docker-config"
            if identity(backup) != state["backup"]:
                raise ValueError("Original native config backup changed")
            fd, name = tempfile.mkstemp(prefix=".pulseplate-restore-", dir=default)
            temporary = Path(name)
            with os.fdopen(fd, "wb") as output:
                output.write(backup.read_bytes())
            temporary.chmod(state["original"]["mode"])
            os.replace(temporary, target)
        state["restored"] = identity(target) if target.exists() else None
        write(directory / SDK, state)
    elif present != state["original"]:
        raise ValueError("Authored native config changed externally; original backup retained")
    temporary = Path(state["temporary"])
    if temporary.exists():
        if identity(temporary) != state["authored"]:
            raise ValueError("Private native config sibling changed")
        temporary.unlink()
    if state["created"]:
        default.rmdir()  # Unexpected children fail; never recursively remove the home directory.
    (directory / SDK).unlink()
    if state["original"] is not None:
        (directory / ".original-docker-config").unlink()


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
    except (ValueError, OSError, KeyError) as error:
        print("Native GHCR credential placement/cleanup HOLD: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
