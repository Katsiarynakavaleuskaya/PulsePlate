"""Fail-closed contracts for the hardened Caddy and staging digest lane."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import yaml

from scripts.ci.ci_risk_profile import build_risk_profile
from scripts.ci import check_docker_runtime_dependency_surface as caddy_surface
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
    from tests.test_deploy_contract_scripts import _historical_AM_scan_oracle

    monkeypatch.setattr(
        fetcher, "_ALERT_ACCEPTED_CANDIDATE", json.loads(json.dumps(fetcher._ALERT_HISTORICAL_C10))
    )
    monkeypatch.setattr(fetcher, "_ALERT_CURRENT_SCAN_ORACLE", _historical_AM_scan_oracle())


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
    "node:24.22.1-bookworm-slim@"
    "sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205"
)
CADDY_BASE = (
    "caddy:2.11.9-alpine@" "sha256:0bbb055bda6793c999bde78b1b5ce3e89f829fb031af2cf50056ea1246559fee"
)
EXPECTED_CADDY_BUILDER_STAGE = (
    "FROM golang:1.26.10-alpine3.23@sha256:0525c952defebc693cdaf62cdf43afa32be5a7f377e99260642ea19c240c708e AS caddy-build\n"
    "\n"
    "ENV CGO_ENABLED=0 \\\n"
    "    GOTOOLCHAIN=local \\\n"
    "    GOENV=off \\\n"
    "    GOWORK=off \\\n"
    '    GOFLAGS="" \\\n'
    '    GOEXPERIMENT="" \\\n'
    "    GOMAXPROCS=2 \\\n"
    "    GOPROXY=https://proxy.golang.org \\\n"
    "    GOSUMDB=sum.golang.org\n"
    "\n"
    "# The stock builder has no patch tool. Install only in this build stage.\n"
    "RUN apk add --no-cache git\n"
    "COPY patches/go-jose-v3.0.5-CVE-2026-116587.patch /opt/go-jose-v3.patch\n"
    "COPY patches/caddy_v3_compat_test.go /opt/caddy_v3_compat_test.go\n"
    "\n"
    "COPY patches/go1.26.10-http-connection-nominations.patch /opt/go1.26.10-http-connection-nominations.patch\n"
    "COPY patches/go_http_connection_nominations_test.go /opt/go_http_connection_nominations_test.go\n"
    "\n"
    "RUN --network=none set -eux; \\\n"
    "    set -o pipefail; \\\n"
    "    evidence=/caddy-build-evidence; \\\n"
    '    mkdir "$evidence"; \\\n'
    "    test \"$(sha256sum /usr/local/go/bin/go | cut -d' ' -f1)\" = 9c2a37ae5b21ba1d5a004bb9ab4d0c64de6fc5778e9d30487adccea62678b8b5; \\\n"
    "    echo '9beb880c561244794fda6176ac17f3f9c1690ae31fc26ac069afbf452e1c3f22  /opt/go1.26.10-http-connection-nominations.patch' | sha256sum -c -; \\\n"
    "    echo '2dc6f44b2e7a95a1b970cdbbcf70ddc532c35921c4b83ff80ca6e48b20a1c32e  /opt/go_http_connection_nominations_test.go' | sha256sum -c -; \\\n"
    '    verify_stdlib() { ( test ! -L "$1"; test -d "$1"; cd "$1"; test -z "$(find . -mindepth 1 ! -type d ! -type f -print)"; find . -type f -exec sha256sum {} + | LC_ALL=C sort > "$evidence/$2"; test "$(sha256sum "$evidence/$2" | cut -d\' \' -f1)" = "$3"; ); }; \\\n'
    "    verify_stdlib /usr/local/go stdlib-original-tree.sha256 e54472503fcedc70793baefd53d9ae2eee748610e190f99f533ae6ef7c3ecf64; \\\n"
    "    test ! -e /opt/go1.26.10-http-baseline; \\\n"
    "    test ! -L /opt/go1.26.10-http-baseline; \\\n"
    "    cp -R /usr/local/go /opt/go1.26.10-http-baseline; \\\n"
    "    cp /opt/go_http_connection_nominations_test.go /opt/go1.26.10-http-baseline/src/net/http/go_http_connection_nominations_test.go; \\\n"
    "    test ! -e /opt/go1.26.10-http-patched; \\\n"
    "    test ! -L /opt/go1.26.10-http-patched; \\\n"
    "    cp -R /usr/local/go /opt/go1.26.10-http-patched; \\\n"
    "    cp /opt/go_http_connection_nominations_test.go /opt/go1.26.10-http-patched/src/net/http/go_http_connection_nominations_test.go; \\\n"
    "    verify_stdlib /opt/go1.26.10-http-baseline stdlib-baseline-tree.sha256 aed4cf1ca75d78f74118dc8686cd0bdd6d017c1b8bb98e0f46c2ed859ad72a26; \\\n"
    "    echo '3e04744176d3cf5bef2827ab158b10aaeec3981ac5f4e7fb86e3dbf5f592eed7  /opt/go1.26.10-http-patched/src/net/http/transfer.go' | sha256sum -c -; \\\n"
    "    (cd /opt/go1.26.10-http-patched; env -i PATH=/usr/bin:/bin GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CEILING_DIRECTORIES=/opt /usr/bin/git apply --no-index --check --whitespace=error-all /opt/go1.26.10-http-connection-nominations.patch; env -i PATH=/usr/bin:/bin GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CEILING_DIRECTORIES=/opt /usr/bin/git apply --no-index --whitespace=error-all /opt/go1.26.10-http-connection-nominations.patch); \\\n"
    "    echo '0a19c32dab21d8c906795189b5c35da22551e0c2932a07b1fe64ac4559e70a01  /opt/go1.26.10-http-patched/src/net/http/transfer.go' | sha256sum -c -; \\\n"
    "    verify_stdlib /opt/go1.26.10-http-patched stdlib-patched-tree.sha256 afce6dcef776fcfe337fff1c5d4a3c68cd4729be7c27463d07e09fc7fafaa3f5; \\\n"
    '    sha256sum /opt/go1.26.10-http-connection-nominations.patch /opt/go_http_connection_nominations_test.go /usr/local/go/bin/go /usr/local/go/src/net/http/transfer.go /opt/go1.26.10-http-patched/src/net/http/transfer.go /usr/local/go/src/net/http/internal/ascii/print.go /usr/local/go/src/net/http/server.go /usr/local/go/src/net/textproto/reader.go /usr/local/go/src/net/textproto/textproto.go /usr/local/go/src/vendor/golang.org/x/net/http/httpguts/httplex.go | LC_ALL=C sort > "$evidence/stdlib-inputs.sha256"; \\\n'
    '    : > "$evidence/stdlib-test-commands.txt"; \\\n'
    '    : > "$evidence/stdlib-test-inventory.txt"; \\\n'
    "    test ! -e /opt/caddy-stdlib-baseline-cache; \\\n"
    "    mkdir -m 700 /opt/caddy-stdlib-baseline-cache; \\\n"
    "    test ! -e /opt/caddy-stdlib-patched-cache; \\\n"
    "    mkdir -m 700 /opt/caddy-stdlib-patched-cache; \\\n"
    "    printf 'BASELINE_NATIVE_LIST\\n' >> \"$evidence/stdlib-test-inventory.txt\"; \\\n"
    '    ( export GOROOT=/opt/go1.26.10-http-baseline GOCACHE=/opt/caddy-stdlib-baseline-cache GOPROXY=off GOSUMDB=off; test "$(go env GOROOT)" = "$GOROOT"; test "$(go env GOCACHE)" = "$GOCACHE"; if /usr/local/go/bin/go test -count=1 -p=2 -list \'^(TestReadResponse|TestWriteResponse|TestReadResponseErrors|TestResponseWritesOnlySingleConnectionClose|TestReadResponseCloseInMiddle|TestResponseContentLengthShortBody|TestTransportConnectionCloseOnResponse|TestTransportConnectionCloseOnRequest|TestTransportRespectRequestWantsClose|TestTransportReadToEndReusesConn|TestIssue3644|TestTransportResponseBodyWritableOnProtocolSwitch|TestPPHTTPConnectionBaseline|TestPPHTTPConnectionSurvivors|TestPPHTTPConnectionFieldNameCase|TestPPHTTPBoundaryControls|TestPPHTTPFramingControls|TestPPHTTPMalformedReaderControls|TestPPHTTPMalformedAcceptedParity|TestPPHTTPResponseWriteRoundTrip|TestPPHTTPTransportCloseNominees|TestPPHTTPTransportPersistenceOptions|TestPPHTTPPersistenceOptions|TestPPHTTPPersistenceBoundaryControls|TestPPHTTPPersistenceWriteRoundTrip|TestReverseProxyStripHeadersPresentInConnection)$\' net/http net/http/httputil >> "$evidence/stdlib-test-inventory.txt" 2>&1; then native_status=0; else native_status=$?; fi; printf \'%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n\' baseline-list "$native_status" "$GOROOT" "$GOCACHE" "$GOPROXY" "$GOSUMDB" \'["/usr/local/go/bin/go","test","-count=1","-p=2","-list","^(TestReadResponse|TestWriteResponse|TestReadResponseErrors|TestResponseWritesOnlySingleConnectionClose|TestReadResponseCloseInMiddle|TestResponseContentLengthShortBody|TestTransportConnectionCloseOnResponse|TestTransportConnectionCloseOnRequest|TestTransportRespectRequestWantsClose|TestTransportReadToEndReusesConn|TestIssue3644|TestTransportResponseBodyWritableOnProtocolSwitch|TestPPHTTPConnectionBaseline|TestPPHTTPConnectionSurvivors|TestPPHTTPConnectionFieldNameCase|TestPPHTTPBoundaryControls|TestPPHTTPFramingControls|TestPPHTTPMalformedReaderControls|TestPPHTTPMalformedAcceptedParity|TestPPHTTPResponseWriteRoundTrip|TestPPHTTPTransportCloseNominees|TestPPHTTPTransportPersistenceOptions|TestPPHTTPPersistenceOptions|TestPPHTTPPersistenceBoundaryControls|TestPPHTTPPersistenceWriteRoundTrip|TestReverseProxyStripHeadersPresentInConnection)$","net/http","net/http/httputil"]\' >> "$evidence/stdlib-test-commands.txt"; if test "$native_status" != 0; then cat "$evidence/stdlib-test-inventory.txt"; exit 1; fi; ); \\\n'
    '    ( export GOROOT=/opt/go1.26.10-http-baseline GOCACHE=/opt/caddy-stdlib-baseline-cache GOPROXY=off GOSUMDB=off; test "$(go env GOROOT)" = "$GOROOT"; test "$(go env GOCACHE)" = "$GOCACHE"; if /usr/local/go/bin/go test -count=1 -p=2 -parallel=2 -timeout=90s -json -run \'^(TestReadResponse|TestWriteResponse|TestReadResponseErrors|TestResponseWritesOnlySingleConnectionClose|TestReadResponseCloseInMiddle|TestResponseContentLengthShortBody|TestTransportConnectionCloseOnResponse|TestTransportConnectionCloseOnRequest|TestTransportRespectRequestWantsClose|TestTransportReadToEndReusesConn|TestIssue3644|TestTransportResponseBodyWritableOnProtocolSwitch|TestPPHTTPBoundaryControls|TestPPHTTPMalformedAcceptedParity|TestPPHTTPMalformedReaderControls|TestPPHTTPPersistenceBoundaryControls|TestReverseProxyStripHeadersPresentInConnection)$\' net/http net/http/httputil > "$evidence/stdlib-baseline-controls.jsonl" 2>&1; then native_status=0; else native_status=$?; fi; printf \'%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n\' baseline-controls "$native_status" "$GOROOT" "$GOCACHE" "$GOPROXY" "$GOSUMDB" \'["/usr/local/go/bin/go","test","-count=1","-p=2","-parallel=2","-timeout=90s","-json","-run","^(TestReadResponse|TestWriteResponse|TestReadResponseErrors|TestResponseWritesOnlySingleConnectionClose|TestReadResponseCloseInMiddle|TestResponseContentLengthShortBody|TestTransportConnectionCloseOnResponse|TestTransportConnectionCloseOnRequest|TestTransportRespectRequestWantsClose|TestTransportReadToEndReusesConn|TestIssue3644|TestTransportResponseBodyWritableOnProtocolSwitch|TestPPHTTPBoundaryControls|TestPPHTTPMalformedAcceptedParity|TestPPHTTPMalformedReaderControls|TestPPHTTPPersistenceBoundaryControls|TestReverseProxyStripHeadersPresentInConnection)$","net/http","net/http/httputil"]\' >> "$evidence/stdlib-test-commands.txt"; if test "$native_status" != 0; then cat "$evidence/stdlib-baseline-controls.jsonl"; exit 1; fi; ); \\\n'
    '    ( export GOROOT=/opt/go1.26.10-http-baseline GOCACHE=/opt/caddy-stdlib-baseline-cache GOPROXY=off GOSUMDB=off; test "$(go env GOROOT)" = "$GOROOT"; test "$(go env GOCACHE)" = "$GOCACHE"; if /usr/local/go/bin/go test -count=1 -p=2 -parallel=2 -timeout=90s -json -run \'^(TestPPHTTPConnectionBaseline)$\' net/http > "$evidence/stdlib-baseline-red.jsonl" 2>&1; then native_status=0; else native_status=$?; fi; printf \'%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n\' baseline-red "$native_status" "$GOROOT" "$GOCACHE" "$GOPROXY" "$GOSUMDB" \'["/usr/local/go/bin/go","test","-count=1","-p=2","-parallel=2","-timeout=90s","-json","-run","^(TestPPHTTPConnectionBaseline)$","net/http"]\' >> "$evidence/stdlib-test-commands.txt"; if test "$native_status" != 1; then cat "$evidence/stdlib-baseline-red.jsonl"; exit 1; fi; ); \\\n'
    "    grep -F 'PP_BASELINE_SETUP_BODY_CLOSE_OK' \"$evidence/stdlib-baseline-red.jsonl\"; \\\n"
    "    grep -F 'PP_EXPECTED_NOMINATION_MISMATCH' \"$evidence/stdlib-baseline-red.jsonl\"; \\\n"
    "    printf 'PATCHED_NATIVE_LIST\\n' >> \"$evidence/stdlib-test-inventory.txt\"; \\\n"
    '    ( export GOROOT=/opt/go1.26.10-http-patched GOCACHE=/opt/caddy-stdlib-patched-cache GOPROXY=off GOSUMDB=off; test "$(go env GOROOT)" = "$GOROOT"; test "$(go env GOCACHE)" = "$GOCACHE"; if /usr/local/go/bin/go test -count=1 -p=2 -list \'^(TestReadResponse|TestWriteResponse|TestReadResponseErrors|TestResponseWritesOnlySingleConnectionClose|TestReadResponseCloseInMiddle|TestResponseContentLengthShortBody|TestTransportConnectionCloseOnResponse|TestTransportConnectionCloseOnRequest|TestTransportRespectRequestWantsClose|TestTransportReadToEndReusesConn|TestIssue3644|TestTransportResponseBodyWritableOnProtocolSwitch|TestPPHTTPConnectionBaseline|TestPPHTTPConnectionSurvivors|TestPPHTTPConnectionFieldNameCase|TestPPHTTPBoundaryControls|TestPPHTTPFramingControls|TestPPHTTPMalformedReaderControls|TestPPHTTPMalformedAcceptedParity|TestPPHTTPResponseWriteRoundTrip|TestPPHTTPTransportCloseNominees|TestPPHTTPTransportPersistenceOptions|TestPPHTTPPersistenceOptions|TestPPHTTPPersistenceBoundaryControls|TestPPHTTPPersistenceWriteRoundTrip|TestReverseProxyStripHeadersPresentInConnection)$\' net/http net/http/httputil >> "$evidence/stdlib-test-inventory.txt" 2>&1; then native_status=0; else native_status=$?; fi; printf \'%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n\' patched-list "$native_status" "$GOROOT" "$GOCACHE" "$GOPROXY" "$GOSUMDB" \'["/usr/local/go/bin/go","test","-count=1","-p=2","-list","^(TestReadResponse|TestWriteResponse|TestReadResponseErrors|TestResponseWritesOnlySingleConnectionClose|TestReadResponseCloseInMiddle|TestResponseContentLengthShortBody|TestTransportConnectionCloseOnResponse|TestTransportConnectionCloseOnRequest|TestTransportRespectRequestWantsClose|TestTransportReadToEndReusesConn|TestIssue3644|TestTransportResponseBodyWritableOnProtocolSwitch|TestPPHTTPConnectionBaseline|TestPPHTTPConnectionSurvivors|TestPPHTTPConnectionFieldNameCase|TestPPHTTPBoundaryControls|TestPPHTTPFramingControls|TestPPHTTPMalformedReaderControls|TestPPHTTPMalformedAcceptedParity|TestPPHTTPResponseWriteRoundTrip|TestPPHTTPTransportCloseNominees|TestPPHTTPTransportPersistenceOptions|TestPPHTTPPersistenceOptions|TestPPHTTPPersistenceBoundaryControls|TestPPHTTPPersistenceWriteRoundTrip|TestReverseProxyStripHeadersPresentInConnection)$","net/http","net/http/httputil"]\' >> "$evidence/stdlib-test-commands.txt"; if test "$native_status" != 0; then cat "$evidence/stdlib-test-inventory.txt"; exit 1; fi; ); \\\n'
    '    ( export GOROOT=/opt/go1.26.10-http-patched GOCACHE=/opt/caddy-stdlib-patched-cache GOPROXY=off GOSUMDB=off; test "$(go env GOROOT)" = "$GOROOT"; test "$(go env GOCACHE)" = "$GOCACHE"; if /usr/local/go/bin/go test -count=1 -p=2 -parallel=2 -timeout=90s -json -run \'^(TestReadResponse|TestWriteResponse|TestReadResponseErrors|TestResponseWritesOnlySingleConnectionClose|TestReadResponseCloseInMiddle|TestResponseContentLengthShortBody|TestTransportConnectionCloseOnResponse|TestTransportConnectionCloseOnRequest|TestTransportRespectRequestWantsClose|TestTransportReadToEndReusesConn|TestIssue3644|TestTransportResponseBodyWritableOnProtocolSwitch|TestPPHTTPConnectionBaseline|TestPPHTTPConnectionSurvivors|TestPPHTTPConnectionFieldNameCase|TestPPHTTPBoundaryControls|TestPPHTTPFramingControls|TestPPHTTPMalformedReaderControls|TestPPHTTPMalformedAcceptedParity|TestPPHTTPResponseWriteRoundTrip|TestPPHTTPTransportCloseNominees|TestPPHTTPTransportPersistenceOptions|TestPPHTTPPersistenceOptions|TestPPHTTPPersistenceBoundaryControls|TestPPHTTPPersistenceWriteRoundTrip|TestReverseProxyStripHeadersPresentInConnection)$\' net/http net/http/httputil > "$evidence/stdlib-patched-tests.jsonl" 2>&1; then native_status=0; else native_status=$?; fi; printf \'%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n\' patched-tests "$native_status" "$GOROOT" "$GOCACHE" "$GOPROXY" "$GOSUMDB" \'["/usr/local/go/bin/go","test","-count=1","-p=2","-parallel=2","-timeout=90s","-json","-run","^(TestReadResponse|TestWriteResponse|TestReadResponseErrors|TestResponseWritesOnlySingleConnectionClose|TestReadResponseCloseInMiddle|TestResponseContentLengthShortBody|TestTransportConnectionCloseOnResponse|TestTransportConnectionCloseOnRequest|TestTransportRespectRequestWantsClose|TestTransportReadToEndReusesConn|TestIssue3644|TestTransportResponseBodyWritableOnProtocolSwitch|TestPPHTTPConnectionBaseline|TestPPHTTPConnectionSurvivors|TestPPHTTPConnectionFieldNameCase|TestPPHTTPBoundaryControls|TestPPHTTPFramingControls|TestPPHTTPMalformedReaderControls|TestPPHTTPMalformedAcceptedParity|TestPPHTTPResponseWriteRoundTrip|TestPPHTTPTransportCloseNominees|TestPPHTTPTransportPersistenceOptions|TestPPHTTPPersistenceOptions|TestPPHTTPPersistenceBoundaryControls|TestPPHTTPPersistenceWriteRoundTrip|TestReverseProxyStripHeadersPresentInConnection)$","net/http","net/http/httputil"]\' >> "$evidence/stdlib-test-commands.txt"; if test "$native_status" != 0; then cat "$evidence/stdlib-patched-tests.jsonl"; exit 1; fi; ); \\\n'
    "    verify_stdlib /opt/go1.26.10-http-baseline stdlib-baseline-tree.sha256 aed4cf1ca75d78f74118dc8686cd0bdd6d017c1b8bb98e0f46c2ed859ad72a26; \\\n"
    "    verify_stdlib /opt/go1.26.10-http-patched stdlib-post-tests-tree.sha256 afce6dcef776fcfe337fff1c5d4a3c68cd4729be7c27463d07e09fc7fafaa3f5; \\\n"
    "    rm -rf /opt/go1.26.10-http-baseline /opt/caddy-stdlib-baseline-cache\n"
    "\n"
    "ENV GOROOT=/opt/go1.26.10-http-patched \\\n"
    "    GOCACHE=/opt/caddy-stdlib-patched-cache\n"
    "\n"
    "RUN set -eux; \\\n"
    "    set -o pipefail; \\\n"
    '    build_dir="$(mktemp -d)"; \\\n'
    '    cd "$build_dir"; \\\n'
    "    go mod init pulseplate.local/caddy-build; \\\n"
    "    go get github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.4; \\\n"
    "    go get google.golang.org/grpc@v1.83.2; \\\n"
    "    go get golang.org/x/crypto@v0.55.0; \\\n"
    "    go get golang.org/x/net@v0.60.0; \\\n"
    "    go get github.com/klauspost/compress@v1.18.7; \\\n"
    "    go get github.com/go-jose/go-jose/v4@v4.1.6; \\\n"
    "    go mod download all; \\\n"
    "    go mod verify; \\\n"
    "    go get github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.9; \\\n"
    "    go mod download all; \\\n"
    "    go mod verify; \\\n"
    "    echo '40a8c29bde80ddaaf323030a9631453d905b1deafc4eb909c0b2b1c43bd2965d  go.mod' | sha256sum -c -; \\\n"
    "    echo 'bc1def232f1f0a8d205b39c38fa9b0159d481c05f90933bc975659ec0c0317c8  go.sum' | sha256sum -c -; \\\n"
    "    go get golang.org/x/net@v0.62.0; \\\n"
    "    cp go.mod /tmp/caddy-xnet062-postget.mod; \\\n"
    "    cp go.sum /tmp/caddy-xnet062-postget.sum; \\\n"
    "    go mod download all; \\\n"
    "    go mod verify; \\\n"
    "    cmp go.mod /tmp/caddy-xnet062-postget.mod; \\\n"
    "    echo 'f5d9289fa0e27604a936ed5e35368db876398dac62154b9a6af9d0d2a891f7d9  /tmp/caddy-xnet062-postget.sum' | sha256sum -c -; \\\n"
    "    echo 'f06331d8fba11ae7ac7ba36f80198bb9ca7c5ac22df4deb7011ab91a4d52f596  go.mod' | sha256sum -c -; \\\n"
    "    echo 'be8f44f7e591bcaa54412fe5f3061235596be2faf9bd3f5fdece0106fea45338  go.sum' | sha256sum -c -; \\\n"
    "    test -z \"$(go list -m -f '{{if .Replace}}{{.Path}} => {{.Replace.Path}}{{end}}' all)\"; \\\n"
    "    evidence=/caddy-build-evidence; \\\n"
    '    test -d "$evidence"; \\\n'
    '    git_bin="$(command -v git)"; \\\n'
    '    test "$git_bin" = /usr/bin/git; \\\n'
    '    "$git_bin" --version > "$evidence/patch-tool.txt"; \\\n'
    '    sha256sum "$git_bin" >> "$evidence/patch-tool.txt"; \\\n'
    '    sha256sum /opt/go-jose-v3.patch /opt/caddy_v3_compat_test.go > "$evidence/inputs.sha256"; \\\n'
    "    echo '628d25c62a2141fb35bea13003483a22f277b3b2c9ba319ff5a53b7b591e7de6  /opt/caddy_v3_compat_test.go' | sha256sum -c -; \\\n"
    "    echo 'f0e1b6f4791089dfebbc9a742533af650268e87bffec09847190e59da04aad27  /opt/go-jose-v3.patch' | sha256sum -c -; \\\n"
    "    verify_jose_source() { ( \\\n"
    '      if test -L "$1" || test ! -d "$1"; then echo caddy_source_root >&2; exit 1; fi; \\\n'
    '      cd "$1"; \\\n'
    '      if test -n "$(find . -mindepth 1 ! -type d ! -type f -print)"; then echo caddy_source_nonregular >&2; exit 1; fi; \\\n'
    "      if test -n \"$(find . -mindepth 1 -print | LC_ALL=C awk '$0 !~ /^\\.\\/[A-Za-z0-9_.\\/-]+$/ { print }')\"; then echo caddy_source_path >&2; exit 1; fi; \\\n"
    '      if test "$(find . -type f | wc -l | tr -d \'[:space:]\')" != "$2"; then echo caddy_source_count >&2; exit 1; fi; \\\n'
    '      find . -type f -exec sha256sum {} + | LC_ALL=C sort > "$evidence/$4-tree.sha256"; \\\n'
    '      if test "$(sha256sum "$evidence/$4-tree.sha256" | cut -d\' \' -f1)" != "$3"; then echo caddy_source_digest >&2; exit 1; fi; \\\n'
    "    ); }; \\\n"
    "    echo '4e7e6b60541ab03bd402e573fc2c1264297e661726c5f53529ca14ae58625a27  '$(go env GOMODCACHE)'/cache/download/github.com/go-jose/go-jose/v3/@v/v3.0.5.zip' | sha256sum -c -; \\\n"
    "    original_tree=1c0d532bafdf2a7de4fea465082117f97e6e8bcf31e1704203f838a873901ce1; \\\n"
    "    patched_tree=e71a63d7a08abecf4c3f2f72c41c1f469c097d853eafe854fdb6e782a70e1065; \\\n"
    "    test \"$(go list -m -f '{{.Version}}' github.com/go-jose/go-jose/v3)\" = v3.0.5; \\\n"
    "    test \"$(go list -m -f '{{.Sum}}' github.com/go-jose/go-jose/v3)\" = 'h1:BLLJWbC4nMZOfuPVxoZIxeYsn6Nl2r1fITaJ78UQlVQ='; \\\n"
    "    original_dir=\"$(go list -m -f '{{.Dir}}' github.com/go-jose/go-jose/v3)\"; \\\n"
    '    verify_jose_source "$original_dir" 71 "$original_tree" original; \\\n'
    "    test ! -e /opt/go-jose-v3.0.5-patched; test ! -L /opt/go-jose-v3.0.5-patched; \\\n"
    '    cp -R "$original_dir" /opt/go-jose-v3.0.5-patched; \\\n'
    "    chmod -R u+w /opt/go-jose-v3.0.5-patched; \\\n"
    '    verify_jose_source /opt/go-jose-v3.0.5-patched 71 "$original_tree" copied; \\\n'
    "    (cd /opt/go-jose-v3.0.5-patched; \\\n"
    '      env -i PATH=/usr/bin:/bin GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CEILING_DIRECTORIES=/opt "$git_bin" apply --no-index --check --whitespace=error-all /opt/go-jose-v3.patch; \\\n'
    '      env -i PATH=/usr/bin:/bin GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CEILING_DIRECTORIES=/opt "$git_bin" apply --no-index --whitespace=error-all /opt/go-jose-v3.patch); \\\n'
    '    verify_jose_source /opt/go-jose-v3.0.5-patched 72 "$patched_tree" patched; \\\n'
    "    (cd /opt/go-jose-v3.0.5-patched; \\\n"
    "      go mod download; \\\n"
    "      go mod verify; \\\n"
    '      if go test -mod=readonly -count=1 -parallel=2 -timeout=300s -json ./... > "$evidence/jose-tests.jsonl" 2>&1; then :; else cat "$evidence/jose-tests.jsonl"; exit 1; fi); \\\n'
    '    verify_jose_source /opt/go-jose-v3.0.5-patched 72 "$patched_tree" post-unit; \\\n'
    "    go mod edit -replace=github.com/go-jose/go-jose/v3@v3.0.5=/opt/go-jose-v3.0.5-patched; \\\n"
    '    go list -mod=readonly -m -json all > "$evidence/modules.json"; \\\n'
    '    go mod graph > "$evidence/module-graph.txt"; \\\n'
    "    test \"$(go list -mod=readonly -m -f '{{if .Replace}}{{.Path}}@{{.Version}}=>{{.Replace.Path}}@{{.Replace.Version}}{{end}}' all | awk 'NF')\" = 'github.com/go-jose/go-jose/v3@v3.0.5=>/opt/go-jose-v3.0.5-patched@'; \\\n"
    "    test \"$(go list -mod=readonly -m -f '{{.Version}}' go.step.sm/crypto)\" = v0.91.0; \\\n"
    "    test \"$(go list -mod=readonly -m -f '{{.Version}}' github.com/smallstep/certificates)\" = v0.30.2; \\\n"
    "    mkdir compat; \\\n"
    "    cp /opt/caddy_v3_compat_test.go compat/caddy_v3_compat_test.go; \\\n"
    '    sha256sum go.mod go.sum > "$evidence/build-module.sha256"; \\\n'
    '    if go test -mod=readonly -count=1 -parallel=2 -timeout=300s -json ./compat > "$evidence/compat-tests.jsonl" 2>&1; then :; else cat "$evidence/compat-tests.jsonl"; exit 1; fi; \\\n'
    '    go list -mod=readonly -deps -json github.com/caddyserver/caddy/v2/cmd/caddy > "$evidence/packages.json"; \\\n'
    '    go list -mod=readonly -deps -f \'{{.ImportPath}}|{{.Dir}}|{{join .Imports " "}}\' github.com/caddyserver/caddy/v2/cmd/caddy > "$evidence/import-graph.txt"; \\\n'
    "    test \"$(go list -mod=readonly -deps -f '{{if eq .ImportPath \"github.com/go-jose/go-jose/v3\"}}{{.Dir}}{{end}}' github.com/caddyserver/caddy/v2/cmd/caddy | awk 'NF')\" = /opt/go-jose-v3.0.5-patched; \\\n"
    '    go list -m -f \'{{if or (eq .Path "github.com/caddyserver/caddy/v2") (eq .Path "github.com/go-jose/go-jose/v3") (eq .Path "github.com/go-jose/go-jose/v4") (eq .Path "github.com/klauspost/compress") (eq .Path "google.golang.org/grpc") (eq .Path "golang.org/x/crypto") (eq .Path "golang.org/x/mod") (eq .Path "golang.org/x/net") (eq .Path "golang.org/x/sync") (eq .Path "golang.org/x/sys") (eq .Path "golang.org/x/telemetry") (eq .Path "golang.org/x/term") (eq .Path "golang.org/x/text") (eq .Path "golang.org/x/tools")}}{{.Path}} {{.Version}}{{end}}\' all \\\n'
    "      | awk 'NF' \\\n"
    "      | LC_ALL=C sort > /tmp/caddy-governed-graph; \\\n"
    "    printf '%s\\n' \\\n"
    "      'github.com/caddyserver/caddy/v2 v2.11.9' \\\n"
    "      'github.com/go-jose/go-jose/v3 v3.0.5' \\\n"
    "      'github.com/go-jose/go-jose/v4 v4.1.6' \\\n"
    "      'github.com/klauspost/compress v1.20.1' \\\n"
    "      'golang.org/x/crypto v0.58.0' \\\n"
    "      'golang.org/x/mod v0.41.0' \\\n"
    "      'golang.org/x/net v0.62.0' \\\n"
    "      'golang.org/x/sync v0.24.0' \\\n"
    "      'golang.org/x/sys v0.49.0' \\\n"
    "      'golang.org/x/telemetry v0.0.0-20260924152758-ed294f943157' \\\n"
    "      'golang.org/x/term v0.47.0' \\\n"
    "      'golang.org/x/text v0.43.0' \\\n"
    "      'golang.org/x/tools v0.51.0' \\\n"
    "      'google.golang.org/grpc v1.83.2' \\\n"
    "      | LC_ALL=C sort > /tmp/caddy-expected-graph; \\\n"
    "    test \"$(wc -l < /tmp/caddy-governed-graph | tr -d '[:space:]')\" = '14'; \\\n"
    "    cmp /tmp/caddy-expected-graph /tmp/caddy-governed-graph; \\\n"
    "    go build -mod=readonly -trimpath \\\n"
    "      -ldflags '-X github.com/caddyserver/caddy/v2.CustomVersion=v2.11.9' \\\n"
    "      -o /go/bin/caddy \\\n"
    "      github.com/caddyserver/caddy/v2/cmd/caddy; \\\n"
    "    /go/bin/caddy version; \\\n"
    "    go version -m /go/bin/caddy > /tmp/caddy-binary-metadata; \\\n"
    "    cat /tmp/caddy-binary-metadata; \\\n"
    '    test "$(awk \'$1 == "dep" { dependency=$2 "@" $3 } $1 == "=>" { print dependency "=>" $2 "@" $3 }\' /tmp/caddy-binary-metadata)" = \'github.com/go-jose/go-jose/v3@v3.0.5=>/opt/go-jose-v3.0.5-patched@(devel)\'; \\\n'
    '    awk \'$1 == "mod" && $2 == "github.com/caddyserver/caddy/v2" { print $1, $2, $3 } $1 == "dep" && ($2 == "github.com/go-jose/go-jose/v3" || $2 == "github.com/go-jose/go-jose/v4" || $2 == "github.com/klauspost/compress" || $2 == "google.golang.org/grpc" || $2 == "golang.org/x/crypto" || $2 == "golang.org/x/net" || $2 == "golang.org/x/sync" || $2 == "golang.org/x/sys" || $2 == "golang.org/x/term" || $2 == "golang.org/x/text") { print $1, $2, $3 }\' /tmp/caddy-binary-metadata \\\n'
    "      | LC_ALL=C sort > /tmp/caddy-governed-binary; \\\n"
    "    printf '%s\\n' \\\n"
    "      'mod github.com/caddyserver/caddy/v2 v2.11.9' \\\n"
    "      'dep github.com/go-jose/go-jose/v3 v3.0.5' \\\n"
    "      'dep github.com/go-jose/go-jose/v4 v4.1.6' \\\n"
    "      'dep github.com/klauspost/compress v1.20.1' \\\n"
    "      'dep golang.org/x/crypto v0.58.0' \\\n"
    "      'dep golang.org/x/net v0.62.0' \\\n"
    "      'dep golang.org/x/sync v0.24.0' \\\n"
    "      'dep golang.org/x/sys v0.49.0' \\\n"
    "      'dep golang.org/x/term v0.47.0' \\\n"
    "      'dep golang.org/x/text v0.43.0' \\\n"
    "      'dep google.golang.org/grpc v1.83.2' \\\n"
    "      | LC_ALL=C sort > /tmp/caddy-expected-binary; \\\n"
    "    test \"$(wc -l < /tmp/caddy-governed-binary | tr -d '[:space:]')\" = '11'; \\\n"
    "    cmp /tmp/caddy-expected-binary /tmp/caddy-governed-binary; \\\n"
    '    sha256sum -c "$evidence/build-module.sha256"; \\\n'
    '    verify_jose_source /opt/go-jose-v3.0.5-patched 72 "$patched_tree" post-build; \\\n'
    '    verify_jose_source "$original_dir" 71 "$original_tree" original-post-build; \\\n'
    '    verify_stdlib() { ( test ! -L "$1"; test -d "$1"; cd "$1"; test -z "$(find . -mindepth 1 ! -type d ! -type f -print)"; find . -type f -exec sha256sum {} + | LC_ALL=C sort > "$evidence/$2"; test "$(sha256sum "$evidence/$2" | cut -d\' \' -f1)" = "$3"; ); }; \\\n'
    '    verify_stdlib "$GOROOT" stdlib-post-build-tree.sha256 afce6dcef776fcfe337fff1c5d4a3c68cd4729be7c27463d07e09fc7fafaa3f5; \\\n'
    "    verify_stdlib /usr/local/go stdlib-original-post-build-tree.sha256 e54472503fcedc70793baefd53d9ae2eee748610e190f99f533ae6ef7c3ecf64; \\\n"
    '    cp /tmp/caddy-binary-metadata "$evidence/build-info.txt"; \\\n'
    '    sha256sum /go/bin/caddy > "$evidence/binary.sha256"; \\\n'
    '    rm "$evidence/packages.json"; \\\n'
    "    total_bytes=0; \\\n"
    "    for name in patch-tool.txt inputs.sha256 original-tree.sha256 copied-tree.sha256 patched-tree.sha256 post-unit-tree.sha256 post-build-tree.sha256 original-post-build-tree.sha256 jose-tests.jsonl compat-tests.jsonl modules.json module-graph.txt import-graph.txt build-module.sha256 build-info.txt binary.sha256; do \\\n"
    '      test -f "$evidence/$name"; \\\n'
    '      bytes="$(wc -c < "$evidence/$name")"; \\\n'
    '      test "$bytes" -gt 0; test "$bytes" -le 2097152; \\\n'
    "      total_bytes=$((total_bytes + bytes)); \\\n"
    "    done; \\\n"
    '    test "$total_bytes" -le 8388608; \\\n'
    "    stdlib_bytes=0; \\\n"
    "    for name in stdlib-inputs.sha256 stdlib-original-tree.sha256 stdlib-baseline-tree.sha256 stdlib-patched-tree.sha256 stdlib-post-tests-tree.sha256 stdlib-post-build-tree.sha256 stdlib-original-post-build-tree.sha256 stdlib-baseline-red.jsonl stdlib-baseline-controls.jsonl stdlib-patched-tests.jsonl stdlib-test-inventory.txt stdlib-test-commands.txt; do \\\n"
    '      test -f "$evidence/$name"; bytes="$(wc -c < "$evidence/$name")"; limit=2097152; \\\n'
    '      case "$name" in stdlib-inputs.sha256) limit=4096 ;; stdlib-test-inventory.txt) limit=65536 ;; stdlib-test-commands.txt) limit=16384 ;; esac; \\\n'
    '      test "$bytes" -gt 0; test "$bytes" -le "$limit"; stdlib_bytes=$((stdlib_bytes + bytes)); \\\n'
    "    done; \\\n"
    '    test "$stdlib_bytes" -le 16777216; test "$((total_bytes + stdlib_bytes))" -le 25165824; \\\n'
    '    test "$(find "$evidence" -type f | wc -l | tr -d \'[:space:]\')" = 28; \\\n'
    "    rm -rf /opt/caddy-stdlib-patched-cache; \\\n"
    "    rm -f \\\n"
    "      /tmp/caddy-binary-metadata \\\n"
    "      /tmp/caddy-expected-binary \\\n"
    "      /tmp/caddy-expected-graph \\\n"
    "      /tmp/caddy-governed-binary \\\n"
    "      /tmp/caddy-governed-graph; \\\n"
    '    rm -rf "$build_dir"\n'
    "\n"
)
EXPECTED_CADDY_FINAL_STAGE = (
    "\n".join(
        (
            f"FROM {CADDY_BASE}",
            "",
            'LABEL org.opencontainers.image.title="PulsePlate Caddy SPA shell" \\',
            (
                '      org.opencontainers.image.description="Caddy 2.11.9 rebuilt with '
                'Go 1.26.10 and PulsePlate frontend assets"'
            ),
            "",
            "# Compare the standard module surface before replacing the upstream binary.",
            "# Package versions and build metadata are intentionally excluded from parity.",
            "# Public synthetic build evidence; cached-stage output is not fresh test execution.",
            "COPY --from=caddy-build /caddy-build-evidence /usr/share/pulseplate-caddy-build",
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
            '      "musl>=1.2.6-r3" \\',
            '      "musl-utils>=1.2.6-r3" \\',
            '      "ca-certificates>=20261020-r0" \\',
            '      "ca-certificates-bundle>=20261020-r0" \\',
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
                '    caddy version | awk \'NR == 1 && $1 == "v2.11.9" { found=1 } '
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
    assert "GOPROXY=https://proxy.golang.org" in text
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
    assert text.index(crypto_get) < text.index(net_get) < text.index(compress_get)
    jose_get = "go get github.com/go-jose/go-jose/v4@v4.1.6"
    assert text.count(jose_get) == 1
    assert text.index(compress_get) < text.index(jose_get) < text.index("go mod download all")
    assert "go mod download all" in text
    assert "go mod verify" in text
    upgrade = "go get github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.9"
    assert text.count(upgrade) == 1
    assert (
        text.index(jose_get)
        < text.index("go mod download all")
        < text.index("go mod verify")
        < text.index(upgrade)
    )
    assert (
        text.index(upgrade)
        < text.index("go mod download all", text.index(upgrade))
        < text.index("go mod verify", text.index(upgrade))
    )
    xnet_get = "go get golang.org/x/net@v0.62.0"
    assert text.count(xnet_get) == 1
    xnet_start = text.index(xnet_get)
    assert text.index("go mod verify", text.index(upgrade)) < xnet_start
    assert (
        xnet_start
        < text.index("go mod download all", xnet_start)
        < text.index("go mod verify", xnet_start)
    )
    assert '"musl>=1.2.6-r3"' in text and '"musl-utils>=1.2.6-r3"' in text
    assert '"GOPROXY=https://proxy.golang.org,direct"' not in text
    for exact_graph_identity in (
        "github.com/caddyserver/caddy/v2 v2.11.9",
        "github.com/go-jose/go-jose/v3 v3.0.5",
        "github.com/go-jose/go-jose/v4 v4.1.6",
        "google.golang.org/grpc v1.83.2",
        "golang.org/x/crypto v0.58.0",
        "golang.org/x/mod v0.41.0",
        "golang.org/x/net v0.62.0",
        "golang.org/x/sync v0.24.0",
        "golang.org/x/sys v0.49.0",
        "golang.org/x/telemetry v0.0.0-20260924152758-ed294f943157",
        "golang.org/x/term v0.47.0",
        "golang.org/x/text v0.43.0",
        "golang.org/x/tools v0.51.0",
    ):
        assert f"'{exact_graph_identity}'" in text
    assert "test -z \"$(go list -m -f '{{if .Replace}}" in text
    assert "cmp /tmp/caddy-expected-graph /tmp/caddy-governed-graph" in text
    assert "go build -mod=readonly -trimpath" in text
    assert "github.com/caddyserver/caddy/v2.CustomVersion=v2.11.9" in text
    assert "go version -m /go/bin/caddy > /tmp/caddy-binary-metadata" in text
    assert "cmp /tmp/caddy-expected-binary /tmp/caddy-governed-binary" in text
    for exact_binary_identity in (
        "mod github.com/caddyserver/caddy/v2 v2.11.9",
        "dep github.com/go-jose/go-jose/v3 v3.0.5",
        "dep github.com/go-jose/go-jose/v4 v4.1.6",
        "dep google.golang.org/grpc v1.83.2",
        "dep golang.org/x/crypto v0.58.0",
        "dep golang.org/x/net v0.62.0",
        "dep golang.org/x/sync v0.24.0",
        "dep golang.org/x/sys v0.49.0",
        "dep golang.org/x/term v0.47.0",
        "dep golang.org/x/text v0.43.0",
    ):
        assert f"'{exact_binary_identity}'" in text
    assert '"c-ares>=1.34.8-r0"' in text
    assert '"curl>=8.20.0-r0"' in text
    assert '"libcurl>=8.20.0-r0"' in text
    assert '"zlib>=1.3.2-r1"' in text
    assert "COPY --from=caddy-build --chmod=0755 /go/bin/caddy" in text
    assert "caddy list-modules --packages" in text
    assert "setcap cap_net_bind_service=+ep /usr/bin/caddy" in text
    assert "getcap /usr/bin/caddy" in text
    # Only the exact offline stdlib block disables module-network services.
    # Networked module acquisition and the remaining recipe keep sumdb enabled.
    stdlib_start = EXPECTED_CADDY_BUILDER_STAGE.index("RUN --network=none set -eux;")
    stdlib_end = EXPECTED_CADDY_BUILDER_STAGE.index("\nENV GOROOT=", stdlib_start)
    stdlib_block = EXPECTED_CADDY_BUILDER_STAGE[stdlib_start:stdlib_end]
    assert text.count(stdlib_block) == 1
    assert "GOSUMDB=off" not in text.replace(stdlib_block, "", 1)
    for forbidden in (
        "@latest",
        "--allow-untrusted",
        "go install",
        "GOINSECURE",
        "GONOSUMDB",
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
    assert '"brotli-libs>=1.2.1-r0"' in text


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
        "xnet062-omitted",
        "xnet062-duplicate",
        "xnet062-downgraded",
        "post-get-sum-unbound",
        "final-sum-unbound",
        "xnet062-floating",
        "xnet062-reordered",
        "post-get-sum-omitted",
        "final-sum-omitted",
        "final-go-mod-unbound",
        "go-mod-comparison-omitted",
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
            "      'dep golang.org/x/crypto v0.58.0' \\\n",
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
    elif case in ("xnet062-omitted", "xnet062-duplicate", "xnet062-downgraded", "xnet062-floating"):
        action = "    go get golang.org/x/net@v0.62.0; \\\n"
        replacement = {
            "xnet062-omitted": "",
            "xnet062-duplicate": action * 2,
            "xnet062-downgraded": action.replace("v0.62.0", "v0.60.0"),
            "xnet062-floating": action.replace("v0.62.0", "latest"),
        }[case]
        candidate = source.replace(action, replacement, 1)
    elif case == "xnet062-reordered":
        action = "    go get golang.org/x/net@v0.62.0; \\\n"
        incumbent = "    go get github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.9; \\\n"
        candidate = source.replace(action, "", 1).replace(incumbent, action + incumbent, 1)
    elif case in ("post-get-sum-omitted", "final-sum-omitted"):
        expected_check = {
            "post-get-sum-omitted": "    echo 'f5d9289fa0e27604a936ed5e35368db876398dac62154b9a6af9d0d2a891f7d9  /tmp/caddy-xnet062-postget.sum' | sha256sum -c -; \\\n",
            "final-sum-omitted": "    echo 'be8f44f7e591bcaa54412fe5f3061235596be2faf9bd3f5fdece0106fea45338  go.sum' | sha256sum -c -; \\\n",
        }[case]
        candidate = source.replace(expected_check, "", 1)
    elif case == "final-go-mod-unbound":
        candidate = source.replace(
            "f06331d8fba11ae7ac7ba36f80198bb9ca7c5ac22df4deb7011ab91a4d52f596", "0" * 64, 1
        )
    elif case == "go-mod-comparison-omitted":
        candidate = source.replace("    cmp go.mod /tmp/caddy-xnet062-postget.mod; \\\n", "", 1)
    elif case in ("post-get-sum-unbound", "final-sum-unbound"):
        digest = {
            "post-get-sum-unbound": "f5d9289fa0e27604a936ed5e35368db876398dac62154b9a6af9d0d2a891f7d9",
            "final-sum-unbound": "be8f44f7e591bcaa54412fe5f3061235596be2faf9bd3f5fdece0106fea45338",
        }[case]
        candidate = source.replace(digest, "0" * 64, 1)
    else:
        assert case == "binary-fixed-graph-stale"
        candidate = source.replace(
            "      'golang.org/x/crypto v0.58.0' \\\n",
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


def _assert_frontend_caddy_contract(workflow: dict[str, object]) -> None:
    changes_steps = _steps(_job(workflow, "changes"))
    job = _job(workflow, "caddy-contract")
    assert job["runs-on"] == "ubuntu-24.04", "Caddy requires the qualified Ubuntu 24.04 runner"
    assert job["if"] == (
        "${{ !cancelled() && (needs.changes.outputs.caddy == 'true' "
        "|| github.event_name == 'workflow_dispatch') }}"
    )
    assert job["permissions"] == {"contents": "read", "actions": "read"}
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
    assert "official_caddy_ref =" in text
    assert "^FROM (caddy:" in text
    assert '"--cap-drop", "ALL", "--cap-add", "NET_BIND_SERVICE"' in text
    assert "aquasecurity/trivy-action@" in text

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "set -o pipefail" in dockerfile


def test_frontend_caddy_contract_is_non_publishing_and_unprivileged() -> None:
    _assert_frontend_caddy_contract(_workflow(FRONTEND_WORKFLOW))


@pytest.mark.parametrize("runner", ["ubuntu-latest", "ubuntu-26.04"])
def test_frontend_caddy_contract_rejects_unqualified_runner(runner: str) -> None:
    workflow = _workflow(FRONTEND_WORKFLOW)
    _assert_frontend_caddy_contract(workflow)
    _job(workflow, "caddy-contract")["runs-on"] = runner
    with pytest.raises(AssertionError, match="Caddy requires the qualified Ubuntu 24.04 runner"):
        _assert_frontend_caddy_contract(workflow)


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
    assert 'CADDY_VERSION_TOKEN" != "v2.11.9"' in text
    assert 'CADDY_GO_VERSION" != "go1.26.10"' in text
    assert "*v2.11.9*" not in text
    assert "*go1.26.10*" not in text


@pytest.mark.parametrize(
    ("caddy_version", "build_info", "expected_error"),
    (
        ("v2.11.90 h1:test", "go\tgo1.26.10\n", "Expected Caddy v2.11.9"),
        ("v2.11.9 h1:test", "go\tgo1.26.100\n", "Expected Caddy built with Go 1.26.10"),
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
        caddy_version="v2.11.9 h1:test",
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
        caddy_version="v2.11.9 h1:test",
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
        caddy_version="v2.11.9 h1:test",
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
        caddy_version="v2.11.9 h1:test",
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
        caddy_version="v2.11.9 h1:test",
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
        caddy_version="v2.11.9 h1:test",
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
    evidence = _named_step(steps, "Select authenticated Prometheus PR evidence")
    assert evidence["if"] == native["if"] and evidence["id"] == "checkpoint-evidence"
    assert evidence["env"] == {
        "GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
        "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
        "PROMETHEUS_ROUTE_HEAD": "${{ steps.checkpoint-route.outputs.head }}",
        "PROMETHEUS_ROUTE_BASE": "${{ steps.checkpoint-route.outputs.base }}",
        "PROMETHEUS_CLASSIFIED_MODE": "${{ steps.checkpoint-route.outputs.mode }}",
        "PROMETHEUS_SELECT_SECONDS": "60",
    }
    for variable, field in (
        ("PROMETHEUS_ROUTE_HEAD", "head"),
        ("PROMETHEUS_ROUTE_BASE", "base"),
        ("PROMETHEUS_CREDENTIAL_ROUTE", "mode"),
    ):
        assert consumer["env"][variable] == "${{ steps.checkpoint-evidence.outputs." + field + " }}"
    assert classifier["id"] == "checkpoint-route"
    assert classifier["if"] == control["if"] == consumer["if"] == native["if"]
    assert set(classifier["env"]) == {"PROMETHEUS_EVENT_HEAD", "PROMETHEUS_EVENT_BASE"}
    assert "secrets." not in str(classifier)
    assert classifier["run"].count('trusted["classify_source_change"](previous, current)') == 1
    assert "mode=" not in selection["run"]
    # pragma: allowlist nextline secret - public trusted control commit
    assert control["with"]["ref"] == "847e08ff971f4f794e101f871e6a1c47a980d23d"
    assert control["with"]["persist-credentials"] is False
    assert "python3 -I -S" in consumer["run"] and "runpy.run_path(str(helper))" in consumer["run"]
    assert consumer["env"]["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert (
        consumer["env"]["GHCR_READ_TOKEN"]
        == "${{ steps.checkpoint-evidence.outcome == 'success' && steps.checkpoint-evidence.outputs.mode == 'unchanged_pr_published' && secrets.GITHUB_TOKEN || '' }}"
    )
    assert (
        steps.index(checkout)
        < steps.index(selection)
        < steps.index(control)
        < steps.index(classifier)
        < steps.index(_named_step(steps, "Select authenticated Prometheus PR evidence"))
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
    build = _named_step(steps, "Build source-patched Caddy candidate")
    original = _named_step(steps, "Scan hardened Caddy shell image")
    assert build["id"] == "caddy-build"
    assert original["id"] == "caddy-security"
    assert original["uses"] == TRIVY_ACTION
    assert original["with"] == {
        "version": TRIVY_VERSION,
        "image-ref": "pulseplate-caddy:contract",
        "format": "table",
        "vuln-type": "os,library",
        "severity": "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL",
        "exit-code": "0",
        "cache-dir": "/tmp/trivy-cache-caddy-contract",
    }
    assert "continue-on-error" not in original
    assert job["permissions"] == {"contents": "read", "actions": "read"}
    assert job["env"]["CADDY_FULL_SCAN_TIMEOUT_SECONDS"] == "300"
    assert "CADDY_METADATA_TIMEOUT_SECONDS" not in job["env"]
    assert "CADDY_METADATA_CLEANUP_SECONDS" not in job["env"]
    assert (
        sum(int(value) for key, value in job["env"].items() if key.startswith("CADDY_PHASE_"))
        == 225 * 60
    )
    assert (
        _step_index(steps, "Capture next loaded Caddy image identity")
        == _step_index(steps, "Build source-patched Caddy candidate") + 1
    )
    expected = {
        "Prepare same-epoch full Caddy observation": (
            "${{ !cancelled() && (steps.caddy-build.outcome == 'success' || steps.caddy-import.outcome == 'success') && "
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
            "${{ (github.event_name != 'workflow_dispatch' || inputs.caddy_action != 'xnet062-metadata') && ("
            + condition[len("${{ ") : -len(" }}")]
            + ") }}"
        )
        assert step["if"] == expected_condition
        assert "continue-on-error" not in step
        assert "uses" not in step  # No second setup/cache restore or provider.
    upload = _named_step(steps, "Upload Caddy contract evidence")
    assert (
        upload["if"]
        == "${{ (github.event_name != 'workflow_dispatch' || inputs.caddy_action != 'xnet062-metadata') && (always()) && steps.caddy-upload-budget.outcome == 'success' }}"
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
    assert metadata["subject"]["scanner_bootstrap_outcome"] == HC
    assert metadata["full_scan_native_exit"] == 0
    assert metadata["Results_Secrets_fields_absent"] == 1
    assert metadata["subject"]["image_config_id"] == "sha256:" + "a" * 64
    assert command["argv"][-1] == "sha256:" + "a" * 64
    projections = metadata["subject"]["native_projections"]
    expected_projections = {
        "version.txt": ["version"],
        "build-info.txt": ["build-info"],
        "rebuilt-modules.txt": ["list-modules", "--packages"],
        "default-ca.pem": ["cat", "/etc/ssl/certs/ca-certificates.crt"],
        "ca-package-versions.txt": [
            "list",
            "--installed",
            "--manifest",
            "ca-certificates",
            "ca-certificates-bundle",
        ],
    }
    assert set(projections) == set(expected_projections)
    assert set(command["published_projection_hashes"]) == set(expected_projections)
    image = metadata["subject"]["image_config_id"]
    for name, native_arguments in expected_projections.items():
        projection = projections[name]
        assert projection["image_config_id"] == image
        expected_argv = [
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
        if name in ("default-ca.pem", "ca-package-versions.txt"):
            expected_argv = [
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--entrypoint",
                "/bin/busybox" if name == "default-ca.pem" else "/sbin/apk",
                image,
                *native_arguments,
            ]
            assert projection["exit_code"] == 0
        assert projection["argv"][1:] == expected_argv
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
        "ca-emsign",
        "ca-aaa",
        "ca-malformed",
        "ca-old-bytes",
        "ca-count",
        "ca-capture-error",
        "ca-empty",
        "ca-old-version",
        "ca-newer-version",
        "ca-scan-version",
        "ca-scan-missing",
        "ca-image-id",
        "ca-missing-projection",
        "ca-projection-mismatch",
        "ca-projection-exit",
        "ca-subject-change",
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


# Three public CA certificates extracted from the retained vendor bundles.
# Unit snapshots substitute only expected bundle hash/length/count; OpenSSL parses real DER.
_CADDY_CA_TEST_PEMS = {
    "good": """-----BEGIN CERTIFICATE-----
