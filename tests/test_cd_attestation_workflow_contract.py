"""Workflow contract tests for CD attestation verification sequencing.

Ensures that Docker attestation verification steps only run when all upstream
attestation steps (provenance, SBOM generation, SBOM attestation) have succeeded.

Root cause: CD workflow on main failed because SBOM attestation timed out
(Rekor InternalError), but the downstream verification step still ran because
its condition only checked ``steps.build.outcome == 'success'``. The verifier
correctly failed closed (no SBOM predicate found), producing a misleading error.

Fix: gate verification on build + provenance + SBOM generation + SBOM attestation
success outcomes. Keep ``always()`` so the condition is always *evaluated* (GitHub
Actions skips ``if:`` entirely on upstream failure without ``always()``), but the
explicit outcome checks prevent the step from *running* unless all upstream steps
passed.
"""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import base64
import copy
import json
import sys
import stat
from typing import Any, IO, Iterator

import pytest

import yaml
from scripts.ci import ghcr_attestation_credentials as credentials
from scripts.ci import check_pgvector_attestations as pgvector

REPO_ROOT = Path(__file__).resolve().parents[1]
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"

STAGING_ATTESTATION_STEP_IDS = (
    "attest-staged-provenance",
    "generate-staged-sbom",
    "attest-staged-sbom",
    "attest-staged-caddy-provenance",
    "generate-staged-caddy-sbom",
    "attest-staged-caddy-sbom",
)

PRODUCTION_ATTESTATION_STEP_IDS = (
    "attest-production-provenance",
    "generate-production-sbom",
    "attest-production-sbom",
)


def _load_cd_workflow() -> dict[str, object]:
    """Load and parse the CD workflow YAML."""
    return yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))


def _sdk_fixture(tmp_path: Path, present: bool = True) -> tuple[Path, Path, Path]:
    runner = tmp_path / "runner"
    runner.mkdir()
    private = runner / "pulseplate-attestation-probe-auth.test"
    private.mkdir(mode=0o700)
    credentials.capture(private, runner)
    (private / "config.json").write_text('{"auths":{"dhi.io":{"auth":"private-dhi"}}}')
    (private / "config.json").chmod(0o600)
    default = tmp_path / "home" / ".docker"
    default.parent.mkdir(mode=0o700)
    if present:
        default.mkdir(mode=0o755)
        (default / "config.json").write_bytes(b"opaque original, not a JSON credential input\n")
        (default / "config.json").chmod(0o644)
        (default / "nested").mkdir()
        (default / "nested" / "sentinel").write_text("unchanged")
    login = credentials.ghcr_directory(private) / "config.json"
    login.write_text('{"auths":{"ghcr.io":{"auth":"nonsecret-native-login"}}}')
    login.chmod(0o600)
    return private, login, default


def _entry_identity(path: Path) -> tuple[int, ...] | None:
    if not path.exists() and not path.is_symlink():
        return None
    value = path.lstat()
    return (
        value.st_dev,
        value.st_ino,
        value.st_uid,
        value.st_gid,
        value.st_mode,
    )


def _original_snapshot(default: Path) -> dict[str, tuple[int, ...] | None]:
    names = (".", "config.json", "nested", "nested/sentinel")
    return {name: _entry_identity(default / name) for name in names}


def _fresh_cleanup(private: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.ghcr_attestation_credentials",
            "cleanup",
            "--directory",
            str(private),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize("present", [False, True])
def test_native_ghcr_default_reader_bridge_preserves_private_dhi_and_original_inodes(
    tmp_path: Path, present: bool
) -> None:
    private, login, default = _sdk_fixture(tmp_path, present)
    before = _original_snapshot(default)
    private_dhi = (private / "config.json").read_bytes()
    credentials.install(private, login, default)
    # Same fixed location as the pinned SDK reader; actual OCI proof remains hosted.
    assert json.loads((default / "config.json").read_text()) == {
        "auths": {"ghcr.io": {"auth": "nonsecret-native-login"}}
    }
    assert default.stat().st_mode & 0o777 == 0o700
    assert (default / "config.json").stat().st_mode & 0o777 == 0o600
    assert (private / "config.json").read_bytes() == private_dhi
    assert _entry_identity(default) != before["."]
    nested = private / "buildx" / "instances"
    nested.mkdir(parents=True)
    (nested / "native-metadata").write_text("owned")
    sentinel = tmp_path / "unrelated"
    sentinel.write_text("preserve")
    (private / "interior-link").symlink_to(sentinel)
    result = _fresh_cleanup(private)
    assert result.returncode == 0, result.stderr
    assert _original_snapshot(default) == before
    assert not (default.parent / credentials.HOLDER).exists()
    assert not private.exists() and sentinel.read_text() == "preserve"


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "unreadable", "foreign_metadata"])
def test_original_children_are_opaque_and_preserved_without_reading_or_enumerating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    config = default / "config.json"
    if kind == "symlink":
        config.unlink()
        config.symlink_to(default / "nested" / "sentinel")
    elif kind == "hardlink":
        (default / "linked-config").hardlink_to(config)
    elif kind == "unreadable":
        config.chmod(0)
    else:
        default.chmod(0o777)  # O is preserved, not admitted as authored credential input.
    before = _original_snapshot(default)
    original_inode = default.lstat().st_ino
    real_lstat, real_open, real_iterdir = Path.lstat, Path.open, Path.iterdir

    def metadata(path: Path) -> os.stat_result:
        value = real_lstat(path)
        if value.st_ino == original_inode and kind == "foreign_metadata":
            fields = list(value)
            fields[4], fields[5] = os.getuid() + 1, os.getgid() + 1
            return os.stat_result(fields)
        return value

    def original_ancestor(path: Path) -> bool:
        for parent in (path, *path.parents):
            if parent.exists() and real_lstat(parent).st_ino == original_inode:
                return True
        return False

    def no_original_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        assert not original_ancestor(path), "adapter must not open original contents"
        return real_open(path, *args, **kwargs)

    def no_original_enumeration(path: Path) -> Iterator[Path]:
        assert not original_ancestor(path), "adapter must not enumerate original children"
        return real_iterdir(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "lstat", metadata)
        patch.setattr(Path, "open", no_original_open)
        patch.setattr(Path, "iterdir", no_original_enumeration)
        credentials.install(private, login, default)
        credentials.cleanup(private)
    assert _original_snapshot(default) == before


