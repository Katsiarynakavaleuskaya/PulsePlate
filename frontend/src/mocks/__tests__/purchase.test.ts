/* @vitest-environment jsdom */
import "../../test/setup";
import { beforeEach, expect, test } from "vitest";
import { delay, http, HttpResponse } from "msw";
import { server } from "../server";

const BASE_URL = "http://localhost";

const matchesApiPath =
  (expectedPathname: string) =>
  ({ request }: { request: Request }): boolean =>
    new URL(request.url).pathname === expectedPathname;

function registerPurchaseHandlers(): void {
  server.use(
    http.post(matchesApiPath("/api/purchase"), async ({ request }) => {
      await delay(300);
      const errorParam = new URL(request.url).searchParams.get("error");

      if (errorParam === "network") {
        return HttpResponse.error();
      }
      if (errorParam === "server") {
        return HttpResponse.json({ error: "Internal server error" }, { status: 500 });
      }
      if (errorParam === "payment") {
        return HttpResponse.json(
          { error: "Payment failed", code: "INSUFFICIENT_FUNDS" },
          { status: 402 }
        );
      }

      return HttpResponse.json({ status: "ok", entitlement: "premium" }, { status: 200 });
    }),
    http.post(matchesApiPath("/api/restore"), async ({ request }) => {
      await delay(200);
      const errorParam = new URL(request.url).searchParams.get("error");

      if (errorParam === "network") {
        return HttpResponse.error();
      }
      if (errorParam === "server") {
        return HttpResponse.json({ error: "Restore service unavailable" }, { status: 503 });
      }
      if (errorParam === "not_found") {
        return HttpResponse.json({ error: "No purchases found" }, { status: 404 });
      }

      return HttpResponse.json({ status: "ok", restored: true }, { status: 200 });
    })
  );
}

beforeEach(() => {
  registerPurchaseHandlers();
});

test("msw /api/purchase responds ok", async () => {
  const res = await fetch(`${BASE_URL}/api/purchase`, { method: "POST" });
  const json = await res.json();
  expect(json.status).toBe("ok");
  expect(json.entitlement).toBe("premium");
});

test("msw /api/purchase handles server error", async () => {
  const res = await fetch(`${BASE_URL}/api/purchase?error=server`, { method: "POST" });
  expect(res.status).toBe(500);
  const json = await res.json();
  expect(json.error).toBe("Internal server error");
});

test("msw /api/purchase handles payment error", async () => {
  const res = await fetch(`${BASE_URL}/api/purchase?error=payment`, { method: "POST" });
  expect(res.status).toBe(402);
  const json = await res.json();
  expect(json.error).toBe("Payment failed");
  expect(json.code).toBe("INSUFFICIENT_FUNDS");
});

test("msw /api/restore responds ok", async () => {
  const res = await fetch(`${BASE_URL}/api/restore`, { method: "POST" });
  const json = await res.json();
  expect(json.status).toBe("ok");
  expect(json.restored).toBe(true);
});

test("msw /api/restore handles server error", async () => {
  const res = await fetch(`${BASE_URL}/api/restore?error=server`, { method: "POST" });
  expect(res.status).toBe(503);
  const json = await res.json();
  expect(json.error).toBe("Restore service unavailable");
});

test("msw /api/restore handles not found error", async () => {
  const res = await fetch(`${BASE_URL}/api/restore?error=not_found`, { method: "POST" });
  expect(res.status).toBe(404);
  const json = await res.json();
  expect(json.error).toBe("No purchases found");
});
