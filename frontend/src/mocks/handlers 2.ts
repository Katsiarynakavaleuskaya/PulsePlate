import { http, HttpResponse, delay } from "msw";

export const handlers = [
  // Работает на любом origin: */api/purchase
  http.post("*/api/purchase", async ({ request: _request }) => {
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

  http.post("*/api/restore", async ({ request: _request }) => {
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
