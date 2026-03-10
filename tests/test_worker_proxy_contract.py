from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_MODULE = REPO_ROOT / "worker.js"


def _run_worker_case(case_name: str) -> dict[str, object]:
    node_path = shutil.which("node")
    if node_path is None:
        pytest.skip("Node.js is required for worker proxy contract checks")

    script = f"""
import worker from {json.dumps(WORKER_MODULE.as_uri())};

const caseName = process.env.WORKER_CASE;
function toObject(headers) {{
  return Object.fromEntries(Array.from(headers.entries()).sort());
}}

async function main() {{
  let captured = null;

  globalThis.fetch = async (url, init) => {{
    captured = {{
      url,
      method: init.method,
      redirect: init.redirect,
      headers: Object.fromEntries(Array.from(init.headers.entries()).sort()),
      bodyLength: init.body ? init.body.byteLength : 0,
    }};
    return new Response("upstream-ok", {{
      status: 200,
      headers: {{
        "Content-Type": "application/json",
        "Vary": "Accept-Encoding",
      }},
    }});
  }};

  if (caseName === "method_not_allowed") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods", {{ method: "PUT" }}),
      {{
        TARGET_BASE: "https://api.pulseplate.app",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      body: await response.json(),
      captured,
    }}));
    return;
  }}

  if (caseName === "path_blocked") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/metrics", {{ method: "GET" }}),
      {{
        TARGET_BASE: "https://api.pulseplate.app",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      body: await response.json(),
      captured,
    }}));
    return;
  }}

  if (caseName === "missing_target_base") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods", {{
        method: "GET",
        headers: {{ Origin: "https://app.pulseplate.app" }},
      }}),
      {{
        TARGET_BASE: "",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      body: await response.json(),
      headers: toObject(response.headers),
      captured,
    }}));
    return;
  }}

  if (caseName === "originless_without_allowlist") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods", {{
        method: "GET",
      }}),
      {{
        TARGET_BASE: "https://api.pulseplate.app",
        WORKER_ALLOWED_ORIGINS: "",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      body: await response.json(),
      captured,
    }}));
    return;
  }}

  if (caseName === "invalid_target_base") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods", {{
        method: "GET",
        headers: {{ Origin: "https://app.pulseplate.app" }},
      }}),
      {{
        TARGET_BASE: "http://localhost:8000",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      body: await response.json(),
      headers: toObject(response.headers),
      captured,
    }}));
    return;
  }}

  if (caseName === "preflight_trusted_origin") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods", {{
        method: "OPTIONS",
        headers: {{ Origin: "https://app.pulseplate.app" }},
      }}),
      {{
        TARGET_BASE: "https://api.pulseplate.app",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app, https://admin.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      headers: toObject(response.headers),
      captured,
    }}));
    return;
  }}

  if (caseName === "blocked_origin") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods", {{
        method: "GET",
        headers: {{ Origin: "https://evil.example.com" }},
      }}),
      {{
        TARGET_BASE: "https://api.pulseplate.app",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      body: await response.json(),
      captured,
    }}));
    return;
  }}

  if (caseName === "forward_headers_and_vary") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods?q=1", {{
        method: "GET",
        headers: {{
          "Accept": "application/json",
          "Authorization": "Bearer abc",
          "CF-Connecting-IP": "203.0.113.10",
          "Content-Type": "application/json",
          "Cookie": "session=1",
          "Origin": "https://app.pulseplate.app",
          "Referer": "https://app.pulseplate.app/home",
          "X-API-Key": "pro-secret",
          "X-Forwarded-For": "203.0.113.10, 203.0.113.11",
          "CF-Ray": "blocked",
          "Host": "edge.example.com",
        }},
      }}),
      {{
        TARGET_BASE: "https://api.pulseplate.app",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      headers: toObject(response.headers),
      captured,
      body: await response.text(),
    }}));
    return;
  }}

  if (caseName === "post_body") {{
    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods", {{
        method: "POST",
        headers: {{
          "Content-Type": "application/json",
          "Origin": "https://app.pulseplate.app",
        }},
        body: JSON.stringify({{ grams: 250 }}),
      }}),
      {{
        TARGET_BASE: "https://api.pulseplate.app",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      captured,
      body: await response.text(),
    }}));
    return;
  }}

  if (caseName === "upstream_failure") {{
    globalThis.fetch = async () => {{
      throw new Error("dns failure");
    }};

    const response = await worker.fetch(
      new Request("https://edge.example.com/api/foods", {{
        method: "GET",
        headers: {{ Origin: "https://app.pulseplate.app" }},
      }}),
      {{
        TARGET_BASE: "https://api.pulseplate.app",
        WORKER_ALLOWED_ORIGINS: "https://app.pulseplate.app",
      }}
    );
    console.log(JSON.stringify({{
      status: response.status,
      body: await response.json(),
      headers: toObject(response.headers),
    }}));
    return;
  }}

  throw new Error(`Unknown worker case: ${{caseName}}`);
}}

main().catch((error) => {{
  console.error(error);
  process.exit(1);
}});
"""

    result = subprocess.run(
        [node_path, "--input-type=module", "--eval", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "WORKER_CASE": case_name},
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def test_worker_rejects_non_allowlisted_methods() -> None:
    payload = _run_worker_case("method_not_allowed")

    assert payload["status"] == 405
    assert payload["body"] == {"error": "Method not allowed", "status": 405}
    assert payload["captured"] is None


def test_worker_rejects_non_api_paths_before_fetch() -> None:
    payload = _run_worker_case("path_blocked")

    assert payload["status"] == 403
    assert payload["body"] == {
        "error": "Only /api/* paths are supported",
        "status": 403,
    }
    assert payload["captured"] is None


def test_worker_fails_closed_when_target_base_is_missing_or_invalid() -> None:
    missing = _run_worker_case("missing_target_base")
    invalid = _run_worker_case("invalid_target_base")

    assert missing["status"] == 500
    assert invalid["status"] == 500
    assert missing["body"] == {
        "error": "TARGET_BASE must be explicitly configured",
        "status": 500,
    }
    assert invalid["body"] == missing["body"]
    assert missing["captured"] is None
    assert invalid["captured"] is None
    assert missing["headers"]["access-control-allow-origin"] == "https://app.pulseplate.app"
    assert missing["headers"]["vary"] == "Origin"


def test_worker_preflight_reflects_only_trusted_origins() -> None:
    allowed = _run_worker_case("preflight_trusted_origin")
    blocked = _run_worker_case("blocked_origin")

    assert allowed["status"] == 204
    assert allowed["captured"] is None
    assert allowed["headers"]["access-control-allow-origin"] == "https://app.pulseplate.app"
    assert allowed["headers"]["access-control-allow-credentials"] == "true"
    assert allowed["headers"]["vary"] == "Origin"

    assert blocked["status"] == 403
    assert blocked["body"] == {"error": "Origin not allowed", "status": 403}
    assert blocked["captured"] is None


def test_worker_fails_closed_without_origin_when_allowlist_is_missing() -> None:
    payload = _run_worker_case("originless_without_allowlist")

    assert payload["status"] == 403
    assert payload["body"] == {"error": "Origin not allowed", "status": 403}
    assert payload["captured"] is None


def test_worker_forwards_only_bounded_headers_and_preserves_vary() -> None:
    payload = _run_worker_case("forward_headers_and_vary")
    captured = payload["captured"]

    assert payload["status"] == 200
    assert payload["body"] == "upstream-ok"
    assert captured["url"] == "https://api.pulseplate.app/api/foods?q=1"
    assert captured["method"] == "GET"
    assert captured["redirect"] == "manual"
    assert captured["bodyLength"] == 0
    assert captured["headers"] == {
        "accept": "application/json",
        "authorization": "Bearer abc",
        "cf-connecting-ip": "203.0.113.10",
        "content-type": "application/json",
        "cookie": "session=1",
        "x-api-key": "pro-secret",
        "x-forwarded-for": "203.0.113.10, 203.0.113.11",
    }
    assert payload["headers"]["access-control-allow-origin"] == "https://app.pulseplate.app"
    assert payload["headers"]["vary"] == "Accept-Encoding, Origin"


def test_worker_forwards_post_bodies_to_allowed_upstream_paths() -> None:
    payload = _run_worker_case("post_body")
    captured = payload["captured"]

    assert payload["status"] == 200
    assert payload["body"] == "upstream-ok"
    assert captured["method"] == "POST"
    assert captured["bodyLength"] > 0


def test_worker_normalizes_upstream_transport_failures() -> None:
    payload = _run_worker_case("upstream_failure")

    assert payload["status"] == 502
    assert payload["body"] == {
        "error": "Upstream request failed",
        "status": 502,
    }
    assert payload["headers"]["access-control-allow-origin"] == "https://app.pulseplate.app"
    assert payload["headers"]["vary"] == "Origin"
