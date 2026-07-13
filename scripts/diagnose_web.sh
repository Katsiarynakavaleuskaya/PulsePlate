#!/usr/bin/env bash
# RU: Диагностика production web shell и SPA routing через edge.
# EN: Diagnose the production web shell and SPA routing through the edge.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEPLOY_DIR="${REPO_ROOT}/deploy"

BASE_URL="${BASE_URL:-}"
CHECK_CADDY_CONFIG_ONLY=0
SKIP_CADDY_VALIDATE=0
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-15}"
CF_ACCESS_CLIENT_ID="${CF_ACCESS_CLIENT_ID:-}"
CF_ACCESS_CLIENT_SECRET="${CF_ACCESS_CLIENT_SECRET:-}"
ADMIN_CANARY_PATH="${ADMIN_CANARY_PATH:-/api/v1/admin/status}"
FAILURES=0
ACCESS_HEADERS_ENABLED=0
declare -a ACCESS_CURL_HEADERS=()

usage() {
    cat <<'EOF'
Usage:
  bash scripts/diagnose_web.sh [--base-url https://pulseplate.app] [--check-caddy-config-only] [--skip-caddy-validate]

Options:
  --base-url URL             Explicit HTTPS/HTTP origin to probe.
  --check-caddy-config-only  Validate only the repo Caddy config; skip HTTP probes.
  --skip-caddy-validate      Skip local Caddyfile validation.

Environment:
  BASE_URL                   Same as --base-url.
  PRODUCTION_DOMAIN          Used to derive https://<domain> when BASE_URL is omitted.
  TIMEOUT_SECONDS            Per-request curl timeout, default 15.
  CF_ACCESS_CLIENT_ID        Optional Cloudflare Access service-token client id for private probes.
  CF_ACCESS_CLIENT_SECRET    Optional Cloudflare Access service-token secret for private probes.
  ADMIN_CANARY_PATH          Admin/backend canary path, default /api/v1/admin/status.
  CADDY_VALIDATION_IMAGE     Optional digest-pinned Caddy image override for config validation.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-url)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --base-url requires a URL argument." >&2
                usage >&2
                exit 2
            fi
            BASE_URL="$2"
            shift 2
            ;;
        --check-caddy-config-only)
            CHECK_CADDY_CONFIG_ONLY=1
            shift
            ;;
        --skip-caddy-validate)
            SKIP_CADDY_VALIDATE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "${BASE_URL}" && -n "${PRODUCTION_DOMAIN:-}" ]]; then
    BASE_URL="https://${PRODUCTION_DOMAIN}"
fi