@pytest.mark.parametrize("object_role", ["generated_ghcr_directory", "generated_ghcr_config"])
def test_native_install_rejection_identifies_only_object_metadata(
    tmp_path: Path, object_role: str
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    selected = login.parent if object_role.endswith("directory") else login
    selected.chmod(0o770 if selected.is_dir() else 0o660)
    before = selected.lstat()
    with pytest.raises(ValueError, match="ownership/type/links/permissions changed") as error:
        credentials.install(private, login, default)
    message = str(error.value)
    assert json.loads(message.split(": ", 1)[1]) == {
        "object_role": object_role,
        "expected_directory": selected.is_dir(),
        "expected_uid": os.getuid(),
        "expected_gid": os.getgid(),
        "type_mode": stat.S_IFMT(before.st_mode),
        "uid": before.st_uid,
        "gid": before.st_gid,
        "mode": oct(stat.S_IMODE(before.st_mode)),
        "links": before.st_nlink,
        "device": before.st_dev,
        "inode": before.st_ino,
    }
    assert str(tmp_path) not in message and "nonsecret-native-login" not in message
    assert "opaque original" not in message
    assert not (private / credentials.SDK).exists()


@pytest.mark.parametrize(
    "kind",
    [
        "symlink",
        "hardlink",
        "fifo",
        "foreign_uid",
        "foreign_gid",
        "readable_config",
        "helper_only",
        "dhi_source",
        "foreign_root",
    ],
)
def test_generated_credentials_remain_strict_and_original_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    if kind in {"symlink", "fifo"}:
        login.unlink()
        if kind == "symlink":
            login.symlink_to(default / "config.json")
        else:
            os.mkfifo(login)
    elif kind == "hardlink":
        (login.parent / "other").hardlink_to(login)
    elif kind in {"foreign_uid", "foreign_gid"}:
        original_lstat = Path.lstat
        target_inode = login.lstat().st_ino

        def foreign_metadata(path: Path) -> os.stat_result:
            value = original_lstat(path)
            if value.st_ino == target_inode:
                fields = list(value)
                fields[4 if kind == "foreign_uid" else 5] += 1
                return os.stat_result(fields)
            return value

        monkeypatch.setattr(Path, "lstat", foreign_metadata)
    elif kind == "helper_only":
        login.write_text('{"credsStore":"external"}')
    elif kind == "dhi_source":
        login.write_text('{"auths":{"ghcr.io":{"auth":"native"},"dhi.io":{"auth":"private"}}}')
    elif kind == "readable_config":
        login.chmod(0o644)
    else:
        private.chmod(0o755)
    with pytest.raises(ValueError):
        credentials.install(private, login, default)
    assert _original_snapshot(default) == before
    assert not (private / credentials.SDK).exists()


@pytest.mark.parametrize(
    "kind",
    [
        "symlink",
        "file",
        "fifo",
        "home_symlink",
        "home_writable",
        "holder_occupied",
        "journal_symlink",
    ],
)
def test_invalid_original_entry_parent_or_overlap_does_not_start_transaction(
    tmp_path: Path, kind: str
) -> None:
    private, login, default = _sdk_fixture(tmp_path, present=False)
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("preserve")
    if kind == "symlink":
        default.symlink_to(sentinel)
    elif kind == "file":
        default.write_text("not a directory")
    elif kind == "fifo":
        os.mkfifo(default)
    elif kind == "home_symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(default.parent, target_is_directory=True)
        default = alias / ".docker"
    elif kind == "home_writable":
        default.parent.chmod(0o777)
    elif kind == "holder_occupied":
        (default.parent / credentials.HOLDER).mkdir()
    else:
        (private / credentials.SDK).symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError):
        credentials.install(private, login, default)
    assert sentinel.read_text() == "preserve"
    assert not (default.parent / credentials.HOLDER / "original").exists()


@pytest.mark.parametrize("move_number", [1, 2, 3, 4])
@pytest.mark.parametrize("after", [False, True])
def test_every_native_move_interruption_recovers_original_in_fresh_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, move_number: int, after: bool
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    native_move = credentials.move_directory
    count = 0

    def interrupted(source: Path, destination: Path) -> None:
        nonlocal count
        count += 1
        if count == move_number and not after:
            raise OSError("before selected native move")
        native_move(source, destination)
        if count == move_number and after:
            raise OSError("after selected native move")

    with monkeypatch.context() as patch:
        patch.setattr(credentials, "move_directory", interrupted)
        with pytest.raises(OSError, match="selected native move"):
            credentials.install(private, login, default)
            credentials.cleanup(private)
    assert (private / credentials.SDK).exists()
    result = _fresh_cleanup(private)
    assert result.returncode == 0, result.stderr
    assert _original_snapshot(default) == before and not private.exists()


