import { http, HttpResponse, delay } from "msw";

const matchesApiPath = (expectedPathname: string) => {
  return ({ request }: { request: Request }) => {
    return new URL(request.url).pathname === expectedPathname;
  };
};

export const handlers = [
  // Явно матчим pathname, чтобы не зависеть от wildcard coercion в path-to-regexp 8.x.
  // Match pathname explicitly to avoid wildcard coercion issues in path-to-regexp 8.x.
  http.post(matchesApiPath("/api/purchase"), async ({ request: _request }) => {
    await delay(300);

    // Simulate error scenarios for testing
    const url = new URL(_request.url);
    const errorParam = url.searchParams.get('error');

    if (errorParam === 'network') {
      return HttpResponse.error();
    }

    if (errorParam === 'server') {
      return HttpResponse.json({ error: "Internal server error" }, { status: 500 });
    }

    if (errorParam === 'payment') {
      return HttpResponse.json({ error: "Payment failed", code: "INSUFFICIENT_FUNDS" }, { status: 402 });
    }

    // Default success response
    return HttpResponse.json({ status: "ok", entitlement: "premium" }, { status: 200 });
  }),

  http.post(matchesApiPath("/api/restore"), async ({ request: _request }) => {
    await delay(200);

    // Simulate error scenarios for testing
    const url = new URL(_request.url);
    const errorParam = url.searchParams.get('error');

    if (errorParam === 'network') {
      return HttpResponse.error();
    }

    if (errorParam === 'server') {
      return HttpResponse.json({ error: "Restore service unavailable" }, { status: 503 });
    }

    if (errorParam === 'not_found') {
      return HttpResponse.json({ error: "No purchases found" }, { status: 404 });
    }

    // Default success response
    return HttpResponse.json({ status: "ok", restored: true }, { status: 200 });
  }),
];
