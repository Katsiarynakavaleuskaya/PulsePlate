/* @vitest-environment jsdom */
import "../../test/setup";
import { expect, test } from "vitest";

const BASE_URL = "http://localhost";

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