MIIH0zCCBbugAwIBAgIIXsO3pkN/pOAwDQYJKoZIhvcNAQEFBQAwQjESMBAGA1UE
AwwJQUNDVlJBSVoxMRAwDgYDVQQLDAdQS0lBQ0NWMQ0wCwYDVQQKDARBQ0NWMQsw
CQYDVQQGEwJFUzAeFw0xMTA1MDUwOTM3MzdaFw0zMDEyMzEwOTM3MzdaMEIxEjAQ
BgNVBAMMCUFDQ1ZSQUlaMTEQMA4GA1UECwwHUEtJQUNDVjENMAsGA1UECgwEQUND
VjELMAkGA1UEBhMCRVMwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQCb
qau/YUqXry+XZpp0X9DZlv3P4uRm7x8fRzPCRKPfmt4ftVTdFXxpNRFvu8gMjmoY
HtiP2Ra8EEg2XPBjs5BaXCQ316PWywlxufEBcoSwfdtNgM3802/J+Nq2DoLSRYWo
G2ioPej0RGy9ocLLA76MPhMAhN9KSMDjIgro6TenGEyxCQ0jVn8ETdkXhBilyNpA
lHPrzg5XPAOBOp0KoVdDaaxXbXmQeOW1tDvYvEyNKKGno6e6Ak4l0Squ7a4DIrhr
IA8wKFSVf+DuzgpmndFALW4ir50awQUZ0m/A8p/4e7MCQvtQqR0tkw8jq8bBD5L/
0KIV9VMJcRz/RROE5iZe+OCIHAr8Fraocwa48GOEAqDGWuzndN9wrqODJerWx5eH
k6fGioozl2A3ED6XPm4pFdahD9GILBKfb6qkxkLrQaLjlUPTAYVtjrs78yM2x/47
4KElB0iryYl0/wiPgL/AlmXz7uxLaL2diMMxs0Dx6M/2OLuc5NF/1OVYm3z61PMO
m3WR5LpSLhl+0fXNWhn8ugb2+1KoS5kE3fj5tItQo05iifCHJPqDQsGH+tUtKSpa
cXpkatcnYGMN285J9Y0fkIkyF/hzQ7jSWpOGYdbhdQrqeWZ2iE9x6wQl1gpaepPl
uUsXQA+xtrn13k/c4LOsOxFwYIRKQ26ZIMApcQrAZQIDAQABo4ICyzCCAscwfQYI
KwYBBQUHAQEEcTBvMEwGCCsGAQUFBzAChkBodHRwOi8vd3d3LmFjY3YuZXMvZmls
ZWFkbWluL0FyY2hpdm9zL2NlcnRpZmljYWRvcy9yYWl6YWNjdjEuY3J0MB8GCCsG
AQUFBzABhhNodHRwOi8vb2NzcC5hY2N2LmVzMB0GA1UdDgQWBBTSh7Tj3zcnk1X2
VuqB5TbMjB4/vTAPBgNVHRMBAf8EBTADAQH/MB8GA1UdIwQYMBaAFNKHtOPfNyeT
VfZW6oHlNsyMHj+9MIIBcwYDVR0gBIIBajCCAWYwggFiBgRVHSAAMIIBWDCCASIG
CCsGAQUFBwICMIIBFB6CARAAQQB1AHQAbwByAGkAZABhAGQAIABkAGUAIABDAGUA
cgB0AGkAZgBpAGMAYQBjAGkA8wBuACAAUgBhAO0AegAgAGQAZQAgAGwAYQAgAEEA
QwBDAFYAIAAoAEEAZwBlAG4AYwBpAGEAIABkAGUAIABUAGUAYwBuAG8AbABvAGcA
7QBhACAAeQAgAEMAZQByAHQAaQBmAGkAYwBhAGMAaQDzAG4AIABFAGwAZQBjAHQA
cgDzAG4AaQBjAGEALAAgAEMASQBGACAAUQA0ADYAMAAxADEANQA2AEUAKQAuACAA
QwBQAFMAIABlAG4AIABoAHQAdABwADoALwAvAHcAdwB3AC4AYQBjAGMAdgAuAGUA
czAwBggrBgEFBQcCARYkaHR0cDovL3d3dy5hY2N2LmVzL2xlZ2lzbGFjaW9uX2Mu
aHRtMFUGA1UdHwROMEwwSqBIoEaGRGh0dHA6Ly93d3cuYWNjdi5lcy9maWxlYWRt
aW4vQXJjaGl2b3MvY2VydGlmaWNhZG9zL3JhaXphY2N2MV9kZXIuY3JsMA4GA1Ud
DwEB/wQEAwIBBjAXBgNVHREEEDAOgQxhY2N2QGFjY3YuZXMwDQYJKoZIhvcNAQEF
BQADggIBAJcxAp/n/UNnSEQU5CmH7UwoZtCPNdpNYbdKl02125DgBS4OxnnQ8pdp
D70ER9m+27Up2pvZrqmZ1dM8MJP1jaGo/AaNRPTKFpV8M9xii6g3+CfYCS0b78gU
JyCpZET/LtZ1qmxNYEAZSUNUY9rizLpm5U9EelvZaoErQNV/+QEnWCzI7UiRfD+m
AM/EKXMRNt6GGT6d7hmKG9Ww7Y49nCrADdg9ZuM8Db3VlFzi4qc1GwQA9j9ajepD
vV+JHanBsMyZ4k0ACtrJJ1vnE5Bc5PUzolVt3OAJTS+xJlsndQAJxGJ3KQhfnlms
tn6tn1QwIgPBHnFk/vk4CpYY3QIUrCPLBhwepH2NDd4nQeit2hW3sCPdK6jT2iWH
7ehVRE2I9DZ+hJp4rPcOVkkO1jMl1oRQQmwgEh0q1b688nCBpHBgvgW1m54ERL5h
I6zppSSMEYCUWqKiuUnSwdzRp+0xESyeGabu4VXhwOrPDYTkF7eifKXeVSUG7szA
h1xA2syVP1XgNce4hL60Xc16gwFy7ofmXx2utYXGJt/mwZrpHgJHnyqobalbz+xF
d3+YJ5oyXSrjhO7FmGYvliAd3djDJ9ew+f7Zfc3Qn48LFFhRny+Lwzgt3uiP1o2H
pPVWQxaZLPSkVrQ0uGE3ycJYgBugl6H8WY3pEfbRD0tVNEYqi4Y7
-----END CERTIFICATE-----
""",
    "emsign": """-----BEGIN CERTIFICATE-----
