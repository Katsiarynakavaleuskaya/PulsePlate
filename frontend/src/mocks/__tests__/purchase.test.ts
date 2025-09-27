/* @vitest-environment jsdom */
import { expect, test } from "vitest";

test("msw /api/purchase responds ok", async () => {
  const res = await fetch("/api/purchase", { method: "POST" });
  const json = await res.json();
  expect(json.status).toBe("ok");
  expect(json.entitlement).toBe("premium");
});
