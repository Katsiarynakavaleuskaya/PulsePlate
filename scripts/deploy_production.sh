#!/usr/bin/env bash
set -euo pipefail

MODE="deploy"
if [ "$#" -gt 1 ]; then
  echo "❌ Usage: $0 [--preflight-only]" >&2
  exit 1
fi
if [ "$#" -eq 1 ]; then
  case "$1" in
    --preflight-only)
      MODE="preflight-only"
      ;;
    *)
      echo "❌ Unsupported argument: $1" >&2
      echo "Usage: $0 [--preflight-only]" >&2
      exit 1
      ;;
  esac
fi
readonly MODE

DEPLOY_IMAGE_REF="${IMAGE_REF:-}"
DEPLOY_TAG="${TAG:-}"
if [ "$MODE" != "preflight-only" ]; then
  : "${IMAGE_REF:?IMAGE_REF is required (ghcr.io/<image>@sha256:...)}"
  : "${TAG:?TAG is required (prod-vX.Y.Z)}"
fi

# Healthcheck configuration
HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-12}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"

COMPOSE_FILE="${COMPOSE_FILE:-}"
RESOLVED_COMPOSE_FILE="${COMPOSE_FILE:-}"
DEPLOY_DIR="${DEPLOY_DIR:-}"
ENV_FILE="${ENV_FILE:-}"
SHELL_BUNDLE_DIR="${SHELL_BUNDLE_DIR:-}"
DOCKER_BIN_OVERRIDE="${DOCKER_BIN:-}"
TRUSTED_DOCKER_CANDIDATES=(
  "/usr/bin/docker"
  "/usr/local/bin/docker"
  "/snap/bin/docker"
)
TRUSTED_DOCKER_CANDIDATES_TEXT="/usr/bin/docker, /usr/local/bin/docker, /snap/bin/docker"

# RU: Сохраняем credentials из workflow/окружения до загрузки .env,
# чтобы локальный deploy/.env не подменял registry contract из CI.
# EN: Snapshot caller-provided credentials before sourcing .env so a host-local
# deploy/.env cannot override the CI-provided registry contract.
ORIGINAL_GHCR_USER="${GHCR_USER:-}"
ORIGINAL_GHCR_TOKEN="${GHCR_TOKEN:-}"