MIICTjCCAdOgAwIBAgIKPPYHqWhwDtqLhDAKBggqhkjOPQQDAzBrMQswCQYDVQQG
EwJJTjETMBEGA1UECxMKZW1TaWduIFBLSTElMCMGA1UEChMcZU11ZGhyYSBUZWNo
bm9sb2dpZXMgTGltaXRlZDEgMB4GA1UEAxMXZW1TaWduIEVDQyBSb290IENBIC0g
RzMwHhcNMTgwMjE4MTgzMDAwWhcNNDMwMjE4MTgzMDAwWjBrMQswCQYDVQQGEwJJ
TjETMBEGA1UECxMKZW1TaWduIFBLSTElMCMGA1UEChMcZU11ZGhyYSBUZWNobm9s
b2dpZXMgTGltaXRlZDEgMB4GA1UEAxMXZW1TaWduIEVDQyBSb290IENBIC0gRzMw
djAQBgcqhkjOPQIBBgUrgQQAIgNiAAQjpQy4LRL1KPOxst3iAhKAnjlfSU2fySU0
WXTsuwYc58Byr+iuL+FBVIcUqEqy6HyC5ltqtdyzdc6LBtCGI79G1Y4PPwT01xyS
fvalY8L1X44uT6EYGQIrMgqCZH0Wk9GjQjBAMB0GA1UdDgQWBBR8XQKEE9TMipuB
zhccLikenEhjQjAOBgNVHQ8BAf8EBAMCAQYwDwYDVR0TAQH/BAUwAwEB/zAKBggq
hkjOPQQDAwNpADBmAjEAvvNhzwIQHWSVB7gYboiFBS+DCBeQyh+KTOgNG3qxrdWB
CUfvO6wIBHxcmbHtRwfSAjEAnbpV/KlK6O3t5nYBQnvI+GDZjVGLVTv7jHvrZQnD
+JbNR6iC8hZVdyR+EhCVBCyj
-----END CERTIFICATE-----
""",
    "aaa": """-----BEGIN CERTIFICATE-----
