import { beforeEach, describe, expect, it, vi } from "vitest";
import { purchasePremium, WEB_CHECKOUT_UNAVAILABLE_MESSAGE } from "../paywallPurchase";

const logMock = vi.fn();

vi.mock("../analytics", () => ({
  Events: {
    PURCHASE_SUCCESS: "purchase_success",
    PURCHASE_FAILURE: "purchase_failure",
  },
  log: (...args: unknown[]) => logMock(...args),
}));

describe("purchasePremium", () => {
  beforeEach(() => {
    logMock.mockReset();
  });

  it("fails closed with a release-safe checkout message", async () => {
    await expect(
      purchasePremium({ source: "plate", via: "paywall_cta" })
    ).rejects.toThrow(WEB_CHECKOUT_UNAVAILABLE_MESSAGE);
    expect(logMock).toHaveBeenCalledWith("purchase_failure", {
      source: "plate",
      via: "paywall_cta",
      status: "web_checkout_unavailable",
    });
  });

  it("records hint context when the paywall seam receives next_best_action metadata", async () => {
    await expect(
      purchasePremium({
        source: "bmi_soft_paywall",
        via: "pro_page",
        triggerReason: "post_bmi",
        actionType: "unlock_targets",
        recommendedSurface: "pro_targets",
        recommendedTier: "PRO",
        whyNow: "post_bmi_baseline_body_metrics",
      })
    ).rejects.toThrow(WEB_CHECKOUT_UNAVAILABLE_MESSAGE);

    expect(logMock).toHaveBeenCalledWith("purchase_failure", {
      source: "bmi_soft_paywall",
      via: "pro_page",
      status: "web_checkout_unavailable",
      triggerReason: "post_bmi",
      actionType: "unlock_targets",
      recommendedSurface: "pro_targets",
      recommendedTier: "PRO",
      whyNow: "post_bmi_baseline_body_metrics",
    });
  });
});
