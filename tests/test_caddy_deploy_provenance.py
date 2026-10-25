"""Fail-closed contracts for the hardened Caddy and staging digest lane."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci.ci_risk_profile import build_risk_profile
from scripts.orchestration.creative_code_patch_workspace import (
    git_env_without_parent_state,
    safe_git_config_args,
)

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


@pytest.fixture(autouse=True)
def historical_alertmanager_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.ci import fetch_docker_source_artifacts as fetcher

    monkeypatch.setattr(
        fetcher, "_ALERT_ACCEPTED_CANDIDATE", json.loads(json.dumps(fetcher._ALERT_HISTORICAL_C10))
    )


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
    assert "Scan accepted AM and execute all four current controls" in workflow
    assert '--ignorefile "$TRIVY_IGNORE_FILE"' in workflow  # Prometheus stays separate.
    assert "--alertmanager-stage security-check" in workflow
    assert '"-e", "PULSEPLATE_ENVIRONMENT=staging"' in workflow
    assert ALERTMANAGER_IGNORE.read_bytes() == b"vulnerabilities: []\n"
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


PROMETHEUS_RULES_HASH_CHECK = (
    """[ "$(sha256sum ./prometheus/alias-alerts.yml | cut -d' ' -f1)" """
    '= "$PROMETHEUS_RULES_SHA256" ]'
)

GO_BUILDER = (
    "golang:1.26.10-alpine3.23@"
    "sha256:0525c952defebc693cdaf62cdf43afa32be5a7f377e99260642ea19c240c708e"
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
            "    go get golang.org/x/net@v0.60.0; \\",
            "    go get github.com/klauspost/compress@v1.18.7; \\",
            "    go mod download all; \\",
            "    go mod verify; \\",
            (
                "    test -z \"$(go list -m -f '{{if .Replace}}{{.Path}} => "
                "{{.Replace.Path}}{{end}}' all)\"; \\"
            ),
            (
                "    go list -m -f '{{if or "
                '(eq .Path "github.com/caddyserver/caddy/v2") '
                '(eq .Path "github.com/klauspost/compress") '
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
            "      'github.com/klauspost/compress v1.18.7' \\",
            "      'golang.org/x/crypto v0.57.0' \\",
            "      'golang.org/x/mod v0.41.0' \\",
            "      'golang.org/x/net v0.60.0' \\",
            "      'golang.org/x/sync v0.23.0' \\",
            "      'golang.org/x/sys v0.48.0' \\",
            "      'golang.org/x/telemetry v0.0.0-20260811182544-a038080d80e5' \\",
            "      'golang.org/x/term v0.46.0' \\",
            "      'golang.org/x/text v0.42.0' \\",
            "      'golang.org/x/tools v0.49.0' \\",
            "      'google.golang.org/grpc v1.83.2' \\",
            "      | LC_ALL=C sort > /tmp/caddy-expected-graph; \\",
            ('    test "$(wc -l < /tmp/caddy-governed-graph | ' "tr -d '[:space:]')\" = '12'; \\"),
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
                '($2 == "github.com/klauspost/compress" || $2 == "google.golang.org/grpc" || $2 == "golang.org/x/crypto" || '
                '$2 == "golang.org/x/net" || $2 == "golang.org/x/sync" || '
                '$2 == "golang.org/x/sys" || $2 == "golang.org/x/term" || '
                '$2 == "golang.org/x/text") { print $1, $2, $3 }\' '
                "/tmp/caddy-binary-metadata \\"
            ),
            "      | LC_ALL=C sort > /tmp/caddy-governed-binary; \\",
            "    printf '%s\\n' \\",
            "      'mod github.com/caddyserver/caddy/v2 v2.11.4' \\",
            "      'dep github.com/klauspost/compress v1.18.7' \\",
            "      'dep golang.org/x/crypto v0.57.0' \\",
            "      'dep golang.org/x/net v0.60.0' \\",
            "      'dep golang.org/x/sync v0.23.0' \\",
            "      'dep golang.org/x/sys v0.48.0' \\",
            "      'dep golang.org/x/term v0.46.0' \\",
            "      'dep golang.org/x/text v0.42.0' \\",
            "      'dep google.golang.org/grpc v1.83.2' \\",
            "      | LC_ALL=C sort > /tmp/caddy-expected-binary; \\",
            ('    test "$(wc -l < /tmp/caddy-governed-binary | ' "tr -d '[:space:]')\" = '9'; \\"),
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
                'Go 1.26.10 and PulsePlate frontend assets"'
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
            '      "brotli-libs>=1.2.1-r0" \\',
            '      "c-ares>=1.34.8-r0" \\',
            '      "curl>=8.20.0-r0" \\',
            '      "libcurl>=8.20.0-r0" \\',
            '      "libcrypto3>=3.5.8-r0" \\',
            '      "libssl3>=3.5.8-r0" \\',
            '      "zlib>=1.3.2-r1"; \\',
            "    mv /usr/bin/caddy.pulseplate /usr/bin/caddy; \\",
            "    setcap cap_net_bind_service=+ep /usr/bin/caddy; \\",
            "    getcap /usr/bin/caddy | grep -F 'cap_net_bind_service=ep'; \\",
            (
                '    caddy version | awk \'NR == 1 && $1 == "v2.11.4" { found=1 } '
                "END { exit found ? 0 : 1 }'; \\"
            ),
            (
                "    caddy build-info | awk -F '\\t' '$1 == \"go\" && $2 == "
                '"go1.26.10" { found=1 } END { exit found ? 0 : 1 }\'; \\'
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
    net_get = "go get golang.org/x/net@v0.60.0"
    assert text.count(net_get) == 1
    compress_get = "go get github.com/klauspost/compress@v1.18.7"
    assert text.count(compress_get) == 1
    assert text.index(crypto_get) < text.index(net_get) < text.index(compress_get)
    assert text.index(compress_get) < text.index("go mod download all")
    assert "go mod download all" in text
    assert "go mod verify" in text
    for exact_graph_identity in (
        "github.com/caddyserver/caddy/v2 v2.11.4",
        "github.com/klauspost/compress v1.18.7",
        "google.golang.org/grpc v1.83.2",
        "golang.org/x/crypto v0.57.0",
        "golang.org/x/mod v0.41.0",
        "golang.org/x/net v0.60.0",
        "golang.org/x/sync v0.23.0",
        "golang.org/x/sys v0.48.0",
        "golang.org/x/telemetry v0.0.0-20260811182544-a038080d80e5",
        "golang.org/x/term v0.46.0",
        "golang.org/x/text v0.42.0",
        "golang.org/x/tools v0.49.0",
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
        "dep github.com/klauspost/compress v1.18.7",
        "dep google.golang.org/grpc v1.83.2",
        "dep golang.org/x/crypto v0.57.0",
        "dep golang.org/x/net v0.60.0",
        "dep golang.org/x/sync v0.23.0",
        "dep golang.org/x/sys v0.48.0",
        "dep golang.org/x/term v0.46.0",
        "dep golang.org/x/text v0.42.0",
    ):
        assert f"'{exact_binary_identity}'" in text
    assert '"brotli-libs>=1.2.1-r0"' in text
    assert '"c-ares>=1.34.8-r0"' in text
    assert '"curl>=8.20.0-r0"' in text
    assert '"libcurl>=8.20.0-r0"' in text
    assert '"zlib>=1.3.2-r1"' in text
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
        "net-omitted",
        "net-duplicate",
        "net-floating",
    ),
)
def test_caddy_builder_stage_snapshot_rejects_dependency_contract_drift(case: str) -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    crypto_action = "    go get golang.org/x/crypto@v0.55.0; \\\n"
    _assert_caddy_builder_stage_contract(source)

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
            "      'dep golang.org/x/crypto v0.57.0' \\\n",
            "      'dep golang.org/x/crypto v0.54.0' \\\n",
            1,
        )
    elif case in ("net-omitted", "net-duplicate", "net-floating"):
        net_action = "    go get golang.org/x/net@v0.60.0; \\\n"
        replacement = {
            "net-omitted": "",
            "net-duplicate": net_action * 2,
            "net-floating": net_action.replace("v0.60.0", "latest"),
        }[case]
        candidate = source.replace(net_action, replacement, 1)
    else:
        assert case == "binary-fixed-graph-stale"
        candidate = source.replace(
            "      'golang.org/x/crypto v0.57.0' \\\n",
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
        "lower-zlib-floor",
    ),
)
def test_caddy_openssl_final_stage_snapshot_rejects_representative_byte_drift(
    case: str,
) -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    _assert_caddy_openssl_runtime_floor_contract(source)
    if case == "lower-floor":
        candidate = source.replace("3.5.8-r0", "3.5.7-r0")
    elif case == "lower-zlib-floor":
        candidate = source.replace("zlib>=1.3.2-r1", "zlib>=1.3.2-r0")
    elif case == "partial-floor":
        candidate = source.replace(
            '      "libssl3>=3.5.8-r0" \\\n',
            "",
            1,
        )
    elif case == "substitute-floor":
        candidate = source.replace(
            '      "libcrypto3>=3.5.8-r0" \\\n' '      "libssl3>=3.5.8-r0" \\\n',
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
        "PROMETHEUS_IMAGE_MANIFEST_SHA256,PROMETHEUS_CONTRACT_HELPER_SHA256,ALERTMANAGER_CONTRACT_HELPER_SHA256,"
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
        "PROMETHEUS_IMAGE_MANIFEST_SHA256,PROMETHEUS_CONTRACT_HELPER_SHA256,ALERTMANAGER_CONTRACT_HELPER_SHA256,"
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
        "PROMETHEUS_IMAGE_MANIFEST_SHA256,PROMETHEUS_CONTRACT_HELPER_SHA256,ALERTMANAGER_CONTRACT_HELPER_SHA256,ALERTMANAGER_CONFIG_SHA256,"
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
    assert 'STAGING_DEPLOY_CONTRACT_VERSION="6"' in script
    for filename in (
        "deploy.sh",
        "docker-compose.staging.yaml",
        "prometheus/prometheus.yml",
        "prometheus/alias-alerts.yml",
        "prometheus/image-manifest.json",
        "scripts/ci/prometheus_source_image.py",
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
        "PROMETHEUS_IMAGE_MANIFEST_SHA256,PROMETHEUS_CONTRACT_HELPER_SHA256,ALERTMANAGER_CONTRACT_HELPER_SHA256,ALERTMANAGER_CONFIG_SHA256,"
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
    assert script.index('STAGING_DEPLOY_CONTRACT_VERSION="6"') < script.index(deploy_call)
    for filename, expected_hash in (
        ("deploy.sh", "DEPLOY_SCRIPT_SHA256"),
        ("docker-compose.staging.yaml", "STAGING_COMPOSE_SHA256"),
        ("prometheus/prometheus.yml", "PROMETHEUS_CONFIG_SHA256"),
        ("prometheus/alias-alerts.yml", "PROMETHEUS_RULES_SHA256"),
        ("prometheus/image-manifest.json", "PROMETHEUS_IMAGE_MANIFEST_SHA256"),
        ("scripts/ci/prometheus_source_image.py", "PROMETHEUS_CONTRACT_HELPER_SHA256"),
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
    assert 'STAGING_DEPLOY_CONTRACT_VERSION="6"' in text
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
    assert 'CADDY_GO_VERSION" != "go1.26.10"' in text
    assert "*v2.11.4*" not in text
    assert "*go1.26.10*" not in text


@pytest.mark.parametrize(
    ("caddy_version", "build_info", "expected_error"),
    (
        ("v2.11.40 h1:test", "go\tgo1.26.10\n", "Expected Caddy v2.11.4"),
        ("v2.11.4 h1:test", "go\tgo1.26.100\n", "Expected Caddy built with Go 1.26.10"),
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
        go_version="go1.26.10",
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
        go_version="go1.26.10",
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
        go_version="go1.26.10",
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
        go_version="go1.26.10",
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
        go_version="go1.26.10",
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
        go_version="go1.26.10",
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
    from tests.test_deploy_contract_scripts import (
        _synthetic_prometheus_manifest_text,
        _write_prometheus_helper,
    )

    _write_prometheus_helper(deploy_dir)
    (deploy_dir / "prometheus").mkdir()
    (deploy_dir / "prometheus/image-manifest.json").write_text(
        _synthetic_prometheus_manifest_text(), encoding="utf-8"
    )
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
    scan = _job(workflow, "prometheus-image-security-pr")
    assert (
        scan["timeout-minutes"]
        == "${{ fromJSON(vars.ALERTMANAGER_CD_PR_JOB_TIMEOUT_MINUTES || '170') }}"
    )
    assert not any(step.get("id") == "checkpoint-native" for step in _steps(scan))
    job = _job(workflow, "obs2a-checkpoint-native")
    assert job["needs"] == "prometheus-image-security", "checkpoint_native_scan_edge"
    assert (
        job["if"]
        == "!cancelled() && github.event_name == 'push' && github.ref == 'refs/heads/main' && needs.prometheus-image-security.result == 'success'"
    ), "checkpoint_native_scan_result"
    assert (
        job["timeout-minutes"]
        == "${{ fromJSON(vars.ALERTMANAGER_NATIVE_JOB_TIMEOUT_MINUTES || '110') }}"
    )
    assert job.get("permissions") == {
        "contents": "read",
        "actions": "read",
        "packages": "read",
    }, "checkpoint_native_reader_permissions"
    assert job.get("environment") == "staging", "checkpoint_native_reader_environment"
    assert job["env"]["PROMETHEUS_CONSUME_SECONDS"] == "900"
    assert job["env"]["PROMETHEUS_CLEANUP_SECONDS"] == "120"
    assert (
        job["env"]["ALERTMANAGER_GENERIC_NATIVE_MINUTES"]
        == "${{ vars.OBS2A_NATIVE_JOB_TIMEOUT_MINUTES || '40' }}"
    )
    build = _job(workflow, "build")
    assert build["needs"] == [
        "prometheus-image-security",
        "obs2a-checkpoint-native",
        "main-push-admission",
        "staging-postgres-native-integration",
    ], "checkpoint_native_build_edges"
    assert (
        "needs.obs2a-checkpoint-native.result == 'success'" in build["if"]
    ), "checkpoint_native_build_result"
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
    setup = _named_step(steps, "Select AM Python without dependency or SDK installation")
    assert setup["with"] == {"python-version": "3.13.14", "skip-base-install": "true"}
    assert "secrets." not in str(setup)
    assert setup["env"]["DEVPI_CI_USER"] == "" and setup["env"]["DEVPI_CI_PASSWORD"] == ""
    native = _named_step(steps, "Native main OBS2A checkpoint lifecycle and owned-task challenge")
    assert native["if"] == setup["if"]
    assert "steps.checkpoint-native.outputs.selected == 'true'" in native["if"]
    consume = _named_step(steps, "Consume exact Prometheus before main native fixtures")
    assert steps.index(consume) < steps.index(native)
    assert consume["timeout-minutes"] == 18
    assert native["timeout-minutes"] == "${{ fromJSON(env.ALERTMANAGER_GENERIC_NATIVE_MINUTES) }}"
    assert "--operation consume" in consume["run"] and "--operation consume" not in native["run"]
    assert native["env"] == {
        "AM_HOST_PYTHON": "${{ steps.am-python.outputs.python }}",
        "AM_IMAGE_ID": "${{ steps.alertmanager-image.outputs.image_id }}",
        "AM_CONFIG_SHA256": "${{ steps.alertmanager-image.outputs.config_sha256 }}",
    }
    child = native["run"].split("sudo /usr/bin/env -i", 1)[1].split("} 2>&1", 1)[0]
    assert (
        "GH_TOKEN" not in child and "GITHUB_TOKEN" not in child and "GHCR_READ_TOKEN" not in child
    )
    assert "--native" in native["run"] and "/usr/bin/env -i" in native["run"]
    assert 'exit "$native_status"' in native["run"]
    assert "native-result.log" in native["run"]
    retention = _named_step(steps, "Retain selected main OBS2A native observations")
    assert retention["if"] == "always() && " + native["if"]
    assert retention["uses"] == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    assert retention["with"] == {
        "name": "obs2a-native-main-${{ github.sha }}",
        "path": "artifacts/orchestration/obs2a_pr3/native-result.log\n"
        "${{ runner.temp }}/prometheus-obs2a-consumer-${{ github.run_id }}-${{ github.run_attempt }}/evidence/\n"
        "${{ runner.temp }}/alertmanager-consumer-${{ github.run_id }}-${{ github.run_attempt }}/consumer-observation.json\n"
        "${{ runner.temp }}/alertmanager-consumer-${{ github.run_id }}-${{ github.run_attempt }}/github-read-evidence/\n"
        "${{ runner.temp }}/alertmanager-consumer-${{ github.run_id }}-${{ github.run_attempt }}/preparation/evidence/\n",
        "if-no-files-found": "error",
        "retention-days": 7,
    }


@pytest.mark.parametrize(
    "consume_status,native_status,capture_status,expected",
    [(0, 0, 0, 0), (0, 7, 0, 7), (0, 0, 9, 9), (0, 7, 9, 7), (13, 0, 0, 13)],
)
def test_checkpoint_native_main_pipeline_preserves_both_statuses(
    tmp_path: Path, consume_status: int, native_status: int, capture_status: int, expected: int
) -> None:
    bash = shutil.which("bash")
    tee = shutil.which("tee")
    assert bash is not None and tee is not None
    native = _named_step(
        _steps(_job(_workflow(CD_WORKFLOW), "obs2a-checkpoint-native")),
        "Native main OBS2A checkpoint lifecycle and owned-task challenge",
    )
    fixture = (
        'python() { [ "$1" = "-m" ] && [ "$2" = "scripts.ci.prometheus_source_image" ] '
        '&& [ "$3" = "--operation" ] && [ "$4" = "consume" ] || return 98; '
        'printf "%s\\n" "$*" > consumer-argv; return "$CONSUME_STATUS"; }\n'
        "sudo() { printf executed > native-called; printf 'synthetic native output\\n'; printf 'synthetic native diagnostic\\n' >&2; return \"$NATIVE_STATUS\"; }\n"
        'tee() { "$FIXTURE_TEE" "$@"; return "$CAPTURE_STATUS"; }\n'
    )
    result = subprocess.run(
        [
            bash,
            "-c",
            fixture
            + _named_step(
                _steps(_job(_workflow(CD_WORKFLOW), "obs2a-checkpoint-native")),
                "Consume exact Prometheus before main native fixtures",
            )["run"]
            + "\n"
            + native["run"],
        ],
        cwd=tmp_path,
        env={
            "PATH": os.defpath,
            "LANG": "C",
            "HOME": str(tmp_path),
            "RUNNER_TEMP": str(tmp_path / "runner-temp"),
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
            "PROMETHEUS_CONSUME_SECONDS": "900",
            "PROMETHEUS_CLEANUP_SECONDS": "120",
            "AM_HOST_PYTHON": "python",
            "AM_IMAGE_ID": "sha256:" + "1" * 64,
            "AM_CONFIG_SHA256": "2" * 64,
            "CONSUME_STATUS": str(consume_status),
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
    assert (tmp_path / "consumer-argv").read_text() == (
        "-m scripts.ci.prometheus_source_image --operation consume --work-dir "
        + str(tmp_path / "runner-temp/prometheus-obs2a-consumer-123-1")
        + " --timeout-seconds 900 --cleanup-seconds 120\n"
    )
    assert (tmp_path / "native-called").exists() is (consume_status == 0)
    if consume_status:
        assert not (tmp_path / "native-called").exists()
        assert not (tmp_path / "artifacts/orchestration/obs2a_pr3/native-result.log").exists()
        assert result.stdout == result.stderr == ""
    elif capture_status == 0:
        assert (tmp_path / "native-called").read_text() == "executed"
        observed = "synthetic native output\nsynthetic native diagnostic\n"
        assert result.stdout == observed
        assert (
            tmp_path / "artifacts/orchestration/obs2a_pr3/native-result.log"
        ).read_text() == observed


@pytest.mark.parametrize(
    ("selected_path", "expected_selected"),
    [
        (".github/workflows/ci.yml", True),
        ("deploy/prometheus/image-manifest.json", True),
        ("scripts/ci/fetch_docker_source_artifacts.py", True),
        ("deploy/alertmanager/alertmanager.yml", True),
        ("deploy/alertmanager/trivy-ignore.yaml", True),
        ("deploy/docker-compose.staging.yaml", True),
        ("deploy/docker-compose.production.yaml", True),
        ("deploy/docker-compose.production.selfhosted.yaml", True),
        ("deploy/prometheus/image-manifest.json.bak", False),
    ],
)
@pytest.mark.parametrize("case", ["unchanged", "changed", "invalid"])
def test_native_main_selection_uses_real_git_exit_status(
    tmp_path: Path, case: str, selected_path: str, expected_selected: bool
) -> None:
    git = shutil.which("git")
    bash = shutil.which("bash")
    assert git is not None and bash is not None
    env = {
        **git_env_without_parent_state(),
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
            [git, *safe_git_config_args(), "-c", "commit.gpgsign=false", *arguments],
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
    source = tmp_path / selected_path
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
            "selected=true\n" if case == "changed" and expected_selected else "selected=false\n"
        )


def test_checkpoint_native_main_has_separate_scan_and_build_admission() -> None:
    _assert_checkpoint_native_job(_workflow(CD_WORKFLOW))


@pytest.mark.parametrize(
    "fault",
    ["scan-edge", "scan-result", "permissions", "environment", "build-edge", "build-result"],
)
def test_checkpoint_native_dag_rejects_lost_admission(fault: str) -> None:
    workflow = deepcopy(_workflow(CD_WORKFLOW))
    _assert_checkpoint_native_job(workflow)
    native = _job(workflow, "obs2a-checkpoint-native")
    build = _job(workflow, "build")
    expected_diagnostic = {
        "scan-edge": "checkpoint_native_scan_edge",
        "scan-result": "checkpoint_native_scan_result",
        "permissions": "checkpoint_native_reader_permissions",
        "environment": "checkpoint_native_reader_environment",
        "build-edge": "checkpoint_native_build_edges",
        "build-result": "checkpoint_native_build_result",
    }[fault]
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
    with pytest.raises(AssertionError, match=rf"^{expected_diagnostic}(?:\n|$)"):
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


def _assert_checkpoint_pr_selection_uses_real_git(
    tmp_path: Path,
    case: str,
    selected_path: str = ".github/workflows/ci.yml",
    *,
    expected_selected: bool = True,
    consume_status: int = 0,
    native_status: int = 0,
    capture_status: int = 0,
    capture_log: bool = True,
) -> None:
    git = shutil.which("git")
    bash = shutil.which("bash")
    tee = shutil.which("tee")
    cat = shutil.which("cat")
    assert git is not None and bash is not None and tee is not None and cat is not None
    env = {
        **git_env_without_parent_state(),
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
            [git, *safe_git_config_args(), "-c", "commit.gpgsign=false", *args],
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
    selected = tmp_path / selected_path
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_text("common\n")
    manifest = tmp_path / "deploy/prometheus/image-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}\n")
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
        assert call("diff", "--name-only", base, head, "--", selected_path) == selected_path
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
    call("checkout", "--detach", "-q", head)
    env.update(
        {
            "OBS2A_BASE_SHA": base,
            "OBS2A_HEAD_SHA": head,
            "RUNNER_TEMP": str(tmp_path / "runner-temp"),
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
            "PROMETHEUS_CONSUME_SECONDS": "900",
            "PROMETHEUS_CLEANUP_SECONDS": "120",
            "AM_IMAGE_ID": "sha256:" + "a" * 64,
            "AM_CONFIG_SHA256": "b" * 64,
            "CONSUME_STATUS": str(consume_status),
            "NATIVE_CALLS": str(tmp_path / "native-calls"),
            "GITHUB_OUTPUT": str(tmp_path / "github-output"),
            "NATIVE_STATUS": str(native_status),
            "CAPTURE_STATUS": str(capture_status),
            "CAPTURE_LOG": "1" if capture_log else "0",
            "FIXTURE_TEE": tee,
            "FIXTURE_CAT": cat,
            "FIXTURE_GIT": git,
        }
    )
    step = _named_step(
        _steps(_job(_workflow(REPO_ROOT / ".github/workflows/ci.yml"), "lint")),
        "Select native OBS2A material before PR startup",
    )
    fixture = (
        'python() { [ "$1" = "-m" ] && [ "$2" = "scripts.ci.prometheus_source_image" ] '
        '&& [ "$3" = "--operation" ] && [ "$4" = "consume" ] || return 98; '
        'printf "%s\\n" "$*" > consumer-argv; return "$CONSUME_STATUS"; }\n'
        'sudo() { printf native >> "$NATIVE_CALLS"; printf "native output\\n"; '
        'printf "native diagnostic\\n" >&2; return "$NATIVE_STATUS"; }\n'
        'tee() { if [ "$CAPTURE_LOG" = 1 ]; then "$FIXTURE_TEE" "$@"; '
        'else "$FIXTURE_CAT" >/dev/null; fi; return "$CAPTURE_STATUS"; }\n'
    )
    if case == "discovery-error":
        fixture += 'git() { for argument in "$@"; do if [ "$argument" = diff ]; then return 2; fi; done; "$FIXTURE_GIT" "$@"; }\n'
    result = subprocess.run(
        [bash, "-c", fixture + step["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    output = tmp_path / "github-output"
    log = tmp_path / "artifacts/orchestration/obs2a_pr3/native-result.log"
    if case in {"invalid", "unrelated", "ambiguous", "discovery-error"}:
        assert result.returncode != 0 and not (tmp_path / "native-calls").exists()
        assert not output.exists() and not log.exists()
    else:
        selected = case == "own" and expected_selected
        assert result.returncode == 0, result.stderr
        # This step owns only native surface selection; the fixed-control step
        # separately invokes the canonical four-blob classifier before credentials.
        assert output.read_text() == ("selected=true\n" if selected else "selected=false\n")
        assert not (tmp_path / "native-calls").exists()
        if selected:
            # The synthetic consumer exit models the separate step result. The
            # actual native program runs only after that admitted step succeeds.
            if consume_status:
                assert not log.exists()
                return
            native = _named_step(
                _steps(_job(_workflow(REPO_ROOT / ".github/workflows/ci.yml"), "lint")),
                "Native OBS2A checkpoint lifecycle and owned-task challenge",
            )
            completed = subprocess.run(
                [bash, "-c", fixture + native["run"]],
                cwd=tmp_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert completed.returncode == (native_status or capture_status), completed.stderr
            assert (tmp_path / "native-calls").exists()
            assert log.exists() is capture_log
            if capture_log:
                assert log.read_text() == "native output\nnative diagnostic\n"


@pytest.mark.parametrize(
    "case", ["base-only", "own", "empty", "invalid", "unrelated", "ambiguous", "discovery-error"]
)
def test_checkpoint_pr_selection_uses_unique_real_merge_base(tmp_path: Path, case: str) -> None:
    _assert_checkpoint_pr_selection_uses_real_git(tmp_path, case)


@pytest.mark.parametrize("case", ["own", "base-only"])
@pytest.mark.parametrize(
    ("selected_path", "expected_selected"),
    [
        ("deploy/prometheus/image-manifest.json", True),
        ("scripts/ci/fetch_docker_source_artifacts.py", True),
        ("deploy/alertmanager/alertmanager.yml", True),
        ("deploy/alertmanager/trivy-ignore.yaml", True),
        ("deploy/docker-compose.staging.yaml", True),
        ("deploy/docker-compose.production.yaml", True),
        ("deploy/docker-compose.production.selfhosted.yaml", True),
        ("deploy/prometheus/image-manifest.json.bak", False),
    ],
)
def test_checkpoint_pr_selects_only_its_manifest_change(
    tmp_path: Path, case: str, selected_path: str, expected_selected: bool
) -> None:
    _assert_checkpoint_pr_selection_uses_real_git(
        tmp_path, case, selected_path, expected_selected=expected_selected
    )


@pytest.mark.parametrize(
    "selected_path",
    [
        "scripts/ops/notify_premium_alias_checkpoint_failure.py",
        "deploy/systemd/pulseplate-premium-alias-checkpoint.service.example",
        "deploy/systemd/pulseplate-premium-alias-checkpoint.timer.example",
        "deploy/systemd/pulseplate-premium-alias-checkpoint-failure.service.example",
    ],
)
def test_checkpoint_pr_native_is_independent_of_backend_risk_admission(
    tmp_path: Path, selected_path: str
) -> None:
    # The actual classifier rejects this outer route while the real inner Git selector selects it.
    assert build_risk_profile([selected_path]).run_backend_blocking is False
    _assert_checkpoint_pr_selection_uses_real_git(tmp_path, "own", selected_path)
    workflow = _workflow(REPO_ROOT / ".github/workflows/ci.yml")
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    holders = [
        name
        for name in jobs
        if any(
            step.get("name") == "Native OBS2A checkpoint lifecycle and owned-task challenge"
            for step in _steps(_job(workflow, name))
        )
    ]
    assert holders == ["lint"], holders
    _assert_checkpoint_pr_native_job(workflow)


def _assert_checkpoint_pr_native_job(workflow: dict[str, object]) -> None:
    lint = _job(workflow, "lint")
    assert lint["needs"] == ["private_python_proxy_health"]
    assert lint["permissions"] == {"contents": "read", "actions": "read", "packages": "read"}
    assert lint["env"] == {
        "PROMETHEUS_CONSUME_SECONDS": "900",
        "PROMETHEUS_CLEANUP_SECONDS": "120",
        "ALERTMANAGER_JOB_TIMEOUT_MINUTES": "${{ fromJSON(vars.CI_LINT_TIMEOUT_MINUTES || '190') }}",
        "ALERTMANAGER_CALLER_KIND": "ci-lint",
        "ALERTMANAGER_GENERIC_NATIVE_MINUTES": "${{ vars.OBS2A_NATIVE_JOB_TIMEOUT_MINUTES || '40' }}",
        "ALERTMANAGER_LINT_CHECK_MINUTES": "${{ vars.CI_LINT_CHECKS_TIMEOUT_MINUTES || '60' }}",
    }
    assert "environment" not in lint
    assert lint["if"] == "${{ !cancelled() }}"
    assert lint["timeout-minutes"] == "${{ fromJSON(vars.CI_LINT_TIMEOUT_MINUTES || '190') }}"
    steps = _steps(lint)
    prerequisite = _named_step(steps, "Enforce prerequisite results")
    assert (
        'if [[ "$PRIVATE_PYTHON_PROXY_HEALTH_RESULT" != "success" ]]; then' in prerequisite["run"]
    )
    assert "exit 1" in prerequisite["run"]
    assert prerequisite["env"] == {
        "PRIVATE_PYTHON_PROXY_HEALTH_RESULT": "${{ needs.private_python_proxy_health.result }}"
    }
    checkout = _named_step(steps, "Checkout")
    assert checkout["with"] == {
        "fetch-depth": 0,
        "persist-credentials": False,
        "ref": "${{ github.event.pull_request.head.sha || github.sha }}",
    }
    setup = _named_step(steps, "Setup Python environment")
    assert setup["with"] == {
        "python-version": "${{ env.PYTHON_VERSION }}",
        "requirements-profile": "ci-lite",
        "install-mode": "direct-proxy",
    }
    assert setup["env"] == {
        "DEVPI_CI_USER": "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && secrets.DEVPI_CI_USER || '' }}",
        "DEVPI_CI_PASSWORD": "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && secrets.DEVPI_CI_PASSWORD || '' }}",
    }
    precommit = _named_step(steps, "Pre-commit (lint/format/security quick checks)")
    assert precommit["timeout-minutes"] == "${{ fromJSON(env.ALERTMANAGER_LINT_CHECK_MINUTES) }}"
    native = _named_step(steps, "Native OBS2A checkpoint lifecycle and owned-task challenge")
    assert native["id"] == "checkpoint-native"
    assert native["if"] == (
        "github.event_name == 'pull_request' && steps.checkpoint-selection.outputs.selected == 'true'"
    )
    # The actual existing CD owner supplies native budget parity; this PR does not redefine it.
    assert native["timeout-minutes"] == "${{ fromJSON(env.ALERTMANAGER_GENERIC_NATIVE_MINUTES) }}"
    assert native["env"] == {
        "AM_IMAGE_ID": "${{ steps.alertmanager-image.outputs.image_id }}",
        "AM_CONFIG_SHA256": "${{ steps.alertmanager-image.outputs.config_sha256 }}",
        "PROMETHEUS_RUNTIME_REF": "${{ steps.checkpoint-image.outputs.runtime_ref }}",
    }
    assert "--operation consume" not in native["run"]
    assert all(key not in native["env"] for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN"))
    consumer = _named_step(steps, "Consume exact Prometheus subject before PR startup")
    control = _named_step(steps, "Checkout fixed trusted Prometheus control")
    cleanup = _named_step(steps, "Remove fixed trusted Prometheus control checkout")
    selection = _named_step(steps, "Select native OBS2A material before PR startup")
    classifier = _named_step(steps, "Classify the fixed regular Prometheus source blobs")
    assert classifier["id"] == "checkpoint-route"
    assert classifier["if"] == control["if"] == consumer["if"] == native["if"]
    assert set(classifier["env"]) == {"PROMETHEUS_EVENT_HEAD", "PROMETHEUS_EVENT_BASE"}
    assert "secrets." not in str(classifier)
    assert classifier["run"].count('trusted["classify_source_change"](previous, current)') == 1
    assert "mode=" not in selection["run"]
    # pragma: allowlist nextline secret - public trusted control commit
    assert control["with"]["ref"] == "c023efbaf3e188b5da3bb5cedbf6363a182ce4d3"
    assert control["with"]["persist-credentials"] is False
    assert "python3 -I -S" in consumer["run"] and "runpy.run_path(str(helper))" in consumer["run"]
    assert consumer["env"]["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert (
        consumer["env"]["GHCR_READ_TOKEN"]
        == "${{ steps.checkpoint-route.outputs.mode == 'unchanged_pr_published' && secrets.GITHUB_TOKEN || '' }}"
    )
    assert (
        steps.index(checkout)
        < steps.index(selection)
        < steps.index(control)
        < steps.index(classifier)
        < steps.index(consumer)
        < steps.index(cleanup)
        < steps.index(setup)
    )
    retention = _named_step(steps, "Retain selected PR OBS2A native observations")
    assert retention["if"] == (
        "always() && github.event_name == 'pull_request' "
        "&& (steps.checkpoint-selection.outputs.selected == 'true' || steps.checkpoint-selection.outcome == 'failure')"
    )
    assert retention["uses"] == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    assert retention["with"] == {
        "name": "obs2a-native-pr-${{ github.event.pull_request.number }}-${{ github.run_attempt }}",
        "path": "artifacts/orchestration/obs2a_pr3/selection.log\n"
        "artifacts/orchestration/obs2a_pr3/native-result.log\n"
        "${{ runner.temp }}/prometheus-obs2a-consumer-${{ github.run_id }}-${{ github.run_attempt }}/evidence/\n"
        "${{ runner.temp }}/alertmanager-consumer-${{ github.run_id }}-${{ github.run_attempt }}/consumer-observation.json\n"
        "${{ runner.temp }}/alertmanager-consumer-${{ github.run_id }}-${{ github.run_attempt }}/github-read-evidence/\n"
        "${{ runner.temp }}/alertmanager-consumer-${{ github.run_id }}-${{ github.run_attempt }}/preparation/evidence/\n",
        "if-no-files-found": "error",
        "retention-days": 7,
    }
    assert steps.index(prerequisite) < steps.index(checkout) < steps.index(setup)
    assert (
        steps.index(setup) < steps.index(precommit) < steps.index(native) < steps.index(retention)
    )
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    holders = [
        name
        for name in jobs
        if any(step.get("name") == native["name"] for step in _steps(_job(workflow, name)))
    ]
    assert holders == ["lint"]
    junit = _named_step(_steps(_job(workflow, "test-pr")), "Upload JUnit test report")
    assert "native-result.log" not in junit["with"]["path"]


@pytest.mark.parametrize(
    "selected_path,expected_selected",
    [
        ("deploy/systemd/pulseplate-premium-alias-checkpoint.service.example", True),
        ("deploy/systemd/pulseplate-premium-alias-checkpoint.timer.example", True),
        ("deploy/systemd/pulseplate-premium-alias-checkpoint-failure.service.example", True),
        ("scripts/ops/notify_premium_alias_checkpoint_failure.py", True),
        ("scripts/verify_premium_alias_telemetry.py", True),
        ("scripts/deploy.sh", True),
        ("scripts/deploy_production.sh", True),
        ("tests/test_notify_premium_alias_checkpoint_failure.py", True),
        (".github/workflows/ci.yml", True),
        (".github/workflows/cd.yml", True),
        ("scripts/ci/prometheus_source_image.py", True),
        (".github/workflows/build.yml", True),
        ("deploy/prometheus/Containerfile", True),
        ("scripts/ci/prometheus_source_image.py.bak", False),
        ("deploy/prometheus/Containerfile.bak", False),
        ("docs/unrelated.md", False),
        ("unrelated.txt", False),
    ],
)
def test_checkpoint_pr_native_surface_membership_uses_real_selector(
    tmp_path: Path, selected_path: str, expected_selected: bool
) -> None:
    _assert_checkpoint_pr_native_job(_workflow(REPO_ROOT / ".github/workflows/ci.yml"))
    _assert_checkpoint_pr_selection_uses_real_git(
        tmp_path, "own", selected_path, expected_selected=expected_selected
    )


@pytest.mark.parametrize(
    "consume_status,native_status,capture_status",
    [(0, 0, 0), (0, 7, 0), (0, 0, 9), (0, 7, 9), (13, 0, 0)],
)
def test_checkpoint_pr_native_preserves_status_and_actual_raw_log(
    tmp_path: Path, consume_status: int, native_status: int, capture_status: int
) -> None:
    _assert_checkpoint_pr_native_job(_workflow(REPO_ROOT / ".github/workflows/ci.yml"))
    _assert_checkpoint_pr_selection_uses_real_git(
        tmp_path,
        "own",
        consume_status=consume_status,
        native_status=native_status,
        capture_status=capture_status,
    )


def test_checkpoint_pr_missing_capture_is_failure_with_selected_invocation(tmp_path: Path) -> None:
    _assert_checkpoint_pr_native_job(_workflow(REPO_ROOT / ".github/workflows/ci.yml"))
    _assert_checkpoint_pr_selection_uses_real_git(
        tmp_path, "own", capture_status=9, capture_log=False
    )


@pytest.mark.parametrize("selected", ["true", "false", ""])
@pytest.mark.parametrize("event", ["pull_request", "push", "workflow_dispatch"])
@pytest.mark.parametrize("cancelled", [False, True])
def test_checkpoint_pr_native_event_and_outer_job_admission(
    event: str, cancelled: bool, selected: str
) -> None:
    workflow = _workflow(REPO_ROOT / ".github/workflows/ci.yml")
    _assert_checkpoint_pr_native_job(workflow)
    lint = _job(workflow, "lint")
    native = _named_step(_steps(lint), "Native OBS2A checkpoint lifecycle and owned-task challenge")
    outer = lint["if"].removeprefix("${{").removesuffix("}}").strip()
    outer = outer.replace("!cancelled()", "1 == 0" if cancelled else "1 == 1")
    inner = native["if"].replace("github.event_name", repr(event))
    inner = inner.replace("steps.checkpoint-selection.outputs.selected", repr(selected))
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", "[[ " + outer + " ]] && [[ " + inner + " ]]"],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert (result.returncode == 0) is (
        not cancelled and event == "pull_request" and selected == "true"
    )


@pytest.mark.parametrize("proxy_result", ["success", "failure", "cancelled", "skipped"])
def test_checkpoint_pr_native_proxy_prerequisite_fails_closed(proxy_result: str) -> None:
    workflow = _workflow(REPO_ROOT / ".github/workflows/ci.yml")
    _assert_checkpoint_pr_native_job(workflow)
    prerequisite = _named_step(_steps(_job(workflow, "lint")), "Enforce prerequisite results")
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", prerequisite["run"]],
        env={"PATH": os.defpath, "PRIVATE_PYTHON_PROXY_HEALTH_RESULT": proxy_result},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert (result.returncode == 0) is (proxy_result == "success")


@pytest.mark.parametrize(
    "fault",
    [
        "outer-risk",
        "proxy-edge",
        "proxy-check",
        "shallow",
        "persisted-credentials",
        "profile",
        "native-event",
        "duplicate",
        "log-cross-runner",
        "retention-status",
        "missing-log",
        "job-budget",
        "precommit-budget",
        "native-budget",
    ],
)
def test_checkpoint_pr_native_contract_rejects_lost_admission(fault: str) -> None:
    workflow = deepcopy(_workflow(REPO_ROOT / ".github/workflows/ci.yml"))
    _assert_checkpoint_pr_native_job(workflow)
    lint = _job(workflow, "lint")
    steps = _steps(lint)
    native = _named_step(steps, "Native OBS2A checkpoint lifecycle and owned-task challenge")
    retention = _named_step(steps, "Retain selected PR OBS2A native observations")
    if fault == "outer-risk":
        lint["if"] = _job(workflow, "test-pr")["if"]
    elif fault == "proxy-edge":
        lint["needs"] = []
    elif fault == "proxy-check":
        _named_step(steps, "Enforce prerequisite results")["run"] = "exit 0\n"
    elif fault in {"shallow", "persisted-credentials"}:
        options = _named_step(steps, "Checkout")["with"]
        assert isinstance(options, dict)
        options["fetch-depth" if fault == "shallow" else "persist-credentials"] = (
            1 if fault == "shallow" else True
        )
    elif fault == "profile":
        options = _named_step(steps, "Setup Python environment")["with"]
        assert isinstance(options, dict)
        options["requirements-profile"] = "ci-test"
    elif fault == "native-event":
        del native["if"]
    elif fault == "duplicate":
        duplicate_steps = _job(workflow, "test-pr")["steps"]
        assert isinstance(duplicate_steps, list)
        duplicate_steps.append(deepcopy(native))
    elif fault == "log-cross-runner":
        options = _named_step(_steps(_job(workflow, "test-pr")), "Upload JUnit test report")["with"]
        assert isinstance(options, dict)
        options["path"] += "artifacts/orchestration/obs2a_pr3/native-result.log\n"
    elif fault == "retention-status":
        retention["if"] = native["if"]
    elif fault == "missing-log":
        options = retention["with"]
        assert isinstance(options, dict)
        options["if-no-files-found"] = "ignore"
    elif fault == "job-budget":
        lint["timeout-minutes"] = 40
    elif fault == "precommit-budget":
        del _named_step(steps, "Pre-commit (lint/format/security quick checks)")["timeout-minutes"]
    else:
        native["timeout-minutes"] = "${{ fromJSON(vars.OBS2A_NATIVE_JOB_TIMEOUT_MINUTES || '41') }}"
    with pytest.raises((AssertionError, KeyError)):
        _assert_checkpoint_pr_native_job(workflow)


def test_caddy_full_observation_preserves_blocking_scan_and_exact_conditions() -> None:
    job = _job(_workflow(FRONTEND_WORKFLOW), "caddy-contract")
    steps = _steps(job)
    build = _named_step(steps, "Build hardened Caddy shell image")
    original = _named_step(steps, "Scan hardened Caddy shell image")
    assert build["id"] == "caddy-build"
    assert original["id"] == "caddy-security"
    assert original["uses"] == TRIVY_ACTION
    assert original["with"] == {
        "version": TRIVY_VERSION,
        "image-ref": "pulseplate-caddy:contract",
        "format": "table",
        "vuln-type": "os,library",
        "severity": "CRITICAL,HIGH",
        "exit-code": "1",
        "cache-dir": "/tmp/trivy-cache-caddy-contract",
    }
    assert "continue-on-error" not in original
    assert job["permissions"] == {"contents": "read"}
    assert job["env"] == {
        "CADDY_FULL_SCAN_TIMEOUT_SECONDS": "300",
        "CADDY_METADATA_TIMEOUT_SECONDS": "900",
        "CADDY_METADATA_CLEANUP_SECONDS": "120",
    }
    assert (
        _step_index(steps, "Capture next loaded Caddy image identity")
        == _step_index(steps, "Build hardened Caddy shell image") + 1
    )
    expected = {
        "Prepare same-epoch full Caddy observation": (
            "${{ !cancelled() && steps.caddy-build.outcome == 'success' && "
            "steps.caddy-image.outcome == 'success' && "
            "(steps.caddy-security.outcome == 'success' || steps.caddy-security.outcome == 'failure') }}"
        ),
        "Observe all-severity Caddy native report": (
            "${{ !cancelled() && steps.caddy-full-prep.outcome == 'success' }}"
        ),
        "Validate and publish full Caddy observation": (
            "${{ !cancelled() && steps.caddy-full-prep.outcome == 'success' && "
            "steps.caddy-full-scan.outcome == 'success' }}"
        ),
    }
    for name, condition in expected.items():
        step = _named_step(steps, name)
        expected_condition = (
            "${{ (github.event_name != 'workflow_dispatch' || inputs.caddy_action != 'xnet060-metadata') && ("
            + condition[len("${{ ") : -len(" }}")]
            + ") }}"
        )
        assert step["if"] == expected_condition
        assert "continue-on-error" not in step
        assert "uses" not in step  # No second setup/cache restore or provider.
    upload = _named_step(steps, "Upload Caddy contract evidence")
    assert (
        upload["if"]
        == "${{ (github.event_name != 'workflow_dispatch' || inputs.caddy_action != 'xnet060-metadata') && (always()) }}"
    )
    assert upload["with"]["path"] == "${{ runner.temp }}/caddy-contract"
    assert (
        _step_index(steps, "Scan hardened Caddy shell image")
        < _step_index(steps, "Prepare same-epoch full Caddy observation")
        < _step_index(steps, "Observe all-severity Caddy native report")
        < _step_index(steps, "Validate and publish full Caddy observation")
        < _step_index(steps, "Upload Caddy contract evidence")
    )


@pytest.mark.parametrize("HC", ["success", "failure"])
def test_caddy_native_full_observation_captures_findings_without_passing_HC(
    tmp_path: Path, HC: str
) -> None:
    result, published, metadata, command = _run_caddy_full_observation_fixture(
        tmp_path, "valid", HC
    )
    assert result.returncode == 0
    assert published
    assert metadata["subject"]["original_HC_outcome"] == HC
    assert metadata["full_scan_native_exit"] == 0
    assert metadata["Results_Secrets_fields_absent"] == 1
    assert metadata["subject"]["image_config_id"] == "sha256:" + "a" * 64
    assert command["argv"][-1] == "sha256:" + "a" * 64
    projections = metadata["subject"]["native_projections"]
    expected_projections = {
        "version.txt": ["version"],
        "build-info.txt": ["build-info"],
        "rebuilt-modules.txt": ["list-modules", "--packages"],
    }
    assert set(projections) == set(expected_projections)
    assert set(command["published_projection_hashes"]) == set(expected_projections)
    image = metadata["subject"]["image_config_id"]
    for name, native_arguments in expected_projections.items():
        projection = projections[name]
        assert projection["image_config_id"] == image
        assert projection["argv"][1:] == [
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--cap-add",
            "NET_BIND_SERVICE",
            "--entrypoint",
            "/usr/bin/caddy",
            image,
            *native_arguments,
        ]
        assert projection["argv"][1:] in command["docker_argv"]
        assert 0 < projection["bytes"] <= 1048576
        assert command["published_projection_hashes"][name] == projection["sha256"]
    assert (
        len(
            [
                args
                for args in command["docker_argv"]
                if "--entrypoint" in args
                and args[args.index("--entrypoint") + 1] == "/usr/bin/caddy"
            ]
        )
        == 3
    )
    clean_environment = metadata["subject"]["clean_env"]
    assert set(clean_environment) == {"PATH", "HOME", "LANG"}
    # The interpreter may add platform state after exec (for example macOS CF
    # text encoding). Compare the exact native outcome, without filtering fields
    # or widening the three-key environment supplied by the workflow.
    environment_control = subprocess.run(
        [sys.executable, "-c", "import json, os; print(json.dumps(dict(os.environ)))"],
        env=clean_environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert not environment_control.stderr
    assert command["env"] == json.loads(environment_control.stdout)
    for flag in (
        "--skip-db-update",
        "--skip-java-db-update",
        "--skip-vex-repo-update",
        "--offline-scan",
        "--skip-version-check",
        "--disable-telemetry",
        "--list-all-pkgs",
        "--ignore-unfixed=false",
    ):
        assert flag in command["argv"]
    assert command["argv"][command["argv"].index("--exit-code") + 1] == "0"
    assert command["argv"][command["argv"].index("--severity") + 1] == (
        "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL"
    )
    assert "does not pass the blocking HC gate" in metadata["claim_boundary"]


@pytest.mark.parametrize(
    "scenario",
    (
        "retag",
        "platform",
        "binary",
        "source",
        "scanner",
        "db",
        "missing-db",
        "scan-error",
        "truncated",
        "wrong-image",
        "wrong-schema",
        "missing-os",
        "missing-caddy",
        "empty-packages",
        "secrets",
        "secrets-null",
        "secrets-object",
        "override",
        "version-image-id",
        "build-info-image-id",
        "modules-image-id",
        "missing-version",
        "missing-build-info",
        "missing-modules",
        "version-mismatch",
        "build-info-mismatch",
        "modules-mismatch",
    ),
)
def test_caddy_native_full_observation_rejects_unbound_or_unsafe_publication(
    tmp_path: Path, scenario: str
) -> None:
    result, published, _metadata, _command = _run_caddy_full_observation_fixture(
        tmp_path, scenario, "failure"
    )
    assert result.returncode != 0
    assert not published
    assert "synthetic-secret-sentinel" not in result.stdout + result.stderr


def _run_caddy_full_observation_fixture(
    tmp_path: Path, scenario: str, HC: str
) -> tuple[subprocess.CompletedProcess[str], bool, dict[str, object], dict[str, object]]:
    """Execute actual inline workflow scripts with finite synthetic native outcomes."""
    workflow = _workflow(FRONTEND_WORKFLOW)
    steps = _steps(_job(workflow, "caddy-contract"))
    workspace = tmp_path / "workspace"
    binaries = tmp_path / "bin"
    runner = tmp_path / "runner"
    cache = tmp_path / "cache"
    for path in (workspace, binaries, runner, cache / "db", runner / "caddy-contract"):
        path.mkdir(parents=True, exist_ok=True)
    paths = (
        "frontend/Dockerfile.caddy-spa",
        "frontend/package.json",
        "frontend/package-lock.json",
        "frontend/.dockerignore",
        ".github/workflows/frontend-ci.yml",
        "deploy/Caddyfile",
        "deploy/Caddyfile.production",
        "scripts/ci/check_docker_runtime_dependency_surface.py",
    )
    for name in paths:
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / name, target)
    for name in ("scripts/__init__.py", "scripts/ci/__init__.py"):
        (workspace / name).touch()
    (cache / "db/trivy.db").write_bytes(b"synthetic-database-epoch")
    (cache / "db/metadata.json").write_text('{"Version":2,"UpdatedAt":"2026-10-10T00:00:00Z"}')
    command_record = tmp_path / "native-command.json"
    docker_record = tmp_path / "docker-commands.json"
    docker = binaries / "docker"
    docker.write_text(
        f"#!{sys.executable}\n"
        "import json,sys\nfrom pathlib import Path\n"
        f"scenario={scenario!r}\n"
        "args=sys.argv[1:]\n"
        f"trace=Path({str(docker_record)!r})\n"
        "history=json.loads(trace.read_text()) if trace.exists() else []\n"
        "history.append(args);trace.write_text(json.dumps(history))\n"
        "if args[:2]==['image','inspect']:\n"
        " image='sha256:'+'a'*64\n"
        " if scenario=='retag' and ("
        + repr(str(tmp_path / "seen"))
        + ") and Path("
        + repr(str(tmp_path / "seen"))
        + ").exists():image='sha256:'+'b'*64\n"
        " Path(" + repr(str(tmp_path / "seen")) + ").touch()\n"
        " if '--format' in args and args[args.index('--format')+1]=='{{.Id}}':print(image)\n"
        " else:print(json.dumps({'Id':image,'Os':'linux','Architecture':'arm64' if scenario=='platform' else 'amd64'}))\n"
        "elif '--entrypoint' in args and args[args.index('--entrypoint')+1]=='/usr/bin/caddy':\n"
        " index=args.index('--entrypoint')\n"
        " if args[index+2]!='sha256:'+'a'*64:sys.exit(3)\n"
        " command=tuple(args[index+3:])\n"
        " outputs={('version',):'v2.11.4 synthetic\\n',('build-info',):'go\\tgo1.26.6\\n',('list-modules','--packages'):'http.handlers.file_server github.com/caddyserver/caddy/v2\\n'}\n"
        " if command not in outputs:sys.exit(4)\n"
        " print(outputs[command],end='')\n"
        "else:\n"
        " print(('c' if scenario=='binary' else 'd')*64+'  /usr/bin/caddy')\n",
        encoding="utf-8",
    )
    # These are native-shape fixtures, not real scanner execution proof.
    report = {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "ArtifactName": "sha256:" + "a" * 64,
        "Metadata": {"ImageID": "sha256:" + "a" * 64},
        "Results": [
            {
                "Target": "Alpine",
                "Class": "os-pkgs",
                "Type": "alpine",
                "Secrets": [],
                "Packages": [{"Name": "libssl3", "Version": "3.5.8-r0"}],
                "Vulnerabilities": [],
            },
            {
                "Target": "usr/bin/caddy",
                "Class": "lang-pkgs",
                "Type": "gobinary",
                "Packages": [{"Name": "golang.org/x/net", "Version": "v0.58.0"}],
                "Vulnerabilities": [{"VulnerabilityID": "CVE-2026-78669", "Severity": "HIGH"}],
            },
        ],
    }
    if scenario == "wrong-image":
        report["Metadata"]["ImageID"] = "sha256:" + "b" * 64
    if scenario == "wrong-schema":
        report["SchemaVersion"] = 1
    if scenario == "missing-os":
        report["Results"] = report["Results"][1:]
    if scenario == "missing-caddy":
        report["Results"] = report["Results"][:1]
    if scenario == "empty-packages":
        report["Results"][1]["Packages"] = []
    if scenario.startswith("secrets"):
        report["Results"][0]["Secrets"] = {
            "secrets": [{"Match": "synthetic-secret-sentinel"}],
            "secrets-null": None,
            "secrets-object": {},
        }[scenario]
    scanner = binaries / "trivy"
    scanner.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\nfrom pathlib import Path\n"
        f"scenario={scenario!r}\nreport={report!r}\n"
        "args=sys.argv[1:]\n"
        "if args==['--version']:\n print('Version: 0.74.0');sys.exit(0)\n"
        f"Path({str(command_record)!r}).write_text(json.dumps({{'argv':args,'env':dict(os.environ)}}))\n"
        "output=Path(args[args.index('--output')+1])\n"
        "output.write_text('{truncated' if scenario=='truncated' else json.dumps(report))\n"
        "if scenario=='db':\n (Path(args[args.index('--cache-dir')+1])/'db/trivy.db').write_bytes(b'changed')\n"
        "if scenario=='scanner':\n Path(__file__).write_text('changed-scanner')\n"
        "sys.exit(2 if scenario=='scan-error' else 0)\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    scanner.chmod(0o755)
    github_output = tmp_path / "github-output"
    github_output.touch()
    # Explicit synthetic environment prevents credential leakage in mocked
    # headers, child diagnostics or full native-command snapshots.
    environment = {
        "PATH": str(binaries) + os.pathsep + os.defpath,
        "RUNNER_TEMP": str(runner),
        "GITHUB_OUTPUT": str(github_output),
        "CADDY_HC_OUTCOME": HC,
        "CADDY_TRIVY_CACHE": str(cache),
        "CADDY_FULL_SCAN_TIMEOUT_SECONDS": "5",
        "TRIVY_SEVERITY": "HIGH",
        "TRIVY_EXIT_CODE": "1",
        "TRIVY_SCANNERS": "vuln",
        "TRIVY_SKIP_FILES": "usr/bin/caddy",
        "TRIVY_VEX": "synthetic-vex",
    }
    if scenario == "override":
        environment["TRIVY_CMD"] = str(binaries / "different-scanner")
    last = None
    for name in (
        "Capture next loaded Caddy image identity",
        "Prepare same-epoch full Caddy observation",
        "Observe all-severity Caddy native report",
        "Validate and publish full Caddy observation",
    ):
        script = (
            _named_step(steps, name)["run"].split("python3 - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        )
        last = subprocess.run(
            [sys.executable, "-c", script],
            env=environment,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if last.returncode:
            break
        if name == "Capture next loaded Caddy image identity":
            outputs = dict(line.split("=", 1) for line in github_output.read_text().splitlines())
            environment["CADDY_OBSERVATION_STATE"] = outputs["state"]
            if scenario == "source":
                (workspace / "frontend/package.json").write_text("changed-source")
            if scenario == "missing-db":
                (cache / "db/trivy.db").unlink()
            if scenario == "binary":
                docker.write_text(
                    docker.read_text().replace("scenario='binary'", "scenario='valid'")
                )
            projection_faults = {
                "version-image-id": ("version.txt", "image-id"),
                "build-info-image-id": ("build-info.txt", "image-id"),
                "modules-image-id": ("rebuilt-modules.txt", "image-id"),
                "missing-version": ("version.txt", "missing"),
                "missing-build-info": ("build-info.txt", "missing"),
                "missing-modules": ("rebuilt-modules.txt", "missing"),
                "version-mismatch": ("version.txt", "mismatch"),
                "build-info-mismatch": ("build-info.txt", "mismatch"),
                "modules-mismatch": ("rebuilt-modules.txt", "mismatch"),
            }
            if scenario in projection_faults:
                filename, fault = projection_faults[scenario]
                state_path = Path(outputs["state"])
                subject = json.loads(state_path.read_text())
                if fault == "image-id":
                    projection = subject["native_projections"][filename]
                    projection["argv"][
                        projection["argv"].index(subject["image_config_id"])
                    ] = "pulseplate-caddy:contract"
                    state_path.write_text(json.dumps(subject))
                elif fault == "missing":
                    (state_path.parent / "native-projections" / filename).unlink()
                else:
                    (state_path.parent / "native-projections" / filename).write_bytes(
                        b"changed-native-projection"
                    )
    assert last is not None
    published = runner / "caddy-contract/full-observation"
    result_metadata = (
        json.loads((published / "observation.json").read_text()) if published.exists() else {}
    )
    native_command = json.loads(command_record.read_text()) if command_record.exists() else {}
    native_command["docker_argv"] = (
        json.loads(docker_record.read_text()) if docker_record.exists() else []
    )
    native_command["published_projection_hashes"] = (
        {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (published / "native-projections").iterdir()
        }
        if published.exists()
        else {}
    )
    return last, published.exists(), result_metadata, native_command


def test_caddy_counterfactual_metadata_owns_no_compiler_or_final_recipe_mutation() -> None:
    workflow = _workflow(FRONTEND_WORKFLOW)
    event = workflow.get("on", workflow.get(True))
    assert event["workflow_dispatch"]["inputs"]["caddy_action"]["options"] == [
        "contract",
        "xnet060-metadata",
    ]
    steps = _steps(_job(workflow, "caddy-contract"))
    metadata = _named_step(
        steps, "Qualify Caddy compiler and two counterfactual compress derivations"
    )
    assert (
        metadata["if"]
        == "${{ github.event_name == 'workflow_dispatch' && inputs.caddy_action == 'xnet060-metadata' }}"
    )
    source = metadata["run"]
    assert re.search(r"\bgo\s+build\b", source) is None
    assert 'for label in ("a", "b")' in source
    assert '"go_build_invocations": 0' in source
    assert 'root_module="pulseplate.local/caddy-build"' in source
    assert "tree_inventory(left) == tree_inventory(right)" in source
    assert "go get golang.org/x/net@v0.60.0" in source
    assert "go mod download all" in source and "go mod verify" in source
    assert "baseline-packages.json" in source and "final-packages.json" in source
    assert "post-get-go.mod" in source and "module-derivation.patch" in source
    assert "C_R_candidate" in source and "pending independent source/security review" in source
    assert "Counterfactual recipe baselines" in source
    assert "zlib-1.3.2-r1" in source and "apk verify /output/zlib-1.3.2-r1.apk" in source
    vendor = source.split("vendor_script = '''", 1)[1].split("'''", 1)[0]
    assert "apk verify --help" not in vendor
    commands = [line.strip() for line in vendor.splitlines() if line.strip()]
    assert commands == [
        "set -eu",
        "/sbin/apk --version > /output/apk-version.txt",
        "cp /etc/apk/repositories /output/compiler-repositories.txt",
        "mkdir /output/keys",
        "cp /etc/apk/keys/* /output/keys/",
        "wget -q -O /output/APKINDEX.tar.gz https://dl-cdn.alpinelinux.org/alpine/v3.23/main/x86_64/APKINDEX.tar.gz",
        "/sbin/apk verify /output/APKINDEX.tar.gz > /output/index-signature.txt",
        "/sbin/apk fetch --no-cache --repository https://dl-cdn.alpinelinux.org/alpine/v3.23/main --match package --output /output zlib-1.3.2-r1",
        "/sbin/apk verify /output/zlib-1.3.2-r1.apk > /output/package-signature.txt",
        "/sbin/apk fetch --no-cache --repository https://dl-cdn.alpinelinux.org/alpine/v3.23/main --match package --output /output brotli-libs-1.2.1-r0",
        "/sbin/apk verify /output/brotli-libs-1.2.1-r0.apk > /output/brotli-signature.txt",
    ]
    assert 'require(gets == baseline_gets + [b"github.com/klauspost/compress@v1.18.7"]' in source
    assert '"counterfactual_seed_gets"' in source and '"selected_recipe_gets"' in source
    # The compatibility mode now observes the current four-get seed plus compress.
    recipe = DOCKERFILE.read_text()
    assert recipe.count("go get golang.org/x/net@v0.60.0") == 1
    assert recipe.count("go get github.com/klauspost/compress@v1.18.7") == 1
    assert "CVE-2026-111497" in source
    assert "Go 1.26.10" in recipe


def test_caddy_full_observation_keeps_native_diagnostics_without_inventing_secrets() -> None:
    steps = _steps(_job(_workflow(FRONTEND_WORKFLOW), "caddy-contract"))
    preparation = _named_step(steps, "Prepare same-epoch full Caddy observation")["run"]
    publication = _named_step(steps, "Validate and publish full Caddy observation")["run"]
    assert '"scanner-version.stdout"' in preparation and '"scanner-version.stderr"' in preparation
    assert '"scan.stdout.private"' in publication and '"scan.stderr.private"' in publication
    assert "scanner_diagnostic_credential_reflection" in publication
    assert "Results_Secrets_fields_absent" in publication
    assert 'native["Results"]' in publication
    assert 'row["Secrets"] = []' not in publication


@pytest.mark.parametrize("mode", ["publish"])
def test_alertmanager_executable_stages_have_exact_manual_events_and_no_Q(mode: str) -> None:
    workflow = _workflow(CD_WORKFLOW)
    name = "alertmanager-candidate-build" if mode == "build" else "alertmanager-main-publication"
    job = _job(workflow, name)
    ref = "codex/dependency-alertmanager-remediation" if mode == "build" else "main"
    assert job["if"] == (
        "github.event_name == 'workflow_dispatch' && inputs.alertmanager_mode == '" + mode + "' "
        "&& github.repository == 'Katsiarynakavaleuskaya/PulsePlate' && github.repository_id == '1043311030' "
        "&& github.ref == 'refs/heads/" + ref + "' "
        "&& github.run_attempt == 1 && inputs.postgres_mode == 'disabled'"
    )
    assert "needs" not in job
    assert job["permissions"] == {
        "contents": "read",
        "actions": "read",
        "packages": "read" if mode == "build" else "write",
    }
    steps = _steps(job)
    setup = _named_step(steps, "Select AM Python without dependency or SDK installation")
    assert setup["uses"] == "./.github/actions/python-setup"
    assert setup["with"] == {
        "python-version": "3.13.14",
        "skip-base-install": "true",
    }
    assert setup["env"]["DEVPI_CI_USER"] == setup["env"]["DEVPI_CI_PASSWORD"] == ""
    install = _named_step(steps, "Install isolated AM host tools through the locked owner")
    smoke = _named_step(steps, "Verify isolated AM host import capability before effects")
    driver = next(
        step
        for step in steps
        if "--artifact alertmanager --alertmanager-stage " + mode in step.get("run", "")
    )
    assert (
        _step_index(steps, setup["name"])
        < _step_index(steps, install["name"])
        < _step_index(steps, smoke["name"])
        < _step_index(steps, driver["name"])
    )
    assert smoke["id"] == "am-python"
    assert driver["env"]["AM_HOST_PYTHON"] == "${{ steps.am-python.outputs.python }}"
    assert (
        '"$AM_HOST_PYTHON" -m scripts.ci.fetch_docker_source_artifacts '
        "--artifact alertmanager --alertmanager-stage " + mode
    ) in driver["run"]
    assert "python -m scripts.ci.fetch_docker_source_artifacts" not in driver["run"]
    assert '"$AM_HOST_PYTHON" -I' not in driver["run"]
    for step in (install, smoke):
        assert (
            'am_root="$RUNNER_TEMP/pulseplate-am-python-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"'
            in step["run"]
        )
        assert 'am_python="$am_root/bin/python"' in step["run"]
    assert "GITHUB_OUTPUT" not in install["run"]
    assert (
        smoke["run"].index("assert callable(native.native_alertmanager_main)")
        < smoke["run"].index(
            '"$am_python" -m tests.test_notify_premium_alias_checkpoint_failure --help'
        )
        < smoke["run"].index('printf \'python=%s\\n\' "$am_python" >> "$GITHUB_OUTPUT"')
    )
    runs = "\n".join(step.get("run", "") for step in steps)
    assert "--alertmanager-stage " + mode in runs
    assert "--alertmanager-module-qualify" not in runs
    assert "go get" not in runs and "docker build" not in runs
    assert 'test "$checkout_sha" = "$SOURCE_SHA"' in runs
    assert all(
        step.get("with", {}).get("persist-credentials") is False
        for step in steps
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    assert all(
        "/retained/" in step["with"]["path"] and "/private/" not in step["with"]["path"]
        for step in steps
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    )
    if mode == "build":
        upload = next(
            step
            for step in steps
            if str(step.get("uses", "")).startswith("actions/upload-artifact@")
        )
        assert (
            upload["with"]["include-hidden-files"] is True
        ), "retained producer-source/.github must survive artifact upload"


def test_alertmanager_independent_phase_ceilings_fit_each_actual_job_with_retention_headroom() -> (
    None
):
    workflow = _workflow(CD_WORKFLOW)
    env = workflow["env"]
    setup = int(env["ALERTMANAGER_SETUP_MINUTES"]) * 60
    upload = int(env["ALERTMANAGER_UPLOAD_MINUTES"]) * 60
    prep = int(env["ALERTMANAGER_PREP_SECONDS"])
    cleanup = int(env["ALERTMANAGER_CLEANUP_SECONDS"])
    native = int(env["ALERTMANAGER_NATIVE_SECONDS"])
    native_cleanup = int(env["ALERTMANAGER_NATIVE_CLEANUP_SECONDS"])
    assert native > 905 + 325
    assert (
        0
        < int(env["ALERTMANAGER_SCAN_TIMEOUT_SECONDS"])
        < int(env["ALERTMANAGER_SCAN_PROCESS_SECONDS"])
        <= int(env["ALERTMANAGER_SECURITY_SECONDS"])
    )
    work = {
        "alertmanager-retained-candidate": prep + cleanup + native + native_cleanup,
        "alertmanager-main-publication": prep
        + cleanup
        + int(env["ALERTMANAGER_PUBLICATION_SECONDS"])
        + native_cleanup
        + native
        + native_cleanup,
    }
    for name, seconds in work.items():
        job = _job(workflow, name)
        assert job["timeout-minutes"] * 60 - (seconds + setup + upload) >= 300
        for step in _steps(job):
            if str(step.get("uses", "")).startswith("actions/upload-artifact@"):
                assert step["timeout-minutes"] == "${{ fromJSON(env.ALERTMANAGER_UPLOAD_MINUTES) }}"


def test_alertmanager_PR_retained_candidate_has_no_registry_or_compiler_authority() -> None:
    workflow = _workflow(CD_WORKFLOW)
    job = _job(workflow, "alertmanager-retained-candidate")
    assert job["if"] == (
        "github.event_name == 'pull_request' && github.repository == 'Katsiarynakavaleuskaya/PulsePlate' "
        "&& github.event.pull_request.head.repo.id == 1043311030 "
        "&& github.event.pull_request.head.ref == 'codex/python-setup-security-stabilization'"
    )
    assert job["permissions"] == {"contents": "read", "actions": "read"}
    assert job["env"] == {
        "ALERTMANAGER_JOB_TIMEOUT_MINUTES": "80",
        "ALERTMANAGER_CALLER_KIND": "standalone",
        "AM_CANDIDATE_RUN": "39143039135",
        "AM_CANDIDATE_ARTIFACT": "12142714566",
        "AM_CANDIDATE_SOURCE": "63455b8a750ef07a1e525078b4e3ce2089eecdde",
    }
    runs = "\n".join(step.get("run", "") for step in _steps(job))
    assert "--alertmanager-stage candidate-check" in runs
    assert "--alertmanager-stage build" not in runs and "--alertmanager-module-qualify" not in runs
    assert "docker login" not in runs and "GHCR_READ_TOKEN" not in runs
    assert (
        _job(workflow, "alertmanager-module-qualification")["if"].count("inputs.alertmanager_mode")
        == 1
    )


@pytest.mark.parametrize(
    "case",
    [
        "absent",
        "same",
        "descendant",
        "proof-retention",
        "primary-proof-retention",
        "unmerged",
        "wrong-pr",
        "foreign-pr",
        "merge-invalid",
        "not-ancestor",
        "shallow",
        "source-drift",
        "template-drift",
        "main-before-login",
        "main-before-copy",
        "main-after-copy",
        "inventory",
        "conflict",
        "denied",
        "pullback",
        "post-readback",
        "credential-mode",
        "cleanup",
    ],
)
def test_alertmanager_publication_entrypoint_uses_canonical_guards_and_exact_copy_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    from scripts.ci import fetch_docker_source_artifacts as fetcher
    from scripts.ci import prometheus_source_image as transport
    from tests.test_docker_workflow_build_path_contract import _alertmanager_proposal_arguments

    original_which = shutil.which
    synthetic_docker = "/synthetic/alertmanager-publication/docker"

    def resolve_docker(command: str | bytes, *args: Any, **kwargs: Any) -> str | bytes | None:
        if command == "docker":
            return synthetic_docker
        return original_which(command, *args, **kwargs)

    monkeypatch.setattr(shutil, "which", resolve_docker)
    for key in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GHCR_READ_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GH_HOST",
        "GH_CONFIG_DIR",
        "DOCKER_CONFIG",
        "DOCKER_AUTH_CONFIG",
        "NETRC",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in _workflow(CD_WORKFLOW)["env"].items():
        if key.startswith("ALERTMANAGER_"):
            monkeypatch.setenv(key, value)
    for key, value in {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_REPOSITORY_OWNER": "Katsiarynakavaleuskaya",
        "GH_TOKEN": "synthetic-publish-credential",
        "GITHUB_TOKEN": "synthetic-publish-credential",
    }.items():
        monkeypatch.setenv(key, value)
    if case in ("proof-retention", "primary-proof-retention"):
        original_write = Path.write_text

        def write(path: Path, *args: Any, **kwargs: Any) -> int:
            if (
                path.name == "native-observation.json"
                and path.parent.name == "publication-source-proof"
            ):
                raise OSError("synthetic publication proof retention failed")
            return original_write(path, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", write)
    events: list[str] = []
    native_calls: list[str] = []
    graph: dict[str, Any] = {}
    reads = 0
    main_reads = 0
    original_tag = transport.immutable_tag_state
    closed = False
    tool_bytes = b"synthetic qualified ORAS transport"

    class API:
        def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
            del evidence, cleanup
            self.private, self.deadline, self.cleanup_seconds = private, deadline, 45
            private.mkdir()
            for name in ("home", "config", "cache", "tmp"):
                (private / name).mkdir()

        def json(self, endpoint: str) -> dict[str, Any]:
            nonlocal main_reads
            if "/git/ref/" in endpoint:
                main_reads += 1
                drift_at = {
                    "main-before-login": 2,
                    "main-before-copy": 3,
                    "main-after-copy": 4,
                }.get(case)
                return {"object": {"sha": ("f" if main_reads == drift_at else "a") * 40}}
            if "/pulls/" in endpoint:
                return {
                    "number": 2477 if case == "wrong-pr" else 2497,
                    "state": "closed",
                    "merged": case != "unmerged",
                    "merge_commit_sha": (
                        "unknown"
                        if case == "merge-invalid"
                        else ("d" if case == "descendant" else "a") * 40
                    ),
                    "base": {
                        "ref": "main",
                        "repo": {"id": 1 if case == "foreign-pr" else 1043311030},
                    },
                    "head": {
                        "ref": fetcher._ALERT_RECEIVER_BRANCH,
                        "sha": "c" * 40,
                        "repo": {"id": 1043311030},
                    },
                }
            assert "/commits/" in endpoint
            return {"sha": "a" * 40}

        def _capture(self, argv: list[str], maximum: int, **kwargs: Any) -> bytes:
            del maximum
            environment = kwargs.get("environment", {})
            assert all(
                key not in environment
                for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "HTTP_PROXY")
            )
            if "rev-parse" in argv:
                return ("a" * 40 + "\n").encode()
            if "login" in argv:
                events.append("login")
                assert argv[0] == synthetic_docker
                assert "tag" in events and kwargs["input_data"] == b"synthetic-publish-credential\n"
                credential = Path(argv[argv.index("--config") + 1]) / "config.json"
                credential.write_text('{"auths":{"ghcr.io":{"auth":"synthetic-only"}}}')
                credential.chmod(0o644 if case == "credential-mode" else 0o600)
            elif "--from-oci-layout" in argv:
                events.append("copy")
                assert events[-2] == "login" and case != "same"
                if case == "denied":
                    raise RuntimeError("synthetic denied real intended copy")
                assert argv[-2].endswith("@" + graph["manifest"]["digest"])
                assert (
                    argv[-1]
                    == "ghcr.io/katsiarynakavaleuskaya/pulseplate:alertmanager-0.34.1-"
                    + graph["manifest"]["digest"][7:]
                )
            elif "--to-oci-layout" in argv:
                events.append("pullback")
                assert (
                    argv[-2]
                    == "ghcr.io/katsiarynakavaleuskaya/pulseplate@" + graph["manifest"]["digest"]
                )
                destination = Path(argv[-1].removesuffix(":pullback"))
                shutil.copytree(destination.parent / "candidate/layout", destination)
                if case == "pullback":
                    (destination / "blobs/sha256" / graph["layers"][0]["digest"][7:]).write_bytes(
                        b"changed retained layer"
                    )
            else:
                pytest.fail("unexpected native transport argv")
            return b"synthetic success"

        def close(self) -> None:
            nonlocal closed
            events.append("close")
            if case == "cleanup":
                raise RuntimeError("synthetic private cleanup failed")
            shutil.rmtree(self.private)
            closed = True

    def authenticated(
        api: API, run: int, artifact: int, source: str, destination: Path, **kwargs: str
    ) -> dict[str, Any]:
        del api, run, artifact
        destination.write_bytes(b"synthetic authenticated artifact")
        return {
            "source": source,
            "zip_sha256": "e" * 64,
            "kind": kwargs.get("kind", "qualification"),
        }

    def support(archive: Path, destination: Path, **kwargs: Any) -> dict[str, Any]:
        del archive
        destination.mkdir()
        return {"probe": {}}

    def candidate(
        archive: Path,
        destination: Path,
        source: dict[str, bytes],
        inspected: dict[str, Any],
        support: Path,
        **kwargs: Any,
    ) -> dict[str, Any]:
        del archive, source, inspected, support
        layout = destination / "layout"
        (layout / "blobs/sha256").mkdir(parents=True)

        def blob(raw: bytes, media: str) -> dict[str, Any]:
            digest = hashlib.sha256(raw).hexdigest()
            (layout / "blobs/sha256" / digest).write_bytes(raw)
            return {"digest": "sha256:" + digest, "size": len(raw), "mediaType": media}

        configuration = blob(
            b'{"architecture":"amd64","os":"linux"}', "application/vnd.oci.image.config.v1+json"
        )
        layer = blob(b"synthetic retained layer", "application/vnd.oci.image.layer.v1.tar")
        manifest = blob(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "config": configuration,
                    "layers": [layer],
                }
            ).encode(),
            "application/vnd.oci.image.manifest.v1+json",
        )
        (layout / "oci-layout").write_text('{"imageLayoutVersion":"1.0.0"}')
        (layout / "index.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "mediaType": "application/vnd.oci.image.index.v1+json",
                    "manifests": [manifest],
                }
            )
        )
        graph.update(
            {
                "manifest": manifest,
                "config": configuration,
                "layers": [layer],
                "files": {"usr/bin/alertmanager": "1" * 64},
            }
        )
        return {"source": "c" * 40, "graph": graph, "status": "OBSERVED_NATIVE_SECURITY_ACCEPTED"}

    def tool(api: API, root: Path, output: Path) -> tuple[Path, dict[str, Any]]:
        del api
        assert root == fetcher.REPO_ROOT
        path = output / "oras"
        path.write_bytes(tool_bytes)
        return path, {"coordinates": {"binary_sha256": hashlib.sha256(tool_bytes).hexdigest()}}

    def package(api: API) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        nonlocal reads
        del api
        reads += 1
        events.append("inventory")
        if case == "inventory":
            raise transport.QualificationError("package_complete_inventory_bound")
        digest = graph["manifest"]["digest"]
        tag = "alertmanager-0.34.1-" + digest[7:]
        versions = []
        if case in ("same", "conflict") or reads > 1:
            versions = [
                {
                    "id": 1,
                    "name": (
                        "sha256:" + "9" * 64
                        if case == "conflict" or case == "post-readback" and reads > 1
                        else digest
                    ),
                    "metadata": {"container": {"tags": [tag]}},
                }
            ]
        return {"repository": {"id": 1043311030}, "package": {"id": 9374404}}, versions

    def tag(versions: list[dict[str, Any]], value: str, digest: str) -> bool:
        events.append("tag")
        return original_tag(versions, value, digest)

    def native(
        result: dict[str, Any], observation: Path, work: Path, limits: dict[str, int]
    ) -> dict[str, Any]:
        del result, limits
        assert closed and "close" == events[-1] and not (work.parent / "private").exists()
        assert observation.is_file() and (observation.parent / "candidate.oci.tar").is_file()
        native_calls.append("same-immutable-pullback")
        work.mkdir()
        (work / "evidence").mkdir()
        return {"synthetic_control_only": True}

    sources = {path: b"synthetic reviewed source" for path in fetcher._ALERT_SELECTION_FILES}

    class PublicationNative:
        def __init__(self, evidence: Path, deadline: float, cleanup: int) -> None:
            assert evidence.parent.name == "retained"
            assert evidence.name == "publication-source-proof" and cleanup == 45
            self.records: list[dict[str, Any]] = []

        def run(
            self,
            argv: list[str],
            label: str,
            environment: dict[str, str],
            *,
            cwd: Path,
            **kwargs: Any,
        ) -> bytes:
            assert cwd == fetcher.REPO_ROOT and "--no-replace-objects" in argv
            assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
            if argv[-2:] == ["rev-parse", "--is-shallow-repository"]:
                return b"true\n" if case == "shallow" else b"false\n"
            assert argv[-4:] == [
                "merge-base",
                "--is-ancestor",
                ("d" if case == "descendant" else "a") * 40,
                "a" * 40,
            ]
            if case in ("not-ancestor", "primary-proof-retention"):
                raise RuntimeError("synthetic native Git exit1")
            return b""

    monkeypatch.setattr(transport, "Native", PublicationNative)
    monkeypatch.setattr(fetcher, "_alertmanager_bind_material", lambda *a: sources)
    monkeypatch.setattr(
        fetcher,
        "_alertmanager_regular_sources",
        lambda *a: (
            {**sources, "deploy/alertmanager/trivy-ignore.yaml": b"drift"}
            if case == "source-drift"
            else sources
        ),
    )

    def render(
        supplied: dict[str, bytes],
        work: Path,
        deadline: float,
        *,
        expected_case: str,
        controller_templates: dict[str, bytes],
    ) -> None:
        assert supplied == sources and expected_case == "accepted"
        if case == "template-drift":
            raise RuntimeError("AM_reviewed_controller_data_closure")

    monkeypatch.setattr(fetcher, "_alertmanager_render_source_contract", render)
    monkeypatch.setattr(transport, "GitHubRead", API)
    monkeypatch.setattr(fetcher, "_alertmanager_original_lineage", lambda *a: None)
    monkeypatch.setattr(transport, "retained_tool", tool)
    monkeypatch.setattr(transport, "existing_public_package", package)
    monkeypatch.setattr(transport, "immutable_tag_state", tag)
    monkeypatch.setattr(fetcher, "_alertmanager_authenticated_inputs", authenticated)

    def selected_inputs(
        api: API, args: Any, output: Path, accepted: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return tuple(
            authenticated(api, 1, 2, accepted["source"], output / (name + ".zip"), kind=name)
            for name in ("qualification", "support")
        )

    monkeypatch.setattr(fetcher, "_alertmanager_selected_inputs", selected_inputs)
    monkeypatch.setattr(fetcher, "_alertmanager_source_snapshot", lambda *a, **k: {})
    monkeypatch.setattr(
        fetcher,
        "_ALERT_ACCEPTED_CANDIDATE",
        {
            "run": 888,
            "attempt": 1,
            "artifact": 777,
            "source": "c" * 40,
            "job": 666,
            "zip_sha256": "e" * 64,
            "source_files": {
                path: hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()
                for path in (
                    *fetcher._ALERT_Q_SOURCE_FILES,
                    "tests/test_notify_premium_alias_checkpoint_failure.py",
                )
            },
            "graph": {"synthetic_guarded_publication_only": True},
            "OCI_archive_sha256": "f" * 64,
        },
    )
    monkeypatch.setattr(fetcher, "_alertmanager_package_read", lambda *a: {})
    monkeypatch.setattr(fetcher, "_alertmanager_qualified_payload", lambda *a, **k: {"plan": {}})
    monkeypatch.setattr(fetcher, "_alertmanager_support_payload", support)
    monkeypatch.setattr(fetcher, "_alertmanager_candidate_payload", candidate)
    monkeypatch.setattr(fetcher, "_alertmanager_candidate_graph", lambda *a: graph)
    monkeypatch.setattr(fetcher, "_alertmanager_native_candidate", native)
    monkeypatch.setattr(
        fetcher, "_alertmanager_pair", lambda *a, **k: pytest.fail("publication started compiler")
    )
    monkeypatch.setattr(
        fetcher, "_qualify_alertmanager_modules", lambda *a: pytest.fail("publication renewed Q")
    )
    output = tmp_path / "owned-publication"
    argv = _alertmanager_proposal_arguments(output)
    argv[argv.index("build")] = "publish"
    argv += [
        "--alertmanager-pr",
        "2497",
        "--alertmanager-candidate-run",
        "888",
        "--alertmanager-candidate-artifact",
        "777",
        "--alertmanager-candidate-source",
        "c" * 40,
    ]
    if case not in ("absent", "same", "descendant"):
        with pytest.raises(OSError if case == "proof-retention" else RuntimeError) as raised:
            fetcher.main(argv)
        if case == "primary-proof-retention":
            assert str(raised.value) == "synthetic native Git exit1"
            assert "AM native proof retention failed: OSError" in raised.value.__notes__
    else:
        assert fetcher.main(argv) == 0
    result = json.loads((output / "retained/candidate-observation.json").read_text())
    assert result["compiler_starts"] == result["logical_build_starts"] == 0
    assert "synthetic-publish-credential" not in json.dumps(result)
    assert events.count("copy") == (
        0
        if case
        in (
            "same",
            "inventory",
            "conflict",
            "credential-mode",
            "unmerged",
            "wrong-pr",
            "foreign-pr",
            "merge-invalid",
            "not-ancestor",
            "shallow",
            "source-drift",
            "template-drift",
            "main-before-login",
            "main-before-copy",
            "proof-retention",
            "primary-proof-retention",
        )
        else 1
    )
    if case in ("inventory", "conflict"):
        assert "login" not in events and native_calls == []
    if case == "denied":
        assert result["package_WRITE"] == "UNPROVED" and result["copy_invocations"] == 0
    if case == "same":
        assert result["package_WRITE"] == "UNEXERCISED_EXISTING_SAME_SUBJECT" and native_calls
    if case in ("absent", "descendant"):
        assert result["package_WRITE"] == "OBSERVED_SUCCESSFUL_INTENDED_COPY" and native_calls
    if case not in ("absent", "same", "descendant"):
        assert native_calls == []

    if case in ("main-after-copy", "pullback", "post-readback"):
        assert result["copy_attempts"] == result["copy_invocations"] == 1
        assert result["package_WRITE"] == "OBSERVED_SUCCESSFUL_INTENDED_COPY"
    if case == "descendant":
        assert result["publication_source_sha"] == "a" * 40
        assert result["publication_merge_sha"] == "d" * 40


@pytest.mark.parametrize("current_epoch", [False, True])
@pytest.mark.parametrize(
    "fault",
    (
        None,
        "scanner-exit",
        "missing-report",
        "malformed",
        "partial",
        "wrong-subject",
        "new-HIGH",
        "target-Go-UNKNOWN",
        "target-Go-LOW",
        "target-Go-MEDIUM",
        "target-Go-HIGH",
        "target-Go-CRITICAL",
        "secret",
        "old-missing",
        "positive-missing",
        "negative-secret",
        "DB-drift",
        "observation-write",
        "primary-and-observation",
    ),
)
def test_alertmanager_current_four_controls_retain_native_reports_and_reject_unproven_scans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str | None,
    current_epoch: bool,
) -> None:
    """Drive the actual current four-control owner through bounded synthetic native I/O."""
    from argparse import Namespace
    from copy import deepcopy
    from scripts.ci import fetch_docker_source_artifacts as fetcher
    from scripts.ci import prometheus_source_image as transport
    from tests.test_docker_workflow_build_path_contract import _alertmanager_current_scan_report

    for key in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GHCR_READ_TOKEN",
        "DOCKER_CONFIG",
        "DOCKER_AUTH_CONFIG",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in _workflow(CD_WORKFLOW)["env"].items():
        if key.startswith("ALERTMANAGER_"):
            monkeypatch.setenv(key, value)
    monkeypatch.setenv("ALERTMANAGER_CALLER_KIND", "shared-pr")
    monkeypatch.setenv("ALERTMANAGER_JOB_TIMEOUT_MINUTES", "170")
    scanner = tmp_path / "trivy"
    scanner.write_bytes(b"synthetic native tool")
    monkeypatch.setattr(
        fetcher, "_ALERT_TRIVY_SHA256", hashlib.sha256(scanner.read_bytes()).hexdigest()
    )
    cache = tmp_path / "cache"
    (cache / "db").mkdir(parents=True)
    (cache / "db/trivy.db").write_bytes(b"synthetic native DB")
    (cache / "db/metadata.json").write_text('{"Version":2,"UpdatedAt":"2026-10-18T00:00:00Z"}')
    monkeypatch.setattr(shutil, "which", lambda name: "/synthetic/" + name)
    calls: list[str] = []
    timers: list[float] = []
    if fault in ("observation-write", "primary-and-observation"):
        import signal

        monkeypatch.setattr(signal, "getitimer", lambda timer: (5.0, 0.0))
        monkeypatch.setattr(signal, "setitimer", lambda timer, value, *args: timers.append(value))
        monkeypatch.setattr(fetcher.time, "monotonic", lambda: 100.0)
        write = Path.write_text

        def write_observation(path: Path, *args: Any, **kwargs: Any) -> Any:
            if path.name == "security-observation.json":
                raise OSError("synthetic observation write failed")
            return write(path, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", write_observation)

    selected = deepcopy(fetcher._ALERT_HISTORICAL_C10)
    oracle = deepcopy(fetcher._ALERT_CURRENT_SCAN_ORACLE)
    if current_epoch:
        selected["source"] = "a" * 40
        selected["graph"]["config"]["digest"] = oracle["subject"]["config"] = "sha256:" + "b" * 64
        selected["graph"]["manifest"]["digest"] = oracle["subject"]["manifest"] = (
            "sha256:" + "c" * 64
        )
        for name, letter in (("alertmanager", "d"), ("amtool", "e")):
            selected["graph"]["files"]["usr/bin/" + name] = oracle["subject"]["binary_sha256"][
                name
            ] = (letter * 64)
            oracle["expected_modules"][name]["stdlib"] = "v1.27.3"
    monkeypatch.setattr(fetcher, "_ALERT_ACCEPTED_CANDIDATE", selected)
    monkeypatch.setattr(fetcher, "_ALERT_CURRENT_SCAN_ORACLE", oracle)
    forwarded: list[tuple[str, bool]] = []
    inventory_owner = fetcher._alertmanager_candidate_inventory
    control_owner = fetcher._alertmanager_vulnerability_control

    def inventory(*args: Any, current: bool = False) -> dict[str, Any]:
        forwarded.append(("candidate", current))
        return inventory_owner(*args, current=current)

    def control(*args: Any, current: bool = False) -> dict[str, Any]:
        forwarded.append(("old_control", current))
        return control_owner(*args, current=current)

    monkeypatch.setattr(fetcher, "_alertmanager_candidate_inventory", inventory)
    monkeypatch.setattr(fetcher, "_alertmanager_vulnerability_control", control)
    graph = selected["graph"]
    subject = graph["config"]["digest"]
    report = _alertmanager_current_scan_report()

    class Native:
        def __init__(self, *args: Any) -> None:
            self.records: list[dict[str, Any]] = []

        def run(
            self,
            argv: list[str],
            label: str,
            environment: dict[str, str],
            *,
            cwd: Path,
            **kwargs: Any,
        ) -> bytes:
            assert cwd == args.output_dir
            calls.append(label)
            assert not any("TOKEN" in key for key in environment)
            assert environment["DOCKER_CONFIG"].endswith("empty-docker-config")
            if label == "current-scanner-version":
                return b'{"Version":"0.74.0"}'
            if label == "live-local-candidate":
                return json.dumps(
                    {
                        "Id": subject,
                        "Os": "linux",
                        "Architecture": "amd64",
                        "RootFS": {"Layers": graph["diff_ids"]},
                    }
                ).encode()
            if label == "live-old-control-identity":
                return json.dumps(
                    {
                        "Id": fetcher._ALERT_OLD_RUNTIME_CONFIG,
                        "Os": "linux",
                        "Architecture": "amd64",
                        "RepoDigests": [fetcher._ALERT_OLD_RUNTIME_REF],
                    }
                ).encode()
            if label == "live-old-control-pull":
                return b"pulled old control only"
            assert argv[argv.index("--severity") + 1] == "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL"
            assert "--list-all-pkgs" in argv and "--skip-db-update" in argv and "--scanners" in argv
            assert Path(argv[argv.index("--ignorefile") + 1]).read_bytes() == b""
            if argv[1] == "image":
                assert argv[argv.index("--image-src") + 1] == "docker"
            if fault in ("scanner-exit", "primary-and-observation"):
                self.records.append({"label": label, "exit": 2})
                raise RuntimeError("synthetic scanner native exit2")
            target = Path(argv[argv.index("--output") + 1])
            if fault == "missing-report":
                return b""
            if fault == "malformed":
                target.write_bytes(b"{")
                return b""
            data = deepcopy(report)
            if label == "current-candidate-full-supported":
                if fault == "partial":
                    data["Results"][1]["Packages"].pop()
                elif fault == "wrong-subject":
                    data["Metadata"]["ImageID"] = "sha256:" + "0" * 64
                elif fault == "secret":
                    data["Results"][0]["Secrets"] = [{"RuleID": "synthetic"}]
                elif fault == "new-HIGH":
                    data["Results"][0]["Vulnerabilities"] = [
                        {
                            "VulnerabilityID": "CVE-new",
                            "PkgName": "synthetic",
                            "InstalledVersion": "1",
                            "Severity": "HIGH",
                        }
                    ]
                elif fault is not None and fault.startswith("target-Go-"):
                    data["Results"][1]["Vulnerabilities"] = [
                        {
                            "VulnerabilityID": "CVE-2026-111943",
                            "PkgName": "stdlib",
                            "InstalledVersion": "v1.27.3" if current_epoch else "v1.27.2",
                            "Severity": fault.removeprefix("target-Go-"),
                        }
                    ]
            elif label == "current-known-vulnerable-control":
                cases = [
                    ("CVE-2026-84445", "google.golang.org/grpc@v1.83.1"),
                    ("CVE-2026-78669", "golang.org/x/net@v0.58.0"),
                    ("CVE-2026-78669", "stdlib@v1.26.8"),
                    ("CVE-2026-78667", "stdlib@v1.26.8"),
                    ("CVE-2026-97031", "stdlib@v1.26.8"),
                ]
                if current_epoch:
                    cases.append(("CVE-2026-111943", "stdlib@v1.26.8"))
                data = {
                    "SchemaVersion": 2,
                    "ArtifactType": "container_image",
                    "Metadata": {"ImageID": fetcher._ALERT_OLD_RUNTIME_CONFIG},
                    "Results": [
                        {
                            "Target": "bin/" + name,
                            "Class": "lang-pkgs",
                            "Type": "gobinary",
                            "Packages": [{"Name": "stdlib", "Version": "v1.26.8"}],
                            "Vulnerabilities": [
                                {
                                    "VulnerabilityID": cve,
                                    "PkgIdentifier": {"PURL": "pkg:golang/" + purl},
                                    "Severity": "HIGH",
                                }
                                for cve, purl in cases
                            ],
                        }
                        for name in ("alertmanager", "amtool")
                    ],
                }
                if fault == "old-missing":
                    data["Results"][0]["Vulnerabilities"].pop()
            else:
                positive = label == "current-secret-positive"
                data = {"SchemaVersion": 2, "ArtifactType": "filesystem", "ArtifactName": argv[-1]}
                if (
                    positive
                    and fault != "positive-missing"
                    or not positive
                    and fault == "negative-secret"
                ):
                    data["Results"] = [
                        {
                            "Target": "credentials.txt",
                            "Secrets": [{"RuleID": "github-pat", "Severity": "CRITICAL"}],
                        }
                    ]
                elif positive:
                    data["Results"] = []
            target.write_text(json.dumps(data))
            if fault == "DB-drift":
                (cache / "db/trivy.db").write_bytes(b"drift")
            self.records.append({"label": label, "exit": 0})
            return b""

    monkeypatch.setattr(transport, "Native", Native)
    args = Namespace(
        alertmanager_scanner=scanner, alertmanager_cache=cache, output_dir=tmp_path / "observation"
    )
    historical_target_observation = not current_epoch and fault in (
        "target-Go-UNKNOWN",
        "target-Go-LOW",
        "target-Go-MEDIUM",
    )
    succeeds = fault is None or historical_target_observation
    if succeeds:
        fetcher._alertmanager_live_security(args)
        assert forwarded == [("candidate", current_epoch), ("old_control", current_epoch)]
        assert [name for name in calls if name.startswith("current-")] == [
            "current-scanner-version",
            "current-candidate-full-supported",
            "current-known-vulnerable-control",
            "current-secret-positive",
            "current-secret-negative",
        ]
    else:
        with pytest.raises((RuntimeError, ValueError, OSError)) as observed:
            fetcher._alertmanager_live_security(args)
        if fault in ("target-Go-UNKNOWN", "target-Go-LOW", "target-Go-MEDIUM"):
            assert current_epoch and str(observed.value) == "AM_current_Go_CVE_still_present"
            assert forwarded == [("candidate", True)]
            assert "live-old-control-pull" not in calls
        elif fault in ("target-Go-HIGH", "target-Go-CRITICAL", "new-HIGH"):
            assert str(observed.value) == "AM_new_blocking_support_finding_HOLD"
        if fault in ("observation-write", "primary-and-observation"):
            assert timers[0] <= 5.0 and timers[-1] == 5.0
            assert not (args.output_dir / "security-observation.json").exists()
            if fault == "primary-and-observation":
                assert str(observed.value) == "synthetic scanner native exit2"
                assert (
                    "AM current security observation also failed: OSError"
                    in observed.value.__notes__
                )
            return
    record = json.loads((args.output_dir / "security-observation.json").read_bytes())
    assert (record.get("status") == "OBSERVED_CURRENT_SUPPORTED_INVENTORY_AND_FOUR_CONTROLS") is (
        succeeds
    )
    if historical_target_observation:
        assert record["candidate"]["findings"][0]["VulnerabilityID"] == "CVE-2026-111943"
    assert all(epoch is current_epoch for _, epoch in forwarded)
    if fault not in ("scanner-exit", "missing-report"):
        assert (
            args.output_dir / "evidence/current-candidate-full-supported.private.json"
        ).is_file()
    assert record["DB"] and record["scanner_sha256"]


def test_alertmanager_actual_caller_steps_fit_distinct_enclosing_budgets_and_retain_evidence() -> (
    None
):
    """Enumerate actual conditional source/native/scanner caps rather than borrowing another route's job."""
    workflow = _workflow(CD_WORKFLOW)
    env = workflow["env"]

    def minutes(step: dict[str, Any]) -> int:
        value = step.get("timeout-minutes")
        if isinstance(value, str):
            match = re.fullmatch(r"\$\{\{ fromJSON\(env\.(\w+)\) \}\}", value)
            assert match is not None, (step.get("name"), value)
            value = 40 if match[1] == "ALERTMANAGER_GENERIC_NATIVE_MINUTES" else int(env[match[1]])
        assert type(value) is int and value > 0, step.get("name")
        return value

    shared = _steps(_job(workflow, "prometheus-image-security-pr"))
    pr_only = {
        "Checkout immutable PR head Prometheus contracts",
        "Require fresh fixed Prometheus control checkout",
        "Checkout fixed trusted Prometheus control",
        "Remove fixed trusted Prometheus control checkout",
        "Require separately designated AM controller",
        "Checkout separately designated AM controller",
        "Remove designated AM controller after credential cleanup",
        "Select AM Python without dependency or SDK installation",
        "Install isolated AM host tools through the locked owner",
        "Verify isolated AM host import capability before effects",
        "Run full accepted AM native controls on this runner",
    }
    assert pr_only <= {step["name"] for step in shared}
    main_steps = [step for step in shared if step["name"] not in pr_only]
    assert sum(map(minutes, main_steps)) <= 285
    # Changed, historical and ordinary PRs all execute the fixed-control steps.
    excluded = {
        "Checkout immutable published Prometheus contracts",
        "Wait for the exact trusted Prometheus publisher",
    }
    assert sum(minutes(step) for step in shared if step["name"] not in excluded) <= 165
    assert sum(map(minutes, _steps(_job(workflow, "alertmanager-retained-candidate")))) <= 78
    assert sum(map(minutes, _steps(_job(workflow, "obs2a-checkpoint-native")))) <= 102
    assert (
        "ALERTMANAGER_CD_PR_JOB_TIMEOUT_MINUTES"
        in _job(workflow, "prometheus-image-security-pr")["timeout-minutes"]
    )
    trusted = _job(workflow, "prometheus-image-security-trusted")
    assert "ALERTMANAGER_CD_TRUSTED_JOB_TIMEOUT_MINUTES" in trusted["timeout-minutes"]
    assert trusted["env"]["PROMETHEUS_JOB_TIMEOUT_MINUTES"] == trusted["timeout-minutes"]
    for step in shared:
        if step["name"] in {
            "Require separately designated AM controller",
            "Checkout separately designated AM controller",
            "Run full accepted AM native controls on this runner",
        }:
            assert step["if"] == "github.event_name == 'pull_request'"
    retain = _named_step(shared, "Retain exact Prometheus consumer evidence")["with"]["path"]
    for suffix in (
        "/consumer-observation.json",
        "/native.stdout",
        "/native.stderr",
        "/github-read-evidence/",
        "/preparation/evidence/",
        "/security-observation.json",
    ):
        assert suffix in retain
    assert "/candidate.zip" not in retain and "/private/" not in retain