@pytest.mark.parametrize("move_number", [1, 2, 3, 4])
def test_process_exit_after_native_move_leaves_replayable_journal(
    tmp_path: Path, move_number: int
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    script = """
import os
from pathlib import Path
import sys
from scripts.ci import ghcr_attestation_credentials as c
real_move = c.move_directory
count = 0
def exit_after_move(source, destination):
    global count
    count += 1
    real_move(source, destination)
    if count == int(sys.argv[4]):
        os._exit(79)
c.move_directory = exit_after_move
c.install(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
c.cleanup(Path(sys.argv[1]))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(private), str(login), str(default), str(move_number)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 79, result.stderr
    recovered = _fresh_cleanup(private)
    assert recovered.returncode == 0, recovered.stderr
    assert _original_snapshot(default) == before and not private.exists()


@pytest.mark.parametrize("kind", ["empty_directory", "nonempty_directory", "file", "symlink"])
def test_kernel_no_replace_preserves_both_entries_on_occupied_destination(
    tmp_path: Path, kind: str
) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    (source / "original").write_text("retained")
    if kind.endswith("directory"):
        destination.mkdir()
        if kind == "nonempty_directory":
            (destination / "other").write_text("occupied")
    elif kind == "symlink":
        destination.symlink_to(source, target_is_directory=True)
    else:
        destination.write_text("occupied")
    before = (_entry_identity(source), _entry_identity(destination))
    with pytest.raises(OSError, match="no-replace directory move rejected"):
        credentials.move_directory(source, destination)
    assert (_entry_identity(source), _entry_identity(destination)) == before
    assert (source / "original").read_text() == "retained"


@pytest.mark.parametrize("move_number", [1, 2, 3, 4])
def test_each_transaction_destination_collision_holds_without_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, move_number: int
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    native_move = credentials.move_directory
    count = 0
    occupied: Path | None = None
    occupied_identity: tuple[int, ...] | None = None

    def collide(source: Path, destination: Path) -> None:
        nonlocal count, occupied, occupied_identity
        count += 1
        if count == move_number:
            destination.mkdir()
            occupied, occupied_identity = destination, _entry_identity(destination)
        native_move(source, destination)

    with monkeypatch.context() as patch:
        patch.setattr(credentials, "move_directory", collide)
        with pytest.raises(OSError, match="no-replace directory move rejected"):
            credentials.install(private, login, default)
            credentials.cleanup(private)
    assert occupied is not None and _entry_identity(occupied) == occupied_identity
    original = default if move_number == 1 else default.parent / credentials.HOLDER / "original"
    assert _original_snapshot(original) == before
    assert (private / credentials.SDK).exists()
    recovered = _fresh_cleanup(private)
    assert recovered.returncode == 1 and "HOLD" in recovered.stderr
    assert _entry_identity(occupied) == occupied_identity
    assert _original_snapshot(original) == before


@pytest.mark.parametrize("fault", ["platform", "symbol", "cross_device"])
def test_native_no_replace_never_falls_back_to_overwrite_or_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    before = _entry_identity(source)
    if fault == "platform":
        monkeypatch.setattr(credentials.sys, "platform", "unsupported")
    elif fault == "symbol":
        monkeypatch.setattr(credentials.ctypes, "CDLL", lambda *a, **kw: object())
    else:

        class RejectingNative:
            def __call__(self, *args: object) -> int:
                credentials.ctypes.set_errno(18)  # EXDEV on the supported platforms.
                return -1

        class Library:
            renameat2 = RejectingNative()
            renameatx_np = RejectingNative()

        monkeypatch.setattr(credentials.ctypes, "CDLL", lambda *a, **kw: Library())
    with pytest.raises((ValueError, OSError)):
        credentials.move_directory(source, destination)
    assert _entry_identity(source) == before and not destination.exists()


@pytest.mark.parametrize(
    "fault",
    [
        "home",
        "holder",
        "original",
        "default",
        "config",
        "authored_child",
        "holder_child",
        "journal_symlink",
    ],
)
def test_unknown_recovery_state_holds_and_retains_original_and_journal(
    tmp_path: Path, fault: str
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    credentials.install(private, login, default)
    holder = default.parent / credentials.HOLDER
    original = holder / "original"
    if fault == "home":
        default.parent.chmod(0o755)
    elif fault in {"holder", "original", "default"}:
        target = {"holder": holder, "original": original, "default": default}[fault]
        target.chmod(0o750)
    elif fault == "config":
        (default / "config.json").write_text("external change")
    elif fault in {"authored_child", "holder_child"}:
        target = default if fault == "authored_child" else holder
        (target / "unexpected").write_text("preserve")
    else:
        (private / credentials.SDK).rename(private / "retained-journal")
        (private / credentials.SDK).symlink_to(private / "missing")
    result = _fresh_cleanup(private)
    assert result.returncode == 1 and "HOLD" in result.stderr
    assert private.exists() and (private / credentials.SDK).is_symlink() == (
        fault == "journal_symlink"
    )
    assert original.exists()
    assert original.stat().st_ino == before["."][1]
    assert (original / "config.json").stat().st_ino == before["config.json"][1]


@pytest.mark.parametrize("fault", ["home", "holder", "original", "default", "config"])
def test_replaced_recovery_objects_do_not_gain_cleanup_authority(
    tmp_path: Path, fault: str
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    credentials.install(private, login, default)
    holder = default.parent / credentials.HOLDER
    original = holder / "original"
    target = {
        "home": default.parent,
        "holder": holder,
        "original": original,
        "default": default,
        "config": default / "config.json",
    }[fault]
    retained = target.with_name(target.name + "-retained")
    was_directory = target.is_dir()
    original_mode = stat.S_IMODE(target.stat().st_mode)
    target.rename(retained)
    if was_directory:
        target.mkdir(mode=original_mode)
    else:
        target.write_bytes(retained.read_bytes())  # Same bytes never substitute for inode identity.
        target.chmod(original_mode)
    foreign = _entry_identity(target)
    saved_original = (
        retained / credentials.HOLDER / "original"
        if fault == "home"
        else (
            retained / "original"
            if fault == "holder"
            else retained if fault == "original" else original
        )
    )
    result = _fresh_cleanup(private)
    assert result.returncode == 1 and "HOLD" in result.stderr
    assert _original_snapshot(saved_original) == before
    assert _entry_identity(target) == foreign
    assert (private / credentials.SDK).exists()


@pytest.mark.parametrize(
    "boundary",
    [
        "marker_write",
        "config_unlink",
        "sdk_rmdir",
        "holder_rmdir",
        "journal_unlink",
        "private_cleanup",
    ],
)
@pytest.mark.parametrize("after", [False, True])
def test_cleanup_interruption_replays_only_after_original_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str, after: bool
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    credentials.install(private, login, default)
    holder = default.parent / credentials.HOLDER
    target = {
        "marker_write": private / credentials.SDK,
        "config_unlink": holder / "sdk" / "config.json",
        "sdk_rmdir": holder / "sdk",
        "holder_rmdir": holder,
        "journal_unlink": private / credentials.SDK,
        "private_cleanup": private,
    }[boundary]
    owner, method = (
        (credentials, "write")
        if boundary == "marker_write"
        else (
            (credentials.shutil, "rmtree")
            if boundary == "private_cleanup"
            else (Path, "unlink" if boundary.endswith("unlink") else "rmdir")
        )
    )
    operation = getattr(owner, method)

    def interrupt(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == target:
            assert _original_snapshot(default) == before
            if not after:
                raise OSError("selected cleanup boundary")
        result = operation(path, *args, **kwargs)
        if path == target and after:
            raise OSError("selected cleanup boundary")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(owner, method, interrupt)
        with pytest.raises(OSError, match="selected cleanup boundary"):
            credentials.cleanup(private)
    assert _original_snapshot(default) == before
    if private.exists():
        result = _fresh_cleanup(private)
        assert result.returncode == 0, result.stderr
    assert not private.exists() and not holder.exists()


@pytest.mark.parametrize("write_number", [1, 2, 3, 4])
@pytest.mark.parametrize("after", [False, True])
def test_preparation_journal_failure_preserves_unmoved_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, write_number: int, after: bool
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    native_write = credentials.write
    count = 0

    def interrupt(path: Path, value: dict) -> None:
        nonlocal count
        count += 1
        if count == write_number and not after:
            raise OSError("selected journal boundary")
        native_write(path, value)
        if count == write_number and after:
            raise OSError("selected journal boundary")

    with monkeypatch.context() as patch:
        patch.setattr(credentials, "write", interrupt)
        with pytest.raises(OSError, match="selected journal boundary"):
            credentials.install(private, login, default)
    assert _original_snapshot(default) == before
    result = _fresh_cleanup(private)
    # Allocation without a persisted identity is retained, never guessed from its name.
    expected_hold = not after and write_number in {2, 3, 4}
    assert result.returncode == int(expected_hold), result.stderr
    assert _original_snapshot(default) == before
    if expected_hold:
        assert (private / credentials.SDK).exists()
    else:
        assert not private.exists()


@pytest.mark.parametrize("kind", ["widened_mode", "broken_symlink"])
def test_journal_replacement_refuses_changed_existing_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    native_write = credentials.write
    count = 0
    changed_identity: tuple[int, ...] | None = None

    def changed_record(path: Path, value: dict) -> None:
        nonlocal count, changed_identity
        count += 1
        if count == 2:
            if kind == "widened_mode":
                path.chmod(0o640)
            else:
                path.rename(path.with_name("retained-record"))
                path.symlink_to(tmp_path / "missing")
            changed_identity = _entry_identity(path)
        native_write(path, value)

    with monkeypatch.context() as patch:
        patch.setattr(credentials, "write", changed_record)
        with pytest.raises(ValueError):
            credentials.install(private, login, default)
    assert _original_snapshot(default) == before
    assert _entry_identity(private / credentials.SDK) == changed_identity
    result = _fresh_cleanup(private)
    assert result.returncode == 1 and "HOLD" in result.stderr
    assert _original_snapshot(default) == before
    assert private.exists()


def test_cli_filesystem_error_does_not_emit_paths_or_exception_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    private, _, _ = _sdk_fixture(tmp_path)

    def fail_cleanup(directory: Path) -> None:
        raise OSError(13, "fixture-value-must-not-be-logged", str(directory / "secret-path"))

    monkeypatch.setattr(credentials, "cleanup", fail_cleanup)
    monkeypatch.setattr(sys, "argv", ["credentials", "cleanup", "--directory", str(private)])
    assert credentials.main() == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == (
        'Native GHCR credential placement/cleanup HOLD: filesystem operation failed; {"errno": 13}\n'
    )
    assert str(tmp_path) not in output.err and "fixture-value" not in output.err


@pytest.mark.parametrize("fsync_number", range(1, 25))
def test_file_and_directory_sync_failures_preserve_recoverable_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fsync_number: int
) -> None:
    private, login, default = _sdk_fixture(tmp_path)
    before = _original_snapshot(default)
    native_sync = os.fsync
    count = 0

    def interrupt(descriptor: int) -> None:
        nonlocal count
        count += 1
        if count == fsync_number:
            raise OSError("selected sync boundary")
        native_sync(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(credentials.os, "fsync", interrupt)
        with pytest.raises(OSError, match="selected sync boundary"):
            credentials.install(private, login, default)
            credentials.cleanup(private)
    result = _fresh_cleanup(private)
    # Journal file fsync can fail before a newly allocated object's identity is published.
    expected_hold = fsync_number in {3, 5, 7, 8, 9}
    assert result.returncode == int(expected_hold), result.stderr
    assert _original_snapshot(default) == before
    if expected_hold:
        assert (private / credentials.SDK).exists()
    else:
        assert not private.exists()


def test_sdk_bridge_and_owned_cleanup_are_shared_by_two_actual_writers() -> None:
    workflow = _load_cd_workflow()
    for job in ("postgres-synthetic-attestation-probe", "postgres-pgvector-publish"):
        steps = workflow["jobs"][job]["steps"]
        text = json.dumps(steps)
        assert "ghcr_attestation_credentials capture" in text
        assert "ghcr_attestation_credentials install" in text
        assert "ghcr_attestation_credentials cleanup" in text
        bridge = next(
            step
            for step in steps
            if step.get("name", "").startswith("Initialize the pinned native SDK")
        )
        assert 'docker --config "$ghcr_dir" login ghcr.io' in bridge["run"]
        assert "dhi.io" not in bridge["run"]
        assert "HOME=" not in text


@pytest.mark.parametrize(
    "primary,logout,cleanup,expected",
    [("success", 0, 0, 0), ("success", 1, 0, 1), ("success", 0, 1, 1), ("failure", 1, 1, 0)],
)
def test_native_cleanup_retains_primary_and_propagates_cleanup_only_failure(
    primary: str, logout: int, cleanup: int, expected: int, tmp_path: Path
) -> None:
    workflow = _load_cd_workflow()
    step = _step_by_name(
        workflow["jobs"]["postgres-synthetic-attestation-probe"]["steps"], "Logout probe registry"
    )
    shell = shutil.which("bash")
    assert shell is not None
    program = (
        'docker() { return "$LOGOUT"; }\npython3() { printf "attempted\\n" > "$MARKER"; return "$CLEANUP"; }\n'
        + step["run"]
    )
    marker = tmp_path / "attempted"
    process = subprocess.run(
        [shell, "-c", program],
        env={
            **os.environ,
            "DOCKER_CONFIG": "owned",
            "PRIMARY_JOB_STATUS": primary,
            "LOGOUT": str(logout),
            "CLEANUP": str(cleanup),
            "MARKER": str(marker),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == expected and marker.exists()


@pytest.mark.parametrize("version,success", [("2.35.0", True), ("2.34.9", False), ("bad", False)])
def test_native_job_declares_and_checks_compose_minimum_before_runtime(
    version: str, success: bool
) -> None:
    workflow = _load_cd_workflow()
    steps = workflow["jobs"]["staging-postgres-native-integration"]["steps"]
    step = _step_by_name(
        steps, "Execute real isolated PostgreSQL TLS crash restart and restore checks"
    )
    assert ">=2.35.0" in step["run"]
    code = (
        step["run"]
        .split("python3 - <<'PY_COMPOSE_VERSION'\n", 1)[1]
        .split("\nPY_COMPOSE_VERSION", 1)[0]
    )
    fake = (
        'import subprocess, shutil\nshutil.which=lambda name: "/native/docker"\nsubprocess.check_output=lambda *args, **kwargs: '
        + repr(version)
        + "\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", fake + code], capture_output=True, text=True, check=False
    )
    assert (result.returncode == 0) is success


@pytest.mark.parametrize(
    "event,ref,changed,native_result,publish,build",
    [
        ("push", "refs/heads/main", True, "success", True, True),
        ("push", "refs/heads/main", False, "success", False, True),
        ("push", "refs/heads/main", True, "failure", False, False),
        ("push", "refs/heads/main", False, "failure", False, False),
        ("push", "refs/heads/main", True, "cancelled", False, False),
        ("push", "refs/heads/main", True, "skipped", False, False),
        ("push", "refs/heads/main", True, "", False, False),
        ("pull_request", "refs/pull/2393/merge", True, "success", False, False),
        ("push", "refs/tags/v1.0.0", True, "success", False, False),
        ("workflow_dispatch", "refs/heads/main", True, "skipped", False, False),
        ("workflow_dispatch", "refs/heads/main", True, "success", False, False),
    ],
)
def test_native_integration_is_a_required_publication_and_deploy_dependency(
    event: str, ref: str, changed: bool, native_result: str, publish: bool, build: bool
) -> None:
    jobs = _load_cd_workflow()["jobs"]
    native_name = "staging-postgres-native-integration"
    publisher = jobs["postgres-pgvector-publish"]
    builder = jobs["build"]
    assert publisher["needs"] == [
        "main-push-admission",
        "postgres-pgvector-contract",
        "postgres-pgvector-material-change",
        "postgres-pgvector-ci-admission",
        native_name,
    ]
    assert builder["needs"] == ["prometheus-image-security", "main-push-admission", native_name]
    assert " ".join(publisher["if"].split()) == (
        "github.event_name == 'push' && github.ref == 'refs/heads/main' "
        "&& needs.postgres-pgvector-material-change.outputs.changed == 'true' "
        "&& needs.postgres-pgvector-ci-admission.result == 'success' "
        "&& needs.staging-postgres-native-integration.result == 'success'"
    )
    assert builder["if"] == (
        "github.ref == 'refs/heads/main' && "
        "needs.staging-postgres-native-integration.result == 'success'"
    )
    assert jobs["main-push-admission"]["if"] == (
        "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    )
    native_job = jobs[native_name]
    assert native_job["if"] == (
        "github.event_name == 'pull_request' || "
        "(github.event_name == 'push' && github.ref == 'refs/heads/main')"
    )
    runtime_step = _step_by_name(
        native_job["steps"],
        "Execute real isolated PostgreSQL TLS crash restart and restore checks",
    )
    assert runtime_step["if"] == "steps.native-material.outputs.changed == 'true'"
    assert not native_job.get("continue-on-error", False)
    assert not runtime_step.get("continue-on-error", False)
    # Closed projection of the exact expressions/needs above, not an Actions
    # expression interpreter. Other prerequisites are successful in this matrix.
    # Default success() also blocks jobs when main-push-admission is skipped.
    admitted_main = event == "push" and ref == "refs/heads/main"
    native_succeeded = native_result == "success"
    assert (admitted_main and native_succeeded and changed) is publish
    assert (admitted_main and native_succeeded) is build


def test_pgvector_native_and_distinct_materials_producers_are_conjunctive() -> None:
    workflow = _load_cd_workflow()
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    native = next(
        step
        for step in steps
        if step.get("name") == "Attest actual PostgreSQL pgvector build provenance"
    )
    materials = next(
        step for step in steps if step.get("name") == "Attest exact PostgreSQL pgvector materials"
    )
    spdx = next(
        step for step in steps if step.get("name") == "Attest PostgreSQL pgvector SPDX SBOM"
    )
    assert native["uses"].startswith("actions/attest-build-provenance@")
    assert "predicate-path" not in native["with"]
    assert (
        materials["with"]["predicate-type"]
        == "https://pulseplate.app/attestations/postgres-pgvector-materials/v1"
    )
    assert spdx["with"]["predicate-type"] == "https://spdx.dev/Document/v2.3"
    assert "outputs.provenance_mode == 'create'" in native["if"]
    assert "outputs.materials_mode == 'create'" in materials["if"]
    assert "outputs.sbom_mode == 'create'" in spdx["if"]
    for step in (native, materials, spdx):
        assert (
            step["with"]["subject-digest"]
            == "${{ needs.postgres-pgvector-contract.outputs.platform_manifest_digest }}"
        )
        assert step["with"]["push-to-registry"] is True


def test_pgvector_spdx_generated_once_digest_only_then_content_bound_and_never_regenerated_on_reuse() -> (
    None
):
    workflow = _load_cd_workflow()
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    names = [step["name"] for step in steps]
    spdx = names.index("Generate PostgreSQL pgvector SPDX SBOM with exact Trivy")
    generate = names.index("Generate exact PostgreSQL material predicate")
    inventory = names.index("Classify existing exact-digest PostgreSQL attestations")
    assert spdx < generate < inventory
    assert '"${REPOSITORY}@${PLATFORM_DIGEST}"' in steps[spdx]["run"]
    assert "$RUNTIME_REF" not in steps[spdx]["run"]
    assert "--sbom postgres-pgvector-image-sbom.spdx.json" in steps[generate]["run"]
    assert "--sbom postgres-pgvector-image-sbom.spdx.json" in steps[inventory]["run"]
    reuse = workflow["jobs"]["postgres-pgvector-reuse"]["steps"][1]["run"]
    assert "--format spdx-json" not in reuse and "--sbom" not in reuse
    assert "--scanners vuln,secret" in reuse and "--exit-code 1" in reuse
    probe = workflow["jobs"]["postgres-synthetic-attestation-probe"]["steps"]
    build = next(
        step["run"] for step in probe if step.get("name") == "Build and push tiny synthetic image"
    )
    assert build.index("> probe.spdx.json") < build.index(
        "scripts/ci/check_pgvector_attestations.py generate"
    )
    assert "--sbom probe.spdx.json" in build


def test_synthetic_probe_and_manual_reuse_have_closed_authority() -> None:
    workflow = _load_cd_workflow()
    probe = workflow["jobs"]["postgres-synthetic-attestation-probe"]
    assert probe["if"] == (
        "github.event_name == 'workflow_dispatch' && inputs.postgres_mode == 'synthetic-probe' "
        "&& startsWith(github.ref, 'refs/heads/')"
    )
    triggers = workflow[True]
    assert triggers["push"]["branches"] == ["main"]
    assert triggers["workflow_dispatch"]["inputs"]["postgres_mode"]["options"] == [
        "disabled",
        "synthetic-probe",
        "reuse",
    ]
    assert "environment" not in probe and "needs" not in probe
    text = str(probe)
    for prohibited in ("DHI_", "SSH_", "canonical_tag", "deploy.sh", "pgvector-publish"):
        assert prohibited not in text
    steps = probe["steps"]
    auth = steps[0]["run"]
    assert 'test "$SOURCE_SHA" = "$GITHUB_SHA"' in auth
    assert "commits/$SOURCE_SHA" in auth
    assert steps[1]["with"]["ref"] == "${{ inputs.source_sha }}"
    for step in steps:
        if "SOURCE_SHA" in step.get("env", {}):
            assert step["env"]["SOURCE_SHA"] == "${{ inputs.source_sha }}"
    assert "FROM scratch" in steps[2]["run"] and "docker build --file" in steps[2]["run"]
    roundtrip = next(
        step["run"]
        for step in steps
        if step.get("name") == "Fresh-process external pullback repeat and source-rejection probe"
    )
    assert "docker pull" in roundtrip and "for attempt in 1 2" in roundtrip
    assert "0000000000000000000000000000000000000000" in roundtrip
    reuse = workflow["jobs"]["postgres-pgvector-reuse"]
    assert "github.ref == 'refs/heads/main' && inputs.postgres_mode == 'reuse'" in reuse["if"]
    assert reuse["permissions"]["packages"] == "read"
    assert reuse["permissions"]["attestations"] == "read"
    assert "id-token" not in reuse["permissions"]


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "push",
        "pull_request",
        "tag_ref",
        "pull_ref",
        "detached_ref",
        "empty_ref",
        "empty_branch",
        "mismatched_sha",
        "empty_sha",
        "malformed_sha",
        "uppercase_sha",
        "other_repository",
        "non_repository_commit",
        "commit_api_failure",
    ],
)
def test_manual_probe_requires_selected_branch_and_exact_repository_commit(
    fault: str | None,
) -> None:
    workflow = _load_cd_workflow()
    probe = workflow["jobs"]["postgres-synthetic-attestation-probe"]
    auth = probe["steps"][0]["run"]
    shell = shutil.which("bash")
    assert shell is not None
    env = {
        **os.environ,
        "SOURCE_SHA": "a" * 40,
        "GITHUB_SHA": "a" * 40,
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/codex/selected-probe-source",
        "RESOLVED_SHA": "a" * 40,
    }
    mutations = {
        "push": ("GITHUB_EVENT_NAME", "push"),
        "pull_request": ("GITHUB_EVENT_NAME", "pull_request"),
        "tag_ref": ("GITHUB_REF", "refs/tags/v1.0.0"),
        "pull_ref": ("GITHUB_REF", "refs/pull/2393/merge"),
        "detached_ref": ("GITHUB_REF", "a" * 40),
        "empty_ref": ("GITHUB_REF", ""),
        "empty_branch": ("GITHUB_REF", "refs/heads/"),
        "mismatched_sha": ("SOURCE_SHA", "b" * 40),
        "empty_sha": ("SOURCE_SHA", ""),
        "malformed_sha": ("SOURCE_SHA", "not-a-full-sha"),
        "uppercase_sha": ("SOURCE_SHA", "A" * 40),
        "other_repository": ("GITHUB_REPOSITORY", "other/PulsePlate"),
        "non_repository_commit": ("RESOLVED_SHA", "b" * 40),
    }
    if fault is not None and fault in mutations:
        key, value = mutations[fault]
        env[key] = value
    gh_stub = 'gh() { printf "%s\\n" "$RESOLVED_SHA"; }\n'
    if fault == "commit_api_failure":
        gh_stub = "gh() { return 1; }\n"
    completed = subprocess.run(
        [shell, "-c", gh_stub + auth],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (completed.returncode == 0) is (fault is None)
    assert "if" not in workflow["jobs"]["postgres-pgvector-contract"]
    for name in (
        "main-push-admission",
        "postgres-pgvector-material-change",
        "build-production",
        "production-deploy-config",
    ):
        condition = workflow["jobs"][name]["if"]
        assert "github.event_name == 'push'" in condition
        assert "refs/heads/main" in condition or "refs/tags/v" in condition


def _job_steps(workflow: dict[str, object], job_name: str) -> list[dict[str, object]]:
    """Return the steps list for a given job."""
    return workflow["jobs"][job_name]["steps"]  # type: ignore[index]


def _step_by_name(steps: list[dict[str, object]], step_name: str) -> dict[str, object]:
    """Find a step by display name."""
    for step in steps:
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"Step {step_name!r} not found in job steps")


def _step_ids(steps: list[dict[str, object]]) -> set[str]:
    """Return the set of step IDs defined in a job."""
    return {step["id"] for step in steps if "id" in step}


def test_cd_staging_attestation_verify_depends_on_all_attestation_steps() -> None:
    """Staging verify must not run unless build + all attestation steps succeeded."""
    workflow = _load_cd_workflow()
    steps = _job_steps(workflow, "build")

    # All required attestation step IDs must exist
    existing_ids = _step_ids(steps)
    for required_id in STAGING_ATTESTATION_STEP_IDS:
        assert required_id in existing_ids, f"Missing step id {required_id!r} in build job"

    # Verify step condition must reference all attestation outcomes
    verify_step = _step_by_name(steps, "Verify staged backend image attestations")
    verify_if = verify_step["if"]
    assert "always()" in verify_if, "Verify step must use always() to ensure condition evaluation"
    assert "steps.build.outcome == 'success'" in verify_if
    assert "steps.attest-staged-provenance.outcome == 'success'" in verify_if
    assert "steps.generate-staged-sbom.outcome == 'success'" in verify_if
    assert "steps.attest-staged-sbom.outcome == 'success'" in verify_if

    caddy_verify_step = _step_by_name(steps, "Verify staged Caddy image attestations")
    caddy_verify_if = caddy_verify_step["if"]
    assert "always()" in caddy_verify_if
    assert "steps.build-caddy.outcome == 'success'" in caddy_verify_if
    assert "steps.attest-staged-caddy-provenance.outcome == 'success'" in caddy_verify_if
    assert "steps.generate-staged-caddy-sbom.outcome == 'success'" in caddy_verify_if
    assert "steps.attest-staged-caddy-sbom.outcome == 'success'" in caddy_verify_if

    for step in (verify_step, caddy_verify_step):
        env = step.get("env")
        assert isinstance(env, dict)
        assert env["REPO_SLUG"] == "${{ github.repository }}"
        assert env["SOURCE_REF"] == "${{ github.ref }}"
        run = step.get("run")
        assert isinstance(run, str)
        assert '--repo "$REPO_SLUG"' in run
        assert '--signer-workflow "$REPO_SLUG/.github/workflows/cd.yml"' in run
        assert '--source-ref "$SOURCE_REF"' in run
        assert "${{ github.repository }}" not in run
        assert "${{ github.ref }}" not in run


def test_cd_production_attestation_verify_depends_on_all_attestation_steps() -> None:
    """Production verify must not run unless build + all attestation steps succeeded."""
    workflow = _load_cd_workflow()
    steps = _job_steps(workflow, "build-production")

    # All required attestation step IDs must exist
    existing_ids = _step_ids(steps)
    for required_id in PRODUCTION_ATTESTATION_STEP_IDS:
        assert (
            required_id in existing_ids
        ), f"Missing step id {required_id!r} in build-production job"

    # Verify step condition must reference all attestation outcomes
    verify_step = _step_by_name(steps, "Verify production image attestations")
    verify_if = verify_step["if"]
    assert "always()" in verify_if, "Verify step must use always() to ensure condition evaluation"
    assert "steps.build.outcome == 'success'" in verify_if
    assert "steps.attest-production-provenance.outcome == 'success'" in verify_if
    assert "steps.generate-production-sbom.outcome == 'success'" in verify_if
    assert "steps.attest-production-sbom.outcome == 'success'" in verify_if


def test_cd_attestation_steps_remain_fail_closed() -> None:
    """Attestation and verification steps must not use continue-on-error."""
    workflow = _load_cd_workflow()

    attestation_step_names = {
        "Attest staged backend image provenance",
        "Generate staged backend image SBOM",
        "Attest staged backend image SBOM",
        "Verify staged backend image attestations",
        "Attest staged Caddy image provenance",
        "Generate staged Caddy image SBOM",
        "Attest staged Caddy image SBOM",
        "Verify staged Caddy image attestations",
        "Attest production image provenance",
        "Generate production image SBOM",
        "Attest production image SBOM",
        "Verify production image attestations",
    }

    for job_name in ("build", "build-production"):
        for step in _job_steps(workflow, job_name):
            name = step.get("name", "")
            if name in attestation_step_names:
                assert (
                    step.get("continue-on-error") is not True
                ), f"Step {name!r} in job {job_name!r} must not use continue-on-error"
                # Also check for || true in run scripts
                run_script = step.get("run", "")
                if run_script:
                    assert (
                        "|| true" not in run_script
                    ), f"Step {name!r} in job {job_name!r} must not use || true"


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "auth_failure",
        "missing_native",
        "missing_materials",
        "wrong_sha",
        "wrong_attempt",
        "wrong_materials",
        "unexpected_validator_failure",
        "validator_accepts_incomplete",
    ],
)
def test_pre_spdx_control_requires_official_current_two_record_positive_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    steps = _load_cd_workflow()["jobs"]["postgres-synthetic-attestation-probe"]["steps"]
    control = _step_by_name(
        steps, "Reject the exact current incomplete native and materials tuple before SPDX"
    )["run"]
    code = control.split("<<'PY_INCOMPLETE_CONTROL'\n", 1)[1].split("\nPY_INCOMPLETE_CONTROL", 1)[0]
    assert control.index("PY_INCOMPLETE_CONTROL") < control.index("if python3")
    assert "--run-invocation-uri" in control
    assert (
        steps.index(_step_by_name(steps, "Attest synthetic exact materials"))
        < steps.index(
            _step_by_name(
                steps, "Reject the exact current incomplete native and materials tuple before SPDX"
            )
        )
        < steps.index(_step_by_name(steps, "Attest synthetic SPDX"))
    )
    repo = "Katsiarynakavaleuskaya/PulsePlate"
    ref = "refs/heads/codex/selected-probe-source"
    identity = {
        "repository": repo,
        "source_sha": "a" * 40,
        "source_ref": ref,
        "signer_workflow": repo + "/.github/workflows/cd.yml",
        "run_invocation_uri": "https://github.com/" + repo + "/actions/runs/123/attempts/2",
    }
    manifest = {
        "schema": "pulseplate.synthetic_attestation_probe.v1",
        "repository": "ghcr.io/owner/probe",
        "platform_manifest_digest": "sha256:" + "b" * 64,
        "recipe": {"base": "scratch", "payload": "synthetic-attestation-probe-v1"},
    }
    materials = pgvector.materials_predicate(manifest, identity, "sha256:" + "c" * 64)
    certificate = {
        "sourceRepositoryDigest": identity["source_sha"],
        "sourceRepositoryRef": ref,
        "sourceRepositoryURI": "https://github.com/" + repo,
        "buildSignerURI": "https://github.com/" + identity["signer_workflow"] + "@" + ref,
        "runInvocationURI": identity["run_invocation_uri"],
        "runnerEnvironment": "github-hosted",
    }
    payloads = {kind: [] for kind in pgvector.TYPES}
    for kind, predicate in zip(
        pgvector.TYPES[:2],
        (
            {"buildDefinition": {"buildType": "https://actions.github.io/buildtypes/workflow/v1"}},
            materials,
        ),
    ):
        payloads[kind] = [
            {
                "verificationResult": {
                    "signature": {"certificate": copy.deepcopy(certificate)},
                    "statement": {
                        "_type": "https://in-toto.io/Statement/v1",
                        "predicateType": kind,
                        "subject": [
                            {"name": manifest["repository"], "digest": {"sha256": "b" * 64}}
                        ],
                        "predicate": copy.deepcopy(predicate),
                    },
                }
            }
        ]
    if fault == "missing_native":
        payloads[pgvector.TYPES[0]] = []
    if fault == "missing_materials":
        payloads[pgvector.TYPES[1]] = []
    if fault in ("wrong_sha", "wrong_attempt"):
        for kind in pgvector.TYPES[:2]:
            cert = payloads[kind][0]["verificationResult"]["signature"]["certificate"]
            cert["sourceRepositoryDigest" if fault == "wrong_sha" else "runInvocationURI"] = (
                "d" * 40
                if fault == "wrong_sha"
                else identity["run_invocation_uri"].replace("/attempts/2", "/attempts/1")
            )
    if fault == "wrong_materials":
        payloads[pgvector.TYPES[1]][0]["verificationResult"]["statement"]["predicate"][
            "spdx_sha256"
        ] = ("sha256:" + "d" * 64)

    def verified(
        manifest_arg: dict, repo_arg: str, workflow: str, ref_arg: str, present: tuple
    ) -> dict:
        assert (manifest_arg, repo_arg, workflow, ref_arg, present) == (
            manifest,
            repo,
            identity["signer_workflow"],
            ref,
            pgvector.TYPES[:2],
        )
        if fault == "auth_failure":
            raise RuntimeError("official gh authentication rejected")
        return payloads

    monkeypatch.setattr(pgvector, "verified_payloads", verified)
    if fault == "unexpected_validator_failure":

        def rejected(*args: object, **kwargs: object) -> dict:
            raise ValueError("unrelated validator failure")

        monkeypatch.setattr(pgvector, "validate_triple", rejected)
    if fault == "validator_accepts_incomplete":
        monkeypatch.setattr(pgvector, "validate_triple", lambda *args, **kwargs: {})
    monkeypatch.chdir(tmp_path)
    for name, value in {
        "GITHUB_REPOSITORY": repo,
        "GITHUB_REF": ref,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "2",
        "SOURCE_SHA": identity["source_sha"],
    }.items():
        monkeypatch.setenv(name, value)
    Path("probe-manifest.json").write_text(json.dumps(manifest))
    Path("probe-materials.json").write_text(json.dumps(materials))
    if fault:
        with pytest.raises((SystemExit, RuntimeError, ValueError)):
            exec(compile(code, "native-incomplete-control", "exec"), {})
        assert not Path("probe-incomplete-control.json").exists()
    else:
        exec(compile(code, "native-incomplete-control", "exec"), {})
        evidence = json.loads(Path("probe-incomplete-control.json").read_text())
        import hashlib

        fingerprint = evidence.pop("fingerprint")
        assert (
            fingerprint == hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
        )
        assert evidence == {
            "original_build": identity,
            "native_and_materials_verified": True,
            "exact_generated_materials_verified": True,
            "incomplete_membership_rejected": True,
            "asset_type": "native_verified_incomplete_tuple_control",
            "upstream_assets": [
                {"path": name, "sha256": hashlib.sha256(Path(name).read_bytes()).hexdigest()}
                for name in ("probe-manifest.json", "probe-materials.json")
            ],
            "policy_version": "original-build-three-records-v1",
            "idempotency_key": identity["run_invocation_uri"],
            "replay_admission": "Fresh current-execution negative control only; no publication or deployment authority",
        }


@pytest.mark.parametrize("fault", [None, "empty_signature", "bad_base64", "multiple_signatures"])
def test_synthetic_probe_signature_corruption_mutates_one_decoded_byte_only(
    tmp_path: Path, fault: str | None
) -> None:
    workflow = _load_cd_workflow()
    steps = workflow["jobs"]["postgres-synthetic-attestation-probe"]["steps"]
    material = _step_by_name(steps, "Attest synthetic exact materials")
    assert material["id"] == "attest-probe-materials"
    control = _step_by_name(
        steps,
        "Verify original reject damaged signature and reverify original native materials bundle",
    )
    assert (
        control["env"]["MATERIALS_BUNDLE_PATH"]
        == "${{ steps.attest-probe-materials.outputs.bundle-path }}"
    )
    run = control["run"]
    for flag in (
        "--bundle",
        "--repo",
        "--signer-workflow",
        "--source-ref",
        "--source-digest",
        "--predicate-type",
        "--deny-self-hosted-runners",
    ):
        assert flag in run
    assert run.index('verify_bundle "$MATERIALS_BUNDLE_PATH"') < run.index("PY_CORRUPT_SIGNATURE")
    assert run.count('verify_bundle "$MATERIALS_BUNDLE_PATH"') == 2
    assert "if verify_bundle probe-materials-corrupted-bundle.json" in run
    assert "exit 1" in run and "continue-on-error" not in control
    assert (
        steps.index(material)
        < steps.index(control)
        < steps.index(_step_by_name(steps, "Retain native external probe evidence"))
    )
    marker = "python3 - <<'PY_CORRUPT_SIGNATURE'\n"
    code = run.split(marker, 1)[1].split("\nPY_CORRUPT_SIGNATURE", 1)[0]
    original_signature = bytes(range(1, 73))
    bundle = {
        "mediaType": "application/vnd.dev.sigstore.bundle.v0.3+json",
        "verificationMaterial": {"certificate": {"rawBytes": "public-certificate"}},
        "dsseEnvelope": {
            "payload": base64.b64encode(b"bound-public-payload").decode(),
            "payloadType": "application/vnd.in-toto+json",
            "signatures": [
                {"sig": base64.b64encode(original_signature).decode(), "keyid": "preserved"}
            ],
        },
    }
    if fault == "empty_signature":
        bundle["dsseEnvelope"]["signatures"][0]["sig"] = ""
    elif fault == "bad_base64":
        bundle["dsseEnvelope"]["signatures"][0]["sig"] = "not base64!"
    elif fault == "multiple_signatures":
        bundle["dsseEnvelope"]["signatures"].append(
            copy.deepcopy(bundle["dsseEnvelope"]["signatures"][0])
        )
    original_file = tmp_path / "original-bundle.json"
    original_file.write_text(json.dumps(bundle))
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env={
            **os.environ,
            "MATERIALS_BUNDLE_PATH": str(original_file),
            "PYTHONPATH": str(REPO_ROOT),
            "GITHUB_RUN_ID": "101",
            "GITHUB_RUN_ATTEMPT": "1",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    output = tmp_path / "probe-materials-corrupted-bundle.json"
    if fault is not None:
        assert result.returncode != 0 and not output.exists()
        return
    assert result.returncode == 0, result.stderr
    damaged = json.loads(output.read_text())
    decoded = base64.b64decode(damaged["dsseEnvelope"]["signatures"][0]["sig"], validate=True)
    assert len(decoded) == len(original_signature)
    assert [
        index
        for index, (before, after) in enumerate(zip(original_signature, decoded))
        if before != after
    ] == [0]
    assert decoded[0] == original_signature[0] ^ 1
    damaged["dsseEnvelope"]["signatures"][0]["sig"] = bundle["dsseEnvelope"]["signatures"][0]["sig"]
    assert damaged == bundle
    assert json.loads(original_file.read_text()) == bundle
