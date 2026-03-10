const ALLOWED_METHODS = new Set(["GET", "POST", "OPTIONS"]);
const ALLOWED_FORWARD_HEADERS = [
  "accept",
  "authorization",
  "content-type",
  "cookie",
  "x-api-key",
];
const ALLOWED_PREFLIGHT_HEADERS = "Content-Type, Authorization, X-API-Key";
const PLACEHOLDER_TARGET_SNIPPETS = [
  "replace_me",
  "trycloudflare.com",
  "example.com",
];

function jsonError(message, status) {
  return new Response(JSON.stringify({ error: message, status }), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}

function normalizeTargetBase(env) {
  const targetBase = (env.TARGET_BASE || "").trim();
  const lowered = targetBase.toLowerCase();

  if (
    !targetBase ||
    PLACEHOLDER_TARGET_SNIPPETS.some((snippet) => lowered.includes(snippet))
  ) {
    return null;
  }

  try {
    return new URL(targetBase);
  } catch {
    return null;
  }
}

function parseAllowedOrigins(env) {
  return new Set(
    (env.WORKER_ALLOWED_ORIGINS || "")
      .split(",")
      .map((origin) => origin.trim())
      .filter(Boolean)
  );
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Headers": ALLOWED_PREFLIGHT_HEADERS,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function trustedOriginOrNull(request, env) {
  const requestOrigin = request.headers.get("Origin");
  if (!requestOrigin) {
    return null;
  }

  const allowedOrigins = parseAllowedOrigins(env);
  if (allowedOrigins.size === 0) {
    return false;
  }

  return allowedOrigins.has(requestOrigin) ? requestOrigin : false;
}

function buildForwardHeaders(request) {
  const headers = new Headers();

  for (const name of ALLOWED_FORWARD_HEADERS) {
    const value = request.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }

  return headers;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const trustedOrigin = trustedOriginOrNull(request, env);
    const targetBase = normalizeTargetBase(env);

    if (!ALLOWED_METHODS.has(request.method)) {
      return jsonError("Method not allowed", 405);
    }

    if (!url.pathname.startsWith("/api/")) {
      return jsonError("Only /api/* paths are supported", 403);
    }

    if (!targetBase) {
      return jsonError("TARGET_BASE must be explicitly configured", 500);
    }

    if (trustedOrigin === false) {
      return jsonError("Origin not allowed", 403);
    }

    if (request.method === "OPTIONS") {
      if (!trustedOrigin) {
        return jsonError("Trusted browser origin is required", 403);
      }
      return new Response(null, {
        status: 204,
        headers: corsHeaders(trustedOrigin),
      });
    }

    const upstream = new URL(url.pathname + url.search, targetBase.toString());
    const init = {
      method: request.method,
      headers: buildForwardHeaders(request),
      body:
        request.method === "GET"
          ? undefined
          : await request.arrayBuffer(),
      redirect: "manual",
    };

    const resp = await fetch(upstream.toString(), init);
    const out = new Response(resp.body, resp);

    if (trustedOrigin) {
      for (const [key, value] of Object.entries(corsHeaders(trustedOrigin))) {
        out.headers.set(key, value);
      }
    }

    return out;
  },
};
