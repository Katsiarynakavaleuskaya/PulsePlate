"""Git evidence shared by the CI and CD Prometheus workflow tests."""

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path


def pinned_prometheus_control_bytes(repo_root: Path, revision: str) -> bytes:
    """Read the actual fixed controller independently of current material P."""
    assert re.fullmatch(r"[0-9a-f]{40}", revision)
    binary = shutil.which("git", path=os.defpath)
    assert binary is not None and Path(binary).is_absolute()
    environment = {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_COUNT": "0",
    }

    def query(*arguments: str) -> bytes:
        result = subprocess.run(
            [
                binary,
                "--no-replace-objects",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=" + os.devnull,
                *arguments,
            ],
            cwd=repo_root,
            env=environment,
            capture_output=True,
            timeout=15,
            check=False,
        )
        assert (
            result.returncode == 0 and not result.stderr
        ), "Pinned controller Git evidence unavailable or ambiguous"
        return result.stdout

    expected = revision.encode("ascii") + b"\n"
    assert (
        query("rev-parse", "--disambiguate=" + revision) == expected
    ), "Pinned controller commit identity is ambiguous"
    assert (
        query("rev-parse", "--verify", "--end-of-options", revision + "^{commit}") == expected
    ), "Pinned controller commit does not match requested identity"
    assert query("cat-file", "-t", revision) == b"commit\n"
    row = query("ls-tree", "-z", revision, "--", "scripts/ci/prometheus_source_image.py")
    match = re.fullmatch(
        rb"100644 blob ([0-9a-f]{40})\tscripts/ci/prometheus_source_image\.py\x00", row
    )
    assert match is not None, "Pinned controller must be one regular Git blob"
    raw = query("cat-file", "blob", match[1].decode("ascii"))
    assert 0 < len(raw) <= 1024**2
    assert (
        hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw, usedforsecurity=False)
        .hexdigest()
        .encode("ascii")
        == match[1]
    )
    return raw
