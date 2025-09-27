import { http, HttpResponse, delay } from "msw";

export const handlers = [
  // Работает на любом origin: */api/purchase
  http.post("*/api/purchase", async ({ request }) => {
    await delay(300);
    // Можно прочитать body при желании: await request.json()
    return HttpResponse.json({ status: "ok", entitlement: "premium" }, { status: 200 });
  }),

  http.post("*/api/restore", async () => {
    await delay(200);
    return HttpResponse.json({ status: "ok", restored: true }, { status: 200 });
  }),
];