MIIEMjCCAxqgAwIBAgIBATANBgkqhkiG9w0BAQUFADB7MQswCQYDVQQGEwJHQjEb
MBkGA1UECAwSR3JlYXRlciBNYW5jaGVzdGVyMRAwDgYDVQQHDAdTYWxmb3JkMRow
GAYDVQQKDBFDb21vZG8gQ0EgTGltaXRlZDEhMB8GA1UEAwwYQUFBIENlcnRpZmlj
YXRlIFNlcnZpY2VzMB4XDTA0MDEwMTAwMDAwMFoXDTI4MTIzMTIzNTk1OVowezEL
MAkGA1UEBhMCR0IxGzAZBgNVBAgMEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4GA1UE
BwwHU2FsZm9yZDEaMBgGA1UECgwRQ29tb2RvIENBIExpbWl0ZWQxITAfBgNVBAMM
GEFBQSBDZXJ0aWZpY2F0ZSBTZXJ2aWNlczCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBAL5AnfRu4ep2hxxNRUSOvkbIgwadwSr+GB+O5AL686tdUIoWMQua
BtDFcCLNSS1UY8y2bmhGC1Pqy0wkwLxyTurxFa70VJoSCsN6sjNg4tqJVfMiWPPe
3M/vg4aijJRPn2jymJBGhCfHdr/jzDUsi14HZGWCwEiwqJH5YZ92IFCokcdmtet4
YgNW8IoaE+oxox6gmf049vYnMlhvB/VruPsUK6+3qszWY19zjNoFmag4qMsXeDZR
rOme9Hg6jc8P2ULimAyrL58OAd7vn5lJ8S3frHRNG5i1R8XlKdH5kBjHYpy+g8cm
ez6KJcfA3Z3mNWgQIJ2P2N7Sw4ScDV7oL8kCAwEAAaOBwDCBvTAdBgNVHQ4EFgQU
oBEKIz6W8Qfs4q8p74Klf9AwpLQwDgYDVR0PAQH/BAQDAgEGMA8GA1UdEwEB/wQF
MAMBAf8wewYDVR0fBHQwcjA4oDagNIYyaHR0cDovL2NybC5jb21vZG9jYS5jb20v
QUFBQ2VydGlmaWNhdGVTZXJ2aWNlcy5jcmwwNqA0oDKGMGh0dHA6Ly9jcmwuY29t
b2RvLm5ldC9BQUFDZXJ0aWZpY2F0ZVNlcnZpY2VzLmNybDANBgkqhkiG9w0BAQUF
AAOCAQEACFb8AvCb6P+k+tZ7xkSAzk/ExfYAWMymtrwUSWgEdujm7l3sAg9g1o1Q
GE8mTgHj5rCl7r+8dFRBv/38ErjHT1r0iWAFf2C3BUrz9vHCv8S5dIa2LX1rzNLz
Rt0vxuBqw8M0Ayx9lt1awg6nCpnBBYurDC/zXDrPbDdVCYfeU0BsWO/8tqtlbgT2
G9w84FoVxp7Z8VlIMCFlA2zs6SFz7JsDoeA3raAVGI/6ugLOpyypEBMs1OUIJqsi
l2D4kF501KKaU73yqWjgom7C12yxow+ev+to51byrvLjKzg6CYG1a4XXvi3tPxq3
smPi9WIsgtRqAEFQ8TmDn5XpNpaYbg==
-----END CERTIFICATE-----
""",
}


def _caddy_fixture_reader(boot_id: str) -> Callable[..., str]:
    """Provide one synthetic Linux kernel file for a Darwin fixture session."""
    native_read = Path.read_text

    def read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if path == Path("/proc/sys/kernel/random/boot_id"):
            return boot_id + "\n"
        return native_read(path, *args, **kwargs)

    return read_text


def _run_caddy_full_observation_fixture(
    tmp_path: Path, scenario: str, HC: str
) -> tuple[subprocess.CompletedProcess[str], bool, dict[str, object], dict[str, object]]:
    """Execute capture/preparation/publication and actual single-call scan owner.

    This fixture is not the six-control decision; its independent tests follow.
    """
    ca = _CADDY_CA_TEST_PEMS[
        "emsign" if scenario == "ca-emsign" else "aaa" if scenario == "ca-aaa" else "good"
    ].encode()
    if scenario == "ca-malformed":
        ca = b"not a PEM certificate"
    if scenario == "ca-count":
        ca += _CADDY_CA_TEST_PEMS["emsign"].encode()
    expected_ca = ca
    if scenario == "ca-old-bytes":
        ca = _CADDY_CA_TEST_PEMS["emsign"].encode()
    ca_file = tmp_path / "public-ca.pem"
    ca_file.write_bytes(ca)
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
        "frontend/scripts/check-redocly-compat.mjs",
        "frontend/patches/redocly-1.34.15-minimatch11.patch",
        "frontend/patches/redocly-1.34.15-minimatch11.inventory.json",
        ".github/workflows/frontend-ci.yml",
        "deploy/Caddyfile",
        "deploy/Caddyfile.production",
        "scripts/ci/check_docker_runtime_dependency_surface.py",
        "scripts/ci/prometheus_source_image.py",
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
        "elif 'tar' in args and '-cf' in args:\n"
        " import io,tarfile\n"
        " CADDY_BUILD_MEMBERS=" + repr(set(caddy_surface.CADDY_BUILD_MEMBERS)) + "\n"
        " buffer=io.BytesIO()\n"
        " with tarfile.open(fileobj=buffer,mode='w') as archive:\n"
        "  for name in sorted(CADDY_BUILD_MEMBERS):\n"
        "   value=b'synthetic capture-only evidence';entry=tarfile.TarInfo('./'+name);entry.size=len(value);archive.addfile(entry,io.BytesIO(value))\n"
        " sys.stdout.buffer.write(buffer.getvalue())\n"
        "elif args[-2:]==['cat','/etc/ssl/certs/ca-certificates.crt']:\n"
        " if scenario=='ca-capture-error':sys.exit(2)\n"
        " if scenario=='ca-empty':sys.exit(0)\n"
        f" ca=Path({str(ca_file)!r}).read_bytes()\n"
        " if scenario=='ca-subject-change' and sum(row[-2:]==['cat','/etc/ssl/certs/ca-certificates.crt'] for row in history)>1:ca=b'changed'\n"
        " sys.stdout.buffer.write(ca)\n"
        "elif '--entrypoint' in args and args[args.index('--entrypoint')+1]=='/sbin/apk':\n"
        " assert args[-5:]==['list','--installed','--manifest','ca-certificates','ca-certificates-bundle']\n"
        " version='20260611-r0' if scenario=='ca-old-version' else '20261021-r0' if scenario=='ca-newer-version' else '20261020-r0'\n"
        " print('ca-certificates '+version);print('ca-certificates-bundle '+version)\n"
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
                "Packages": [
                    {"Name": "libssl3", "Version": "3.5.8-r0"},
                    {"Name": "ca-certificates", "Version": "20261020-r0"},
                    {"Name": "ca-certificates-bundle", "Version": "20261020-r0"},
                ],
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
    if scenario == "ca-scan-version":
        report["Results"][0]["Packages"][1]["Version"] = "20260611-r0"
    if scenario == "ca-scan-missing":
        report["Results"][0]["Packages"].pop()
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
        "PYTHONPATH": str(workspace),
        "RUNNER_TEMP": str(runner),
        "GITHUB_OUTPUT": str(github_output),
        "CADDY_BOOTSTRAP_OUTCOME": HC,
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
    environment.update(
        {
            key: str(value)
            for key, value in _job(workflow, "caddy-contract")["env"].items()
            if key.startswith("CADDY_PHASE_") or key.startswith("CADDY_SCAN_")
        }
    )
    environment["CADDY_REUSE_TIMEOUT_SECONDS"] = "840"
    import time

    (runner / "caddy-admission").mkdir()
    caps = {
        key.removeprefix("CADDY_PHASE_"): int(value)
        for key, value in environment.items()
        if key.startswith("CADDY_PHASE_")
    }
    boot_id_path = Path("/proc/sys/kernel/random/boot_id")
    if sys.platform == "darwin":
        boot_id = str(uuid4())
        # Each extracted workflow step runs in a fresh interpreter. Install the same
        # narrow reader there without changing the workflow source or child environment.
        bootstrap = (
            "from __future__ import annotations\n"
            "from pathlib import Path\n"
            + inspect.getsource(_caddy_fixture_reader)
            + f"\nPath.read_text = _caddy_fixture_reader({boot_id!r})\n"
            + "import sys\nexec(compile(sys.argv.pop(), '<workflow-step>', 'exec'), "
            + "{'__name__': '__main__'})"
        )
        command = [sys.executable, "-c", bootstrap]
    else:
        boot_id = boot_id_path.read_text().strip()
        command = [sys.executable, "-c"]
    (runner / "caddy-admission/admission.json").write_text(
        json.dumps(
            {
                "budget": {
                    "started": time.monotonic(),
                    "seconds": sum(caps.values()),
                    "boot_id": boot_id,
                    "charged": dict.fromkeys(caps, 0),
                    "action_deadlines": {},
                }
            }
        )
    )
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
        if name == "Observe all-severity Caddy native report":
            import ast

            nodes = ast.parse(script).body
            cutoff = next(index for index, node in enumerate(nodes) if isinstance(node, ast.Try))
            script = ast.unparse(ast.Module(body=nodes[:cutoff], type_ignores=[])) + "\n"
            script += "freeze()\n"
            script += 'code, timed = invoke("candidate-full", subject["full_argv"], "SCANS", int(os.environ["CADDY_FULL_SCAN_TIMEOUT_SECONDS"]) + 30, scan=True)\n'
            script += 'if code != 0 or timed: raise ValueError("native_full_scan_failed")\n'
            script += "freeze()\n"
            script += 'subject["controls"] = {"scans": {"candidate-full": {"exit": code, "timeout": timed}}}\nstate_path.write_text(json.dumps(subject))\n'
            script += 'record = records[-1]\nfor channel in ("stdout", "stderr"):\n    (private / ("scan." + channel + ".private")).write_bytes((control_dir / record[channel]).read_bytes())\n'
        if name == "Validate and publish full Caddy observation":
            assert (
                script.count("5961c0a3c65459931c023e0075c09733f09aea4ca439cb85bc4a08bb4f3f568b")
                == 1
            )
            script = script.replace(
                "5961c0a3c65459931c023e0075c09733f09aea4ca439cb85bc4a08bb4f3f568b",
                hashlib.sha256(expected_ca).hexdigest(),
            )
            script = script.replace("len(ca) != 178791", f"len(ca) != {len(expected_ca)}")
            script = script.replace("len(certificates) != 118", "len(certificates) != 1")
        last = subprocess.run(
            [*command, script],
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
            if scenario == "ca-projection-exit":
                state_path = Path(outputs["state"])
                subject = json.loads(state_path.read_text())
                subject["native_projections"]["default-ca.pem"]["exit_code"] = 1
                state_path.write_text(json.dumps(subject))
            if scenario == "source":
                (workspace / "frontend/package.json").write_text("changed-source")
            if scenario == "missing-db":
                (cache / "db/trivy.db").unlink()
            if scenario == "binary":
                docker.write_text(
                    docker.read_text().replace("scenario='binary'", "scenario='valid'")
                )
            projection_faults = {
                "ca-image-id": ("default-ca.pem", "image-id"),
                "ca-missing-projection": ("default-ca.pem", "missing"),
                "ca-projection-mismatch": ("default-ca.pem", "mismatch"),
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
        "xnet062-metadata",
        "candidate-D",
    ]
    steps = _steps(_job(workflow, "caddy-contract"))
    metadata = _named_step(steps, "Qualify Caddy compiler and two independent root derivations")
    assert (
        metadata["if"]
        == "${{ steps.caddy-admission.outputs.mode == 'metadata' || steps.caddy-admission.outputs.mode == 'build' }}"
    )
    source = metadata["run"]
    assert re.search(r"\bgo\s+build\b", source) is None
    assert 'for label in ("a", "b")' in source
    assert '"go_build_invocations": 0' in source
    assert "result = validate_caddy_xnet062_metadata(output)" in source
    checker = inspect.getsource(caddy_surface.validate_caddy_xnet062_metadata)
    assert 'root_module="pulseplate.local/caddy-build"' in checker
    assert "tree_inventory(left, deadline=native.deadline)" in source
    assert "== tree_inventory(right, deadline=native.deadline)" in source
    assert '"/output/$phase-packages.json"' in source
    assert "post-get-go.mod" in source and "module-derivation.patch" in source
    assert 'result["complete_delta"]' in source and 'result["historical_caddy_delta"]' in source
    assert '"v2.11.4"' in checker and '"v2.11.9"' in checker
    assert "vendor_script" not in source and "secdb_url" not in source
    assert (
        source.index("go get github.com/klauspost/compress@v1.18.7")
        < source.index("capture baseline")
        < source.index("go get github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.9")
        < source.index("capture incumbent")
        < source.index("go get golang.org/x/net@v0.62.0")
        < source.index("capture final")
    )
    build = _named_step(steps, "Build source-patched Caddy candidate")
    assert (
        build["if"]
        == "${{ steps.caddy-admission.outputs.mode == 'build' && steps.caddy-metadata.outcome == 'success' }}"
    )
    assert steps.index(metadata) < steps.index(build)
    assert build["with"]["platforms"] == "linux/amd64"


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
        "alertmanager-main-publication": int(
            _job(workflow, "alertmanager-main-publication")["env"]["ALERTMANAGER_PUBLISHER_SECONDS"]
        ),
    }
    for name, seconds in work.items():
        job = _job(workflow, name)
        if name == "alertmanager-main-publication":
            declared = job["timeout-minutes"]
            matched = re.fullmatch(
                r"\$\{\{ fromJSON\(vars\.ALERTMANAGER_PUBLISHER_JOB_MINUTES \|\| '([1-9][0-9]{0,2})'\) \}\}",
                declared,
            )
            assert matched is not None
            minutes = int(matched[1])
            publisher = job["env"]
            assert publisher["ALERTMANAGER_PUBLISHER_JOB_MINUTES"] == declared
            assert seconds == (
                prep
                + int(env["ALERTMANAGER_SECURITY_SECONDS"])
                + 2 * (native + native_cleanup)
                + int(publisher["ALERTMANAGER_PUBLISHER_REBIND_SECONDS"])
                + int(env["ALERTMANAGER_PUBLICATION_SECONDS"])
                + int(publisher["ALERTMANAGER_PUBLISHER_OTHER_CLEANUP_SECONDS"])
            )
            assert int(publisher["ALERTMANAGER_PUBLISHER_OTHER_CLEANUP_SECONDS"]) == (
                3 * cleanup
                + int(publisher["ALERTMANAGER_PUBLISHER_API_CLEANUP_SECONDS"])
                + int(publisher["ALERTMANAGER_PUBLISHER_FAILURE_SECONDS"])
                + int(publisher["ALERTMANAGER_PUBLISHER_RETENTION_SECONDS"])
            )
        else:
            assert type(job["timeout-minutes"]) is int
            minutes = job["timeout-minutes"]
        assert minutes * 60 - (seconds + setup + upload) >= 300
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
        "AM_CANDIDATE_RUN": "42110438896",
        "AM_CANDIDATE_ARTIFACT": "13456175467",
        "AM_CANDIDATE_SOURCE": "8aee3976d8f13027a5f2a38f0152ede0f4990156",
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
        "clock-no-parent",
        "clock-full-parent",
        "clock-short-parent",
        "clock-nextafter-parent",
        "clock-prep-exhausted",
        "clock-prep-advanced",
        "clock-later-exact",
        "clock-later-excess",
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
    """Exercise the real H publisher with synthetic transport, never qualify a producer."""
    from scripts.ci import fetch_docker_source_artifacts as fetcher
    from scripts.ci import prometheus_source_image as transport
    from tests.test_docker_workflow_build_path_contract import _alertmanager_proposal_arguments

    # Clock profiles use the same full publisher path as the main-before-copy control.
    import math
    import signal
    from types import SimpleNamespace

    clock_profile = case if case.startswith("clock-") else None
    start = 800.125 if clock_profile == "clock-later-exact" else 800.000000027
    if clock_profile == "clock-prep-advanced":
        start = 0.125
    now = start
    timers: list[float] = []
    if clock_profile:
        case = "main-before-copy"
        parent = {
            "clock-full-parent": 10440.0,
            "clock-short-parent": 10440.0 - 0.000001,
            "clock-nextafter-parent": math.nextafter(10440.0, 0.0),
        }.get(clock_profile, 0.0)
        initial_samples = iter([start])

        def monotonic() -> float:
            return next(initial_samples, now)

        if clock_profile == "clock-prep-exhausted":
            now = start + 601
        if clock_profile == "clock-prep-advanced":
            now = math.nextafter(start, math.inf)
        fixture_time = SimpleNamespace(monotonic=monotonic)
        monkeypatch.setattr(fetcher, "time", fixture_time)
        monkeypatch.setattr(transport, "time", fixture_time)
        monkeypatch.setattr(signal, "getitimer", lambda timer: (parent, 0.0))
        monkeypatch.setattr(
            signal, "setitimer", lambda _timer, seconds, *args: timers.append(seconds)
        )

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
        "GIT_ASKPASS",
        "SSH_ASKPASS",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_PARAMETERS",
        "CURL_HOME",
        "XDG_CONFIG_HOME",
    ):
        monkeypatch.delenv(key, raising=False)
    workflow = _workflow(CD_WORKFLOW)
    publisher = _job(workflow, "alertmanager-main-publication")
    for key, value in {**workflow["env"], **publisher["env"]}.items():
        if key.startswith("ALERTMANAGER_"):
            if key == "ALERTMANAGER_PUBLISHER_JOB_MINUTES":
                matched = re.fullmatch(
                    r"\$\{\{ fromJSON\(vars.ALERTMANAGER_PUBLISHER_JOB_MINUTES \|\| '([0-9]+)'\) \}\}",
                    value,
                )
                assert matched is not None
                value = matched[1]
            monkeypatch.setenv(key, str(value))
    h, c = "a" * 40, "c" * 40
    merge = ("d" if case == "descendant" else "a") * 40
    for key, value in {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "999",
        "GITHUB_SHA": h,
        "GITHUB_WORKFLOW_SHA": h,
        "GITHUB_WORKFLOW_REF": "Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml@refs/heads/main",
        "GITHUB_REPOSITORY_OWNER": "Katsiarynakavaleuskaya",
        "GH_TOKEN": "synthetic-publish-credential",
        "GITHUB_TOKEN": "synthetic-publish-credential",
    }.items():
        monkeypatch.setenv(key, value)

    # Keep the actual typed whole-material reader. Drift changes real local bytes,
    # while both authenticated API and native Git replies retain the original blobs.
    sources = {
        path: (REPO_ROOT / path).read_bytes()
        for path in {
            *fetcher._ALERT_Q_SOURCE_FILES,
            *fetcher._ALERT_SELECTION_FILES,
            "tests/test_notify_premium_alias_checkpoint_failure.py",
        }
    }
    root = tmp_path / "reviewed-H"
    root.mkdir()
    tree = "e" * 40
    blobs = {}
    for path, raw in sources.items():
        leaf = root / path
        leaf.parent.mkdir(parents=True, exist_ok=True)
        leaf.write_bytes(raw)
        leaf.chmod(0o644)
        blobs[path] = hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
        ).hexdigest()
    drift_path = {
        "source-drift": "scripts/ci/fetch_docker_source_artifacts.py",
        "template-drift": "deploy/docker-compose.staging.yaml",
    }.get(case)
    if drift_path is not None:
        (root / drift_path).write_bytes(sources[drift_path] + b"\n# changed captured input\n")
    monkeypatch.setattr(fetcher, "REPO_ROOT", root)
    monkeypatch.setattr(
        fetcher,
        "_ALERT_ACCEPTED_CANDIDATE",
        {
            "run": 888,
            "attempt": 1,
            "artifact": 777,
            "source": c,
            "job": 666,
            "zip_sha256": "e" * 64,
            "source_files": {
                path: hashlib.sha256(sources[path]).hexdigest()
                for path in (
                    *fetcher._ALERT_Q_SOURCE_FILES,
                    "tests/test_notify_premium_alias_checkpoint_failure.py",
                )
            },
            "graph": {"synthetic_guarded_publication_only": True},
            "OCI_archive_sha256": "f" * 64,
        },
    )
    events: list[str] = []
    native_calls: list[str] = []
    sessions: list[Any] = []
    graph: dict[str, Any] = {}
    output = tmp_path / "owned-publication"
    copied = False
    pulled_back = False
    logged_in = False
    scanner = {"sha256": fetcher._ALERT_TRIVY_SHA256, "DB": dict(fetcher._ALERT_DB)}
    tool_bytes = b"synthetic qualified ORAS transport"
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

    class API:
        def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
            self.private, self.deadline, self.cleanup_seconds = private, deadline, cleanup
            self.name = "prepare" if private.name == "private" else "final"
            self.closed = False
            self.main_reads = 0
            assert evidence.name == (
                "github-read-evidence" if self.name == "prepare" else "final-github-read-evidence"
            )
            private.mkdir()
            for name in ("home", "config", "cache", "tmp"):
                (private / name).mkdir()
            sessions.append(self)
            events.append(self.name + "-open")

        def json(self, endpoint: str) -> dict[str, Any]:
            if "/git/ref/" in endpoint:
                self.main_reads += 1
                drift = (
                    case == "main-before-login"
                    and self.name == "final"
                    and not logged_in
                    or case == "main-before-copy"
                    and logged_in
                    and not copied
                    or case == "main-after-copy"
                    and copied
                )
                return {"ref": "refs/heads/main", "object": {"sha": "f" * 40 if drift else h}}
            if endpoint.endswith("/pulls/2494"):
                return {
                    "number": 2477 if case == "wrong-pr" else 2494,
                    "state": "closed",
                    "merged": case != "unmerged",
                    "merge_commit_sha": "unknown" if case == "merge-invalid" else merge,
                    "commits": 1,
                    "base": {
                        "ref": "main",
                        "repo": {"id": 1 if case == "foreign-pr" else 1043311030},
                    },
                    "head": {"ref": fetcher._ALERT_Q_BRANCH, "sha": c, "repo": {"id": 1043311030}},
                }
            if "/git/commits/" in endpoint:
                assert endpoint.endswith(h)
                return {"sha": h, "tree": {"sha": tree}}
            if "/git/trees/" in endpoint:
                assert endpoint.endswith(tree + "?recursive=1")
                return {
                    "sha": tree,
                    "truncated": False,
                    "tree": [
                        {"path": path, "mode": "100644", "type": "blob", "sha": oid}
                        for path, oid in sorted(blobs.items())
                    ],
                }
            assert "/actions/artifacts/" in endpoint
            return {
                "digest": "sha256:"
                + hashlib.sha256(b"synthetic authenticated artifact").hexdigest()
            }

        def pages(self, endpoint: str, key: str | None, count: int) -> list[dict[str, str]]:
            assert endpoint.endswith("/pulls/2494/commits") and key is None and count == 1
            return [{"sha": c}]

        def _capture(self, argv: list[str], maximum: int, **kwargs: Any) -> bytes:
            nonlocal copied, pulled_back, logged_in
            assert maximum > 0
            environment = kwargs.get("environment", {})
            assert all(
                key not in environment
                for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "HTTP_PROXY")
            )
            if "merge-base" in argv:
                assert argv[-2:] == [merge, h] and c not in argv
                return b""
            if "rev-parse" in argv:
                if argv[-1] == "info/grafts":
                    return str(root / ".git/info/grafts").encode() + b"\n"
                return ((tree if argv[-1] == h + "^{tree}" else h) + "\n").encode()
            if "ls-tree" in argv:
                return b"".join(
                    f"100644 blob {oid}\t{path}\0".encode() for path, oid in sorted(blobs.items())
                )
            if "ls-files" in argv:
                if "--stage" in argv:
                    return b"".join(
                        f"100644 {oid} 0\t{path}\0".encode() for path, oid in sorted(blobs.items())
                    )
                assert "--others" in argv
                return b""
            if "login" in argv:
                assert (
                    events.index("prepare-close")
                    < events.index("security")
                    < events.index("pre-native")
                )
                assert self.name == "final" and argv[0] == synthetic_docker
                assert kwargs["input_data"] == b"synthetic-publish-credential\n"
                assert "tag" in events
                events.append("login")
                logged_in = True
                credential = Path(argv[argv.index("--config") + 1]) / "config.json"
                credential.write_text('{"auths":{"ghcr.io":{"auth":"synthetic-only"}}}')
                credential.chmod(0o644 if case == "credential-mode" else 0o600)
            elif "--from-oci-layout" in argv:
                assert logged_in and case != "same"
                assert (
                    argv[-2]
                    == str(output / "prepare-inputs/candidate/layout")
                    + "@"
                    + graph["manifest"]["digest"]
                )
                assert (
                    argv[-1]
                    == "ghcr.io/katsiarynakavaleuskaya/pulseplate:alertmanager-0.34.2-"
                    + graph["manifest"]["digest"][7:]
                )
                events.append("copy")
                if case == "denied":
                    raise RuntimeError("synthetic denied real intended copy")
                copied = True
            elif "--to-oci-layout" in argv:
                assert logged_in
                assert (
                    argv[-2]
                    == "ghcr.io/katsiarynakavaleuskaya/pulseplate@" + graph["manifest"]["digest"]
                )
                events.append("pullback")
                destination = Path(argv[-1].removesuffix(":pullback"))
                shutil.copytree(output / "prepare-inputs/candidate/layout", destination)
                if case == "pullback":
                    (destination / "blobs/sha256" / graph["layers"][0]["digest"][7:]).write_bytes(
                        b"changed retained layer"
                    )
                pulled_back = True
            else:
                pytest.fail("unexpected native transport argv: " + repr(argv))
            return b"synthetic success"

        def close(self) -> None:
            events.append(self.name + "-close")
            if case == "cleanup" and self.name == "final":
                raise RuntimeError("synthetic private cleanup failed")
            shutil.rmtree(self.private)
            self.closed = True

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
            assert cwd == root and "--no-replace-objects" in argv
            assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
            assert argv[-4:] == ["merge-base", "--is-ancestor", merge, h] and c not in argv
            assert label == "actual-merge-ancestor-H" and kwargs["maximum_seconds"] == 8
            events.append("merge-ancestry")
            # A relevant shallow boundary makes the selected merge proof unavailable.
            # An unrelated shallow repository is not declared globally forbidden.
            if case == "shallow":
                raise RuntimeError(
                    "synthetic selected merge ancestry unavailable at shallow boundary"
                )
            if case in ("not-ancestor", "primary-proof-retention"):
                raise RuntimeError("synthetic native Git exit1")
            return b""

    def source_snapshot(api: API, revision: str, **kwargs: Any) -> dict[str, bytes]:
        assert revision == h and kwargs == {"upstream_version": "0.34.2"}
        return dict(sources)

    def authenticated(
        api: API, run: int, artifact: int, source: str, destination: Path, **kwargs: Any
    ) -> dict[str, Any]:
        assert (
            source == h
            and kwargs["upstream_version"] == "0.34.2"
            and kwargs["source_branch"] == "main"
        )
        assert run > 0 and artifact > 0 and str(run) != os.environ["GITHUB_RUN_ID"]
        names = sources if kwargs["kind"] == "candidate" else fetcher._ALERT_Q_SOURCE_FILES
        assert kwargs["current_source_files"] == {
            path: hashlib.sha256(sources[path]).hexdigest() for path in names
        }
        raw = b"synthetic authenticated artifact"
        assert kwargs["current_artifact_digest"] == "sha256:" + hashlib.sha256(raw).hexdigest()
        destination.write_bytes(raw)
        return {
            "source": source,
            "run": run,
            "artifact": artifact,
            "attempt": 1,
            "zip_sha256": hashlib.sha256(raw).hexdigest(),
            "kind": kwargs["kind"],
        }

    def qualified(archive: Path, **kwargs: Any) -> dict[str, Any]:
        assert archive.is_file() and kwargs["current"] is True
        assert kwargs["producer_recipe"] == sources["deploy/alertmanager/Containerfile"]
        return {
            "root_inputs": {
                "source.tar.gz": "81e69f87954aedb557ed67d9ef0218a1c0c9b9e0c3184c9ddffe07bd247239fc",
                "ui.tar.gz": "3d6b13c5af094724e0bed8f757399e08af44d40d6c6cd87392a1f8ee6ed1e457",
            },
            "plan": {
                "assembly_argv": [
                    "--build-context",
                    transport.BASE
                    + "=oci-layout:///inputs/base-layout@<UNOBSERVED_CURRENT_EXPORT>",
                ]
            },
        }

    def support(archive: Path, destination: Path, **kwargs: Any) -> dict[str, Any]:
        assert archive.is_file() and kwargs["qualification"]["source"] == h
        assert kwargs["support_binding"]["source"] == h
        destination.mkdir()
        (destination / "trivy").write_bytes(b"synthetic scanner")
        return {
            "probe": {},
            "scanner": scanner,
            "base": {"actual_local_OCI_descriptor": {"digest": "sha256:" + "b" * 64}},
        }

    def candidate(
        archive: Path,
        destination: Path,
        source: dict[str, bytes],
        inspected: dict[str, Any],
        support: Path,
        **kwargs: Any,
    ) -> dict[str, Any]:
        assert archive.is_file() and source == sources and support.is_dir()
        assert (
            inspected["plan"]["assembly_argv"][1]
            == transport.BASE + "=oci-layout:///inputs/base-layout@sha256:" + "b" * 64
        )
        assert kwargs["merged_producer"]["source"] == h
        assert kwargs["merged_material"]["source"] == h
        assert {row["path"] for row in kwargs["merged_material"]["members"]} == set(sources)
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
        (destination / "candidate.oci.tar").write_bytes(b"synthetic immutable OCI input")
        (destination / "security-evidence").mkdir()
        observed = {
            "source": h,
            "graph": dict(graph),
            "status": "OBSERVED_MERGED_H_REBUILD_SECURITY_NATIVE",
            "OCI_archive_sha256": hashlib.sha256(b"synthetic immutable OCI input").hexdigest(),
            "build_information": {},
            "security": {"scanner": scanner},
            "producer_admission": {"mode": "H"},
        }
        (destination / "candidate-observation.json").write_text(json.dumps(observed))
        return observed

    def tool(api: API, selected_root: Path, directory: Path) -> tuple[Path, dict[str, Any]]:
        assert selected_root == root
        binary = directory / "oras"
        binary.write_bytes(tool_bytes)
        return binary, {"coordinates": {"binary_sha256": hashlib.sha256(tool_bytes).hexdigest()}}

    def package(api: API) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        events.append("inventory")
        if case == "inventory":
            raise transport.QualificationError("package_complete_inventory_bound")
        digest = graph["manifest"]["digest"]
        tag = "alertmanager-0.34.2-" + digest[7:]
        present = case in ("same", "conflict") or copied
        versions = (
            [
                {
                    "id": 1,
                    "name": (
                        "sha256:" + "9" * 64
                        if case == "conflict" or case == "post-readback" and pulled_back
                        else digest
                    ),
                    "metadata": {"container": {"tags": [tag]}},
                }
            ]
            if present
            else []
        )
        return {"repository": {"id": 1043311030}, "package": {"id": 9374404}}, versions

    original_tag = transport.immutable_tag_state

    def tag(versions: list[dict[str, Any]], value: str, digest: str) -> bool:
        events.append("tag")
        return original_tag(versions, value, digest)

    def security(
        archive: Path,
        selected_graph: dict[str, Any],
        support: Path,
        work: Path,
        limits: dict[str, int],
        **kwargs: Any,
    ) -> dict[str, Any]:
        nonlocal now
        if clock_profile in ("clock-later-exact", "clock-later-excess"):
            # The latter pair exceeds 2535s in exact arithmetic, yet float subtraction
            # rounds the elapsed duration down to exactly 2535s.
            now = start + 2535
        assert sessions[0].closed and not sessions[0].private.exists() and len(sessions) == 1
        assert archive.is_file() and selected_graph == graph and support.is_dir()
        assert (
            kwargs["upstream_version"] == "0.34.2"
            and kwargs["support_report"]["scanner"] == scanner
        )
        assert not logged_in
        events.append("security")
        (work / "evidence").mkdir(parents=True)
        return {"scanner": scanner, "native_records": [{"exit": 0, "failure": None}]}

    def native(
        result: dict[str, Any], observation: Path, work: Path, limits: dict[str, int], **kwargs: Any
    ) -> dict[str, Any]:
        assert kwargs == {"producer_image": True} and result["graph"] == graph
        assert observation.is_file() and result["producer_admission"]["mode"] == "H"
        name = "pre-native" if work.name == "pre-native" else "post-native"
        assert all(api.closed and not api.private.exists() for api in sessions)
        if name == "pre-native":
            assert not logged_in and events.index("prepare-close") < events.index("security")
        else:
            assert pulled_back and events[-1] == "final-close"
        native_calls.append(name)
        events.append(name)
        (work / "evidence").mkdir(parents=True)
        return {
            "validation_scope": "merged_H_selected_image",
            "native_records": [{"exit": 0, "failure": None}],
        }

    def scan_evidence(files: Path, observed: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        assert files in {
            output / "prepare-inputs/candidate/security-evidence",
            output / "security/evidence",
        }
        assert files.is_dir() and observed["scanner"] == scanner
        assert (
            kwargs["current"] is True and kwargs["comparison_subject"] == graph["config"]["digest"]
        )
        return {"synthetic_control_only": True, "subject": graph["config"]["digest"]}

    monkeypatch.setattr(transport, "Native", PublicationNative)
    monkeypatch.setattr(transport, "GitHubRead", API)
    monkeypatch.setattr(transport, "retained_tool", tool)
    monkeypatch.setattr(transport, "existing_public_package", package)
    monkeypatch.setattr(transport, "immutable_tag_state", tag)
    monkeypatch.setattr(fetcher, "_alertmanager_host_inputs", lambda *_: {"synthetic_host": True})
    monkeypatch.setattr(fetcher, "_alertmanager_source_snapshot", source_snapshot)
    monkeypatch.setattr(fetcher, "_alertmanager_authenticated_inputs", authenticated)
    monkeypatch.setattr(fetcher, "_alertmanager_qualified_payload", qualified)
    monkeypatch.setattr(fetcher, "_alertmanager_support_payload", support)
    monkeypatch.setattr(fetcher, "_alertmanager_candidate_payload", candidate)
    monkeypatch.setattr(fetcher, "_alertmanager_candidate_graph", lambda *a, **k: dict(graph))
    monkeypatch.setattr(fetcher, "_alertmanager_candidate_scan_evidence", scan_evidence)
    monkeypatch.setattr(fetcher, "_alertmanager_final_security", security)
    monkeypatch.setattr(fetcher, "_alertmanager_native_candidate", native)
    monkeypatch.setattr(
        fetcher, "_alertmanager_pair", lambda *a, **k: pytest.fail("publication started compiler")
    )
    monkeypatch.setattr(
        fetcher, "_qualify_alertmanager_modules", lambda *a: pytest.fail("publication renewed Q")
    )
    argv = _alertmanager_proposal_arguments(output)
    argv[argv.index("build")] = "publish"
    for selector in ("--alertmanager-qualification-source", "--alertmanager-support-source"):
        argv[argv.index(selector) + 1] = h
    argv += [
        "--alertmanager-pr",
        "2494",
        "--alertmanager-candidate-run",
        "888",
        "--alertmanager-candidate-artifact",
        "777",
        "--alertmanager-candidate-source",
        h,
    ]
    denied_clock_phase = {
        "clock-short-parent": "preparation",
        "clock-nextafter-parent": "preparation",
        "clock-prep-exhausted": "preparation",
        "clock-later-excess": "pre-copy-full-native",
    }.get(clock_profile or "")
    if denied_clock_phase:
        with pytest.raises(
            RuntimeError, match="^AM_publisher_downstream_reserve_" + denied_clock_phase + "$"
        ):
            fetcher.main(argv)
        result = json.loads((output / "retained/candidate-observation.json").read_text())
        assert result["copy_attempts"] == result["copy_invocations"] == 0
        assert not logged_in and not copied and not native_calls
        assert "login" not in events and "copy" not in events
        if denied_clock_phase == "preparation":
            assert not sessions and "security" not in events
        else:
            assert len(sessions) == 1 and sessions[0].closed and "security" in events
        return

    expected = {
        "proof-retention": "synthetic publication proof retention failed",
        "primary-proof-retention": "synthetic native Git exit1",
        "unmerged": "AM_separate_human_merge_observed",
        "wrong-pr": "AM_separate_human_merge_observed",
        "foreign-pr": "AM_separate_human_merge_observed",
        "merge-invalid": "AM_separate_human_merge_observed",
        "not-ancestor": "synthetic native Git exit1",
        "shallow": "synthetic selected merge ancestry unavailable at shallow boundary",
        "source-drift": "AM_material_worktree_blob",
        "template-drift": "AM_material_worktree_blob",
        "main-before-login": "AM_exact_current_main_publication",
        "main-before-copy": "AM_exact_current_main_publication",
        "main-after-copy": "AM_current_main_after_copy",
        "inventory": "package_complete_inventory_bound",
        "conflict": "immutable_tag_existing_other_subject_HOLD",
        "denied": "synthetic denied real intended copy",
        "pullback": "blob_identity",
        "post-readback": "immutable_tag_existing_other_subject_HOLD",
        "credential-mode": "AM_owned0600_registry_config",
        "cleanup": "synthetic private cleanup failed",
    }
    if case in expected:
        with pytest.raises(OSError if case == "proof-retention" else RuntimeError) as raised:
            fetcher.main(argv)
        assert str(raised.value) == expected[case]
        if case == "primary-proof-retention":
            assert "AM publication source-proof retention failed: OSError" in raised.value.__notes__
    else:
        assert case in ("absent", "same", "descendant")
        assert fetcher.main(argv) == 0
    if clock_profile == "clock-prep-advanced":
        assert timers[0] == math.nextafter(600.0, 0.0)
    result = json.loads((output / "retained/candidate-observation.json").read_text())
    assert result["compiler_starts"] == result["logical_build_starts"] == 0
    assert "synthetic-publish-credential" not in json.dumps(result)
    early = {
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
        "inventory",
        "conflict",
    }
    successful = {"absent", "same", "descendant"}
    assert native_calls == (
        []
        if case in early
        else ["pre-native", "post-native"] if case in successful else ["pre-native"]
    )
    if case in early:
        assert "security" not in events and "login" not in events and "copy" not in events
    elif case == "main-before-login":
        assert "login" not in events and "copy" not in events
    else:
        assert events.index("security") < events.index("pre-native") < events.index("login")
    copy_cases = {
        "absent",
        "descendant",
        "denied",
        "pullback",
        "post-readback",
        "main-after-copy",
        "cleanup",
    }
    assert events.count("copy") == int(case in copy_cases)
    if case == "denied":
        assert result["copy_attempts"] == 1 and result["copy_invocations"] is None
        assert result["package_WRITE"] == "UNKNOWN_COPY_ATTEMPT_MAY_HAVE_WRITTEN"
    elif copied:
        assert result["copy_attempts"] == result["copy_invocations"] == 1
        assert result["package_WRITE"] == "OBSERVED_SUCCESSFUL_INTENDED_COPY"
    elif case == "same":
        assert result["copy_attempts"] == result["copy_invocations"] == 0
        assert result["package_WRITE"] == "UNEXERCISED_EXISTING_SAME_SUBJECT"
    else:
        assert result["copy_attempts"] == result["copy_invocations"] == 0
        assert result["package_WRITE"] == "UNPROVED"
    assert len(sessions) == (1 if case in early else 2)
    assert sessions[0].closed
    if len(sessions) == 2:
        assert sessions[1].closed is (case != "cleanup")
    if case in successful:
        assert events.index("pullback") < events.index("final-close") < events.index("post-native")
        assert result["status"] == "OBSERVED_IMMUTABLE_PUBLICATION_PULLBACK_NATIVE"
    if case == "descendant":
        assert result["publication_source_sha"] == h and result["publication_merge_sha"] == merge
    if drift_path is not None:
        assert (root / drift_path).read_bytes() != sources[drift_path]


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
        oracle["subject"].update(source=selected["source"], upstream_version="0.34.2")
        selected["source_files"][
            "deploy/alertmanager/Containerfile"
        ] = fetcher._ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
        selected["graph"]["config"]["digest"] = oracle["subject"]["config"] = "sha256:" + "b" * 64
        selected["graph"]["manifest"]["digest"] = oracle["subject"]["manifest"] = (
            "sha256:" + "c" * 64
        )
        for name, letter in (("alertmanager", "d"), ("amtool", "e")):
            selected["graph"]["files"]["usr/bin/" + name] = oracle["subject"]["binary_sha256"][
                name
            ] = (letter * 64)
            oracle["expected_modules"][name]["stdlib"] = "v1.27.3"
            oracle["expected_modules"][name]["github.com/prometheus/alertmanager"] = "0.34.2"
    monkeypatch.setattr(fetcher, "_ALERT_ACCEPTED_CANDIDATE", selected)
    monkeypatch.setattr(fetcher, "_ALERT_CURRENT_SCAN_ORACLE", oracle)
    forwarded: list[tuple[str, bool]] = []
    inventory_owner = fetcher._alertmanager_candidate_inventory
    control_owner = fetcher._alertmanager_vulnerability_control

    def inventory(
        *args: Any, current: bool = False, proof_mode: str, upstream_version: str
    ) -> dict[str, Any]:
        assert proof_mode == "accepted-live"
        assert upstream_version == ("0.34.2" if current_epoch else "0.34.1")
        forwarded.append(("candidate", current))
        return inventory_owner(
            *args, current=current, proof_mode=proof_mode, upstream_version=upstream_version
        )

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
        "Select authenticated Prometheus PR evidence",
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
    pr = _job(workflow, "prometheus-image-security-pr")
    pr_total = sum(minutes(step) for step in shared if step["name"] not in excluded)
    assert pr_total == 167 and "|| '170'" in pr["timeout-minutes"]
    selector = _named_step(shared, "Select authenticated Prometheus PR evidence")
    assert selector["timeout-minutes"] == 4 and "reserved_minutes = 167" in selector["run"]
    ci = _workflow(REPO_ROOT / ".github/workflows/ci.yml")
    lint = _job(ci, "lint")
    all_lint = _steps(lint)
    dynamic = {
        "${{ fromJSON(env.ALERTMANAGER_LINT_CHECK_MINUTES) }}": 60,
        "${{ fromJSON(env.ALERTMANAGER_GENERIC_NATIVE_MINUTES) }}": 40,
        "${{ fromJSON(env.ALERTMANAGER_PREPARATION_MINUTES) }}": int(
            ci["env"]["ALERTMANAGER_PREPARATION_MINUTES"]
        ),
    }
    lint_total = sum(
        value if type(value) is int else dynamic[value]
        for step in all_lint
        for value in (step["timeout-minutes"],)
    )
    assert lint_total == 187 and "|| '190'" in lint["timeout-minutes"]
    lint_selector = _named_step(all_lint, "Select authenticated Prometheus PR evidence")
    assert (
        lint_selector["timeout-minutes"] == 4 and "reserved_minutes = 87 +" in lint_selector["run"]
    )
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


def _caddy_source_check_function() -> str:
    """Exercise the recipe's real closed source check, not a second validator."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    start = text.index("    verify_jose_source()")
    end = text.index("    echo '4e7e6b", start)
    return text[start:end].replace("\\\n", "\n")


@pytest.mark.parametrize(
    "fault", ("valid", "missing", "extra", "symlink", "fifo", "content", "digest", "filename")
)
def test_caddy_source_check_rejects_one_material_mutation(tmp_path: Path, fault: str) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name, data in (
        ("go.mod", b"module synthetic\n"),
        ("LICENSE", b"license\n"),
        ("key.go", b"package synthetic\n"),
    ):
        (source / name).write_bytes(data)
    projection = "".join(
        sorted(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  ./{path.name}\n"
            for path in source.iterdir()
        )
    )
    digest = hashlib.sha256(projection.encode("ascii")).hexdigest()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    binaries = tmp_path / "bin"
    binaries.mkdir()
    sha = shutil.which("sha256sum")
    if sha is None:
        shasum = shutil.which("shasum")
        assert shasum is not None, "source contract needs standard SHA256 tooling"
        wrapper = binaries / "sha256sum"
        wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(shasum)} -a 256 "$@"\n')
        wrapper.chmod(0o755)
    bash = shutil.which("bash")
    assert bash is not None
    script = "set -euo pipefail\n" + _caddy_source_check_function()
    script += '\nverify_jose_source "$SOURCE" 3 "$DIGEST" observed\n'
    env = {
        "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", os.defpath),
        "SOURCE": str(source),
        "DIGEST": digest,
        "evidence": str(evidence),
        "LC_ALL": "C",
    }
    baseline = subprocess.run(
        [bash, "-c", script], env=env, capture_output=True, text=True, timeout=15
    )
    assert baseline.returncode == 0, baseline.stderr
    if fault == "missing":
        (source / "LICENSE").unlink()
    elif fault == "extra":
        (source / "extra.go").write_text("package extra\n")
    elif fault == "symlink":
        (source / "key.go").unlink()
        (source / "key.go").symlink_to(source / "go.mod")
    elif fault == "fifo":
        os.mkfifo(source / "pipe")
    elif fault == "content":
        (source / "LICENSE").write_text("changed unchanged file\n")
    elif fault == "digest":
        env["DIGEST"] = "0" * 64
    elif fault == "filename":
        (source / "key.go").rename(source / "key with space.go")
    result = subprocess.run(
        [bash, "-c", script], env=env, capture_output=True, text=True, timeout=15
    )
    assert (result.returncode == 0) is (fault == "valid"), result.stderr
    expected = {
        "missing": "caddy_source_count",
        "extra": "caddy_source_count",
        "symlink": "caddy_source_nonregular",
        "fifo": "caddy_source_nonregular",
        "content": "caddy_source_digest",
        "digest": "caddy_source_digest",
        "filename": "caddy_source_path",
    }
    if fault != "valid":
        assert expected[fault] in result.stderr


@pytest.mark.parametrize("fault", ("valid", "symlink", "fifo", "root-symlink"))
def test_caddy_postbuild_stdlib_check_rejects_unmeasured_members(
    tmp_path: Path, fault: str
) -> None:
    recipe = DOCKERFILE.read_text(encoding="utf-8")
    lines = recipe.splitlines()
    post = next(
        i
        for i, line in enumerate(lines)
        if line.startswith('    verify_stdlib "$GOROOT" stdlib-post-build-tree.sha256 ')
    )
    definition = lines[post - 1]
    assert definition.startswith("    verify_stdlib()")
    assert definition == next(line for line in lines if line.startswith("    verify_stdlib()"))
    assert lines[post + 1].startswith(
        "    verify_stdlib /usr/local/go stdlib-original-post-build-tree.sha256 "
    )
    source = tmp_path / "source"
    source.mkdir()
    (source / "ordinary.go").write_bytes(b"package synthetic\n")
    projection = (
        hashlib.sha256((source / "ordinary.go").read_bytes()).hexdigest() + "  ./ordinary.go\n"
    )
    digest = hashlib.sha256(projection.encode()).hexdigest()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    binaries = tmp_path / "bin"
    binaries.mkdir()
    if shutil.which("sha256sum") is None:
        shasum = shutil.which("shasum")
        assert shasum is not None, "source contract needs standard SHA256 tooling"
        wrapper = binaries / "sha256sum"
        wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(shasum)} -a 256 "$@"\n')
        wrapper.chmod(0o755)
    bash = shutil.which("bash")
    assert bash is not None
    script = "set -euo pipefail\n" + definition.removesuffix(" \\") + "\n"
    script += 'verify_stdlib "$SOURCE" observed.sha256 "$DIGEST"\n'
    env = {
        "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", os.defpath),
        "SOURCE": str(source),
        "DIGEST": digest,
        "evidence": str(evidence),
        "LC_ALL": "C",
    }
    baseline = subprocess.run(
        [bash, "-c", script], env=env, capture_output=True, text=True, timeout=15
    )
    assert baseline.returncode == 0, baseline.stderr
    assert (evidence / "observed.sha256").read_text() == projection
    if fault == "symlink":
        # Adding an unmeasured link leaves every regular file/hash unchanged.
        (source / "unmeasured-link").symlink_to(source / "ordinary.go")
    elif fault == "fifo":
        os.mkfifo(source / "unmeasured-pipe")
    elif fault == "root-symlink":
        alias = tmp_path / "source-alias"
        alias.symlink_to(source, target_is_directory=True)
        env["SOURCE"] = str(alias)
    result = subprocess.run(
        [bash, "-c", script], env=env, capture_output=True, text=True, timeout=15
    )
    assert (result.returncode == 0) is (fault == "valid"), result.stderr


