import { beforeEach, describe, expect, it, vi } from "vitest";
import { purchasePremium } from "../paywallPurchase";

const apiMock = vi.fn();
const logMock = vi.fn();
const premiumStorage = new Map<string, string>();
const localStorageMock = {
  getItem: vi.fn((key: string) => premiumStorage.get(key) ?? null),
  setItem: vi.fn((key: string, value: string) => {
    premiumStorage.set(key, value);
  }),
  removeItem: vi.fn((key: string) => {
    premiumStorage.delete(key);
  }),
  clear: vi.fn(() => {
    premiumStorage.clear();
  }),
};

Object.defineProperty(window, "localStorage", {
  configurable: true,
  writable: true,
  value: localStorageMock,
});

Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  writable: true,
  value: localStorageMock,
});

vi.mock("../../api/client", () => ({
  api: (...args: unknown[]) => apiMock(...args),
}));

vi.mock("../analytics", () => ({
  Events: {
    PURCHASE_SUCCESS: "purchase_success",
    PURCHASE_FAILURE: "purchase_failure",
  },
  log: (...args: unknown[]) => logMock(...args),
}));

describe("purchasePremium", () => {
  beforeEach(() => {
    apiMock.mockReset();
    logMock.mockReset();
    premiumStorage.clear();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
    localStorageMock.clear.mockClear();
  });

  it("stores premium flag and emits premium-change event on success", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    apiMock.mockResolvedValue({ status: "ok", entitlement: "premium" });

    await purchasePremium({ source: "plate", via: "paywall_cta" });

    expect(apiMock).toHaveBeenCalledWith("/api/purchase", {
      method: "POST",
      body: {
        source: "plate",
        via: "paywall_cta",
      },
    });
    expect(localStorage.getItem("pp_premium")).toBe("true");
    expect(dispatchSpy).toHaveBeenCalledTimes(1);
    expect(logMock).toHaveBeenCalledWith("purchase_success", {
      source: "plate",
      via: "paywall_cta",
      entitlement: "premium",
    });
  });

  it("throws when purchase status is not ok", async () => {
    apiMock.mockResolvedValue({ status: "error" });

    await expect(
      purchasePremium({ source: "plate", via: "paywall_cta" })
    ).rejects.toThrow("Purchase failed");

    expect(localStorage.getItem("pp_premium")).toBeNull();
    expect(logMock).toHaveBeenCalledWith("purchase_failure", {
      source: "plate",
      via: "paywall_cta",
      status: "error",
    });
  });
});
