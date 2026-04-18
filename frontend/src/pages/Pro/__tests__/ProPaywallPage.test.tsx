/* @vitest-environment jsdom */
import "../../../test/setup";
import "../../../i18n";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProPaywallPage from "../ProPaywallPage";
import { WEB_CHECKOUT_UNAVAILABLE_MESSAGE } from "../../../lib/paywallPurchase";

type PurchasePremium = typeof import("../../../lib/paywallPurchase")["purchasePremium"];

const { navigateMock, purchasePremiumMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  purchasePremiumMock: vi.fn<PurchasePremium>(),
}));
const logPaywallExposureMock = vi.fn();
const createAnalyticsEventIdMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../../lib/paywallPurchase", async () => {
  const actual = await vi.importActual<typeof import("../../../lib/paywallPurchase")>(
    "../../../lib/paywallPurchase"
  );
  return {
    ...actual,
    purchasePremium: purchasePremiumMock,
  };
});

vi.mock("../../../lib/analytics", () => ({
  Events: {
    PAYWALL_VIEW: "paywall_view",
    PURCHASE_ATTEMPT: "purchase_attempt",
    PURCHASE_CANCEL: "purchase_cancel",
  },
  createAnalyticsEventId: () => createAnalyticsEventIdMock(),
  logLegacyPaywallExposure: (...args: unknown[]) => logPaywallExposureMock(...args),
}));

function renderAtProRoute(state?: {
  exposureId?: string;
  source?: string;
  triggerReason?: string;
  via?: string;
}) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/pro", state }]}>
      <Routes>
        <Route path="/pro" element={<ProPaywallPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProPaywallPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createAnalyticsEventIdMock
      .mockReturnValueOnce("exposure-pro")
      .mockReturnValueOnce("event-pro-view")
      .mockReturnValueOnce("event-pro-cta");
  });

  it("uses direct /pro defaults without BMI-specific analytics on failed web purchase", async () => {
    purchasePremiumMock.mockRejectedValueOnce(new Error(WEB_CHECKOUT_UNAVAILABLE_MESSAGE));

    renderAtProRoute();

    fireEvent.click(screen.getByTestId("paywall-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("paywall-purchase-error")).toHaveTextContent(
        WEB_CHECKOUT_UNAVAILABLE_MESSAGE
      );
    });

    expect(purchasePremiumMock).toHaveBeenCalledWith({
      source: "pro_page",
      via: "pro_page",
    });
    expect(logPaywallExposureMock).toHaveBeenCalledWith("paywall_view", {
      client_event_id: "event-pro-view",
      exposure_id: "exposure-pro",
      source_surface: "pro_page",
      trigger_reason: "unknown",
      via: "pro_page",
      metadata: undefined,
    });
    expect(logPaywallExposureMock).toHaveBeenCalledWith("purchase_attempt", {
      client_event_id: "event-pro-cta",
      exposure_id: "exposure-pro",
      source_surface: "pro_page",
      trigger_reason: "unknown",
      via: "pro_page",
      metadata: undefined,
    });
    expect(logPaywallExposureMock).not.toHaveBeenCalledWith(
      "upgrade_started",
      expect.anything()
    );
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("reuses the same exposure id across direct /pro paywall view and purchase attempt", async () => {
    purchasePremiumMock.mockResolvedValueOnce(undefined);

    renderAtProRoute();

    fireEvent.click(screen.getByTestId("paywall-cta"));

    await waitFor(() => {
      expect(purchasePremiumMock).toHaveBeenCalledWith({
        source: "pro_page",
        via: "pro_page",
      });
      expect(logPaywallExposureMock).toHaveBeenCalledTimes(2);
      expect(logPaywallExposureMock).toHaveBeenNthCalledWith(1, "paywall_view", {
        client_event_id: "event-pro-view",
        exposure_id: "exposure-pro",
        source_surface: "pro_page",
        trigger_reason: "unknown",
        via: "pro_page",
        metadata: undefined,
      });
      expect(logPaywallExposureMock).toHaveBeenNthCalledWith(2, "purchase_attempt", {
        client_event_id: "event-pro-cta",
        exposure_id: "exposure-pro",
        source_surface: "pro_page",
        trigger_reason: "unknown",
        via: "pro_page",
        metadata: undefined,
      });
      expect(navigateMock).toHaveBeenCalledWith(-1);
    });

    expect(logPaywallExposureMock).not.toHaveBeenCalledWith(
      "upgrade_started",
      expect.anything()
    );
    expect(screen.queryByTestId("paywall-purchase-error")).not.toBeInTheDocument();
  });

  it("navigates back when the user closes the paywall", async (): Promise<void> => {
    renderAtProRoute();

    fireEvent.click(screen.getByTestId("paywall-cancel"));

    expect(purchasePremiumMock).not.toHaveBeenCalled();
    expect(navigateMock).toHaveBeenCalledWith(-1);
  });

  it("reuses teaser-provided route state for the paywall exposure lifecycle", async () => {
    purchasePremiumMock.mockResolvedValueOnce(undefined);

    renderAtProRoute({
      exposureId: "upstream-exposure-id",
      source: "bmi_soft_paywall",
      triggerReason: "post_bmi",
      via: "pro_page",
    });

    fireEvent.click(screen.getByTestId("paywall-cta"));

    await waitFor(() => {
      expect(logPaywallExposureMock).toHaveBeenNthCalledWith(1, "paywall_view", {
        client_event_id: "exposure-pro",
        exposure_id: "upstream-exposure-id",
        source_surface: "bmi_soft_paywall",
        trigger_reason: "post_bmi",
        via: "pro_page",
        metadata: undefined,
      });
      expect(logPaywallExposureMock).toHaveBeenNthCalledWith(2, "purchase_attempt", {
        client_event_id: "event-pro-view",
        exposure_id: "upstream-exposure-id",
        source_surface: "bmi_soft_paywall",
        trigger_reason: "post_bmi",
        via: "pro_page",
        metadata: undefined,
      });
      expect(purchasePremiumMock).toHaveBeenCalledWith({
        source: "bmi_soft_paywall",
        via: "pro_page",
      });
    });
  });
});