def test_caddy_patch_has_one_complete_source_carrier() -> None:
    patch_path = REPO_ROOT / "frontend/patches/go-jose-v3.0.5-CVE-2026-116587.patch"
    patch = patch_path.read_text(encoding="utf-8")
    names = re.findall(r"^diff --git a/(\S+) b/\1$", patch, re.MULTILINE)
    assert sorted(names) == sorted(
        (
            "jwk.go",
            "shared.go",
            "jws.go",
            "jwe.go",
            "jwk_test.go",
            "jws_test.go",
            "jwe_test.go",
            "shared_test.go",
        )
    )
    digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    recipe = DOCKERFILE.read_text(encoding="utf-8")
    owner_path = REPO_ROOT / "docs/security/CVE-2026-116587-caddy-go-jose.md"
    owner = owner_path.read_text(encoding="utf-8")
    assert f"echo '{digest}  /opt/go-jose-v3.patch' | sha256sum -c -" in recipe
    assert digest in owner
    assert (
        "go mod edit -replace=github.com/go-jose/go-jose/v3@v3.0.5=" "/opt/go-jose-v3.0.5-patched;"
    ) in recipe
    assert recipe.count("go mod edit") == 1
    for command in ("./...", "./compat"):
        assert f"go test -mod=readonly -count=1 -parallel=2 -timeout=300s -json {command}" in recipe
    assert recipe.index("--check --whitespace=error-all") < recipe.index("go test -mod=readonly")
    assert recipe.index("-json ./compat") < recipe.index("go build -mod=readonly")
    assert recipe.index('72 "$patched_tree" patched') < recipe.index("-json ./...")
    assert recipe.index('72 "$patched_tree" post-build') > recipe.index("go build -mod=readonly")


def test_caddy_unit_download_preserves_original_module_inputs() -> None:
    recipe = DOCKERFILE.read_text(encoding="utf-8")
    _assert_caddy_builder_stage_contract(recipe)
    start = recipe.index('72 "$patched_tree" patched;')
    end = recipe.index('72 "$patched_tree" post-unit;', start)
    unit = recipe[start:end]
    assert "      go mod download;" in unit
    assert "go mod download all" not in unit
    assert unit.index("go mod download;") < unit.index("go mod verify;")
    assert unit.index("go mod verify;") < unit.index("go test -mod=readonly")
    assert recipe.count("go mod download all;") == 3
    assert recipe.index("go mod download all;") < start
    assert '72 "$patched_tree" post-build;' in recipe
    # Returning to the scratch acquisition command must fail the current recipe
    # contract, even though module versions would remain unchanged.
    changed = recipe.replace("      go mod download;", "      go mod download all;", 1)
    with pytest.raises(AssertionError):
        _assert_caddy_builder_stage_contract(changed)


@pytest.mark.parametrize(
    "before,after",
    (
        ("@v3.0.5=/opt/go-jose", "=/opt/go-jose"),
        ("@v3.0.5=/opt/go-jose", "@v3.0.4=/opt/go-jose"),
        ("@v3.0.5=/opt/go-jose", "@v3.0.5=/wrong/go-jose"),
        ("    mkdir compat;", "    go mod edit -replace=other=/other;\n    mkdir compat;"),
        ("    cp /opt/caddy_v3_compat_test.go compat/caddy_v3_compat_test.go;", "    :;"),
        ("go test -mod=readonly -count=1 -parallel=2 -timeout=300s -json ./compat", "echo omitted"),
        ("original_tree=1c0d", "original_tree=0c0d"),
        ("patched_tree=e71a", "patched_tree=071a"),
        ("f0e1b6f4791089df", "00e1b6f4791089df"),
        ("-json ./...", "-json ./omitted"),
        ('{{join .Imports " "}}', '{{join .Deps " "}}'),
        ("{{.ImportPath}}|{{.Dir}}|", "{{.ImportPath}}||"),
        (
            "module-graph.txt import-graph.txt build-module.sha256",
            "module-graph.txt build-module.sha256",
        ),
        ("--check --whitespace=error-all", "--check --ignore-whitespace"),
        ("GOSUMDB=sum.golang.org", "GOSUMDB=off"),
        ("github.com/klauspost/compress v1.20.1", "github.com/klauspost/compress v1.20.0"),
    ),
)
def test_caddy_patched_recipe_rejects_unbound_material(before: str, after: str) -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    _assert_caddy_builder_stage_contract(text)
    assert before in text
    with pytest.raises(AssertionError):
        _assert_caddy_builder_stage_contract(text.replace(before, after, 1))


@pytest.mark.parametrize(
    "fault",
    (
        "missing-get",
        "wrong-get",
        "floating-get",
        "missing-graph-v4",
        "wrong-graph-v4",
        "missing-binary-v4",
        "wrong-binary-v4",
        "missing-graph-v3",
        "missing-binary-v3",
        "wrong-graph-count",
        "wrong-binary-count",
    ),
)
def test_caddy_published_bb5_jose_carryover_rejects_incomplete_projections(fault: str) -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    _assert_caddy_builder_stage_contract(text)
    action = "    go get github.com/go-jose/go-jose/v4@v4.1.6; \\\n"
    graph_v4 = "      'github.com/go-jose/go-jose/v4 v4.1.6' \\\n"
    binary_v4 = "      'dep github.com/go-jose/go-jose/v4 v4.1.6' \\\n"
    graph_v3 = "      'github.com/go-jose/go-jose/v3 v3.0.5' \\\n"
    binary_v3 = "      'dep github.com/go-jose/go-jose/v3 v3.0.5' \\\n"
    mutations = {
        "missing-get": (action, ""),
        "wrong-get": (action, action.replace("v4.1.6", "v4.1.4")),
        "floating-get": (action, action.replace("v4.1.6", "latest")),
        "missing-graph-v4": (graph_v4, ""),
        "wrong-graph-v4": (graph_v4, graph_v4.replace("v4.1.6", "v4.1.4")),
        "missing-binary-v4": (binary_v4, ""),
        "wrong-binary-v4": (binary_v4, binary_v4.replace("v4.1.6", "v4.1.4")),
        "missing-graph-v3": (graph_v3, ""),
        "missing-binary-v3": (binary_v3, ""),
        "wrong-graph-count": ("= '14';", "= '12';"),
        "wrong-binary-count": ("= '11';", "= '9';"),
    }
    before, after = mutations[fault]
    assert text.count(before) == 1
    with pytest.raises(AssertionError):
        _assert_caddy_builder_stage_contract(text.replace(before, after, 1))


@pytest.mark.parametrize(
    "path",
    (
        "frontend/patches/go-jose-v3.0.5-CVE-2026-116587.patch",
        "frontend/patches/caddy_v3_compat_test.go",
        "frontend/patches/go1.26.10-http-connection-nominations.patch",
        "frontend/patches/go_http_connection_nominations_test.go",
    ),
)
def test_caddy_patch_inputs_select_job_and_are_measured(path: str) -> None:
    workflow = _workflow(FRONTEND_WORKFLOW)
    changes = _job(workflow, "changes")
    filter_step = next(step for step in _steps(changes) if "filters" in step.get("with", {}))
    filters = yaml.safe_load(filter_step["with"]["filters"])
    assert path in filters["caddy"]
    recipe = DOCKERFILE.read_text(encoding="utf-8")
    assert Path(path).name in recipe


@pytest.mark.parametrize(
    "rows",
    (
        "",
        "github.com/go-jose/go-jose/v3@=>/opt/go-jose-v3.0.5-patched@\n",
        "github.com/go-jose/go-jose/v3@v3.0.4=>/opt/go-jose-v3.0.5-patched@\n",
        "github.com/go-jose/go-jose/v3@v3.0.5=>/wrong@\n",
        "github.com/go-jose/go-jose/v3@v3.0.5=>/opt/go-jose-v3.0.5-patched@v3.0.6\n",
        "github.com/go-jose/go-jose/v3@v3.0.5=>/opt/go-jose-v3.0.5-patched@\nother@v1=>/other@\n",
    ),
)
def test_caddy_module_replacement_consumer_rejects_metadata_drift(
    tmp_path: Path, rows: str
) -> None:
    recipe = DOCKERFILE.read_text(encoding="utf-8")
    check = next(line for line in recipe.splitlines() if "{{.Path}}@{{.Version}}=>" in line)
    command = check.removesuffix(" \\")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    go = binaries / "go"
    go.write_text('#!/bin/sh\nprintf "%s" "$MODULE_ROWS"\n')
    go.chmod(0o755)
    bash = shutil.which("bash")
    assert bash is not None
    env = {
        "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", os.defpath),
        "MODULE_ROWS": "github.com/go-jose/go-jose/v3@v3.0.5=>/opt/go-jose-v3.0.5-patched@\n",
    }
    baseline = subprocess.run([bash, "-ec", command], env=env, capture_output=True, timeout=10)
    assert baseline.returncode == 0
    env["MODULE_ROWS"] = rows
    rejected = subprocess.run([bash, "-ec", command], env=env, capture_output=True, timeout=10)
    assert rejected.returncode != 0


@pytest.mark.parametrize("mutation", ("missing", "wrong-owner", "wrong-target", "second"))
def test_caddy_binary_replacement_consumer_keeps_association(tmp_path: Path, mutation: str) -> None:
    recipe = DOCKERFILE.read_text(encoding="utf-8")
    check = next(line for line in recipe.splitlines() if "dependency=$2" in line)
    metadata = tmp_path / "build-info.txt"
    check = check.removesuffix(" \\").replace(
        "/tmp/caddy-binary-metadata", shlex.quote(str(metadata))
    )
    valid = "dep\tgithub.com/go-jose/go-jose/v3\tv3.0.5\n=>\t/opt/go-jose-v3.0.5-patched\t(devel)\n"
    metadata.write_text(valid)
    bash = shutil.which("bash")
    assert bash is not None
    baseline = subprocess.run([bash, "-ec", check], capture_output=True, timeout=10)
    assert baseline.returncode == 0
    changed = {
        "missing": "dep\tgithub.com/go-jose/go-jose/v3\tv3.0.5\n",
        "wrong-owner": valid.replace("github.com/go-jose/go-jose/v3", "other/module"),
        "wrong-target": valid.replace("/opt/go-jose-v3.0.5-patched", "/wrong"),
        "second": valid + "dep\tother/module\tv1\n=>\t/other\t(devel)\n",
    }
    metadata.write_text(changed[mutation])
    rejected = subprocess.run([bash, "-ec", check], capture_output=True, timeout=10)
    assert rejected.returncode != 0


def test_alertmanager_input_support_job_is_independent_manual_read_permissions_without_compiler() -> (
    None
):
    workflow = _workflow(CD_WORKFLOW)
    job = _job(workflow, "alertmanager-input-inspection")
    assert job["runs-on"] == "ubuntu-24.04"
    assert "needs" not in job
    assert job["permissions"] == {"contents": "read", "actions": "read", "packages": "read"}
    assert job["if"] == (
        "github.event_name == 'workflow_dispatch' "
        "&& inputs.alertmanager_mode == 'support-inspect' "
        "&& github.repository == 'Katsiarynakavaleuskaya/PulsePlate' "
        "&& (github.ref == 'refs/heads/codex/dependency-alertmanager-remediation' || github.ref == 'refs/heads/main') && github.run_attempt == 1 "
        "&& inputs.postgres_mode == 'disabled'"
    )
    step = _named_step(
        _steps(job),
        "Inspect authenticated retained Alertmanager inputs and read existing package metadata",
    )
    assert step["env"]["GH_TOKEN"] == step["env"]["GITHUB_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert '--alertmanager-stage "$ALERTMANAGER_STAGE"' in step["run"]
    for selector in ("run", "artifact", "source"):
        assert "--alertmanager-qualification-" + selector in step["run"]
    assert "docker " not in step["run"] and "go build" not in step["run"]
    assert "--alertmanager-module-qualify" not in step["run"]
    assert "prometheus" not in step["run"].lower()
    assert (
        _named_step(_steps(job), "Checkout exact Alertmanager inspection implementation")["with"][
            "persist-credentials"
        ]
        is False
    )


def test_alertmanager_support_job_covers_aggregate_budgets_and_retains_screened_API_evidence() -> (
    None
):
    workflow = _workflow(CD_WORKFLOW)
    job = _job(workflow, "alertmanager-input-inspection")
    budgets = {**workflow["env"], **job["env"]}
    tool_fetch = _named_step(
        _steps(job), "Prepare exact existing Alertmanager support scanner and Buildx CLI"
    )
    assert job["timeout-minutes"] == 60
    assert sum(step["timeout-minutes"] for step in _steps(job)) == 59
    # The distinct existing API and Native owners each retain their own cleanup.
    # Keep at least five minutes for pure data inspection and artifact upload.
    acquisition = tool_fetch["run"].count("curl -q ") * int(
        budgets["ALERTMANAGER_TOOL_FETCH_SECONDS"]
    )
    work = (
        acquisition
        + int(budgets["ALERTMANAGER_INPUT_INSPECT_SECONDS"])
        + int(budgets["ALERTMANAGER_SUPPORT_SECONDS"])
    )
    assert job["timeout-minutes"] * 60 - (work + 2 * 45) >= 5 * 60
    assert (
        0
        < int(budgets["ALERTMANAGER_TOOL_CONNECT_SECONDS"])
        <= int(budgets["ALERTMANAGER_TOOL_FETCH_SECONDS"])
    )
    assert (
        0
        < int(budgets["ALERTMANAGER_SCAN_TIMEOUT_SECONDS"])
        < int(budgets["ALERTMANAGER_SCAN_PROCESS_SECONDS"])
        <= int(budgets["ALERTMANAGER_SUPPORT_SECONDS"])
    )
    assert (
        tool_fetch["run"].count(
            '--connect-timeout "$ALERTMANAGER_TOOL_CONNECT_SECONDS" --max-time "$ALERTMANAGER_TOOL_FETCH_SECONDS"'
        )
        == 2
    )
    retained = _named_step(
        _steps(job), "Retain Alertmanager input observations without compiler authority"
    )
    prefix = "${{ runner.temp }}/alertmanager-input-inspection-${{ github.run_id }}-${{ github.run_attempt }}/"
    assert retained["if"] == "always()"
    assert retained["with"]["path"].splitlines() == [
        prefix + name
        for name in ("input-inspection.json", "github-read-evidence/", "native-support/")
    ]
    assert not any(
        value in retained["with"]["path"]
        for value in ("/private/", "/home/", "qualification.zip", "*")
    )


@pytest.mark.parametrize(
    "connect,fetch",
    [
        (None, "180"),
        ("", "180"),
        ("0", "180"),
        ("01", "180"),
        ("15", None),
        ("15", ""),
        ("15", "0"),
        ("15", "1.5"),
        ("15", " 180"),
        ("181", "180"),
    ],
)
def test_alertmanager_support_tool_budget_rejects_before_any_acquisition(
    tmp_path: Path, connect: str | None, fetch: str | None
) -> None:
    job = _job(_workflow(CD_WORKFLOW), "alertmanager-input-inspection")
    step = _named_step(
        _steps(job), "Prepare exact existing Alertmanager support scanner and Buildx CLI"
    )
    # No executables on PATH: the shell must reject invalid budget configuration
    # before attempting mktemp, curl or any other acquisition command.
    env = {
        "PATH": str(tmp_path / "absent"),
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_ENV": str(tmp_path / "env"),
    }
    for name, value in (
        ("ALERTMANAGER_TOOL_CONNECT_SECONDS", connect),
        ("ALERTMANAGER_TOOL_FETCH_SECONDS", fetch),
    ):
        if value is not None:
            env[name] = value
    result = subprocess.run(
        ["/bin/bash", "-c", step["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0 and "command not found" not in result.stderr
    assert not (tmp_path / "env").exists()


@pytest.mark.parametrize(
    "fault", [None, "empty", "source", "git-failure", "run", "artifact", "qualification-source"]
)
def test_alertmanager_inspection_shell_rejects_bad_selectors_before_reader(
    tmp_path: Path, fault: str | None
) -> None:
    step = _named_step(
        _steps(_job(_workflow(CD_WORKFLOW), "alertmanager-input-inspection")),
        "Inspect authenticated retained Alertmanager inputs and read existing package metadata",
    )
    # Keep transport stubs in this shell: selector validation must not depend
    # on launching generated executables. The existing five-second timeout
    # remains a hang guard for the finite shell program.
    program = (
        'git() { printf "%s\\n" "$GITHUB_SHA"; return "$SYNTHETIC_GIT_EXIT"; }\n'
        'python3() { printf "%s\\n" "$@" > "$READER_MARKER"; }\n' + step["run"]
    )
    marker = tmp_path / "reader.args"
    env = {
        "PATH": str(tmp_path / "absent"),
        "HOME": str(tmp_path),
        "GH_CONFIG_DIR": str(tmp_path / "gh"),
        "GH_TOKEN": "synthetic-test-token",
        "GITHUB_TOKEN": "synthetic-test-token",
        "INSPECTION_SOURCE": "b" * 40,
        "GITHUB_SHA": "b" * 40,
        "QUALIFICATION_RUN": "39018353942",
        "QUALIFICATION_ARTIFACT": "12095483900",
        "QUALIFICATION_SOURCE": "36cd171c4ebe44f63cb58d09a741b3d07098904d",
        "ALERTMANAGER_STAGE": "support-inspect",
        "SYNTHETIC_GIT_EXIT": "0",
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_RUN_ID": "456",
        "GITHUB_RUN_ATTEMPT": "1",
        "READER_MARKER": str(marker),
    }
    if fault == "empty":
        for key in ("QUALIFICATION_RUN", "QUALIFICATION_ARTIFACT", "QUALIFICATION_SOURCE"):
            env[key] = ""
    elif fault == "source":
        env["INSPECTION_SOURCE"] = "a" * 40
    elif fault == "git-failure":
        env["SYNTHETIC_GIT_EXIT"] = "1"
    elif fault == "run":
        env["QUALIFICATION_RUN"] = "latest"
    elif fault == "artifact":
        env["QUALIFICATION_ARTIFACT"] = ""
    elif fault == "qualification-source":
        env["QUALIFICATION_SOURCE"] = "HEAD"
    result = subprocess.run(
        ["/bin/bash", "-c", program],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert (result.returncode == 0) is (fault in (None, "empty")), result.stderr
    assert marker.exists() is (fault in (None, "empty"))
    if fault in (None, "empty"):
        selectors = (
            [
                "--alertmanager-qualification-run",
                env["QUALIFICATION_RUN"],
                "--alertmanager-qualification-artifact",
                env["QUALIFICATION_ARTIFACT"],
                "--alertmanager-qualification-source",
                env["QUALIFICATION_SOURCE"],
            ]
            if fault is None
            else []
        )
        assert marker.read_text().splitlines() == [
            "-m",
            "scripts.ci.fetch_docker_source_artifacts",
            "--artifact",
            "alertmanager",
            "--alertmanager-stage",
            "support-inspect",
            "--source-sha",
            env["INSPECTION_SOURCE"],
            *selectors,
            "--output-dir",
            str(tmp_path / "alertmanager-input-inspection-456-1"),
        ]


@pytest.fixture
def alertmanager_support_native(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    import io
    import struct
    import tarfile
    import time
    import zipfile
    from scripts.ci import fetch_docker_source_artifacts as fetcher
    from scripts.ci import prometheus_source_image as transport

    # Only external native operations are replaced. Files, digests, ELF header,
    # default scanner argv, reports and cleanup control flow use the real owner.
    data: dict[str, Any] = {
        "fault": None,
        "calls": [],
        "present": False,
        "instances": [],
        "anonymous_volume": False,
    }
    for variable in (
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
        monkeypatch.delenv(variable, raising=False)
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("trivy", "docker-buildx", "docker"):
        path = tools / name
        path.write_bytes(("synthetic selected tool: " + name).encode())
        path.chmod(0o755)
    monkeypatch.setenv("TRIVY_BIN", str(tools / "trivy"))
    monkeypatch.setenv("BUILDX_BIN", str(tools / "docker-buildx"))
    workflow = _workflow(CD_WORKFLOW)
    budgets = {**workflow["env"], **_job(workflow, "alertmanager-input-inspection")["env"]}
    for name in (
        "ALERTMANAGER_SUPPORT_SECONDS",
        "ALERTMANAGER_SCAN_TIMEOUT_SECONDS",
        "ALERTMANAGER_SCAN_PROCESS_SECONDS",
    ):
        monkeypatch.setenv(name, budgets[name])
    data["scan_timeout"] = budgets["ALERTMANAGER_SCAN_TIMEOUT_SECONDS"]
    data["scan_process"] = budgets["ALERTMANAGER_SCAN_PROCESS_SECONDS"]
    monkeypatch.setattr(
        fetcher, "_ALERT_TRIVY_SHA256", hashlib.sha256((tools / "trivy").read_bytes()).hexdigest()
    )
    monkeypatch.setattr(
        fetcher,
        "_ALERT_BUILDX_SHA256",
        hashlib.sha256((tools / "docker-buildx").read_bytes()).hexdigest(),
    )
    probe = bytearray(1173752)
    probe[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", probe, 16, 2, 62)
    struct.pack_into("<Q", probe, 32, 64)
    struct.pack_into("<HH", probe, 54, 56, 1)
    struct.pack_into("<I", probe, 64, 1)
    marker = b"BusyBox v1.38.0 (synthetic fixture)"
    probe[128 : 128 + len(marker)] = marker
    data["probe"] = bytes(probe)
    monkeypatch.setattr(fetcher, "_ALERT_PROBE_SHA256", hashlib.sha256(probe).hexdigest())
    layer_buffer = io.BytesIO()
    with tarfile.open(fileobj=layer_buffer, mode="w") as layer_tar:
        member = tarfile.TarInfo("etc/os-release")
        body = b"ID=debian\nVERSION_ID=13\n"
        member.mode, member.size = 0o644, len(body)
        layer_tar.addfile(member, io.BytesIO(body))
    layer_bytes = layer_buffer.getvalue()
    diff_id = "sha256:" + hashlib.sha256(layer_bytes).hexdigest()
    config_bytes = json.dumps(
        {
            "os": "linux",
            "architecture": "amd64",
            "rootfs": {"type": "layers", "diff_ids": [diff_id]},
        }
    ).encode()
    base_id = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
    monkeypatch.setattr(fetcher, "_ALERT_BASE_CONFIG", base_id)
    config_descriptor = {
        "mediaType": "application/vnd.oci.image.config.v1+json",
        "digest": base_id,
        "size": len(config_bytes),
    }
    layer_descriptor = {
        "mediaType": "application/vnd.oci.image.layer.v1.tar",
        "digest": diff_id,
        "size": len(layer_bytes),
    }
    manifest_bytes = json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": config_descriptor,
            "layers": [layer_descriptor],
        }
    ).encode()
    manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    base_members = {
        "oci-layout": b'{"imageLayoutVersion":"1.0.0"}',
        "index.json": json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.index.v1+json",
                "manifests": [
                    {
                        "mediaType": "application/vnd.oci.image.manifest.v1+json",
                        "digest": manifest_digest,
                        "size": len(manifest_bytes),
                    }
                ],
            }
        ).encode(),
        "blobs/sha256/" + base_id[7:]: config_bytes,
        "blobs/sha256/" + diff_id[7:]: layer_bytes,
        "blobs/sha256/" + manifest_digest[7:]: manifest_bytes,
        "manifest.json": json.dumps(
            [
                {
                    "Config": "blobs/sha256/" + base_id[7:],
                    "RepoTags": None,
                    "Layers": ["blobs/sha256/" + diff_id[7:]],
                }
            ]
        ).encode(),
    }
    base_buffer = io.BytesIO()
    with tarfile.open(fileobj=base_buffer, mode="w") as base_tar:
        for name, body in base_members.items():
            member = tarfile.TarInfo(name)
            member.mode, member.size = 0o644, len(body)
            base_tar.addfile(member, io.BytesIO(body))
    base = {
        "Id": base_id,
        "Os": "linux",
        "Architecture": "amd64",
        "RootFS": {"Type": "layers", "Layers": [diff_id]},
    }
    archive = tmp_path / "qualification.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("base-retention/base-image.tar", base_buffer.getvalue())
        zip_file.writestr("public-base-inspect.stdout", json.dumps(base))
    monkeypatch.setattr(
        fetcher, "_ALERT_Q_ZIP_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    original_which = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: str(tools / "docker") if name == "docker" else original_which(name),
    )
    original_copy = shutil.copyfile

    def copy(source: object, destination: object, **kwargs: Any) -> str:
        result = original_copy(source, destination, **kwargs)
        if (
            data["fault"] == "copied-scanner"
            and Path(destination).name == "trivy"
            or data["fault"] == "copied-buildx"
            and Path(destination).name == "docker-buildx"
        ):
            Path(destination).write_bytes(b"tampered copied tool")
        return result

    monkeypatch.setattr(shutil, "copyfile", copy)

    class Native:
        def __init__(self, evidence: Path, deadline: float, cleanup: int) -> None:
            self.evidence, self.deadline, self.cleanup = evidence, deadline, cleanup
            self.cleanup_deadline: float | None = None
            self.records: list[dict[str, Any]] = []
            data["instances"].append(self)

        def begin_cleanup(self) -> None:
            assert self.cleanup == 45
            self.cleanup_deadline = time.monotonic() + 45

        def run(
            self, argv: list[str], label: str, env: dict[str, str], *, cwd: Path, **kwargs: Any
        ) -> bytes:
            assert set(env) == {"PATH", "HOME", "DOCKER_CONFIG", "LANG"}
            assert not any(
                key in env for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "NETRC")
            )
            data["calls"].append((label, argv, kwargs))
            raw = b""
            failure = None
            try:
                if label == "base-inspect":
                    raw = json.dumps(base).encode()
                elif label == "probe-origin-inspect":
                    raw = json.dumps(
                        {
                            "Id": "sha256:53622b714941158bc20cc92a7571aef515556218eef914b7b8ec5b2a0cb6f607",
                            "Os": "linux",
                            "Architecture": "amd64",
                            "RepoDigests": [
                                "prom/alertmanager@sha256:84967b9b7ba45e38a9278d3e594305f43d4993c310df3905b51138b816c365f3"
                            ],
                        }
                    ).encode()
                elif label == "probe-owned-create-never-start":
                    data["name"] = argv[argv.index("--name") + 1]
                    data["label"] = argv[argv.index("--label") + 1].split("=", 1)[1]
                    data["present"] = True
                    # Image-declared VOLUME initialization occurs during create,
                    # including a transport failure after the server-side effect.
                    data["anonymous_volume"] = True
                    if data["fault"] == "create-after-effect":
                        raise RuntimeError("synthetic create transport failure")
                    raw = ("a" * 64 + "\n").encode()
                elif label == "probe-native-copy":
                    path = Path(argv[-1])
                    path.write_bytes(data["probe"])
                    path.chmod(0o755)
                elif label == "retain-known-vulnerable-control":
                    Path(argv[argv.index("--output") + 1]).write_bytes(
                        b"synthetic old image control export"
                    )
                elif label == "buildx-version-only":
                    raw = b"github.com/docker/buildx v0.37.0 synthetic\n"
                elif label == "buildx-help-only":
                    raw = b"--build-context --network --output\n"
                elif label == "scanner-version":
                    raw = b'{"Version":"0.74.0"}'
                elif label == "scanner-DB-acquisition":
                    db = Path(argv[argv.index("--cache-dir") + 1]) / "db"
                    db.mkdir(parents=True)
                    (db / "trivy.db").write_bytes(b"synthetic database")
                    (db / "metadata.json").write_text(
                        '{"Version":2,"UpdatedAt":"2026-10-17T00:00:00Z"}'
                    )
                elif "--output" in argv:
                    assert kwargs["maximum_seconds"] == int(data["scan_process"])
                    assert argv[argv.index("--timeout") + 1] == data["scan_timeout"] + "s"
                    for flag in (
                        "--offline-scan",
                        "--skip-db-update",
                        "--list-all-pkgs",
                        "--skip-vex-repo-update",
                    ):
                        assert flag in argv
                    assert argv[argv.index("--scanners") + 1] == "vuln,secret"
                    assert argv[argv.index("--severity") + 1] == "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL"
                    if data["fault"] == "scanner-error":
                        raise RuntimeError("synthetic scanner exit2")
                    if data["fault"] == "timeout":
                        raise TimeoutError("synthetic scanner timeout")
                    subject = argv[-1]
                    # v0.74.0 Report.Results omitempty preserves the actual zero shape.
                    report: dict[str, Any] = {
                        "SchemaVersion": 2,
                        "ArtifactName": subject,
                        "ArtifactType": "filesystem",
                    }
                    if label == "secret-positive":
                        report["Results"] = [
                            {
                                "Target": "credentials.txt",
                                "Class": "secret",
                                "Secrets": [{"RuleID": "github-pat", "Severity": "CRITICAL"}],
                            }
                        ]
                        if data["fault"] == "positive-missing":
                            report["Results"] = []
                        elif data["fault"] == "positive-omitted":
                            report.pop("Results")
                    elif label == "base-full-supported-scan":
                        report["ArtifactType"] = "container_image"
                        report["Metadata"] = {"ImageID": base_id}
                        report["Results"] = [
                            {
                                "Target": "debian",
                                "Class": "os-pkgs",
                                "Type": "debian",
                                "Packages": [{"Name": "base-files", "Version": "1"}],
                                "Vulnerabilities": [],
                            }
                        ]
                        if data["fault"] == "base-target":
                            report["Metadata"]["ImageID"] = "sha256:" + "f" * 64
                        elif data["fault"] == "omitted-base":
                            report["Results"] = []
                        elif data["fault"] == "absent-base":
                            report.pop("Results")
                        elif data["fault"] == "secret":
                            report["Results"][0]["Secrets"] = [{"RuleID": "synthetic"}]
                        elif data["fault"] == "high":
                            report["Results"][0]["Vulnerabilities"] = [
                                {
                                    "VulnerabilityID": "CVE-synthetic",
                                    "PkgName": "base-files",
                                    "InstalledVersion": "1",
                                    "Severity": "HIGH",
                                }
                            ]
                    elif label == "known-vulnerable-full-control":
                        report["ArtifactType"] = "container_image"
                        report["Metadata"] = {
                            "ImageID": "sha256:53622b714941158bc20cc92a7571aef515556218eef914b7b8ec5b2a0cb6f607"
                        }
                        report["Results"] = [
                            {
                                "Target": target,
                                "Class": "lang-pkgs",
                                "Type": "gobinary",
                                "Packages": [
                                    {"Name": "stdlib", "Version": "v1.26.8"},
                                    {"Name": "golang.org/x/net", "Version": "v0.58.0"},
                                    {"Name": "google.golang.org/grpc", "Version": "v1.83.1"},
                                ],
                                "Vulnerabilities": [
                                    {
                                        "VulnerabilityID": cve,
                                        "PkgIdentifier": {"PURL": purl},
                                        "Severity": "HIGH",
                                    }
                                    for cve, purl in (
                                        (
                                            "CVE-2026-84445",
                                            "pkg:golang/google.golang.org/grpc@v1.83.1",
                                        ),
                                        ("CVE-2026-78669", "pkg:golang/golang.org/x/net@v0.58.0"),
                                        ("CVE-2026-78669", "pkg:golang/stdlib@v1.26.8"),
                                        ("CVE-2026-78667", "pkg:golang/stdlib@v1.26.8"),
                                        ("CVE-2026-97031", "pkg:golang/stdlib@v1.26.8"),
                                    )
                                ],
                            }
                            for target in ("bin/alertmanager", "bin/amtool")
                        ]
                        if data["fault"] == "vulnerability-control-missing":
                            report["Results"].pop()
                    if data["fault"] == label + "-null":
                        report["Results"] = None
                    elif data["fault"] == label + "-scalar":
                        report["Results"] = "invalid"
                    # The pinned scanner has no standalone BusyBox recognizer;
                    # a real empty supported domain is not fabricated as a busybox Package.
                    Path(argv[argv.index("--output") + 1]).write_text(
                        "{" if data["fault"] == "malformed" else json.dumps(report)
                    )
                    if data["fault"] == "DB-drift":
                        (Path(argv[argv.index("--cache-dir") + 1]) / "db/trivy.db").write_bytes(
                            b"changed DB"
                        )
                elif label in ("support-cleanup-census", "support-cleanup-absence"):
                    assert kwargs["cleaning"] is True
                    raw = ("a" * 64 + "\n").encode() if data["present"] else b""
                elif label == "support-cleanup-inspect":
                    raw = json.dumps(
                        {
                            "Id": "a" * 64,
                            "Name": "/" + data["name"],
                            "Config": {
                                "Labels": {"pulseplate.alertmanager-support": data["label"]}
                            },
                        }
                    ).encode()
                elif label == "support-cleanup-remove":
                    data["present"] = False
                    if "--volumes" in argv:
                        data["anonymous_volume"] = False
                else:
                    assert label in ("base-load", "probe-public-origin-pull"), label
                return raw
            except BaseException as error:
                failure = type(error).__name__
                raise
            finally:
                self.records.append(
                    {
                        "argv": argv,
                        "environment": env,
                        "exit": 0 if failure is None else 2,
                        "failure": failure,
                        "cwd": str(cwd),
                    }
                )

    monkeypatch.setattr(transport, "Native", Native)
    data.update({"archive": archive, "output": tmp_path, "fetcher": fetcher})
    return data


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("copied-scanner", "AM_copied_scanner_bytes"),
        ("copied-buildx", "AM_copied_Buildx_bytes"),
        ("positive-missing", "AM_secret_positive_or_negative_control"),
        ("positive-omitted", "AM_scan_native_schema"),
        ("absent-base", "AM_scan_native_schema"),
        ("secret-negative-null", "AM_scan_native_schema"),
        ("secret-negative-scalar", "AM_scan_native_schema"),
        ("probe-full-supported-scan-null", "AM_scan_native_schema"),
        ("probe-full-supported-scan-scalar", "AM_scan_native_schema"),
        ("base-target", "AM_base_scan_exact_subject"),
        ("omitted-base", "AM_base_supported_OS_inventory_missing"),
        ("secret", "AM_support_secret_HOLD"),
        ("high", "AM_new_blocking_support_finding_HOLD"),
        ("DB-drift", "AM_scanner_or_DB_drift"),
        ("create-after-effect", "synthetic create transport failure"),
        ("scanner-error", "synthetic scanner exit2"),
        ("timeout", "synthetic scanner timeout"),
        ("vulnerability-control-missing", "AM_known_vulnerable_control_inventory_changed_HOLD"),
    ],
)
def test_alertmanager_native_support_keeps_unsupported_scopes_and_failures_explicit(
    alertmanager_support_native: dict[str, Any], fault: str | None, diagnostic: str
) -> None:
    data = alertmanager_support_native
    data["fault"] = fault
    error_type = TimeoutError if fault == "timeout" else RuntimeError
    with pytest.raises(error_type, match=diagnostic):
        data["fetcher"]._alertmanager_support_observation(
            data["archive"], data["output"], current=False
        )
    assert data["present"] is False
    for label, argv, _ in data["calls"]:
        assert "start" not in argv and "run" not in argv and "--bootstrap" not in argv
        assert "build" not in argv or "--help" in argv
    if fault == "create-after-effect":
        removals = [argv for label, argv, _ in data["calls"] if label == "support-cleanup-remove"]
        assert len(removals) == 1
        assert removals[0][-4:] == ["rm", "--force", "--volumes", "a" * 64]
        assert data["anonymous_volume"] is False


@pytest.mark.parametrize(
    "scan_seconds,process_seconds", [(None, None), ("1", "2"), ("97", "123"), ("299", "330")]
)
def test_alertmanager_native_supported_empty_probe_is_bounded_observation_not_acceptance(
    alertmanager_support_native: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    scan_seconds: str | None,
    process_seconds: str | None,
) -> None:
    data = alertmanager_support_native
    for variable, key, value in (
        ("ALERTMANAGER_SCAN_TIMEOUT_SECONDS", "scan_timeout", scan_seconds),
        ("ALERTMANAGER_SCAN_PROCESS_SECONDS", "scan_process", process_seconds),
    ):
        if value is not None:
            monkeypatch.setenv(variable, value)
            data[key] = value
    observed = data["fetcher"]._alertmanager_support_observation(
        data["archive"], data["output"], current=False
    )
    assert data["present"] is False and observed["owned_container_absence_observed"] is True
    assert observed["compiler_starts"] == observed["logical_build_starts"] == 0
    assert observed["secret_controls"]["positive"]["rule"] == "github-pat"
    assert observed["vulnerability_control"]["known_HIGH_occurrences"] == 10
    assert (
        observed["probe_scan"]["packages"] == [] and "not" not in observed["support_status"].lower()
    )
    assert "no standalone BusyBox" in observed["probe_scan"]["support_limit"]
    assert observed["final_candidate_acceptance"] == "UNACHIEVED_NO_CANDIDATE_OR_BUILD"
    assert (data["output"] / "native-support/artifact-payload-members.json").is_file()
    evidence = data["output"] / "native-support/evidence"
    assert "Results" not in json.loads((evidence / "secret-negative.private.json").read_text())
    assert "Results" not in json.loads(
        (evidence / "probe-full-supported-scan.private.json").read_text()
    )


@pytest.mark.parametrize(
    "scan_seconds,process_seconds",
    [
        (None, "330"),
        ("", "330"),
        ("0", "330"),
        ("0300", "330"),
        ("300\n", "330"),
        ("1.5", "330"),
        ("300", None),
        ("300", ""),
        ("300", "0"),
        ("300", "false"),
        ("330", "330"),
        ("331", "330"),
        ("301", "330"),
        ("300", "331"),
        ("300", "1801"),
        ("9999", "10000"),
    ],
)
def test_alertmanager_scan_budget_is_required_canonical_and_bounded_before_native(
    alertmanager_support_native: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    scan_seconds: str | None,
    process_seconds: str | None,
) -> None:
    data = alertmanager_support_native
    for variable, value in (
        ("ALERTMANAGER_SCAN_TIMEOUT_SECONDS", scan_seconds),
        ("ALERTMANAGER_SCAN_PROCESS_SECONDS", process_seconds),
    ):
        if value is None:
            monkeypatch.delenv(variable)
        else:
            monkeypatch.setenv(variable, value)
    with pytest.raises(RuntimeError, match="AM_support_scan_budgets"):
        data["fetcher"]._alertmanager_support_observation(
            data["archive"], data["output"], current=False
        )
    assert data["calls"] == [] and data["instances"] == []
    assert not (data["output"] / "native-support").exists()


def test_alertmanager_native_support_malformed_report_cannot_be_a_negative_control(
    alertmanager_support_native: dict[str, Any],
) -> None:
    data = alertmanager_support_native
    data["fault"] = "malformed"
    with pytest.raises(ValueError):
        data["fetcher"]._alertmanager_support_observation(
            data["archive"], data["output"], current=False
        )
    assert data["present"] is False


@pytest.mark.parametrize("fault", [None, "missing-tool", "not-directory", "denied"])
def test_alertmanager_precompiler_capability_is_bounded_readonly_permission_observation(
    monkeypatch: pytest.MonkeyPatch,
    fault: str | None,
) -> None:
    """Execute the workflow's actual fixed capability block with synthetic IO."""
    import ast
    import subprocess

    smoke = _named_step(
        _steps(_job(_workflow(CD_WORKFLOW), "alertmanager-candidate-build")),
        "Verify isolated AM host import capability before effects",
    )["run"]
    source = smoke.split("# Read-only prerequisite observation;", 1)[1]
    source = source[source.index("import os\n") : source.index("print(json.dumps({")]
    tree = ast.parse(source)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: None if fault == "missing-tool" and name == "install" else "/absolute/" + name,
    )
    real_is_dir = Path.is_dir

    def is_dir(path: Path) -> bool:
        return (
            fault != "not-directory" if path == Path("/run/systemd/system") else real_is_dir(path)
        )

    monkeypatch.setattr(Path, "is_dir", is_dir)

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(argv)
        assert argv == ["/absolute/sudo", "-n", "/absolute/test", "-w", "/run/systemd/system"]
        assert kwargs == {
            "env": {"PATH": os.defpath, "LANG": "C"},
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "timeout": 5,
            "check": True,
        }
        if fault == "denied":
            raise subprocess.CalledProcessError(1, argv)
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", run)
    if fault is None:
        exec(compile(tree, "<cd.yml:AM-readonly-prerequisite>", "exec"), {"Path": Path})
    else:
        with pytest.raises(subprocess.CalledProcessError if fault == "denied" else AssertionError):
            exec(compile(tree, "<cd.yml:AM-readonly-prerequisite>", "exec"), {"Path": Path})
    assert len(calls) == (0 if fault in {"missing-tool", "not-directory"} else 1)
    assert "install/start is native evidence" in smoke


