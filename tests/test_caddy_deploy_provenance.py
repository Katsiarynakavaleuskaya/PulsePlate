"""Fail-closed contracts for the hardened Caddy and staging digest lane."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "frontend" / "Dockerfile.caddy-spa"
BACKLOG_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
CVE_SECURITY_OWNER = (
    REPO_ROOT / "docs" / "security" / "PR_2356_CVE_2026_56854_CONTAINER_RUNTIME_REMEDIATION.md"
)
STAGING_COMPOSE = REPO_ROOT / "deploy" / "docker-compose.staging.yaml"
PROMETHEUS_CONFIG = REPO_ROOT / "deploy" / "prometheus" / "prometheus.yml"
PROMETHEUS_IMAGE_MANIFEST = REPO_ROOT / "deploy" / "prometheus" / "image-manifest.json"
CD_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "cd.yml"
FRONTEND_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "frontend-ci.yml"
TRIVY_ACTION = "aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25"
TRIVY_VERSION = "v0.74.0"
ALERTMANAGER_CONFIG = REPO_ROOT / "deploy" / "alertmanager" / "alertmanager.yml"
ALERTMANAGER_IGNORE = REPO_ROOT / "deploy" / "alertmanager" / "trivy-ignore.yaml"


def test_alertmanager_cd_contract_carries_exact_files_and_keeps_scans_separate() -> None:
    workflow = CD_WORKFLOW.read_text(encoding="utf-8")
    for name, output in (
        ("alertmanager.yml", "ALERTMANAGER_CONFIG_SHA256"),
        ("trivy-ignore.yaml", "ALERTMANAGER_TRIVY_IGNORE_SHA256"),
    ):
        path = f"alertmanager/{name}"
        assert f"sha256sum deploy/{path}" in workflow
        assert workflow.count(f"[ ! -L ./{path} ]") == 2
        assert workflow.count(f'"${output}" ]') == 2
        assert f"deploy/{path}" in workflow
    assert "Admit exact Alertmanager image, config, and narrow CVE exception" in workflow
    assert '--ignorefile "$TRIVY_IGNORE_FILE"' in workflow  # Prometheus stays separate.
    assert '--ignorefile "$ignore"' in workflow  # Alertmanager only.
    assert "-e PULSEPLATE_ENVIRONMENT=staging" in workflow
    assert "CVE-2026-84445" in ALERTMANAGER_IGNORE.read_text(encoding="utf-8")
    assert "group_interval: 5m" in ALERTMANAGER_CONFIG.read_text(encoding="utf-8")
    for required in (
        "Prove staging environment label reaches Alertmanager despite forged metric label",
        'environment="production"',
        "PULSEPLATE_ENVIRONMENT=staging",
        "http://127.0.0.1:9093/api/v2/alerts",
        'labels.get("environment") != "staging"',
        '"environment" not in item["metric"]',
        '"network", "create", "--internal"',
    ):
        assert required in workflow


def _run_alertmanager_scan_fixture(
    tmp_path: Path, scenario: str
) -> subprocess.CompletedProcess[str]:
    """Execute the actual admission step with controlled native-command outcomes."""
    step = _named_step(
        _steps(_job(_workflow(CD_WORKFLOW), "prometheus-image-security")),
        "Admit exact Alertmanager image, config, and narrow CVE exception",
    )
    script = step["run"]
    assert isinstance(script, str)
    workspace = tmp_path / "workspace"
    config = workspace / "deploy" / "alertmanager"
    config.mkdir(parents=True)
    shutil.copyfile(ALERTMANAGER_CONFIG, config / "alertmanager.yml")
    shutil.copyfile(ALERTMANAGER_IGNORE, config / "trivy-ignore.yaml")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    digest = "sha256:84967b9b7ba45e38a9278d3e594305f43d4993c310df3905b51138b816c365f3"
    docker = binaries / "docker"
    docker.write_text(
        f"#!{sys.executable}\n"
        "import json,sys\n"
        f"digest={digest!r}\n"
        "args=sys.argv[1:]\n"
        "if args[:2]==['buildx','imagetools']:\n"
        " print(json.dumps({'manifests':[{'digest':digest,'platform':{'os':'linux','architecture':'amd64'}}]}))\n"
        "elif args[:2]==['image','inspect']:\n"
        " print(json.dumps([{'Os':'linux','Architecture':'amd64','RepoDigests':['prom/alertmanager@'+digest]}]))\n"
        "elif '--version' in args: print('alertmanager, version 0.34.1')\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    report = {
        "SchemaVersion": 2,
        "ArtifactName": "prom/alertmanager@" + digest,
        "Results": [
            {
                "Target": target,
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2026-84445",
                        "PkgIdentifier": {"PURL": "pkg:golang/google.golang.org/grpc@v1.83.1"},
                    }
                ],
            }
            for target in ("bin/alertmanager", "bin/amtool")
        ],
    }
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="utf-8")
    trivy = binaries / "trivy"
    trivy.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\nfrom pathlib import Path\n"
        "args=sys.argv[1:]\n"
        "ignore=Path(args[args.index('--ignorefile')+1]).name if '--ignorefile' in args else ''\n"
        "negative=bool(ignore) and ignore!='trivy-ignore.yaml'\n"
        "late='expired' in ignore\n"
        "scenario=os.environ['SCAN_SCENARIO']\n"
        "report=json.loads(Path(os.environ['SCAN_REPORT']).read_text())\n"
        "if negative:\n"
        " with Path(os.environ['SCAN_CALLS']).open('a') as stream: stream.write(ignore+'\\n')\n"
        " if scenario in ('exit1','exit2'):\n"
        "  print('scanner prerequisite failed; no report',file=sys.stderr); sys.exit(int(scenario[-1]))\n"
        " if scenario=='stale' and late: sys.exit(0)\n"
        " if scenario=='empty': report['Results']=[]\n"
        " if scenario=='wrong': report['Results'][0]['Vulnerabilities'][0]['PkgIdentifier']['PURL']='pkg:golang/google.golang.org/grpc@v1.83.0'\n"
        " if scenario=='extra': report['Results'][0]['Vulnerabilities'].append({'VulnerabilityID':'CVE-0000-0000','PkgIdentifier':{'PURL':'pkg:generic/other@1'}})\n"
        " if scenario=='secret': report['Results'][0]['Secrets']=[{'RuleID':'synthetic','Severity':'HIGH'}]\n"
        "if '--output' in args:\n"
        " output=Path(args[args.index('--output')+1])\n"
        " output.write_text('{' if negative and scenario=='malformed' else json.dumps(report))\n",
        encoding="utf-8",
    )
    trivy.chmod(0o755)
    runner = tmp_path / "runner"
    runner.mkdir()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "GITHUB_", "GH_"))
    }
    env.update(
        {
            "PATH": str(binaries) + os.pathsep + env["PATH"],
            "GITHUB_WORKSPACE": str(workspace),
            "RUNNER_TEMP": str(runner),
            "TRIVY_BIN": str(trivy),
            "SCAN_SCENARIO": scenario,
            "SCAN_REPORT": str(tmp_path / "report.json"),
            "SCAN_CALLS": str(tmp_path / "calls.log"),
        }
    )
    bash = shutil.which("bash")
    assert bash is not None
    return subprocess.run(
        [bash, "-c", script], cwd=workspace, env=env, capture_output=True, text=True, timeout=20
    )


@pytest.mark.parametrize(
    "scenario", ("exit1", "exit2", "malformed", "empty", "wrong", "extra", "secret", "stale")
)
def test_alertmanager_negative_controls_reject_unproven_scans(
    tmp_path: Path, scenario: str
) -> None:
    """An error or absent/different report cannot masquerade as policy rejection."""
    result = _run_alertmanager_scan_fixture(tmp_path, scenario)
    assert result.returncode != 0, result.stdout + result.stderr
    assert (tmp_path / "calls.log").read_text(encoding="utf-8").strip()


def test_alertmanager_negative_controls_require_both_retained_inventories(tmp_path: Path) -> None:
    """Both real scan-success branches must retain the complete frozen inventory."""
    result = _run_alertmanager_scan_fixture(tmp_path, "valid")
    assert result.returncode == 0, result.stdout + result.stderr
    calls = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    assert len(calls) == 2
    assert "wrong" in calls[0] and "expired" in calls[1]


PROMETHEUS_RULES_HASH_CHECK = (
    """[ "$(sha256sum ./prometheus/alias-alerts.yml | cut -d' ' -f1)" """
    '= "$PROMETHEUS_RULES_SHA256" ]'
)

GO_BUILDER = (
    "golang:1.26.6-alpine3.23@"
    "sha256:5978cc992ad5ef96a7469713c8af849c1433824761ce3be2c56381403cd8d9a3"
)
NODE_BUILDER = (
    "node:24.18.1-bookworm-slim@"
    "sha256:235600a8101ab264e117b1768e925532262668dc9b581ef1dd7d96ced463b8e7"
)
CADDY_BASE = (
    "caddy:2.11.4-alpine@" "sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648"
)
EXPECTED_CADDY_BUILDER_STAGE = (
    "\n".join(
        (
            f"FROM {GO_BUILDER} AS caddy-build",
            "",
            "ENV CGO_ENABLED=0 \\",
            "    GOTOOLCHAIN=local \\",
            "    GOPROXY=https://proxy.golang.org,direct \\",
            "    GOSUMDB=sum.golang.org",
            "",
            "RUN set -eux; \\",
            "    set -o pipefail; \\",
            '    build_dir="$(mktemp -d)"; \\',
            '    cd "$build_dir"; \\',
            "    go mod init pulseplate.local/caddy-build; \\",
            "    go get github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.4; \\",
            "    go get google.golang.org/grpc@v1.83.2; \\",
            "    go get golang.org/x/crypto@v0.55.0; \\",
            "    go mod download all; \\",
            "    go mod verify; \\",
            (
                "    test -z \"$(go list -m -f '{{if .Replace}}{{.Path}} => "
                "{{.Replace.Path}}{{end}}' all)\"; \\"
            ),
            (
                "    go list -m -f '{{if or "
                '(eq .Path "github.com/caddyserver/caddy/v2") '
                '(eq .Path "google.golang.org/grpc") '
                '(eq .Path "golang.org/x/crypto") '
                '(eq .Path "golang.org/x/mod") '
                '(eq .Path "golang.org/x/net") '
                '(eq .Path "golang.org/x/sync") '
                '(eq .Path "golang.org/x/sys") '
                '(eq .Path "golang.org/x/telemetry") '
                '(eq .Path "golang.org/x/term") '
                '(eq .Path "golang.org/x/text") '
                '(eq .Path "golang.org/x/tools")'
                "}}{{.Path}} {{.Version}}{{end}}' all \\"
            ),
            "      | awk 'NF' \\",
            "      | LC_ALL=C sort > /tmp/caddy-governed-graph; \\",
            "    printf '%s\\n' \\",
            "      'github.com/caddyserver/caddy/v2 v2.11.4' \\",
            "      'golang.org/x/crypto v0.55.0' \\",
            "      'golang.org/x/mod v0.38.0' \\",
            "      'golang.org/x/net v0.58.0' \\",
            "      'golang.org/x/sync v0.22.0' \\",
            "      'golang.org/x/sys v0.47.0' \\",
            "      'golang.org/x/telemetry v0.0.0-20260708182218-49f421fb7959' \\",
            "      'golang.org/x/term v0.45.0' \\",
            "      'golang.org/x/text v0.41.0' \\",
            "      'golang.org/x/tools v0.48.0' \\",
            "      'google.golang.org/grpc v1.83.2' \\",
            "      | LC_ALL=C sort > /tmp/caddy-expected-graph; \\",
            ('    test "$(wc -l < /tmp/caddy-governed-graph | ' "tr -d '[:space:]')\" = '11'; \\"),
            "    cmp /tmp/caddy-expected-graph /tmp/caddy-governed-graph; \\",
            "    go build -mod=readonly -trimpath \\",
            ("      -ldflags '-X github.com/caddyserver/caddy/v2.CustomVersion=v2.11.4' " "\\"),
            "      -o /go/bin/caddy \\",
            "      github.com/caddyserver/caddy/v2/cmd/caddy; \\",
            "    /go/bin/caddy version; \\",
            "    go version -m /go/bin/caddy > /tmp/caddy-binary-metadata; \\",
            "    cat /tmp/caddy-binary-metadata; \\",
            (
                '    test "$(awk \'$1 == "=>" { count++ } END { print count + 0 }\' '
                "/tmp/caddy-binary-metadata)\" = '0'; \\"
            ),
            (
                '    awk \'$1 == "mod" && $2 == "github.com/caddyserver/caddy/v2" '
                '{ print $1, $2, $3 } $1 == "dep" && '
                '($2 == "google.golang.org/grpc" || $2 == "golang.org/x/crypto" || '
                '$2 == "golang.org/x/net" || $2 == "golang.org/x/sync" || '
                '$2 == "golang.org/x/sys" || $2 == "golang.org/x/term" || '
                '$2 == "golang.org/x/text") { print $1, $2, $3 }\' '
                "/tmp/caddy-binary-metadata \\"
            ),
            "      | LC_ALL=C sort > /tmp/caddy-governed-binary; \\",
            "    printf '%s\\n' \\",
            "      'mod github.com/caddyserver/caddy/v2 v2.11.4' \\",
            "      'dep golang.org/x/crypto v0.55.0' \\",
            "      'dep golang.org/x/net v0.58.0' \\",
            "      'dep golang.org/x/sync v0.22.0' \\",
            "      'dep golang.org/x/sys v0.47.0' \\",
            "      'dep golang.org/x/term v0.45.0' \\",
            "      'dep golang.org/x/text v0.41.0' \\",
            "      'dep google.golang.org/grpc v1.83.2' \\",
            "      | LC_ALL=C sort > /tmp/caddy-expected-binary; \\",
            ('    test "$(wc -l < /tmp/caddy-governed-binary | ' "tr -d '[:space:]')\" = '8'; \\"),
            "    cmp /tmp/caddy-expected-binary /tmp/caddy-governed-binary; \\",
            "    rm -f \\",
            "      /tmp/caddy-binary-metadata \\",
            "      /tmp/caddy-expected-binary \\",
            "      /tmp/caddy-expected-graph \\",
            "      /tmp/caddy-governed-binary \\",
            "      /tmp/caddy-governed-graph; \\",
            '    rm -rf "$build_dir"',
            "",
        )
    )
    + "\n"
)
EXPECTED_CADDY_FINAL_STAGE = (
    "\n".join(
        (
            f"FROM {CADDY_BASE}",
            "",
            'LABEL org.opencontainers.image.title="PulsePlate Caddy SPA shell" \\',
            (
                '      org.opencontainers.image.description="Caddy 2.11.4 rebuilt with '
                'Go 1.26.6 and PulsePlate frontend assets"'
            ),
            "",
            "# Compare the standard module surface before replacing the upstream binary.",
            "# Package versions and build metadata are intentionally excluded from parity.",
            "COPY --from=caddy-build --chmod=0755 /go/bin/caddy /usr/bin/caddy.pulseplate",
            "RUN set -eux; \\",
            "    set -o pipefail; \\",
            (
                '    caddy list-modules --packages | awk \'NF && $1 != "Standard" '
                "{ print $1 }' | LC_ALL=C sort > /tmp/caddy-official-modules; \\"
            ),
            (
                "    /usr/bin/caddy.pulseplate list-modules --packages | awk "
                "'NF && $1 != \"Standard\" { print $1 }' | LC_ALL=C sort > "
                "/tmp/caddy-rebuilt-modules; \\"
            ),
            "    diff -u /tmp/caddy-official-modules /tmp/caddy-rebuilt-modules; \\",
            "    apk add --no-cache \\",
            '      "c-ares>=1.34.8-r0" \\',
            '      "curl>=8.20.0-r0" \\',
            '      "libcurl>=8.20.0-r0" \\',
            '      "libcrypto3>=3.5.8-r0" \\',
            '      "libssl3>=3.5.8-r0"; \\',
            "    mv /usr/bin/caddy.pulseplate /usr/bin/caddy; \\",
            "    setcap cap_net_bind_service=+ep /usr/bin/caddy; \\",
            "    getcap /usr/bin/caddy | grep -F 'cap_net_bind_service=ep'; \\",
            (
                '    caddy version | awk \'NR == 1 && $1 == "v2.11.4" { found=1 } '
                "END { exit found ? 0 : 1 }'; \\"
            ),
            (
                "    caddy build-info | awk -F '\\t' '$1 == \"go\" && $2 == "
                '"go1.26.6" { found=1 } END { exit found ? 0 : 1 }\'; \\'
            ),
            "    rm -f /tmp/caddy-official-modules /tmp/caddy-rebuilt-modules",
            "",
            'RUN ["/bin/busybox", "rm", "-rf", "/srv/frontend"]',
            "COPY --from=frontend-build /app/dist /srv/frontend",
        )
    )
    + "\n"
)


def _workflow(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _job(workflow: dict[str, object], name: str) -> dict[str, object]:
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    job = jobs.get(name)
    assert isinstance(job, dict)
    return job


def _steps(job: dict[str, object]) -> list[dict[str, object]]:
    raw_steps = job.get("steps")
    assert isinstance(raw_steps, list)
    result: list[dict[str, object]] = []
    for step in raw_steps:
        assert isinstance(step, dict)
        result.append(step)
    return result


def _named_step(steps: list[dict[str, object]], name: str) -> dict[str, object]:
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"Missing workflow step: {name}")


def _step_index(steps: list[dict[str, object]], name: str) -> int:
    return steps.index(_named_step(steps, name))


def _assert_caddy_builder_stage_contract(text: str) -> None:
    builder_stage_marker = f"FROM {GO_BUILDER} AS caddy-build\n"
    node_stage_marker = f"FROM {NODE_BUILDER} AS frontend-build\n"
    assert text.count(builder_stage_marker) == 1
    assert text.count(node_stage_marker) == 1
    builder_start = text.index(builder_stage_marker)
    node_start = text.index(node_stage_marker, builder_start)
    assert text[builder_start:node_start] == EXPECTED_CADDY_BUILDER_STAGE


def _assert_caddy_openssl_runtime_floor_contract(text: str) -> None:
    final_stage_marker = f"FROM {CADDY_BASE}\n"
    assert text.count(final_stage_marker) == 1
    _, final_stage = text.split(final_stage_marker, maxsplit=1)
    assert final_stage_marker + final_stage == EXPECTED_CADDY_FINAL_STAGE


def test_frontend_workflow_routes_quick_fix_through_caddy_contract() -> None:
    workflow = _workflow(FRONTEND_WORKFLOW)
    triggers = workflow.get("on", workflow.get(True))
    assert isinstance(triggers, dict)
    quick_fix = "scripts/QUICK_FIX_PRODUCTION.sh"

    pull_request = triggers.get("pull_request")
    assert isinstance(pull_request, dict)
    pull_request_paths = pull_request.get("paths")
    assert isinstance(pull_request_paths, list)
    assert ".github/workflows/frontend-ci.yml" in pull_request_paths
    assert quick_fix in pull_request_paths

    push = triggers.get("push")
    assert isinstance(push, dict)
    push_paths = push.get("paths")
    assert isinstance(push_paths, list)
    assert quick_fix in push_paths

    changes = _job(workflow, "changes")
    filter_step = _named_step(_steps(changes), "Detect Caddy contract changes")
    filter_with = filter_step.get("with")
    assert isinstance(filter_with, dict)
    filters_text = filter_with.get("filters")
    assert isinstance(filters_text, str)
    filters = yaml.safe_load(filters_text)
    assert isinstance(filters, dict)
    caddy_paths = filters.get("caddy")
    assert isinstance(caddy_paths, list)
    assert quick_fix in caddy_paths


def test_caddy_dockerfile_owns_exact_hardened_build_recipe() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")

    _assert_caddy_builder_stage_contract(text)
    assert f"FROM {GO_BUILDER} AS caddy-build" in text
    assert f"FROM {NODE_BUILDER} AS frontend-build" in text
    assert f"FROM {CADDY_BASE}" in text
    assert "GOTOOLCHAIN=local" in text
    assert "CGO_ENABLED=0" in text
    assert "GOPROXY=https://proxy.golang.org,direct" in text
    assert "GOSUMDB=sum.golang.org" in text
    assert 'build_dir="$(mktemp -d)"' in text
    assert "go mod init pulseplate.local/caddy-build" in text
    caddy_get = "go get github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.4"
    grpc_get = "go get google.golang.org/grpc@v1.83.2"
    crypto_get = "go get golang.org/x/crypto@v0.55.0"
    assert caddy_get in text
    assert grpc_get in text
    assert text.count(crypto_get) == 1
    assert text.index(caddy_get) < text.index(grpc_get) < text.index(crypto_get)
    assert text.index(crypto_get) < text.index("go mod download all")
    assert "go mod download all" in text
    assert "go mod verify" in text
    for exact_graph_identity in (
        "github.com/caddyserver/caddy/v2 v2.11.4",
        "google.golang.org/grpc v1.83.2",
        "golang.org/x/crypto v0.55.0",
        "golang.org/x/mod v0.38.0",
        "golang.org/x/net v0.58.0",
        "golang.org/x/sync v0.22.0",
        "golang.org/x/sys v0.47.0",
        "golang.org/x/telemetry v0.0.0-20260708182218-49f421fb7959",
        "golang.org/x/term v0.45.0",
        "golang.org/x/text v0.41.0",
        "golang.org/x/tools v0.48.0",
    ):
        assert f"'{exact_graph_identity}'" in text
    assert "test -z \"$(go list -m -f '{{if .Replace}}" in text
    assert "cmp /tmp/caddy-expected-graph /tmp/caddy-governed-graph" in text
    assert "go build -mod=readonly -trimpath" in text
    assert "github.com/caddyserver/caddy/v2.CustomVersion=v2.11.4" in text
    assert "go version -m /go/bin/caddy > /tmp/caddy-binary-metadata" in text
    assert "cmp /tmp/caddy-expected-binary /tmp/caddy-governed-binary" in text
    for exact_binary_identity in (
        "mod github.com/caddyserver/caddy/v2 v2.11.4",
        "dep google.golang.org/grpc v1.83.2",
        "dep golang.org/x/crypto v0.55.0",
        "dep golang.org/x/net v0.58.0",
        "dep golang.org/x/sync v0.22.0",
        "dep golang.org/x/sys v0.47.0",
        "dep golang.org/x/term v0.45.0",
        "dep golang.org/x/text v0.41.0",
    ):
        assert f"'{exact_binary_identity}'" in text
    assert '"c-ares>=1.34.8-r0"' in text
    assert '"curl>=8.20.0-r0"' in text
    assert '"libcurl>=8.20.0-r0"' in text
    assert "COPY --from=caddy-build --chmod=0755 /go/bin/caddy" in text
    assert "caddy list-modules --packages" in text
    assert "setcap cap_net_bind_service=+ep /usr/bin/caddy" in text
    assert "getcap /usr/bin/caddy" in text
    for forbidden in (
        "@latest",
        "--allow-untrusted",
        "go install",
        "go mod edit -replace",
        "go mod edit --replace",
        "GOINSECURE",
        "GONOSUMDB",
        "GOSUMDB=off",
        "google.golang.org/grpc@v1.81.0",
        "google.golang.org/grpc v1.81.0",
        "google.golang.org/grpc@v1.82.1",
        "google.golang.org/grpc v1.82.1",
        "golang.org/x/crypto@v0.53.0",
        "golang.org/x/crypto@v0.54.0",
        "golang.org/x/crypto v0.53.0",
        "golang.org/x/crypto v0.54.0",
        "go get golang.org/x/mod@",
        "go get golang.org/x/net@",
        "go get golang.org/x/sync@",
        "go get golang.org/x/sys@",
        "go get golang.org/x/telemetry@",
        "go get golang.org/x/term@",
        "go get golang.org/x/text@",
        "go get golang.org/x/tools@",
        "golang.org/x/text@v0.37.0",
        "golang.org/x/text v0.37.0",
        "golang.org/x/text@v0.39.0",
        "golang.org/x/text v0.39.0",
        "GONOPROXY",
        "GOPRIVATE",
        "go env -w",
        "-mod=vendor",
        "xcaddy",
    ):
        assert forbidden not in text
    assert re.search(r"(?m)^\s*replace(?:\s|=)", text) is None
    assert "CVE-2026-56852" not in (REPO_ROOT / ".trivyignore").read_text(encoding="utf-8")
    assert 'rm -rf "$build_dir"' in text


def test_caddy_dockerfile_keeps_closed_fixed_builder_stage_recipe() -> None:
    _assert_caddy_builder_stage_contract(DOCKERFILE.read_text(encoding="utf-8"))


def test_caddy_cve_owner_and_ledger_remain_one_bounded_contract() -> None:
    ledger = BACKLOG_LEDGER.read_text(encoding="utf-8")
    anchor = '<a id="ledger-p1-caddy-cve-2026-56854-remediation"></a>'
    exit_anchor = '<a id="ledger-p1-caddy-x-crypto-upstream-exit"></a>'
    assert ledger.count(anchor) == 1
    assert ledger.count(exit_anchor) == 1
    start = ledger.index(anchor)
    end = ledger.index(exit_anchor, start)
    item = ledger[start:end]
    for required in (
        "Owner: @katsiaryna_kavaleuskaya (Security/SRE)",
        "Priority: P1 (required current-head security gate)",
        "Target PR: [#2356]",
        "Status:",
        "Reason (EN):",
        "Links:",
        "DoD:",
        "Rollback:",
        "Exit criteria:",
        "../security/PR_2356_CVE_2026_56854_CONTAINER_RUNTIME_REMEDIATION.md",
    ):
        assert required in item

    owner = CVE_SECURITY_OWNER.read_text(encoding="utf-8")
    for required in (
        "## Decision and authority boundary",
        "## Exact base failure evidence",
        "## D / S / A / R / P reconciliation",
        "### I_R — one authored replacement action",
        "### C_R — deterministic resolver closure",
        "### P — required universal head postcondition",
        "## Local exact candidate image evidence",
        "## Rollback and exit criteria",
        "trivy_high_critical_findings=0",
    ):
        assert owner.count(required) == 1


@pytest.mark.parametrize(
    "case",
    (
        "omitted",
        "duplicate",
        "reordered",
        "downgraded-0.53",
        "downgraded-0.54",
        "floating",
        "replaced",
        "local",
        "checksum-bypass",
        "independent-closure-action",
        "graph-fixed-binary-stale",
        "binary-fixed-graph-stale",
    ),
)
def test_caddy_builder_stage_snapshot_rejects_dependency_contract_drift(case: str) -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    crypto_action = "    go get golang.org/x/crypto@v0.55.0; \\\n"

    if case == "omitted":
        candidate = source.replace(crypto_action, "", 1)
    elif case == "duplicate":
        candidate = source.replace(crypto_action, crypto_action * 2, 1)
    elif case == "reordered":
        candidate = source.replace(crypto_action, "", 1).replace(
            "    go mod verify; \\\n",
            "    go mod verify; \\\n" + crypto_action,
            1,
        )
    elif case == "downgraded-0.53":
        candidate = source.replace("x/crypto@v0.55.0", "x/crypto@v0.53.0", 1)
    elif case == "downgraded-0.54":
        candidate = source.replace("x/crypto@v0.55.0", "x/crypto@v0.54.0", 1)
    elif case == "floating":
        candidate = source.replace("x/crypto@v0.55.0", "x/crypto@latest", 1)
    elif case == "replaced":
        candidate = source.replace(
            "    go mod init pulseplate.local/caddy-build; \\\n",
            "    go mod init pulseplate.local/caddy-build; \\\n"
            "    go mod edit -replace=golang.org/x/crypto=../crypto; \\\n",
            1,
        )
    elif case == "local":
        candidate = source.replace(
            crypto_action,
            crypto_action + "    go get ../crypto; \\\n",
            1,
        )
    elif case == "checksum-bypass":
        candidate = source.replace("    GOSUMDB=sum.golang.org", "    GOSUMDB=off", 1)
    elif case == "independent-closure-action":
        candidate = source.replace(
            crypto_action,
            crypto_action + "    go get golang.org/x/text@v0.41.0; \\\n",
            1,
        )
    elif case == "graph-fixed-binary-stale":
        candidate = source.replace(
            "      'dep golang.org/x/crypto v0.55.0' \\\n",
            "      'dep golang.org/x/crypto v0.54.0' \\\n",
            1,
        )
    else:
        assert case == "binary-fixed-graph-stale"
        candidate = source.replace(
            "      'golang.org/x/crypto v0.55.0' \\\n",
            "      'golang.org/x/crypto v0.54.0' \\\n",
            1,
        )

    assert candidate != source
    with pytest.raises(AssertionError):
        _assert_caddy_builder_stage_contract(candidate)


def test_caddy_dockerfile_keeps_closed_fixed_openssl_final_stage_recipe() -> None:
    _assert_caddy_openssl_runtime_floor_contract(DOCKERFILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "case",
    (
        "lower-floor",
        "partial-floor",
        "substitute-floor",
        "insert-before-transaction",
        "insert-after-transaction",
    ),
)
def test_caddy_openssl_final_stage_snapshot_rejects_representative_byte_drift(
    case: str,
) -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    if case == "lower-floor":
        candidate = source.replace("3.5.8-r0", "3.5.7-r0")
    elif case == "partial-floor":
        candidate = source.replace(
            '      "libssl3>=3.5.8-r0"; \\\n',
            "",
            1,
        )
    elif case == "substitute-floor":
        candidate = source.replace(
            '      "libcrypto3>=3.5.8-r0" \\\n' '      "libssl3>=3.5.8-r0"; \\\n',
            '      "openssl>=3.5.8-r0"; \\\n',
            1,
        )
    elif case == "insert-before-transaction":
        candidate = source.replace(
            "    apk add --no-cache \\\n",
            "    true; \\\n    apk add --no-cache \\\n",
            1,
        )
    else:
        assert case == "insert-after-transaction"
        candidate = source.replace(
            "    mv /usr/bin/caddy.pulseplate /usr/bin/caddy; \\\n",
            "    true; \\\n    mv /usr/bin/caddy.pulseplate /usr/bin/caddy; \\\n",
            1,
        )

    with pytest.raises(AssertionError):
        _assert_caddy_openssl_runtime_floor_contract(candidate)


def test_staging_compose_requires_two_digest_references_and_preserves_caddy_state() -> None:
    compose = yaml.safe_load(STAGING_COMPOSE.read_text(encoding="utf-8"))
    assert isinstance(compose, dict)
    assert "version" not in compose
    services = compose.get("services")
    assert isinstance(services, dict)

    app = services.get("app")
    caddy = services.get("caddy")
    prometheus = services.get("prometheus")
    assert isinstance(app, dict)
    assert isinstance(caddy, dict)
    assert isinstance(prometheus, dict)
    assert app["image"] == "${STAGING_IMAGE_REF:?STAGING_IMAGE_REF is required}"
    assert caddy["image"] == ("${STAGING_CADDY_IMAGE_REF:?STAGING_CADDY_IMAGE_REF is required}")
    assert "caddy_data:/data" in caddy["volumes"]
    assert "caddy_config:/config" in caddy["volumes"]
    assert caddy["depends_on"]["app"]["condition"] == "service_healthy"
    assert compose["networks"]["observability"] == {"internal": True}
    assert app["networks"] == ["web", "observability", "database"]
    assert app["secrets"] == ["pulseplate_metrics_scrape_key", "postgres_ca", "postgres_pgpass"]
    assert prometheus["networks"] == ["observability", "alerting"]
    assert prometheus["secrets"] == ["pulseplate_metrics_scrape_key"]
    assert "ports" not in prometheus
    assert compose["secrets"] == {
        "pulseplate_metrics_scrape_key": {"file": "./secrets/pulseplate_metrics_scrape_key"},
        "alertmanager_smtp_key": {"file": "./secrets/alertmanager_smtp_key"},
        "postgres_ca": {"file": "./secrets/postgres_ca"},
        "postgres_server_crt": {"file": "./secrets/postgres_server_crt"},
        "postgres_server_key": {"file": "./secrets/postgres_server_key"},
        "postgres_password": {"file": "./secrets/postgres_password"},
        "postgres_pgpass": {"file": "./secrets/postgres_pgpass"},
    }
    assert "prometheus_data" in compose["volumes"]

    text = STAGING_COMPOSE.read_text(encoding="utf-8")
    assert "${TAG:-latest}" not in text
    assert "caddy:2" not in text
    assert "staging-latest" not in text
    assert PROMETHEUS_CONFIG.is_file()
    assert PROMETHEUS_IMAGE_MANIFEST.is_file()


def test_cd_builds_attests_scans_and_deploys_both_same_job_digests() -> None:
    workflow = _workflow(CD_WORKFLOW)
    build_job = _job(workflow, "build")
    steps = _steps(build_job)

    required_order = (
        "Build & Push backend image (staging)",
        "Build & Push Caddy image (staging)",
        "Validate immutable staging image references",
        "Verify staged backend image attestations",
        "Verify staged Caddy image attestations",
        "Prepare Trivy ignore policy",
        "Scan staged backend image",
        "Scan staged Caddy image",
        "Verify remote staging deploy contract",
        "Deploy to staging over SSH",
        "Healthcheck (staging)",
    )
    indexes = [_step_index(steps, name) for name in required_order]
    assert indexes == sorted(indexes)

    backend_build = _named_step(steps, "Build & Push backend image (staging)")
    caddy_build = _named_step(steps, "Build & Push Caddy image (staging)")
    assert backend_build["id"] == "build"
    assert caddy_build["id"] == "build-caddy"
    backend_with = backend_build.get("with")
    caddy_with = caddy_build.get("with")
    assert isinstance(backend_with, dict)
    assert isinstance(caddy_with, dict)
    assert "staging-backend-${{ github.sha }}" in backend_with["tags"]
    assert "staging-caddy-${{ github.sha }}" in caddy_with["tags"]

    prepare_policy = _named_step(steps, "Prepare Trivy ignore policy")
    assert prepare_policy.get("continue-on-error") is not True
    assert prepare_policy["run"].splitlines() == [
        "set -euo pipefail",
        "test -f .trivyignore",
        "test -f trivy/ignore-policy.rego",
        "cp trivy/ignore-policy.rego .trivy-ignore-policy.rego",
        "test -s .trivy-ignore-policy.rego",
        "cmp -s trivy/ignore-policy.rego .trivy-ignore-policy.rego",
        "rm -f -- .trivyignore-caddy",
        ": > .trivyignore-caddy",
        "test -f .trivyignore-caddy",
        "test ! -L .trivyignore-caddy",
        "test ! -s .trivyignore-caddy",
    ]
    assert _step_index(steps, "Prepare Trivy ignore policy") + 1 == _step_index(
        steps, "Scan staged backend image"
    )
    assert _step_index(steps, "Scan staged backend image") + 1 == _step_index(
        steps, "Scan staged Caddy image"
    )

    common_scan_contract = {
        "scan-type": "image",
        "scanners": "vuln,secret",
        "format": "table",
        "vuln-type": "os,library",
        "severity": "CRITICAL,HIGH",
        "exit-code": "1",
        "timeout": "15m",
        "version": TRIVY_VERSION,
    }
    trivy_steps = [
        step
        for step in steps
        if isinstance(step.get("uses"), str)
        and str(step["uses"]).startswith("aquasecurity/trivy-action@")
    ]
    assert [step.get("name") for step in trivy_steps] == [
        "Scan staged backend image",
        "Scan staged Caddy image",
    ]
    for name, digest_ref, cache_dir, policy_contract in (
        (
            "Scan staged backend image",
            "steps.staging-image-refs.outputs.backend_ref",
            "/tmp/trivy-cache-staging-backend",
            {
                "trivyignores": ".trivyignore",
                "ignore-policy": ".trivy-ignore-policy.rego",
            },
        ),
        (
            "Scan staged Caddy image",
            "steps.staging-image-refs.outputs.caddy_ref",
            "/tmp/trivy-cache-staging-caddy",
            {"trivyignores": ".trivyignore-caddy"},
        ),
    ):
        step = _named_step(steps, name)
        assert step.get("continue-on-error") is None
        assert step["uses"] == TRIVY_ACTION
        assert step["env"] == {
            "TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db",
        }
        with_block = step.get("with")
        assert isinstance(with_block, dict)
        assert with_block == {
            **common_scan_contract,
            "image-ref": "${{ " + digest_ref + " }}",
            **policy_contract,
            "cache-dir": cache_dir,
        }

    image_refs = _named_step(steps, "Validate immutable staging image references")
    image_refs_env = image_refs.get("env")
    assert isinstance(image_refs_env, dict)
    assert image_refs_env["BACKEND_DIGEST"] == "${{ steps.build.outputs.digest }}"
    assert image_refs_env["CADDY_DIGEST"] == "${{ steps.build-caddy.outputs.digest }}"

    preflight = _named_step(steps, "Verify remote staging deploy contract")
    preflight_env = preflight.get("env")
    preflight_with = preflight.get("with")
    assert isinstance(preflight_env, dict)
    assert isinstance(preflight_with, dict)
    assert preflight_env["STAGING_DOMAIN"] == "${{ secrets.STAGING_DOMAIN }}"
    assert preflight_env["PROMETHEUS_RULES_SHA256"] == (
        "${{ steps.staging-contract.outputs.prometheus_rules_sha256 }}"
    )
    assert preflight_with["envs"] == (
        "STAGING_DOMAIN,STAGING_IMAGE_REF,STAGING_CADDY_IMAGE_REF,"
        "DEPLOY_SCRIPT_SHA256,STAGING_COMPOSE_SHA256,"
        "PROMETHEUS_CONFIG_SHA256,PROMETHEUS_RULES_SHA256,"
        "PROMETHEUS_IMAGE_MANIFEST_SHA256,"
        "ALERTMANAGER_CONFIG_SHA256,ALERTMANAGER_TRIVY_IGNORE_SHA256,"
        "POSTGRES_IMAGE_MANIFEST_SHA256,"
        "STAGING_CADDYFILE_SHA256,BACKUP_HELPER_SHA256,RESTORE_HELPER_SHA256,"
        "STAGING_SECURITY_HELPER_SHA256,PGVECTOR_ATTESTATION_HELPER_SHA256,"
        "NATIVE_ATTESTATION_HELPER_SHA256,POSTGRES_HBA_SHA256,"
        "STAGING_STORAGE_SYSTEMD_SHA256,STAGING_BACKUP_SYSTEMD_SHA256,STAGING_BACKUP_TIMER_SHA256,"
        "CHECKPOINT_VERIFIER_SHA256,CHECKPOINT_NOTIFIER_SHA256,CHECKPOINT_SERVICE_SHA256,"
        "CHECKPOINT_TIMER_SHA256,CHECKPOINT_FAILURE_SHA256"
    )

    deploy = _named_step(steps, "Deploy to staging over SSH")
    deploy_if = deploy.get("if")
    assert isinstance(deploy_if, str)
    assert "vars.STAGING_ATTESTED_DIGEST_READY == 'true'" in deploy_if
    assert "steps.staging-contract-preflight.outcome == 'success'" in deploy_if
    deploy_with = deploy.get("with")
    assert isinstance(deploy_with, dict)
    assert "${{ secrets." not in deploy_with["script"]
    assert "$GHCR_TOKEN" not in deploy_with["script"]
    assert "GHCR_TOKEN=" not in deploy_with["script"]
    assert "github.sha" not in deploy_with["script"]
    assert deploy_with["envs"] == (
        "GHCR_USER,GHCR_TOKEN,STAGING_DOMAIN,STAGING_IMAGE_REF,"
        "STAGING_CADDY_IMAGE_REF,DEPLOY_SCRIPT_SHA256,STAGING_COMPOSE_SHA256,"
        "PROMETHEUS_CONFIG_SHA256,PROMETHEUS_RULES_SHA256,"
        "PROMETHEUS_IMAGE_MANIFEST_SHA256,"
        "ALERTMANAGER_CONFIG_SHA256,ALERTMANAGER_TRIVY_IGNORE_SHA256,"
        "POSTGRES_IMAGE_MANIFEST_SHA256,"
        "STAGING_CADDYFILE_SHA256,BACKUP_HELPER_SHA256,RESTORE_HELPER_SHA256,"
        "STAGING_SECURITY_HELPER_SHA256,PGVECTOR_ATTESTATION_HELPER_SHA256,"
        "NATIVE_ATTESTATION_HELPER_SHA256,POSTGRES_HBA_SHA256,"
        "STAGING_STORAGE_SYSTEMD_SHA256,STAGING_BACKUP_SYSTEMD_SHA256,STAGING_BACKUP_TIMER_SHA256,"
        "CHECKPOINT_VERIFIER_SHA256,CHECKPOINT_NOTIFIER_SHA256,CHECKPOINT_SERVICE_SHA256,"
        "CHECKPOINT_TIMER_SHA256,CHECKPOINT_FAILURE_SHA256"
    )

    assert build_job["concurrency"]["cancel-in-progress"] is False

    readiness = _named_step(steps, "Check staging deploy readiness")
    readiness_env = readiness.get("env")
    assert isinstance(readiness_env, dict)
    assert readiness_env["STAGING_DEPLOY_REQUIRED"] == ("${{ vars.STAGING_DEPLOY_REQUIRED }}")
    assert "staging credentials are incomplete" in readiness["run"]
    assert "STAGING_DEPLOY_REQUIRED=true" in readiness["run"]

    required_policy = _named_step(steps, "Enforce required staging deployment policy")
    assert "if" not in required_policy
    required_policy_env = required_policy.get("env")
    assert isinstance(required_policy_env, dict)
    assert required_policy_env == {
        "STAGING_DEPLOY_REQUIRED": "${{ vars.STAGING_DEPLOY_REQUIRED }}",
        "STAGING_DEPLOY_ENABLED": "${{ vars.STAGING_DEPLOY_ENABLED }}",
        "WEB_IOS_RELEASE_READY": "${{ vars.WEB_IOS_RELEASE_READY }}",
        "STAGING_ATTESTED_DIGEST_READY": "${{ vars.STAGING_ATTESTED_DIGEST_READY }}",
    }
    required_policy_run = required_policy["run"]
    for gate in (
        "STAGING_DEPLOY_ENABLED",
        "WEB_IOS_RELEASE_READY",
        "STAGING_ATTESTED_DIGEST_READY",
    ):
        assert gate in required_policy_run
    assert "STAGING_DEPLOY_REQUIRED=true requires ${required_gate}=true" in required_policy_run

    healthcheck = _named_step(steps, "Healthcheck (staging)")
    healthcheck_env = healthcheck.get("env")
    assert isinstance(healthcheck_env, dict)
    assert healthcheck_env["STAGING_DOMAIN_REF"] == "${{ secrets.STAGING_DOMAIN }}"
    assert "${{ secrets.STAGING_DOMAIN }}" not in healthcheck["run"]
    assert '"https://${STAGING_DOMAIN_REF}/ready"' in healthcheck["run"]


def test_remote_contract_preflight_has_no_registry_secret_and_checks_current_files() -> None:
    workflow = _workflow(CD_WORKFLOW)
    steps = _steps(_job(workflow, "build"))
    preflight = _named_step(steps, "Verify remote staging deploy contract")
    assert preflight.get("continue-on-error") is not True
    env = preflight.get("env")
    with_block = preflight.get("with")
    assert isinstance(env, dict)
    assert isinstance(with_block, dict)
    assert "GHCR_READ_TOKEN" not in str(env)
    assert "GHCR_TOKEN" not in str(env)
    assert "GHCR_TOKEN" not in str(with_block)
    assert with_block["envs"] == (
        "STAGING_DOMAIN,STAGING_IMAGE_REF,STAGING_CADDY_IMAGE_REF,DEPLOY_SCRIPT_SHA256,"
        "STAGING_COMPOSE_SHA256,PROMETHEUS_CONFIG_SHA256,PROMETHEUS_RULES_SHA256,"
        "PROMETHEUS_IMAGE_MANIFEST_SHA256,ALERTMANAGER_CONFIG_SHA256,"
        "ALERTMANAGER_TRIVY_IGNORE_SHA256,POSTGRES_IMAGE_MANIFEST_SHA256,"
        "STAGING_CADDYFILE_SHA256,BACKUP_HELPER_SHA256,RESTORE_HELPER_SHA256,"
        "STAGING_SECURITY_HELPER_SHA256,PGVECTOR_ATTESTATION_HELPER_SHA256,"
        "NATIVE_ATTESTATION_HELPER_SHA256,POSTGRES_HBA_SHA256,"
        "STAGING_STORAGE_SYSTEMD_SHA256,STAGING_BACKUP_SYSTEMD_SHA256,STAGING_BACKUP_TIMER_SHA256,"
        "CHECKPOINT_VERIFIER_SHA256,CHECKPOINT_NOTIFIER_SHA256,CHECKPOINT_SERVICE_SHA256,"
        "CHECKPOINT_TIMER_SHA256,CHECKPOINT_FAILURE_SHA256"
    )
    script = with_block["script"]
    assert ".attested-digest-deploy-v1" in script
    assert "pulseplate-staging-attested-digest-v1" in script
    assert 'STAGING_DEPLOY_CONTRACT_VERSION="5"' in script
    for filename in (
        "deploy.sh",
        "docker-compose.staging.yaml",
        "prometheus/prometheus.yml",
        "prometheus/alias-alerts.yml",
        "prometheus/image-manifest.json",
        "alertmanager/alertmanager.yml",
        "alertmanager/trivy-ignore.yaml",
        "postgres-pgvector/image-manifest.json",
        "Caddyfile",
        "scripts/ops/postgres_backup.sh",
        "scripts/ops/postgres_restore.sh",
        "scripts/ops/check_staging_security.py",
        "scripts/ci/check_pgvector_attestations.py",
        "scripts/ci/check_docker_provenance_attestation.py",
        "postgres-pgvector/pg_hba.conf",
        "systemd/pulseplate-staging-storage.conf",
        "systemd/pulseplate-postgres-backup.service.example",
        "systemd/pulseplate-postgres-backup.timer.example",
    ):
        no_link = f"[ ! -L ./{filename} ]"
        regular = f"[ -f ./{filename} ]"
        digest = f"sha256sum ./{filename}"
        assert script.index(no_link) < script.index(regular) < script.index(digest)
        assert script.index(digest) < script.index("sudo -n ")
    assert PROMETHEUS_RULES_HASH_CHECK in script
    assert script.index(PROMETHEUS_RULES_HASH_CHECK) < script.index("sudo -n ")
    assert "/bin/bash /srv/pulseplate-staging/deploy.sh" in script
    assert '--preflight-only "$STAGING_IMAGE_REF" "$STAGING_CADDY_IMAGE_REF"' in script


@pytest.mark.parametrize(
    "phase", ["Verify remote staging deploy contract", "Deploy to staging over SSH"]
)
@pytest.mark.parametrize("fault", ["none", "stale", "absent", "symlink", "directory", "fifo"])
def test_restore_helper_hash_blocks_stale_remote_bundle(
    tmp_path: Path, phase: str, fault: str
) -> None:
    steps = _steps(_job(_workflow(CD_WORKFLOW), "build"))
    producer = _named_step(steps, "Prepare staging deploy contract hashes")["run"]
    assert "restore_helper_sha256=$(sha256sum scripts/ops/postgres_restore.sh" in producer
    step = _named_step(steps, phase)
    assert step["env"]["RESTORE_HELPER_SHA256"] == (
        "${{ steps.staging-contract.outputs.restore_helper_sha256 }}"
    )
    script = step["with"]["script"]
    checks = [line for line in script.splitlines() if "./scripts/ops/postgres_restore.sh" in line]
    assert len(checks) == 3
    assert "] && [" not in script
    assert all(script.index(line) < script.index("sudo -n ") for line in checks)
    target = tmp_path / "scripts/ops/postgres_restore.sh"
    target.parent.mkdir(parents=True)
    admitted = b"reviewed restore fixture\n"
    if fault == "symlink":
        external = tmp_path / "external"
        external.write_bytes(admitted)
        target.symlink_to(external)
    elif fault == "directory":
        target.mkdir()
    elif fault == "fifo":
        os.mkfifo(target)
    elif fault != "absent":
        target.write_bytes(b"old restore fixture\n" if fault == "stale" else admitted)
    bash = shutil.which("bash")
    assert bash is not None
    completed = subprocess.run(
        [bash, "-c", "set -euo pipefail\n" + "\n".join(checks)],
        cwd=tmp_path,
        env={**os.environ, "RESTORE_HELPER_SHA256": hashlib.sha256(admitted).hexdigest()},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert (completed.returncode == 0) is (fault == "none"), completed.stderr
    if fault == "symlink":
        assert external.read_bytes() == admitted


def test_all_staging_ssh_and_health_steps_require_default_false_rollout_gate() -> None:
    workflow = _workflow(CD_WORKFLOW)
    steps = _steps(_job(workflow, "build"))
    for name in (
        "Check staging deploy readiness",
        "Verify remote staging deploy contract",
        "Deploy to staging over SSH",
        "Handle staging deployment failure (non-blocking by default)",
        "Healthcheck (staging)",
    ):
        step_if = _named_step(steps, name).get("if")
        assert isinstance(step_if, str)
        assert "vars.STAGING_DEPLOY_ENABLED == 'true'" in step_if
        assert "vars.WEB_IOS_RELEASE_READY == 'true'" in step_if
        assert "vars.STAGING_ATTESTED_DIGEST_READY == 'true'" in step_if


def test_credentialed_deploy_revalidates_the_preflighted_remote_contract() -> None:
    workflow = _workflow(CD_WORKFLOW)
    steps = _steps(_job(workflow, "build"))
    deploy = _named_step(steps, "Deploy to staging over SSH")
    env = deploy.get("env")
    with_block = deploy.get("with")
    assert isinstance(env, dict)
    assert isinstance(with_block, dict)
    assert env["DEPLOY_SCRIPT_SHA256"] == (
        "${{ steps.staging-contract.outputs.deploy_script_sha256 }}"
    )
    assert env["STAGING_COMPOSE_SHA256"] == (
        "${{ steps.staging-contract.outputs.staging_compose_sha256 }}"
    )
    assert env["STAGING_CADDYFILE_SHA256"] == (
        "${{ steps.staging-contract.outputs.staging_caddyfile_sha256 }}"
    )
    assert env["BACKUP_HELPER_SHA256"] == (
        "${{ steps.staging-contract.outputs.backup_helper_sha256 }}"
    )
    assert env["PROMETHEUS_CONFIG_SHA256"] == (
        "${{ steps.staging-contract.outputs.prometheus_config_sha256 }}"
    )
    assert env["PROMETHEUS_RULES_SHA256"] == (
        "${{ steps.staging-contract.outputs.prometheus_rules_sha256 }}"
    )
    assert env["PROMETHEUS_IMAGE_MANIFEST_SHA256"] == (
        "${{ steps.staging-contract.outputs.prometheus_image_manifest_sha256 }}"
    )
    assert env["POSTGRES_IMAGE_MANIFEST_SHA256"] == (
        "${{ steps.staging-contract.outputs.postgres_image_manifest_sha256 }}"
    )
    assert with_block["envs"].endswith(
        "DEPLOY_SCRIPT_SHA256,STAGING_COMPOSE_SHA256,PROMETHEUS_CONFIG_SHA256,"
        "PROMETHEUS_RULES_SHA256,"
        "PROMETHEUS_IMAGE_MANIFEST_SHA256,ALERTMANAGER_CONFIG_SHA256,"
        "ALERTMANAGER_TRIVY_IGNORE_SHA256,POSTGRES_IMAGE_MANIFEST_SHA256,"
        "STAGING_CADDYFILE_SHA256,BACKUP_HELPER_SHA256,RESTORE_HELPER_SHA256,"
        "STAGING_SECURITY_HELPER_SHA256,PGVECTOR_ATTESTATION_HELPER_SHA256,"
        "NATIVE_ATTESTATION_HELPER_SHA256,POSTGRES_HBA_SHA256,"
        "STAGING_STORAGE_SYSTEMD_SHA256,STAGING_BACKUP_SYSTEMD_SHA256,STAGING_BACKUP_TIMER_SHA256,"
        "CHECKPOINT_VERIFIER_SHA256,CHECKPOINT_NOTIFIER_SHA256,CHECKPOINT_SERVICE_SHA256,"
        "CHECKPOINT_TIMER_SHA256,CHECKPOINT_FAILURE_SHA256"
    )
    script = with_block["script"]
    deploy_call = "/bin/bash /srv/pulseplate-staging/deploy.sh"
    assert script.index(".attested-digest-deploy-v1") < script.index(deploy_call)
    assert script.index('STAGING_DEPLOY_CONTRACT_VERSION="5"') < script.index(deploy_call)
    for filename, expected_hash in (
        ("deploy.sh", "DEPLOY_SCRIPT_SHA256"),
        ("docker-compose.staging.yaml", "STAGING_COMPOSE_SHA256"),
        ("prometheus/prometheus.yml", "PROMETHEUS_CONFIG_SHA256"),
        ("prometheus/alias-alerts.yml", "PROMETHEUS_RULES_SHA256"),
        ("prometheus/image-manifest.json", "PROMETHEUS_IMAGE_MANIFEST_SHA256"),
        ("alertmanager/alertmanager.yml", "ALERTMANAGER_CONFIG_SHA256"),
        ("alertmanager/trivy-ignore.yaml", "ALERTMANAGER_TRIVY_IGNORE_SHA256"),
        ("postgres-pgvector/image-manifest.json", "POSTGRES_IMAGE_MANIFEST_SHA256"),
        ("Caddyfile", "STAGING_CADDYFILE_SHA256"),
        ("scripts/ops/postgres_backup.sh", "BACKUP_HELPER_SHA256"),
        ("scripts/ops/postgres_restore.sh", "RESTORE_HELPER_SHA256"),
        ("scripts/ops/check_staging_security.py", "STAGING_SECURITY_HELPER_SHA256"),
        ("scripts/ci/check_pgvector_attestations.py", "PGVECTOR_ATTESTATION_HELPER_SHA256"),
        ("scripts/ci/check_docker_provenance_attestation.py", "NATIVE_ATTESTATION_HELPER_SHA256"),
        ("postgres-pgvector/pg_hba.conf", "POSTGRES_HBA_SHA256"),
        ("systemd/pulseplate-staging-storage.conf", "STAGING_STORAGE_SYSTEMD_SHA256"),
        ("systemd/pulseplate-postgres-backup.service.example", "STAGING_BACKUP_SYSTEMD_SHA256"),
        ("systemd/pulseplate-postgres-backup.timer.example", "STAGING_BACKUP_TIMER_SHA256"),
    ):
        hash_check = f"sha256sum ./{filename}"
        no_link = f"[ ! -L ./{filename} ]"
        regular = f"[ -f ./{filename} ]"
        assert script.index(no_link) < script.index(regular) < script.index(hash_check)
        assert hash_check in script
        assert expected_hash in script
        assert script.index(hash_check) < script.index(deploy_call)
    assert PROMETHEUS_RULES_HASH_CHECK in script
    assert script.index(PROMETHEUS_RULES_HASH_CHECK) < script.index(deploy_call)


def test_staging_deploy_script_embeds_marker_and_two_digest_contract() -> None:
    text = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    assert 'STAGING_DEPLOY_CONTRACT_VERSION="5"' in text
    assert 'STAGING_DEPLOY_MARKER_CONTENT="pulseplate-staging-attested-digest-v1"' in text
    assert "0:0:644" in text
    assert "STAGING_IMAGE_REF" in text
    assert "STAGING_CADDY_IMAGE_REF" in text
    assert "${TAG:-latest}" not in text
    assert 'IMG_REF="${1:-latest}"' not in text
    assert "|| true" not in text


def test_frontend_caddy_contract_is_non_publishing_and_unprivileged() -> None:
    workflow = _workflow(FRONTEND_WORKFLOW)
    changes_steps = _steps(_job(workflow, "changes"))
    job = _job(workflow, "caddy-contract")
    assert job["if"] == (
        "${{ !cancelled() && (needs.changes.outputs.caddy == 'true' "
        "|| github.event_name == 'workflow_dispatch') }}"
    )
    assert job["permissions"] == {"contents": "read"}
    assert "environment" not in job
    steps = _steps(job)
    text = str(steps)
    changes_checkout = _named_step(changes_steps, "Checkout code")
    contract_checkout = _named_step(steps, "Checkout code")
    assert changes_checkout["with"]["persist-credentials"] is False
    assert contract_checkout["with"]["persist-credentials"] is False
    assert "docker/login-action" not in text
    assert "appleboy/ssh-action" not in text
    assert "push: true" not in text
    assert "caddy version" in text
    assert "caddy build-info" in text
    assert "caddy validate" in text
    assert "official_caddy_ref=" in text
    assert "^FROM caddy:" in text
    assert "--cap-drop ALL --cap-add NET_BIND_SERVICE" in text
    assert "aquasecurity/trivy-action@" in text

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "set -o pipefail" in dockerfile


def test_production_quick_fix_rebuilds_and_verifies_hardened_caddy() -> None:
    text = (REPO_ROOT / "scripts" / "QUICK_FIX_PRODUCTION.sh").read_text(encoding="utf-8")

    pull_index = text.index("dc pull app")
    build_index = text.index("dc build caddy")
    up_index = text.index("dc up -d --force-recreate")
    version_index = text.index("dc exec -T caddy caddy version")
    build_info_index = text.index("dc exec -T caddy caddy build-info")
    success_index = text.index("Quick Fix Complete")

    assert pull_index < build_index < up_index < version_index < build_info_index < success_index
    assert "dc pull ||" not in text
    assert 'CADDY_VERSION_TOKEN" != "v2.11.4"' in text
    assert 'CADDY_GO_VERSION" != "go1.26.6"' in text
    assert "*v2.11.4*" not in text
    assert "*go1.26.6*" not in text


@pytest.mark.parametrize(
    ("caddy_version", "build_info", "expected_error"),
    (
        ("v2.11.40 h1:test", "go\tgo1.26.6\n", "Expected Caddy v2.11.4"),
        ("v2.11.4 h1:test", "go\tgo1.26.60\n", "Expected Caddy built with Go 1.26.6"),
    ),
)
def test_production_quick_fix_rejects_inexact_caddy_identity(
    tmp_path: Path,
    caddy_version: str,
    build_info: str,
    expected_error: str,
) -> None:
    completed = _run_production_quick_fix(
        tmp_path,
        caddy_version=caddy_version,
        go_version=build_info.removeprefix("go\t").strip(),
    )

    assert completed.returncode == 1
    assert expected_error in completed.stdout
    assert "Quick Fix Complete" not in completed.stdout


def test_production_quick_fix_fails_closed_when_readiness_fails(tmp_path: Path) -> None:
    completed = _run_production_quick_fix(
        tmp_path,
        caddy_version="v2.11.4 h1:test",
        go_version="go1.26.6",
        curl_exit=22,
    )

    assert completed.returncode == 1
    assert "Health check failed after 1 attempts" in completed.stdout
    assert "Quick Fix Complete" not in completed.stdout


def test_production_quick_fix_redacts_duplicate_secret_values(tmp_path: Path) -> None:
    password_sentinel = "duplicate-password-must-not-leak"  # pragma: allowlist secret
    dsn_sentinel = "duplicate-dsn-must-not-leak"  # pragma: allowlist secret
    completed = _run_production_quick_fix(
        tmp_path,
        caddy_version="v2.11.4 h1:test",
        go_version="go1.26.6",
        extra_env=(
            f"POSTGRES_PASSWORD={password_sentinel}\n"
            f"DATABASE_URL=postgresql+psycopg://pulseplate:{dsn_sentinel}@db/pulseplate\n"
        ),
    )

    assert completed.returncode == 1
    assert "Duplicate required environment keys found in .env" in completed.stdout
    assert "POSTGRES_PASSWORD=<redacted>" in completed.stdout
    assert "DATABASE_URL=<redacted>" in completed.stdout
    assert password_sentinel not in completed.stdout
    assert dsn_sentinel not in completed.stdout
    assert "Quick Fix Complete" not in completed.stdout


@pytest.mark.parametrize(
    "duplicate_line",
    (
        "  DATABASE_URL = postgresql+psycopg://hidden-whitespace@db/pulseplate",
        " export DATABASE_URL=postgresql+psycopg://hidden-export@db/pulseplate",
    ),
)
def test_production_quick_fix_rejects_compose_normalized_duplicate_keys(
    tmp_path: Path,
    duplicate_line: str,
) -> None:
    deploy_dir = tmp_path / "production"
    completed = _run_production_quick_fix(
        tmp_path,
        caddy_version="v2.11.4 h1:test",
        go_version="go1.26.6",
        extra_env=f"{duplicate_line}\n",
    )

    env_path = deploy_dir / ".env"
    assert completed.returncode == 1
    assert "Duplicate required environment keys found in .env" in completed.stdout
    assert "DATABASE_URL=<redacted>" in completed.stdout
    assert "hidden-" not in completed.stdout
    assert duplicate_line in env_path.read_text(encoding="utf-8")
    assert list(deploy_dir.glob(".env.backup.*")) == []
    assert (tmp_path / "docker-invocations.log").read_text(encoding="utf-8").splitlines() == [
        "compose version"
    ]
    assert "Quick Fix Complete" not in completed.stdout


def test_production_quick_fix_fails_closed_when_env_file_is_missing(tmp_path: Path) -> None:
    completed = _run_production_quick_fix(
        tmp_path,
        caddy_version="v2.11.4 h1:test",
        go_version="go1.26.6",
        create_env=False,
    )

    assert completed.returncode == 1
    assert "Production environment file is missing or unreadable: .env" in completed.stdout
    assert "awk:" not in completed.stderr
    assert "Quick Fix Complete" not in completed.stdout


def test_production_quick_fix_replaces_env_atomically_with_preserved_mode(tmp_path: Path) -> None:
    completed = _run_production_quick_fix(
        tmp_path,
        caddy_version="v2.11.4 h1:test",
        go_version="go1.26.6",
    )

    env_path = tmp_path / "production" / ".env"
    env_text = env_path.read_text(encoding="utf-8")
    script_text = (REPO_ROOT / "scripts" / "QUICK_FIX_PRODUCTION.sh").read_text(encoding="utf-8")
    assert completed.returncode == 0
    assert stat.S_IMODE(env_path.stat().st_mode) == 0o640
    assert list(env_path.parent.glob(".env.clean.*")) == []
    for required_flag in (
        "APP_ENV=production",
        "ENVIRONMENT=production",
        "SUBSCRIPTION_DB_ENABLED=true",
        "ALLOW_DEV_API_KEY=false",
        "API_KEY_REQUIRED=true",
    ):
        assert env_text.count(required_flag) == 1
    assert script_text.index('} >> "$CLEAN_ENV_FILE"') < script_text.index(
        'mv "$CLEAN_ENV_FILE" .env'
    )
    assert ">> .env" not in script_text


@pytest.mark.parametrize(
    ("legacy_line", "canonical_line"),
    (
        (" export APP_ENV = staging", "APP_ENV=production"),
        ("export ALLOW_DEV_API_KEY = true", "ALLOW_DEV_API_KEY=false"),
    ),
)
def test_production_quick_fix_normalizes_managed_flag_cleanup(
    tmp_path: Path,
    legacy_line: str,
    canonical_line: str,
) -> None:
    completed = _run_production_quick_fix(
        tmp_path,
        caddy_version="v2.11.4 h1:test",
        go_version="go1.26.6",
        extra_env=f"{legacy_line}\n",
    )

    env_text = (tmp_path / "production" / ".env").read_text(encoding="utf-8")
    assert completed.returncode == 0
    assert legacy_line not in env_text
    assert env_text.count(canonical_line) == 1
    assert "Quick Fix Complete" in completed.stdout


def _run_production_quick_fix(
    tmp_path: Path,
    *,
    caddy_version: str,
    go_version: str,
    curl_exit: int = 0,
    extra_env: str = "",
    create_env: bool = True,
) -> subprocess.CompletedProcess[str]:
    deploy_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    deploy_dir.mkdir()
    bin_dir.mkdir()
    (deploy_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    if create_env:
        (deploy_dir / ".env").write_text(
            (
                "DATABASE_URL=postgresql+psycopg://pulseplate@db/pulseplate\n"
                "POSTGRES_DB=pulseplate\n"
                "POSTGRES_USER=pulseplate\n"
                "POSTGRES_PASSWORD=test\n"
                "PRODUCTION_DOMAIN=pulseplate.test\n" + extra_env
            ),
            encoding="utf-8",
        )
        (deploy_dir / ".env").chmod(0o640)
    docker_stub = """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$STUB_DOCKER_LOG"
case "$*" in
  "compose version") exit 0 ;;
  *"exec -T caddy caddy version") printf '%s\n' "$STUB_CADDY_VERSION" ;;
  *"exec -T caddy caddy build-info") printf 'go\t%s\n' "$STUB_GO_VERSION" ;;
  "ps --format {{.Names}}") exit 0 ;;
  *) exit 0 ;;
