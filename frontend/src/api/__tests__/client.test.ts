import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../client";

const logMod = require("../../lib/analytics");
const logError = vi.spyOn(logMod, "logError").mockImplementation(() => {});

beforeEach(() => {
  vi.resetAllMocks();
});

describe("api client auth", () => {
  it("calls onAuthError + logs on 401", async () => {
    const onAuthError = vi.fn();
    const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const url = "/premium/plate";

    // Mock fetch to return 401
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      text: () => Promise.resolve(""),
      url: `${API_BASE}${url}`,
    } as unknown as Response);

    await expect(api(url, { method: "POST", body: {}, onAuthError })).rejects.toBeTruthy();
    expect(onAuthError).toHaveBeenCalledWith(401, expect.objectContaining({ clearApiKey: expect.any(Function) }));
    expect(logError).toHaveBeenCalled();
  });

  it("falls back to mockUrl on network error when forceMock is false", async () => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const url = "/premium/plate";
    const mockUrl = "/mocks/premium/plate.json";

    // 1-й вызов — сеть падает
    // 2-й вызов — мок успешен
    global.fetch = vi.fn()
      .mockRejectedValueOnce(new TypeError("Network down"))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ok: true }),
        url: mockUrl,
      } as unknown as Response);

    const res = await api(url, { method: "POST", body: {}, mockUrl, forceMock: false });
    expect(res).toEqual({ ok: true });

    // Проверяем порядок вызовов
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      `${API_BASE}${url}`,
      expect.objectContaining({ method: "POST" })
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      mockUrl,
      expect.objectContaining({ method: "POST" })
    );
  });
});