if [[ -n "${BASE_URL}" && "${BASE_URL}" != http://* && "${BASE_URL}" != https://* ]]; then
    BASE_URL="https://${BASE_URL}"
fi

tmp_dir="$(mktemp -d)"
cleanup() {
    rm -rf "${tmp_dir}"
}
trap cleanup EXIT

pass() {
    printf 'PASS: %s\n' "$1"
}

warn() {
    printf 'WARN: %s\n' "$1"
}

fail() {
    printf 'FAIL: %s\n' "$1"
    FAILURES=$((FAILURES + 1))
}

configure_private_probe_headers() {
    if [[ -z "${CF_ACCESS_CLIENT_ID}" && -z "${CF_ACCESS_CLIENT_SECRET}" ]]; then
        return 0
    fi

    if [[ -z "${CF_ACCESS_CLIENT_ID}" || -z "${CF_ACCESS_CLIENT_SECRET}" ]]; then
        fail "CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must be provided together for private Access probes."
        return 1
    fi

    ACCESS_CURL_HEADERS=(
        -H "CF-Access-Client-Id: ${CF_ACCESS_CLIENT_ID}"
        -H "CF-Access-Client-Secret: ${CF_ACCESS_CLIENT_SECRET}"
    )
    ACCESS_HEADERS_ENABLED=1
    pass "Cloudflare Access service-token headers enabled for private probes."
}

validate_caddy_config() {
    if [[ "${SKIP_CADDY_VALIDATE}" -eq 1 ]]; then
        warn "Skipping local Caddyfile validation by request."
        return 0
    fi

    if ! command -v docker >/dev/null 2>&1; then
        warn "Docker is unavailable; skipping local Caddyfile validation."
        return 0
    fi

    if ! docker info >/dev/null 2>&1; then
        warn "Docker daemon/socket is unavailable; skipping local Caddyfile validation."
        return 0
    fi

    if [[ ! -f "${DEPLOY_DIR}/Caddyfile.production" ]]; then
        warn "deploy/Caddyfile.production is missing; skipping local Caddyfile validation."
        return 0
    fi

    echo "== Caddy config validation =="
    local caddy_validation_image="${CADDY_VALIDATION_IMAGE:-}"
    if [[ -z "${caddy_validation_image}" ]]; then
        caddy_validation_image="$(awk '/^FROM caddy:/{print $2; exit}' "${REPO_ROOT}/frontend/Dockerfile.caddy-spa")"
    fi
    if [[ -z "${caddy_validation_image}" || "${caddy_validation_image}" != *@sha256:* ]]; then
        fail "Unable to resolve the digest-pinned Caddy validation image from frontend/Dockerfile.caddy-spa."
        return 1
    fi
    if PRODUCTION_DOMAIN="${PRODUCTION_DOMAIN:-example.com}" \
        STAGING_FALLBACK_DOMAIN="${STAGING_FALLBACK_DOMAIN:-pulseplate-staging.duckdns.org}" \
        docker run --rm \
        -e PRODUCTION_DOMAIN \
        -e STAGING_FALLBACK_DOMAIN \
        -v "${DEPLOY_DIR}/Caddyfile.production:/etc/caddy/Caddyfile:ro" \
        "${caddy_validation_image}" \
        caddy validate --config /etc/caddy/Caddyfile >/dev/null; then
        pass "deploy/Caddyfile.production validates with Caddy."
    else
        fail "deploy/Caddyfile.production failed Caddy validation."
    fi
}

curl_probe() {
    local name="$1"
    local url="$2"
    shift 2
    local use_access_headers=1

    if [[ "${1:-}" == "--no-access-headers" ]]; then
        use_access_headers=0
        shift
    fi

    local headers_file="${tmp_dir}/${name}.headers"
    local body_file="${tmp_dir}/${name}.body"
    local status=""
    local content_type=""

    local -a curl_args=(
        -sS
        --max-time "${TIMEOUT_SECONDS}"
        -D "${headers_file}"
        -o "${body_file}"
        -w '%{http_code}'
    )

    if [[ "${ACCESS_HEADERS_ENABLED}" -eq 1 && "${use_access_headers}" -eq 1 ]]; then
        curl_args+=("${ACCESS_CURL_HEADERS[@]}")
    fi

    status="$(curl "${curl_args[@]}" "$@" "${url}")" || return 1

    content_type="$(
        awk '
            tolower($1) == "content-type:" {
                sub(/\r$/, "", $0)
                print substr($0, index($0, ":") + 2)
                exit
            }
        ' "${headers_file}"
    )"

    printf '%s|%s|%s|%s\n' "${status}" "${content_type}" "${headers_file}" "${body_file}"
}

looks_like_spa_shell() {
    local body_file="$1"
    # RU: SPA shell детектируем по стабильному frontend marker из `frontend/index.html`.
    # EN: Detect the SPA shell by the stable frontend marker from `frontend/index.html`.
    grep -Eiq '<div[[:space:]]+id=["'"'"']root["'"'"'][[:space:]]*></div>' "${body_file}"
}

assert_html_200() {
    local label="$1"
    local path="$2"
    local probe=""
    probe="$(curl_probe "${label}" "${BASE_URL}${path}")" || {
        fail "${label}: request to ${BASE_URL}${path} failed."
        return
    }

    IFS='|' read -r status content_type _headers body_file <<<"${probe}"
    if [[ "${status}" != "200" ]]; then
        fail "${label}: expected HTTP 200, got ${status}."
        return
    fi
    if [[ "${content_type}" != text/html* ]]; then
        fail "${label}: expected text/html, got '${content_type:-<empty>}' ."
        return
    fi
    if ! looks_like_spa_shell "${body_file}"; then
        fail "${label}: response does not contain the SPA shell marker."
        return
    fi
    pass "${label}: ${path} serves the SPA shell with HTTP 200."
}

assert_public_css_asset() {
    local label="$1"
    local root_probe=""
    root_probe="$(curl_probe "${label}-root" "${BASE_URL}/" --no-access-headers)" || {
        fail "${label}: request to ${BASE_URL}/ failed."
        return
    }

    IFS='|' read -r root_status _root_content_type _root_headers root_body_file <<<"${root_probe}"
    if [[ "${root_status}" != "200" ]]; then
        fail "${label}: expected root HTML HTTP 200 before CSS discovery, got ${root_status}."
        return
    fi

    local css_path=""
    css_path="$(
        awk '
            match($0, /href="[^"]*\/assets\/[^"]+\.css"/) {
                css = substr($0, RSTART + 6, RLENGTH - 7)
                print css
                exit
            }
        ' "${root_body_file}"
    )"
    if [[ -z "${css_path}" ]]; then
        fail "${label}: root HTML did not reference a Vite CSS asset under /assets/."
        return
    fi

    local css_probe=""
    css_probe="$(curl_probe "${label}" "${BASE_URL}${css_path}" --no-access-headers)" || {
        fail "${label}: request to ${BASE_URL}${css_path} failed."
        return
    }

    IFS='|' read -r status content_type headers_file body_file <<<"${css_probe}"
    if grep -Eiq 'location: .*cloudflareaccess\.com' "${headers_file}"; then
        fail "${label}: ${css_path} redirected to Cloudflare Access instead of public CSS."
        return
    fi
    if [[ "${status}" != "200" ]]; then
        fail "${label}: expected HTTP 200 for ${css_path}, got ${status}."
        return
    fi
    case "${content_type}" in
        text/css*) ;;
        *)
            fail "${label}: expected text/css for ${css_path}, got '${content_type:-<empty>}' ."
            return
            ;;
    esac
    if grep -Eiq 'cloudflare access|cf-access|/cdn-cgi/access' "${body_file}"; then
        fail "${label}: ${css_path} body looks like a Cloudflare Access page."
        return
    fi
    pass "${label}: ${css_path} is public CSS with HTTP 200."
}