esac
"""
    curl_stub = '#!/usr/bin/env bash\nprintf \'{"status":"ok"}\\n\'\nexit "$STUB_CURL_EXIT"\n'
    docker_path = bin_dir / "docker"
    curl_path = bin_dir / "curl"
    docker_path.write_text(docker_stub, encoding="utf-8")
    curl_path.write_text(curl_stub, encoding="utf-8")
    docker_path.chmod(0o755)
    curl_path.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DEPLOY_DIR"] = str(deploy_dir)
    env["STUB_CADDY_VERSION"] = caddy_version
    env["STUB_GO_VERSION"] = go_version
    env["STUB_CURL_EXIT"] = str(curl_exit)
    env["STUB_DOCKER_LOG"] = str(tmp_path / "docker-invocations.log")
    env["HEALTH_MAX_ATTEMPTS"] = "1"
    env["HEALTH_SLEEP_S"] = "0"
    env["HEALTH_CURL_MAX_TIME_S"] = "1"
    return subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "QUICK_FIX_PRODUCTION.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_active_caddyfiles_keep_proxy_order_and_security_headers() -> None:
    def active_lines(path: Path) -> list[str]:
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    def directive_blocks(lines: list[str], opener: str) -> list[list[str]]:
        blocks: list[list[str]] = []
        for index, line in enumerate(lines):
            if line != opener:
                continue
            depth = 1
            block: list[str] = []
            for nested in lines[index + 1 :]:
                depth += nested.count("{") - nested.count("}")
                if depth == 0:
                    blocks.append(block)
                    break
                block.append(nested)
            else:
                raise AssertionError(f"unterminated Caddy directive block: {opener}")
        return blocks

    production = active_lines(REPO_ROOT / "deploy" / "Caddyfile.production")
    staging = active_lines(REPO_ROOT / "deploy" / "Caddyfile")

    assert production.index("handle @legacy_post {") < production.index("handle @api {")
    assert production.index("handle @api {") < production.index("handle {")
    production_headers = directive_blocks(production, "header {")
    staging_headers = directive_blocks(staging, "header {")
    assert production_headers
    assert staging_headers
    for directive in (
        'Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"',
        'X-Content-Type-Options "nosniff"',
        'X-Frame-Options "DENY"',
        'Referrer-Policy "strict-origin-when-cross-origin"',
        'Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=(), ambient-light-sensor=(), autoplay=(), encrypted-media=(), fullscreen=(self), picture-in-picture=()"',
    ):
        assert all(directive in block for block in production_headers)
    for directive in (
        'X-Content-Type-Options "nosniff"',
        'X-Frame-Options "DENY"',
        'Referrer-Policy "no-referrer"',
        "Content-Security-Policy \"default-src 'self'; frame-ancestors 'none'; object-src 'none'\"",
    ):
        assert all(directive in block for block in staging_headers)
    assert "reverse_proxy app:8000" in staging


@pytest.mark.parametrize(
    "phase", ["Verify remote staging deploy contract", "Deploy to staging over SSH"]
)
@pytest.mark.parametrize(
    "relative,name",
    [
        ("scripts/verify_premium_alias_telemetry.py", "CHECKPOINT_VERIFIER_SHA256"),
        ("scripts/ops/notify_premium_alias_checkpoint_failure.py", "CHECKPOINT_NOTIFIER_SHA256"),
        (
            "systemd/pulseplate-premium-alias-checkpoint.service.example",
            "CHECKPOINT_SERVICE_SHA256",
        ),
        ("systemd/pulseplate-premium-alias-checkpoint.timer.example", "CHECKPOINT_TIMER_SHA256"),
        (
            "systemd/pulseplate-premium-alias-checkpoint-failure.service.example",
            "CHECKPOINT_FAILURE_SHA256",
        ),
    ],
)
@pytest.mark.parametrize(
    "fault", ["none", "absent", "symlink", "directory", "stale", "parent-link"]
)
def test_checkpoint_hash_rejection_precedes_privileged_mutation(
    tmp_path: Path, phase: str, relative: str, name: str, fault: str
) -> None:
    step = _named_step(_steps(_job(_workflow(CD_WORKFLOW), "build")), phase)
    script = step["with"]["script"]
    assert step["env"][name] == "${{ steps.staging-contract.outputs." + name.lower() + " }}"
    lines = [line for line in script.splitlines() if "./" + relative in line]
    assert len(lines) == 3 and all(script.index(line) < script.index("sudo -n ") for line in lines)
    assert "] && [" not in script
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    payload = b"admitted fixture bytes\n"
    external = tmp_path / "external"
    if fault == "parent-link":
        external.mkdir()
        (external / target.name).write_bytes(payload)
        target.parent.rmdir()
        target.parent.symlink_to(external, target_is_directory=True)
    elif fault == "symlink":
        external.write_bytes(payload)
        target.symlink_to(external)
    elif fault == "directory":
        target.mkdir()
    elif fault != "absent":
        target.write_bytes(b"stale" if fault == "stale" else payload)
    ancestor = relative.rsplit("/", 1)[0]
    prefix = f"[ ! -L ./{ancestor} ]\n[ -d ./{ancestor} ]\n"
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", "set -euo pipefail\n" + prefix + "\n".join(lines) + "\ntouch mutation"],
        cwd=tmp_path,
        env={"PATH": os.environ["PATH"], name: hashlib.sha256(payload).hexdigest()},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert (result.returncode == 0) is (fault == "none"), result.stderr
    assert (tmp_path / "mutation").exists() is (fault == "none")


def _assert_checkpoint_native_job(workflow: dict[str, object]) -> None:
    scan = _job(workflow, "prometheus-image-security")
    assert scan["timeout-minutes"] == 30
    assert not any(step.get("id") == "checkpoint-native" for step in _steps(scan))
    job = _job(workflow, "obs2a-checkpoint-native")
    assert job["needs"] == "prometheus-image-security"
    assert (
        job["if"]
        == "!cancelled() && github.event_name == 'push' && github.ref == 'refs/heads/main' && needs.prometheus-image-security.result == 'success'"
    )
    assert (
        job["timeout-minutes"] == "${{ fromJSON(vars.OBS2A_NATIVE_JOB_TIMEOUT_MINUTES || '40') }}"
    )
    assert job["permissions"] == {"contents": "read"}
    assert "environment" not in job and "secrets." not in str(job)
    build = _job(workflow, "build")
    assert build["needs"] == [
        "prometheus-image-security",
        "obs2a-checkpoint-native",
        "main-push-admission",
        "staging-postgres-native-integration",
    ]
    assert "needs.obs2a-checkpoint-native.result == 'success'" in build["if"]
    steps = _steps(job)
    checkout = _named_step(steps, "Checkout immutable OBS2A native contracts")
    assert checkout["with"]["persist-credentials"] is False
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    selection = _named_step(steps, "Select main OBS2A native controls")
    assert selection["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    text = selection["run"]
    assert 'test "$(git rev-parse HEAD)" = "$OBS2A_HEAD_SHA"' in text
    assert '1) echo "selected=true"' in text and 'exit "$diff_status"' in text
    setup = _named_step(steps, "Setup bounded checkpoint native Python")
    assert setup["with"] == {
        "python-version": "3.13.14",
        "requirements-profile": "ci-lite",
        "install-mode": "direct-proxy",
    }
    assert "secrets." not in str(setup)
    assert setup["env"]["DEVPI_CI_USER"] == "" and setup["env"]["DEVPI_CI_PASSWORD"] == ""
    native = _named_step(steps, "Native main OBS2A checkpoint lifecycle and owned-task challenge")
    assert native["if"] == setup["if"]
    assert "steps.checkpoint-native.outputs.selected == 'true'" in native["if"]
    assert "--native" in native["run"] and "/usr/bin/env -i" in native["run"]
    assert 'exit "$native_status"' in native["run"]
    assert "native-result.log" in native["run"]
    retention = _named_step(steps, "Retain selected main OBS2A native observations")
    assert retention["if"] == "always() && " + native["if"]
    assert retention["uses"] == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    assert retention["with"] == {
        "name": "obs2a-native-main-${{ github.sha }}",
        "path": "artifacts/orchestration/obs2a_pr3/native-result.log",
        "if-no-files-found": "error",
        "retention-days": 7,
    }


@pytest.mark.parametrize(
    "native_status,capture_status,expected", [(0, 0, 0), (7, 0, 7), (0, 9, 9), (7, 9, 7)]
)
def test_checkpoint_native_main_pipeline_preserves_both_statuses(
    tmp_path: Path, native_status: int, capture_status: int, expected: int
) -> None:
    bash = shutil.which("bash")
    tee = shutil.which("tee")
    assert bash is not None and tee is not None
    native = _named_step(
        _steps(_job(_workflow(CD_WORKFLOW), "obs2a-checkpoint-native")),
        "Native main OBS2A checkpoint lifecycle and owned-task challenge",
    )
    fixture = (
        "python() { :; }\n"
        "sudo() { printf 'synthetic native output\\n'; printf 'synthetic native diagnostic\\n' >&2; return \"$NATIVE_STATUS\"; }\n"
        'tee() { "$FIXTURE_TEE" "$@"; return "$CAPTURE_STATUS"; }\n'
    )
    result = subprocess.run(
        [bash, "-c", fixture + native["run"]],
        cwd=tmp_path,
        env={
            "PATH": os.defpath,
            "LANG": "C",
            "HOME": str(tmp_path),
            "NATIVE_STATUS": str(native_status),
            "CAPTURE_STATUS": str(capture_status),
            "FIXTURE_TEE": tee,
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == expected, result.stderr
    if capture_status == 0:
        observed = "synthetic native output\nsynthetic native diagnostic\n"
        assert result.stdout == observed
        assert (
            tmp_path / "artifacts/orchestration/obs2a_pr3/native-result.log"
        ).read_text() == observed


@pytest.mark.parametrize("case", ["unchanged", "changed", "invalid"])
def test_native_main_selection_uses_real_git_exit_status(tmp_path: Path, case: str) -> None:
    git = shutil.which("git")
    bash = shutil.which("bash")
    assert git is not None and bash is not None
    env = {
        "PATH": os.environ["PATH"],
        "LANG": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }

    def call(*arguments: str) -> str:
        result = subprocess.run(
            [git, "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false", *arguments],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    call("init", "--template=", "-q")
    source = tmp_path / ".github/workflows/ci.yml"
    source.parent.mkdir(parents=True)
    source.write_text("base\n")
    call("add", ".")
    call("commit", "-qm", "base")
    base = call("rev-parse", "HEAD")
    source.write_text("head\n")
    call("add", ".")
    call("commit", "-qm", "head")
    head = call("rev-parse", "HEAD")
    output = tmp_path / "output"
    env.update(
        {
            "OBS2A_BASE_SHA": (
                head if case == "unchanged" else "0" * 40 if case == "invalid" else base
            ),
            "OBS2A_HEAD_SHA": head,
            "GITHUB_OUTPUT": str(output),
        }
    )
    step = _named_step(
        _steps(_job(_workflow(CD_WORKFLOW), "obs2a-checkpoint-native")),
        "Select main OBS2A native controls",
    )
    result = subprocess.run(
        [bash, "-c", step["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if case == "invalid":
        assert result.returncode != 0 and not output.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert output.read_text() == (
            "selected=true\n" if case == "changed" else "selected=false\n"
        )


def test_checkpoint_native_main_has_separate_scan_and_build_admission() -> None:
    _assert_checkpoint_native_job(_workflow(CD_WORKFLOW))


@pytest.mark.parametrize(
    "fault",
    ["scan-edge", "scan-result", "permissions", "environment", "build-edge", "build-result"],
)
def test_checkpoint_native_dag_rejects_lost_admission(fault: str) -> None:
    workflow = deepcopy(_workflow(CD_WORKFLOW))
    native = _job(workflow, "obs2a-checkpoint-native")
    build = _job(workflow, "build")
    if fault == "scan-edge":
        native["needs"] = []
    elif fault == "scan-result":
        native["if"] = native["if"].replace(
            " && needs.prometheus-image-security.result == 'success'", ""
        )
    elif fault == "permissions":
        del native["permissions"]
    elif fault == "environment":
        native["environment"] = "production"
    elif fault == "build-edge":
        build["needs"].remove("obs2a-checkpoint-native")
    else:
        build["if"] = build["if"].replace(
            " && needs.obs2a-checkpoint-native.result == 'success'", ""
        )
    with pytest.raises((AssertionError, KeyError)):
        _assert_checkpoint_native_job(workflow)


@pytest.mark.parametrize("scan_result", ["success", "failure", "cancelled", "skipped"])
@pytest.mark.parametrize("native_result", ["success", "failure", "cancelled", "skipped"])
@pytest.mark.parametrize("cancelled", [False, True])
def test_checkpoint_native_required_results_do_not_publish_after_failure(
    scan_result: str, native_result: str, cancelled: bool
) -> None:
    workflow = _workflow(CD_WORKFLOW)
    _assert_checkpoint_native_job(workflow)
    # Evaluate the actual finite result conjuncts through the existing Bash control semantics.
    expression = _job(workflow, "build")["if"]
    native_expression = _job(workflow, "obs2a-checkpoint-native")["if"]
    replacements = {
        "!cancelled()": "1 == 0" if cancelled else "1 == 1",
        "github.event_name": "'push'",
        "github.ref": "'refs/heads/main'",
        "needs.prometheus-image-security.result": repr(scan_result),
        "needs.obs2a-checkpoint-native.result": repr(native_result),
        "needs.main-push-admission.result": "'success'",
        "needs.staging-postgres-native-integration.result": "'success'",
    }
    for key, value in replacements.items():
        expression = expression.replace(key, value)
        native_expression = native_expression.replace(key, value)
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", "[[ " + expression + " ]]"],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    admission = subprocess.run(
        [bash, "-c", "[[ " + native_expression + " ]]"],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert (admission.returncode == 0) is (not cancelled and scan_result == "success")
    assert (result.returncode == 0) is (not cancelled and scan_result == native_result == "success")


@pytest.mark.parametrize("case", ["base-only", "own", "empty", "invalid", "unrelated", "ambiguous"])
def test_checkpoint_pr_selection_uses_unique_real_merge_base(tmp_path: Path, case: str) -> None:
    git = shutil.which("git")
    bash = shutil.which("bash")
    assert git is not None and bash is not None
    env = {
        "PATH": os.defpath,
        "LANG": "C",
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }

    def call(*args: str) -> str:
        completed = subprocess.run(
            [git, "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false", *args],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        return completed.stdout.strip()

    call("init", "--template=", "-q")
    selected = tmp_path / ".github/workflows/ci.yml"
    selected.parent.mkdir(parents=True)
    selected.write_text("common\n")
    call("add", ".")
    call("commit", "-qm", "common")
    common = call("rev-parse", "HEAD")
    tree = call("rev-parse", "HEAD^{tree}")
    selected.write_text("new main\n")
    call("add", ".")
    call("commit", "-qm", "main")
    base = call("rev-parse", "HEAD")
    call("checkout", "-qb", "fixture-pr", common)
    (tmp_path / "unrelated.txt").write_text("own unrelated\n")
    if case == "own":
        selected.write_text("own selected\n")
    call("add", ".")
    call("commit", "-qm", "pr")
    head = call("rev-parse", "HEAD")
    if case == "base-only":
        assert (
            call("diff", "--name-only", base, head, "--", ".github/workflows/ci.yml")
            == ".github/workflows/ci.yml"
        )
    if case == "empty":
        base = head = common
    elif case == "invalid":
        base = "0" * 40
    elif case == "unrelated":
        base = call("commit-tree", tree, "-m", "unrelated")
    elif case == "ambiguous":
        left, right = base, head
        base = call("commit-tree", tree, "-p", left, "-p", right, "-m", "left merge")
        head = call("commit-tree", tree, "-p", right, "-p", left, "-m", "right merge")
    env.update(
        {
            "OBS2A_BASE_SHA": base,
            "OBS2A_HEAD_SHA": head,
            "NATIVE_CALLS": str(tmp_path / "native-calls"),
        }
    )
    step = _named_step(
        _steps(_job(_workflow(REPO_ROOT / ".github/workflows/ci.yml"), "test-pr")),
        "Native OBS2A checkpoint lifecycle and owned-task challenge",
    )
    fixture = 'python() { :; }\nsudo() { printf native >> "$NATIVE_CALLS"; }\n'
    result = subprocess.run(
        [bash, "-c", fixture + step["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if case in {"invalid", "unrelated", "ambiguous"}:
        assert result.returncode != 0 and not (tmp_path / "native-calls").exists()
    else:
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "native-calls").exists() is (case == "own")