def _caddy_inline(name: str) -> str:
    source = _named_step(_steps(_job(_workflow(FRONTEND_WORKFLOW), "caddy-contract")), name)["run"]
    return source.split("python3 - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


def _caddy_budget_fixture(runner: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    if sys.platform == "darwin":
        monkeypatch.setattr(Path, "read_text", _caddy_fixture_reader(str(uuid4())))
    runner.mkdir(parents=True, exist_ok=True)
    for key, value in _job(_workflow(FRONTEND_WORKFLOW), "caddy-contract")["env"].items():
        if key != "CADDY_CONFIGURED_JOB_MINUTES":
            monkeypatch.setenv(key, str(value))
    monkeypatch.setenv("CADDY_CONFIGURED_JOB_MINUTES", "")
    monkeypatch.setenv("RUNNER_TEMP", str(runner))
    monkeypatch.setenv("GITHUB_ENV", str(runner / "github-env"))
    exec(
        compile(
            _caddy_inline("Initialize bounded Caddy runner clock"),
            "<actual-Caddy-budget-init>",
            "exec",
        ),
        {},
    )
    return json.loads((runner / "caddy-admission/admission.json").read_text())


@pytest.mark.parametrize("fault", [None, "post-get", "post-download", "go.mod", "swapped"])
def test_caddy_metadata_advance_checks_each_raw_sum_before_capture(
    tmp_path: Path, fault: str | None
) -> None:
    source = _caddy_inline("Qualify Caddy compiler and two independent root derivations")
    advance = source.split("advance = '''", 1)[1].split("'''", 1)[0]
    original, final = "post get witness\n", "post download witness\n"
    pinned = (
        "f5d9289fa0e27604a936ed5e35368db876398dac62154b9a6af9d0d2a891f7d9",
        "be8f44f7e591bcaa54412fe5f3061235596be2faf9bd3f5fdece0106fea45338",
    )
    for digest, value in zip(pinned, (original, final), strict=True):
        assert advance.count(digest) == 1
        advance = advance.replace(digest, hashlib.sha256(value.encode()).hexdigest())
    output = tmp_path / "output"
    output.mkdir()
    env = {
        "PATH": os.defpath + ":/sbin",
        "OUTPUT": str(output),
        "POST_GET_SUM": (
            final if fault == "swapped" else original + ("drift" if fault == "post-get" else "")
        ),
        "POST_DOWNLOAD_SUM": (
            original
            if fault == "swapped"
            else final + ("drift" if fault == "post-download" else "")
        ),
        "MOD_AFTER_DOWNLOAD": "changed" if fault == "go.mod" else "original",
    }
    stubs = """go() {
        if [ "$1" = get ]; then
            printf '%s' "$POST_GET_SUM" > go.sum
            printf '%s' original > go.mod
        elif [ "$*" = 'mod download all' ]; then
            printf '%s' "$POST_DOWNLOAD_SUM" > go.sum
            printf '%s' "$MOD_AFTER_DOWNLOAD" > go.mod
        else
            return 88
        fi
    }
    capture() { [ "$1" = final ] && : > "$OUTPUT/captured-final"; }
    """
    result = subprocess.run(
        ["/bin/bash", "-euc", stubs + advance.replace("/output", "output")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert (output / "post-get-go.sum").read_text() == env["POST_GET_SUM"]
    if fault is None:
        assert result.returncode == 0, result.stderr
        assert (output / "captured-final").exists()
    else:
        assert result.returncode == 1
        assert not (output / "captured-final").exists()
        if fault == "go.mod":
            assert b"go.mod" in result.stdout + result.stderr
        else:
            name = b"go.sum" if fault == "post-download" else b"post-get-go.sum"
            assert name + b": FAILED" in result.stdout


@pytest.mark.parametrize(
    ("fault", "diagnostic"),
    [
        (None, None),
        ("version-profile", "declared_data_value"),
        ("resolver-profile", "declared_data_value"),
        ("cache-replaced", "caddy_metadata_phase_cache_replaced"),
        ("cache-link", "caddy_metadata_phase_cache_member"),
        ("offline-input-drift", "caddy_metadata_offline_input_changed"),
        ("module-cap", "tree_size_bound"),
        ("work-cap", "tree_size_bound"),
        ("cleanup-rename", "caddy_cleanup_full_custody"),
        ("cleanup-replacement", "caddy_metadata_owned_container_survives"),
        ("cleanup-truncated", "caddy_metadata_container_inventory"),
        ("timeout", "resolver test timeout"),
        ("timeout-without-start", "resolver test timeout"),
    ],
)
def test_caddy_metadata_step_owns_full_id_watcher_and_terminal_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None, diagnostic: str | None
) -> None:
    import platform
    import time
    from contextlib import contextmanager
    from types import SimpleNamespace

    from scripts.ci import prometheus_source_image as native_owner

    step_name = "Qualify Caddy compiler and two independent root derivations"
    _caddy_budget_fixture(tmp_path, monkeypatch)
    next_env = dict(row.split("=", 1) for row in (tmp_path / "github-env").read_text().splitlines())
    aliases = {
        "CADDY_METADATA_TIMEOUT_SECONDS": "1200",
        "CADDY_METADATA_CLEANUP_SECONDS": "120",
        "CADDY_ACTION_METADATA_MINUTES": "22",
    }
    assert {key: next_env[key] for key in aliases} == aliases
    assert all(key not in os.environ for key in aliases)
    workflow_step = _named_step(
        _steps(_job(_workflow(FRONTEND_WORKFLOW), "caddy-contract")), step_name
    )
    assert workflow_step["timeout-minutes"] == "${{ fromJSON(env.CADDY_ACTION_METADATA_MINUTES) }}"
    for key, value in {
        **aliases,
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "9",
    }.items():
        monkeypatch.setenv(key, value)
    (tmp_path / "caddy-admission/admission.json").write_text(json.dumps({"current_head": "9" * 40}))
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(shutil, "which", lambda binary: "/synthetic/" + binary)
    cache = tmp_path / "scanner-cache"
    (cache / "db").mkdir(parents=True)
    for name in ("trivy.db", "metadata.json"):
        (cache / "db" / name).write_text("scanner fixture")
    real_read_bytes = Path.read_bytes

    def read_bytes(path: Path) -> bytes:
        if str(path) == "/synthetic/trivy":
            return b"synthetic scanner"
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    index = (
        b'{"manifests":[{"platform":{"architecture":"amd64","os":"linux"},"digest":"sha256:'
        + b"a" * 64
        + b'"}]}'
    )
    image = "sha256:" + "b" * 64
    real_sha256 = hashlib.sha256

    class IndexHash:
        def hexdigest(self) -> str:
            return "0525c952defebc693cdaf62cdf43afa32be5a7f377e99260642ea19c240c708e"

    monkeypatch.setattr(
        hashlib, "sha256", lambda raw=b"": IndexHash() if raw == index else real_sha256(raw)
    )
    monkeypatch.setattr(native_owner, "native_go_identity", lambda *_: {"operand": image})
    monkeypatch.setattr(caddy_surface, "validate_trivy_image_report", lambda *_: None)
    monkeypatch.setattr(caddy_surface, "CADDY_XNET062_INCUMBENT_FILES", {})
    monkeypatch.setattr(
        caddy_surface,
        "validate_caddy_xnet062_metadata",
        lambda _: {"complete_delta": [], "historical_caddy_delta": []},
    )

    def native_image_identity(actual: dict[str, Any], relation: dict[str, str]) -> None:
        assert actual["Image"] == relation["operand"]

    monkeypatch.setattr(native_owner, "native_container_image_identity", native_image_identity)

    @contextmanager
    def phase(name: str) -> Any:
        yield lambda limit: min(limit, {"COMPILER_WORK": 1100, "COMPILER_CLEANUP": 120}[name])

    monkeypatch.setattr(caddy_surface, "caddy_ci_phase", phase)
    real_inventory = native_owner.tree_inventory
    real_lstat, real_file_hash = Path.lstat, native_owner.file_hash
    snapshots: list[tuple[str, int | None]] = []

    def inventory_size(path: Path) -> Any:
        info = real_lstat(path)
        if path.name != "synthetic-inventory-size":
            return info
        size = 3 * 1024**3
        if fault == "module-cap" and path.parent.name == "modules":
            size = 4 * 1024**3 + 1
        return SimpleNamespace(st_mode=info.st_mode, st_size=size)

    def inventory_hash(path: Path, *args: Any, **kwargs: Any) -> str:
        if path.name == "synthetic-inventory-size":
            return real_sha256(path.read_bytes()).hexdigest()
        return real_file_hash(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", inventory_size)
    monkeypatch.setattr(native_owner, "file_hash", inventory_hash)

    def tree_inventory(path: Path, **options: Any) -> list[dict[str, Any]]:
        snapshots.append((path.name, options.get("maximum")))
        return real_inventory(path, **options)

    monkeypatch.setattr(native_owner, "tree_inventory", tree_inventory)
    active: dict[str, dict[str, Any]] = {}
    watch: list[tuple[str, Path]] = []
    commands: list[tuple[str, list[str]]] = []
    initial = {"Status": "created", "Running": False, "StartedAt": "0001-01-01T00:00:00Z"}

    class FixtureNative:
        def __init__(self, evidence: Path, deadline: float, cleanup: int) -> None:
            assert evidence.parent == tmp_path / "caddy-xnet062-metadata"
            assert 1199 <= deadline - time.monotonic() <= 1200
            assert cleanup == 120
            self.deadline = deadline
            self.cleanup_deadline = None
            self.records: list[dict[str, Any]] = []

        def begin_cleanup(self) -> None:
            self.cleanup_deadline = self.deadline + 120

        def run(self, argv: list[str], channel: str, env: dict[str, str], **kwargs: Any) -> bytes:
            commands.append((channel, argv))
            self.records.append({"channel": channel, "argv": argv})
            if argv[0] == "/synthetic/trivy":
                if "--output" in argv:
                    Path(argv[argv.index("--output") + 1]).write_text('{"Results":[{}]}')
                    return b""
                return b"Version: 0.74.0\n"
            assert argv[0] == "/synthetic/docker"
            command = argv[3]
            if command == "buildx":
                return index if channel == "compiler-index" else b"{}"
            if command == "pull":
                return b""
            if command == "image":
                return json.dumps(
                    [{"Id": image, "Os": "linux", "Architecture": "amd64", "Config": {"Env": []}}]
                ).encode()
            if command == "create":
                entry = argv.index("--entrypoint")
                name = argv[argv.index("--name") + 1]
                cid = real_sha256(name.encode()).hexdigest()
                mounts = []
                for index_arg, arg in enumerate(argv):
                    if arg == "--mount":
                        _, source, target, *flags = argv[index_arg + 1].split(",")
                        mounts.append(
                            {
                                "Type": "bind",
                                "Source": source[7:],
                                "Destination": target[7:],
                                "RW": not flags,
                            }
                        )
                active[cid] = {
                    "Id": cid,
                    "Name": "/" + name,
                    "Image": argv[entry + 2],
                    "Mounts": mounts,
                    "Config": {
                        "Cmd": argv[entry + 3 :],
                        "Entrypoint": [argv[entry + 1]],
                        "User": argv[argv.index("--user") + 1],
                        "Labels": {"pulseplate.caddy-metadata": "9"},
                        "Env": [argv[i + 1] for i, arg in enumerate(argv) if arg == "--env"],
                    },
                    "HostConfig": {
                        "NetworkMode": "none" if "--network" in argv else "default",
                        "ReadonlyRootfs": True,
                        "Privileged": False,
                        "CapDrop": ["ALL"],
                        "SecurityOpt": ["no-new-privileges"],
                        "NanoCpus": 2000000000,
                        "Memory": 2147483648,
                        "PidsLimit": 128,
                        "OomKillDisable": False,
                    },
                    "State": dict(initial),
                }
                return (cid + "\n").encode()
            if command == "ps":
                assert argv[4:] == ["--all", "--no-trunc", "--format", "{{.ID}}\t{{.Names}}"]
                pairs = [(cid, value["Name"][1:]) for cid, value in active.items()]
                if channel == "cleanup-inventory" and fault in {
                    "cleanup-rename",
                    "cleanup-replacement",
                }:
                    assert len(pairs) == 1
                    cid, name = pairs[0]
                    pairs = (
                        [(cid, "foreign-name")] if fault == "cleanup-rename" else [("f" * 64, name)]
                    )
                raw = "".join(f"{cid}\t{name}\n" for cid, name in pairs).encode()
                return (
                    raw[:-1]
                    if channel == "cleanup-inventory" and fault == "cleanup-truncated"
                    else raw
                )
            cid = argv[-1]
            assert cid in active
            container = active[cid]
            if command == "inspect":
                return json.dumps([container]).encode()
            if command == "start":
                assert kwargs.get("cleaning", False) is False
                assert 0 < self.deadline - time.monotonic() <= 1100
                container["State"].update(
                    Status="exited",
                    Running=False,
                    StartedAt="2026-11-07T18:00:00.123456789Z",
                    OOMKilled=False,
                    ExitCode=0,
                )
                container["HostConfig"]["OomKillDisable"] = None
                if channel == "compiler-native-version":
                    assert "watched_output" not in kwargs
                    if fault == "version-profile":
                        container["HostConfig"]["PidsLimit"] = 129
                    return b"go version go1.26.10 linux/amd64\n"
                paths = {m["Destination"]: Path(m["Source"]) for m in container["Mounts"]}
                watch.append((channel, kwargs["watched_output"]))
                assert kwargs["watched_output"] == paths["/work"].parent
                if channel == "a-incumbent-online-native":
                    if fault == "resolver-profile":
                        container["Config"]["Cmd"][1] = "changed"
                    elif fault == "cache-replaced":
                        paths["/cache"].rename(paths["/cache"].with_name("old-cache"))
                        paths["/cache"].mkdir()
                    elif fault == "cache-link":
                        (paths["/cache"] / "foreign").symlink_to(paths["/modules"])
                    elif fault in {"timeout", "timeout-without-start"}:
                        if fault == "timeout":
                            container["State"].update(Status="running", Running=True)
                        else:
                            container["State"] = dict(initial)
                        raise TimeoutError("resolver test timeout")
                if fault == "offline-input-drift" and channel == "a-incumbent-offline-native":
                    (paths["/modules"] / "drift").write_text("changed offline")
                if channel.endswith("-online-native"):
                    target = paths["/work"] if fault == "work-cap" else paths["/modules"]
                    (target / "synthetic-inventory-size").write_text("small fixture, large lstat")
                phase_name = "final" if "-final-" in channel else "incumbent"
                for lock in ("go.mod", "go.sum"):
                    (paths["/output"] / f"{phase_name}-{lock}").write_text(lock + phase_name)
                return b""
            if command == "stop":
                assert argv[4:7] == ["--time", "10", cid] and kwargs["cleaning"] is True
                assert kwargs["maximum_seconds"] == 20 and container["State"]["Running"] is True
                container["State"].update(Status="exited", Running=False)
                return b""
            assert command == "rm" and argv[4:] == [cid]
            assert container["State"]["Running"] is False
            del active[cid]
            return b""

    monkeypatch.setattr(native_owner, "Native", FixtureNative)
    source = _caddy_inline(step_name)
    assert source.count('"/tmp/trivy-cache-caddy-metadata"') == 1
    source = source.replace('"/tmp/trivy-cache-caddy-metadata"', repr(str(cache)))
    program = compile(source, "<actual-Caddy-metadata>", "exec")
    if diagnostic is None:
        exec(program, {})
    else:
        with pytest.raises((RuntimeError, ValueError, TimeoutError), match=diagnostic):
            exec(program, {})
    root = tmp_path / "caddy-xnet062-metadata"
    report = json.loads((root / "evidence/qualification.json").read_text())
    channels = [channel for channel, _ in commands]
    if fault is None:
        assert len(watch) == 8 and set(path.name for _, path in watch) == {"a", "b"}
        assert snapshots.count(("modules", 4 * 1024**3)) == snapshots.count(("work", None)) == 8
        assert not list(root.glob("*/cache-*")) and not active
        assert all(
            (root / lane / directory).is_dir()
            for lane in ("a", "b")
            for directory in ("work", "modules", "output")
        )
        assert channels[-1] == "cleanup-absence"
        assert report["status"] == caddy_surface.CADDY_XNET062_METADATA_SUCCESS
    else:
        assert "status" not in report
        cleanup_faults = {"cleanup-rename", "cleanup-replacement", "cleanup-truncated"}
        assert "a-final-online-native" not in channels or fault in cleanup_faults
        if fault in cleanup_faults | {"timeout-without-start"}:
            assert "cleanup_failure" in report and active
        if fault in {"timeout", "timeout-without-start"}:
            assert report["failure"] == "TimeoutError"
        if fault == "timeout":
            assert not active and sum(argv[3:4] == ["stop"] for _, argv in commands) == 1
        if fault == "timeout-without-start":
            assert not any(argv[3:4] == ["stop"] for _, argv in commands)
        if fault == "cache-replaced":
            assert (root / "a/cache-incumbent-online").is_dir()
            assert (root / "a/old-cache").is_dir()


@pytest.mark.parametrize(
    ("fault", "diagnostic"),
    [
        (None, None),
        ("reuse", None),
        ("historical-status", "metadata predecessor"),
        ("cleanup-failed", "metadata predecessor"),
        ("skipped-metadata", "metadata predecessor"),
        ("wrong-source", "metadata predecessor"),
        ("wrong-run", "metadata predecessor"),
        ("wrong-attempt", "metadata predecessor"),
        ("wrong-recipe", "metadata predecessor"),
        ("false-zero", "metadata predecessor"),
        ("float-zero", "metadata predecessor"),
        ("wrong-b-epoch", "metadata epoch"),
        ("flat-phase", "final modules missing"),
        ("wrong-sum", "ordinary modules differ"),
        ("duplicate-binary-module", "ordinary modules differ"),
        ("missing-binary-module", "ordinary modules differ"),
    ],
)
def test_caddy_retention_requires_current_completed_metadata_before_candidate_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None, diagnostic: str | None
) -> None:
    from contextlib import nullcontext

    mode = "reuse" if fault == "reuse" else "build"
    admission: dict[str, Any] = {
        "mode": mode,
        "current_head": "9" * 40,
        "current_run_id": 9,
        "current_run_attempt": 1,
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "inputs": {},
        "producer": {"run_id": 7},
        "original_candidate": {"image_config_id": "image", "binary_sha256": "binary"},
    }
    (tmp_path / "caddy-admission").mkdir()
    (tmp_path / "caddy-admission/admission.json").write_text(json.dumps(admission))
    observation = tmp_path / "observation"
    (observation / "native-projections").mkdir(parents=True)
    state = observation / "state.json"
    state.write_text(
        json.dumps(
            {
                "docker": "/synthetic/docker",
                "image_config_id": "image",
                "binary_sha256": "binary",
                "build_evidence": str(observation / "build-evidence"),
            }
        )
    )
    metadata = tmp_path / "caddy-xnet062-metadata"
    (metadata / "evidence").mkdir(parents=True)
    (metadata / "a/output").mkdir(parents=True)
    (metadata / "b/output").mkdir(parents=True)
    root, net, original_v3 = (
        "github.com/caddyserver/caddy/v2",
        "golang.org/x/net",
        "github.com/go-jose/go-jose/v3",
    )
    modules = {
        root: {"Version": "v2.11.9", "Sum": "h1:caddy"},
        net: {"Version": "v0.62.0", "Sum": "h1:net"},
        original_v3: {"Version": "v3.0.5", "Sum": "h1:v3"},
    }
    packages = "".join(json.dumps({"Module": {"Path": name}}) + "\n" for name in modules)
    for lane in ("a", "b"):
        (metadata / lane / "output/final-packages.json").write_text(packages)
    qualification: dict[str, Any] = {
        "status": caddy_surface.CADDY_XNET062_METADATA_SUCCESS,
        "failure": None,
        "source_head": "9" * 40,
        "run_id": 9,
        "run_attempt": 1,
        "recipe_sha256": hashlib.sha256(DOCKERFILE.read_bytes()).hexdigest(),
        "go_build_invocations": 0,
        "derivations": {
            lane: {
                "epoch": caddy_surface.CADDY_XNET062_METADATA_EPOCH,
                "phases": {"final": {"modules": modules}},
            }
            for lane in ("a", "b")
        },
    }
    mutations = {
        "historical-status": ("status", "observed_counterfactual_metadata_only"),
        "cleanup-failed": ("cleanup_failure", "QualificationError"),
        "wrong-source": ("source_head", "8" * 40),
        "wrong-run": ("run_id", 8),
        "wrong-attempt": ("run_attempt", 2),
        "wrong-recipe": ("recipe_sha256", "8" * 64),
        "false-zero": ("go_build_invocations", False),
        "float-zero": ("go_build_invocations", 0.0),
    }
    if fault is not None and fault in mutations:
        key, value = mutations[fault]
        qualification[key] = value
    elif fault == "wrong-b-epoch":
        qualification["derivations"]["b"]["epoch"] = "historical"
    elif fault == "flat-phase":
        qualification["derivations"]["a"].pop("phases")
        qualification["derivations"]["a"]["final"] = {"modules": modules}
    (metadata / "evidence/qualification.json").write_text(json.dumps(qualification))
    rows = [
        f"mod {root} v2.11.9 h1:caddy",
        f"dep {original_v3} v3.0.5",
        f"dep {net} v0.62.0 h1:net",
    ]
    if fault == "wrong-sum":
        rows[-1] = f"dep {net} v0.62.0 h1:other"
    elif fault == "duplicate-binary-module":
        rows.append(rows[-1])
    elif fault == "missing-binary-module":
        rows.pop()
    binary = observation / "native-projections/build-info.txt"
    binary.write_text("\n".join(rows) + "\n")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("CADDY_OBSERVATION_STATE", str(state))
    monkeypatch.setenv(
        "CADDY_METADATA_OUTCOME", "skipped" if fault in {"reuse", "skipped-metadata"} else "success"
    )
    step_name = "Retain original Caddy candidate or current import binding"
    step = _named_step(_steps(_job(_workflow(FRONTEND_WORKFLOW), "caddy-contract")), step_name)
    assert step["env"]["CADDY_METADATA_OUTCOME"] == "${{ steps.caddy-metadata.outcome }}"
    monkeypatch.setattr(
        caddy_surface, "caddy_ci_phase", lambda _: nullcontext(lambda seconds: seconds)
    )
    source_checks: list[bytes] = []

    def source_evidence(
        path: Path, *, binary_metadata: bytes, binary_sha256: str, recipe: bytes
    ) -> None:
        assert path == observation / "build-evidence"
        assert binary_metadata == binary.read_bytes() and binary_sha256 == "binary"
        assert recipe == DOCKERFILE.read_bytes()
        source_checks.append(recipe)

    monkeypatch.setattr(caddy_surface, "validate_caddy_source_evidence", source_evidence)
    saves: list[list[str]] = []

    def save(argv: list[str], *, check: bool, timeout: int) -> None:
        assert argv[:3] == ["/synthetic/docker", "save", "--output"]
        assert argv[-1] == "pulseplate-caddy:contract" and check and timeout == 300
        saves.append(argv)
        Path(argv[3]).write_bytes(b"synthetic Docker save")

    monkeypatch.setattr(subprocess, "run", save)
    program = compile(_caddy_inline(step_name), "<actual-Caddy-retention>", "exec")
    if diagnostic is None:
        exec(program, {})
    else:
        with pytest.raises(ValueError, match=diagnostic):
            exec(program, {})
    if mode == "reuse":
        assert json.loads((tmp_path / "caddy-contract/original-producer.json").read_text()) == {
            "run_id": 7
        }
        assert source_checks == [] and saves == []
    elif fault is None:
        assert len(saves) == len(source_checks) == 1
        candidate = json.loads((observation / "candidate/candidate.json").read_text())
        assert candidate["producer_head"] == "9" * 40
        assert (
            candidate["metadata_qualification_sha256"]
            == hashlib.sha256((metadata / "evidence/qualification.json").read_bytes()).hexdigest()
        )
    else:
        assert saves == [] and not (observation / "candidate").exists()


def test_caddy_job_budget_is_complete_and_owned_only_by_existing_job() -> None:
    job = _job(_workflow(FRONTEND_WORKFLOW), "caddy-contract")
    assert job["timeout-minutes"] == "${{ fromJSON(vars.CADDY_CONTRACT_TIMEOUT_MINUTES || '225') }}"
    caps = {
        key.removeprefix("CADDY_PHASE_"): int(value)
        for key, value in job["env"].items()
        if key.startswith("CADDY_PHASE_")
    }
    assert caps == {
        "SETUP": 300,
        "ADMISSION": 600,
        "COMPILER_BOOTSTRAP": 600,
        "COMPILER_WORK": 1200,
        "COMPILER_CLEANUP": 120,
        "METADATA_UPLOAD": 180,
        "BUILD": 1800,
        "CAPTURE": 420,
        "RUNTIME_CONFIG": 420,
        "OFFICIAL_PULL": 300,
        "SOURCE16": 180,
        "FINAL_SUBJECT": 300,
        "REPORT_BINDINGS": 540,
        "CONVERSION": 60,
        "RUNTIME": 900,
        "FIXTURE": 1050,
        "SCANNER_BOOTSTRAP": 600,
        "SCANS": 1980,
        "PROCESSING": 300,
        "CONTROL_CLEANUP": 360,
        "RETENTION": 420,
        "UPLOAD": 600,
        "SAFETY": 270,
    }
    assert sum(caps.values()) == 13500
    assert caps["SCANS"] == 6 * sum(
        int(job["env"][key])
        for key in (
            "CADDY_FULL_SCAN_TIMEOUT_SECONDS",
            "CADDY_SCAN_TERM_SECONDS",
            "CADDY_SCAN_KILL_SECONDS",
            "CADDY_SCAN_BOOKKEEPING_SECONDS",
        )
    )
    assert caps["COMPILER_WORK"] == 1200 and caps["COMPILER_CLEANUP"] == 120
    assert caps["RUNTIME"] == 15 * 60 and caps["FIXTURE"] == 14 * 60 + 180 + 30
    assert caps["SAFETY"] == 270 and "TERMINATION" not in caps
    steps = _steps(job)
    for step in steps:
        if "uses" in step:
            assert "timeout-minutes" in step
    assert job["concurrency"] == {
        "group": "caddy-source-single-producer-2494",
        "cancel-in-progress": False,
    }
    build = _named_step(steps, "Build source-patched Caddy candidate")
    assert build["with"]["no-cache-filters"] == "caddy-build"
    assert build["with"]["push"] is False
    assert "steps.caddy-admission.outputs.mode == 'build'" in build["if"]
    admission = _named_step(steps, "Admit existing Caddy producer or exact retained subject")["run"]
    assert 'pr["number"] != 2494' in admission
    assert 'state["observed_build_history"] = spent' in admission
    assert "len(spent) > 4" not in admission and "no fifth" not in admission
    assert "authenticate_pr_source(proof_api, 2494," in admission
    assert (
        '"Caddy requires a real successful same-source PR2494 producer; no automatic build"'
        in admission
    )
    decision = _named_step(
        steps, "Decide source-qualified Caddy inventory and current native controls"
    )["run"]
    for required in (
        "validate_caddy_source",
        "validate_caddy_ci_report",
        "validate_caddy_control_reports",
        "validate_caddy_policy_projection",
        "observe_caddy_ci_runtime",
    ):
        if required != "validate_caddy_source":
            assert required in decision
    assert decision.index("validate_caddy_control_reports(json") < decision.index(
        "os.rename(private_candidate / name"
    )
    assert decision.index('controls["cleanup"] = True') < decision.index(
        "os.rename(private_candidate / name"
    )
    assert '"D-policy"' not in decision and "accepted_v3_rows" not in decision
    assert "ignore-policy-caddy-go-jose-v3.rego" not in FRONTEND_WORKFLOW.read_text()


@pytest.mark.parametrize(
    "fault", [None, "220", "224", "host", "exhausted-phase", "global-reserve", "clock-reset"]
)
def test_caddy_shared_budget_rejects_drift_and_preserves_cleanup_reserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from scripts.ci import check_docker_runtime_dependency_surface as owner

    runner = tmp_path / "runner"
    state = _caddy_budget_fixture(runner, monkeypatch)
    path = runner / "caddy-admission/admission.json"
    if fault in {"220", "224"}:
        other = tmp_path / "low"
        other.mkdir()
        monkeypatch.setenv("RUNNER_TEMP", str(other))
        assert fault is not None
        monkeypatch.setenv("CADDY_CONFIGURED_JOB_MINUTES", fault)
        with pytest.raises(ValueError, match="below phase ledger"):
            exec(
                compile(
                    _caddy_inline("Initialize bounded Caddy runner clock"),
                    "<actual-low-budget>",
                    "exec",
                ),
                {},
            )
        assert not (other / "caddy-admission/admission.json").exists()
        return
    if fault == "host":
        state["budget"]["boot_id"] = "different-host"
    elif fault == "exhausted-phase":
        state["budget"]["charged"]["SCANS"] = int(os.environ["CADDY_PHASE_SCANS"])
    elif fault == "global-reserve":
        state["budget"]["started"] -= 13500
    path.write_text(json.dumps(state))
    if fault is None:
        with owner.caddy_ci_phase("SCANS") as remaining:
            assert 0 < remaining(330) <= 330
        observed = json.loads(path.read_text())
        assert observed["budget"]["started"] == state["budget"]["started"]
        assert observed["budget"]["charged"]["CONTROL_CLEANUP"] == 0
        assert 0 < observed["budget"]["charged"]["SCANS"] < 1
    else:
        with pytest.raises(ValueError):
            with owner.caddy_ci_phase("SCANS"):
                if fault == "clock-reset":
                    changed = json.loads(path.read_text())
                    changed["budget"]["started"] += 1
                    path.write_text(json.dumps(changed))


@pytest.mark.parametrize("timeouts", [0, 1, 2])
def test_caddy_actual_scan_runner_contains_work_term_kill_in_one_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, timeouts: int
) -> None:
    import ast
    from contextlib import contextmanager
    from collections.abc import Callable, Iterator
    from types import SimpleNamespace
    import signal

    tree = ast.parse(_caddy_inline("Observe all-severity Caddy native report"))
    function = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "invoke"
    )
    clock = [0.0]
    waits: list[float] = []
    signals: list[int] = []
    records: list[dict] = []

    @contextmanager
    def phase(name: str) -> Iterator[Callable[[float], float]]:
        assert name == "SCANS"
        yield lambda cap: min(cap, 330 - clock[0])

    class Child:
        pid = 12345

        def wait(self, timeout: float) -> int:
            waits.append(timeout)
            if len(waits) <= timeouts:
                clock[0] += timeout
                raise subprocess.TimeoutExpired("synthetic-scanner", timeout)
            clock[0] += 0.01
            return 0 if timeouts == 0 else -9

    def spawn(argv: list[str], **kwargs: Any) -> Child:
        assert kwargs["start_new_session"] is True
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["env"] == {"LANG": "C.UTF-8"}
        kwargs["stdout"].write(b"native fixture stdout")
        return Child()

    for key, value in {
        "CADDY_FULL_SCAN_TIMEOUT_SECONDS": "300",
        "CADDY_SCAN_TERM_SECONDS": "10",
        "CADDY_SCAN_KILL_SECONDS": "10",
        "CADDY_SCAN_BOOKKEEPING_SECONDS": "10",
    }.items():
        monkeypatch.setenv(key, value)
    namespace = {
        "control_dir": tmp_path,
        "records": records,
        "caddy_ci_phase": phase,
        "time": SimpleNamespace(monotonic=lambda: clock[0]),
        "os": SimpleNamespace(environ=os.environ, killpg=lambda pid, sig: signals.append(sig)),
        "signal": signal,
        "subprocess": SimpleNamespace(
            Popen=spawn, DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired
        ),
        "subject": {"clean_env": {"LANG": "C.UTF-8"}},
        "private": tmp_path,
        "digest": lambda path: hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), "<actual-Caddy-scan-runner>", "exec"),
        namespace,
    )
    code, timed = namespace["invoke"]("fixture", ["/qualified/trivy"], "SCANS", 330, scan=True)
    assert waits == [300, *([10] * timeouts)]
    assert signals == [signal.SIGTERM, signal.SIGKILL][:timeouts]
    assert timed is (timeouts > 0)
    assert code == (0 if timeouts == 0 else -9)
    assert clock[0] <= 330 and len(records) == 1
    assert records[0]["timeout"] == timed and records[0]["exit"] == code


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "source",
        "HC",
        "secret",
        "fingerprint",
        "epoch",
        "cleanup",
        "API",
        "policy",
        "runtime",
        "archive",
    ],
)
def test_caddy_candidate_release_requires_current_source_control_and_cleanup_conjunction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from scripts.ci import check_docker_runtime_dependency_surface as owner
    from tests.test_docker_runtime_dependency_surface import (
        _caddy_control_fixture,
        _caddy_source_fixture,
    )

    for key in tuple(os.environ):
        if any(
            word in key.upper() for word in ("TOKEN", "PASSWORD", "SECRET", "CREDENTIAL", "AUTH")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GH_TOKEN", "synthetic-only-token")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.chdir(REPO_ROOT)
    runner = tmp_path / "runner"
    initial = _caddy_budget_fixture(runner, monkeypatch)
    private = runner / "private"
    private.mkdir()
    source = private / "build-evidence"
    binary, binary_hash, _ = _caddy_source_fixture(source, monkeypatch)
    report, controls = _caddy_control_fixture(private / "controls")
    controls.update(
        failure=None,
        container_cleanup=True,
        child_tag="pulseplate-caddy-control:synthetic",
        owner="synthetic",
    )
    if fault == "HC":
        controls["scans"]["candidate-HC"]["exit"] = 1
    if fault in ("secret", "fingerprint"):
        for name in ("secret-full", "secret-HC"):
            path = private / "controls" / (name + ".raw.json")
            document = json.loads(path.read_text())
            if fault == "secret":
                document["Results"][-1]["Secrets"][0]["unknown"] = "retained"
            elif name.endswith("full"):
                document["Results"][0]["Vulnerabilities"][0]["Fingerprint"] = "sha256:" + "0" * 64
            path.write_text(json.dumps(document))
            controls["scans"][name]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    if fault == "source":
        (source / "post-build-tree.sha256").write_text("wrong source")
    scanner = private / "trivy"
    scanner.write_bytes(b"synthetic scanner bytes")
    cache = private / "cache"
    (cache / "db").mkdir(parents=True)
    frozen = {}
    for name in ("db/trivy.db", "db/metadata.json"):
        path = cache / name
        path.write_bytes(b"synthetic frozen epoch")
        frozen[name] = {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    if fault == "epoch":
        (cache / "db/trivy.db").write_bytes(b"different epoch")
    evidence = runner / "caddy-contract"
    full = evidence / "full-observation"
    (full / "native-projections").mkdir(parents=True)
    (full / "native-projections/build-info.txt").write_bytes(binary)
    raw = full / "full.raw.json"
    raw.write_text(json.dumps(report))
    (full / "observation.json").write_text(
        json.dumps(
            {
                "full_scan_native_exit": 0,
                "full_report_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            }
        )
    )
    paths = [
        "frontend/Dockerfile.caddy-spa",
        "frontend/package-lock.json",
        "frontend/.dockerignore",
        "frontend/scripts/check-redocly-compat.mjs",
        "frontend/patches/redocly-1.34.15-minimatch11.patch",
        "frontend/patches/redocly-1.34.15-minimatch11.inventory.json",
        ".github/workflows/frontend-ci.yml",
        "deploy/Caddyfile",
        "deploy/Caddyfile.production",
        "scripts/ci/check_docker_runtime_dependency_surface.py",
        "scripts/ci/prometheus_source_image.py",
        "scripts/ci/check_trivy_ignore_policy_expiry.py",
        "trivy/ignore-policy.rego",
    ]
    inputs = owner.caddy_ci_source_inventory(REPO_ROOT, paths)
    head = "1" * 40
    admission = {
        "mode": "build",
        "inputs": inputs,
        "current_head": head,
        "current_run_id": 123,
        "current_run_attempt": 1,
        "budget": initial["budget"],
    }
    (runner / "caddy-admission/admission.json").write_text(json.dumps(admission))
    subject = {
        "controls": controls,
        "image_config_id": report["ArtifactName"],
        "binary_sha256": binary_hash,
        "build_evidence": str(source),
        "scanner": str(scanner),
        "scanner_sha256": hashlib.sha256(scanner.read_bytes()).hexdigest(),
        "docker": "/synthetic/docker",
        "clean_env": {"LANG": "C.UTF-8"},
        "frozen_db": frozen,
        "cache": str(cache),
    }
    state = private / "subject.json"
    state.write_text(json.dumps(subject))
    monkeypatch.setenv("CADDY_OBSERVATION_STATE", str(state))
    candidate = private / "candidate"
    candidate.mkdir()
    image_bytes = b"synthetic image; never a native qualification claim"
    (candidate / "candidate.docker.tar").write_bytes(
        image_bytes + (b"changed" if fault == "archive" else b"")
    )
    (candidate / "candidate.json").write_text(
        json.dumps(
            {
                "archive_bytes": len(image_bytes),
                "archive_sha256": hashlib.sha256(image_bytes).hexdigest(),
                "image_config_id": subject["image_config_id"],
                "binary_sha256": binary_hash,
                "inputs": inputs,
                "producer_run_id": 123,
                "producer_run_attempt": 1,
                "producer_head": head,
            }
        )
    )

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args, 0, args[-1] + "\n", "")

    def runtime(*args: Any, **kwargs: Any) -> dict:
        if fault == "runtime":
            raise ValueError("synthetic runtime failure")
        return {"actual_fixture_only": True}

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        if argv[0] == str(scanner):
            converted = json.loads(raw.read_text())
            if fault == "policy":
                converted["Results"][0]["Packages"][0]["Version"] = "changed"
            kwargs["stdout"].write(json.dumps(converted).encode())
        else:
            assert argv[:3] == ["/synthetic/docker", "image", "rm"]
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    def output(argv: list[str], **kwargs: Any) -> bytes:
        if argv[1:3] == ["image", "inspect"]:
            return json.dumps(
                [
                    {
                        "Id": "wrong" if fault == "cleanup" else controls["subjects"]["secret"],
                        "RepoTags": [controls["child_tag"]],
                        "RootFS": {"Layers": controls["child_layers"]},
                    }
                ]
            ).encode()
        assert argv[1] == "ps"
        return b""

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def geturl(self) -> str:
            return "https://api.github.com/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/2494"

        def read(self, bound: int) -> bytes:
            assert bound == 8388609
            return json.dumps(
                {
                    "number": 2494,
                    "state": "open",
                    "head": {
                        "repo": {"id": 1043311030},
                        "sha": "2" * 40 if fault == "API" else head,
                    },
                }
            ).encode()

    monkeypatch.setattr(owner, "_run_docker", native)
    monkeypatch.setattr(owner, "observe_caddy_ci_runtime", runtime)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "check_output", output)

    def api_call(
        selected_root: Path, directory: Path, endpoint: str, remaining: Any, expected: str
    ) -> Any:
        assert selected_root == REPO_ROOT and endpoint == "/pulls/2494"
        assert expected == inputs["scripts/ci/prometheus_source_image.py"]["sha256"]
        assert 0 < remaining(30) <= 30
        return json.loads(Response().read(8388609))

    monkeypatch.setattr(owner, "caddy_ci_api", api_call)
    script = _caddy_inline("Decide source-qualified Caddy inventory and current native controls")
    if fault is None:
        exec(compile(script, "<actual-current-Caddy-release>", "exec"), {})
        assert (evidence / "candidate.docker.tar").read_bytes() == image_bytes
        result = json.loads((evidence / "candidate.json").read_text())
        assert result["source_correction"] == "CVE-2026-116587"
        assert result["v3_scanner_comparability"] == "UNKNOWN"
        assert len(list((evidence / "build-evidence").iterdir())) == 28
        assert len(list((evidence / "controls").glob("*.raw.json"))) == 6
    else:
        with pytest.raises(ValueError):
            exec(compile(script, "<actual-current-Caddy-release>", "exec"), {})
        assert not (evidence / "candidate.docker.tar").exists()
        assert not (evidence / "candidate.json").exists()


@pytest.mark.parametrize(
    "case",
    [
        "build",
        "reuse",
        "metadata",
        "ordinary-no-producer",
        "wrong-PR",
        "foreign-repo",
        "wrong-head",
        "wrong-ref",
        "missing-job",
        "duplicate-run",
        "inventory-drift",
        "active-producer",
        "source-alias",
        "expired-artifact",
        "failed-producer",
        "refresh-both",
        "refresh-mixed",
        "refresh-second",
        "refresh-ordinary",
        "refresh-persistent",
        "refresh-run-regressed",
        "refresh-job-regressed",
        "refresh-step-disappeared",
        "refresh-step-renumbered",
        "refresh-missing-step",
        "refresh-duplicate-step",
        "refresh-step-started",
        "refresh-terminal",
        "refresh-cancelled",
        "refresh-unknown",
        "refresh-conclusion",
        "refresh-run-id",
        "refresh-job-id",
        "refresh-attempt",
        "refresh-branch",
        "refresh-event",
        "refresh-repo",
        "refresh-workflow",
        "refresh-head",
        "refresh-job-run",
        "refresh-job-head",
        "refresh-job-branch",
        "refresh-budget",
        "refresh-job-budget",
        "refresh-malformed-steps",
        "refresh-initial-terminal",
        "refresh-initial-started",
        "refresh-job-complete-time",
    ],
)
def test_caddy_actual_admission_binds_current_PR_and_successful_source_producer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    from scripts.ci import prometheus_source_image as transport

    for key in tuple(os.environ):
        if any(
            word in key.upper() for word in ("TOKEN", "PASSWORD", "SECRET", "CREDENTIAL", "AUTH")
        ):
            monkeypatch.delenv(key, raising=False)
    runner = tmp_path / "runner"
    _caddy_budget_fixture(runner, monkeypatch)
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.chdir(root)
    head, old_head = "1" * 40, "2" * 40
    branch = "codex/dependency-alertmanager-remediation"
    repo = "Katsiarynakavaleuskaya/PulsePlate"
    fixed = [
        ".github/workflows/frontend-ci.yml",
        "deploy/Caddyfile",
        "deploy/Caddyfile.production",
        "scripts/ci/check_docker_runtime_dependency_surface.py",
        "scripts/ci/prometheus_source_image.py",
        "scripts/ci/check_trivy_ignore_policy_expiry.py",
        "trivy/ignore-policy.rego",
    ]
    tracked = [
        "frontend/Dockerfile.caddy-spa",
        "frontend/package-lock.json",
        "frontend/.dockerignore",
        "frontend/scripts/check-redocly-compat.mjs",
        "frontend/patches/redocly-1.34.15-minimatch11.patch",
        "frontend/patches/redocly-1.34.15-minimatch11.inventory.json",
    ]
    source_bytes = b"synthetic immutable Git source\n"
    blob = hashlib.sha1(
        b"blob " + str(len(source_bytes)).encode() + b"\0" + source_bytes, usedforsecurity=False
    ).hexdigest()
    for name in [*fixed, *tracked]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source_bytes)
    if case == "source-alias":
        tracked.append("frontend/../trivy/ignore-policy.rego")
    repository = {"id": 1043311030, "full_name": repo}
    pr = {
        "number": 2497 if case == "wrong-PR" else 2494,
        "state": "open",
        "merged": False,
        "head": {"repo": dict(repository), "sha": head, "ref": branch},
        "base": {"repo": dict(repository), "ref": "main"},
    }
    if case == "foreign-repo":
        pr["head"]["repo"]["id"] = 999
    refresh = case.removeprefix("refresh-") if case.startswith("refresh-") else None
    reuse = case in {"reuse", "expired-artifact", "failed-producer"}
    event_name = (
        "pull_request"
        if reuse or refresh == "ordinary" or case == "ordinary-no-producer"
        else "workflow_dispatch"
    )
    action = (
        ""
        if event_name == "pull_request"
        else "xnet062-metadata" if case == "metadata" else "candidate-D"
    )
    event = runner / "event.json"
    event.write_text(json.dumps({"pull_request": pr} if event_name == "pull_request" else {}))
    output = runner / "github-output"
    output.touch()
    for key, value in {
        "GH_TOKEN": "synthetic-only-token",
        "GITHUB_REPOSITORY": repo,
        "GITHUB_REPOSITORY_ID": "1043311030",
        "CADDY_ACTION": action,
        "CADDY_SOURCE_HEAD": "3" * 40 if case == "wrong-head" else head,
        "GITHUB_SHA": head,
        "GITHUB_EVENT_PATH": str(event),
        "GITHUB_EVENT_NAME": event_name,
        "GITHUB_REF": "refs/heads/other" if case == "wrong-ref" else "refs/heads/" + branch,
        "GITHUB_RUN_ID": "11",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_OUTPUT": str(output),
    }.items():
        monkeypatch.setenv(key, value)
    build_name = "Build source-patched Caddy candidate"
    decision_name = "Decide source-qualified Caddy inventory and current native controls"
    current_run = {
        "id": 11,
        "repository": repository,
        "head_repository": repository,
        "workflow_id": 196310935,
        "path": ".github/workflows/frontend-ci.yml",
        "head_sha": head,
        "head_branch": branch,
        "run_attempt": 1,
        "event": event_name,
        "status": "in_progress",
        "conclusion": None,
        "created_at": "2026-10-31T01:00:00Z",
    }
    current_job = {
        "id": 21,
        "run_id": 11,
        "run_attempt": 1,
        "head_sha": head,
        "name": "caddy-contract",
        "status": "in_progress",
        "conclusion": None,
        "head_branch": branch,
        "completed_at": None,
        "steps": [
            {
                "number": 12,
                "name": build_name,
                "status": "pending",
                "conclusion": None,
                "started_at": None,
                "completed_at": None,
            }
        ],
    }
    active_run, active_job = deepcopy(current_run), deepcopy(current_job)
    if refresh:
        current_run["status"] = "in_progress" if refresh == "run-regressed" else "queued"
        if refresh not in {"mixed", "job-regressed"}:
            current_job.update(status="queued", started_at="2026-10-31T01:00:01Z", steps=[])
        if refresh in {"step-disappeared", "step-renumbered"}:
            current_job["steps"] = deepcopy(active_job["steps"])
        if refresh == "initial-terminal":
            current_run["status"] = "completed"
        if refresh == "initial-started":
            current_job["steps"] = deepcopy(active_job["steps"])
            current_job["steps"][0].update(status="in_progress", started_at="2026-10-31T01:00:02Z")
        if refresh in {"budget", "job-budget"}:
            path = runner / "caddy-admission/admission.json"
            ledger = json.loads(path.read_text())
            ledger["budget"]["charged"]["ADMISSION"] = 541 if refresh == "budget" else 538
            path.write_text(json.dumps(ledger))
    runs = [current_run]
    jobs = {11: [] if case == "missing-job" else [current_job]}
    if reuse or case == "active-producer":
        prior = {
            **current_run,
            "id": 12,
            "head_sha": old_head,
            "event": "workflow_dispatch",
            "created_at": "2026-10-31T00:00:00Z",
            "updated_at": "2026-10-31T00:30:01Z",
            "status": "in_progress" if case == "active-producer" else "completed",
            "conclusion": (
                None
                if case == "active-producer"
                else "failure" if case == "failed-producer" else "success"
            ),
        }
        prior_job = {
            **current_job,
            "id": 22,
            "run_id": 12,
            "head_sha": old_head,
            "status": prior["status"],
            "conclusion": prior["conclusion"],
            "started_at": "2026-10-31T00:00:01Z",
            "completed_at": "2026-10-31T00:30:00Z",
            "steps": [
                {
                    "number": 12,
                    "name": build_name,
                    "status": prior["status"],
                    "conclusion": prior["conclusion"],
                    "started_at": "2026-10-31T00:01:00Z",
                    "completed_at": None if case == "active-producer" else "2026-10-31T00:10:00Z",
                },
                {
                    "number": 22,
                    "name": decision_name,
                    "status": "completed",
                    "conclusion": "success",
                    "started_at": "2026-10-31T00:20:00Z",
                    "completed_at": "2026-10-31T00:29:00Z",
                },
            ],
        }
        runs.append(prior)
        jobs[12] = [prior_job]
    if case == "duplicate-run":
        runs.append(dict(current_run))
    calls: list[str] = []

    class Response:
        def __init__(self, url: str, value: dict) -> None:
            self.url, self.value = url, value

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def geturl(self) -> str:
            return self.url

        def read(self, bound: int) -> bytes:
            assert bound == 8388609
            return json.dumps(self.value).encode()

    class API:
        def open(self, request: Any, timeout: float) -> Response:
            assert request.get_header("Authorization") == "Bearer synthetic-only-token"
            assert 0 < timeout <= 30
            url = request.full_url
            calls.append(url)
            if url.endswith("/pulls/2494"):
                value = pr
            elif url.endswith("/actions/workflows/frontend-ci.yml"):
                value = {"id": 196310935}
            elif "/actions/workflows/frontend-ci.yml/runs?" in url:
                observed = deepcopy(runs)
                if case == "inventory-drift" and calls.count(url) > 1:
                    observed[0]["created_at"] = "2026-10-31T01:00:01Z"
                value = {"total_count": len(observed), "workflow_runs": observed}
            elif "/jobs?filter=all" in url:
                run_id = int(url.split("/runs/", 1)[1].split("/", 1)[0])
                value = {"total_count": len(jobs[run_id]), "jobs": jobs[run_id]}
            elif url.endswith("/actions/runs/11/attempts/1"):
                value = deepcopy(active_run)
                if refresh in {"persistent", "run-regressed"} or (
                    refresh == "second" and calls.count(url) == 1
                ):
                    value["status"] = "queued"
                for fault, field, invalid in (
                    ("run-id", "id", 12),
                    ("attempt", "run_attempt", True),
                    ("branch", "head_branch", "other"),
                    ("event", "event", "push"),
                    ("repo", "repository", {"id": 99, "full_name": repo}),
                    ("workflow", "workflow_id", 7),
                    ("head", "head_sha", old_head),
                    ("terminal", "status", "completed"),
                    ("cancelled", "status", "cancelled"),
                    ("unknown", "status", "unknown"),
                    ("conclusion", "conclusion", "success"),
                ):
                    if refresh == fault:
                        value[field] = invalid
            elif url.endswith("/actions/jobs/21"):
                value = deepcopy(active_job)
                if refresh in {"persistent", "job-regressed", "step-disappeared"}:
                    value.update(status="queued", steps=[])
                elif refresh == "step-renumbered":
                    value["steps"][0]["number"] += 1
                elif refresh == "missing-step":
                    value["steps"] = []
                elif refresh == "malformed-steps":
                    value["steps"] = {}
                elif refresh == "duplicate-step":
                    value["steps"].append({**value["steps"][0], "number": 13})
                elif refresh == "step-started":
                    value["steps"][0]["started_at"] = "2026-10-31T01:00:02Z"
                elif refresh == "job-complete-time":
                    value["completed_at"] = "2026-10-31T01:00:02Z"
                elif refresh == "job-id":
                    value["id"] = 22
                elif refresh == "job-head":
                    value["head_sha"] = old_head
                elif refresh == "job-run":
                    value["run_id"] = 12
                elif refresh == "job-branch":
                    value["head_branch"] = "other"
            elif "/artifacts?" in url:
                value = {
                    "total_count": 1,
                    "artifacts": [
                        {
                            "id": 31,
                            "name": "caddy-contract-evidence",
                            "expired": case == "expired-artifact",
                            "digest": "sha256:" + "a" * 64,
                            "workflow_run": {
                                "id": 12,
                                "head_sha": old_head,
                                "repository_id": 1043311030,
                                "head_repository_id": 1043311030,
                                "head_branch": branch,
                            },
                        }
                    ],
                }
            else:
                raise AssertionError(url)
            return Response(url, value)

    def git_output(argv: list[str], **kwargs: Any) -> bytes | str:
        assert argv[0] == "/synthetic/git" and 0 < kwargs["timeout"] <= 60
        if "rev-parse" in argv:
            return head + "\n"
        if "ls-files" in argv:
            return ("\0".join(tracked) + "\0").encode()
        if "status" in argv:
            return b""
        if "ls-tree" in argv and "--name-only" in argv:
            return ("\0".join([*tracked, *fixed]) + "\0").encode()
        if "ls-tree" in argv:
            return ("100644 blob " + blob + "\n").encode()
        if "cat-file" in argv:
            return source_bytes
        raise AssertionError(argv)

    def git_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        assert "fetch" in argv and argv[-1] == old_head
        assert kwargs["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
        return subprocess.CompletedProcess(argv, 0)

    lineage: list[tuple] = []
    from scripts.ci import check_docker_runtime_dependency_surface as owner
    from urllib.request import Request

    if refresh == "job-budget":
        from types import SimpleNamespace

        now = ledger["budget"]["started"]
        monkeypatch.setattr(owner, "time", SimpleNamespace(monotonic=lambda: now))

    def api_call(
        selected_root: Path, directory: Path, endpoint: str, remaining: Any, expected: str
    ) -> Any:
        nonlocal now
        assert selected_root == root
        assert expected == hashlib.sha256(source_bytes).hexdigest()
        request = Request(
            "https://api.github.com/repos/" + repo + endpoint,
            headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"]},
        )
        response = json.loads(API().open(request, remaining(30)).read(8388609))
        if refresh == "job-budget" and endpoint == "/actions/runs/11/attempts/1":
            now += 33
        return response

    monkeypatch.setattr(owner, "caddy_ci_api", api_call)
    monkeypatch.setattr(transport, "authenticate_pr_source", lambda *args: lineage.append(args[1:]))
    monkeypatch.setattr(shutil, "which", lambda name: "/synthetic/" + name)
    monkeypatch.setattr(subprocess, "check_output", git_output)
    monkeypatch.setattr(subprocess, "run", git_run)
    code = _caddy_inline("Admit existing Caddy producer or exact retained subject")
    if case in {"build", "reuse", "metadata"} or refresh in {"both", "mixed", "second"}:
        exec(compile(code, "<actual-Caddy-current-admission>", "exec"), {})
        result = json.loads((runner / "caddy-admission/admission.json").read_text())
        mode = "build" if refresh else case
        assert result["mode"] == mode
        assert output.read_text().startswith("mode=" + mode)
        if case == "reuse":
            assert result["producer"]["git_inputs"] == result["inputs"]
            assert result["producer"]["artifact"]["id"] == 31
            assert lineage == [(2494, old_head, head, "refs/heads/" + branch)]
    else:
        expected_error = {
            "ordinary-no-producer": "real successful same-source PR2494 producer",
            "wrong-PR": "original PR identity differs",
            "foreign-repo": "original PR identity differs",
            "wrong-head": "checkout is not selected source head",
            "wrong-ref": "dispatch must select current accepted PR head",
            "missing-job": "current native run/job missing or ambiguous",
            "duplicate-run": "duplicate API identity",
            "inventory-drift": "same-count inventory replacement",
            "active-producer": "another producer still active",
            "source-alias": "relevant source path alias",
            "expired-artifact": "original producer artifact unavailable",
            "failed-producer": "real successful same-source PR2494 producer",
        }.get(case, "Caddy current")
        if refresh == "attempt":
            expected_error = "native positive ID required"
        if refresh == "ordinary":
            expected_error = "real successful same-source PR2494 producer"
        if refresh in {"budget", "persistent"}:
            expected_error = "current state unresolved: run=11 job=21 attempt=1 statuses="
        with pytest.raises(ValueError, match=expected_error):
            exec(compile(code, "<actual-Caddy-current-admission>", "exec"), {})
        assert output.read_text() == ""
    if refresh:
        expected_pairs = (
            0
            if refresh in {"budget", "initial-terminal", "initial-started"}
            else 2 if refresh in {"second", "persistent"} else 1
        )
        assert sum(url.endswith("/actions/runs/11/attempts/1") for url in calls) == expected_pairs
        invalid_run = refresh in {
            "run-regressed",
            "run-id",
            "attempt",
            "branch",
            "event",
            "repo",
            "workflow",
            "head",
            "terminal",
            "cancelled",
            "unknown",
            "conclusion",
            "job-budget",
        }
        expected_job_reads = 0 if invalid_run else expected_pairs
        assert sum(url.endswith("/actions/jobs/21") for url in calls) == expected_job_reads
        assert sum("/actions/workflows/frontend-ci.yml/runs?" in url for url in calls) == 2
        assert sum("/jobs?filter=all" in url for url in calls) == 2
        assert not any("/artifacts?" in url for url in calls)
    assert not (runner / "caddy-contract/candidate.docker.tar").exists()


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "redirect",
        "slow-body",
        "reflection",
        "source",
        "source-after-auth",
        "namespace-scripts",
        "namespace-ci",
        "directory-alias",
        "bytecode",
        "helper-shadow",
        "cleanup",
    ],
)
def test_caddy_same_opener_child_binds_namespace_source_and_whole_call_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    import time
    from scripts.ci import check_docker_runtime_dependency_surface as owner
    from scripts.ci import prometheus_source_image as transport

    for key in tuple(os.environ):
        if any(
            word in key.upper() for word in ("TOKEN", "PASSWORD", "SECRET", "CREDENTIAL", "AUTH")
        ):
            monkeypatch.delenv(key, raising=False)
    token = "synthetic-only-token"
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv("CADDY_API_CALL_SECONDS", "6")
    monkeypatch.setenv("CADDY_API_CLEANUP_SECONDS", "1")
    root = tmp_path / "source"
    helper = root / "scripts/ci/prometheus_source_image.py"
    helper.parent.mkdir(parents=True)
    helper.write_bytes((REPO_ROOT / "scripts/ci/prometheus_source_image.py").read_bytes())
    expected = hashlib.sha256(helper.read_bytes()).hexdigest()
    if fault == "source":
        expected = "0" * 64
    elif fault == "namespace-scripts":
        (root / "scripts/__init__.py").write_text(
            'raise RuntimeError("shadow must never execute")\n'
        )
    elif fault == "namespace-ci":
        (root / "scripts/ci/__init__.py").write_text(
            'raise RuntimeError("shadow must never execute")\n'
        )
    elif fault == "directory-alias":
        helper.parent.rename(root / "scripts/other-ci")
        (root / "scripts/ci").symlink_to(root / "scripts/other-ci", target_is_directory=True)
    elif fault == "bytecode":
        cache = root / "scripts/ci/__pycache__"
        cache.mkdir()
        (cache / "unbound.cpython-313.pyc").write_bytes(b"unbound project bytecode")
    elif fault == "helper-shadow":
        shadow = root / "scripts/ci/prometheus_source_image"
        shadow.mkdir()
        (shadow / "__init__.py").write_text('raise RuntimeError("shadow must never execute")\n')
    trace = tmp_path / "HTTP-trace"
    # Only the child test transport is synthetic. It exercises the actual canonical
    # NoRedirect opener; no real network request or gh authentication is performed.
    preamble = """import io, json, os, time, urllib.request, urllib.response
from email.message import Message
from pathlib import Path
class Body(io.BytesIO):
    def read(self, *args):
        if os.environ["CADDY_TEST_CASE"] == "slow-body": time.sleep(10)
        return super().read(*args)
def response(handler, request):
    expected_url = "https://api.github.com/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/2494"
    assert request.full_url == expected_url, "foreign request was attempted"
    assert request.get_header("Authorization") == "Bearer " + os.environ["GH_TOKEN"]
    Path(os.environ["CADDY_TEST_TRACE"]).write_text(request.full_url)
    headers = Message()
    redirect = os.environ["CADDY_TEST_CASE"] == "redirect"
    if redirect: headers["Location"] = "https://foreign.invalid/credential-target"
    payload = {"ok": True}
    if os.environ["CADDY_TEST_CASE"] == "reflection": payload["reflected"] = os.environ["GH_TOKEN"]
    result = urllib.response.addinfourl(Body(json.dumps(payload).encode()), headers, request.full_url, 302 if redirect else 200)
    result.msg = "Found" if redirect else "OK"
    return result
urllib.request.HTTPSHandler.https_open = response
"""
    original_capture = transport.GitHubRead._capture
    original_close = transport.GitHubRead.close
    original_which = shutil.which
    readers: list[Any] = []
    deadlines: list[float] = []

    def capture(reader: Any, argv: list[str], maximum: int, **kwargs: Any) -> bytes:
        deadlines.append(reader.deadline)
        if argv[1:3] == ["auth", "status"]:
            readers.append(reader)
            assert reader.cleanup_seconds == 1
            if fault == "source-after-auth":
                helper.write_bytes(helper.read_bytes() + b"\n# observed source drift\n")
            return b"synthetic authentication fixture\n"
        assert argv[0] == sys.executable
        assert argv[1:4] == ["-E", "-S", "-B"]
        assert token not in "\n".join(argv)
        assert "from scripts.ci.prometheus_source_image import opener" in argv[argv.index("-c") + 1]
        assert maximum == 8388608
        reader.environment.update(CADDY_TEST_CASE=fault or "valid", CADDY_TEST_TRACE=str(trace))
        selected = list(argv)
        selected[selected.index("-c") + 1] = preamble + selected[selected.index("-c") + 1]
        return original_capture(reader, selected, maximum, **kwargs)

    def close(reader: Any) -> None:
        original_close(reader)
        if fault == "cleanup":
            raise transport.QualificationError("synthetic owned cleanup failure")

    monkeypatch.setattr(
        shutil, "which", lambda name: "/synthetic/gh" if name == "gh" else original_which(name)
    )
    monkeypatch.setattr(transport.GitHubRead, "_capture", capture)
    monkeypatch.setattr(transport.GitHubRead, "close", close)
    started = time.monotonic()
    directory = tmp_path / "call"
    if fault is None:
        assert owner.caddy_ci_api(
            root, directory, "/pulls/2494", lambda cap: min(cap, 6), expected
        ) == {"ok": True}
    elif fault == "slow-body":
        with pytest.raises((transport.QualificationError, subprocess.TimeoutExpired)) as expired:
            owner.caddy_ci_api(root, directory, "/pulls/2494", lambda cap: min(cap, 6), expected)
        if isinstance(expired.value, subprocess.TimeoutExpired):
            assert expired.value.cmd == ["/bin/ps", "-axo", "pid,ppid,pgid,uid,lstart,state,comm"]
            assert 0 < expired.value.timeout <= 1
            assert time.monotonic() >= readers[0].deadline
    else:
        with pytest.raises((ValueError, transport.QualificationError)):
            owner.caddy_ci_api(root, directory, "/pulls/2494", lambda cap: min(cap, 6), expected)
    if fault == "source":
        assert deadlines == [] and not directory.exists()
    else:
        assert (
            len(deadlines) == 2 and deadlines[0] == deadlines[1]
        ), "auth and body must share one work deadline"
        assert readers and all(reader.process is None for reader in readers)
    if fault in (
        "source",
        "source-after-auth",
        "namespace-scripts",
        "namespace-ci",
        "directory-alias",
        "bytecode",
        "helper-shadow",
    ):
        assert not trace.exists(), "unqualified source must not reach HTTP"
    elif fault != "slow-body":
        assert trace.read_text().endswith("/pulls/2494")
    if fault == "slow-body":
        assert (
            time.monotonic() - started < 8
        ), "slow body must be stopped by the whole-call process owner"
    if fault == "redirect":
        diagnostic = b"\n".join(path.read_bytes() for path in directory.rglob("*.stderr"))
        assert (
            b"HTTP Error 302" in diagnostic and b"foreign request was attempted" not in diagnostic
        )
    assert all(
        token.encode() not in path.read_bytes() for path in directory.rglob("*") if path.is_file()
    )
    assert not (tmp_path / "candidate.json").exists()


