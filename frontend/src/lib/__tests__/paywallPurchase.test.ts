import { beforeEach, describe, expect, it, vi } from "vitest";
import { purchasePremium } from "../paywallPurchase";

const apiMock = vi.fn();
const logMock = vi.fn();

vi.mock("../../api/client", () => ({
  api: (...args: unknown[]) => apiMock(...args),
}));

vi.mock("../analytics", () => ({
  Events: {
    PURCHASE_SUCCESS: "purchase_success",
  },
  log: (...args: unknown[]) => logMock(...args),
}));

describe("purchasePremium", () => {
  beforeEach(() => {
    apiMock.mockReset();
    logMock.mockReset();
    localStorage.clear();
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
  });
});
