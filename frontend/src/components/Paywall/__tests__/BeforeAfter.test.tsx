/* @vitest-environment jsdom */
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { vi, describe, test, expect, afterEach, beforeAll } from "vitest";
import "@testing-library/jest-dom";
import BeforeAfter from "../BeforeAfter";
import "../../../test/setup";
import i18n from "../../../i18n";

beforeAll(async () => {
  // Wait for i18n to be ready with timeout
  if (!i18n.isInitialized) {
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("i18n initialization timeout"));
      }, 5000);

      const handler = () => {
        i18n.off("initialized", handler);
        clearTimeout(timeout);
        resolve();
      };

      // Register listener first to avoid race condition
      i18n.on("initialized", handler);

      // Immediately re-check if already initialized after registering listener
      if (i18n.isInitialized) {
        i18n.off("initialized", handler);
        clearTimeout(timeout);
        resolve();
      }
    });
  } else {
    // i18n is already initialized, nothing to wait for
    await Promise.resolve();
  }
});


// Mock analytics to verify calls
vi.mock("../../../lib/analytics", () => {
  return {
    log: vi.fn(),
    Events: {
      PAYWALL_VIEW: "paywall_view",
      PURCHASE_ATTEMPT: "purchase_attempt",
      PURCHASE_CANCEL: "purchase_cancel",
      PURCHASE_SUCCESS: "purchase_success",
      RESTORE_SUCCESS: "restore_success",
    },
  };
});

import { log, Events } from "../../../lib/analytics";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Paywall BeforeAfter", () => {
  test("renders dialog and logs view", () => {
    render(<BeforeAfter onClose={() => {}} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(log).toHaveBeenCalledWith(Events.PAYWALL_VIEW, expect.anything());
  });

  test("fires purchase_attempt on CTA click", async (): Promise<void> => {
    const onPurchase = vi.fn();
    render(<BeforeAfter onClose={() => {}} onPurchase={onPurchase} />);

    const ctas = screen.getAllByTestId("paywall-cta");
    fireEvent.click(ctas[0]);
    await waitFor(() => {
      expect(onPurchase).toHaveBeenCalled();
      // Should have PAYWALL_VIEW (on mount) + PURCHASE_ATTEMPT (on click)
      expect(log).toHaveBeenCalledTimes(2);
      expect(log).toHaveBeenCalledWith(Events.PAYWALL_VIEW, expect.anything());
      expect(log).toHaveBeenCalledWith(Events.PURCHASE_ATTEMPT, expect.anything());
    });
  });

  test("shows purchase error when callback rejects", async (): Promise<void> => {
    const onPurchase = vi.fn().mockRejectedValue(new Error("Payment failed"));
    render(<BeforeAfter onClose={() => {}} onPurchase={onPurchase} />);

    fireEvent.click(screen.getByTestId("paywall-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("paywall-purchase-error")).toHaveTextContent("Payment failed");
    });
  });

  test("fires purchase_cancel on Cancel click", () => {
    const onClose = vi.fn();
    render(<BeforeAfter onClose={onClose} />);

    const cancelBtns = screen.getAllByTestId("paywall-cancel");
    fireEvent.click(cancelBtns[0]);
    expect(onClose).toHaveBeenCalled();
    // Should have PAYWALL_VIEW (on mount) + PURCHASE_CANCEL (on click)
    expect(log).toHaveBeenCalledTimes(2);
    expect(log).toHaveBeenCalledWith(Events.PAYWALL_VIEW, expect.anything());
    expect(log).toHaveBeenCalledWith(Events.PURCHASE_CANCEL, expect.anything());
  });

  test("disables body scroll when modal opens and restores on unmount", () => {
    // Store original overflow value
    const originalOverflow = document.body.style.overflow;

    // Render modal
    const { unmount } = render(<BeforeAfter onClose={() => {}} />);

    // Check that body scroll is disabled
    expect(document.body.style.overflow).toBe("hidden");

    // Unmount modal
    unmount();

    // Check that body scroll is restored
    expect(document.body.style.overflow).toBe(originalOverflow);
  });
});