def test_caddy_upstream_patch_has_exact_whitespace_hook_exclusion() -> None:
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hooks = [
        hook
        for repo in config["repos"]
        if repo["repo"] == "https://github.com/pre-commit/pre-commit-hooks"
        for hook in repo["hooks"]
        if hook["id"] == "trailing-whitespace"
    ]
    assert len(hooks) == 1
    expected = r"\Afrontend/patches/go-jose-v3\.0\.5-CVE-2026-116587\.patch\Z"
    assert hooks[0]["exclude"] == expected
    path = "frontend/patches/go-jose-v3.0.5-CVE-2026-116587.patch"
    assert re.search(expected, path) is not None
    for candidate in (
        path + "\n",
        path + ".bak",
        "prefix/" + path,
        path.replace("v3.0.5", "v3X0X5"),
        path.replace("v3.0.5", "v3.0.6"),
        path.replace("116587", "116588"),
        path.replace("patches/", "patches/nested/"),
        "frontend/Dockerfile.caddy-spa",
    ):
        assert re.search(expected, candidate) is None
    assert [
        hook
        for repo in config["repos"]
        for hook in repo["hooks"]
        if hook.get("exclude") == expected
    ] == hooks


def test_caddy_stdlib_exact_inputs_and_private_source_contract() -> None:
    recipe = DOCKERFILE.read_text()
    patch = REPO_ROOT / "frontend/patches/go1.26.10-http-connection-nominations.patch"
    fixture = REPO_ROOT / "frontend/patches/go_http_connection_nominations_test.go"
    assert hashlib.sha256(patch.read_bytes()).hexdigest() == caddy_surface.CADDY_STDLIB_PATCH_SHA256
    assert (
        hashlib.sha256(fixture.read_bytes()).hexdigest()
        == caddy_surface.CADDY_STDLIB_FIXTURE_SHA256
    )
    assert not any(line.endswith(b" ") for line in patch.read_bytes().splitlines())
    assert set(re.findall(r"^func (TestPP\w+)\(", fixture.read_text(), re.MULTILINE)) == set(
        caddy_surface.CADDY_STDLIB_CUSTOM_TOPS
    )
    assert "RUN --network=none" in recipe
    assert "ENV GOROOT=" + caddy_surface.CADDY_STDLIB_ROOT in recipe
    assert "GOCACHE=/opt/caddy-stdlib-patched-cache" in recipe
    assert recipe.index("go build -mod=readonly") < recipe.index("stdlib-post-build-tree.sha256")
    assert 'test "$total_bytes" -le 8388608' in recipe
    assert 'test "$stdlib_bytes" -le 16777216' in recipe
    assert 'test "$((total_bytes + stdlib_bytes))" -le 25165824' in recipe
    assert len(caddy_surface.CADDY_V3_BUILD_MEMBERS) == 16
    assert len(caddy_surface.CADDY_STDLIB_MEMBERS) == 12


