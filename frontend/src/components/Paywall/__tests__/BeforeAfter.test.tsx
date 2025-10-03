/* @vitest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { vi, describe, test, expect, afterEach, beforeAll } from "vitest";
import "@testing-library/jest-dom";
import BeforeAfter from "../BeforeAfter";
import "../../../test/setup";
import i18n from "../../../i18n";

beforeAll(async () => {
  await new Promise<void>((resolve, reject) => {
    let handler: (() => void) | null = null;
    const timeout = setTimeout(() => {
      if (handler) {
        i18n.off("initialized", handler);
        handler = null;
      }
      reject(new Error("i18n initialization timeout"));
    }, 5000);

    handler = () => {
      if (handler) {
        i18n.off("initialized", handler);
        handler = null;
      }
      clearTimeout(timeout);
      resolve();
    };

    // Register listener first to avoid race condition
    i18n.on("initialized", handler);

    // Immediately re-check if already initialized after registering listener
    if (i18n.isInitialized) {
      // Remove the listener since we don't need it
      i18n.off("initialized", handler);
      handler = null;
      // Clear the timeout since we're resolving immediately
      clearTimeout(timeout);
      resolve();
    }
  });
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

  test("fires purchase_attempt on CTA click", () => {
    const onPurchase = vi.fn();
    render(<BeforeAfter onClose={() => {}} onPurchase={onPurchase} />);

    const ctas = screen.getAllByTestId("paywall-cta");
    fireEvent.click(ctas[0]);
    expect(onPurchase).toHaveBeenCalled();
    // Should have PAYWALL_VIEW (on mount) + PURCHASE_ATTEMPT (on click)
    expect(log).toHaveBeenCalledTimes(2);
    expect(log).toHaveBeenCalledWith(Events.PAYWALL_VIEW, expect.anything());
    expect(log).toHaveBeenCalledWith(Events.PURCHASE_ATTEMPT, expect.anything());
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
});