resolve_docker_bin() {
  local candidate

  if [ -n "$DOCKER_BIN_OVERRIDE" ]; then
    # RU: Разрешаем только абсолютный путь, чтобы не запускать docker-wrapper из PATH.
    # EN: Accept only an absolute path to avoid executing a PATH-injected docker wrapper.
    if [[ "$DOCKER_BIN_OVERRIDE" != /* ]]; then
      echo "❌ DOCKER_BIN must be an absolute path: $DOCKER_BIN_OVERRIDE" >&2
      return 1
    fi
    if [ ! -x "$DOCKER_BIN_OVERRIDE" ]; then
      echo "❌ DOCKER_BIN is not executable: $DOCKER_BIN_OVERRIDE" >&2
      return 1
    fi

    printf '%s\n' "$DOCKER_BIN_OVERRIDE"
    return 0
  fi

  for candidate in "${TRUSTED_DOCKER_CANDIDATES[@]}"; do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

if ! DOCKER_BIN="$(resolve_docker_bin)"; then
  if [ -n "$DOCKER_BIN_OVERRIDE" ]; then
    echo "❌ docker binary not found. DOCKER_BIN override: $DOCKER_BIN_OVERRIDE. Trusted paths: $TRUSTED_DOCKER_CANDIDATES_TEXT" >&2
  else
    echo "❌ docker binary not found. Checked trusted paths: $TRUSTED_DOCKER_CANDIDATES_TEXT" >&2
  fi
  exit 1
fi
readonly DOCKER_BIN

resolve_deploy_dir() {
  if [ -n "$DEPLOY_DIR" ]; then
    if [ -d "$DEPLOY_DIR" ]; then
      echo "$DEPLOY_DIR"
      return 0
    fi
    echo "⚠️  DEPLOY_DIR is set but does not exist: $DEPLOY_DIR" >&2
    echo "    Falling back to auto-detect..." >&2
  fi

  if [ -d "/opt/pulseplate" ]; then
    echo "/opt/pulseplate"
    return 0
  fi

  if [ -d "/srv/pulseplate-production" ]; then
    echo "/srv/pulseplate-production"
    return 0
  fi

  return 1
}

DEPLOY_DIR="$(resolve_deploy_dir || true)"
if [ -z "$DEPLOY_DIR" ]; then
  echo "❌ Could not find deploy directory." >&2
  echo "Set DEPLOY_DIR or create /opt/pulseplate or /srv/pulseplate-production." >&2
  exit 1
fi

cd "$DEPLOY_DIR"

compose_args=()
if [ -n "$RESOLVED_COMPOSE_FILE" ]; then
  if [ ! -f "$RESOLVED_COMPOSE_FILE" ]; then
    echo "❌ RESOLVED_COMPOSE_FILE does not exist: $RESOLVED_COMPOSE_FILE" >&2
    exit 1
  fi
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
elif [ -f "deploy/docker-compose.production.yaml" ]; then
  RESOLVED_COMPOSE_FILE="deploy/docker-compose.production.yaml"
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
elif [ -f "deploy/docker-compose.production.yml" ]; then
  RESOLVED_COMPOSE_FILE="deploy/docker-compose.production.yml"
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
elif [ -f "docker-compose.production.yaml" ]; then
  RESOLVED_COMPOSE_FILE="docker-compose.production.yaml"
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
elif [ -f "docker-compose.production.yml" ]; then
  RESOLVED_COMPOSE_FILE="docker-compose.production.yml"
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
elif [ -f "docker-compose.yml" ]; then
  RESOLVED_COMPOSE_FILE="docker-compose.yml"
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
elif [ -f "docker-compose.yaml" ]; then
  RESOLVED_COMPOSE_FILE="docker-compose.yaml"
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
elif [ -f "compose.yml" ]; then
  RESOLVED_COMPOSE_FILE="compose.yml"
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
elif [ -f "compose.yaml" ]; then
  RESOLVED_COMPOSE_FILE="compose.yaml"
  compose_args=(-f "$RESOLVED_COMPOSE_FILE")
fi

if [ -z "$ENV_FILE" ]; then
  if [[ "$RESOLVED_COMPOSE_FILE" = deploy/* || "$RESOLVED_COMPOSE_FILE" = "$DEPLOY_DIR"/deploy/* ]]; then
    ENV_FILE="$DEPLOY_DIR/deploy/.env"
  else
    ENV_FILE="$DEPLOY_DIR/.env"
  fi
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Missing production env file: $ENV_FILE" >&2
  echo "Create this server-local runtime file before deploy; GitHub Actions does not provision it." >&2
  echo "See deploy/PRODUCTION.md for the canonical bootstrap contract." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

IMAGE_REF="$DEPLOY_IMAGE_REF"
TAG="$DEPLOY_TAG"

if [ -n "$ORIGINAL_GHCR_USER" ]; then
  GHCR_USER="$ORIGINAL_GHCR_USER"
fi
if [ -n "$ORIGINAL_GHCR_TOKEN" ]; then
  GHCR_TOKEN="$ORIGINAL_GHCR_TOKEN"
fi

export IMAGE_REF TAG

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${PRODUCTION_DOMAIN:?PRODUCTION_DOMAIN is required}"

export PRODUCTION_DOMAIN

echo "Deploy dir: $DEPLOY_DIR"
if [ ${#compose_args[@]} -gt 0 ]; then
  echo "Compose file: ${compose_args[*]}"
else
  echo "Compose file: <default>"
fi
echo "TAG: $TAG"
echo "IMAGE_REF: $IMAGE_REF"
echo "ENV_FILE: $ENV_FILE"

dc() {
  local base=("$DOCKER_BIN" compose --env-file "$ENV_FILE")
  if [ ${#compose_args[@]} -gt 0 ]; then
    base+=("${compose_args[@]}")
  fi
  "${base[@]}" "$@"
}

login_to_ghcr_if_configured() {
  if [ -z "${GHCR_TOKEN:-}" ]; then
    return 0
  fi

  if [ -z "${GHCR_USER:-}" ]; then
    echo "❌ GHCR_USER is required when GHCR_TOKEN is provided" >&2
    exit 1
  fi

  echo "Logging in to ghcr.io with deploy credentials..."
  printf '%s\n' "$GHCR_TOKEN" | "$DOCKER_BIN" login ghcr.io -u "$GHCR_USER" --password-stdin >/dev/null
}

sync_shell_bundle() {
  if [ -z "$SHELL_BUNDLE_DIR" ]; then
    return 0
  fi

  if [ -z "$DEPLOY_DIR" ]; then
    echo "❌ DEPLOY_DIR is required when SHELL_BUNDLE_DIR is set" >&2
    exit 1
  fi

  local source_frontend="$SHELL_BUNDLE_DIR/frontend"
  local source_caddyfile="$SHELL_BUNDLE_DIR/deploy/Caddyfile.production"
  local source_compose=""
  local source_diagnose="$SHELL_BUNDLE_DIR/scripts/diagnose_web.sh"
  local target_compose=""
  local compose_relative_path=""
  local shell_root
  shell_root="$(cd "$DEPLOY_DIR/.." && pwd)"

  if [ -z "$RESOLVED_COMPOSE_FILE" ]; then
    echo "❌ Could not resolve a compose filename for shell bundle sync" >&2
    exit 1
  fi

  if [[ "$RESOLVED_COMPOSE_FILE" = /* ]]; then
    case "$RESOLVED_COMPOSE_FILE" in
      "$DEPLOY_DIR"/*)
        compose_relative_path="${RESOLVED_COMPOSE_FILE#"$DEPLOY_DIR"/}"
        target_compose="$RESOLVED_COMPOSE_FILE"
        ;;
      *)
        echo "❌ COMPOSE_FILE must stay within DEPLOY_DIR: $RESOLVED_COMPOSE_FILE" >&2
        exit 1
        ;;
    esac
  else
    compose_relative_path="${RESOLVED_COMPOSE_FILE#./}"
    case "$compose_relative_path" in
      ""|"."|..|../*|*/../*|*/..)
        echo "❌ COMPOSE_FILE must stay within DEPLOY_DIR: $RESOLVED_COMPOSE_FILE" >&2
        exit 1
        ;;
    esac
    target_compose="$DEPLOY_DIR/$compose_relative_path"
  fi

  if [[ "$compose_relative_path" = deploy/* ]]; then
    source_compose="$SHELL_BUNDLE_DIR/$compose_relative_path"
  else
    source_compose="$SHELL_BUNDLE_DIR/deploy/$compose_relative_path"
  fi

  if [ ! -d "$source_frontend" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing frontend/: $source_frontend" >&2
    exit 1
  fi

  if [ ! -f "$source_caddyfile" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing deploy/Caddyfile.production: $source_caddyfile" >&2
    exit 1
  fi

  if [ ! -f "$source_compose" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing $compose_relative_path: $source_compose" >&2
    exit 1
  fi

  echo "Syncing production shell bundle from: $SHELL_BUNDLE_DIR"
  rm -rf "$shell_root/frontend"
  mkdir -p "$shell_root/frontend" "$shell_root/scripts"
  mkdir -p "$(dirname "$target_compose")"
  cp -R "$source_frontend/." "$shell_root/frontend/"
  cp "$source_caddyfile" "$DEPLOY_DIR/Caddyfile.production"
  cp "$source_compose" "$target_compose"
  rm -f "$shell_root/scripts/diagnose_web.sh"

  if [ -f "$source_diagnose" ]; then
    cp "$source_diagnose" "$shell_root/scripts/diagnose_web.sh"
    chmod +x "$shell_root/scripts/diagnose_web.sh"
  fi
}

wait_for_app_ready() {
  local max_wait="${1:-30}"
  local wait_count=0

  while [ "$wait_count" -lt "$max_wait" ]; do
    local app_container
    app_container="$(dc ps -q app | tr -d '\n\r ')"
    if [ -n "${app_container:-}" ] && "$DOCKER_BIN" exec "$app_container" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready').read()" 2>/dev/null; then
      echo "app is ready"
      return 0
    fi
    wait_count=$((wait_count + 1))
    echo "Waiting for app readiness... ($wait_count/$max_wait)"
    sleep 1
  done

  echo "❌ App failed to become ready within $max_wait seconds" >&2
  return 1
}

validate_managed_postgres_contract() {
  local compose_file_path=""

  if [ ${#compose_args[@]} -gt 0 ]; then
    compose_file_path="${compose_args[1]}"
  fi

  case "$DATABASE_URL" in
    postgresql+psycopg://*)
      ;;
    *)
      echo "❌ DATABASE_URL must use canonical Postgres DSN (postgresql+psycopg://...)" >&2
      exit 1
      ;;
  esac

  case "$DATABASE_URL" in
    *@postgres:*/* | *@postgres/*)
      echo "❌ Production deploy expects external managed PostgreSQL, not compose-local @postgres" >&2
      exit 1
      ;;
  esac

  if [ -n "$compose_file_path" ] && grep -qE '^[[:space:]]+postgres:' "$compose_file_path"; then
    echo "❌ Production compose still references local postgres; canonical lane is managed PostgreSQL only" >&2
    exit 1
  fi
}

run_preflight() {
  echo "Validating managed PostgreSQL production contract..."
  validate_managed_postgres_contract
  echo "✅ Production deploy preflight passed"
}

run_preflight
if [ "$MODE" = "preflight-only" ]; then
  exit 0
fi

login_to_ghcr_if_configured

echo "Pulling production app image..."
dc pull app

echo "Production DB backups are managed outside the deploy script (provider snapshots / PITR)."

echo "Running database migrations via one-shot release container..."
if dc run --rm --no-deps app alembic upgrade head; then
  echo "✅ Database migrations completed successfully"
else
  migration_exit_code=$?
  echo "❌ Database migrations failed (exit code: $migration_exit_code)" >&2
  exit "$migration_exit_code"
fi

sync_shell_bundle

echo "Starting app before exposing traffic..."
dc up -d --remove-orphans app
wait_for_app_ready 30

echo "Starting caddy after successful migrations..."
dc build caddy
dc up -d --remove-orphans caddy

# Healthcheck using --resolve to avoid DNS dependency (works even if DNS is temporarily unavailable)
# This checks locally via 127.0.0.1 but uses the domain for Host/SNI headers (TLS works correctly)
DOMAIN="${PRODUCTION_DOMAIN}"
HEALTH_URL="https://${DOMAIN}/ready"
attempt=1

# Quick non-blocking HTTP smoke check (diagnostic only; expected 308 -> HTTPS redirect)
echo "Smoke check HTTP..."
curl -sS -o /dev/null -w "HTTP:%{http_code}\n" \
  "http://${DOMAIN}/ready" --resolve "${DOMAIN}:80:127.0.0.1" --max-time "${HEALTH_CURL_MAX_TIME_S}" || true

# Main healthcheck on HTTPS (does not depend on external DNS)
echo "Healthcheck HTTPS (attempt ${attempt}/${HEALTH_MAX_ATTEMPTS})..."
until curl -fsS --max-time "${HEALTH_CURL_MAX_TIME_S}" "$HEALTH_URL" \
    --resolve "${DOMAIN}:443:127.0.0.1" > /dev/null; do
  if [ "$attempt" -ge "$HEALTH_MAX_ATTEMPTS" ]; then
    echo "❌ Healthcheck failed after ${HEALTH_MAX_ATTEMPTS} attempts: $HEALTH_URL" >&2
    echo "Container status:"
    dc ps || true
    echo "Container logs (last 200 lines):"
    dc logs --tail=200 || true
    exit 1
  fi
  echo "Healthcheck not ready (attempt ${attempt}/${HEALTH_MAX_ATTEMPTS}), retrying in ${HEALTH_SLEEP_S}s..."
  attempt=$((attempt + 1))
  sleep "${HEALTH_SLEEP_S}"
done

echo "✅ Healthcheck OK"

"$DOCKER_BIN" ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | head -n 20