def test_caddy_source_extraction_uses_closed_split_limits() -> None:
    source = _caddy_inline("Capture next loaded Caddy image identity")
    for name in (
        "CADDY_SOURCE_TAR_BYTES",
        "CADDY_SOURCE_TOTAL_BYTES",
        "CADDY_V3_TOTAL_BYTES",
        "CADDY_STDLIB_TOTAL_BYTES",
        "CADDY_STDLIB_MEMBER_LIMITS",
        "CADDY_BUILD_MEMBERS",
    ):
        assert name in source
    assert caddy_surface.CADDY_V3_TOTAL_BYTES == 8 * 1024**2
    assert caddy_surface.CADDY_STDLIB_TOTAL_BYTES == 16 * 1024**2
    assert caddy_surface.CADDY_SOURCE_TOTAL_BYTES == 24 * 1024**2


# These compact metadata fixtures do not qualify a native Go source/build output.
def _am062_module_rows(version: str) -> list[dict[str, Any]]:
    return [
        {"Path": "github.com/prometheus/alertmanager", "Main": True},
        {"Path": "golang.org/x/net", "Version": version},
        {"Path": "google.golang.org/grpc", "Version": "v1.83.2"},
        {"Path": "example.test/unchanged", "Version": "v1.0.0"},
    ]


def test_am062_metadata_delta_has_one_intent_and_complete_added_removed_closure() -> None:
    from scripts.ci import fetch_docker_source_artifacts as fetcher

    before = _am062_module_rows("v0.60.0")
    after = _am062_module_rows("v0.62.0")
    before += [{"Path": "example.test/removed", "Version": "v1.0.0"}]
    after += [{"Path": "example.test/added", "Version": "v2.0.0"}]
    after[2]["Version"] = "v1.84.0"  # A solver transition, never a second authored identity.
    frozen = deepcopy((before, after))
    delta = fetcher._alertmanager_xnet062_delta(before, after, epoch="alertmanager-0.34.2-xnet062")
    assert (before, after) == frozen
    by_path = {row["path"]: row for row in delta}
    assert set(by_path) == {
        "golang.org/x/net",
        "google.golang.org/grpc",
        "example.test/removed",
        "example.test/added",
    }
    assert [row["path"] for row in delta if row["class"] == "authored"] == ["golang.org/x/net"]
    assert by_path["golang.org/x/net"]["before"] == "v0.60.0"
    assert by_path["golang.org/x/net"]["after"] == "v0.62.0"
    assert by_path["example.test/removed"]["after"] is None
    assert by_path["example.test/added"]["before"] is None
    assert all(row["before"] is not None or row["after"] is not None for row in delta)
    assert all(
        row["class"] == "solver_closure_reproduced_by_fixed_get"
        for row in delta
        if row["path"] != "golang.org/x/net"
    )


@pytest.mark.parametrize("epoch", ["", "0.34.2", "alertmanager-0.34.1", "alertmanager-0.34.2-noop"])
def test_am062_metadata_rejects_historical_or_ambiguous_epoch(epoch: str) -> None:
    from scripts.ci import fetch_docker_source_artifacts as fetcher

    with pytest.raises(RuntimeError, match="metadata epoch"):
        fetcher._alertmanager_xnet062_delta(
            _am062_module_rows("v0.60.0"), _am062_module_rows("v0.62.0"), epoch=epoch
        )


@pytest.mark.parametrize(
    "fault",
    [
        "original058",
        "noop",
        "wrong-target",
        "duplicate",
        "missing-net",
        "missing-main",
        "extra-main",
        "version-null",
        "error",
        "replacement",
        "main-type",
        "missing-grpc",
    ],
)
def test_am062_metadata_rejects_wrong_base_noop_and_unqualified_rows(fault: str) -> None:
    from scripts.ci import fetch_docker_source_artifacts as fetcher

    before = _am062_module_rows("v0.60.0")
    after = _am062_module_rows("v0.62.0")
    if fault == "original058":
        before[1]["Version"] = "v0.58.0"
    elif fault == "noop":
        after[1]["Version"] = "v0.60.0"
    elif fault == "wrong-target":
        after[1]["Version"] = "v0.63.0"
    elif fault == "duplicate":
        after.append(dict(after[1]))
    elif fault == "missing-net":
        after.pop(1)
    elif fault == "missing-main":
        after.pop(0)
    elif fault == "extra-main":
        after.append({"Path": "example.test/other", "Main": True})
    elif fault == "version-null":
        after.append({"Path": "example.test/unresolved", "Version": None})
    elif fault == "error":
        after[1]["Error"] = {}
    elif fault == "replacement":
        after[1]["Replace"] = {}
    elif fault == "main-type":
        after[0]["Main"] = 1
    else:
        before.pop(2)
    with pytest.raises(RuntimeError):
        fetcher._alertmanager_xnet062_delta(before, after, epoch="alertmanager-0.34.2-xnet062")


def test_am062_metadata_ignores_hydration_fields_but_preserves_raw_module_inputs() -> None:
    from scripts.ci import fetch_docker_source_artifacts as fetcher

    before = _am062_module_rows("v0.60.0")
    after = _am062_module_rows("v0.62.0")
    after[3].update(Dir="/owned/modules/unchanged", Sum="h1:synthetic-checksum")
    delta = fetcher._alertmanager_xnet062_delta(before, after, epoch="alertmanager-0.34.2-xnet062")
    assert [row["path"] for row in delta] == ["golang.org/x/net"]
    assert after[3]["Sum"] == "h1:synthetic-checksum"


def test_am062_metadata_fixed_get_and_immediate_lock_capture_contract() -> None:
    import ast

    from scripts.ci import fetch_docker_source_artifacts as fetcher

    phase = inspect.getsource(fetcher._alertmanager_module_phase)
    get = phase.index('["get", "golang.org/x/net@v0.62.0"]')
    freeze = phase.index("derived_locks = {name: (source / name).read_bytes()", get)
    retain = phase.index('"-derived-" + lock', freeze)
    bind = phase.index("expected_locks = derived_locks", retain)
    download = phase.index('command(["mod", "download", "-json"], "derived-download")', bind)
    assert get < freeze < retain < bind < download
    assert phase.count('["get",') == 1
    assert '"xnet062-authored-get",\n                    solver=True,' in phase
    assert 'dict(env, GOFLAGS="") if solver else env' in phase
    assert "or before_locks != expected_locks" in phase
    assert '"GOFLAGS": "-mod=readonly"' in phase
    assert '"-failed-get-" + lock' in phase
    retained_error_note = ast.parse(
        'error.add_note("Failed-get lock retention failed: " + type(retention_error).__name__)',
        mode="eval",
    ).body
    assert any(
        ast.dump(node) == ast.dump(retained_error_note)
        for node in ast.walk(ast.parse(phase))
        if isinstance(node, ast.Call)
    )
    assert '"derivation_epoch": _ALERT_XNET062_METADATA_EPOCH' in phase
    assert 'for cmd in ("alertmanager", "amtool")' in phase
    assert '["list", "-mod=readonly", "-tags=netgo", "-deps", "-json", "./cmd/" + cmd]' in phase
    # New discovery report cannot silently enter the closed historical Q reader.
    retained = inspect.getsource(fetcher._alertmanager_qualified_payload)
    assert '"derivation_epoch"' not in retained
    assert '"AM_upstream_noop_lock_replay"' in retained
    assert '"AM_source_epoch_dependency_action"' in retained