assert_json_200() {
    local label="$1"
    local path="$2"
    local probe=""
    probe="$(curl_probe "${label}" "${BASE_URL}${path}")" || {
        fail "${label}: request to ${BASE_URL}${path} failed."
        return
    }

    IFS='|' read -r status content_type _headers body_file <<<"${probe}"
    if [[ "${status}" != "200" ]]; then
        fail "${label}: expected HTTP 200, got ${status}."
        return
    fi
    if [[ "${content_type}" != application/json* ]]; then
        fail "${label}: expected application/json, got '${content_type:-<empty>}' ."
        return
    fi
    if ! grep -Eq '^[[:space:]]*[\{\[]' "${body_file}"; then
        fail "${label}: response body does not look like JSON."
        return
    fi
    pass "${label}: ${path} reaches the JSON backend surface."
}

assert_not_spa_html() {
    local label="$1"
    local path="$2"
    local probe=""
    probe="$(curl_probe "${label}" "${BASE_URL}${path}")" || {
        fail "${label}: request to ${BASE_URL}${path} failed."
        return
    }

    IFS='|' read -r status content_type _headers body_file <<<"${probe}"
    if [[ "${status}" == "200" ]] && looks_like_spa_shell "${body_file}"; then
        fail "${label}: ${path} fell through to the SPA shell."
        return
    fi
    pass "${label}: ${path} stayed off the SPA shell (status ${status}, content-type '${content_type:-<empty>}')."
}

assert_not_spa_or_static_405() {
    local label="$1"
    local path="$2"
    shift 2
    local probe=""
    probe="$(curl_probe "${label}" "${BASE_URL}${path}" "$@")" || {
        fail "${label}: request to ${BASE_URL}${path} failed."
        return
    }

    IFS='|' read -r status content_type _headers body_file <<<"${probe}"
    if [[ "${status}" == "200" ]] && looks_like_spa_shell "${body_file}"; then
        fail "${label}: ${path} fell through to the SPA shell."
        return
    fi
    if [[ "${status}" == "405" && "${content_type}" == text/plain* ]]; then
        fail "${label}: ${path} looks like a static file_server 405 instead of the backend split."
        return
    fi
    pass "${label}: ${path} stayed off SPA/static-405 (status ${status}, content-type '${content_type:-<empty>}')."
}

assert_json_backend() {
    local label="$1"
    local path="$2"
    shift 2
    local probe=""
    probe="$(curl_probe "${label}" "${BASE_URL}${path}" "$@")" || {
        fail "${label}: request to ${BASE_URL}${path} failed."
        return
    }

    IFS='|' read -r status content_type _headers body_file <<<"${probe}"
    if [[ "${status}" =~ ^5 ]]; then
        fail "${label}: backend probe returned server error ${status}."
        return
    fi
    if [[ "${content_type}" != application/json* ]]; then
        fail "${label}: expected backend JSON, got '${content_type:-<empty>}' ."
        return
    fi
    if ! grep -Eq '^[[:space:]]*[\{\[]' "${body_file}"; then
        fail "${label}: backend probe body does not look like JSON."
        return
    fi
    pass "${label}: ${path} reached the backend JSON surface (status ${status})."
}

