const ALLOWED_METHODS = new Set(["GET", "POST", "OPTIONS"]);
const BODYLESS_METHODS = new Set(["GET", "HEAD"]);
const ALLOWED_FORWARD_HEADERS = [
  "accept",
  "authorization",
  "cf-connecting-ip",
  "content-type",
  "cookie",
  "x-forwarded-for",
  "x-api-key",
];
const ALLOWED_PREFLIGHT_HEADERS = "Content-Type, Authorization, X-API-Key";
const PLACEHOLDER_TARGET_HOSTS = new Set(["example.com", "localhost", "127.0.0.1"]);
const PLACEHOLDER_TARGET_SUFFIXES = [".trycloudflare.com"];
let cachedAllowedOriginsRaw = null;
let cachedAllowedOrigins = new Set();

/**
 * @typedef {{
 *   TARGET_BASE?: string,
 *   WORKER_ALLOWED_ORIGINS?: string
 * }} WorkerEnv
 */

/**
 * @typedef {false | null | string} TrustedOrigin
 */

/**
 * @param {string} message
 * @param {number} status
 * @returns {Response}
 */
function jsonError(message, status) {
  return new Response(JSON.stringify({ error: message, status }), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}

/**
 * @param {WorkerEnv} env
 * @returns {URL | null}
 */
function normalizeTargetBase(env) {
  const targetBase = (env.TARGET_BASE || "").trim();
  if (!targetBase) {
    return null;
  }

  try {
    const parsed = new URL(targetBase);
    const hostname = parsed.hostname.toLowerCase();
    const isPlaceholderHost = PLACEHOLDER_TARGET_HOSTS.has(hostname);
    const isPlaceholderSuffix = PLACEHOLDER_TARGET_SUFFIXES.some(
      (suffix) => hostname === suffix.slice(1) || hostname.endsWith(suffix)
    );

    if (parsed.protocol !== "https:" || isPlaceholderHost || isPlaceholderSuffix) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}

/**
 * @param {string} rawOrigins
 * @returns {Set<string>}
 */
function parseAllowedOrigins(rawOrigins) {
  if (rawOrigins === cachedAllowedOriginsRaw) {
    return cachedAllowedOrigins;
  }

  cachedAllowedOriginsRaw = rawOrigins;
  cachedAllowedOrigins = new Set(
    rawOrigins
      .split(",")
      .map((origin) => origin.trim())
      .filter(Boolean)
  );
  return cachedAllowedOrigins;
}

/**
 * @param {string} origin
 * @returns {Record<string, string>}
 */
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

/**
 * @param {Headers} headers
 * @param {string} value
 * @returns {void}
 */
function mergeVaryHeader(headers, value) {
  const existing = headers.get("Vary");
  const merged = new Set(
    (existing || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
  );
  merged.add(value);
  headers.set("Vary", Array.from(merged).join(", "));
}

/**
 * @param {Request} request
 * @param {WorkerEnv} env
 * @returns {TrustedOrigin}
 */
function trustedOriginOrNull(request, env) {
  const requestOrigin = request.headers.get("Origin");
  if (!requestOrigin) {
    return null;
  }

  const allowedOrigins = parseAllowedOrigins(env.WORKER_ALLOWED_ORIGINS || "");
  if (allowedOrigins.size === 0) {
    return false;
  }

  return allowedOrigins.has(requestOrigin) ? requestOrigin : false;
}

/**
 * @param {Request} request
 * @returns {Headers}
 */
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
  /**
   * @param {Request} request
   * @param {WorkerEnv} env
   * @returns {Promise<Response>}
   */
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
      body: BODYLESS_METHODS.has(request.method)
        ? undefined
        : await request.arrayBuffer(),
      redirect: "manual",
    };

    const resp = await fetch(upstream.toString(), init);
    const out = new Response(resp.body, resp);

    if (trustedOrigin) {
      for (const [key, value] of Object.entries(corsHeaders(trustedOrigin))) {
        if (key === "Vary") {
          mergeVaryHeader(out.headers, value);
        } else {
          out.headers.set(key, value);
        }
      }
    }

    return out;
  },
};
