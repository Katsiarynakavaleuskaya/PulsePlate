/* @vitest-environment jsdom */
import "../../../test/setup";
import "../../../i18n";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProPaywallPage from "../ProPaywallPage";
import { WEB_CHECKOUT_UNAVAILABLE_MESSAGE } from "../../../lib/paywallPurchase";

const navigateMock = vi.fn();
const purchasePremiumMock = vi.fn();

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
    purchasePremium: (...args: unknown[]) => purchasePremiumMock(...args),
  };
});

describe("ProPaywallPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("surfaces the release-safe checkout message and does not navigate on failed web purchase", async () => {
    purchasePremiumMock.mockRejectedValueOnce(new Error(WEB_CHECKOUT_UNAVAILABLE_MESSAGE));

    render(<ProPaywallPage />);

    fireEvent.click(screen.getByTestId("paywall-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("paywall-purchase-error")).toHaveTextContent(
        WEB_CHECKOUT_UNAVAILABLE_MESSAGE
      );
    });

    expect(purchasePremiumMock).toHaveBeenCalledWith({
      source: "bmi_soft_paywall",
      via: "pro_page",
    });
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("navigates back on successful web purchase without surfacing an error", async () => {
    purchasePremiumMock.mockResolvedValueOnce(undefined);

    render(<ProPaywallPage />);

    fireEvent.click(screen.getByTestId("paywall-cta"));

    await waitFor(() => {
      expect(purchasePremiumMock).toHaveBeenCalledWith({
        source: "bmi_soft_paywall",
        via: "pro_page",
      });
      expect(navigateMock).toHaveBeenCalledWith(-1);
    });

    expect(screen.queryByTestId("paywall-purchase-error")).toBeNull();
  });
});