assert_admin_canary() {
    local label="$1"
    local path="$2"
    local probe=""
    probe="$(curl_probe "${label}" "${BASE_URL}${path}")" || {
        fail "${label}: request to ${BASE_URL}${path} failed."
        return
    }

    IFS='|' read -r status content_type _headers body_file <<<"${probe}"
    if [[ "${status}" == "404" ]]; then
        fail "${label}: ${path} returned 404, so the admin canary route is missing or misrouted."
        return
    fi
    if [[ "${status}" =~ ^5 ]]; then
        fail "${label}: backend probe returned server error ${status}."
        return
    fi
    if [[ "${content_type}" != application/json* ]]; then
        fail "${label}: expected backend JSON, got '${content_type:-<empty>}' ."
        return
    fi
    if ! grep -Eq '^[[:space:]]*[\{\[]' "${body_file}"; then
        fail "${label}: backend probe body does not look like JSON."
        return
    fi
    pass "${label}: ${path} reached the admin/backend canary surface (status ${status})."
}

assert_xml_sitemap() {
    local label="$1"
    local path="$2"
    local probe=""
    probe="$(curl_probe "${label}" "${BASE_URL}${path}")" || {
        fail "${label}: request to ${BASE_URL}${path} failed."
        return
    }

    IFS='|' read -r status content_type _headers body_file <<<"${probe}"
    if [[ "${status}" != "200" ]]; then
        fail "${label}: expected HTTP 200, got ${status}."
        return
    fi
    if [[ "${content_type}" != application/xml* && "${content_type}" != text/xml* ]]; then
        fail "${label}: expected XML sitemap content-type, got '${content_type:-<empty>}' ."
        return
    fi
    if looks_like_spa_shell "${body_file}"; then
        fail "${label}: ${path} fell through to the SPA shell."
        return
    fi
    if ! grep -q "<urlset" "${body_file}"; then
        fail "${label}: response body does not look like a sitemap."
        return
    fi
    pass "${label}: ${path} reaches the XML sitemap surface."
}

assert_ws_not_spa() {
    local label="websocket-upgrade"
    local probe=""
    probe="$(
        curl_probe "${label}" "${BASE_URL}/ws" \
            -H "Connection: Upgrade" \
            -H "Upgrade: websocket" \
            -H "Sec-WebSocket-Version: 13" \
            -H "Sec-WebSocket-Key: SGVsbG9QdWxzZVBsYXRlIQ=="
    )" || {
        fail "${label}: websocket probe request failed."
        return
    }

    IFS='|' read -r status content_type _headers _body_file <<<"${probe}"
    if [[ "${content_type}" == text/html* && "${status}" == "200" ]]; then
        fail "${label}: /ws was served by the SPA shell."
        return
    fi
    pass "${label}: /ws did not fall through to SPA (status ${status})."
}

run_http_probes() {
    if [[ -z "${BASE_URL}" ]]; then
        fail "BASE_URL or PRODUCTION_DOMAIN is required for HTTP probes."
        return
    fi

    echo "== Edge routing probes =="
    echo "Base URL: ${BASE_URL}"
    if [[ "${ACCESS_HEADERS_ENABLED}" -eq 1 ]]; then
        echo "Private probe mode: Cloudflare Access service token headers enabled."
    fi

    assert_html_200 "spa-root" "/"
    assert_html_200 "spa-bmi" "/bmi"
    assert_html_200 "spa-profile" "/profile"
    assert_html_200 "spa-plate" "/plate"
    assert_html_200 "spa-progress" "/progress"
    assert_public_css_asset "static-css"

    assert_json_200 "health-json" "/health"
    assert_json_backend "openapi-json" "/openapi.json"
    assert_xml_sitemap "sitemap-xml" "/sitemap.xml"
    assert_json_backend \
        "legacy-bmi-post" \
        "/bmi" \
        -X POST \
        -H "Content-Type: application/json" \
        --data '{}'
    assert_not_spa_or_static_405 \
        "legacy-bmi-options" \
        "/bmi" \
        -X OPTIONS \
        -H "Origin: https://pulseplate.test" \
        -H "Access-Control-Request-Method: POST"

    assert_not_spa_html "legacy-plan-get" "/plan"
    assert_not_spa_html "legacy-insight-get" "/insight"
    assert_not_spa_html "legacy-premium-bmr-get" "/premium_bmr"
    assert_not_spa_html "legacy-premium-targets-get" "/premium_targets"
    assert_not_spa_html "legacy-bmi-calculator-get" "/legacy/bmi-calculator"
    assert_json_backend "api-prefix" "/api/v1/does-not-exist"
    assert_admin_canary "admin-canary" "${ADMIN_CANARY_PATH}"
    assert_ws_not_spa
}

echo "PulsePlate web-shell diagnosis"
echo "Repo root: ${REPO_ROOT}"

configure_private_probe_headers
validate_caddy_config

if [[ "${CHECK_CADDY_CONFIG_ONLY}" -eq 0 ]]; then
    run_http_probes
fi

if [[ "${FAILURES}" -gt 0 ]]; then
    echo "Summary: ${FAILURES} failure(s) detected."
    exit 1
fi

echo "Summary: all requested checks passed."
