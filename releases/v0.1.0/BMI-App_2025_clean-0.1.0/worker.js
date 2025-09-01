export default {
  async fetch(request, env, ctx) {
    const TARGET_BASE = env.TARGET_BASE || "https://REPLACE_ME.trycloudflare.com";
    const url = new URL(request.url);
    const upstream = new URL(url.pathname + url.search, TARGET_BASE);

    if (request.method === "OPTIONS") {
      const r = new Response(null, { status: 204 });
      r.headers.set("Access-Control-Allow-Origin", "*");
      r.headers.set("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
      r.headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization");
      r.headers.set("Access-Control-Max-Age", "86400");
      return r;
    }

    const init = {
      method: request.method,
      headers: new Headers(request.headers),
      body: ["GET","HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
      redirect: "follow",
    };

    const resp = await fetch(upstream.toString(), init);
    const out = new Response(resp.body, resp);
    out.headers.set("Access-Control-Allow-Origin", "*");
    return out;
  }
}
